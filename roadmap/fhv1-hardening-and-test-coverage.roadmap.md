# EXECUTION ROADMAP: `fhv1` HARDENING, REFACTOR & FULL TEST COVERAGE (`TASK-010`)

> **Single Source of Truth**: This document is 100% self-contained for `TASK-010`. Do **not** pull requirements from `roadmap/archived/` or `roadmap/future-holistic-resonance-gate.md`.  
> **Baseline**: `feat/fhv1-hector-filter-v1` @ `e448906` (`TASK-009` completed over `v0.2.1` `main` @ `f2ac3dd`)  
> **Task Governance**: `TASK-010` in [`TASKS.md`](../TASKS.md) (`fabrica-de-software` + `transparent-dev-protocol`)  
> **Git Branch Model**: Continue on **branch `feat/fhv1-hector-filter-v1`**, with **atomic verified commits per Slice (Slices 1–4)**. Stop at the human Approval Gate before `push` or `merge --no-ff` to `main`.

---

## 1. Ground Truth & Non-Negotiable Constraints

### 1.1 Active Baseline & Verification Target
* Current verified suite on `e448906`: Rust (`cargo test --workspace`: `137` passed), Frontend (`oxlint`, `tsc -b && vite build`, Vitest `53` passed / `13` files), Python (`12 + 5 + 3` passed), Playwright (`11` passed: `9` `playground.spec.ts` + `2` `fhv1.spec.ts`).
* Keep package version `0.2.1` across `Cargo.toml`, `manifest.json`, and `frontend/package.json` (any new notes go strictly under `## [Unreleased]` in `CHANGELOG.md`).
* **NEVER delete, overwrite, or re-seed `data/sf-lancedb/domain_hypercubes.lance`**.
* **FORBIDDEN: `./setup.sh`** (interactive `read -p` hangs). Start `:8080` and `:8088` only via the non-interactive §1.3 runbook below with PID cleanup.
* **Canonical Toolchains**: `cargo` (`1.94.1`), `pnpm` (`11.8.0` in `frontend/`), `uv run --script` (`tools/`). Zero mixing.
* **Zero-Rounding `fhv1` & `3HM` Fence**: keep `String(v)` (`formatLosslessF64`) on all `fhv1` surfaces and tests; preserve `.toFixed(4)` in `format.ts` / `BreachCard.tsx` and the 11 protected `Playground` selectors verbatim. Keep `crates/sf-kernels` **0-dep (no `serde`)**.

### 1.2 Protected Frontend Selectors (Verbatim)
Do not alter any selector expected by `Playground.test.tsx`, `BreachCard.test.tsx`, `request.test.ts`, and `playground.spec.ts`:
* `Gateway base`, `POST http://127.0.0.1:8088/api/v1/chat`, `Domain id` (`11` canonical options in `3hm_default`), `Prompt`, `Send|Sending`, `Messages`, `Live tuning` (`w-60`, `overflow-y: auto`), `#root > div` (`h-[100dvh]`, `overflow-hidden`), `Apply overrides`, `L1 cosine threshold`, `L2 clause threshold`, `Quorum K`, `Epsilon`, `.env` controls, and the 4 preset chips (`Python generator`, `Risotto L1`, `Piggyback L2`, `Spectral L3`).

### 1.3 Non-Interactive Live Service Runbook (for Slice 4 Playwright E2E)
```bash
TEI_PID=""; PROXY_PID=""
cleanup() { kill ${PROXY_PID:+$PROXY_PID} ${TEI_PID:+$TEI_PID} 2>/dev/null || true; }
trap cleanup EXIT

HF_HUB_OFFLINE=1 uv run --script tools/bge_m3_mps_server.py > /tmp/fhv1_e2e_tei.log 2>&1 &
TEI_PID=$!
for i in $(seq 1 120); do curl -sf http://127.0.0.1:8080/health >/dev/null && break; sleep 1; done

cargo run -p sf-proxy --bin sf-proxy -- \
  --listen 127.0.0.1:8088 \
  --lancedb-uri data/sf-lancedb \
  --embedder http \
  --tei-http-url http://127.0.0.1:8080 \
  --default-domain python > /tmp/fhv1_e2e_proxy.log 2>&1 &
PROXY_PID=$!
for i in $(seq 1 60); do
  code=$(curl -s -o /dev/null -w "%{http_code}" -X OPTIONS http://127.0.0.1:8088/api/v1/chat || true)
  [ "$code" = "200" ] || [ "$code" = "405" ] && break
  sleep 1
done

PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-$HOME/Library/Caches/ms-playwright}" \
  pnpm --dir frontend test:e2e
```

