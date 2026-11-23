# EXECUTION ROADMAP: `fhv1_1` PHASE 0 1,024D X-RAY (`1A`/`1B`) & PHASE 2 OFFLINE REPLAY SIMULATOR (`2A`/`2B` UNDER `3A`) (`TASK-012`)

> **Single Source of Truth**: Self-contained I+D specification for `TASK-012`.  
> **Baseline**: `main @ 4536aaa30e521fbf70baac9c84507deef40d34c5` (post-`TASK-011` merge, containing `reports/fhv1_task011_empirical_report.md`)  
> **Branch**: `feat/fhv1-1-xray-offline-replay`  
> **Task Governance**: `TASK-012` in [`TASKS.md`](../TASKS.md) (`fabrica-de-software` + `transparent-dev-protocol`)  
> **Delivery Fence**: 100% offline I+D (`tools/` + `reports/` + `roadmap/` + `TASKS.md` + untracked `data/fhv1_1_research/` & `audit_fhv1_1_id_bundle.md`). **ZERO** changes to production core (`crates/`, `frontend/`, `Cargo.toml`, `manifest.json`, `frontend/package.json`, `architecture_spec.md`, `CHANGELOG.md`). 1 fresh coding sub-agent + 1 atomic local commit per Vertical Slice (`Slices 1..4`). **HALT** at human Approval Gate before `git push` or `git merge --no-ff`.

---

## 1. Ground Truth & Non-Negotiable Invariants

### 1.1 Production Core & Package Freeze
* **Package Version Freeze**: `0.2.1` unchanged across `Cargo.toml`, `manifest.json`, and `frontend/package.json`.
* **Zero Core Edits**: `crates/`, `frontend/`, `architecture_spec.md`, and `CHANGELOG.md` remain untouched (`git diff --stat main..HEAD` must show 0 diff rows for all production paths).
* **Canonical Toolchains**:
  * Python (`tools/`): `uv run --script ...` exclusively with PEP 723 (`# /// script`) headers. Zero `pip`, zero `npm`.
  * Non-regression verification: `cargo` (`1.94.1`) and `pnpm` (`11.8.0`).
* **Authorship, Lexical & Staging Rules**:
  * Sole Git author: `Héctor Andrés Bauzán Saavedra <hbauzan@gmail.com>` (`hbauzan`), zero `Co-authored-by:` trailers.
  * Zero mentions of external AI assistants, bots, coding-agent brands, editors, or IDEs anywhere.
  * Explicit staging only (never `git add -A`). Never stage `.env`, `data/`, `repomix-output.xml`, `audit_*`, `.xlsx`, or `.parquet`.

### 1.2 Locked Architectural Decisions (`TASK-012`)
* **Axis 1 (`1A` → `1B`)**:
  * `1A`: Contrast `python-v1` vs `receta-v1` purely from read-only `data/sf-lancedb/` data.
  * `1B`: Contrast `python-v1` vs a leak-free 250-doc EN non-Python background corpus, and `receta-v1` vs a leak-free 250-doc ES non-Receta background corpus (plus `clause_opt2c` chunks), embedded offline via `HF_HUB_OFFLINE=1 tools/bge_m3_mps_server.py` (`127.0.0.1:8080`, Metal FP32, clean PID teardown) to isolate pure domain vs language EN/ES dimensions.
* **Axis 2 (`2A` + `2B` Side-by-Side)**:
  * `2A`: Pure composite score `Score = w1·F1 + w2·F2 + w3·F3 >= threshold`.
  * `2B`: Composite score + fail-closed hard Kill-Switch (`K1: max_excess_sigma`, `K2: max_neg_sensor_z`, and optional `K3: ||x||_2` deviation if justified by `1A/1B` diagnostics) with full forensic telemetry on exclusive catches vs added false rejections.
* **Axis 3 (`3A` Uncapped I+D + Informative `cap=24`)**:
  * Evaluate `clauses` without chunk cap to measure the true algorithmic ceiling; separately log non-limiting telemetry for a `24`-clause cap (`8 head + 8 middle + 8 tail`, always preserving Base64 payloads).
