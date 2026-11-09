---
task_id: "TASK-006"
status: "DONE"
assigned_architect: "maximum-architect-agent"
protocol: "transparent-dev-protocol"
title: "3HM (sf-core) v1.0 Scientific & Systems Hardening"
created_at: "2026-11-09T18:00:00-03:00"
---

# TASK-006: 3HM (sf-core) v1.0 Scientific & Systems Hardening

## 1. Objective
Harden 3HM (`sf-core`) for academic peer review (InCo / UdelaR), CERN Zenodo DOI archival, and Hacker News / NLnet Foundation evaluation. Sanitize all terminology to rigorous scientific standards, implement a deterministic pre-segmentation `InputNormalizer` (Unicode NFKC, Cyrillic/Greek homoglyph mapping, zero-width stripping, Base64 payload inspection), introduce sequential clause early-exit evaluation with disaggregated latency telemetry, expand public benchmark evaluation in `sf-bench` (SCPB-220 + OOS/Adversarial Injections ROC/FPR), create `.zenodo.json`, and overhaul `README.md`.

## 2. Invariants & Constraints
- **Canonical Toolchain**: Exclusive use of `cargo` in Rust and `pnpm` in `frontend/`.
- **Zero Warnings**: `-D warnings` on Clippy, zero rustc warnings, zero linter warnings.
- **Zero Placeholders**: No `TODO`, `unimplemented!()`, or mock stubs in production paths.
- **Numerical Parity**: 0 ULP IEEE 754 `binary32` cross-architecture determinism in `sf-kernels`.
- **Exclusive Authorship**: Sole author and collaborator in Git commits is `hbauzan` (`Héctor Andrés Bauzán Saavedra` <`hbauzan@gmail.com`>). No AI or bot co-authorship trailers.

## 3. Tracer Bullet Slices
- [x] **Tracer Bullet 1 (Terminology Sanitization)**: Transition `Rompepepe` to `SCPB-220` (`Sub-Clause Piggybacking Benchmark`), `Spectral Quorum` to `Subspace Coordinate Quorum (K-of-D L∞ Gate)`, universal noise dimensions to `Anisotropic Rogue Dimensions (Timkey & van Schijndel, 2021)`, domain locks to `55 Pairwise OvO Cross-Lingual Subspace Masks`, and embedding space to `1024D Contrastive Embedding Manifold ($S^{1023} \subset \mathbb{R}^{1024}$)` with deterministic IEEE 754 binary32 evaluation.
- [x] **Tracer Bullet 2 (Pre-Segmentation Input Normalizer)**: Implement `crates/sf-proxy/src/normalizer.rs` performing NFKC normalization, Cyrillic/Greek homoglyph mapping, stripping invisible control characters (`\u{200B}`, `\u{200C}`, `\u{200D}`, `\u{2060}`, `\u{FEFF}`, `\u{00AD}`), and high-entropy Base64 payload extraction and decoding. Verified by unit and integration tests.
- [x] **Tracer Bullet 3 (Sequential Early-Exit & Disaggregated Telemetry)**: Update `cascade.rs`, `chat_api.rs`, `handler.rs`, and `sf-ui/src/chat.rs` to short-circuit multi-clause evaluation at first failing clause, recording `clauses_skipped`. Expose disaggregated metrics (`normalizer_segmenter_us`, `embedding_inference_ms`, `simd_gate_kernel_us`, `total_pipeline_ms`) in JSON bodies and `x-sf-*` headers. Update `frontend/` types and `BreachCard.tsx`.
- [x] **Tracer Bullet 4 (Public Benchmark Metrics in `sf-bench`)**: Implement Suite 1 (`SCPB-220`) and Suite 2 (In-Domain FPR vs OOS/Adversarial Injection Recall + 1,000 RPS SIMD latency histogram). Add `tools/fetch_public_benchmarks.py` and configure `cargo run --release -p sf-bench` to generate reproducible Markdown reports offline out-of-the-box.
- [x] **Tracer Bullet 5 (CERN Zenodo DOI & Scientific README)**: Author root `.zenodo.json` metadata file. Overhaul `README.md` with DNPI Nº 226 badge, Zenodo DOI badge, cosine dilution mathematical formulation, Mahalanobis vs Strict $\ell_\infty$ vs 3HM comparison, Timkey citation, disaggregated benchmarks table, and operational threat model.
- [x] **Tracer Bullet 6 (Full Verification & Task Logging)**: Verify `cargo fmt`, `cargo clippy`, `cargo test`, `sf-bench` release execution, and frontend vitest/lint suites. Present Approval Gate.
