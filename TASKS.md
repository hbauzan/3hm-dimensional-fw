---
task_id: "TASK-007"
status: "IN_PROGRESS"
assigned_architect: "maximum-architect-agent"
protocol: "transparent-dev-protocol"
title: "v0.2 Hardening, Empirical Benchmark Truth & Multi-Arch CI"
created_at: "2026-11-13T19:56:00-03:00"
---

# TASK-007: v0.2 Hardening, Empirical Benchmark Truth & Multi-Arch CI

## 1. Objective
Close the verified v0.2 integrity gaps in `sf-storage`, `sf-proxy`, and `sf-ui`, then align seeding, batch-RPC claims, Suite 2, ingress-only scope, version governance, empirical benchmark reports, and multi-arch CI. One tracer bullet per slice. Spec: `roadmap/v0.2-hardening-and-empirical-truth.prompt.md`.

## 2. Invariants & Constraints
- **Canonical Toolchain**: `cargo` for Rust, `pnpm` for `frontend/`, `uv` for `tools/`. No second package manager.
- **Zero Warnings**: `cargo clippy --workspace --all-targets -- -D warnings` and `cargo fmt --check`.
- **Storage**: `domain_hypercubes` keeps `DIM = 1024`, `MAX_TOPK = 128`, and `NoiseBitmask1024` (128 bytes). `top_k_len` round-trips. Mode A scores that length once per coordinate.
- **Kernels**: 0 ULP bitmask parity and `|simd - scalar| < 1e-14` on `f64` cosine. `NaN` fails closed.
- **HTTP**: valid `/v1/chat/completions`, `/api/v1/chat`, and `/api/v1/upstream/env` payloads keep their current JSON/SSE contracts.
- **Scope fence**: no holistic resonance gate and no egress amplification in this task.
- **Exclusive Authorship**: `hbauzan` (`Héctor Andrés Bauzán Saavedra` <hbauzan@gmail.com>). No `Co-authored-by` trailers.
- **Delivery**: local commit on the slice branch, then stop for audit. No push and no merge to `main` before an explicit OK.

## 3. Tracer Bullet Slices
- [ ] **Slice 1** (`fix/slice-01-lancedb-topk`): Persist `top_k_len` and real `corpus_doc_count` / `sha256_manifest`. `append_batch` restores `top_k_len` capped by `min(MAX_TOPK)`, not `DEFAULT_QUORUM_K`. Round-trip `top_k_len = 27` and score 27 unique dims in `eval_mode_a`.
- [ ] **Slice 2** (`fix/slice-02-http-override-validation`): Reject non-finite overrides, `epsilon < 0`, and thresholds outside `[-1.0, 1.0]` with HTTP 400 before dilation.
- [ ] **Slice 3** (`fix/slice-03-sf-ui-clause-inspect`): Embed each inspect clause with its own vector. Skip pairwise containment when the embedder is mock.
- [ ] **Slice 4** (`feat/slice-04-seeding-66-locks`): Hydrate 11 base locks plus 55 pairs. `MockBatchEmbedder` resolves by `domain_id`.
- [ ] **Slice 5** (`docs/slice-05-batch-rpc-truth`): Keep one `embed_batch_f32` call. Document that short-circuit saves CPU/SIMD, not the GPU batch.
- [ ] **Slice 6** (`feat/slice-06-suite2-e2e-and-future-adr`): Run Suite 2 through the real pipeline on 66 locks, unify language, and seed `roadmap/future-holistic-resonance-gate.md` without changing the v0.2 scorer.
- [ ] **Slice 7** (`docs/slice-07-ingress-only-scope`): Mark this version ingress-only. Assign egress semantic amplification to v1.1+.
- [ ] **Slice 8** (`chore/slice-08-version-020-and-roadmaps`): Align `/health` and changelog with `0.2.0`. Archive the two merged prompts.
- [ ] **Slice 9** (`feat/slice-09-truthful-benchmarks-and-readme`): Persist load-benchmark JSON and correct README latency, lock size, cosine normalization, and `ceil(0.10 * 1024) = 103`.
- [ ] **Slice 10** (`ci/slice-10-multiarch-github-actions`): Add `.github/workflows/ci.yml` for `x86_64`, `arm64`, and the frontend only after slices 1–9 are on `main`.