* **Spatial Base**: Primary space **`normalize=true`** (`python-v1-42270ed8870d`, `receta-v1-5c820b9b36b3`) across all **`1,024` dimensions** (`use_rogue_mask=false`), plus auxiliary check on pre-L2 norm `||x||_2` from `v2` (`python-v2-42270ed8870d`, `receta-v2-5c820b9b36b3`).
* **IEEE 754 `Float64` (`RFC-003`) & Anti-Leakage Discipline**:
  * All numerical computations use `np.float64`.
  * Strictly zero holdout leakage (`data/fhv1_benchmarks/{python,receta}.jsonl`, `tools/fhv1_benchmark_banks.json`, `crates/sf-bench/src/suite2_prompts.json`) in box calibration, Top-K dimension selection, or `1B` background corpus construction.
  * Every main simulator result reports `ROC-AUC`, `PR-AUC`, `CAL_ONLY` (calibration-only thresholds), `5-Fold Stratified OOF CV`, and `[ORACLE_UPPER_BOUND]` (explicitly labeled in-sample ceiling).

---

## 2. Pre-Run `data/sf-lancedb/` Read-Only Integrity Snapshot

`data/sf-lancedb/` is strictly **READ-ONLY** throughout `TASK-012` (never invoke `./setup.sh`, never mutate or compact any LanceDB table).

### 2.1 Table Row Counts & Active Profiles (`main @ 4536aaa`)
* `domain_hypercubes`: **`66`** rows
* `fhv1_profiles`: **`4`** rows (`python-v1-42270ed8870d` [norm=True, 36,494], `receta-v1-5c820b9b36b3` [norm=True, 38,235], `python-v2-42270ed8870d` [norm=False, 36,494], `receta-v2-5c820b9b36b3` [norm=False, 38,235])
* `fhv1_calibration_samples`: **`149,458`** rows (`36,494×2 + 38,235×2`)
* `fhv1_benchmark_runs`: **`24`** rows
* `fhv1_audit_traces`: **`164,939`** rows (`164,924` `BENCHMARK` rows across `9,600` prompt-scoped `trace_id`s + `15` `REALTIME_CHAT`/`REALTIME_LAB` rows)

### 2.2 `domain_hypercubes.lance` Pre-Run SHA-256 Baseline (19 Files)
```text
632466dd30fcd86df791201d9e3e87673f90adf7d85fadbd74954cf100d4b5c5  data/sf-lancedb/domain_hypercubes.lance/_transactions/0-274897fa-cd1e-45c5-9829-e7188513de19.txn
de426e830a02ec34f1378b576a5b77b2d9c74e24abfdc966e7e056038e777482  data/sf-lancedb/domain_hypercubes.lance/_transactions/1-a65ed658-6565-42b2-9982-dcf389fc0f36.txn
16ee2648e242ca680c8b2e93b62f82b95dba1969e66d1c2a3c306b5a83d77429  data/sf-lancedb/domain_hypercubes.lance/_transactions/2-61cb3773-5ecf-4cbb-a5fd-92b5f0914556.txn
2050c7f3368e924f964456d83fa0421aaf1b18681e957c99e2c28ab822c0c13f  data/sf-lancedb/domain_hypercubes.lance/_transactions/3-ea5a03c9-80ce-4fca-afc9-a67e6f1df8ea.txn
ab52f6e545857730d9c61398b0db60cb565c70a0c335bfa2c3b9c2dd6ae80ae5  data/sf-lancedb/domain_hypercubes.lance/_transactions/4-dba9f33a-65af-406b-af38-ae34e6f85b79.txn
46270bb923de8356fbd5acbe4ab24b2b28c9bf3a86d1666de1b4d5d5701a1578  data/sf-lancedb/domain_hypercubes.lance/_transactions/5-69d7a800-beb0-4caf-b0e2-4f438b22a94d.txn
74dbca8c828dedc9d0fc0e2bceee6f07cffb2047f01a945db043613967bf0a1a  data/sf-lancedb/domain_hypercubes.lance/_versions/18446744073709551609.manifest
4ae6d01694eda78bb5eaf8747fb3e9eb12a3f8d41ed17ca99a1dd52b4497aa0e  data/sf-lancedb/domain_hypercubes.lance/_versions/18446744073709551610.manifest
eb36883c6fd26430abfc6d75b618e7019a7592f41c1ccebc13bc15f3509de307  data/sf-lancedb/domain_hypercubes.lance/_versions/18446744073709551611.manifest
6af274a0465c5acfe060e3844423cd4f5292391c36392371a97f7fdadaad8688  data/sf-lancedb/domain_hypercubes.lance/_versions/18446744073709551612.manifest
ed25aad11209393b6edbc191bdf5e4b2a69b67dcd865c3919a8e1ad7ab91d3aa  data/sf-lancedb/domain_hypercubes.lance/_versions/18446744073709551613.manifest
c750de7b9a777b65425324c15e9e4af8f56267c7da188015ead64cf0feb50e0b  data/sf-lancedb/domain_hypercubes.lance/_versions/18446744073709551614.manifest
1e1901b2658bbbb3512c4e8867974632a030c38adb83ab4b5e3b0b39e6705ac2  data/sf-lancedb/domain_hypercubes.lance/_versions/latest_version_hint.json
7bd5186eaac43baa2c195476eb74c2bcf7326b7bca4ebaf66246ecb408c6bafb  data/sf-lancedb/domain_hypercubes.lance/data/011010010000011001101011d0ffc74ccb937e8218f9f4b05d.lance
eb28f3a7d0d3812ff0dd2bb1e47ae9310d746a544b2d3d4f07d5f97b216626e8  data/sf-lancedb/domain_hypercubes.lance/data/1010110100111010001011106bf2bc404c87d1443b9a2168cf.lance
248121eca39f44369c966fd2e2a82dc670b09918c4b865b44266c30899b022a3  data/sf-lancedb/domain_hypercubes.lance/data/1101001001010010000011110c1e954290b975e18a2915f249.lance
0328413d9c98f00304b911a99e8d570d0aa06dd602ad00a50c01a17615269320  data/sf-lancedb/domain_hypercubes.lance/data/1101100110111000110110005b392b4e22ad3262871e5ff5c6.lance
91c751ebda14a40048806df7ccc6165a861f1acea20947a4b65facc85581e1e6  data/sf-lancedb/domain_hypercubes.lance/data/111000111010000011010000dbf9f74dd7994d37a969480e05.lance
6bc02e9bc838fd16ef5305377c1b4f7ee68c662afa41eedb1386dfdb3115e6d9  data/sf-lancedb/domain_hypercubes.lance/data/1110100011011001101100004ca69741899dc56c761138e5b9.lance
```

