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

GENERAL_TOPICS: tuple[str, ...] = (
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

TECHNICAL_TOPICS: tuple[str, ...] = (
    "business_json_yaml",
    "server_network_logs",
    "technical_manuals",
    "tables_schemas",
    "imperative_instructions",
)

NEAR_EN_TOPICS: tuple[str, ...] = (
    "javascript_typescript",
    "rust",
    "go",
    "java",
    "cpp",
    "csharp",
    "sql",
    "bash_shell",
    "ruby",
    "docker_terraform",
)

NEAR_ES_TOPICS: tuple[str, ...] = (
    "nutricion_clinica",
    "quimica_alimentos",
    "finanzas_restaurante",
    "hornos_electricos",
    "agronomia_cosecha",
)

STRATA: tuple[str, ...] = ("general_prose", "technical_structured", "near_ood_neighbor")

# Python-specific denylist. import / yield / lambda stay legal: they occur in
# non-Python neighbor languages.
PYTHON_LEAK_RE = re.compile(
    r"__init__|\bdef\s+\w+\s*\(|"
    r"\b(?:python|pythonic|cpython|pypi|pip|venv|conda|pytest|asyncio|itertools|"
    r"functools|pathlib|hashlib|pickle|dataclass|dataclasses|numpy|scipy|pandas|"
    r"matplotlib|django|flask|fastapi|uvicorn|isinstance|traceback|gil)\b",
    re.IGNORECASE,
)

EN_SPANISH_LEAK_RE = re.compile(
    r"[áéíóúüñ¿¡]|"
    r"\b(para|desde|hasta|después|además|también|porque|mientras|según|"
    r"sobre|entre|hacia|receta|horno|cocinar|sartén|cebolla|del|las|los|"
    r"una|uno|con|pero|más|como|por|que|era)\b",
    re.IGNORECASE,
)

ES_RECIPE_RE = re.compile(r"\brecetas?\b|\brecetario\b", re.IGNORECASE)

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

BLOCK_SPECS: tuple[tuple[str, str, int], ...] = (
    ("en", "general_prose", 300),
    ("en", "technical_structured", 100),
    ("en", "near_ood_neighbor", 100),
    ("es", "general_prose", 300),
    ("es", "technical_structured", 100),
    ("es", "near_ood_neighbor", 100),
)


def _words(text: str) -> list[str]:
    return [w for w in text.split() if w]


def _norm_tokens(text: str) -> list[str]:
    return generator.nfkc_lower(text).split()


def _prefix(text: str) -> str:
    cleaned = re.sub(r"\d+", "#", re.sub(r"[^\w\s]", " ", text.lower()))
    toks = cleaned.split()
    width = min(6, len(toks))
    return " ".join(toks[:width])


def _ngrams(tokens: list[str], n: int) -> set[str]:
    if len(tokens) < n:
        return set()
    return {" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)}


def _length_band(text: str) -> str:
    wc = len(_words(text))
    if 5 <= wc <= 15:
        if "\n\n" in text:
            return "short-bad-blank"
        return "short"
    if 20 <= wc <= 65:
        return "medium"
    if 80 <= wc <= 160:
        paras = [p for p in text.split("\n\n") if p.strip()]
        if len(paras) != 2:
            return "long-bad-paras"
        return "long"
    return f"out-{wc}"


def _alpha_set(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ]+", text.lower()))


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
    @classmethod
    def setUpClass(cls) -> None:
        if not CORPUS_PATH.is_file():
            raise AssertionError(f"missing corpus file: {CORPUS_PATH}")
        lines = [line for line in CORPUS_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
        cls.rows = [json.loads(line) for line in lines]

    def _block(self, lang: str, stratum: str) -> list[dict[str, Any]]:
        return [row for row in self.rows if row["lang"] == lang and row["stratum"] == stratum]

    def test_schema_order_ids_and_exact_keys(self) -> None:
        self.assertEqual(len(self.rows), 1000)
        offset = 0
        for lang, stratum, count in BLOCK_SPECS:
            block = self.rows[offset : offset + count]
            self.assertEqual(len(block), count)
            for local_idx, row in enumerate(block, start=1):
                global_idx = local_idx if stratum == "general_prose" else (
                    300 + local_idx if stratum == "technical_structured" else 400 + local_idx
                )
                self.assertEqual(set(row.keys()), {"id", "lang", "stratum", "topic", "text"})
                self.assertEqual(row["lang"], lang)
                self.assertEqual(row["stratum"], stratum)
                self.assertEqual(row["id"], f"bg-{lang}-{global_idx:04d}")
                self.assertTrue(row["text"].strip())
                self.assertEqual(row["text"], row["text"].strip())
                self.assertIn(row["stratum"], STRATA)
            offset += count
        self.assertEqual(offset, 1000)
        langs = Counter(row["lang"] for row in self.rows)
        self.assertEqual(langs, Counter({"en": 500, "es": 500}))

    def test_general_prose_topic_quotas(self) -> None:
        for lang in ("en", "es"):
            block = self._block(lang, "general_prose")
            self.assertEqual(len(block), 300)
            counts = Counter(row["topic"] for row in block)
            self.assertEqual(set(counts), set(GENERAL_TOPICS))
            for topic, count in counts.items():
                expected = 24 if topic == "electronics_hardware" else 23
                self.assertEqual(count, expected, f"{lang} {topic}")

    def test_general_prose_length_quotas_and_per_topic_coverage(self) -> None:
        for lang in ("en", "es"):
            block = self._block(lang, "general_prose")
            bands: Counter[str] = Counter()
            per_topic: dict[str, set[str]] = {topic: set() for topic in GENERAL_TOPICS}
            for row in block:
                band = _length_band(row["text"])
                self.assertIn(band, {"short", "medium", "long"}, f"{row['id']} band {band}")
                bands[band] += 1
                per_topic[row["topic"]].add(band)
            self.assertEqual(bands["short"], 60, lang)
            self.assertEqual(bands["medium"], 180, lang)
            self.assertEqual(bands["long"], 60, lang)
            for topic, seen in per_topic.items():
                self.assertTrue({"short", "medium", "long"} <= seen, f"{lang} {topic} missing {seen}")

    def test_technical_structured_quotas_and_lengths(self) -> None:
        for lang in ("en", "es"):
            block = self._block(lang, "technical_structured")
            self.assertEqual(len(block), 100)
            counts = Counter(row["topic"] for row in block)
            self.assertEqual(dict(counts), {topic: 20 for topic in TECHNICAL_TOPICS})
            bands: Counter[str] = Counter()
            for row in block:
                band = _length_band(row["text"])
                self.assertIn(band, {"short", "medium", "long"}, f"{row['id']} band {band}")
                bands[band] += 1
            self.assertEqual(bands["short"], 20, lang)
            self.assertEqual(bands["medium"], 50, lang)
            self.assertEqual(bands["long"], 30, lang)

    def test_near_ood_english_quotas_and_lengths(self) -> None:
        block = self._block("en", "near_ood_neighbor")
        self.assertEqual(len(block), 100)
        counts = Counter(row["topic"] for row in block)
        self.assertEqual(dict(counts), {topic: 10 for topic in NEAR_EN_TOPICS})
        bands: Counter[str] = Counter()
        for row in block:
            band = _length_band(row["text"])
            self.assertIn(band, {"short", "medium", "long"}, f"{row['id']} band {band}")
            bands[band] += 1
        self.assertEqual(dict(bands), {"short": 20, "medium": 50, "long": 30})

    def test_near_ood_spanish_quotas_and_lengths(self) -> None:
        block = self._block("es", "near_ood_neighbor")
        self.assertEqual(len(block), 100)
        counts = Counter(row["topic"] for row in block)
        self.assertEqual(dict(counts), {topic: 20 for topic in NEAR_ES_TOPICS})
        bands: Counter[str] = Counter()
        for row in block:
            band = _length_band(row["text"])
            self.assertIn(band, {"short", "medium", "long"}, f"{row['id']} band {band}")
            bands[band] += 1
        self.assertEqual(dict(bands), {"short": 20, "medium": 50, "long": 30})

    def test_unique_normalized_prefixes_per_language(self) -> None:
        for lang in ("en", "es"):
            subset = [row for row in self.rows if row["lang"] == lang]
            prefixes = Counter(_prefix(row["text"]) for row in subset)
            dups = [(prefix, freq) for prefix, freq in prefixes.items() if freq != 1]
            self.assertEqual(dups, [], f"{lang} prefix collisions")

    def test_pairwise_jaccard_strictly_below_threshold(self) -> None:
        for lang in ("en", "es"):
            subset = [row for row in self.rows if row["lang"] == lang]
            word_sets = [_alpha_set(row["text"]) for row in subset]
            bad: list[str] = []
            for i in range(len(word_sets)):
                if not word_sets[i]:
                    continue
                for j in range(i + 1, len(word_sets)):
                    if not word_sets[j]:
                        continue
                    union = len(word_sets[i] | word_sets[j])
                    if union == 0:
                        continue
                    score = len(word_sets[i] & word_sets[j]) / union
                    if score >= 0.72:
                        bad.append(
                            f"{subset[i]['id']} vs {subset[j]['id']} Jaccard={score:.3f}"
                        )
                        if len(bad) >= 8:
                            break
                if len(bad) >= 8:
                    break
            self.assertEqual(bad, [], f"{lang} Jaccard")

    def test_english_rows_reject_spanish_leaks_and_python_denylist(self) -> None:
        for row in self.rows:
            if row["lang"] != "en":
                continue
            text = row["text"]
            py_hits = PYTHON_LEAK_RE.findall(text)
            self.assertEqual(py_hits, [], f"{row['id']} Python leak {py_hits}: {text[:160]}")
            es_hits = EN_SPANISH_LEAK_RE.findall(text)
            self.assertEqual(es_hits, [], f"{row['id']} Spanish leak {es_hits}: {text[:160]}")

    def test_python_denylist_allows_import_yield_and_lambda(self) -> None:
        spared = "import stream; yield item; const lambda = (v) => v;"
        self.assertEqual(PYTHON_LEAK_RE.findall(spared), [])
        self.assertIsNone(EN_SPANISH_LEAK_RE.search(spared))
        for banned in ("python", "isinstance", "gil", "__init__", "def rank(cost)", "pypi", "pytest"):
            self.assertIsNotNone(PYTHON_LEAK_RE.search(banned), banned)

    def test_spanish_rows_reject_english_leaks_and_recipe_words(self) -> None:
        for row in self.rows:
            if row["lang"] != "es":
                continue
            text = row["text"]
            en_hits = ES_ENGLISH_LEAK_RE.findall(text)
            self.assertEqual(en_hits, [], f"{row['id']} English leak {en_hits}: {text[:160]}")
            recipe_hits = ES_RECIPE_RE.findall(text)
            self.assertEqual(recipe_hits, [], f"{row['id']} recipe leak {recipe_hits}: {text[:160]}")

    def test_culinary_lexicon_applies_only_outside_near_ood_neighbor(self) -> None:
        neighbor_hits = 0
        for row in self.rows:
            if row["lang"] != "es":
                continue
            hits = ES_CULINARY_LEAK_RE.findall(row["text"])
            if row["stratum"] == "near_ood_neighbor":
                neighbor_hits += len(hits)
                continue
            self.assertIn(row["stratum"], {"general_prose", "technical_structured"})
            self.assertEqual(hits, [], f"{row['id']} culinary leak {hits}: {row['text'][:160]}")
        self.assertGreater(neighbor_hits, 0)

    def test_internal_raw_and_nfkc_uniqueness(self) -> None:
        seen_raw: set[str] = set()
        seen_folded: set[str] = set()
        for row in self.rows:
            raw = row["text"].strip()
            folded = generator.nfkc_lower(raw)
            self.assertNotIn(raw, seen_raw, f"internal raw dup: {row['id']}")
            self.assertNotIn(folded, seen_folded, f"internal folded dup: {row['id']}")
            seen_raw.add(raw)
            seen_folded.add(folded)

    def test_external_firewall_raw_nfkc_and_sliding_4_and_5_grams(self) -> None:
        ref_texts = _collect_reference_texts()
        self.assertGreater(len(ref_texts), 1500)
        ref_raw: set[str] = set()
        ref_folded: set[str] = set()
        ref_4: set[str] = set()
        ref_5: set[str] = set()
        for ref in ref_texts:
            trimmed = ref.strip()
            ref_raw.add(trimmed)
            ref_folded.add(generator.nfkc_lower(trimmed))
            tokens = _norm_tokens(trimmed)
            ref_4.update(_ngrams(tokens, 4))
            ref_5.update(_ngrams(tokens, 5))
        self.assertGreater(len(ref_4), 10000)
        self.assertGreater(len(ref_5), 10000)

        bad: list[str] = []
        for row in self.rows:
            raw = row["text"].strip()
            folded = generator.nfkc_lower(raw)
            if raw in ref_raw:
                bad.append(f"{row['id']} raw")
            if folded in ref_folded:
                bad.append(f"{row['id']} nfkc")
            tokens = _norm_tokens(raw)
            hit4 = _ngrams(tokens, 4) & ref_4
            hit5 = _ngrams(tokens, 5) & ref_5
            if hit4:
                bad.append(f"{row['id']} 4gram {next(iter(hit4))}")
            if hit5:
                bad.append(f"{row['id']} 5gram {next(iter(hit5))}")
            if len(bad) >= 12:
                break
        self.assertEqual(bad, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
