---
task_id: "TASK-013"
status: "DONE"
assigned_architect: "maximum-architect-agent"
protocol: "transparent-dev-protocol"
title: "fhv1_1 I+D v2: 1000-doc 1B, 1024D fine dials, document-level calibration"
created_at: "2026-11-22T18:50:00-03:00"
active_slice: "DONE"
---

# TASK-013: `fhv1_1` I+D v2 — 1,000-doc `1B`, 1,024D Fine Dials, Document-Level Calibration

## 1. Objective
Execute 100% offline R&D (`tools/`, `reports/`, `roadmap/`, `TASKS.md` only — zero production core edits) per [`roadmap/fhv1-1-id-v2-fine-dials-and-scale.roadmap.md`](roadmap/fhv1-1-id-v2-fine-dials-and-scale.roadmap.md) on branch `feat/fhv1-1-id-v2-fine-dials-and-scale` (from `HEAD @ a89b20d`, because `main @ 4536aaa` does not contain `TASK-012`) to: (a) replace the 500-doc background with `1,000` leak-free docs (`500` EN + `500` ES, three strata) and a `normalize=true` embedding cache; (b) label all `1,024` coordinates (language sweet spot, six buckets, polarity-flip dials, hypothesis `2.3`); (c) replay `fhv1_1` with `Tail-Z`, `F_polarity`, optional language-lock, document-level `CAL_ONLY`, short-query routing, and a `long_context_flooding` closure under repeated OOF and bootstrap CIs; and (d) halt at the human Approval Gate.

## 2. Invariants & Constraints
- **Zero Production Edits & Version Freeze**: NEVER modify `crates/`, `frontend/`, `Cargo.toml`, `manifest.json`, `frontend/package.json`, `architecture_spec.md`, or `CHANGELOG.md`. Package frozen at `0.2.1`.
- **LanceDB Strict Read-Only Fence**: NEVER write, delete, or compact `data/sf-lancedb/`. Pre-run counts: `domain_hypercubes=66`, `fhv1_profiles=4`, `fhv1_calibration_samples=149458`, `fhv1_benchmark_runs=24`, `fhv1_audit_traces=164939`. Nineteen SHA-256 files of `domain_hypercubes.lance` are the baseline in the roadmap.
- **Canonical Toolchains**: `uv run --offline --script` (PEP 723, `np.float64`) for Python. `cargo` and `pnpm` only at the Slice 4 non-regression gate. Zero `pip`, zero `npm`.
- **Offline Loopback & Process Hygiene**: NEVER invoke `./setup.sh`, never read `.env`, zero internet calls (`HF_HUB_OFFLINE=1`). Manage `tools/bge_m3_mps_server.py` (`127.0.0.1:8080`) with `trap cleanup EXIT` and exact PID termination; confirm `PORTS_8080_8088_CLOSED`.
- **1,024D `normalize=true`**: Scoring uses every coordinate on the unit sphere. `normalize=false` exists only as an in-memory Prueba A comparison over the `600` `general_prose` docs, persisted solely at `/tmp/fhv1_1_id_v2/bg_general_unnorm.parquet` until Slice 2 deletes it.
- **Document bundles**: `source_ref` is the policy id, not a document id. Group each of the `600` `full_doc` rows with the `clause_opt2c` rows in the following `sample_id` index interval.
- **Anti-Leakage & Scientific Rigor**: Zero overlap with the `800` holdout prompts and the other corpora named in the roadmap. Report `CAL_ONLY` (document-level), `5×5` repeated stratified OOF (`mean ± std`), bootstrap `95%` CI (`1,000`), `ROC-AUC`, `PR-AUC`, and label any `[ORACLE_UPPER_BOUND]`.
- **Authorship, Lexical & Staging Fence**: Sole author `Héctor Andrés Bauzán Saavedra <hbauzan@gmail.com>` (`hbauzan`), zero coauthor trailers, zero mentions of external assistants, bots, agent brands, editors, or IDEs. Never stage `data/`, `.env`, `repomix-output.xml`, `audit_*`, `.xlsx`, or `.parquet`.

## 3. Tracer Bullet Slices
- [x] **Slice 0**: Disk audit (`14.23 GiB` free before, `1,483,436 KB` authorized delete, `15.81 GiB` free after), branch from `a89b20d` because `TASK-012` is not on `main`, roadmap, and `TASKS.md` governance.
- [x] **Slice 1**: 1,000-doc three-stratum background is on disk as `background_embeddings_1k.parquet` (`du -sk` 48,188 KiB) and the old `background_embeddings.parquet` was deleted at 25,300 KiB.
- [x] **Slice 2**: `--mode v2` labeled all 1,024 coordinates, primary `LOCALE_LANG_DIMS` is empty, and `bg_general_unnorm.parquet` was deleted after `xray_v2.json` was written.
- [x] **Slice 3**: `--mode v2` replay stored Tail-Z, `F_polarity`, language-lock, document-level calibration, short-query, and flooding, with 5×5 and 1,000-resample bootstrap on the four winning cells.
- [x] **Slice 4**: `reports/fhv1_1_id_v2_report.md` records those measurements, `/tmp/fhv1_1_id_v2` is removed, and this task is `DONE`; the audit bundle stays untracked.