---

## 3. Vertical Slices & Exit Criteria

### Slice 0 — Roadmap & Governance (Architect Direct)
* **Deliverables**: `roadmap/fhv1-1-xray-offline-replay.roadmap.md`, `TASKS.md` (`TASK-012` `IN_PROGRESS`, `active_slice: "Slice 1"`).
* **Gate**: `agent.sh validate --task-file TASKS.md` + atomic local commit.

### Slice 1 (Fresh Sub-Agent #1) — Phase 0 `1A`: Read-Only 1,024D X-Ray (`python-v1` vs `receta-v1`)
* **Deliverables**: `tools/fhv1_1_xray.py` (`--mode 1a`, PEP 723, `np.float64`), `tools/test_fhv1_1_xray.py`.
* **Scope**:
  1. Box inflation quantification by granularity (`full_doc`, `clause_opt2c`, `pooled`): exact `min`, `max`, `mean`, `std_dev` (`ddof=1` & `ddof=0`), `variance`, `span`, plus distribution (`min/p25/p50/p75/p90/max`) of `span_pooled / span_full_doc`, `span_pooled / span_clause`, `std_pooled / std_full_doc`.
  2. Mutually exclusive 4-bucket classification (`BACKBONE_ENGINE`, `FIRM_DOMAIN_ANCHOR`, `NEGATIVE_INTRUDER_SENSOR`, `DEAD_OR_OSCILLATOR`) on both `full_doc` and `clause_opt2c` for `python-v1` vs `receta-v1`, emitting counts, Top-20 per bucket, and `/tmp/fhv1_1_id/xray_1a.json`.
  3. Autopsy of the 9 rogue dimensions `[292, 297, 308, 329, 386, 404, 577, 616, 780]`.
  4. Auxiliary pre-L2 norm `||x||_2` check from `v2` traces/calibration (`min/p10/p50/p90/max` by category and `subtype`, plus ROC-AUC of `| ||x||_2 - mean_norm |`).
* **Gate**: `uv run --script tools/test_fhv1_1_xray.py` PASS + `uv run --script tools/fhv1_1_xray.py --mode 1a --out /tmp/fhv1_1_id/xray_1a.json` + atomic local commit.

