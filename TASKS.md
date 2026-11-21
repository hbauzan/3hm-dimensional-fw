---
task_id: "TASK-008"
status: "BLOCKED"
assigned_architect: "maximum-architect-agent"
protocol: "transparent-dev-protocol"
title: "Cierre de auditoría y verificación local v0.2.1"
created_at: "2026-11-21T09:29:00-03:00"
---

# TASK-008: Cierre de auditoría y verificación local v0.2.1

## 1. Objective
Close the pending `v0.2.1` audit (handoff §4 points 1–3) on the tagged baseline. Verify the local suite, tabulate productive Mode C recall beside the existing Mode A recall, run Playwright against the documented gateway, and record AVX-512 runtime coverage on this host. Do not design or implement Resonancia Holística Continua or Egress Semantic Amplification.

## 2. Invariants & Constraints
- **Canonical Toolchain**: `cargo` (Rust `1.94.1`), `pnpm` (`frontend/`), `uv` (`tools/`). No second package manager.
- **Scope fence**: do not change productive scoring in `sf-kernels`, the L1/L2/L3 cascade, or `evaluate_pairwise_containment`.
- **Suite 2**: existing Mode A `blocked` / `recall` and both false-positive tiers stay numerically unchanged. Productive Mode C recall is an additional count of `!contained_prod` on attack rows.
- **E2E**: do not weaken or falsify Playwright assertions. Environment or prerequisite fixes only when the contract is unambiguous.
- **AVX-512**: this host is `arm64`. Do not claim an `avx512f` runtime pass.
- **Exclusive Authorship**: `hbauzan` (`Héctor Andrés Bauzán Saavedra` <hbauzan@gmail.com>). No `Co-authored-by` trailers.
- **Delivery**: local commit on this branch, then stop. No push and no merge to `main` before an explicit OK.
- **Out of scope**: vNext engine design.

## 3. Tracer Bullet Slices
- [x] **Slice 1** (`chore/task-008-v021-audit-verification`): `v0.2.1` is `5f9ab4b` on `main`. Local fmt, clippy, `cargo test --workspace` (111 passed), frontend lint/build/test (44 passed), and `cargo run --release -p sf-bench` reproduced the Suite 2 rates in `README.md`. Gate p50 was 0.542 µs. This run's suite2 gate p99 was 0.625 µs; `reports/load_benchmark_mock.json` stores 0.583 µs.
- [x] **Slice 2** (`feat/suite2-recall-prod`): `blocked_prod` / `recall_prod` count attack rows with `!contained_prod`. Existing Mode A fields stay. Measured EN 64/82, ES 90/90, pooled 154/172, equal to Mode A on these fixtures. Clean FPR stays 36/100 vs 31/100.
- [ ] **Slice 3** (`test/playwright-e2e-v021`): `pnpm --dir frontend test:e2e` ran with Vite on `127.0.0.1:5173` and `sf-proxy` on `127.0.0.1:8088`. `SF_EMBEDDER=http` plus `tools/bge_m3_mps_server.py`: 6 passed, 3 failed (python pass, piggyback L2, L2 perilla). `SF_EMBEDDER=mock`: 6 passed, 3 failed (risotto L1, piggyback L2, L2 perilla). Assertions were not changed. Blocked: the preset contract is not satisfied by either embedder, and no unambiguous environment fix was applied.
- [x] **Slice 4** (`docs/avx512-arm64-unverified`): Host is Apple M4 `arm64` with NEON. `avx512f` was not executed. `.github/workflows/ci.yml` records the `#[cfg(target_arch = "x86_64")]` compile gate and that the x86_64 job does not record whether `avx512f` or AVX2+FMA ran.
