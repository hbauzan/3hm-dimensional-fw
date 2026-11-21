#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "httpx>=0.27.0",
#     "pydantic>=2.9.0",
# ]
# ///
"""Offline corpus augmentation cache. The provider flag is mandatory."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Mapping

import httpx
from pydantic import BaseModel, Field

PROVIDERS = ("gemini", "openai", "deepseek", "groq", "ollama")

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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Augment an fhv1 corpus and cache the JSONL")
    parser.add_argument("--provider", choices=PROVIDERS)
    parser.add_argument("--policy-id", required=True)
    parser.add_argument("--text", action="append", dest="texts")
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--out-dir", default="data/fhv1_augmented")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    env_map = load_env_map(Path(args.env_file), {})
    found = detected_keys(env_map)
    if not args.provider:
        listed = ", ".join(found) if found else "(none)"
        print(f"missing --provider; detected keys: {listed}", file=sys.stderr)
        return 2
    texts = args.texts or []
    if not texts:
        print("missing --text", file=sys.stderr)
        return 2
    request = AugmentRequest(policy_id=args.policy_id, provider=args.provider, texts=texts)
    with httpx.Client(timeout=60.0) as client:
        path, hit = augment_corpus(request, env_map, Path(args.out_dir), client)
    print(f"cache={'hit' if hit else 'miss'} path={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
