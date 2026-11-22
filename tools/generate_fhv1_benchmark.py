#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Offline four-quadrant fhv1 benchmark generator. Remote dataset fetch is opt-in."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import unicodedata
from pathlib import Path

QUOTA = 100
CATEGORIES = (
    "IN_DOMAIN_VALID",
    "OUT_OF_DOMAIN_BENIGN",
    "HYBRID_BOUNDARY",
    "ADVERSARIAL_FUZZING",
)
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUGMENTED_DIR = REPO_ROOT / "data/fhv1_augmented"

_COOKING_CLINC_TERMS = ("mushroom", "chicken", "skillet")
_ES_OOD_COOKING_KEYS = ("astronomia", "geologia")
_ES_NON_CULINARY_DOMAINS = (
    "legal",
    "medicina",
    "astronomia",
    "finanzas",
    "filosofia",
    "musica",
    "geologia",
    "botanica",
    "arquitectura",
)


def nfkc_lower(text: str) -> str:
    return unicodedata.normalize("NFKC", text).lower()


def fetch_hf_banks() -> dict:
    if os.environ.get("FHV1_ALLOW_HF_FETCH") != "1":
        raise SystemExit(
            "fetch-hf is opt-in; vendored CLINC and deepset banks are already local"
        )
    raise SystemExit("FHV1_ALLOW_HF_FETCH does not download datasets in this build")


def _unescape_rust(text: str) -> str:
    return text.replace(r"\n", "\n").replace(r"\t", "\t").replace(r"\"", '"')


def _rust_strings(block: str) -> list[str]:
    return [_unescape_rust(item) for item in re.findall(r'"((?:\\.|[^"\\])*)"', block)]


def _read_jsonl_texts(path: Path) -> list[str]:
    if not path.is_file():
        return []
    texts: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        trimmed = line.strip()
        if not trimmed:
            continue
        if trimmed.startswith("{"):
            obj = json.loads(trimmed)
            val = obj.get("text") or obj.get("prompt")
            if isinstance(val, str) and val.strip():
                texts.append(val.strip())
        else:
            texts.append(trimmed)
    return texts


def calibration_documents(
    policy_id: str,
    augmented_dir: Path | None = None,
) -> list[str]:
    documents: list[str] = []

    corpus = (REPO_ROOT / "crates/sf-bench/src/canonical_corpus.rs").read_text(encoding="utf-8")
    marker = f'domain_id: "{policy_id}"'
    start = corpus.find(marker)
    if start >= 0:
        end = corpus.find("domain_id:", start + len(marker))
        block = corpus[start : end if end > 0 else len(corpus)]
        documents.extend(_rust_strings(block))

    extra = (REPO_ROOT / "crates/sf-bench/src/fhv1_corpus.rs").read_text(encoding="utf-8")
    const_name = "PYTHON_PARAGRAPHS" if policy_id == "python" else "RECETA_PARAGRAPHS"
    matched = re.search(rf'const {const_name}: &str = "(.*?)";', extra, flags=re.DOTALL)
    if matched:
        body = matched.group(1).replace("\\\n", "")
        documents.append(_unescape_rust(body))

    fixture_path = REPO_ROOT / f"crates/sf-bench/fixtures/fhv1_corpus_{policy_id}.jsonl"
    documents.extend(_read_jsonl_texts(fixture_path))

    aug_root = DEFAULT_AUGMENTED_DIR if augmented_dir is None else augmented_dir
    if aug_root.is_dir():
        for jsonl_file in sorted(aug_root.glob(f"{policy_id}*.jsonl")):
            documents.extend(_read_jsonl_texts(jsonl_file))

    seen: set[str] = set()
    unique: list[str] = []
    for doc in documents:
        trimmed = doc.strip()
        if trimmed and trimmed not in seen:
            seen.add(trimmed)
            unique.append(trimmed)
    return unique


def _words(text: str) -> list[str]:
    return [word for word in text.split() if word]


