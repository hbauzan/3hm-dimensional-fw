---
task_id: "TASK-012"
status: "DONE"
assigned_architect: "maximum-architect-agent"
protocol: "transparent-dev-protocol"
title: "fhv1_1 Phase 0 1,024D X-Ray (1A/1B) & Phase 2 Offline Replay Simulator (2A/2B under 3A)"
created_at: "2026-11-22T14:23:00-03:00"
active_slice: "DONE"
---

# TASK-012: `fhv1_1` Phase 0 1,024D X-Ray (`1A`/`1B`) & Phase 2 Offline Replay Simulator (`2A`/`2B` under `3A`)

## 1. Objective
Execute 100% offline R&D (`tools/`, `reports/`, `roadmap/`, `TASKS.md` only — zero production core edits) per [`roadmap/fhv1-1-xray-offline-replay.roadmap.md`](roadmap/fhv1-1-xray-offline-replay.roadmap.md) on branch `feat/fhv1-1-xray-offline-replay` (from `main @ 4536aaa`) to: (a) X-ray all 1,024 BGE-M3 dimensions (`1A` cross-domain `python-v1` vs `receta-v1` and `1B` same-language leak-free non-domain background corpora) quantifying box inflation, 4 dimensional buckets, rogue-dim behavior, and pre-L2 norm signal; (b) replay-simulate `fhv1_1` composite scoring (`F1` soft box, `F2` centroid proximity, `F3` Top-K anchors/negative sensors) comparing `2A` vs `2B` (Kill-Switch) and `3A` uncapped clauses (+ informative `cap=24` telemetry) under `ROC-AUC`, `PR-AUC`, `CAL_ONLY`, `5-Fold Stratified OOF CV`, and `[ORACLE_UPPER_BOUND]`; and (c) deliver an objective `GO / NO-GO / ADJUST` verdict in `reports/fhv1_1_xray_and_replay_report.md` before halting at the human Approval Gate.

## 2. Invariants & Constraints
- **Zero Production Edits & Version Freeze**: NEVER modify `crates/`, `frontend/`, `Cargo.toml`, `manifest.json`, `frontend/package.json`, `architecture_spec.md`, or `CHANGELOG.md`. Package frozen at `0.2.1`.
- **LanceDB Strict Read-Only Fence**: NEVER write, delete, or compact `data/sf-lancedb/` (`domain_hypercubes` `66` rows / 19 SHA-256 files + `4` `fhv1_*` tables verified pre/post).
- **Canonical Toolchains**: `uv run --script` (PEP 723, `np.float64`) for Python; `cargo` (`1.94.1`) and `pnpm` (`11.8.0` in `frontend/`) for non-regression gates. Zero `pip`, zero `npm`.
- **Offline Loopback & Process Hygiene**: NEVER invoke `./setup.sh`, never read `.env`, zero internet calls (`HF_HUB_OFFLINE=1`). Manage `tools/bge_m3_mps_server.py` (`127.0.0.1:8080`) with `trap cleanup EXIT` and exact PID termination; confirm `PORTS_8080_8088_CLOSED`.
- **Anti-Leakage & Scientific Rigor**: NEVER leak any of the 400 holdout prompts (`data/fhv1_benchmarks/*.jsonl`, `tools/fhv1_benchmark_banks.json`, `crates/sf-bench/src/suite2_prompts.json`) into calibration, Top-K selection, or `1B` background corpus.
- **Authorship, Lexical & Staging Fence**: Sole author `Héctor Andrés Bauzán Saavedra <hbauzan@gmail.com>` (`hbauzan`), zero `Co-authored-by:`, zero mentions of external AI assistants, bots, coding-agent brands, editors, or IDEs. Never stage `data/`, `.env`, `repomix-output.xml`, `audit_*`, `.xlsx`, or `.parquet`.

## 3. Tracer Bullet Slices
- [x] **Slice 0**: Baseline & LanceDB integrity snapshot (`main @ 4536aaa`), branch `feat/fhv1-1-xray-offline-replay`, `roadmap/fhv1-1-xray-offline-replay.roadmap.md`, and `TASKS.md` governance (`agent.sh validate`) — commit `0353483`.
- [x] **Slice 1**: Phase 0 `1A` read-only 1,024D X-Ray (`tools/fhv1_1_xray.py --mode 1a`, `tools/test_fhv1_1_xray.py`) — granularity box inflation, 4-bucket classification (`full_doc` & `clause_opt2c`), 9-rogue-dim autopsy, and `v2` `||x||_2` pre-L2 norm check — commit `6e14095`.
- [x] **Slice 2**: Phase 0 `1B` leak-free same-language background corpus (`tools/fhv1_1_background_corpus.jsonl`, `tools/test_fhv1_1_background_corpus.py`), offline MPS embedding cache (`data/fhv1_1_research/background_embeddings.parquet`), `--mode 1b` + `1A` vs `1B` language delta — commit `8e60a5a`.
- [x] **Slice 3**: Phase 2 offline replay simulator (`tools/fhv1_1_replay_sim.py`, `tools/test_fhv1_1_replay_sim.py`) — decoupled vs pooled, `F1`/`F2`/`F3`, `1A` vs `1B`, `2A` vs `2B` Kill-Switch telemetry, `3A` uncapped clauses + informative `cap=24`, `ROC-AUC`/`PR-AUC`/`CAL_ONLY`/`5-Fold OOF CV`/`[ORACLE_UPPER_BOUND]`, and per-quadrant/per-`subtype` comparison vs `TASK-011` — commit `480724d`.
- [x] **Slice 4**: Scientific verdict report (`reports/fhv1_1_xray_and_replay_report.md`, `AJUSTAR` -> Conditional `GO`), full Python/Rust/Frontend non-regression gates, LanceDB/port/git/hygiene audits, `TASKS.md` `DONE` + `agent.sh validate`/`notify`, untracked `audit_fhv1_1_id_bundle.md`, and human Approval Gate HALT.
