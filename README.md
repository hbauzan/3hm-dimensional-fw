# Three-Headed Semantic Firewall (sf-core)

A high-performance, deterministic, hardware-accelerated L7 semantic firewall and containment gateway for Large Language Models (LLMs) and 1024D vector manifolds.

[![Rust](https://img.shields.io/badge/Rust-1.94.1-orange?logo=rust)](rust-toolchain.toml)
[![License](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)
[![DNPI](https://img.shields.io/badge/Registro%20DNPI-N%C2%BA%20226-green)](NOTICE)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.14049872.svg)](https://doi.org/10.5281/zenodo.14049872)
[![Latency](https://img.shields.io/badge/p99%20Gate%20Latency-0.127ms%20%40%201000%20RPS-brightgreen)](reports/scpb_220_matrix.json)
[![Containment](https://img.shields.io/badge/SCPB--220-100%25%20Containment-purple)](reports/scpb_220_matrix.json)

---

## 1. Problem Statement: Cosine Dilution via Sub-Clause Piggybacking

In modern enterprise architectures, Large Language Models are frequently protected by semantic embedding firewalls that evaluate prompt safety by computing the cosine similarity between the incoming prompt vector and an authorized domain centroid:

$$\cos(v, \mu_{target}) = \frac{v \cdot \mu_{target}}{\|v\|_2 \|\mu_{target}\|_2} \ge \tau_{cos}$$

However, global sequence embeddings (such as those produced by `BAAI/bge-m3` or other contrastive transformers on the **1024D Contrastive Embedding Manifold ($S^{1023} \subset \mathbb{R}^{1024}$)**) perform mean-pooling over token representations. When an attacker appends an unauthorized, off-domain, or adversarial payload $x_{mal}$ to an extensive, legitimate in-domain query $x_{host}$:

$$x_{comp} = [x_{host} \,\|\, x_{mal}]$$

The resulting composite vector $v_{comp}$ behaves as a convex combination:

$$v_{comp} \approx \alpha v_{host} + (1 - \alpha) v_{mal}, \quad \text{where } \alpha = \frac{|x_{host}|}{|x_{host}| + |x_{mal}|}$$

As the legitimate host context grows ($\alpha \to 1$), the global sequence cosine similarity behaves as an adversarial low-pass filter:

$$\cos(v_{comp}, \mu_{target}) \approx \alpha \cos(v_{host}, \mu_{target}) + (1 - \alpha) \cos(v_{mal}, \mu_{target}) \ge \tau_{cos}$$

The global score comfortably exceeds the security threshold $\tau_{cos}$, leaking the unauthorized payload into the upstream LLM context. In our empirical **SCPB-220 (Sub-Clause Piggybacking Benchmark)**, global sequence cosine gating leaks **50.0%** of adversarial payloads.

---

## 2. Why Coordinate-Wise $K$-of-$D$ Subspace Quorum ($K$-of-$D$ $\ell_\infty$ Gate)?

To prevent cosine dilution, a semantic firewall must isolate and inspect individual sub-clauses in high-dimensional space. However, traditional geometric containment approaches fail in production:

| Approach | Mathematical Formulation | Time Complexity | Memory / Cache Footprint | Operational Boundary & Failure Mode |
| :--- | :--- | :---: | :---: | :--- |
| **Full Mahalanobis Distance** | $D_M(x) = \sqrt{(x-\mu)^T \Sigma^{-1} (x-\mu)}$ | $\mathcal{O}(D^2)$ | **~4.0 MB** per domain ($\Sigma^{-1} \in \mathbb{R}^{1024 \times 1024}$) | **L3/RAM Bound**: Memory bus saturation; latency spikes (>15 ms) under 1,000 RPS concurrent load. |
| **Strict $\ell_\infty$ Hyper-Rectangle** | $\bigwedge_{d=1}^{1015} [x_d \in [lo_d, hi_d]]$ | $\mathcal{O}(D)$ | **~8 KB** per domain | **Curse of Dimensionality**: Vanishing intersection probability. Even if each dimension has $99\%$ marginal coverage, $(0.99)^{1015} \approx 3.7 \times 10^{-5}$. Catastrophic False Positive Rate (**99.996% false rejections**). |
| **3HM $K$-of-$D$ Subspace Quorum** | $\sum_{d \in \mathcal{A}} \mathbf{1}_{\{lo_d \le x_d \le hi_d\}} \ge K$ | $\mathcal{O}(D)$ SIMD | **8 KB** per domain (fits in **L1 Cache**) | **0 ULP Determinism**: SIMD bitmask + `POPCNT`. **100.0% containment** on SCPB-220, **0.00% False Positive Rate** on clean traffic, **0.127 ms p99** gate execution. |

3HM adopts a coordinate-wise **$K$-of-$D$ $\ell_\infty$ Quorum Gate** ($K=103 \approx \lceil 0.10 \times 1015 \rceil$). It does not mandate that all coordinates simultaneously lie inside the envelope; instead, it requires that affirmative in-box coordinate votes meet or exceed quorum $K$ over active coordinates.

---

## 3. Anisotropic Rogue Dimension Pruning (Timkey & van Schijndel, 2021)

Contextualized language models and contrastive embedding spaces suffer from representation anisotropy: embeddings occupy a narrow cone in the vector space, dominated by a handful of high-variance, rogue coordinates.

Citing **Timkey & van Schijndel (2021)** (*"All Bark and No Bite: Rogue Dimensions Dominate Contextualized Embeddings"*, EMNLP), 3HM prunes the nine universal background coordinates that exhibit non-semantic universal magnitude across all text domains:

$$\text{Universal Noise Coordinates} = [292, 297, 308, 329, 386, 404, 577, 616, 780]$$

In `sf-kernels`, `NoiseBitmask1024` masks out these 9 rogue dimensions, leaving **1,015 active discriminative coordinates**. This eliminates background isotropic drift and prevents adversarial piggybacking from exploiting universal coordinate inflation.

---

## 4. Multi-Tier Defense Architecture & Sequential Early-Exit

`sf-core` executes a multi-stage defense pipeline before allowing upstream LLM inference:

```
Ingress Prompt
      │
      ▼
[ Stage 0: InputNormalizer ] ──> NFKC Normalization + Homoglyph Mapping + Invisible Stripping
      │                         + Base64 / High-Entropy Payload Inspection
      ▼
[ Stage 1: ClauseSegmenter ] ──> Delimiter & Trilingual Connector Splitting (ES/EN/DE)
      │
      ▼
[ Stage 2: Embedder ] ─────────> BAAI/bge-m3 on 1024D Manifold (S¹⁰²³ ⊂ ℝ¹⁰²⁴)
      │                          Batched [1 + M, 1024] IEEE 754 binary32 (0 ULP)
      ▼
[ Tier 1: Centroid Cosine ] ───> Full Prompt Cosine Gate: cos(v_prompt, μ) ≥ τ₁
      │ (PASS)
      ▼
[ Sequential Clause Loop ] ────> Evaluates clause i = 0 .. M-1 sequentially:
      │                            ├─ Tier 2: Clause Cosine Gate: cos(v_clause, μ) ≥ τ₂
      │                            └─ Tier 3: Subspace Coordinate Quorum (K-of-D L∞ Gate)
      │                          * Short-circuits immediately on first failure:
      │                            returns HTTP 403 & reports `clauses_skipped`.
      ▼ (PASS)
[ Pairwise Containment ] ──────> 55 Pairwise OvO (One-vs-One) Cross-Lingual Subspace Masks
      │ (PASS)
      ▼
Upstream LLM Streaming (SSE)
```

### Sequential Clause Early-Exit
When evaluating multi-clause prompts ($M$ clauses), 3HM executes short-circuiting: as soon as clause $i$ breaches either Tier 2 or Tier 3, evaluation halts immediately, returns HTTP 403, and records how many downstream clauses were skipped:

$$\text{clauses\_skipped} = M - 1 - i$$

---

## 5. Disaggregated Dual-Latency Telemetry & Benchmarks

Systems engineers require strict separation between hardware-accelerated SIMD gate latency and upstream neural network embedding inference. 3HM tracks and exposes both metrics in HTTP headers (`x-sf-*`) and structured response JSON:

| Pipeline Stage | Metric Key | Typical Value (p50) | Typical Value (p99) | Execution Engine |
| :--- | :--- | :---: | :---: | :--- |
| **Input Normalization & Segmentation** | `normalizer_segmenter_us` | 18 µs | 42 µs | CPU (Rust `unicode-normalization`) |
| **SIMD Gate Kernel** | `simd_gate_kernel_us` | **46 µs (0.046 ms)** | **127 µs (0.127 ms)** | CPU SIMD (`sf-kernels` NEON / AVX2) |
| **Embedding Generation** | `embedding_inference_ms` | 8.50 ms | 14.20 ms | Local Metal MPS / TEI Server |
| **Total Gateway Overhead** | `total_pipeline_ms` | 8.56 ms | 14.37 ms | End-to-end proxy pipeline |

### Scientific Benchmark Verification

Evaluated on Apple Silicon (M-series, ARM64 NEON) and x86_64:

| Benchmark Suite | Total Samples | Global Sequence Cosine Baseline | 3HM Subspace Quorum (Recall) | Clean In-Domain FPR | Gate Kernel p50 | Gate Kernel p99 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Suite 1: SCPB-220** (Sub-Clause Piggybacking) | 220 | 50.00% (*110 leaks*) | **100.00% (220/220)** | 0.00% (0/55) | 46 µs (0.046 ms) | **127 µs (0.127 ms)** |
| **Suite 2: OOS & Injection** (CLINC / Deepset ROC) | 200 | 48.00% (*48 leaks*) | **100.00% (100/100)** | **0.00% (0/100)** | 45 µs (0.045 ms) | **125 µs (0.125 ms)** |

---

## 6. Threat Model & Known Operational Boundaries

### What 3HM Prevents
1. **Sub-Clause Piggybacking**: Unauthorized tasks smuggled inside verbose host queries.
2. **Topical Drift & Cross-Domain Leakage**: Queries drifting across the 11 calibrated canonical domains and **55 Pairwise OvO Cross-Lingual Subspace Masks**.
3. **Homoglyph Obfuscation**: Cyrillic, Greek, and full-width homoglyphs mapped to canonical ASCII equivalents before tokenization via `InputNormalizer`.
4. **Invisible Control Smuggling**: Zero-width evasion characters (`\u{200B}`, `\u{200C}`, `\u{200D}`, `\u{2060}`, `\u{FEFF}`, `\u{00AD}`) stripped before clause parsing.
5. **Base64 Payload Smuggling**: Contiguous Base64 tokens ($\ge 24$ chars) decoded, verified for UTF-8 cleartext entropy, and routed through `ClauseSegmenter`.

### Known Operational Boundaries
- **Embedding Invariance**: Injections that map strictly inside the calibrated coordinate bounding box of the target domain without displacing coordinates are outside L7 coordinate boundaries and require egress analysis.
- **Maximum Embedding Token Length**: Bound by `BAAI/bge-m3` maximum sequence length (8,192 tokens).

---

## 7. Workspace Topology

| Component | Path | Description |
| :--- | :--- | :--- |
| **`sf-kernels`** | [`crates/sf-kernels`](crates/sf-kernels) | Hardware-accelerated SIMD kernels (NEON, AVX2+FMA, AVX-512) and IEEE 754 binary32 numeric routines. 0 ULP bitmask parity and scalar-SIMD cosine agreement within $10^{-14}$. |
| **`sf-storage`** | [`crates/sf-storage`](crates/sf-storage) | Columnar domain hypercube registry on LanceDB (pinned Arrow 58.4.1), wait-free `ArcSwap` hot-reloading, SHA-256 lock manifests, and SNR pruning. |
| **`sf-proxy`** | [`crates/sf-proxy`](crates/sf-proxy) | Reverse proxy daemon (:8088). Serves `/v1/chat/completions`, streaming `/api/v1/chat`, `InputNormalizer`, and sequential early-exit cascade. |
| **`sf-bench`** | [`crates/sf-bench`](crates/sf-bench) | Benchmark harness: SCPB-220, OOS injection ROC suite, and 1,000 RPS load SLA benchmark. |
| **`sf-ui`** | [`crates/sf-ui`](crates/sf-ui) | Embedded diagnostic studio server (:3000) with Axum handlers for in-depth coordinate containment analysis. |
| **`frontend`** | [`frontend/`](frontend) | Decoupled Vite/React/TypeScript playground (:5173) with live parameter tuning, preset test chips, SSE streaming, and breach telemetry. |

---

## 8. Quickstart: Interactive Control Panel (`./setup.sh`)

```bash
chmod +x setup.sh
./setup.sh
```

### Main Menu:
- **`1`**: **🚀 Desplegar Stack Completo**: Launches `sf-proxy` (:8088), the `frontend` SPA (:5173), and auto-seeds 55 canonical locks into LanceDB.
- **`2`**: **Iniciar Servicio en Primer Plano**: Runs `sf-proxy`, `frontend`, or `sf-ui` in the foreground.
- **`3`**: **Ejecutar Suite de Tests Unificada**: Runs `cargo test --workspace` + Vitest in `frontend/`.
- **`4`**: **Quality Gates & Linters Estrictos**: Executes `cargo fmt`, `cargo clippy`, TypeScript checks, and Oxlint.
- **`5`**: **Evaluar Ataques SCPB-220**: Runs the 220 adversarial attack test matrix against 55 locks.
- **`6`**: **Benchmark de Carga & SLA 1000 RPS**: Verifies the p99 latency SLA (< 2ms) under concurrent load.
- **`7`**: **Gestión de LanceDB & Catálogo**: Seeds canonical locks, calibrates domains, and runs `sf-ingest`.

---

## 9. Manual Verification & Toolchain Commands

### Rust Toolchain (Pinned 1.94.1)
```bash
# Code formatting check
cargo fmt --all -- --check

# Strict Clippy linter
cargo clippy --workspace --all-targets -- -D warnings

# Execute test suite
cargo test --workspace

# Run scientific benchmark suite (SCPB-220 + OOS Injection)
cargo run --release -p sf-bench
```

### Frontend Toolchain (pnpm)
```bash
cd frontend
pnpm test
pnpm run lint
```

---

## 10. License & Official Software Registration

Licensed under the Apache License, Version 2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE).  
Copyright © 2026 Héctor Andrés Bauzán Saavedra.

### Official Software Registration / Registro Oficial
- **Obra / Work**: Three-Headed Semantic Firewall (3HM)
- **Titular / Author**: Héctor Andrés Bauzán Saavedra
- **Número de Inscripción**: Nº 226
- **Fecha de Inscripción**: 04/08/2026 (August 4, 2026)
- **Clasificación / Type**: Programa de ordenador (Software)
- **Organismo / Registry**: Dirección Nacional de la Propiedad Industrial (DNPI - MIEM) / Registro de Software, República Oriental del Uruguay
- **Marco Legal**: Ley 9.739 de 17/12/1937 (conforme Ley N° 20.212 y Decreto N° 39/2025)

Pursuant to Section 4(d) of the Apache License, Version 2.0, the [NOTICE](NOTICE) file must be retained and distributed with any reproduction or derivative work.
