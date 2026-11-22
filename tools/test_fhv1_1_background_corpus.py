#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Contract, purity, diversity, and anti-leakage tests for tools/fhv1_1_background_corpus.jsonl."""

from __future__ import annotations

import json
import re
import sys
import unittest
from collections import Counter
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import generate_fhv1_benchmark as generator  # noqa: E402

CORPUS_PATH = TOOLS_DIR / "fhv1_1_background_corpus.jsonl"

EXPECTED_TOPICS: tuple[str, ...] = (
    "finance",
    "law",
    "medicine",
    "biology",
    "astronomy",
    "geology",
    "history",
    "philosophy",
    "architecture",
    "music",
    "travel_weather",
    "sports",
    "electronics_hardware",
)

PYTHON_LEAK_RE = re.compile(
    r"(?:__init__|__get__|__set__|__dict__|\bdef\s+\w+\s*\(|\bimport\s+\w+)"
    r"|\b(python|pythonic|cpython|bytecode|pip|venv|conda|pytest|asyncio|itertools|"
    r"functools|pathlib|hashlib|pickle|dataclass|dataclasses|decorator|decorators|"
    r"coroutine|coroutines|walrus|memoryview|numpy|scipy|pandas|matplotlib|django|"
    r"flask|fastapi|uvicorn|isinstance|traceback|lambda|yield|gil)\b",
    re.IGNORECASE,
)

EN_SPANISH_LEAK_RE = re.compile(
    r"[áéíóúüñ¿¡]|"
    r"\b(para|desde|hasta|después|además|también|porque|mientras|según|"
    r"sobre|entre|hacia|receta|horno|cocinar|sartén|cebolla|del|las|los|"
    r"una|uno|con|pero|más|como|por|que|era)\b",
    re.IGNORECASE,
)

ES_CULINARY_LEAK_RE = re.compile(
    r"\b(receta|recetas|cocina|cocinar|cocción|horno|hornear|horneado|sartén|"
    r"olla|cacerola|cuchillo|cuchara|cucharón|tenedor|ingrediente|ingredientes|"
    r"cebolla|ajo|aceite|manteca|mantequilla|harina|huevo|huevos|sal|pimienta|"
    r"azúcar|limón|perejil|albahaca|tomate|caldo|salsa|guiso|risotto|arroz|"
    r"pasta|fideos|masa|pan|pollo|pescado|verdura|verduras|queso|crema|leche|"
    r"vino|vinagre|hervir|hirviendo|sofreír|freír|dorar|asar|marinar|picar|"
    r"rallar|batir|amasar|tamizar|emulsionar|desglasar|gastronomía|culinario|"
    r"culinaria|restaurante|almuerzo|cena|desayuno|alimento|alimentos|comida)\b",
    re.IGNORECASE,
)

ES_ENGLISH_LEAK_RE = re.compile(
    r"\b(hardware|software|marketing|stock|jazz|rock|test|set|a|the|and|of|with|"
    r"from|for|is|in|this|that|your|you|are|was|were|have|has|had|can|could|"
    r"would|should|will|an|at|by|on|or|to|as|if|it|not|be|follow-up|unrelated|"
    r"boundary|note|request|review|ignore|quoted|marker|recipe|cooking|kitchen|"
    r"ingredients|instructions)\b",
    re.IGNORECASE,
)


def _words(text: str) -> list[str]:
    return [w for w in text.split() if w]


def _prefix_6(text: str) -> str:
    cleaned = re.sub(r"\d+", "#", re.sub(r"[^\w\s]", " ", text.lower()))
    toks = cleaned.split()
    return " ".join(toks[:6]) if len(toks) >= 6 else " ".join(toks)


def _collect_json_strings(value: Any, out: list[str]) -> None:
    if isinstance(value, str):
        stripped = value.strip()
        if stripped:
            out.append(stripped)
    elif isinstance(value, list):
        for item in value:
            _collect_json_strings(item, out)
    elif isinstance(value, dict):
        if isinstance(value.get("text"), str):
            stripped = value["text"].strip()
            if stripped:
                out.append(stripped)
            return
        for item in value.values():
            _collect_json_strings(item, out)


