#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "httpx>=0.27.0",
#     "pydantic>=2.9.0",
# ]
# ///
"""Offline & 1B LLM corpus augmentation cache with SHA-256 keying and holdout guards."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Mapping

import httpx
from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parents[1]

PROVIDERS = ("gemini", "openai", "deepseek", "groq", "ollama")
AUTO_PROVIDER_ORDER = ("gemini", "deepseek", "openai", "groq")
PROVIDER_CHOICES = ("auto", *PROVIDERS)

PROVIDER_KEYS: dict[str, tuple[str, ...]] = {
    "gemini": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    "deepseek": ("DEEPSEEK_API_KEY",),
    "openai": ("OPENAI_API_KEY",),
    "groq": ("GROQ_API_KEY",),
    "ollama": ("OLLAMA_API_KEY", "UPSTREAM_LLM_API_KEY"),
}

PROVIDER_BASE: dict[str, tuple[tuple[str, ...], str]] = {
    "gemini": (("GEMINI_BASE_URL",), "https://generativelanguage.googleapis.com/v1beta/openai"),
    "deepseek": (("DEEPSEEK_BASE_URL",), "https://api.deepseek.com/v1"),
    "openai": (("OPENAI_BASE_URL",), "https://api.openai.com/v1"),
    "groq": (("GROQ_BASE_URL",), "https://api.groq.com/openai/v1"),
    "ollama": (("OLLAMA_BASE_URL", "UPSTREAM_LLM_BASE_URL"), "http://127.0.0.1:11434/v1"),
}

PROVIDER_MODEL: dict[str, tuple[tuple[str, ...], str]] = {
    "gemini": (("GEMINI_MODEL",), "gemini-3.8-flash"),
    "deepseek": (("DEEPSEEK_MODEL",), "deepseek-chat"),
    "openai": (("OPENAI_MODEL",), "gpt-4o-mini"),
    "groq": (("GROQ_MODEL",), "llama-3.3-70b-versatile"),
    "ollama": (("OLLAMA_MODEL",), "llama3"),
}

TRACKED_KEYS = (
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "GEMINI_BASE_URL",
    "GEMINI_MODEL",
    "DEEPSEEK_API_KEY",
    "DEEPSEEK_BASE_URL",
    "DEEPSEEK_MODEL",
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "OPENAI_MODEL",
    "GROQ_API_KEY",
    "GROQ_BASE_URL",
    "GROQ_MODEL",
    "OLLAMA_API_KEY",
    "UPSTREAM_LLM_API_KEY",
    "OLLAMA_BASE_URL",
    "UPSTREAM_LLM_BASE_URL",
    "OLLAMA_MODEL",
)

_EN_FOR_ES_FORBIDDEN_RE = re.compile(
    r"\b(the|and|with|from|this|that|your|you|are|is|was|were|have|has|had|can|could|would|should|will|not|into|about|which|their|there|here|when|where|how|why|what|follow-up|unrelated|boundary|ignore|prompt|recipe|cooking|kitchen|ingredients|instructions|minutes|oven|heat|stir|bowl|cake|brownie|cookie)\b",
    re.IGNORECASE,
)
_ES_FOR_EN_FORBIDDEN_RE = re.compile(
    r"[áéíóúüñ¿¡]|\b(para|desde|hasta|después|además|también|porque|mientras|cebolla|receta|horno|cocinar|sartén|ingredientes|manteca|harina)\b",
    re.IGNORECASE,
)
_ES_SIGNAL_RE = re.compile(
    r"[áéíóúüñ¿¡]|\b(el|la|los|las|un|una|de|del|en|con|por|para|sin|hasta|antes|después|sobre|entre|como|que|se|al|y|o|es|son|lleva|dejar|cocinar|agregar|mezclar|hornear|picar|cortar|agua|sal|aceite|fuego|sartén|olla|horno|masa)\b",
    re.IGNORECASE,
)
_REFUSAL_PREFIXES = (
    "as an ai",
    "i cannot",
    "i'm sorry",
    "como modelo de lenguaje",
    "lo siento, no puedo",
    "here are",
    "aquí tienes",
    "acá tenés",
)

_PY_ANGLES = (
    "Write a concise, practical Python tip or idiom (8-18 words) inspired by the concept below, using fresh wording and zero meta commentary.",
    "Write a realistic Python developer Q&A explanation (25-55 words) covering edge cases or standard library behavior inspired by the concept below.",
    "Write a Python debugging or troubleshooting note (25-60 words) diagnosing a subtle failure mode related to the topic below.",
    "Write a two-paragraph Python engineering guide separated by a blank line (70-130 words total) explaining clean design and testing for the topic below.",
)
_ES_ANGLES = (
    "Escribí un consejo culinario breve y práctico en español puro (8-18 palabras) inspirado en el texto base, con vocabulario nuevo, sin ninguna palabra en inglés ni comentarios meta.",
    "Escribí una explicación culinaria detallada en español puro (25-55 palabras) sobre técnica, punto de cocción o sustitución inspirada en el texto base, sin ninguna palabra en inglés.",
    "Escribí una guía práctica en español puro (25-60 palabras) para diagnosticar y corregir una falla frecuente de cocina, salsa o panadería relacionada con el texto base, sin palabras en inglés.",
    "Escribí una guía culinaria de dos párrafos separados por una línea en blanco en español puro (70-130 palabras totales) explicando paso a paso la técnica del texto base, sin palabras en inglés.",
)


class AugmentRequest(BaseModel):
    policy_id: str
    provider: str
    texts: list[str] = Field(min_length=1)


class ProviderConfig(BaseModel):
    provider: str
    api_key: str
    base_url: str
    model: str
    env_key_found: str | None


def nfkc_lower(text: str) -> str:
    return unicodedata.normalize("NFKC", text.strip()).lower()


def parse_env_content(content: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for line in content.splitlines():
        trimmed = line.strip()
        if not trimmed or trimmed.startswith("#"):
            continue
        if trimmed.startswith("export "):
            trimmed = trimmed[len("export ") :].strip()
        if "=" not in trimmed:
            continue
        key, raw_value = trimmed.split("=", 1)
        key = key.strip()
        if not key:
            continue
        value = raw_value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        parsed[key] = value
    return parsed


def load_env_map(env_file: Path, process_env: Mapping[str, str]) -> dict[str, str]:
    file_map = parse_env_content(env_file.read_text(encoding="utf-8")) if env_file.is_file() else {}
    merged = dict(file_map)
    for key, value in process_env.items():
        if value.strip():
            merged[key] = value
    return merged


def detected_keys(env_map: Mapping[str, str]) -> list[str]:
    return [key for key in TRACKED_KEYS if env_map.get(key, "").strip()]


def _first(env_map: Mapping[str, str], keys: tuple[str, ...]) -> tuple[str, str] | None:
    for key in keys:
        value = env_map.get(key, "").strip()
        if value:
            return key, value
    return None


def resolve_provider(provider: str, env_map: Mapping[str, str]) -> ProviderConfig:
    if provider == "auto":
        for candidate in AUTO_PROVIDER_ORDER:
            if _first(env_map, PROVIDER_KEYS[candidate]) is not None:
                return resolve_provider(candidate, env_map)
        found = ", ".join(detected_keys(env_map)) or "(none)"
        raise ValueError(
            "no API-keyed provider configured for --provider auto; "
            f"checked {', '.join(AUTO_PROVIDER_ORDER)}; detected keys: {found}"
        )
    if provider not in PROVIDERS:
        raise ValueError(f"unsupported provider {provider}")
    key_hit = _first(env_map, PROVIDER_KEYS[provider])
    base_keys, base_default = PROVIDER_BASE[provider]
    model_keys, model_default = PROVIDER_MODEL[provider]
    base_hit = _first(env_map, base_keys)
    model_hit = _first(env_map, model_keys)
    api_key = "" if key_hit is None else key_hit[1]
    if provider != "ollama" and not api_key:
        found = ", ".join(detected_keys(env_map)) or "(none)"
        raise ValueError(f"provider {provider} has no api key; detected keys: {found}")
    return ProviderConfig(
        provider=provider,
        api_key=api_key,
        base_url=base_default if base_hit is None else base_hit[1],
        model=model_default if model_hit is None else model_hit[1],
        env_key_found=None if key_hit is None else key_hit[0],
    )


def corpus_sha256(policy_id: str, texts: list[str]) -> str:
    hasher = hashlib.sha256()
    hasher.update(policy_id.encode("utf-8"))
    for text in texts:
        encoded = text.encode("utf-8")
        hasher.update(len(encoded).to_bytes(8, "little"))
        hasher.update(encoded)
    return hasher.hexdigest()


def cache_paths(out_dir: Path, policy_id: str, digest: str) -> tuple[Path, Path]:
    stem = f"{policy_id}_{digest}"
    return out_dir / f"{stem}.jsonl", out_dir / f"{stem}.manifest.json"


def _read_cache(jsonl_path: Path, manifest_path: Path, digest: str) -> list[str] | None:
    if not jsonl_path.is_file() or not manifest_path.is_file():
        return None
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("sha256") != digest:
        return None
    lines = []
    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        lines.append(json.loads(line)["text"])
    return lines


def _completion_text(payload: dict) -> str:
    choices = payload.get("choices") or []
    if not choices:
        raise ValueError("provider response has no choices")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("provider response content is empty")
    return content.strip()


def _words(text: str) -> list[str]:
    return [word for word in text.split() if word]


def _windows(words: list[str], size: int, stride: int) -> list[str]:
    if not words or size == 0 or stride == 0:
        return []
    if len(words) <= size:
        return [" ".join(words)]
    out: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + size, len(words))
        if end > start:
            out.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start += stride
    return out


def expand_surface(text: str) -> list[str]:
    stripped = text.strip()
    surfaces = [stripped]
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", stripped) if part.strip()]
    surfaces.extend(paragraphs)
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", stripped) if part.strip()]
    surfaces.extend(sentences)
    words = _words(stripped)
    for size, stride in ((5, 3), (10, 5), (20, 10), (40, 20)):
        surfaces.extend(_windows(words, size, stride))
    return surfaces


def is_expected_language(policy_id: str, text: str) -> bool:
    stripped = text.strip()
    words = _words(stripped)
    if len(words) < 4:
        return False
    lowered = stripped.lower()
    if any(lowered.startswith(prefix) for prefix in _REFUSAL_PREFIXES):
        return False
    if policy_id == "python":
        if _ES_FOR_EN_FORBIDDEN_RE.search(stripped):
            return False
        return bool(re.search(r"[a-zA-Z]{2,}", stripped))
    if policy_id == "receta":
        if _EN_FOR_ES_FORBIDDEN_RE.search(stripped):
            return False
        if len(words) >= 6 and not _ES_SIGNAL_RE.search(stripped):
            return False
        return True
    return True


def _collect_json_strings(obj, out: list[str]) -> None:
    if isinstance(obj, str):
        if obj.strip():
            out.append(obj.strip())
    elif isinstance(obj, list):
        for item in obj:
            _collect_json_strings(item, out)
    elif isinstance(obj, dict):
        text = obj.get("text")
        if isinstance(text, str) and text.strip():
            out.append(text.strip())
            return
        for val in obj.values():
            _collect_json_strings(val, out)


def read_corpus_file(path: Path) -> list[str]:
    if not path.is_file():
        raise FileNotFoundError(f"corpus file does not exist: {path}")
    raw = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".jsonl":
        docs: list[str] = []
        for idx, line in enumerate(raw.splitlines(), start=1):
            trimmed = line.strip()
            if not trimmed:
                continue
            if trimmed.startswith("{"):
                obj = json.loads(trimmed)
                text = obj.get("text") or obj.get("prompt")
                if not isinstance(text, str) or not text.strip():
                    raise ValueError(f"{path} line {idx} missing text/prompt")
                docs.append(text.strip())
            else:
                docs.append(trimmed)
        return docs
    trimmed = raw.strip()
    return [trimmed] if trimmed else []


def load_holdout_texts(
    policy_id: str,
    benchmark_file: Path | None = None,
    explicit_benchmark_file: bool = False,
    banks_file: Path | None = None,
    suite2_file: Path | None = None,
) -> list[str]:
    texts: list[str] = []
    if benchmark_file is not None:
        if benchmark_file.is_file():
            texts.extend(read_corpus_file(benchmark_file))
        elif explicit_benchmark_file:
            raise FileNotFoundError(f"benchmark file does not exist: {benchmark_file}")

    banks_path = REPO_ROOT / "tools/fhv1_benchmark_banks.json" if banks_file is None else banks_file
    if banks_path.is_file():
        banks = json.loads(banks_path.read_text(encoding="utf-8"))
        section = banks.get(policy_id, banks)
        _collect_json_strings(section, texts)

    suite2_path = (
        REPO_ROOT / "crates/sf-bench/src/suite2_prompts.json"
        if suite2_file is None
        else suite2_file
    )
    if suite2_path.is_file():
        suite2 = json.loads(suite2_path.read_text(encoding="utf-8"))
        for key in ("clean", "clinc_oos", "deepset_english", "es_injections", "es_oos"):
            if key in suite2:
                _collect_json_strings(suite2[key], texts)

    deduped: list[str] = []
    seen: set[str] = set()
    for text in texts:
        folded = nfkc_lower(text)
        if folded and folded not in seen:
            seen.add(folded)
            deduped.append(text)
    return deduped


def build_holdout_index(holdout_texts: list[str]) -> tuple[set[str], set[str]]:
    raw_folded: set[str] = set()
    surfaces_folded: set[str] = set()
    for text in holdout_texts:
        raw_folded.add(nfkc_lower(text))
        for surf in expand_surface(text):
            surfaces_folded.add(nfkc_lower(surf))
    return raw_folded, surfaces_folded


def overlaps_holdout(
    candidate: str,
    holdout_raw_folded: set[str],
    holdout_surfaces_folded: set[str],
) -> bool:
    folded = nfkc_lower(candidate)
    if not folded or folded in holdout_raw_folded or folded in holdout_surfaces_folded:
        return True
    for surf in expand_surface(candidate):
        sf = nfkc_lower(surf)
        if sf in holdout_raw_folded:
            return True
        if len(_words(surf)) >= 5 and sf in holdout_surfaces_folded:
            return True
    return False


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 2 and lines[-1].strip().startswith("```"):
            return "\n".join(lines[1:-1]).strip()
    return stripped


def _parse_llm_variants(raw_content: str) -> list[str]:
    cleaned = _strip_code_fence(raw_content)
    if not cleaned:
        raise ValueError("provider returned empty completion content")
    if cleaned.startswith("[") or cleaned.startswith("{"):
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ValueError(f"provider returned malformed JSON variant payload: {exc}") from exc
        if isinstance(parsed, list):
            items = [item.strip() for item in parsed if isinstance(item, str) and item.strip()]
            if not items:
                raise ValueError("provider returned empty JSON array")
            return items
        if isinstance(parsed, dict):
            for key in ("variants", "texts", "items", "passages"):
                val = parsed.get(key)
                if isinstance(val, list):
                    items = [item.strip() for item in val if isinstance(item, str) and item.strip()]
                    if items:
                        return items
            raise ValueError("provider JSON object contained no valid variant strings")
    return [cleaned]


def _llm_prompt(policy_id: str, seed_text: str, round_idx: int, batch_size: int) -> str:
    if policy_id == "receta":
        angle = _ES_ANGLES[round_idx % len(_ES_ANGLES)]
        domain_line = "Dominio: recetas de cocina y técnicas culinarias en español puro (cero palabras en inglés)."
    else:
        angle = _PY_ANGLES[round_idx % len(_PY_ANGLES)]
        domain_line = "Domain: Python software engineering, standard library, typing, asyncio, pytest, and debugging in English."
    return (
        f"{domain_line}\n"
        f"{angle}\n"
        f"Generate exactly {batch_size} genuinely distinct items inspired by—but not copying—the passage below.\n"
        f"Return ONLY a JSON array of {batch_size} strings.\n\n"
        f"Seed passage:\n{seed_text}"
    )


def augment_corpus(
    request: AugmentRequest,
    env_map: Mapping[str, str],
    out_dir: Path,
    client: httpx.Client,
) -> tuple[Path, bool]:
    config = resolve_provider(request.provider, env_map)
    digest = corpus_sha256(request.policy_id, request.texts)
    out_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path, manifest_path = cache_paths(out_dir, request.policy_id, digest)
    cached = _read_cache(jsonl_path, manifest_path, digest)
    if cached is not None:
        return jsonl_path, True
    augmented: list[str] = []
    headers = {"Content-Type": "application/json"}
    if config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"
    for text in request.texts:
        response = client.post(
            f"{config.base_url.rstrip('/')}/chat/completions",
            headers=headers,
            json={
                "model": config.model,
                "temperature": 0,
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "Rewrite the following passage once, keeping the same language "
                            f"and meaning:\n{text}"
                        ),
                    }
                ],
            },
        )
        response.raise_for_status()
        augmented.append(_completion_text(response.json()))
    body = "".join(
        json.dumps(
            {"source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(), "text": text},
            ensure_ascii=False,
        )
        + "\n"
        for source, text in zip(request.texts, augmented, strict=True)
    )
    jsonl_path.write_text(body, encoding="utf-8")
    manifest_path.write_text(
        json.dumps(
            {
                "policy_id": request.policy_id,
                "sha256": digest,
                "provider": config.provider,
                "model": config.model,
                "count": len(augmented),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return jsonl_path, False


def augment_corpus_llm(
    policy_id: str,
    provider: str,
    base_texts: list[str],
    holdout_texts: list[str],
    env_map: Mapping[str, str],
    out_dir: Path,
    client: httpx.Client,
    target_count: int = 600,
) -> tuple[Path, bool]:
    if not base_texts:
        raise ValueError("base corpus is empty")
    if target_count < 1:
        raise ValueError("target_count must be >= 1")

    # Resolve provider upfront so missing API keys fail closed before touching cache.
    config = resolve_provider(provider, env_map)
    holdout_raw_folded, holdout_surfaces_folded = build_holdout_index(holdout_texts)
    holdout_hash = corpus_sha256(f"{policy_id}:holdout", sorted(holdout_raw_folded))
    digest = corpus_sha256(
        policy_id,
        [f"augment-llm:v1:target={target_count}:holdout={holdout_hash}", *base_texts],
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path, manifest_path = cache_paths(out_dir, policy_id, digest)
    cached = _read_cache(jsonl_path, manifest_path, digest)
    if cached is not None and len(cached) >= target_count:
        if all(
            not overlaps_holdout(item, holdout_raw_folded, holdout_surfaces_folded)
            for item in cached
        ):
            return jsonl_path, True

    records: list[dict[str, str]] = []
    seen_folded: set[str] = set()
    seen_sha: set[str] = set()

    for base in base_texts:
        trimmed = base.strip()
        if not trimmed:
            continue
        folded = nfkc_lower(trimmed)
        sha = hashlib.sha256(trimmed.encode("utf-8")).hexdigest()
        if folded in seen_folded or sha in seen_sha:
            continue
        if overlaps_holdout(trimmed, holdout_raw_folded, holdout_surfaces_folded):
            continue
        seen_folded.add(folded)
        seen_sha.add(sha)
        records.append({"source_sha256": sha, "kind": "base", "text": trimmed})

    headers = {"Content-Type": "application/json"}
    if config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"

    llm_added = 0
    round_idx = 0
    consecutive_zero_yield = 0
    max_calls = max(len(base_texts) * 6, 30)

    while (len(records) < target_count or llm_added == 0) and round_idx < max_calls:
        seed = base_texts[round_idx % len(base_texts)]
        remaining = max(1, target_count - len(records))
        batch_size = min(4, max(2, remaining)) if remaining > 1 else 2
        prompt = _llm_prompt(policy_id, seed, round_idx, batch_size)
        response = client.post(
            f"{config.base_url.rstrip('/')}/chat/completions",
            headers=headers,
            json={
                "model": config.model,
                "temperature": 0,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        response.raise_for_status()
        variants = _parse_llm_variants(_completion_text(response.json()))
        seed_sha = hashlib.sha256(seed.encode("utf-8")).hexdigest()
        added_this_call = 0
        for variant in variants:
            cleaned = variant.strip()
            if not cleaned or not is_expected_language(policy_id, cleaned):
                continue
            folded = nfkc_lower(cleaned)
            sha = hashlib.sha256(cleaned.encode("utf-8")).hexdigest()
            if folded in seen_folded or sha in seen_sha:
                continue
            if overlaps_holdout(cleaned, holdout_raw_folded, holdout_surfaces_folded):
                continue
            seen_folded.add(folded)
            seen_sha.add(sha)
            records.append({"source_sha256": seed_sha, "kind": "llm_expansion", "text": cleaned})
            llm_added += 1
            added_this_call += 1
            if len(records) >= target_count and llm_added > 0:
                break
        if added_this_call == 0:
            consecutive_zero_yield += 1
            if consecutive_zero_yield >= 8:
                break
        else:
            consecutive_zero_yield = 0
        round_idx += 1

    if len(records) < target_count or llm_added == 0:
        raise RuntimeError(
            f"LLM augmentation failed closed: collected {len(records)}/{target_count} unique valid texts "
            f"(llm_added={llm_added}) for policy '{policy_id}'"
        )

    body = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records)
    jsonl_path.write_text(body, encoding="utf-8")
    manifest_path.write_text(
        json.dumps(
            {
                "policy_id": policy_id,
                "sha256": digest,
                "augmented_llm": True,
                "provider": config.provider,
                "model": config.model,
                "target_count": target_count,
                "count": len(records),
                "base_count": sum(1 for row in records if row["kind"] == "base"),
                "llm_count": llm_added,
                "holdout_overlap": 0,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return jsonl_path, False


def _redact_secrets(message: str, env_map: Mapping[str, str]) -> str:
    redacted = message
    for key, val in env_map.items():
        if key.endswith("_KEY") and val.strip():
            redacted = redacted.replace(val.strip(), "[REDACTED]")
    return redacted


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Augment an fhv1 corpus and cache the JSONL")
    parser.add_argument("--provider", choices=PROVIDER_CHOICES)
    parser.add_argument("--policy-id", required=True)
    parser.add_argument("--text", action="append", dest="texts")
    parser.add_argument("--augment-llm", action="store_true")
    parser.add_argument("--corpus-file", type=Path, default=None)
    parser.add_argument("--benchmark-file", type=Path, default=None)
    parser.add_argument("--target-count", type=int, default=600)
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--out-dir", default="data/fhv1_augmented")
    return parser


def main(argv: list[str] | None = None, client: httpx.Client | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    env_map = load_env_map(Path(args.env_file), {})
    found = detected_keys(env_map)
    if not args.provider:
        listed = ", ".join(found) if found else "(none)"
        print(f"missing --provider; detected keys: {listed}", file=sys.stderr)
        return 2

    try:
        if args.augment_llm:
            corpus_path = (
                args.corpus_file
                if args.corpus_file is not None
                else REPO_ROOT / f"crates/sf-bench/fixtures/fhv1_corpus_{args.policy_id}.jsonl"
            )
            base_texts = list(args.texts or []) + read_corpus_file(corpus_path)
            explicit_bench = args.benchmark_file is not None
            bench_path = (
                args.benchmark_file
                if args.benchmark_file is not None
                else REPO_ROOT / f"data/fhv1_benchmarks/{args.policy_id}.jsonl"
            )
            holdout_texts = load_holdout_texts(
                args.policy_id,
                benchmark_file=bench_path,
                explicit_benchmark_file=explicit_bench,
            )
            if client is not None:
                path, hit = augment_corpus_llm(
                    args.policy_id,
                    args.provider,
                    base_texts,
                    holdout_texts,
                    env_map,
                    Path(args.out_dir),
                    client,
                    target_count=args.target_count,
                )
            else:
                with httpx.Client(timeout=60.0) as owned_client:
                    path, hit = augment_corpus_llm(
                        args.policy_id,
                        args.provider,
                        base_texts,
                        holdout_texts,
                        env_map,
                        Path(args.out_dir),
                        owned_client,
                        target_count=args.target_count,
                    )
        else:
            texts = args.texts or []
            if not texts:
                print("missing --text", file=sys.stderr)
                return 2
            request = AugmentRequest(
                policy_id=args.policy_id,
                provider=args.provider,
                texts=texts,
            )
            if client is not None:
                path, hit = augment_corpus(request, env_map, Path(args.out_dir), client)
            else:
                with httpx.Client(timeout=60.0) as owned_client:
                    path, hit = augment_corpus(request, env_map, Path(args.out_dir), owned_client)
    except (ValueError, FileNotFoundError, RuntimeError, httpx.HTTPError) as exc:
        print(_redact_secrets(str(exc), env_map), file=sys.stderr)
        return 2

    print(f"cache={'hit' if hit else 'miss'} path={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
