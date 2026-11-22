---
task_id: "TASK-011"
status: "IN_PROGRESS"
assigned_architect: "maximum-architect-agent"
protocol: "transparent-dev-protocol"
title: "fhv1 Hardening, Leak-Free Scientific Benchmark, LLM Corpus Augmentation (1B) & Empirical Falsification Re-Run"
created_at: "2026-11-21T22:45:00-03:00"
active_slice: "7"
---

# TASK-011: `fhv1` Hardening, Leak-Free Scientific Benchmark, LLM Corpus Augmentation (`1B`) & Empirical Falsification Re-Run

## 1. Objective
Close all P0 (3), P1 (4), and P2 (6) defects identified in `main @ f239f19` per [`roadmap/fhv1-task-011-hardening-falsification.roadmap.md`](roadmap/fhv1-task-011-hardening-falsification.roadmap.md) on branch `feat/fhv1-task-011-hardening-falsification`, execute live `1B` LLM corpus augmentation and the clean 24-run `normalize=true` vs `normalize=false` empirical falsification campaign on `BAAI/bge-m3` (FP32 MPS), certify full live Playwright E2E + 0-ULP `.xlsx`/`.csv`/`.parquet` export parity, and halt at the human Approval Gate with `audit_task011_evidence.md`.

## 2. Invariants & Constraints
- **Canonical Toolchains**: `cargo` (`1.94.1`), `pnpm` (`11.8.0` in `frontend/`), `uv run --script` (`tools/`). Zero mixing.
- **Sole Authorship & Lexical Hygiene**: `Héctor Andrés Bauzán Saavedra <hbauzan@gmail.com>` (`hbauzan`), zero `Co-authored-by:`, zero mentions of external AI assistants, bots, coding-agent brands, editors, or IDEs anywhere.
- **LanceDB & Version Fence**: NEVER delete, overwrite, or re-seed `data/sf-lancedb/domain_hypercubes.lance` (`66` rows, SHA-256 verified pre/post). Freeze `0.2.1` in `Cargo.toml`, `manifest.json`, and `frontend/package.json`.
- **Non-Interactive Services & Staging Fence**: NEVER run `./setup.sh`. Never echo `.env` secrets or stage `.env`, `data/`, `repomix-output.xml`, `audit_*`, or `.xlsx` files.
- **Slice Discipline**: Strictly 1 fresh coding agent and 1 atomic local commit per Vertical Tracer Bullet Slice (`1..7`). Halt after Slice 7 before `git push` or `git merge --no-ff`.

## 3. Tracer Bullet Slices
- [x] **Slice 1**: Kernel polarity fail-closed (`P2-13`), ADR-006 `violation_delta` doc lock (`P2-9` / `2B`), LanceDB predicate pushdown without silent `1_000_000` truncation & deterministic pagination (`P2-12`).
- [x] **Slice 2**: `atomic_phrases()` EN/ES stopword & boundary fix (`P0-2`), `FullOnly` Base64 decoded payloads (`P2-10`), default movement metric `"variance"` in Rust (`P2-8`), lossless single-HTTP-call `3hm_plus_fhv1` dual embedder seam removing `promote_f32` (`P1-3`).
- [x] **Slice 3**: Shared evaluation engine in `sf-proxy` with `failed_dims_count_histogram_by_category`, per-category percentiles, and per-subtype counts (`P0-3`), plus full REST `POST /api/v1/fhv1/benchmarks/run` parity & bounded batched embedding (`P1-2`).
- [x] **Slice 4**: Curated offline base corpus `150–300` docs/domain (`1A` / `P0-2`), leak-free 400-prompt/domain 4-quadrant benchmark rebuild with `subtype` metadata & strict leak/language/length validators (`P0-1`), and `augment_fhv1_corpus.py --augment-llm` fail-closed CLI + offline tests (`1B` tooling).
- [x] **Slice 5**: Complete View 3 (`Fhv1BenchmarkExplorer` histogram global/per-category ECharts canvas, 1,024D input vector overlay canvas, lossless drill-down `mean`/`delta_vs_mean`/`norm_pos`, Category/Verdict filters — `P1-1`), default `"variance"` in `Fhv1VarianceStudio.tsx` (`P2-8`), and `fhv1.spec.ts` regex + View 3 E2E assertions (`P2-11`).
- [x] **Slice 6**: Live `1B` `--augment-llm` expansion (`500–1,000+` cached SHA-256 JSONL texts/domain), purge stale `fhv1_*` ONLY (`domain_hypercubes` untouched), calibrate 4 live profiles (`normalize={true,false}`), execute 24-run live matrix, run `verify_fhv1_exports_0ulp.py` across `.xlsx`/`.csv`/`.parquet`/JSON/LanceDB (`P0-3`), write `reports/fhv1_task011_empirical_report.md` (profiles: `python-v1-42270ed8870d`, `python-v2-42270ed8870d`, `receta-v1-5c820b9b36b3`, `receta-v2-5c820b9b36b3`; `24` runs, `9,600` prompt-scoped traces / `164,924` chunk rows, `76,608,512` floats `max_ulp=0`).
- [ ] **Slice 7**: Live Playwright E2E certification (`playground.spec.ts` + expanded `fhv1.spec.ts` on `:8080` + `:8088`, `P1-4`), full workspace gate re-verification, `CHANGELOG.md` `## [Unreleased]` sync (`0.2.1` frozen), `TASKS.md` `DONE` + `agent.sh validate`/`notify`, git/authorship/lexical/LanceDB audit, and untracked `audit_task011_evidence.md`.
