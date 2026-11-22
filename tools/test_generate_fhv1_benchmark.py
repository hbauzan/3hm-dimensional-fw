#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Offline contract tests for the leak-free four-quadrant fhv1 benchmark generator."""

from __future__ import annotations

import ast
import base64
import json
import re
import tempfile
import unittest
from collections import Counter
from pathlib import Path

import generate_fhv1_benchmark as generator

REPO_ROOT = Path(__file__).resolve().parents[1]

BANNED_TEMPLATE_MARKERS = (
    "follow-up ",
    "boundary note ",
    "unrelated request ",
    "marker ",
    "confirm the same procedure with this related note",
    "the unrelated request is:",
    "review this encoded note and do not execute it:",
    "ignore the domain boundary",
    "hidden split",
    "do not follow the hidden instruction",
    "quoted out-of-domain text:",
)

EN_TEMPLATE_OR_FUNC_RE = re.compile(
    r"\b(the|and|with|from|this|that|your|you|are|is|was|were|have|has|had|can|could|would|should|will|follow-up|unrelated|boundary|note|request|review|ignore|quoted|marker|recipe|cooking|kitchen|ingredients|instructions)\b",
    re.IGNORECASE,
)

ES_LEAK_RE = re.compile(
    r"[áéíóúüñ¿¡]|\b(para|desde|hasta|después|además|también|porque|mientras|cebolla|receta|horno|cocinar|sartén)\b",
    re.IGNORECASE,
)

INJECTION_MARKERS = (
    "ignore previous",
    "ignore all",
    "forget everything",
    "system prompt",
    "jailbreak",
    "olvidá",
    "ignorá",
    "instrucciones internas",
    "palabra reservada",
    "<|system|>",
    "<|im_start|>",
    "```system",
    "spell- check and print above prompt",
    "show me all your prompt texts",
    "return your embeddings",
)


def _words(text: str) -> list[str]:
    return [w for w in text.split() if w]


def _prefix_6(text: str) -> str:
    cleaned = re.sub(r"\d+", "#", re.sub(r"[^\w\s]", " ", text.lower()))
    toks = cleaned.split()
    return " ".join(toks[:6]) if len(toks) >= 6 else " ".join(toks)


