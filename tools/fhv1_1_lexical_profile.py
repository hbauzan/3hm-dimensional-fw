#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Auto-calibrated character, symbol, and connector structural guardrail.

Arithmetic is IEEE 754 binary64. Input is the raw
string: no compatibility normalization is applied, so format characters,
fullwidth forms, and non-Latin letters stay visible to the features.

Rare non-letters are not a hand-written symbol list. ``fit`` records document
frequency on the supplied texts only. A non-letter or a 2-character non-letter
bigram contributes surprise only when its calibration document frequency is
strictly below 1 percent (exact rational test ``doc_count * 100 < n_docs``).
"""

from __future__ import annotations

import math
import time
import unicodedata
from collections import Counter
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping, Sequence

# Basic ASCII punctuation. Symbol characters are the residual outside ASCII
# letters, decimal digits, whitespace, and this set.
ASCII_PUNCT: frozenset[str] = frozenset(
    "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~"
)

# Closed connector sets. Primary language is whichever set has the higher
# token total on the fit texts. There is no domain-to-language table.
EN_CONNECTORS: frozenset[str] = frozenset(
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
)
ES_CONNECTORS: frozenset[str] = frozenset(
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
)
if not EN_CONNECTORS.isdisjoint(ES_CONNECTORS):
    raise RuntimeError("connector sets must be disjoint")

GRANULARITIES: frozenset[str] = frozenset(("full_doc", "clause", "clause_opt2c"))

# Short alphabetic queries skip only the low-side connector penalty.
SHORT_TEXT_ALPHA_WORDS = 6

# Positive floor inside max(p95 - median, IQR, floor). One floor for every channel.
ROBUST_SCALE_FLOOR = 0.05

# Clip the exponent so exp() stays inside the open unit interval (0, 1].
S_STRUCT_MIN_EXPONENT = -700.0

# Channel weights w_f. Constants. They are not estimated from evaluation rows.
#
#   excess_f = 0
#       when the channel lies inside [p01, p99]
#   excess_f = one-sided distance outside that interval / robust_scale
#       otherwise
#
#   S_struct = 1.0
#       if every excess_f == 0
#   S_struct = exp( -sum(w_f * excess_f) / S_STRUCT_SCALE )
#       otherwise
#
# S_STRUCT_SCALE is the positive constant in the exponential.
# It is not the per-channel robust scale.
CHANNEL_WEIGHT_TABLE: tuple[tuple[str, float], ...] = (
    ("letter_ratio", 1.00),
    ("digit_ratio", 0.80),
    ("punct_ratio", 1.20),
    ("symbol_ratio", 1.50),
    ("non_latin_or_control_unicode_ratio", 1.80),
    ("max_repeated_punct_run", 1.40),
    ("char_shannon_entropy", 0.70),
    ("rare_nonletter_char_rate", 1.70),
    ("rare_nonletter_bigram_rate", 1.70),
    ("target_connector_ratio", 1.30),
    ("foreign_connector_ratio", 1.60),
)
CHANNEL_WEIGHTS: Mapping[str, float] = MappingProxyType(
    {name: weight for name, weight in CHANNEL_WEIGHT_TABLE}
)
S_STRUCT_SCALE = 8.0
SCORED_CHANNELS: tuple[str, ...] = tuple(name for name, _ in CHANNEL_WEIGHT_TABLE)

ALPHA_WORD_COUNT = "alpha_word_count"


def s_struct_from_weighted_sum(weighted_sum: float) -> float:
    """Map ``sum(w_f * excess_f)`` onto ``S_struct`` in ``(0, 1]``.

    A zero sum is exactly ``1.0``. Any positive sum uses the exponential above.
    """
    if weighted_sum == 0.0:
        return 1.0
    if weighted_sum < 0.0:
        raise ValueError("weighted excess sum must be >= 0")
    exponent = -weighted_sum / S_STRUCT_SCALE
    if exponent < S_STRUCT_MIN_EXPONENT:
        exponent = S_STRUCT_MIN_EXPONENT
    value = math.exp(exponent)
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError("S_struct left the open unit interval")
    return value


@dataclass(frozen=True, slots=True)
class ChannelEnvelope:
    """Normal envelope for one structural channel, fit on calibration texts."""

    p01: float
    p99: float
    median: float
    p25: float
    p75: float
    p95: float
    iqr: float
    robust_scale: float


@dataclass(frozen=True, slots=True)
class TriggeredFeature:
    """One channel with positive excess, ordered later by contribution."""

    name: str
    excess: float
    weight: float

    @property
    def contribution(self) -> float:
        return self.weight * self.excess


@dataclass(frozen=True, slots=True)
class StructuralScore:
    """``S_struct`` plus the channels that fell outside the envelope."""

    s_struct: float
    top_triggered_features: tuple[TriggeredFeature, ...]
    features: Mapping[str, float]
    excesses: Mapping[str, float]
    missing_connector_penalty: float


@dataclass(frozen=True, slots=True)
class ClauseReduction:
    """Full-document score and ``min(full, min clause)``."""

    full_doc: StructuralScore
    clause_scores: tuple[StructuralScore, ...]
    min_clause: float
    s_struct: float


@dataclass(frozen=True, slots=True)
class LatencyReport:
    """Microseconds per ``score`` call over a fixed iteration count."""

    p50_us: float
    p99_us: float
    repeats: int


@dataclass(frozen=True, slots=True)
class LexicalProfile:
    """Snapshot of calibration document frequencies and channel envelopes."""

    granularity: str
    n_docs: int
    primary_language: str
    en_connector_total: int
    es_connector_total: int
    char_df: Mapping[str, float]
    bigram_df: Mapping[str, float]
    char_doc_count: Mapping[str, int]
    bigram_doc_count: Mapping[str, int]
    envelopes: Mapping[str, ChannelEnvelope]

    def score(self, text: str) -> StructuralScore:
        return _evaluate(text, self)


def _is_ascii_letter(char: str) -> bool:
    return ("A" <= char <= "Z") or ("a" <= char <= "z")


def _is_non_latin_or_control(char: str) -> bool:
    """Format characters, fullwidth forms, and letters outside the Latin script."""
    code = ord(char)
    if code < 128:
        return False
    if unicodedata.category(char) == "Cf":
        return True
    if unicodedata.east_asian_width(char) == "F" or 0xFF00 <= code <= 0xFFEF:
        return True
    if not char.isalpha():
        return False
    return "LATIN" not in unicodedata.name(char, "")


def _alpha_tokens(text: str) -> list[str]:
    """Alphabetic runs, casefolded. Digits and punctuation split tokens."""
    tokens: list[str] = []
    buffer: list[str] = []
    for char in text:
        if char.isalpha():
            buffer.append(char)
            continue
        if buffer:
            tokens.append("".join(buffer).casefold())
            buffer.clear()
    if buffer:
        tokens.append("".join(buffer).casefold())
    return tokens


def _max_repeated_punct_run(text: str) -> int:
    best = 0
    run = 0
    prev = ""
    for char in text:
        if char in ASCII_PUNCT and char == prev:
            run += 1
        elif char in ASCII_PUNCT:
            run = 1
            prev = char
        else:
            run = 0
            prev = ""
        if run > best:
            best = run
    return best


def _shannon_bits(text: str) -> float:
    """Character Shannon entropy in bits. Same multiset always yields the same float."""
    length = len(text)
    if length == 0:
        return 0.0
    counts = Counter(text)
    entropy = 0.0
    inverse = 1.0 / float(length)
    for char in sorted(counts):
        probability = counts[char] * inverse
        entropy -= probability * math.log2(probability)
    return entropy


def _scan_nonletters(text: str) -> tuple[list[str], list[str]]:
    """Non-letter non-space characters, and consecutive pairs of those characters."""
    chars: list[str] = []
    bigrams: list[str] = []
    prev: str | None = None
    for char in text:
        if char.isalpha() or char.isspace():
            prev = None
            continue
        chars.append(char)
        if prev is not None:
            bigrams.append(prev + char)
        prev = char
    return chars, bigrams


def _is_rare(doc_count: int, n_docs: int) -> bool:
    """``df < 0.01`` in exact integer arithmetic."""
    return doc_count * 100 < n_docs


def _rare_rate(items: Sequence[str], doc_counts: Mapping[str, int], n_docs: int) -> float:
    """In-prompt relative frequency of items whose calibration df is below 1 percent.

    Each occurrence has weight ``1 / len(items)``. Common items contribute 0.
    An empty item list yields 0.
    """
    total = len(items)
    if total == 0:
        return 0.0
    rare = 0
    for item in items:
        if _is_rare(doc_counts.get(item, 0), n_docs):
            rare += 1
    return float(rare) / float(total)


def _ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return float(numerator) / float(denominator)


def _connector_totals(texts: Sequence[str]) -> tuple[int, int]:
    english = 0
    spanish = 0
    for text in texts:
        for token in _alpha_tokens(text):
            if token in EN_CONNECTORS:
                english += 1
            elif token in ES_CONNECTORS:
                spanish += 1
    return english, spanish


def _primary_language(en_total: int, es_total: int) -> str:
    if es_total > en_total:
        return "es"
    return "en"


def _feature_map(
    text: str,
    n_docs: int,
    char_doc_count: Mapping[str, int],
    bigram_doc_count: Mapping[str, int],
    primary_language: str,
) -> dict[str, float]:
    length = len(text)
    ascii_letter_n = 0
    digit_n = 0
    whitespace_n = 0
    punct_n = 0
    letter_n = 0
    non_latin_n = 0
    for char in text:
        if char.isalpha():
            letter_n += 1
        if _is_ascii_letter(char):
            ascii_letter_n += 1
        elif char.isdigit():
            digit_n += 1
        elif char.isspace():
            whitespace_n += 1
        elif char in ASCII_PUNCT:
            punct_n += 1
        if _is_non_latin_or_control(char):
            non_latin_n += 1
    symbol_n = length - ascii_letter_n - digit_n - whitespace_n - punct_n
    if symbol_n < 0:
        raise ValueError("character partition undercounted the string")

    tokens = _alpha_tokens(text)
    word_count = len(tokens)
    if primary_language == "es":
        target_set = ES_CONNECTORS
        foreign_set = EN_CONNECTORS
    elif primary_language == "en":
        target_set = EN_CONNECTORS
        foreign_set = ES_CONNECTORS
    else:
        raise ValueError("primary language must be en or es")
    target_hits = 0
    foreign_hits = 0
    for token in tokens:
        if token in target_set:
            target_hits += 1
        elif token in foreign_set:
            foreign_hits += 1

    nonletters, bigrams = _scan_nonletters(text)
    return {
        "letter_ratio": _ratio(letter_n, length),
        "digit_ratio": _ratio(digit_n, length),
        "punct_ratio": _ratio(punct_n, length),
        "symbol_ratio": _ratio(symbol_n, length),
        "non_latin_or_control_unicode_ratio": _ratio(non_latin_n, length),
        "max_repeated_punct_run": float(_max_repeated_punct_run(text)),
        "char_shannon_entropy": _shannon_bits(text),
        ALPHA_WORD_COUNT: float(word_count),
        "rare_nonletter_char_rate": _rare_rate(nonletters, char_doc_count, n_docs),
        "rare_nonletter_bigram_rate": _rare_rate(bigrams, bigram_doc_count, n_docs),
        "target_connector_ratio": _ratio(target_hits, word_count),
        "foreign_connector_ratio": _ratio(foreign_hits, word_count),
    }


def _percentile(sorted_values: Sequence[float], percent: float) -> float:
    """Linear (type-7) percentile. ``percent`` is in ``[0, 100]``."""
    count = len(sorted_values)
    if count == 0:
        raise ValueError("percentile of an empty sample")
    if count == 1 or percent <= 0.0:
        return float(sorted_values[0])
    if percent >= 100.0:
        return float(sorted_values[-1])
    rank = (count - 1) * (percent / 100.0)
    low = math.floor(rank)
    high = math.ceil(rank)
    weight = rank - low
    return (float(sorted_values[low]) * (1.0 - weight)) + (
        float(sorted_values[high]) * weight
    )


def _envelope(values: Sequence[float]) -> ChannelEnvelope:
    ordered = sorted(float(value) for value in values)
    p01 = _percentile(ordered, 1.0)
    p25 = _percentile(ordered, 25.0)
    median = _percentile(ordered, 50.0)
    p75 = _percentile(ordered, 75.0)
    p95 = _percentile(ordered, 95.0)
    p99 = _percentile(ordered, 99.0)
    iqr = max(0.0, p75 - p25)
    upper_spread = max(0.0, p95 - median)
    robust_scale = max(upper_spread, iqr, ROBUST_SCALE_FLOOR)
    if not math.isfinite(robust_scale) or robust_scale <= 0.0:
        raise ValueError("robust scale must be a positive finite float")
    return ChannelEnvelope(
        p01=p01,
        p99=p99,
        median=median,
        p25=p25,
        p75=p75,
        p95=p95,
        iqr=iqr,
        robust_scale=robust_scale,
    )


def _document_counts(
    texts: Sequence[str],
) -> tuple[dict[str, int], dict[str, int]]:
    char_docs: Counter[str] = Counter()
    bigram_docs: Counter[str] = Counter()
    for text in texts:
        chars, bigrams = _scan_nonletters(text)
        char_docs.update(set(chars))
        bigram_docs.update(set(bigrams))
    return dict(char_docs), dict(bigram_docs)


def _df_map(doc_counts: Mapping[str, int], n_docs: int) -> dict[str, float]:
    return {
        key: float(doc_counts[key]) / float(n_docs)
        for key in sorted(doc_counts)
    }


def _outside_excess(value: float, envelope: ChannelEnvelope) -> tuple[float, float]:
    """Low-side and high-side excess. At most one side is positive."""
    low = 0.0
    high = 0.0
    if value < envelope.p01:
        low = (envelope.p01 - value) / envelope.robust_scale
    elif value > envelope.p99:
        high = (value - envelope.p99) / envelope.robust_scale
    return low, high


def _evaluate(text: str, profile: LexicalProfile) -> StructuralScore:
    if not isinstance(text, str):
        raise TypeError("text must be a str")
    features = _feature_map(
        text,
        profile.n_docs,
        profile.char_doc_count,
        profile.bigram_doc_count,
        profile.primary_language,
    )
    short = features[ALPHA_WORD_COUNT] < float(SHORT_TEXT_ALPHA_WORDS)
    excesses: dict[str, float] = {}
    missing_connector_penalty = 0.0
    for name in SCORED_CHANNELS:
        value = features[name]
        low, high = _outside_excess(value, profile.envelopes[name])
        if name == "target_connector_ratio":
            # Missing-connector penalty is only the low side, and only at 6+ words.
            if short:
                low = 0.0
            missing_connector_penalty = low
        excesses[name] = low + high
        if not math.isfinite(excesses[name]) or excesses[name] < 0.0:
            raise ValueError(f"non-finite excess for {name}")

    weighted = 0.0
    triggered: list[TriggeredFeature] = []
    for name in SCORED_CHANNELS:
        excess = excesses[name]
        weight = CHANNEL_WEIGHTS[name]
        if excess > 0.0:
            weighted += weight * excess
            triggered.append(TriggeredFeature(name=name, excess=excess, weight=weight))
    triggered.sort(key=lambda item: (-item.contribution, item.name))
    s_struct = s_struct_from_weighted_sum(weighted)
    if not math.isfinite(s_struct) or s_struct <= 0.0 or s_struct > 1.0:
        raise ValueError("S_struct left (0, 1]")
    return StructuralScore(
        s_struct=s_struct,
        top_triggered_features=tuple(triggered),
        features=MappingProxyType(features),
        excesses=MappingProxyType(excesses),
        missing_connector_penalty=missing_connector_penalty,
    )


def fit(
    calibration_texts: Sequence[str],
    granularity: str = "full_doc",
) -> LexicalProfile:
    """Fit envelopes and document frequencies on ``calibration_texts`` only.

    ``granularity`` labels the caller-supplied sample (``full_doc``,
    ``clause``, or ``clause_opt2c``). The math does not change with the label.
    Two calls fit the two granularities. This function does not open files.
    """
    if granularity not in GRANULARITIES:
        raise ValueError(
            "granularity must be full_doc, clause, or clause_opt2c"
        )
    texts = tuple(calibration_texts)
    if not texts:
        raise ValueError("calibration_texts must contain at least one document")
    for text in texts:
        if not isinstance(text, str):
            raise TypeError("calibration texts must be str")

    en_total, es_total = _connector_totals(texts)
    primary = _primary_language(en_total, es_total)
    char_counts, bigram_counts = _document_counts(texts)
    n_docs = len(texts)
    rows = [
        _feature_map(text, n_docs, char_counts, bigram_counts, primary)
        for text in texts
    ]
    envelopes = {
        name: _envelope([row[name] for row in rows])
        for name in SCORED_CHANNELS
    }
    return LexicalProfile(
        granularity=granularity,
        n_docs=n_docs,
        primary_language=primary,
        en_connector_total=en_total,
        es_connector_total=es_total,
        char_df=MappingProxyType(_df_map(char_counts, n_docs)),
        bigram_df=MappingProxyType(_df_map(bigram_counts, n_docs)),
        char_doc_count=MappingProxyType(dict(sorted(char_counts.items()))),
        bigram_doc_count=MappingProxyType(dict(sorted(bigram_counts.items()))),
        envelopes=MappingProxyType(envelopes),
    )


def score(text: str, profile: LexicalProfile) -> StructuralScore:
    """Score one raw string. ``S_struct`` is exactly ``1.0`` inside the envelope."""
    return _evaluate(text, profile)


def score_clauses(
    full_text: str,
    clauses: Sequence[str],
    full_profile: LexicalProfile,
    clause_profile: LexicalProfile,
) -> ClauseReduction:
    """Return the full-document score and ``min(full, min clause score)``.

    An empty clause list has no anomalous clause, so the clause minimum is ``1.0``.
    """
    full_score = score(full_text, full_profile)
    clause_scores = tuple(score(clause, clause_profile) for clause in clauses)
    if clause_scores:
        min_clause = min(item.s_struct for item in clause_scores)
    else:
        min_clause = 1.0
    reduced = min(full_score.s_struct, min_clause)
    return ClauseReduction(
        full_doc=full_score,
        clause_scores=clause_scores,
        min_clause=min_clause,
        s_struct=reduced,
    )


def latency_benchmark(
    text: str,
    repeats: int,
    profile: LexicalProfile,
) -> LatencyReport:
    """Time ``repeats`` calls of ``score`` on the same text.

    The iteration count is exactly ``repeats``. Reported percentiles are
    microseconds and are finite and non-negative.
    """
    if isinstance(repeats, bool) or not isinstance(repeats, int) or repeats < 1:
        raise ValueError("repeats must be a positive integer")
    samples = [0.0] * repeats
    for index in range(repeats):
        started = time.perf_counter_ns()
        score(text, profile)
        elapsed_ns = time.perf_counter_ns() - started
        samples[index] = float(elapsed_ns) / 1000.0
    samples.sort()
    report = LatencyReport(
        p50_us=_percentile(samples, 50.0),
        p99_us=_percentile(samples, 99.0),
        repeats=repeats,
    )
    if report.p50_us < 0.0 or report.p99_us < 0.0:
        raise ValueError("latency percentiles must be non-negative")
    if not math.isfinite(report.p50_us) or not math.isfinite(report.p99_us):
        raise ValueError("latency percentiles must be finite")
    return report
