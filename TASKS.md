---
task_id: "TASK-015"
status: "IN_PROGRESS"
assigned_architect: "maximum-architect-agent"
protocol: "transparent-dev-protocol"
title: "fhv1_1 I+D v4: hardening pre-Rust, near-OOD axis, clause_cap DoS, N_cal curve"
created_at: "2026-11-23T20:05:00-03:00"
active_slice: "Slice 0"
---

# TASK-015: `fhv1_1` I+D v4 — Hardening Pre-Rust, Eje 2 Near-OOD, `clause_cap` DoS, Curva `N_cal`

## 1. Objective
Execute 100% offline R&D (`tools/`, `reports/`, `roadmap/`, `TASKS.md` only) per [`roadmap/fhv1-1-id-v4-hardening-and-sample-curve.roadmap.md`](roadmap/fhv1-1-id-v4-hardening-and-sample-curve.roadmap.md) on branch `feat/fhv1-1-id-v4-hardening-and-sample-curve` cut from `main @ 5bcab5f8bd630720809f0a8accc7d62150c851dc` (already contains the merged `TASK-014`). Repair the three verified `S_struct` bugs, implement dual-axis v4 replay with 5-fold calibration OOF and `clause_cap`, run the `N_cal` volume curve, publish `reports/fhv1_1_id_v4_report.md`, and halt at the human Approval Gate. Do not execute the `TASK-016` backlog.

## 2. Invariants & Constraints
- **Zero Production Edits & Version Freeze**: NEVER modify `crates/`, `frontend/`, `Cargo.toml`, `manifest.json`, `frontend/package.json`, `architecture_spec.md`, or `CHANGELOG.md`. Package frozen at `0.2.1`.
- **LanceDB Strict Read-Only Fence**: NEVER write, delete, or compact `data/sf-lancedb/`. Phase-0 counts: `domain_hypercubes=66`, `fhv1_profiles=4`, `fhv1_calibration_samples=149458`, `fhv1_benchmark_runs=24`, `fhv1_audit_traces=164939`. Nineteen SHA-256 files of `domain_hypercubes.lance` match `roadmap/fhv1-task-011-hardening-falsification.roadmap.md` §2 (`DIFF_IDENTICAL=0`, `HASH_CHANGED_AFTER_COUNT=0`).
- **Canonical Toolchains**: `uv run --offline --script` (PEP 723, `np.float64`) for Python. Export `UV_CACHE_DIR=/Users/hbauzan/.cache/uv` before `uv`. `cargo` only with `CARGO_TARGET_DIR=/Users/hbauzan/treepwood/3hm-dimentional-fw/target`. `pnpm --dir frontend` only at Phase-0 and Slice 4. Zero `pip`, zero `npm`, zero `./setup.sh`.
- **Offline Loopback**: `HF_HUB_OFFLINE=1`. Loopback `http://127.0.0.1:8080` only for flooding latency and description embeddings. `trap` cleanup on `EXIT`. Confirm `PORTS_8080_8088_CLOSED` afterward. Zero reads of `.env`.
- **Locked Science**: `normalize=true` always for primary scorers. Eje 1 uses `1B_base_tech` only; Eje 2 uses pure `near_ood_neighbor`. All calibration scores for thresholds use 5-fold OOF. Compact recipe catalog `<= 12`. Standalone `fhv1_1` only; production scorer stays OFF.
- **Anti-Leakage**: Thresholds and recipe selection that are reported as `CAL_ONLY` or nested OOF never see holdout labels. `[ORACLE_UPPER_BOUND]` stays labeled and separate.
- **Authorship, Lexical & Staging Fence**: Sole author and committer `Héctor Andrés Bauzán Saavedra <hbauzan@gmail.com>`. Zero `Co-authored-by:` trailers. Zero mentions of external assistants, bots, agent brands, editors, IDEs, or external commercial model brands. Explicit `git add` of named paths. Never stage `.env`, `data/`, `audit_*`, `repomix-output.xml`, `.xlsx`, or `.parquet`.
- **HALT**: After Slice 4, stop before any `git merge --no-ff` or `git push`.

## 3. Tracer Bullet Slices
- [x] **Slice 0**: `TASK-014` closure verified on `main @ 5bcab5f` (already pushed; `cargo clean` noop; `audit_task014_code.txt` absent). Phase-0 passed (`19,229,584` KiB free post-cargo, LanceDB `DIFF_IDENTICAL=0` / `HASH_CHANGED_AFTER_COUNT=0`, parquet `8,147` / `UNIT_1E-5 PASS`, Python `192/192`, cargo `173/173`, frontend `70/70`). Branch cut. Roadmap and this task file registered.
- [ ] **Slice 1**: Repair unidirectional `S_struct` channels, Latin letters out of `symbol_ratio`, and rare-rate smoothing in `tools/fhv1_1_lexical_profile.py` with `>= 44` tests.
- [ ] **Slice 2**: `--mode v4` dual-axis engine, 5-fold cal OOF, compact recipe catalog, `clause_cap` + real flooding latency, `>= 32` tests.
- [ ] **Slice 3**: `N_cal` volume curve (`1` description .. `600`) and full v4 JSON under `/tmp/fhv1_1_id_v4/`.
- [ ] **Slice 4**: Report from those JSON files, cleanup, full gates, `TASK-015` `DONE`, untracked audit bundle, halt before push or merge.