def _windows(words: list[str], size: int, stride: int) -> list[str]:
    if not words or size == 0 or stride == 0:
        return []
    if len(words) <= size:
        return [" ".join(words)]
    out = []
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
    surfaces = [text.strip()]
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    surfaces.extend(paragraphs)
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
    surfaces.extend(sentences)
    words = _words(text)
    for size, stride in ((5, 3), (10, 5), (20, 10), (40, 20)):
        surfaces.extend(_windows(words, size, stride))
    return surfaces


def forbidden_surfaces(
    policy_id: str,
    augmented_dir: Path | None = None,
) -> set[str]:
    banned: set[str] = set()
    for document in calibration_documents(policy_id, augmented_dir=augmented_dir):
        for surface in expand_surface(document):
            banned.add(surface)
            banned.add(nfkc_lower(surface))
    return banned


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _string_list(value) -> list[str]:
    if isinstance(value, list):
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]
    if isinstance(value, dict):
        rows: list[str] = []
        for item in value.values():
            rows.extend(_string_list(item))
        return rows
    return []


def _tagged_entries(items: list[dict]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for item in items:
        subtype = str(item["subtype"]).strip()
        text = str(item["text"]).strip()
        if subtype and text:
            out.append((subtype, text))
    return out


def _clean_clinc_oos(suite2: dict) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for text in _string_list(suite2["clinc_oos"]):
        lowered = text.lower()
        if any(term in lowered for term in _COOKING_CLINC_TERMS):
            continue
        rows.append(("ood_suite2_clinc", text))
    return rows


def _clean_es_canonical_and_oos(suite2: dict) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for domain in _ES_NON_CULINARY_DOMAINS:
        for text in _string_list(suite2["clean"].get(domain, [])):
            rows.append((f"ood_suite2_clean_{domain}", text))
    for domain, items in suite2["es_oos"].items():
        if domain in _ES_OOD_COOKING_KEYS:
            continue
        for text in _string_list(items):
            if "encimera" in text.lower() or "cuchillo" in text.lower():
                continue
            rows.append(("ood_suite2_es_oos", text))
    return rows


def _is_clean_injection(text: str) -> bool:
    lowered = text.lower().strip()
    if len(lowered.split()) < 6:
        return False
    return not lowered.startswith("generate sql code")


def source_pools(policy_id: str, suite2: dict, banks: dict) -> dict[str, list[tuple[str, str]]]:
    domain_bank = banks[policy_id]
    in_candidates = _tagged_entries(domain_bank["in_domain_valid"])

    ood_candidates = _tagged_entries(domain_bank["out_of_domain_benign"])
    if policy_id == "python":
        ood_candidates.extend(_clean_clinc_oos(suite2)[:40])
    else:
        canonical_es = _clean_es_canonical_and_oos(suite2)
        clean_es = [row for row in canonical_es if row[0].startswith("ood_suite2_clean_")][:25]
        oos_es = [row for row in canonical_es if row[0] == "ood_suite2_es_oos"][:20]
        ood_candidates.extend(clean_es)
        ood_candidates.extend(oos_es)

    hybrid_candidates = _tagged_entries(domain_bank["hybrid_boundary"])

    adv_candidates = _tagged_entries(domain_bank["adversarial_fuzzing"])
    if policy_id == "python":
        deepset = [
            ("prompt_injection_jailbreak", text)
            for text in _string_list(suite2["deepset_english"])
            if _is_clean_injection(text)
        ][:18]
        adv_candidates.extend(deepset)
    else:
        es_inj = [
            ("prompt_injection_jailbreak", text)
            for text in _string_list(suite2["es_injections"])
            if _is_clean_injection(text)
        ]
        adv_candidates.extend(es_inj)

    return {
        "IN_DOMAIN_VALID": in_candidates,
        "OUT_OF_DOMAIN_BENIGN": ood_candidates,
        "HYBRID_BOUNDARY": hybrid_candidates,
        "ADVERSARIAL_FUZZING": adv_candidates,
    }


def _accept(
    text: str,
    seen: set[str],
    banned: set[str],
    cal_raw_folded: set[str],
) -> bool:
    stripped = text.strip()
    folded = nfkc_lower(stripped)
    if not folded or stripped in banned or folded in banned or folded in seen:
        return False
    for surface in expand_surface(stripped):
        if len(_words(surface)) >= 5:
            sf = nfkc_lower(surface)
            if sf in cal_raw_folded or sf in banned:
                return False
    seen.add(folded)
    return True


def _fill(
    candidates: list[tuple[str, str]],
    seen: set[str],
    banned: set[str],
    cal_raw_folded: set[str],
    quota: int,
) -> list[tuple[str, str]]:
    chosen: list[tuple[str, str]] = []
    for subtype, raw_text in candidates:
        if len(chosen) >= quota:
            break
        text = raw_text.strip()
        if _accept(text, seen, banned, cal_raw_folded):
            chosen.append((subtype, text))
    if len(chosen) < quota:
        raise RuntimeError(
            f"unable to fill {quota} prompts without calibration overlap or duplicates (got {len(chosen)})"
        )
    return chosen


def build_dataset(
    policy_id: str,
    suite2: dict,
    banks: dict,
    augmented_dir: Path | None = None,
) -> list[dict]:
    pools = source_pools(policy_id, suite2, banks)
    banned = forbidden_surfaces(policy_id, augmented_dir=augmented_dir)
    cal_raw_folded = {
        nfkc_lower(doc) for doc in calibration_documents(policy_id, augmented_dir=augmented_dir)
    }

    seen: set[str] = set()
    grouped = {
        category: _fill(pools[category], seen, banned, cal_raw_folded, QUOTA)
        for category in CATEGORIES
    }
    rows: list[dict] = []
    for category in CATEGORIES:
        expected = category == "IN_DOMAIN_VALID"
        for index, (subtype, text) in enumerate(grouped[category], start=1):
            rows.append(
                {
                    "input_id": f"{policy_id}-{category.lower()}-{index:04d}",
                    "category": category,
                    "subtype": subtype,
                    "expected_pass": expected,
                    "text": text,
                }
            )
    return rows


def dataset_sha256(rows: list[dict]) -> str:
    payload = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def write_dataset(policy_id: str, out_dir: Path, rows: list[dict]) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = out_dir / f"{policy_id}.jsonl"
    manifest_path = out_dir / f"{policy_id}.manifest.json"
    body = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
    jsonl_path.write_text(body, encoding="utf-8")
    counts = {category: sum(row["category"] == category for row in rows) for category in CATEGORIES}
    manifest = {
        "policy_id": policy_id,
        "sha256": dataset_sha256(rows),
        "total": len(rows),
        "counts": counts,
        "fetch_hf": False,
        "min_per_quadrant": QUOTA,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return jsonl_path, manifest_path


def generate(
    policy_id: str,
    out_dir: Path,
    fetch_hf: bool,
    augmented_dir: Path | None = None,
) -> tuple[Path, Path]:
    if fetch_hf:
        fetch_hf_banks()
    suite2 = _load_json(REPO_ROOT / "crates/sf-bench/src/suite2_prompts.json")
    banks = _load_json(REPO_ROOT / "tools/fhv1_benchmark_banks.json")
    rows = build_dataset(policy_id, suite2, banks, augmented_dir=augmented_dir)
    return write_dataset(policy_id, out_dir, rows)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate an offline fhv1 benchmark JSONL")
    parser.add_argument("--policy-id", required=True, choices=("python", "receta"))
    parser.add_argument("--out-dir", default="data/fhv1_benchmarks")
    parser.add_argument("--fetch-hf", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        jsonl_path, _manifest = generate(args.policy_id, Path(args.out_dir), args.fetch_hf)
    except SystemExit as exc:
        if exc.code not in (None, 0):
            print(exc.code if isinstance(exc.code, str) else "fetch-hf refused", flush=True)
            return 2
        raise
    print(f"wrote={jsonl_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
