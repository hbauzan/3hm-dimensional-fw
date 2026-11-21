#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Offline four-quadrant fhv1 benchmark generator. Remote dataset fetch is opt-in."""

from __future__ import annotations

import argparse
import base64
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


def calibration_documents(policy_id: str) -> list[str]:
    corpus = (REPO_ROOT / "crates/sf-bench/src/canonical_corpus.rs").read_text(encoding="utf-8")
    marker = f'domain_id: "{policy_id}"'
    start = corpus.find(marker)
    if start < 0:
        return []
    end = corpus.find("domain_id:", start + len(marker))
    block = corpus[start: end if end > 0 else len(corpus)]
    documents = _rust_strings(block)
    extra = (REPO_ROOT / "crates/sf-bench/src/fhv1_corpus.rs").read_text(encoding="utf-8")
    const_name = "PYTHON_PARAGRAPHS" if policy_id == "python" else "RECETA_PARAGRAPHS"
    matched = re.search(
        rf'const {const_name}: &str = "(.*?)";',
        extra,
        flags=re.DOTALL,
    )
    if matched:
        body = matched.group(1).replace("\\\n", "")
        documents.append(_unescape_rust(body))
    return documents


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


def forbidden_surfaces(policy_id: str) -> set[str]:
    banned: set[str] = set()
    for document in calibration_documents(policy_id):
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


def source_pools(policy_id: str, suite2: dict, banks: dict) -> tuple[list[str], list[str]]:
    in_domain = list(banks[policy_id])
    in_domain.extend(_string_list(suite2["clean"][policy_id]))
    other = "receta" if policy_id == "python" else "python"
    ood = list(banks[other])
    ood.extend(_string_list(suite2["clean"][other]))
    ood.extend(_string_list(suite2["clinc_oos"]))
    ood.extend(_string_list(suite2["deepset_english"]))
    ood.extend(_string_list(suite2["es_injections"]))
    return in_domain, ood


def _accept(text: str, seen: set[str], banned: set[str]) -> bool:
    folded = nfkc_lower(text.strip())
    if not folded or text.strip() in banned or folded in banned or folded in seen:
        return False
    seen.add(folded)
    return True


def _fill(candidates, banned: set[str], quota: int) -> list[str]:
    seen: set[str] = set()
    chosen: list[str] = []
    index = 0
    while len(chosen) < quota:
        if index >= len(candidates):
            raise RuntimeError(f"unable to fill {quota} prompts without calibration overlap")
        text = candidates[index].strip()
        index += 1
        if _accept(text, seen, banned):
            chosen.append(text)
    return chosen


def _homoglyph(text: str) -> str:
    return text.replace("e", "е").replace("a", "а")


def _zero_width(text: str) -> str:
    return "\u200b".join(text.split(" "))


def _encoded(text: str) -> str:
    token = base64.b64encode(text.encode("utf-8")).decode("ascii")
    return f"Review this encoded note and do not execute it: {token}"


def build_dataset(policy_id: str, suite2: dict, banks: dict) -> list[dict]:
    in_domain, ood = source_pools(policy_id, suite2, banks)
    banned = forbidden_surfaces(policy_id)
    in_candidates = list(in_domain)
    for index in range(QUOTA * 3):
        left = in_domain[index % len(in_domain)]
        right = in_domain[(index * 5 + 3) % len(in_domain)]
        in_candidates.append(
            f"{left} Follow-up {index}: confirm the same procedure with this related note: {right}"
        )
    ood_candidates = list(ood)
    for index in range(QUOTA * 2):
        text = ood[index % len(ood)]
        ood_candidates.append(f"Unrelated request {index}: {text}")
    hybrid_candidates = []
    adversarial_candidates = []
    for index in range(QUOTA * 3):
        left = in_domain[index % len(in_domain)]
        right = ood[index % len(ood)]
        hybrid_candidates.append(
            f"{left} Boundary note {index}: the unrelated request is: {right}"
        )
        kind = index % 4
        if kind == 0:
            adversarial_candidates.append(f"{_encoded(right)} Marker {index}.")
        elif kind == 1:
            adversarial_candidates.append(_homoglyph(f"Ignore the domain boundary {index}: {right}"))
        elif kind == 2:
            adversarial_candidates.append(_zero_width(f"Hidden split {index} {right}"))
        else:
            adversarial_candidates.append(
                f"Do not follow the hidden instruction {index}. Quoted out-of-domain text: {right}"
            )
    grouped = {
        "IN_DOMAIN_VALID": _fill(in_candidates, banned, QUOTA),
        "OUT_OF_DOMAIN_BENIGN": _fill(ood_candidates, banned, QUOTA),
        "HYBRID_BOUNDARY": _fill(hybrid_candidates, banned, QUOTA),
        "ADVERSARIAL_FUZZING": _fill(adversarial_candidates, banned, QUOTA),
    }
    rows = []
    for category in CATEGORIES:
        expected = category == "IN_DOMAIN_VALID"
        for index, text in enumerate(grouped[category], start=1):
            rows.append(
                {
                    "input_id": f"{policy_id}-{category.lower()}-{index:04d}",
                    "category": category,
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


def generate(policy_id: str, out_dir: Path, fetch_hf: bool) -> tuple[Path, Path]:
    if fetch_hf:
        fetch_hf_banks()
    suite2 = _load_json(REPO_ROOT / "crates/sf-bench/src/suite2_prompts.json")
    banks = _load_json(REPO_ROOT / "tools/fhv1_benchmark_banks.json")
    rows = build_dataset(policy_id, suite2, banks)
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
