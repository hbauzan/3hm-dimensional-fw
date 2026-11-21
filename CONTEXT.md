# CONTEXT — sf-core ubiquitous language

## DomainHypercubeLock

A calibrated domain: centroid, pre-dilated coordinate bounds, noise mask, Top-K indices, quorum, cosine thresholds, and polarity.

## AlignedVec1024

A 1024-dimensional IEEE 754 binary32 tensor on the 1024D Contrastive Embedding Manifold ($S^{1023} \subset \mathbb{R}^{1024}$). Layout is 4096 bytes, aligned to 64 bytes. Evaluated with deterministic IEEE 754 binary32 arithmetic with 0 ULP cross-architecture parity.

## NoiseBitmask1024

A 1024-bit mask. A set bit marks an active coordinate. A clear bit marks pruned noise.

## SubspaceCoordinateQuorum

Tier-3 Mode C rule: Subspace Coordinate Quorum (K-of-D L∞ Gate). An allowlist passes when affirmative in-box coordinate votes reach quorum `K` (default 103) over active coordinates in the canonical coordinate basis via ℓ_∞ bounding boxes and bitmask popcount.

## UniversalNoiseIndices

Anisotropic Rogue Dimensions (Timkey & van Schijndel, 2021). The nine BGE-M3 background coordinates cleared by the default mask: 292, 297, 308, 329, 386, 404, 577, 616, 780. Active count is 1015.

## InputNormalizer

Deterministic pre-segmentation normalizer executing before ClauseSegmenter: Unicode NFKC canonicalization, Cyrillic/Greek homoglyph mapping to ASCII, zero-width evasion character stripping, and high-entropy Base64 payload decoding.

## ClauseSegmenter

The deterministic splitter that yields borrowed clause slices from one prompt.

## PairwiseDifferentialLock

55 Pairwise OvO (One-vs-One) Cross-Lingual Subspace Masks. A **DomainHypercubeLock** whose id is `left_right` for two canonical domains. The coordinate envelope belongs to `left`.

## SCPB-220

Sub-Clause Piggybacking Benchmark with 220 adversarial test cases evaluating containment against cosine dilution.

## L3PairwiseQuorum

Failing tier `L3_PAIRWISE_QUORUM`. A **PairwiseDifferentialLock** rejected the prompt or one clause.

## AnyAllowlist

Wildcard policy for `X-Semantic-Domain: *`. One allowlist must contain the prompt and every clause.

## AllLocks

Wildcard policy selected by `X-SF-Wildcard-Mode: all`. Every selected lock must pass.

## Denylist

A lock with `polarity == 1`. When several denylists are in scope, all of them must pass.

## Allowlist

A lock with `polarity == 0`. Containment means the vector stays inside that lock's gates.

## FiltroHectorV1

Deterministic exhaustive coordinate-wise AABB on raw IEEE 754 binary64 embeddings. A prompt passes when every evaluated coordinate satisfies `min_d <= x_d <= max_d`. Polarity `0` is an allowlist. The kernel stores `observed_bits` as `u64` from `f64::to_bits()` and does not depend on a serializer. The proxy prints those bits as `0x` plus 16 lowercase hex digits.

## Fhv1EnvelopeProfile

One saved calibration. The id is `{policy}-v{version}-{12 hex}` from the first six bytes of the corpus SHA-256. It stores min, max, mean, span, variance, std dev, movement-tier codes, sample count, the normalize flag, and the rogue-mask default. It lives in `fhv1_profiles` beside `domain_hypercubes` and does not replace that table.

## MovementTier

`ZeroSpan`, `LowAnchor`, `Moderate`, `HighVolatility`, `ExtremeMovement`. The tier of a coordinate comes from its population span, variance, or standard deviation against the P25, P75, and P90 cutoffs of the finite positive values.

## SymmetricInferencePipeline

Calibration and evaluation call the same raw binary64 embed path. A chat request may reuse one normalized `/embed` batch only when the profile normalizes and `eval_granularity` is not `full_mirror`, and only when the expanded chunk texts are exactly that batch.

## Fhv1AuditTrace

One persisted chunk of an evaluation. `source_kind` is `REALTIME_CHAT`, `REALTIME_LAB`, or `BENCHMARK`. Rows that share a `trace_id` are one drill-down. `3hm_plus_fhv1` still writes the chat trace when the 3HM cascade rejects the prompt first.

## _Avoid_

- "embedding box", "filter", "rule" — use **DomainHypercubeLock**
- "vector", "tensor buffer" — use **AlignedVec1024**
- "threshold vote", "spectral quorum" — use **Subspace Coordinate Quorum (K-of-D L∞ Gate)**
- "LLM latent space" — use **1024D Contrastive Embedding Manifold ($S^{1023} \subset \mathbb{R}^{1024}$)**
- "17-digit precision" — use **Deterministic IEEE 754 binary32 evaluation with 0 ULP cross-architecture parity**
- "rompepepe" — use **SCPB-220**
- rounded fhv1 coordinates — use **raw binary64** and `observed_bits`
