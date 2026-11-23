#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Behavior tests for the auto-calibrated structural guardrail.

Fixtures set document frequency. A story about which marks are common loses
when the fitted counts disagree.
"""

from __future__ import annotations

import ast
import inspect
import math
import sys
import unicodedata
import unittest
from pathlib import Path
from unittest.mock import patch

import fhv1_1_lexical_profile as lex

_HARINA = "harina"
_HARINA_SORTED = sorted(_HARINA)
_HARINA_ANAGRAMS = ("harina", "ranhai", "ahrina", "hanira")
_PROBE_WORD = "hirana"

_CEBOLLA = "cebolla"
_CLAUSE_ANAGRAMS = ("cebolla", "bocella", "lleboca")
_CLAUSE_PROBE_WORD = "abcello"

_CODE = (
    "fn apply(item) { return item => item.value && item.ready; } "
    "use crate::path::item; let flag = left && right;"
)
_CODE_PROBE = _CODE.replace("value", "evula", 1)

_SMUGGLE = (
    '{"rows":[{"id":"x"},{"id":"z"}],"ok":true} '
    "item => item; crate::path && flag;"
)

_STUFFING = (
    "tomate zanahoria papa cebolla ajo pimiento calabacin berenjena "
    "zapallo choclo arroz fideo lenteja garbanzo poroto quinoa"
)

_EN_PROSE = (
    "the receta is on the table and the cook is in the kitchen with a spoon"
)
_ES_PROSE = (
    "el uso de python en la clase es para una tarea y la guia de la casa"
)


def _recipe(word: str = _HARINA) -> str:
    if sorted(word) != _HARINA_SORTED:
        raise AssertionError("recipe anagram changed the character multiset")
    return (
        f"Mezcla 1/4 de taza de {word} con 2g de sal, y hornea la masa en el horno. "
        "La sopa lleva una papa, el ajo y la cebolla para el caldo. "
        "Sirve con pan, y prueba la mezcla?"
    )


def _clause(word: str = _CEBOLLA) -> str:
    if sorted(word) != sorted(_CEBOLLA):
        raise AssertionError("clause anagram changed the character multiset")
    return f"La sopa lleva una papa, el ajo y la {word} para el caldo."


def _recipe_corpus() -> list[str]:
    return [_recipe(word) for word in _HARINA_ANAGRAMS for _ in range(10)]


def _assert_finite(test: unittest.TestCase, scored: lex.StructuralScore) -> None:
    test.assertIsInstance(scored.s_struct, float)
    test.assertTrue(math.isfinite(scored.s_struct))
    test.assertFalse(math.isnan(scored.s_struct))
    test.assertFalse(math.isinf(scored.s_struct))
    test.assertGreater(scored.s_struct, 0.0)
    test.assertLessEqual(scored.s_struct, 1.0)
    for name, value in scored.features.items():
        test.assertIsInstance(value, float, name)
        test.assertTrue(math.isfinite(value), name)
        test.assertFalse(math.isnan(value), name)
        test.assertFalse(math.isinf(value), name)
    for name, value in scored.excesses.items():
        test.assertTrue(math.isfinite(value), name)
        test.assertGreaterEqual(value, 0.0, name)
    test.assertTrue(math.isfinite(scored.missing_connector_penalty))
    test.assertGreaterEqual(scored.missing_connector_penalty, 0.0)


class LexicalProfileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.profile = lex.fit(_recipe_corpus(), granularity="full_doc")
        self.probe = _recipe(_PROBE_WORD)

    def test_float64_runtime(self) -> None:
        self.assertEqual(sys.float_info.mant_dig, 53)
        scored = lex.score(self.probe, self.profile)
        self.assertIsInstance(scored.s_struct, float)

    def test_module_imports_are_stdlib_only_and_do_not_touch_disk_stores(self) -> None:
        source = Path(lex.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        allowed = {
            "__future__",
            "math",
            "time",
            "unicodedata",
            "collections",
            "dataclasses",
            "types",
            "typing",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertIn(alias.name.split(".")[0], allowed)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                self.assertIn(node.module.split(".")[0], allowed)
        folded = source.casefold()
        for token in ("lancedb", ".parquet", "sf-lancedb", "huggingface", "dotenv"):
            self.assertNotIn(token, folded)
        self.assertNotIn("data/", source)
        body_lines: list[str] = []
        in_header = False
        for line in source.splitlines():
            if line.startswith("# ///"):
                in_header = not in_header
                continue
            if in_header:
                continue
            body_lines.append(line)
        body = "\n".join(body_lines).casefold()
        self.assertNotIn("receta", body)
        self.assertNotIn("python", body)
        signature = inspect.signature(lex.fit)
        self.assertIn("calibration_texts", signature.parameters)
        self.assertIn("granularity", signature.parameters)
        self.assertNotIn("domain", signature.parameters)
        self.assertNotIn("lang", signature.parameters)

    def test_fit_does_not_open_files(self) -> None:
        texts = _recipe_corpus()

        def _refuse_open(*_args: object, **_kwargs: object) -> None:
            raise AssertionError("fit opened a file")

        with patch("builtins.open", _refuse_open):
            profile = lex.fit(texts)
        self.assertEqual(profile.n_docs, len(texts))

    def test_fit_snapshots_supplied_texts_only_zero_leakage(self) -> None:
        texts = _recipe_corpus()
        outsider = "{ not fitted }"
        profile = lex.fit(list(texts))
        outsider = outsider + "{}" * 30
        texts.append("{}" * 10)
        texts[0] = texts[0] + "{"
        self.assertEqual(profile.n_docs, 40)
        self.assertEqual(profile.char_df.get("{", 0.0), 0.0)
        self.assertEqual(profile.char_doc_count.get("{", 0), 0)
        leaked = lex.fit(texts)
        self.assertGreater(leaked.char_df.get("{", 0.0), 0.0)
        self.assertEqual(profile.char_df.get("{", 0.0), 0.0)
        self.assertIn("{", outsider)
        braced = lex.score("{", profile)
        self.assertEqual(braced.features["rare_nonletter_char_rate"], 1.0)

    def test_connector_sets_match_the_closed_lists(self) -> None:
        self.assertEqual(
            lex.EN_CONNECTORS,
            frozenset(
                (
                    "the",
                    "of",
                    "to",
                    "and",
                    "in",
                    "a",
                    "an",
                    "for",
                    "is",
                    "on",
                    "with",
                    "that",
                    "as",
                    "by",
                    "from",
                    "or",
                    "at",
                    "this",
                    "it",
                    "be",
                    "are",
                    "was",
                    "if",
                    "not",
                )
            ),
        )
        self.assertEqual(
            lex.ES_CONNECTORS,
            frozenset(
                (
                    "de",
                    "la",
                    "el",
                    "y",
                    "en",
                    "con",
                    "para",
                    "un",
                    "una",
                    "los",
                    "las",
                    "del",
                    "al",
                    "por",
                    "que",
                    "se",
                    "es",
                    "su",
                    "como",
                    "más",
                    "o",
                    "pero",
                    "sin",
                    "sobre",
                )
            ),
        )
        self.assertTrue(lex.EN_CONNECTORS.isdisjoint(lex.ES_CONNECTORS))

    def test_detects_english_from_connector_totals(self) -> None:
        profile = lex.fit([_EN_PROSE] * 12)
        self.assertEqual(profile.primary_language, "en")
        self.assertGreater(profile.en_connector_total, profile.es_connector_total)
        self.assertGreater(profile.en_connector_total, 0)

    def test_detects_spanish_from_connector_totals(self) -> None:
        profile = lex.fit([_ES_PROSE] * 12)
        self.assertEqual(profile.primary_language, "es")
        self.assertGreater(profile.es_connector_total, profile.en_connector_total)
        self.assertEqual(profile.en_connector_total, 0)

    def test_domain_words_do_not_select_language(self) -> None:
        spanish = lex.fit([_ES_PROSE] * 8)
        english = lex.fit([_EN_PROSE] * 8)
        self.assertEqual(spanish.primary_language, "es")
        self.assertEqual(english.primary_language, "en")
        self.assertIn("python", _ES_PROSE)
        self.assertIn("receta", _EN_PROSE)

    def test_recipe_fit_common_marks_and_absent_braces(self) -> None:
        self.assertEqual(self.profile.primary_language, "es")
        for mark in ("1", "/", "4", "2", "?", ","):
            self.assertGreaterEqual(self.profile.char_df[mark], 0.01, mark)
            self.assertFalse(
                self.profile.char_doc_count[mark] * 100 < self.profile.n_docs,
                mark,
            )
        for bigram in ("1/", "/4"):
            self.assertGreaterEqual(self.profile.bigram_df[bigram], 0.01, bigram)
        for mark in ("{", "}", ";", "=", ">", "&", ":"):
            self.assertEqual(self.profile.char_df.get(mark, 0.0), 0.0, mark)
        for bigram in ("=>", "::", "&&"):
            self.assertEqual(self.profile.bigram_df.get(bigram, 0.0), 0.0, bigram)

    def test_benign_recipe_fragment_scores_exactly_one(self) -> None:
        self.assertIn("1/4", self.probe)
        self.assertIn("2g", self.probe)
        self.assertIn("?", self.probe)
        self.assertNotIn(self.probe, _recipe_corpus())
        scored = lex.score(self.probe, self.profile)
        self.assertEqual(scored.features["rare_nonletter_char_rate"], 0.0)
        self.assertEqual(scored.features["rare_nonletter_bigram_rate"], 0.0)
        self.assertEqual(scored.top_triggered_features, ())
        self.assertEqual(scored.s_struct, 1.0)

    def test_all_calibration_texts_score_exactly_one(self) -> None:
        for name in lex.SCORED_CHANNELS:
            envelope = self.profile.envelopes[name]
            self.assertEqual(envelope.p01, envelope.p99, name)
            self.assertEqual(envelope.robust_scale, lex.ROBUST_SCALE_FLOOR, name)
            self.assertGreater(envelope.robust_scale, 0.0)
        for text in _recipe_corpus():
            scored = lex.score(text, self.profile)
            self.assertEqual(scored.s_struct, 1.0)
            self.assertEqual(scored.top_triggered_features, ())
            self.assertEqual(scored.missing_connector_penalty, 0.0)

    def test_code_json_delimiter_smuggling_fires_strongly(self) -> None:
        scored = lex.score(_SMUGGLE, self.profile)
        self.assertLess(scored.s_struct, 0.05)
        self.assertGreaterEqual(len(scored.top_triggered_features), 4)
        self.assertGreater(scored.features["rare_nonletter_char_rate"], 0.0)
        self.assertGreater(scored.features["rare_nonletter_bigram_rate"], 0.0)
        self.assertGreater(scored.missing_connector_penalty, 0.0)

    def test_question_run_fires(self) -> None:
        scored = lex.score("???", self.profile)
        self.assertEqual(scored.features["max_repeated_punct_run"], 3.0)
        self.assertEqual(scored.features["letter_ratio"], 0.0)
        self.assertGreater(scored.excesses["max_repeated_punct_run"], 0.0)
        self.assertLess(scored.s_struct, 1.0)
        names = {item.name for item in scored.top_triggered_features}
        self.assertIn("max_repeated_punct_run", names)

    def test_exclamation_run_fires(self) -> None:
        scored = lex.score("!!!", self.profile)
        self.assertEqual(scored.features["max_repeated_punct_run"], 3.0)
        self.assertEqual(self.profile.char_df.get("!", 0.0), 0.0)
        self.assertEqual(scored.features["rare_nonletter_char_rate"], 1.0)
        self.assertGreater(scored.excesses["max_repeated_punct_run"], 0.0)
        self.assertLess(scored.s_struct, 1.0)

    def test_zero_letter_string_fires(self) -> None:
        scored = lex.score("000111222", self.profile)
        self.assertEqual(scored.features["letter_ratio"], 0.0)
        self.assertEqual(scored.features[lex.ALPHA_WORD_COUNT], 0.0)
        self.assertGreater(scored.excesses["letter_ratio"], 0.0)
        self.assertLess(scored.s_struct, 1.0)

    def test_cyrillic_fires_on_raw_string(self) -> None:
        raw = self.probe.replace("a", "\u0430", 1)
        self.assertNotEqual(unicodedata.normalize("NFKC", raw), self.probe)
        self.assertIn("\u0430", raw)
        scored = lex.score(raw, self.profile)
        self.assertGreater(scored.features["non_latin_or_control_unicode_ratio"], 0.0)
        self.assertGreater(scored.features["symbol_ratio"], 0.0)
        self.assertGreater(scored.excesses["non_latin_or_control_unicode_ratio"], 0.0)
        self.assertLess(scored.s_struct, 1.0)
        self.assertEqual(lex.score(self.probe, self.profile).s_struct, 1.0)

    def test_zwsp_fires_on_raw_string(self) -> None:
        raw = self.probe[:12] + "\u200b" + self.probe[12:]
        self.assertEqual(unicodedata.category("\u200b"), "Cf")
        self.assertIn("\u200b", raw)
        self.assertEqual(unicodedata.normalize("NFKC", raw), raw)
        scored = lex.score(raw, self.profile)
        self.assertGreater(scored.features["non_latin_or_control_unicode_ratio"], 0.0)
        self.assertGreater(scored.features["rare_nonletter_char_rate"], 0.0)
        self.assertGreater(scored.features["symbol_ratio"], 0.0)
        self.assertLess(scored.s_struct, 1.0)

    def test_fullwidth_fires_on_raw_string_when_nfkc_would_hide_it(self) -> None:
        raw = self.probe.replace("a", "\uff41", 1)
        folded = unicodedata.normalize("NFKC", raw)
        self.assertEqual(folded, self.probe)
        self.assertNotEqual(raw, self.probe)
        raw_score = lex.score(raw, self.profile)
        folded_score = lex.score(folded, self.profile)
        self.assertEqual(folded_score.s_struct, 1.0)
        self.assertGreater(
            raw_score.features["non_latin_or_control_unicode_ratio"], 0.0
        )
        self.assertGreater(raw_score.excesses["non_latin_or_control_unicode_ratio"], 0.0)
        self.assertLess(raw_score.s_struct, 1.0)

    def test_short_query_takes_no_missing_connector_penalty(self) -> None:
        short = "papa horno caldo"
        scored = lex.score(short, self.profile)
        envelope = self.profile.envelopes["target_connector_ratio"]
        self.assertLess(scored.features[lex.ALPHA_WORD_COUNT], 6.0)
        self.assertGreater(envelope.p01, 0.0)
        self.assertLess(scored.features["target_connector_ratio"], envelope.p01)
        self.assertEqual(scored.missing_connector_penalty, 0.0)
        self.assertEqual(scored.excesses["target_connector_ratio"], 0.0)
        names = {item.name for item in scored.top_triggered_features}
        self.assertNotIn("target_connector_ratio", names)

        five = "tomate zanahoria papa cebolla ajo"
        five_score = lex.score(five, self.profile)
        self.assertEqual(five_score.features[lex.ALPHA_WORD_COUNT], 5.0)
        self.assertEqual(five_score.missing_connector_penalty, 0.0)

        six = "tomate zanahoria papa cebolla ajo pimiento"
        six_score = lex.score(six, self.profile)
        self.assertEqual(six_score.features[lex.ALPHA_WORD_COUNT], 6.0)
        self.assertGreater(six_score.missing_connector_penalty, 0.0)
        self.assertLess(six_score.s_struct, 1.0)

    def test_short_text_still_scores_other_channels(self) -> None:
        scored = lex.score("papa horno ???", self.profile)
        self.assertLess(scored.features[lex.ALPHA_WORD_COUNT], 6.0)
        for name in (
            "letter_ratio",
            "punct_ratio",
            "max_repeated_punct_run",
            "non_latin_or_control_unicode_ratio",
            "rare_nonletter_char_rate",
            "foreign_connector_ratio",
        ):
            self.assertIn(name, scored.features)
            self.assertTrue(math.isfinite(scored.features[name]), name)
        self.assertEqual(scored.missing_connector_penalty, 0.0)
        self.assertGreater(scored.excesses["max_repeated_punct_run"], 0.0)
        self.assertLess(scored.s_struct, 1.0)

        foreign = lex.score("with the and", self.profile)
        self.assertLess(foreign.features[lex.ALPHA_WORD_COUNT], 6.0)
        self.assertEqual(foreign.features[lex.ALPHA_WORD_COUNT], 3.0)
        self.assertEqual(foreign.missing_connector_penalty, 0.0)
        self.assertEqual(foreign.features["foreign_connector_ratio"], 1.0)
        self.assertGreater(foreign.excesses["foreign_connector_ratio"], 0.0)

    def test_long_keyword_stuffing_without_connectors_fires(self) -> None:
        scored = lex.score(_STUFFING, self.profile)
        self.assertGreaterEqual(scored.features[lex.ALPHA_WORD_COUNT], 6.0)
        self.assertEqual(scored.features["target_connector_ratio"], 0.0)
        self.assertGreater(scored.missing_connector_penalty, 0.0)
        self.assertGreater(scored.excesses["target_connector_ratio"], 0.0)
        names = {item.name for item in scored.top_triggered_features}
        self.assertIn("target_connector_ratio", names)
        self.assertLess(scored.s_struct, 1.0)

    def test_english_run_in_spanish_fit_raises_foreign_connector_ratio(self) -> None:
        clean = lex.score(self.probe, self.profile)
        dirty = lex.score(
            self.probe + " with the salt and the oil for a sauce",
            self.profile,
        )
        self.assertEqual(clean.features["foreign_connector_ratio"], 0.0)
        self.assertGreater(
            dirty.features["foreign_connector_ratio"],
            clean.features["foreign_connector_ratio"],
        )
        self.assertGreater(dirty.excesses["foreign_connector_ratio"], 0.0)

    def test_operators_fire_when_rare_in_fit(self) -> None:
        self.assertIn("=>", _CODE)
        self.assertIn("::", _CODE)
        self.assertIn("&&", _CODE)
        for bigram in ("=>", "::", "&&"):
            self.assertLess(
                self.profile.bigram_doc_count.get(bigram, 0) * 100,
                self.profile.n_docs,
            )
        scored = lex.score(_CODE, self.profile)
        self.assertGreater(scored.features["rare_nonletter_char_rate"], 0.0)
        self.assertGreater(scored.features["rare_nonletter_bigram_rate"], 0.0)
        self.assertGreater(scored.excesses["rare_nonletter_bigram_rate"], 0.0)
        self.assertLess(scored.s_struct, 1.0)

    def test_code_fit_common_operators_and_absent_fraction_marks(self) -> None:
        profile = lex.fit([_CODE] * 24, granularity="full_doc")
        for mark in ("{", "}", "=", ">", ":", "&"):
            self.assertGreaterEqual(profile.char_df[mark], 0.01, mark)
        for bigram in ("=>", "::", "&&"):
            self.assertGreaterEqual(profile.bigram_df[bigram], 0.01, bigram)
            self.assertFalse(profile.bigram_doc_count[bigram] * 100 < profile.n_docs)
        for mark in ("/", "?", ",", "1", "4"):
            self.assertEqual(profile.char_df.get(mark, 0.0), 0.0, mark)
        fraction = lex.score("1/4", profile)
        self.assertEqual(fraction.features["rare_nonletter_char_rate"], 1.0)
        self.assertEqual(fraction.features["rare_nonletter_bigram_rate"], 1.0)

    def test_operators_stay_quiet_when_common_in_fit(self) -> None:
        profile = lex.fit([_CODE] * 24, granularity="full_doc")
        self.assertNotEqual(_CODE_PROBE, _CODE)
        scored = lex.score(_CODE_PROBE, profile)
        self.assertIn("=>", _CODE_PROBE)
        self.assertIn("::", _CODE_PROBE)
        self.assertIn("&&", _CODE_PROBE)
        self.assertEqual(scored.features["rare_nonletter_char_rate"], 0.0)
        self.assertEqual(scored.features["rare_nonletter_bigram_rate"], 0.0)
        self.assertEqual(scored.top_triggered_features, ())
        self.assertEqual(scored.s_struct, 1.0)

    def test_mark_at_one_percent_contributes_zero_surprise(self) -> None:
        docs = [_recipe() for _ in range(99)]
        docs.append(_recipe() + " {")
        profile = lex.fit(docs)
        self.assertEqual(profile.n_docs, 100)
        self.assertEqual(profile.char_doc_count["{"], 1)
        self.assertEqual(profile.char_df["{"], 0.01)
        self.assertFalse(profile.char_doc_count["{"] * 100 < profile.n_docs)
        scored = lex.score("{", profile)
        self.assertEqual(scored.features["rare_nonletter_char_rate"], 0.0)

    def test_mark_below_one_percent_contributes_surprise(self) -> None:
        docs = [_recipe() for _ in range(199)]
        docs.append(_recipe() + " {")
        profile = lex.fit(docs)
        self.assertEqual(profile.n_docs, 200)
        self.assertEqual(profile.char_doc_count["{"], 1)
        self.assertLess(profile.char_df["{"], 0.01)
        self.assertLess(profile.char_doc_count["{"] * 100, profile.n_docs)
        scored = lex.score("{", profile)
        self.assertEqual(scored.features["rare_nonletter_char_rate"], 1.0)
        self.assertGreater(scored.excesses["rare_nonletter_char_rate"], 0.0)

    def test_empirical_df_overrides_brace_story(self) -> None:
        profile = lex.fit([_recipe() + " {" for _ in range(40)])
        self.assertGreaterEqual(profile.char_df["{"], 0.01)
        quiet = lex.score("{", profile)
        self.assertEqual(quiet.features["rare_nonletter_char_rate"], 0.0)
        absent = lex.score("|", profile)
        self.assertEqual(profile.char_df.get("|", 0.0), 0.0)
        self.assertEqual(absent.features["rare_nonletter_char_rate"], 1.0)

    def test_single_rare_bigram_scores_higher_than_many(self) -> None:
        one = lex.score(self.probe + " =>", self.profile)
        many = lex.score(self.probe + (" =>" * 12), self.profile)
        self.assertGreater(one.features["rare_nonletter_bigram_rate"], 0.0)
        self.assertGreater(
            many.features["rare_nonletter_bigram_rate"],
            one.features["rare_nonletter_bigram_rate"],
        )
        self.assertGreater(
            many.excesses["rare_nonletter_bigram_rate"],
            one.excesses["rare_nonletter_bigram_rate"],
        )
        self.assertGreater(one.s_struct, many.s_struct)
        self.assertLess(many.s_struct, 1.0)

    def test_separate_full_doc_and_clause_fits(self) -> None:
        full = lex.fit(_recipe_corpus(), granularity="full_doc")
        clauses = lex.fit(
            [_clause(word) for word in _CLAUSE_ANAGRAMS for _ in range(8)],
            granularity="clause_opt2c",
        )
        labeled = lex.fit([_clause()], granularity="clause")
        self.assertEqual(full.granularity, "full_doc")
        self.assertEqual(clauses.granularity, "clause_opt2c")
        self.assertEqual(labeled.granularity, "clause")
        self.assertGreaterEqual(full.char_df.get("/", 0.0), 0.01)
        self.assertEqual(clauses.char_df.get("/", 0.0), 0.0)
        self.assertNotEqual(full.char_df.get("/", 0.0), clauses.char_df.get("/", 0.0))
        with self.assertRaises(ValueError):
            lex.fit([_recipe()], granularity="sentence")

    def test_clause_min_below_full_doc_when_one_clause_is_anomalous(self) -> None:
        full = self.profile
        clause_profile = lex.fit(
            [_clause(word) for word in _CLAUSE_ANAGRAMS for _ in range(8)],
            granularity="clause",
        )
        benign_clause = _clause(_CLAUSE_PROBE_WORD)
        reduction = lex.score_clauses(
            self.probe,
            [benign_clause, _SMUGGLE],
            full,
            clause_profile,
        )
        self.assertEqual(reduction.full_doc.s_struct, 1.0)
        self.assertEqual(len(reduction.clause_scores), 2)
        self.assertEqual(reduction.clause_scores[0].s_struct, 1.0)
        self.assertLess(reduction.clause_scores[1].s_struct, 1.0)
        self.assertEqual(reduction.min_clause, reduction.clause_scores[1].s_struct)
        self.assertEqual(reduction.s_struct, reduction.min_clause)
        self.assertLess(reduction.s_struct, reduction.full_doc.s_struct)

    def test_empty_string_is_finite(self) -> None:
        _assert_finite(self, lex.score("", self.profile))

    def test_one_character_is_finite(self) -> None:
        _assert_finite(self, lex.score("q", self.profile))

    def test_emoji_only_is_finite(self) -> None:
        _assert_finite(self, lex.score("😀", self.profile))

    def test_channel_weights_are_positive_constants(self) -> None:
        self.assertEqual(
            set(lex.CHANNEL_WEIGHTS),
            set(lex.SCORED_CHANNELS),
        )
        for name, weight in lex.CHANNEL_WEIGHTS.items():
            self.assertGreater(weight, 0.0, name)
            self.assertIsInstance(weight, float)
        self.assertGreater(lex.S_STRUCT_SCALE, 0.0)
        self.assertGreater(lex.ROBUST_SCALE_FLOOR, 0.0)
        self.assertNotIn(lex.ALPHA_WORD_COUNT, lex.CHANNEL_WEIGHTS)

    def test_triggered_features_sorted_by_descending_contribution(self) -> None:
        scored = lex.score(_SMUGGLE, self.profile)
        contributions = [item.contribution for item in scored.top_triggered_features]
        self.assertGreater(len(contributions), 1)
        self.assertEqual(contributions, sorted(contributions, reverse=True))
        for item in scored.top_triggered_features:
            self.assertGreater(item.excess, 0.0)
            self.assertEqual(item.weight, lex.CHANNEL_WEIGHTS[item.name])
            self.assertEqual(item.contribution, item.weight * item.excess)
        names = [item.name for item in scored.top_triggered_features]
        self.assertEqual(len(names), len(set(names)))

    def test_s_struct_formula_and_open_unit_interval(self) -> None:
        self.assertEqual(lex.s_struct_from_weighted_sum(0.0), 1.0)
        scored = lex.score(_SMUGGLE, self.profile)
        weighted = sum(item.contribution for item in scored.top_triggered_features)
        self.assertGreater(weighted, 0.0)
        self.assertAlmostEqual(
            scored.s_struct,
            lex.s_struct_from_weighted_sum(weighted),
            places=12,
        )
        tiny = lex.s_struct_from_weighted_sum(1.0e9)
        self.assertGreater(tiny, 0.0)
        self.assertLessEqual(tiny, 1.0)
        self.assertTrue(math.isfinite(tiny))
        burst = lex.score("@" * 10000, self.profile)
        _assert_finite(self, burst)
        self.assertLess(burst.s_struct, 1.0)
        for sample in ("", "q", "😀", self.probe, _SMUGGLE, "???", "!!!"):
            _assert_finite(self, lex.score(sample, self.profile))

    def test_latency_benchmark_is_finite_and_iteration_count_is_exact(self) -> None:
        repeats = 11
        calls = {"n": 0}
        original = lex.score

        def _wrapped(text: str, profile: lex.LexicalProfile) -> lex.StructuralScore:
            calls["n"] += 1
            return original(text, profile)

        lex.score = _wrapped
        try:
            report = lex.latency_benchmark(self.probe, repeats, self.profile)
        finally:
            lex.score = original
        self.assertEqual(calls["n"], repeats)
        self.assertEqual(report.repeats, repeats)
        self.assertIsInstance(report.p50_us, float)
        self.assertIsInstance(report.p99_us, float)
        self.assertTrue(math.isfinite(report.p50_us))
        self.assertTrue(math.isfinite(report.p99_us))
        self.assertGreaterEqual(report.p50_us, 0.0)
        self.assertGreaterEqual(report.p99_us, 0.0)
        self.assertGreaterEqual(report.p99_us, report.p50_us)


if __name__ == "__main__":
    unittest.main(verbosity=2)
