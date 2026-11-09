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

## _Avoid_

- "embedding box", "filter", "rule" — use **DomainHypercubeLock**
- "vector", "tensor buffer" — use **AlignedVec1024**
- "threshold vote", "spectral quorum" — use **Subspace Coordinate Quorum (K-of-D L∞ Gate)**
- "LLM latent space" — use **1024D Contrastive Embedding Manifold ($S^{1023} \subset \mathbb{R}^{1024}$)**
- "17-digit precision" — use **Deterministic IEEE 754 binary32 evaluation with 0 ULP cross-architecture parity**
- "rompepepe" — use **SCPB-220**