### Slice 2 (Fresh Sub-Agent #2) — Phase 0 `1B`: Leak-Free Same-Language Background Corpus & `1A` vs `1B` Delta
* **Deliverables**: `tools/fhv1_1_background_corpus.jsonl` (`250` EN non-Python + `250` ES non-Receta = `500` texts across 10+ non-domain topics, realistic lengths, zero template cloning), `tools/test_fhv1_1_background_corpus.py`, `tools/fhv1_1_xray.py --mode 1b`, updated `tools/test_fhv1_1_xray.py`, untracked cache `data/fhv1_1_research/background_embeddings.parquet`.
* **Execution**:
  1. Anti-leak firewall verified against all benchmark/calibration JSONs and JSONLs (`0` duplicates, strict EN/ES purity, `0` 5+ word window overlaps).
  2. Non-interactive `HF_HUB_OFFLINE=1 uv run --script tools/bge_m3_mps_server.py` (`127.0.0.1:8080`, `trap cleanup EXIT`, `/health` wait, embed `500` `full_doc`s + equivalent `clause_opt2c` chunks with `normalize=true` + optional `normalize=false` norm check, exact PID kill, confirm `PORTS_8080_8088_CLOSED`).
  3. Run `--mode 1b` (`python-v1` vs `bg_en`, `receta-v1` vs `bg_es`) and measure `1A` vs `1B` language delta (Top-`{32, 64, 128, 256}` Jaccard/overlap, Top-64 language dropouts, backbone isolation, negative sensors by mean vs variance/RMS intruder ratio).
* **Gate**: `uv run --script tools/test_fhv1_1_background_corpus.py` & `uv run --script tools/test_fhv1_1_xray.py` PASS + `PORTS_8080_8088_CLOSED` + atomic local commit.

### Slice 3 (Fresh Sub-Agent #3) — Phase 2: Offline Replay Simulator `fhv1_1`
* **Deliverables**: `tools/fhv1_1_replay_sim.py` (PEP 723, `np.float64`), `tools/test_fhv1_1_replay_sim.py`.
* **Scope**:
  1. Granularity-decoupled statistics (`full_doc` vs `clause_opt2c`) vs `pooled`, plus empirical `[min, max]` vs `sigma-trimmed` (`mean ± 3σ`).
  2. Normalized `[0.0, 1.0]` factors `F1` (soft containment), `F2` (`F2_L1` & `F2_L2` diagonal Mahalanobis, 1024D vs 1024D-without-backbone), `F3` (Top-K `1A` vs `1B` anchors + Top-M negative sensors, `K ∈ {32,64,128,256}`, `M ∈ {32,64,128}`), scales fixed purely on calibration data.
  3. Side-by-side `2A` (pure composite) vs `2B` (composite + Kill-Switch `K1`/`K2` + conditional `K3`) with full ablation matrix & Kill-Switch forensic table.
  4. Multi-chunk `3A` rules (`full_only` w/ Base64 fail-closed; `clauses` uncapped `clauses_hard_kill` & `clauses_dual_zone`) + informative `cap=24` (`8+8+8` + Base64) telemetry.
  5. Strict anti-overfitting reporting on every main row: `ROC-AUC`, `PR-AUC`, `CAL_ONLY`, `5-Fold Stratified OOF CV`, and `[ORACLE_UPPER_BOUND]`, plus per-quadrant and per-`subtype` comparison vs `TASK-011`.
* **Gate**: `uv run --script tools/test_fhv1_1_replay_sim.py` PASS + `uv run --script tools/fhv1_1_replay_sim.py --xray-1a /tmp/fhv1_1_id/xray_1a.json --xray-1b /tmp/fhv1_1_id/xray_1b.json --out /tmp/fhv1_1_id/replay_results.json` + atomic local commit.

### Slice 4 (Fresh Sub-Agent #4) — Scientific Report, Full Gates & Handoff Bundle
* **Deliverables**: `reports/fhv1_1_xray_and_replay_report.md` (tracked), `TASKS.md` (`DONE`), `audit_fhv1_1_id_bundle.md` (untracked, NEVER staged).
* **Exit Criteria**:
  1. Complete high-density report with objective `GO / NO-GO / ADJUST` verdict for `TASK-013`.
  2. Full Python (`6` test scripts), Rust (`cargo fmt --check`, `cargo clippy`, `cargo test --workspace`), and Frontend (`pnpm lint`, `pnpm test`) non-regression passes.
  3. `git diff --stat main..HEAD` confirms 0 changes in production paths; `domain_hypercubes.lance` 19 SHA-256 files and 5 table row counts 100% identical; `PORTS_8080_8088_CLOSED`; sole authorship `hbauzan <hbauzan@gmail.com>`; 0 lexical/staging violations.
  4. `agent.sh validate` + `agent.sh notify` + atomic Slice 4 commit + **HALT** at Approval Gate.
