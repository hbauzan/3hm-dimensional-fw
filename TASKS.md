---
task_id: "TASK-014"
status: "IN_PROGRESS"
assigned_architect: "maximum-architect-agent"
protocol: "transparent-dev-protocol"
title: "fhv1_1 I+D v3: full-1024D directional dials and auto-calibrated lexical guardrail"
created_at: "2026-11-23T11:30:00-03:00"
active_slice: "Slice 2"
---

# TASK-014: `fhv1_1` I+D v3 — Full-1,024D Directional Dials, Auto-Calibrated Lexical/Symbol Guardrail, 1,200-Doc `1B`

## 1. Objective
Execute 100% offline R&D (`tools/`, `reports/`, `roadmap/`, `TASKS.md` only) per [`roadmap/fhv1-1-id-v3-full1024d-and-lexical-guard.roadmap.md`](roadmap/fhv1-1-id-v3-full1024d-and-lexical-guard.roadmap.md) on branch `feat/fhv1-1-id-v3-full1024d-and-lexical-guard` cut from `main @ 89f1cba2789ec2f0e54e149cc987fb5de8c15c6c` (both `a89b20d` and `6a0831a` are ancestors of `main`). Expand the background corpus to `1,200` documents with a `structural_symbol_noise` stratum, add an auto-calibrated character/symbol/connector guardrail, replay all-1,024D directional scorers with swept guardrails under document-level `CAL_ONLY` and nested `5×5` OOF, publish `reports/fhv1_1_id_v3_report.md`, and halt at the human Approval Gate.

## 2. Invariants & Constraints
- **Zero Production Edits & Version Freeze**: NEVER modify `crates/`, `frontend/`, `Cargo.toml`, `manifest.json`, `frontend/package.json`, `architecture_spec.md`, or `CHANGELOG.md`. Package frozen at `0.2.1`.
- **LanceDB Strict Read-Only Fence**: NEVER write, delete, or compact `data/sf-lancedb/`. Phase-0 counts: `domain_hypercubes=66`, `fhv1_profiles=4`, `fhv1_calibration_samples=149458`, `fhv1_benchmark_runs=24`, `fhv1_audit_traces=164939`. Nineteen SHA-256 files of `domain_hypercubes.lance` match `roadmap/fhv1-task-011-hardening-falsification.roadmap.md` §2 (`DIFF_IDENTICAL=0`).
- **Canonical Toolchains**: `uv run --offline --script` (PEP 723, `np.float64`) for Python. Export `UV_CACHE_DIR=/Users/hbauzan/.cache/uv` before `uv` (the process environment may point that variable at an empty temporary cache). `cargo` only with `CARGO_TARGET_DIR=/Users/hbauzan/treepwood/3hm-dimentional-fw/target`. `pnpm --dir frontend` only at the Slice 4 gate. Zero `pip`, zero `npm`, zero `./setup.sh`.
- **Offline Loopback**: `HF_HUB_OFFLINE=1`. Loopback `http://127.0.0.1:8080` only for Slice 1 embeddings. `trap` cleanup on `EXIT`. Confirm `PORTS_8080_8088_CLOSED` afterward. Zero reads of `.env`. Do not touch `~/.cache/huggingface/` except by the offline embedder process reading the already cached weights.
- **Locked Science**: `normalize=true` always for primary scorers. Every `F_dir1024` variant evaluates all `1,024` coordinates with `w_d >= w_floor > 0`. Standalone `fhv1_1` only. No short-query routing to `clause_opt2c`.
- **Anti-Leakage**: Thresholds and recipe selection that are reported as `CAL_ONLY` or nested OOF never see holdout labels. `[ORACLE_UPPER_BOUND]` stays labeled and separate.
- **Authorship, Lexical & Staging Fence**: Sole author and committer `Héctor Andrés Bauzán Saavedra <hbauzan@gmail.com>`. Zero `Co-authored-by:` trailers. Zero mentions of external assistants, bots, agent brands, editors, IDEs, or external commercial model brands. Explicit `git add` of named paths. Never stage `.env`, `data/`, `audit_*`, `repomix-output.xml`, `.xlsx`, or `.parquet`.

## 3. Tracer Bullet Slices
- [x] **Slice 0**: Phase-0 integrity audit passed (`12,074,392` KiB free, LanceDB `DIFF_IDENTICAL=0`, Python `103/103`, cargo `173/173`, frontend `70/70`). Branch cut from `main @ 89f1cba`. Roadmap and this task file registered.
- [x] **Slice 1**: Append `200` `structural_symbol_noise` docs, refresh `background_embeddings_1200.parquet` at `normalize=true`, extend contrast presets, delete `background_embeddings_1k.parquet` only after verification.
- [ ] **Slice 2**: Auto-calibrated character, non-letter, and connector guardrail in `tools/fhv1_1_lexical_profile.py` with `>= 26` tests.
- [ ] **Slice 3**: `--mode v3` all-1,024D directional scorers, swept `F2_L2` / `Tail-Z` / `S_struct` hooks, nested OOF and document-level `CAL_ONLY`, `>= 30` tests, JSON under `/tmp/fhv1_1_id_v3/`.
- [ ] **Slice 4**: Report from those JSON files, cleanup, full gates, `TASK-014` `DONE`, untracked audit bundle, halt before push or merge.