---

## 2. Hardening & Missing Coverage Scope (Slices 1–4 Sequential)

> Execute Slices 1 -> 4 sequentially on `feat/fhv1-hector-filter-v1`. Within a Slice, parallelize independent file edits/tests across sub-tasks, integrate cleanly, run the Slice's verification command, update `- [x]` in `TASKS.md`, validate via `agent.sh validate`, and commit atomically.

---

### Slice 1 — Core Refactor, Trace Uniqueness, Chat Pass Headers & Kernel/Storage Edge Tests
* **Commit Scope**: `refactor,fix(storage,proxy): deduplicate profile stats, fix reuse latency, trace_id grouping, and chat headers`
* **Files to Modify**:
  * `crates/sf-storage/src/fhv1_calibration.rs` & `crates/sf-storage/src/lib.rs` (promote `pub fn stats_from_profile` and re-export it cleanly)
  * `crates/sf-proxy/src/fhv1_pipeline.rs` (delete local `profile_stats()`, call `sf_storage::stats_from_profile`)
  * `crates/sf-proxy/src/fhv1_api.rs` (fixes #1–#4 below)
  * `crates/sf-proxy/src/chat_api.rs` (fixes #2 & #3 below)
  * `crates/sf-bench/src/fhv1_eval.rs` (use `sf_storage::stats_from_profile` and fix benchmark `trace_id` grouping)
  * `crates/sf-kernels/tests/fhv1_precision_test.rs`
  * `crates/sf-storage/tests/fhv1_roundtrip_test.rs`
* **Code Fixes Required**:
  1. **Deduplicate `profile_stats`**: remove local copies in `fhv1_pipeline.rs`, `fhv1_api.rs`, and `fhv1_eval.rs`; use `sf_storage::stats_from_profile`.
  2. **Deduplicate `3hm_plus_fhv1` + measure `eval_latency_ns` on `reuse` path**:
     * In `chat_api.rs`, extract one shared helper for `3hm_plus_fhv1` execution across the 3HM breach paths and clean pass path.
     * In `fhv1_api.rs` inside `score_realtime`, when `reuse == true` (single `/embed` batch reused from 3HM), wrap `evaluate_fhv1_batch(...)` with `Instant::now()` and record real nanoseconds in `eval_latency_ns` instead of `0`.
  3. **Return `x-sf-trace-id` & `x-sf-fhv1-decision: PASS` headers on `/api/v1/chat` accept (`fhv1` & `3hm_plus_fhv1`)**:
     * Have `run_realtime_chat` return `Result<Option<String>, Response>` yielding `Some(trace_id)` when `fhv1` evaluated without `preserve_3hm_breach` and passed, and `None` for `"3hm_default"`.
     * In `forward_accepted_chat`, when `Option<String>` is `Some(trace_id)`, stamp `"x-sf-trace-id"` and `"x-sf-fhv1-decision": "PASS"` on the `200 text/event-stream` response headers (which `cors.rs` already exposes). Keep `"3hm_default"` headers completely untouched.
  4. **Collision-free `new_trace_id` & Consistent Prompt-Scoped Benchmark `trace_id`**:
     * In `fhv1_api.rs`, update `new_trace_id(prefix)` to combine `now_ms()` with a process-wide `AtomicU64` sequence (`format!("{prefix}-{ms}-{seq}")`) so same-millisecond bursts never collide.
     * In `fhv1_api.rs` (`run_benchmark`) and `fhv1_eval.rs` (`persist_benchmark_run`), assign `trace_id = format!("{run_id}-{input_id}")` across all chunks of a single prompt (replacing `&run_id` in `fhv1_api.rs` and `{run_id}-{input_id}-{index}` in `fhv1_eval.rs`), so `GET /api/v1/fhv1/traces/{trace_id}` drills down cleanly across all chunks (`chunk 0..M`) of that prompt.
* **Missing Kernel & Storage Tests Required**:
  * `crates/sf-kernels/tests/fhv1_precision_test.rs`:
    1. `MovementMetric::Variance` and `MovementMetric::StdDev` tier classification (`classify_movement_tiers` & `compute_fhv1_profile_stats`).
    2. Exact envelope boundary & telemetry checks: `norm_pos == Some(0.0)` at `min_d`, `norm_pos == Some(1.0)` at `max_d`, negative `delta_vs_mean` when `x_d < mean_d`, and fail-closed `BadDim` / `NonFinite` in `evaluate_fhv1_chunk`.
  * `crates/sf-storage/tests/fhv1_roundtrip_test.rs`:
    1. `query_audit_trace_summaries` filtering by `profile_id`, `category`, `passed = Some(false)`, pagination (`page = 2`), and missing-profile error on `get_trace_drilldown`.
    2. `get_trace_drilldown` with `use_rogue_mask = true` verifying `DimBoundStatus::PrunedRogue` (`evaluated_dims == 1015`) preserves exact raw `observed_bits` on rogue dimensions (`UNIVERSAL_NOISE_INDICES`).
* **Verification**:
  * `cargo fmt --all -- --check && cargo clippy --workspace --all-targets -- -D warnings && cargo test --workspace`

---

### Slice 2 — Exhaustive API, Batch Reuse, Error Envelope & Eval Matrix Coverage (`sf-proxy`, `sf-bench`)
* **Commit Scope**: `test(proxy,bench): add comprehensive REST, batch-reuse, error-path, and eval coverage`
* **Files to Modify**:
  * `crates/sf-bench/src/fhv1_corpus.rs`
  * `crates/sf-bench/src/fhv1_eval.rs`
  * `crates/sf-proxy/tests/fhv1_api_e2e_test.rs`
* **Missing Tests Required**:
  * `crates/sf-bench/src/fhv1_corpus.rs` (`#[cfg(test)]`):
    * `.jsonl` ingestion with `{"prompt": "..."}`, blank-line skipping, malformed JSON line fail-closed error, and cross-file SHA-256 deduplication in directory scans.
  * `crates/sf-bench/src/fhv1_eval.rs` (`#[cfg(test)]`):
    * Verify `failed_dims_count_histogram`, `attach_comparison` (`granularity_comparison`), `attribution.oob_catch_counts`, exact per-category `precision`/`recall`/`f1`/`far_fpr`/`frr_fnr`, `select_view` missing-view error, and `parse_granularity` unknown error.
  * `crates/sf-proxy/tests/fhv1_api_e2e_test.rs` (expand from 1 test into isolated E2E tests covering every contract):
    1. **Lazy empty & `None` store behavior**: `GET /profiles`, `/benchmarks`, `/traces` return `200 []` / `{rows: []}` when `fhv1_store: None` or directory uninitialized; `/calibrate`, `/evaluate`, `/benchmarks/run` fail closed (`503`) when `fhv1_store: None`.
    2. **Profile detail & custom quantile reclassification**: `GET /api/v1/fhv1/profiles/{profile_id}?metric=variance&p25=0.1&p75=0.6&p90=0.8` and `metric=std_dev`, plus `400` on invalid quantiles (`p25 >= p75`) and `404` on unknown `profile_id`.
    3. **`/evaluate` granularities, headers & error envelopes**: `full_only`, `clauses`, and `full_mirror` verifying `x-sf-trace-id`, `x-sf-fhv1-decision`, and `400` unknown granularity / `404` missing profile.
    4. **REST benchmark lifecycle & fail-closed `409` overlap**: `POST /api/v1/fhv1/benchmarks/run` with inline `samples` AND `dataset_path` -> `GET /benchmarks` & `GET /benchmarks/{run_id}` -> verify prompt-scoped multi-chunk `trace_id` drill-down, `409 Conflict` on calibration overlap, and `404` on unknown `run_id`.
    5. **Single `.xlsx` & export error checks**: `?format=xlsx&max_rows=100` returns `.xlsx` bytes readable as a valid `ZipArchive` with `Summary_Envelope` + `Raw_Samples_Matrix`; `400` unknown format; `404` unknown profile.
    6. **`/api/v1/chat` full matrix & zero-duplicate `/embed` reuse counter**:
       - `fhv1` PASS (`200 SSE`, `x-sf-fhv1-decision: PASS`, `x-sf-trace-id` persisted in `REALTIME_CHAT` traces).
       - `3hm_plus_fhv1` (`3HM` PASS + `fhv1` PASS -> `200 SSE`, `x-sf-fhv1-decision: PASS`, trace persisted).
       - `3hm_plus_fhv1` (`3HM` PASS + `fhv1` FAIL -> `403` `fhv1_ingress_breach` `FHV1_AABB_ENVELOPE`, non-zero `eval_latency_ns` on reuse path).
       - **Counting embedder test**: asserts `embed_batch_f32` called once and `embed_batch_raw_f64` called **0 times** when `3hm_plus_fhv1` runs with `normalize: true && granularity != "full_mirror"`, vs invoking `embed_batch_raw_f64` when `granularity == "full_mirror"` or `normalize == false`.
    7. **Trace query filters & concurrent `trace_id` uniqueness**: filter by `run_id`, `category`, `passed=false`, `page=2`, `400` invalid `passed`, and back-to-back rapid `/evaluate` requests generating distinct `trace_id`s.
* **Verification**:
  * `cargo fmt --all -- --check && cargo clippy --workspace --all-targets -- -D warnings && cargo test --workspace`

---

### Slice 3 — Frontend Studio Polish (`Fhv1BenchmarkExplorer`, `Fhv1VarianceStudio`) & Full Vitest Coverage
* **Commit Scope**: `feat,test(frontend): polish fhv1 explorer comparison matrix, quantile bounds, and Vitest suites`
* **Files to Create**:
  * `frontend/src/ui/StudioShell.test.tsx`
* **Files to Modify**:
  * `frontend/src/domain/fhv1.ts`
  * `frontend/src/domain/fhv1.test.ts`
  * `frontend/src/ui/fhv1Charts.ts`
  * `frontend/src/ui/Fhv1VarianceStudio.tsx`
  * `frontend/src/ui/Fhv1VarianceStudio.test.tsx`
  * `frontend/src/ui/Fhv1BenchmarkExplorer.tsx`
  * `frontend/src/ui/Fhv1BenchmarkExplorer.test.tsx`
  * `frontend/src/ui/BreachCard.test.tsx`
  * `frontend/src/ui/Playground.test.tsx`
* **UI Refinements Required**:
  1. **`Fhv1BenchmarkExplorer` Granularity Comparison & Attribution Parity**:
     * Extend `Fhv1BenchmarkDetail` in `frontend/src/domain/fhv1.ts` to parse optional `granularity_comparison` entries and `attribution.oob_catch_counts`.
     * Render a compact **`Granularity & Mask Comparison`** table (`aria-label="Granularity comparison"`) showing `granularity`, `use_rogue_mask`, `evaluated_dims`, `tp`, `tn`, `fp`, `fn`, `far_fpr`, `frr_fnr`, `f1` with `formatLosslessF64` (`String(v)`).
     * Expose toggleable or paired `oob_catch_counts` series alongside `in_domain_fail_counts` in `attributionOption` (`fhv1Charts.ts`) with lossless tooltips.
  2. **`Fhv1VarianceStudio` Kernel-Parity Quantile Validation**:
     * Update `quantilesValid` in `Fhv1VarianceStudio.tsx` to allow `0 <= p25 < p75 < p90 <= 1` matching `Fhv1Quantiles::validate` in `sf-kernels/src/fhv1.rs`.
* **Missing Vitest Tests Required (Zero `.toFixed` in `fhv1` assertions)**:
  1. `frontend/src/domain/fhv1.test.ts`: `movementTierName` bounds, `isFhv1RogueDim` indices, invalid `Fhv1ChatTelemetry` / `Fhv1Evaluation` fail-closed parsing, `granularity_comparison` + `oob_catch_counts` parsing.
  2. `frontend/src/ui/BreachCard.test.tsx`: add test rendering `FHV1_AABB_ENVELOPE` breach card verifying `profile_id`, `eval_granularity`, `rogue mask on/off`, `failed dims`, `underflow`, `overflow`, `max violation` lossless formatting (no `.toFixed(4)`).
  3. `frontend/src/ui/StudioShell.test.tsx` (**new**): verify switching between `Playground`, `Variance studio`, and `Benchmark explorer`, `aria-pressed` states, preserving `Messages` list & `w-60` drawer when returning to `Playground`, and `onOpenTrace` switching directly from `Playground` audit log to `Benchmark explorer` with drill-down loaded.
  4. `frontend/src/ui/Playground.test.tsx`: test **`3hm_plus_fhv1`** chat request + `fhv1` breach rendering, **`fhv1` PASS (`200 SSE`)** stream rendering, toggling **`Use rogue mask`** and **`Eval granularity`** (`full_only`/`clauses`/`full_mirror`), Direct Lab **`FHV1 PASS`**, and **`Open trace <id>`** callback.
  5. `frontend/src/ui/Fhv1VarianceStudio.test.tsx`: test switching `Movement metric` (`variance`/`std_dev`), updating `P25`/`P75`/`P90` query params + invalid quantile warning message, uploading a calibration file (`userEvent.upload`), clicking **`Export xlsx`** and **`Export parquet`**, and filtering by `yes` / dimension index.
  6. `frontend/src/ui/Fhv1BenchmarkExplorer.test.tsx`: test `Granularity comparison` table, `oob_catch_counts` attribution view, changing `Benchmark run` resets `page=1`, clicking trace button fires `onTraceId`, and empty-run graceful rendering.
* **Verification**:
  * `pnpm --dir frontend lint && pnpm --dir frontend build && pnpm --dir frontend test`

---

### Slice 4 — Expanded Live Playwright E2E Suite, Clean Sync & Final Milestone Gate
* **Commit Scope**: `test(e2e): cover fhv1 chat modes, variance studio exports, and explorer comparison live`
* **Files to Modify**:
  * `frontend/e2e/fhv1.spec.ts`
  * `CHANGELOG.md` (add one concise bullet under `## [Unreleased]` if new capabilities such as chat pass trace headers and explorer comparison matrix ship; keep `0.2.1`)
  * `TASKS.md` (mark all Slices `[x]`, `status: "DONE"`)
* **Expanded Live Playwright E2E Scenarios (`frontend/e2e/fhv1.spec.ts`, added to existing 2 tests -> `5` tests in `fhv1.spec.ts` + `9` in `playground.spec.ts` = `14` total)**:
  * **Test 3 — Playground live `fhv1` breach & `3hm_plus_fhv1` dual-trace persistence**: switch `Filter mode` to `fhv1` -> pick `python-v1-...` -> submit out-of-domain prompt -> assert `FHV1_AABB_ENVELOPE` card renders lossless `max violation` (no `.toFixed(4)`); switch to `3hm_plus_fhv1` -> submit `Risotto L1` preset -> assert `L1_CENTROID_COSINE` 3HM breach card wins while `/api/v1/fhv1/traces?source_kind=REALTIME_CHAT` recorded the dual `fhv1` trace.
  * **Test 4 — Variance Studio live metric/quantile & binary download**: select `python-v1-...`, switch `Movement metric` to `variance`, update `P25` to `0.2`, await live API detail refresh, trigger `Export csv` and `Export xlsx` asserting Playwright download filenames (`python-v1-*.csv`, `python-v1-*.xlsx`).
  * **Test 5 — Benchmark Explorer live comparison matrix & pagination**: select a `python` benchmark run, assert `Granularity comparison` table & 4 quadrant cards render, click `Next page`, click a trace ID -> assert `fhv1 drill-down` displays `0x[0-9a-f]{16}`.
* **Full Milestone Verification Gate (Mandatory before Approval Gate)**:
  1. `cargo fmt --all -- --check`
  2. `cargo clippy --workspace --all-targets -- -D warnings`
  3. `cargo test --workspace`
  4. `pnpm --dir frontend lint`
  5. `pnpm --dir frontend build`
  6. `pnpm --dir frontend test`
  7. `uv run --script tools/test_bge_m3_mps_server.py && uv run --script tools/test_augment_fhv1_corpus.py && uv run --script tools/test_generate_fhv1_benchmark.py`
  8. Non-interactive `:8080` + `:8088` run (§1.3 runbook) -> `pnpm --dir frontend test:e2e` (all `14` Playwright tests pass) -> PID cleanup + confirm `:8080`/`:8088` stopped
  9. Verify `data/sf-lancedb/domain_hypercubes.lance` untouched (`66` locks, original mtime/checksums)
  10. `/Users/hbauzan/treepwood/fabrica_de_software/agent.sh validate --task-file TASKS.md`
  11. `/Users/hbauzan/treepwood/fabrica_de_software/agent.sh notify --task-file TASKS.md`

---

## 3. Protocol Invariants & Approval Gate
* **Exclusive Authorship**: `hbauzan <hbauzan@gmail.com>`. Zero `Co-authored-by:` trailers.
* **Lexical Hygiene**: NEVER mention external assistants, bots, models, or editors in source code, comments, tests, docs, or commit messages.
* **Git Safety**: NEVER `git add -A` (stage explicit file paths only; never stage `repomix-output.xml`, `data/`, `.env`, `.DS_Store`). NEVER `git push` or `merge` to `main` — stop at the Approval Gate after Slice 4 passes all checks.