def _collect_reference_texts() -> list[str]:
    texts: list[str] = []

    jsonl_paths = [
        REPO_ROOT / "data/fhv1_benchmarks/python.jsonl",
        REPO_ROOT / "data/fhv1_benchmarks/receta.jsonl",
        REPO_ROOT / "crates/sf-bench/fixtures/fhv1_corpus_python.jsonl",
        REPO_ROOT / "crates/sf-bench/fixtures/fhv1_corpus_receta.jsonl",
        *sorted((REPO_ROOT / "data/fhv1_augmented").glob("*.jsonl")),
    ]
    for path in jsonl_paths:
        if not path.is_file():
            raise FileNotFoundError(f"missing reference corpus file: {path}")
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

    banks = json.loads((REPO_ROOT / "tools/fhv1_benchmark_banks.json").read_text(encoding="utf-8"))
    _collect_json_strings(banks, texts)

    suite2 = json.loads((REPO_ROOT / "crates/sf-bench/src/suite2_prompts.json").read_text(encoding="utf-8"))
    _collect_json_strings(suite2, texts)

    canonical_rs = (REPO_ROOT / "crates/sf-bench/src/canonical_corpus.rs").read_text(encoding="utf-8")
    for raw in re.findall(r'"((?:\\.|[^"\\])*)"', canonical_rs):
        val = raw.replace(r"\n", "\n").replace(r"\t", "\t").replace(r"\"", '"').strip()
        if len(val.split()) >= 4:
            texts.append(val)

    return texts


class BackgroundCorpusContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(CORPUS_PATH.is_file(), f"missing corpus file: {CORPUS_PATH}")
        lines = [line for line in CORPUS_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
        self.rows = [json.loads(line) for line in lines]

    def test_schema_counts_and_topic_balance(self) -> None:
        self.assertEqual(len(self.rows), 500, "corpus must contain exactly 500 items")
        en_rows = [r for r in self.rows if r["lang"] == "en"]
        es_rows = [r for r in self.rows if r["lang"] == "es"]
        self.assertEqual(len(en_rows), 250)
        self.assertEqual(len(es_rows), 250)

        for idx, row in enumerate(en_rows, start=1):
            self.assertEqual(set(row.keys()), {"id", "lang", "topic", "text"})
            self.assertEqual(row["id"], f"bg-en-{idx:04d}")
            self.assertIn(row["topic"], EXPECTED_TOPICS)
            self.assertTrue(row["text"].strip())
            self.assertEqual(row["text"], row["text"].strip())

        for idx, row in enumerate(es_rows, start=1):
            self.assertEqual(set(row.keys()), {"id", "lang", "topic", "text"})
            self.assertEqual(row["id"], f"bg-es-{idx:04d}")
            self.assertIn(row["topic"], EXPECTED_TOPICS)
            self.assertTrue(row["text"].strip())
            self.assertEqual(row["text"], row["text"].strip())

        for lang_label, subset in (("en", en_rows), ("es", es_rows)):
            topic_counts = Counter(r["topic"] for r in subset)
            self.assertEqual(set(topic_counts.keys()), set(EXPECTED_TOPICS))
            for topic, count in topic_counts.items():
                self.assertIn(count, (19, 20), f"{lang_label} topic {topic} count={count}")

    def test_length_diversity_matches_calibration_profile(self) -> None:
        for lang_label in ("en", "es"):
            subset = [r for r in self.rows if r["lang"] == lang_label]
            short_n = 0
            med_n = 0
            long_n = 0
            for row in subset:
                text = row["text"]
                wc = len(_words(text))
                if 5 <= wc <= 15:
                    short_n += 1
                    self.assertNotIn("\n\n", text)
                elif 20 <= wc <= 65:
                    med_n += 1
                elif 80 <= wc <= 160:
                    long_n += 1
                    paras = [p for p in text.split("\n\n") if p.strip()]
                    self.assertEqual(len(paras), 2, f"{row['id']} long doc must have 2 paragraphs")
                else:
                    self.fail(f"{row['id']} word count {wc} outside [5..15, 20..65, 80..160]")
            self.assertEqual(short_n, 50, f"{lang_label} short count")
            self.assertEqual(med_n, 140, f"{lang_label} medium count")
            self.assertEqual(long_n, 60, f"{lang_label} long count")

    def test_no_template_cloning_or_high_jaccard_duplicates(self) -> None:
        for lang_label in ("en", "es"):
            subset = [r for r in self.rows if r["lang"] == lang_label]
            prefixes = Counter(_prefix_6(r["text"]) for r in subset if len(_words(r["text"])) >= 6)
            for prefix, freq in prefixes.items():
                self.assertLess(freq, 3, f"{lang_label} repeated 6-word prefix ({freq}x): {prefix!r}")

            word_sets = [
                set(re.findall(r"[a-zA-Záéíóúüñ]+", r["text"].lower()))
                for r in subset
            ]
            for i in range(len(word_sets)):
                if len(word_sets[i]) < 5:
                    continue
                for j in range(i + 1, len(word_sets)):
                    if len(word_sets[j]) < 5:
                        continue
                    union = len(word_sets[i] | word_sets[j])
                    if union == 0:
                        continue
                    jaccard = len(word_sets[i] & word_sets[j]) / union
                    self.assertLessEqual(
                        jaccard,
                        0.72,
                        f"{lang_label} high Jaccard={jaccard:.3f}: {subset[i]['id']} vs {subset[j]['id']}",
                    )

    def test_language_purity_and_domain_exclusion(self) -> None:
        for row in self.rows:
            text = row["text"]
            if row["lang"] == "en":
                py_hits = PYTHON_LEAK_RE.findall(text)
                self.assertEqual(py_hits, [], f"{row['id']} Python leak {py_hits}: {text[:120]}")
                es_hits = EN_SPANISH_LEAK_RE.findall(text)
                self.assertEqual(es_hits, [], f"{row['id']} Spanish leak {es_hits}: {text[:120]}")
            else:
                cul_hits = ES_CULINARY_LEAK_RE.findall(text)
                self.assertEqual(cul_hits, [], f"{row['id']} culinary leak {cul_hits}: {text[:120]}")
                en_hits = ES_ENGLISH_LEAK_RE.findall(text)
                self.assertEqual(en_hits, [], f"{row['id']} English leak {en_hits}: {text[:120]}")

    def test_anti_leakage_firewall_internal_and_external(self) -> None:
        seen_raw: set[str] = set()
        seen_folded: set[str] = set()
        for row in self.rows:
            raw = row["text"].strip()
            folded = generator.nfkc_lower(raw)
            self.assertNotIn(raw, seen_raw, f"internal raw dup: {row['id']}")
            self.assertNotIn(folded, seen_folded, f"internal folded dup: {row['id']}")
            seen_raw.add(raw)
            seen_folded.add(folded)

        ref_texts = _collect_reference_texts()
        self.assertGreater(len(ref_texts), 1500)

        ref_raw: set[str] = set()
        ref_folded: set[str] = set()
        ref_surfaces_5plus: set[str] = set()
        for ref in ref_texts:
            trimmed = ref.strip()
            ref_raw.add(trimmed)
            ref_folded.add(generator.nfkc_lower(trimmed))
            for surf in generator.expand_surface(trimmed):
                if len(_words(surf)) >= 5:
                    ref_surfaces_5plus.add(generator.nfkc_lower(surf))

        for row in self.rows:
            raw = row["text"].strip()
            folded = generator.nfkc_lower(raw)
            self.assertNotIn(raw, ref_raw, f"external raw overlap: {row['id']}")
            self.assertNotIn(folded, ref_folded, f"external folded overlap: {row['id']}")
            for surf in generator.expand_surface(raw):
                if len(_words(surf)) >= 5:
                    sf = generator.nfkc_lower(surf)
                    self.assertNotIn(sf, ref_folded, f"surface overlaps ref doc: {row['id']} -> {sf!r}")
                    self.assertNotIn(
                        sf,
                        ref_surfaces_5plus,
                        f"5+ word surface overlaps ref surface: {row['id']} -> {sf!r}",
                    )


if __name__ == "__main__":
    unittest.main(verbosity=2)