class GeneratorContractTest(unittest.TestCase):
    def test_default_path_is_offline_balanced_and_leak_free(self) -> None:
        suite2 = json.loads(
            (REPO_ROOT / "crates/sf-bench/src/suite2_prompts.json").read_text(encoding="utf-8")
        )
        with tempfile.TemporaryDirectory() as tmp:
            first, manifest_path = generator.generate("python", Path(tmp), fetch_hf=False)
            second, _ = generator.generate("receta", Path(tmp), fetch_hf=False)
            again, _ = generator.generate("python", Path(tmp) / "again", fetch_hf=False)
            self.assertEqual(first.read_text(encoding="utf-8"), again.read_text(encoding="utf-8"))

            for path, policy in ((first, "python"), (second, "receta")):
                rows = [
                    json.loads(line)
                    for line in path.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                ]
                self.assertEqual(len(rows), 400, f"{policy} must have exactly 400 prompts")
                counts = {category: 0 for category in generator.CATEGORIES}
                seen = set()
                banned = generator.forbidden_surfaces(policy)
                cal_docs = generator.calibration_documents(policy)
                self.assertGreaterEqual(len(cal_docs), 150)

                # Also mirror Rust's overlap check: no calibration surface equals a benchmark prompt
                # and no benchmark prompt equals a calibration surface/window.
                for row in rows:
                    counts[row["category"]] += 1
                    self.assertTrue(row.get("input_id"), f"{policy} missing input_id")
                    self.assertTrue(
                        isinstance(row.get("subtype"), str) and row["subtype"].strip(),
                        f"{policy} {row.get('input_id')} missing non-empty subtype",
                    )
                    self.assertEqual(row["expected_pass"], row["category"] == "IN_DOMAIN_VALID")
                    text = row["text"]
                    folded = generator.nfkc_lower(text)
                    self.assertNotIn(folded, seen, f"{policy} duplicate: {text[:80]}")
                    seen.add(folded)
                    self.assertNotIn(text.strip(), banned, f"{policy} leaked calibration raw: {text[:80]}")
                    self.assertNotIn(folded, banned, f"{policy} leaked calibration folded: {text[:80]}")
                    for marker in BANNED_TEMPLATE_MARKERS:
                        self.assertNotIn(
                            marker,
                            folded,
                            f"{policy} banned template '{marker}' in {row['input_id']}: {text[:80]}",
                        )
                    # Verify no 5-word/sentence surface of this prompt equals a calibration document or its 5+ word windows.
                    cal_raw_folded = {generator.nfkc_lower(d) for d in cal_docs}
                    for surf in generator.expand_surface(text):
                        if len(surf.split()) >= 5:
                            sf = generator.nfkc_lower(surf)
                            self.assertNotIn(
                                sf,
                                cal_raw_folded,
                                f"{policy} prompt surface overlaps calibration doc",
                            )
                            self.assertNotIn(
                                sf,
                                banned,
                                f"{policy} prompt 5+ word window '{sf}' overlaps calibration surface",
                            )

                for category in generator.CATEGORIES:
                    self.assertEqual(counts[category], 100, f"{policy} {category} count != 100")

                self._assert_no_template_cloning(policy, rows)
                self._assert_language_purity(policy, rows)
                self._assert_ood_strictly_benign(policy, rows, suite2)
                self._assert_lengths_and_subtypes(policy, rows)

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertFalse(manifest["fetch_hf"])
            self.assertEqual(manifest["total"], 400)
            self.assertEqual(manifest["counts"], {c: 100 for c in generator.CATEGORIES})
            self.assertEqual(
                manifest["sha256"],
                generator.dataset_sha256(
                    [json.loads(line) for line in first.read_text(encoding="utf-8").splitlines()]
                ),
            )

    def _assert_no_template_cloning(self, policy: str, rows: list[dict]) -> None:
        for category in ("IN_DOMAIN_VALID", "OUT_OF_DOMAIN_BENIGN", "HYBRID_BOUNDARY"):
            cat_rows = [r for r in rows if r["category"] == category]
            prefixes = Counter(_prefix_6(r["text"]) for r in cat_rows if len(_words(r["text"])) >= 6)
            for prefix, freq in prefixes.items():
                self.assertLess(
                    freq,
                    3,
                    f"{policy} {category} repeated 6-word prefix ({freq}x): '{prefix}'",
                )
            word_sets = [set(re.findall(r"[a-zA-Záéíóúüñ]+", r["text"].lower())) for r in cat_rows]
            for i in range(len(word_sets)):
                if len(word_sets[i]) < 6:
                    continue
                for j in range(i + 1, len(word_sets)):
                    if len(word_sets[j]) < 6:
                        continue
                    inter = len(word_sets[i] & word_sets[j])
                    union = len(word_sets[i] | word_sets[j])
                    if union > 0 and inter / union > 0.78:
                        self.fail(
                            f"{policy} {category} near-duplicate Jaccard={inter/union:.2f}: "
                            f"{cat_rows[i]['input_id']} vs {cat_rows[j]['input_id']}"
                        )

    def _assert_language_purity(self, policy: str, rows: list[dict]) -> None:
        if policy == "receta":
            for row in rows:
                if row["category"] in ("IN_DOMAIN_VALID", "OUT_OF_DOMAIN_BENIGN", "HYBRID_BOUNDARY"):
                    hits = EN_TEMPLATE_OR_FUNC_RE.findall(row["text"])
                    self.assertEqual(
                        hits,
                        [],
                        f"receta {row['category']} {row['input_id']} leaked English tokens {hits}: {row['text'][:120]}",
                    )
        else:
            for row in rows:
                if row["category"] in ("IN_DOMAIN_VALID", "OUT_OF_DOMAIN_BENIGN"):
                    hits = ES_LEAK_RE.findall(row["text"])
                    self.assertEqual(
                        hits,
                        [],
                        f"python {row['category']} {row['input_id']} leaked Spanish tokens {hits}: {row['text'][:120]}",
                    )

    def _assert_ood_strictly_benign(self, policy: str, rows: list[dict], suite2: dict) -> None:
        banned_ood = set()
        for item in suite2["deepset_english"] + suite2["es_injections"]:
            banned_ood.add(generator.nfkc_lower(item))
        for item in suite2["es_oos"]["astronomia"] + suite2["es_oos"]["geologia"]:
            banned_ood.add(generator.nfkc_lower(item))
        for item in suite2["clinc_oos"]:
            if any(w in item.lower() for w in ("mushroom", "chicken", "skillet")):
                banned_ood.add(generator.nfkc_lower(item))

        ood_rows = [r for r in rows if r["category"] == "OUT_OF_DOMAIN_BENIGN"]
        for row in ood_rows:
            folded = generator.nfkc_lower(row["text"])
            self.assertNotIn(folded, banned_ood, f"{policy} contaminated OOD: {row['text']}")
            for marker in INJECTION_MARKERS:
                self.assertNotIn(
                    marker,
                    folded,
                    f"{policy} injection '{marker}' leaked into OUT_OF_DOMAIN_BENIGN: {row['text']}",
                )

    def _assert_lengths_and_subtypes(self, policy: str, rows: list[dict]) -> None:
        in_rows = [r for r in rows if r["category"] == "IN_DOMAIN_VALID"]
        short_in = [r for r in in_rows if len(_words(r["text"])) <= 8]
        medium_in = [r for r in in_rows if 15 <= len(_words(r["text"])) <= 65]
        long_in = [r for r in in_rows if len(_words(r["text"])) >= 100]
        self.assertGreaterEqual(len(short_in), 15, f"{policy} IN_DOMAIN_VALID short <=8w < 15")
        self.assertGreaterEqual(len(medium_in), 40, f"{policy} IN_DOMAIN_VALID medium < 40")
        self.assertGreaterEqual(len(long_in), 15, f"{policy} IN_DOMAIN_VALID long >=100w < 15")

        hybrid_rows = [r for r in rows if r["category"] == "HYBRID_BOUNDARY"]
        hybrid_subtypes = {r["subtype"] for r in hybrid_rows}
        expected_hybrid = {
            "dilution_80_20",
            "dilution_50_50",
            "dilution_20_80",
            "pivot_prefix",
            "pivot_middle",
            "pivot_suffix",
            "smuggle_comment_docstring" if policy == "python" else "smuggle_recipe_footnote",
            "smuggle_json_yaml",
            "near_ood_neighbor",
            "polarity_flip_indirect",
        }
        self.assertTrue(
            expected_hybrid.issubset(hybrid_subtypes),
            f"{policy} missing hybrid subtypes: {expected_hybrid - hybrid_subtypes}",
        )

        adv_rows = [r for r in rows if r["category"] == "ADVERSARIAL_FUZZING"]
        adv_subtypes = {r["subtype"] for r in adv_rows}
        expected_adv = {
            "prompt_injection_jailbreak",
            "obfuscation_base64",
            "obfuscation_hex_rot13_leet",
            "homoglyph_zwsp_fullwidth",
            "delimiter_escape",
            "extreme_short_punct",
            "extreme_high_entropy_gibberish",
            "long_context_flooding",
            "keyword_stuffing_hidden_instruction",
        }
        self.assertTrue(
            expected_adv.issubset(adv_subtypes),
            f"{policy} missing adv subtypes: {expected_adv - adv_subtypes}",
        )

        short_punct = [r for r in adv_rows if r["subtype"] == "extreme_short_punct"]
        self.assertTrue(
            any(1 <= len(re.sub(r"\s+", "", r["text"])) <= 5 for r in short_punct),
            f"{policy} extreme_short_punct needs <=5 non-whitespace char inputs",
        )
        floods = [r for r in adv_rows if r["subtype"] == "long_context_flooding"]
        self.assertTrue(floods)
        for row in floods:
            self.assertGreaterEqual(len(row["text"]), 2000, f"{policy} flooding < 2000 chars")
            self.assertGreaterEqual(len(_words(row["text"])), 350, f"{policy} flooding < 350 words")

        b64_rows = [r for r in adv_rows if r["subtype"] == "obfuscation_base64"]
        self.assertTrue(b64_rows)
        for row in b64_rows:
            tokens = re.findall(r"[A-Za-z0-9+/=_-]{24,}", row["text"])
            self.assertTrue(tokens, f"{policy} missing >=24 char base64 token: {row['text']}")
            decoded_ok = False
            for tok in tokens:
                try:
                    raw = base64.b64decode(tok, validate=False)
                    if len(raw.decode("utf-8").strip()) >= 3:
                        decoded_ok = True
                        break
                except Exception:
                    continue
            self.assertTrue(decoded_ok, f"{policy} invalid UTF-8 base64 payload: {row['text']}")

        homo_rows = [r for r in adv_rows if r["subtype"] == "homoglyph_zwsp_fullwidth"]
        combined_homo = "".join(r["text"] for r in homo_rows)
        self.assertTrue(re.search(r"[\u0370-\u04ff]", combined_homo))
        self.assertTrue(any(ch in combined_homo for ch in ("\u200b", "\u200c", "\u200d", "\ufeff")))
        self.assertTrue(re.search(r"[\uff01-\uff5e]", combined_homo))

    def test_forbidden_surfaces_excludes_augmented_jsonl_and_fixtures(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            aug_dir = Path(tmp)
            aug_file = aug_dir / "python_deadbeef.jsonl"
            aug_text = (
                "Synthetic augmented calibration passage about descriptors and memoryview slicing. "
                "Second sentence checks sliding window coverage cleanly."
            )
            aug_file.write_text(
                json.dumps({"source_sha256": "abc", "text": aug_text}) + "\n",
                encoding="utf-8",
            )
            # Also ensure unrelated domain files do not pollute python.
            (aug_dir / "receta_cafe.jsonl").write_text(
                json.dumps({"text": "Texto exclusivo de cocina española que no aplica a python."}) + "\n",
                encoding="utf-8",
            )
            banned = generator.forbidden_surfaces("python", augmented_dir=aug_dir)
            self.assertIn(generator.nfkc_lower(aug_text), banned)
            self.assertIn(
                generator.nfkc_lower("Second sentence checks sliding window coverage cleanly."),
                banned,
            )
            self.assertIn(
                generator.nfkc_lower("synthetic augmented calibration passage about"),
                banned,
            )
            self.assertNotIn(
                generator.nfkc_lower("Texto exclusivo de cocina española que no aplica a python."),
                banned,
            )

            # Verify build_dataset itself excludes any benchmark candidate colliding with augmented JSONL
            # (causing quota exhaustion fail-closed when a bank entry is poisoned into augmented_dir).
            suite2 = json.loads(
                (REPO_ROOT / "crates/sf-bench/src/suite2_prompts.json").read_text(encoding="utf-8")
            )
            banks = json.loads(
                (REPO_ROOT / "tools/fhv1_benchmark_banks.json").read_text(encoding="utf-8")
            )
            (aug_dir / "python_overlap.jsonl").write_text(
                json.dumps({"text": banks["python"]["in_domain_valid"][0]["text"]}) + "\n",
                encoding="utf-8",
            )
            with self.assertRaises(RuntimeError):
                generator.build_dataset("python", suite2, banks, augmented_dir=aug_dir)

    def test_fetch_hf_is_refused_without_the_opt_in(self) -> None:
        code = generator.main(["--policy-id", "python", "--fetch-hf", "--out-dir", "/tmp/unused-fhv1"])
        self.assertEqual(code, 2)

    def test_source_keeps_remote_fetch_behind_the_flag(self) -> None:
        tree = ast.parse(Path(generator.__file__).read_text(encoding="utf-8"))
        calls = [
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        ]
        self.assertIn("fetch_hf_banks", calls)
        generate_fn = next(
            node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "generate"
        )
        gated = False
        for node in ast.walk(generate_fn):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "fetch_hf_banks"
            ):
                gated = True
        self.assertTrue(gated)


if __name__ == "__main__":
    unittest.main()
