# EXECUTION ROADMAP: EXHAUSTIVE COORDINATE-WISE BOUNDING FILTER `fhv1` ("FILTRO HÉCTOR V1")

> **Single Source of Truth**: This document is 100% self-contained for `TASK-009`. Do **not** pull requirements from `roadmap/archived/` or `roadmap/future-holistic-resonance-gate.md`.  
> **Baseline**: `v0.2.1` (`main` @ `f2ac3dd`, tag `v0.2.1` @ `564ad28`)  
> **Task Governance**: `TASK-009` in [`TASKS.md`](../TASKS.md) (`fabrica-de-software` + `transparent-dev-protocol`)  
> **Git Branch Model**: **Single feature branch `feat/fhv1-hector-filter-v1`** (branched from `main`), with **atomic verified commits per Slice (Slices 1–8)**. Stop at the human Approval Gate before `push` or `merge --no-ff` to `main`.

---

## 1. Project Context & Current State (Ground Truth)

### 1.1 Active Topology & Ports
* **Backend Gateway (`crates/sf-proxy`)**: `http://127.0.0.1:8088` (**Axum `0.8.9` / `matchit 0.8.4`**: dynamic route segments MUST use `{id}` syntax, NEVER `:id`). Existing routes: `/v1/chat/completions`, `/api/v1/chat`, `/api/v1/upstream/env`.
* **Frontend SPA (`frontend/`)**: `http://127.0.0.1:5173` (React `^19.3.1`, TypeScript `~7.0.2`, Vite `^8.3.5`, Tailwind CSS `^4.3.3`, Vitest `^5.0.5`, Playwright `^1.64.1`). Entrypoint [`frontend/src/main.tsx`](../frontend/src/main.tsx) mounts `<Playground />` directly (`App.tsx` does not exist).
* **Native Metal Embedder (`tools/bge_m3_mps_server.py`)**: `http://127.0.0.1:8080` (`BAAI/bge-m3`, `mps`, `torch.float32`, RFC-003). `POST /embed` already supports `{"inputs": ..., "truncate": bool, "normalize": bool}` and `GET /health` returns `200` when warm.
* **Vector Store (`data/sf-lancedb`)**: LanceDB `0.40.0` (`remote`), Arrow crates pinned `=58.4.1`, imported exclusively via `lancedb::arrow::{arrow_array, arrow_buffer, arrow_schema}`. Existing table: `domain_hypercubes` (66 BGE-M3 calibrated canonical locks). **NEVER delete, overwrite, or re-seed `domain_hypercubes`**.
* **Legacy Diagnostic Studio (`crates/sf-ui`)**: `http://127.0.0.1:3000` — out of scope beyond keeping `cargo test --workspace` and `cargo clippy --workspace --all-targets -- -D warnings` green.

### 1.2 Canonical Toolchains (Strict — Zero Mixing)
* **Rust (`rust-toolchain.toml` `1.94.1`)**: `cargo` exclusively (`cargo fmt --all -- --check`, `cargo clippy --workspace --all-targets -- -D warnings`, `cargo test --workspace`).
* **Frontend (`frontend/`)**: `pnpm` (`11.8.0`) exclusively (`pnpm --dir frontend lint`, `pnpm --dir frontend build`, `pnpm --dir frontend test`, `pnpm --dir frontend test:e2e`).
* **Python (`tools/`)**: `uv` exclusively (PEP 723 `# /// script` headers). Zero `pip`/`npm`.
* **Task Governance**: `/Users/hbauzan/treepwood/fabrica_de_software/agent.sh validate --task-file TASKS.md`.

### 1.3 Verified Baseline Quality Gate (`v0.2.1`)
* Rust: `111` tests passing (`0` failed), `fmt` & `clippy -D warnings` clean.
* Frontend: `44` Vitest tests passing (`10` files), `oxlint` & `tsc -b && vite build` clean, `9` Playwright E2E tests (`frontend/e2e/playground.spec.ts`) passing against live `:8080` + `:8088` + calibrated `data/sf-lancedb`.

### 1.4 Non-Interactive Service Runbook (FORBIDDEN: `./setup.sh`)
`./setup.sh` is an interactive `read -p` menu and **MUST NEVER be invoked by agents**. Use non-interactive background processes with `/health` polling and deterministic PID cleanup:

```bash
# 1. Start native Metal BGE-M3 embedder (:8080) offline from HF cache
HF_HUB_OFFLINE=1 uv run --script tools/bge_m3_mps_server.py > /tmp/fhv1_tei.log 2>&1 &
TEI_PID=$!
for i in $(seq 1 120); do
  if curl -sf http://127.0.0.1:8080/health >/dev/null; then break; fi
  sleep 1
done

# 2. Start sf-proxy (:8088) against existing data/sf-lancedb (preserves domain_hypercubes)
cargo run -p sf-proxy --bin sf-proxy -- \
  --listen 127.0.0.1:8088 \
  --lancedb-uri data/sf-lancedb \
  --embedder http \
  --tei-http-url http://127.0.0.1:8080 \
  --default-domain python > /tmp/fhv1_proxy.log 2>&1 &
PROXY_PID=$!
for i in $(seq 1 60); do
  code=$(curl -s -o /dev/null -w "%{http_code}" -X OPTIONS http://127.0.0.1:8088/api/v1/chat || true)
  if [ "$code" = "200" ] || [ "$code" = "405" ]; then break; fi
  sleep 1
done

# 3. Run Playwright E2E (playwright.config.ts manages Vite on :5173)
PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-$HOME/Library/Caches/ms-playwright}" \
  pnpm --dir frontend test:e2e

# 4. Always cleanup background PIDs
kill "$PROXY_PID" "$TEI_PID" 2>/dev/null || true
```

---

## 2. Objective, Scope & Locked Architectural Decisions

### 2.1 Primary Objective
Deliver **`filtro hector v1` (`fhv1`)** as an independent, strictly deterministic **Exhaustive Coordinate-Wise Axis-Aligned Bounding Box (AABB / Strict $\ell_\infty$ Envelope Gate)**:

$$\text{PASS} \iff \forall d \in \mathcal{D}_{\text{eval}}: \min_d \le x_d \le \max_d \quad (\text{polarity}=0 \text{ ALLOWLIST})$$

with lossless IEEE 754 `f64` precision end-to-end (zero rounding, zero `f16`/`bf16`, zero `.toFixed()` in `fhv1` APIs/UI/exports), deterministic multi-granularity calibration, offline 4-quadrant adversarial benchmarking (`>= 400` real prompts/domain), lossless `.xlsx`/`.zip`/`.csv`/`.parquet` export, full forensic `fhv1_audit_traces` persistence, and a 3-view Frontend Studio.

### 2.2 Locked Decisions (All Closed — Do Not Reopen)

| ID | Area | Locked Contract |
| :--- | :--- | :--- |
| **D-01 (`1C`)** | Filter boundary & Rogue Mask | `fhv1` coexists as an independent selectable filter (`filter_mode: "3hm_default" \| "fhv1" \| "3hm_plus_fhv1"`). Default evaluates all `1,024` dims (`use_rogue_mask = false`), toggleable to `1,015` dims (`use_rogue_mask = true`, pruning `UNIVERSAL_NOISE_INDICES = [292, 297, 308, 329, 386, 404, 577, 616, 780]`). Existing `3HM` path stays untouched. |
| **D-02 (`2C`)** | Multi-granularity calibration | Deterministic pipeline emits 10 `strategy_tag` families deduplicated by `(strategy_tag, text_sha256)`: `full_doc`, `paragraph`, `sentence`, `clause_opt2c`, `window_w5_s3`, `window_w10_s5`, `window_w20_s10`, `window_w40_s20`, `atomic_phrase`, `surface_norm_variant`. Optional offline `--augment-llm` (`tools/augment_fhv1_corpus.py`) requires explicit `--provider <gemini\|openai\|deepseek\|groq\|ollama>`, reads `.env` matching `env_config.rs`, and caches immutable SHA-256 JSONL under `data/fhv1_augmented/`. **During autonomous slices, execute live `:8080` runs deterministically without `--augment-llm`, and verify `--augment-llm` via offline contract/mock HTTP tests.** |
| **D-03 (`1B`)** | `eval_granularity` & No Early-Exit | `full_only`: `[normalized_full_text]` (`overall_passed = full_text_passed`). `clauses`: `[normalized_full_text]` + `ClauseSegmenter` Option 2C (`overall_passed = all_chunks_passed`, default for realtime). `full_mirror`: `[normalized_full_text]` + full 10-strategy deterministic §D-02 multi-granularity expander (`overall_passed = all_chunks_passed`, default for benchmarks). Always evaluate every chunk without early-exit, recording `full_text_passed` (`chunk[0]`) and `all_chunks_passed`. |
| **D-04 (`4A` + `4.1-B`)** | Precision, Normalization & Raw Embedder | Store `fhv1` vectors and statistics in IEEE 754 `Float64` (`Arrow DataType::Float64`). Per-profile `normalize: bool` (default `true`, optional `false` via `embed_batch_raw_f64` without Rust re-normalization or `f32` cast). `MockBatchEmbedder::embed_batch_raw_f64` fails closed (`Err(...)`); `TeiGrpcEmbedder::embed_batch_raw_f64(..., false)` fails closed (`normalize=true` delegates to `embed_batch_f32` + `f64::from`); unit/E2E tests use a dedicated `TestRawF64Embedder`. |
| **D-05 (`2A` + `echarts`)** | Dependencies & Kernel Purity | Root `Cargo.toml` adds `rust_xlsxwriter`, `parquet = "=58.4.1"`, `zip`. `crates/sf-storage/Cargo.toml` adds `rust_xlsxwriter`, `parquet`, `zip`, `serde`, `serde_json`. `crates/sf-bench/Cargo.toml` adds `sha2`. `crates/sf-kernels/Cargo.toml` stays **0-dep (no `serde`)**: `Fhv1DimComparison` stores `observed_bits: u64` (`f64::to_bits()`), formatted to `"0x{:016x}"` in `sf-proxy` DTOs. `crates/sf-proxy/src/cors.rs` exposes `content-disposition`, `x-sf-trace-id`, `x-sf-fhv1-decision`. Frontend installs `echarts` (`echarts/core` + `CanvasRenderer`, `import type` compatible with `erasableSyntaxOnly: true`). |
| **D-06 (`3A` + `3B`)** | `/api/v1/chat` & `3hm_plus_fhv1` | `buildChatRequest` omits `filter_mode` (and `fhv1_*`) when unset or `"3hm_default"`. `fhv1` breaches on `/api/v1/chat` return HTTP `403` with sibling envelope `fhv1_ingress_breach` (`failing_tier: "FHV1_AABB_ENVELOPE"`), mapped in `parseChatBreach`. In `"3hm_plus_fhv1"`: reuse the single `/embed` batch when `fhv1.normalize == true && granularity != "full_mirror"`, evaluate `3HM` first (returning `3HM` breach if it fails, else `fhv1_ingress_breach`), and **always run + persist `fhv1_audit_traces` (`REALTIME_CHAT`)** even when `3HM` blocked. |
| **D-07 (`6A` + `D1` + `E1`)** | Storage, `.xlsx` & Audit API | 4 dedicated LanceDB tables inside `data/sf-lancedb` opened/created lazily so `sf-proxy` starts cleanly even before `fhv1` calibration (`GET` routes return `[]`). Lossless 2-sheet `.xlsx` (`Summary_Envelope` + `Raw_Samples_Matrix`, auto-split into `part_001.xlsx`... inside `.zip` when rows `> 10,000`), lossless `.csv` (`f64::to_string()`), and native `.parquet` (`ArrowWriter`). |
| **D-08 (`B1` + `C1`)** | Decision Literalism & Movement Tiers | Only `[min_d, max_d]` decides `PASS`/`FAIL`. `mean_d` never changes verdicts; audited via `delta_vs_mean = x_d - mean_d` and `norm_pos = (x_d - min_d) / span_d` (`None` if `span_d == 0.0`). Movement tiers: `ZERO_SPAN` (`0`, `span == 0.0`), `LOW_ANCHOR` (`1`, `<= P25`), `MODERATE` (`2`, `(P25, P75]`), `HIGH_VOLATILITY` (`3`, `(P75, P90]`), `EXTREME_MOVEMENT` (`4`, `> P90`) over non-zero dimensions, switchable across `variance`, `std_dev`, `span`. |
| **D-09 (`5A` + `7A`)** | Offline Benchmark Floor & Versioning | `tools/generate_fhv1_benchmark.py` runs **100% offline** by default (`--fetch-hf` strictly opt-in), generating `>= 400` real prompts per domain (`>= 100`/quadrant, `0%` exact & NFKC-lowercased SHA-256 overlap with calibration) on canonical `python` [EN] & `receta` [ES] plus generic user domains. Keep version `0.2.1` and log additions under `## [Unreleased]` in `CHANGELOG.md` (no version bump/tag). |

### 2.3 Explicitly Out of Scope (Forbidden)
* Altering `3HM` scoring (`sf-kernels/src/scalar.rs`, `simd/`), `domain_hypercubes` schema/data, `PairwiseDifferentialLock`, or published `Suite 1` / `Suite 2` metrics.
* Changing `formatGate` (`.toFixed(4)`) in [`frontend/src/domain/format.ts`](../frontend/src/domain/format.ts) for `3HM` `PassCard`/`BreachCard`.
* Implementing Holistic Resonance Gate or Egress Semantic Amplification (`v1.1+`).
* Modifying `crates/sf-ui` beyond keeping workspace build/tests green.
* Staging/committing untracked `repomix-output.xml`, `data/`, `.env`, or `.DS_Store`.

---

## 3. Ground Truth: Protected Contracts & Full Data Schemas

### 3.1 Protected Frontend Testing Selectors (`Playground.test.tsx`, `BreachCard.test.tsx`, `request.test.ts`, `playground.spec.ts`)
Must remain verbatim:
* `getByRole('textbox', { name: 'Gateway base' })` (default `http://127.0.0.1:8088`), header text `POST http://127.0.0.1:8088/api/v1/chat` in default view.
* `getByRole('combobox', { name: 'Domain id' })` (exactly `11` options in `3HM` mode: `expect(options).toHaveCount(11)`).
* `getByRole('textbox', { name: 'Prompt' })` (Enter submits, Shift+Enter newline), `getByRole('button', { name: /Send|Sending/ })`.
* `getByRole('list', { name: 'Messages' })` (`<ol>`, `overflow-y: auto`), `getByRole('complementary', { name: 'Live tuning' })` (fixed `w-60` = `240px`, `overflow-y: auto`), `#root > div` (`h-[100dvh]`, `overflow: hidden`).
* `getByRole('checkbox', { name: 'Apply overrides' })` (default `false`), sliders `L1 cosine threshold`, `L2 clause threshold`, `Quorum K`, `Epsilon`.
* `Usar keys de .env`, `Cargar de .env`, `Provider`, `Base URL`, `Model`, `API key`, and chips `Python generator`, `Risotto L1`, `Piggyback L2`, `Spectral L3`.
* `buildChatRequest(draft())` exact `.toEqual()` shape when `filterMode` is unset/`'3hm_default'`.
* `formatGate(score, threshold)` `.toFixed(4)` outputs (`0.1200`, `0.5884`, `0.4200`) in `BreachCard.test.tsx` and `format.test.ts`.
* Reuse theme tokens from [`frontend/src/index.css`](../frontend/src/index.css): `--color-studio-bg` (`#0b0f17`), `--color-studio-panel` (`#111827`), `--color-studio-card` (`#161f30`), `--color-studio-line` (`#273549`), `--color-studio-text` (`#f1f5f9`), `--color-studio-muted` (`#94a3b8`), `--color-studio-accent` (`#38bdf8`), `--color-studio-pass` (`#10b981`), `--color-studio-breach` (`#ef4444`), `--color-studio-warn` (`#f59e0b`).

### 3.2 Exact Arrow `=58.4.1` LanceDB Schemas (`crates/sf-storage/src/fhv1_schema.rs`)
All 4 tables live in `data/sf-lancedb` alongside `domain_hypercubes`, built via `lancedb::arrow::arrow_schema::{DataType, Field, Schema}`:

1. **`fhv1_calibration_samples`**:
   `sample_id: Utf8`, `profile_id: Utf8`, `policy_id: Utf8`, `version: UInt64`, `source_ref: Utf8`, `strategy_tag: Utf8`, `raw_text: Utf8`, `text_sha256: FixedSizeBinary(32)`, `normalize: Boolean`, `model_id: Utf8`, `source_dtype: Utf8`, `vector: FixedSizeList(Float64, 1024)`, `created_at_ms: Int64`.
2. **`fhv1_profiles`**:
   `profile_id: Utf8` (e.g. `python-v1-<12_hex>`), `policy_id: Utf8`, `version: UInt64`, `polarity: UInt8` (`0` = ALLOWLIST), `normalize: Boolean`, `use_rogue_mask_default: Boolean`, `sample_count: UInt64`, `corpus_sha256: FixedSizeBinary(32)`, `model_id: Utf8`, `source_dtype: Utf8`, `augmented_llm: Boolean`, `min_vector: FixedSizeList(Float64, 1024)`, `max_vector: FixedSizeList(Float64, 1024)`, `mean_vector: FixedSizeList(Float64, 1024)`, `span_vector: FixedSizeList(Float64, 1024)`, `variance_vector: FixedSizeList(Float64, 1024)`, `std_dev_vector: FixedSizeList(Float64, 1024)`, `movement_tier_codes: FixedSizeList(UInt8, 1024)`, `created_at_ms: Int64`.
3. **`fhv1_benchmark_runs`**:
   `run_id: Utf8`, `profile_id: Utf8`, `policy_id: Utf8`, `dataset_name: Utf8`, `dataset_sha256: FixedSizeBinary(32)`, `eval_granularity: Utf8`, `use_rogue_mask: Boolean`, `total_inputs: UInt64`, `total_chunks: UInt64`, `summary_metrics_json: Utf8`, `created_at_ms: Int64`.
4. **`fhv1_audit_traces`**:
   `trace_id: Utf8`, `run_id: Utf8` (empty string `""` for realtime), `source_kind: Utf8` (`"BENCHMARK"` | `"REALTIME_CHAT"` | `"REALTIME_LAB"`), `profile_id: Utf8`, `policy_id: Utf8`, `category: Utf8` (`"IN_DOMAIN_VALID"` | `"OUT_OF_DOMAIN_BENIGN"` | `"HYBRID_BOUNDARY"` | `"ADVERSARIAL_FUZZING"` | `"REALTIME"`), `expected_pass: Boolean` (nullable `true` in Arrow `Field`), `input_id: Utf8`, `raw_text: Utf8`, `eval_granularity: Utf8`, `use_rogue_mask: Boolean`, `chunk_index: UInt32`, `chunk_strategy: Utf8`, `chunk_text: Utf8`, `input_vector: FixedSizeList(Float64, 1024)`, `chunk_passed: Boolean`, `overall_passed: Boolean`, `full_text_passed: Boolean`, `all_chunks_passed: Boolean`, `evaluated_dims: UInt16`, `failed_dims_count: UInt16`, `underflow_count: UInt16`, `overflow_count: UInt16`, `max_violation_delta: Float64`, `mean_abs_delta_vs_mean: Float64`, `eval_latency_ns: UInt64`, `embedding_ms: Float64`, `created_at_ms: Int64`.

### 3.3 Exact Gateway REST & Breach Envelope Contracts (`crates/sf-proxy`, Axum `0.8` `{id}`)

| Method & Path | Purpose & Payload |
| :--- | :--- |
| `GET /api/v1/fhv1/profiles` | Returns `[]` if table absent; else `[{ profile_id, policy_id, version, polarity, normalize, use_rogue_mask_default, sample_count, model_id, source_dtype, augmented_llm, created_at_ms }]`. |
| `GET /api/v1/fhv1/profiles/{profile_id}` | Query `?metric=variance\|std_dev\|span&p25=0.25&p75=0.75&p90=0.90`. Returns profile metadata + exact 1,024-element `f64` arrays (`min`, `max`, `mean`, `span`, `variance`, `std_dev`), `movement_tier_codes`, `quantile_cutoffs`. |
| `POST /api/v1/fhv1/calibrate` | Body: `{ policy_id, texts: string[], normalize?: bool, use_rogue_mask_default?: bool }`. Runs 10-strategy expansion + `embed_batch_raw_f64` + LanceDB save; returns created profile summary. |
| `GET /api/v1/fhv1/profiles/{profile_id}/export` | Query `?format=xlsx\|csv\|parquet&max_rows=10000`. Streams `.xlsx` (or `.zip` if split), `.csv`, or `.parquet` with `Content-Disposition: attachment; filename="..."`. |
| `POST /api/v1/fhv1/evaluate` | Body: `{ profile_id, text, eval_granularity?: "full_only"\|"clauses"\|"full_mirror", use_rogue_mask?: bool }`. Persists all chunk traces (`REALTIME_LAB`). Returns `{ trace_id, profile_id, policy_id, eval_granularity, use_rogue_mask, overall_passed, full_text_passed, all_chunks_passed, embedding_ms, eval_latency_ns, chunks: [{ chunk_index, chunk_strategy, chunk_text, chunk_passed, evaluated_dims, failed_dims_count, underflow_count, overflow_count, max_violation_delta, mean_abs_delta_vs_mean, dimensions: Fhv1DimComparisonDto[1024] }] }`. |
| `POST /api/v1/chat` | Optional `{ filter_mode?: "3hm_default"\|"fhv1"\|"3hm_plus_fhv1", fhv1_profile_id?, fhv1_granularity?, fhv1_use_rogue_mask? }`. `fhv1` breach returns HTTP `403`: `{ error: { kind: "fhv1_ingress_breach", code: "SEMANTIC_CONTAINMENT_BREACH", message, telemetry: { trace_id, profile_id, policy_id, failing_tier: "FHV1_AABB_ENVELOPE", eval_granularity, use_rogue_mask, full_text_passed, all_chunks_passed, failing_chunk_index, failed_dims_count, underflow_count, overflow_count, max_violation_delta, embedding_ms, eval_latency_ns } } }`. |
| `GET /api/v1/fhv1/benchmarks` | List persisted `fhv1_benchmark_runs` summaries (`[]` if table absent). |
| `POST /api/v1/fhv1/benchmarks/run` | Body: `{ profile_id, dataset_path? \| samples?, eval_granularity?, use_rogue_mask? }`. Executes benchmark (enforcing 0% overlap), persists run & traces, returns run summary. |
| `GET /api/v1/fhv1/benchmarks/{run_id}` | Full `summary_metrics_json` parsed dashboard payload (confusion matrix, per-category FAR/FRR/Recall/F1, granularity matrix, `failed_dims_count` histogram, 1,024D attribution). |
| `GET /api/v1/fhv1/traces` | Query `?run_id=&profile_id=&source_kind=&category=&passed=true\|false&page=1&page_size=50`. Paginated compact summaries (no 1024-float arrays). |
| `GET /api/v1/fhv1/traces/{trace_id}` | Joins all chunks of `trace_id` with immutable `fhv1_profiles`, returning lossless `f64` vectors + `dimensions[1024]` (`observed`, `observed_bits_hex`, `min`, `max`, `mean`, `status`, `violation_delta`, `delta_vs_mean`, `norm_pos`). |

---

## 4. Vertical Tracer Bullet Slices (Sequential Execution on `feat/fhv1-hector-filter-v1`)

> **Subagent Orchestration Rule**: Execute Slices 1 -> 8 sequentially on branch `feat/fhv1-hector-filter-v1` (since each crate layer depends on the prior). Within a Slice, parallelize independent file creation/test authoring across parallel sub-tasks, then merge and run the Slice's verification commands before making that Slice's commit.

### Slice 1 — Core `fhv1` Kernel (`sf-kernels`) & Raw `f64` Embedder Seam (`sf-proxy`)
* **Commit Scope**: `feat(kernels,proxy): add lossless f64 fhv1 AABB kernel and raw embedder seam`
* **Files to Create**:
  * `crates/sf-kernels/src/fhv1.rs`
  * `crates/sf-kernels/tests/fhv1_precision_test.rs`
* **Files to Modify**:
  * `crates/sf-kernels/src/lib.rs` (export `fhv1`; keep `crates/sf-kernels/Cargo.toml` 0-dep)
  * `crates/sf-proxy/src/normalize.rs` (`validate_raw_f64_slice`)
  * `crates/sf-proxy/src/embedder.rs` (`embed_batch_raw_f64` + fail-closed `MockBatchEmbedder`)
  * `crates/sf-proxy/src/tei.rs` (`TeiHttpEmbedder` & `TeiGrpcEmbedder`)
  * `crates/sf-proxy/src/lib.rs` (export `validate_raw_f64_slice`)
  * `tools/test_bge_m3_mps_server.py` (assert `normalize=False` preserves unnormalized output)
* **Specification**:
  1. `crates/sf-kernels/src/fhv1.rs`:
     * `Fhv1Error { BadDim { len: usize }, NonFinite { sample_index: usize, dim: usize }, EmptyCorpus, InvalidQuantiles }`
     * `MovementMetric { Variance, StdDev, Span }`, `MovementTier { ZeroSpan = 0, LowAnchor = 1, Moderate = 2, HighVolatility = 3, ExtremeMovement = 4 }`, `Fhv1Quantiles { pub p25: f64, pub p75: f64, pub p90: f64 }`.
     * `Fhv1ProfileStats`: `[f64; DIM]` arrays (`min`, `max`, `mean`, `span`, `variance`, `std_dev`), `movement_tier_codes: [u8; DIM]`, `quantiles: Fhv1Quantiles`, `sample_count: u64`, `polarity: u8`.
     * `compute_fhv1_profile_stats(rows, polarity, metric, quantiles)`: Welford online `mean` & population `variance = M2 / N` in `f64`, rejecting any non-finite value, plus `classify_movement_tiers` over `span > 0.0` dims (`span == 0.0` -> `ZeroSpan`).
     * `DimBoundStatus { InBounds, Underflow, Overflow, PrunedRogue }`, `Fhv1DimComparison` with `observed_bits: u64` (`f64::to_bits()`), `observed`, `min`, `max`, `mean`, `violation_delta`, `delta_vs_mean`, `norm_pos: Option<f64>`.
     * `Fhv1EvalGranularity { FullOnly, Clauses, FullMirror }`, `evaluate_fhv1_chunk`, `evaluate_fhv1_batch` (no short-circuit; `full_text_passed = chunks[0].chunk_passed`; `all_chunks_passed = chunks.iter().all(...)`; `overall_passed` per `D-03`).
  2. `crates/sf-proxy/src/normalize.rs`: `validate_raw_f64_slice(&[f64]) -> Result<[f64; DIM], NormalizeError>` (no L2 normalization, no `f32` cast).
  3. `crates/sf-proxy/src/embedder.rs` & `tei.rs`:
     * `BatchEmbedderClient::embed_batch_raw_f64(&self, texts: &[&str], normalize: bool) -> Result<Vec<[f64; DIM]>, String>`.
     * `MockBatchEmbedder::embed_batch_raw_f64` -> `Err("fail-closed: fhv1 raw float64 evaluation requires TeiHttpEmbedder (SF_EMBEDDER=http)".to_string())`.
     * `TeiGrpcEmbedder::embed_batch_raw_f64`: fail closed on `!normalize`; `normalize == true` delegates to `embed_batch_f32` + `f64::from`.
     * `TeiHttpEmbedder::embed_batch_raw_f64`: posts `{"inputs": texts, "normalize": normalize}`, parses JSON numbers with `number.as_f64()`, validates with `validate_raw_f64_slice`.
* **TDD & Verification**:
  * 1-ULP (`from_bits(lo.to_bits() - 1)`) and 16-ULP rejection, Welford stability, quantile tiers, `use_rogue_mask` 1024 vs 1015, `NaN`/`Inf` fail-closed, `mean` non-interference, and local `TcpListener` stub HTTP tests for `TeiHttpEmbedder` (`normalize: true/false`).
  * Run: `cargo fmt --all -- --check && cargo clippy --workspace --all-targets -- -D warnings && cargo test --workspace && uv run --script tools/test_bge_m3_mps_server.py`.

---

### Slice 2 — LanceDB `fhv1_*` Schemas, Store & Lossless Exporter (`sf-storage`)
* **Commit Scope**: `feat(storage): add fhv1 LanceDB tables, store, and lossless xlsx/zip/csv/parquet exporter`
* **Files to Create**:
  * `crates/sf-storage/src/fhv1_schema.rs`
  * `crates/sf-storage/src/fhv1_calibration.rs`
  * `crates/sf-storage/src/fhv1_store.rs`
  * `crates/sf-storage/src/fhv1_export.rs`
  * `crates/sf-storage/tests/fhv1_roundtrip_test.rs`
* **Files to Modify**:
  * `Cargo.toml` (`rust_xlsxwriter`, `parquet = "=58.4.1"`, `zip` in `[workspace.dependencies]`)
  * `crates/sf-storage/Cargo.toml` (add `rust_xlsxwriter`, `parquet`, `zip`, `serde`, `serde_json` from workspace)
  * `crates/sf-storage/src/lib.rs` (export `fhv1_*` modules)
* **Specification**:
  1. `fhv1_schema.rs`: exact Arrow `=58.4.1` schemas from §3.2 (`Float64` `FixedSizeList`, `FixedSizeBinary(32)`).
  2. `fhv1_store.rs`: `Fhv1Store { uri: String }` with lazy table opening/creation (reads on missing tables return empty results without error; writes create or append tables without touching `domain_hypercubes`). Supports `save_calibration_profile` (auto-increment `version` per `policy_id`), `list_profiles`, `get_profile`, `list_samples_for_profile`, `save_benchmark_run`, `list_benchmark_runs`, `get_benchmark_run`, `append_audit_traces`, `query_audit_trace_summaries` (paginated, no `[f64; 1024]` vector), `get_trace_drilldown`.
  3. `fhv1_export.rs`:
     * `.xlsx` (`rust_xlsxwriter`): Sheet `Summary_Envelope` (1,024 rows: `dim`, `is_rogue_dim`, `min`, `max`, `mean`, `span`, `variance`, `std_dev`, `movement_tier`) + Sheet `Raw_Samples_Matrix` (`sample_id`, `policy_id`, `strategy_tag`, `source_ref`, `raw_text`, `dim_0..dim_1023`), raw `worksheet.write_number(...)` IEEE 754 `f64`.
     * Auto-split when `samples.len() > max_rows_per_xlsx` (default `10_000`) into `part_001.xlsx`, `part_002.xlsx`, ... bundled in `.zip` via `zip::ZipWriter`.
     * `.csv`: `f64::to_string()` lossless precision.
     * `.parquet`: `parquet::arrow::ArrowWriter` over Arrow `=58.4.1` `RecordBatch`.
* **TDD & Verification**:
  * `fhv1_roundtrip_test.rs`: 0-ULP `to_bits()` round-trip across LanceDB write -> read, `.xlsx` (unzip `xl/worksheets/sheet*.xml` via `zip::ZipArchive` and parse `<v>` cells as `f64` checking `to_bits()`), auto-split `.zip` (`max_rows_per_xlsx = 2` on `5` rows), `.csv`, and `.parquet` (`ParquetRecordBatchReaderBuilder`).
  * Run: `cargo fmt --all -- --check && cargo clippy --workspace --all-targets -- -D warnings && cargo test --workspace`.

---

### Slice 3 — Multi-Granularity Calibration Pipeline, CLI & Offline-Tested `--augment-llm`
* **Commit Scope**: `feat(proxy,bench,tools): add deterministic multi-granularity fhv1 calibration pipeline and CLI`
* **Files to Create**:
  * `crates/sf-proxy/src/fhv1_pipeline.rs`
  * `crates/sf-bench/src/fhv1_corpus.rs`
  * `crates/sf-bench/src/bin/fhv1_calibrate.rs`
  * `tools/augment_fhv1_corpus.py`
  * `tools/test_augment_fhv1_corpus.py` (offline contract & mock HTTP test suite)
* **Files to Modify**:
  * `crates/sf-proxy/src/lib.rs` (export `fhv1_pipeline`)
  * `crates/sf-bench/Cargo.toml` (add `sha2 = { workspace = true }`, `[[bin]] name = "fhv1_calibrate"`)
  * `crates/sf-bench/src/lib.rs` (export `fhv1_corpus`)
* **Specification**:
  1. `fhv1_pipeline.rs` (shared by `sf-proxy` & `sf-bench`):
     * `ExpandedChunk { pub strategy_tag: &'static str, pub text: String, pub text_sha256: [u8; 32] }`.
     * `expand_text_multi_granularity(raw_text: &str)`: emits `chunk[0]` (`full_doc` via `InputNormalizer::normalize(raw_text).text`, plus decoded Base64 payloads), `paragraph`, `sentence`, `clause_opt2c`, `window_w5_s3`, `window_w10_s5`, `window_w20_s10`, `window_w40_s20`, `atomic_phrase`, `surface_norm_variant`, deduplicated deterministically by `(strategy_tag, text_sha256)`.
     * `expand_for_granularity(raw_text, granularity)` implements `D-03` (`FullOnly` -> `[normalized_full_text]`, `Clauses` -> `[normalized_full_text] + clause_opt2c`, `FullMirror` -> full 10-strategy set).
     * Shared async helpers `calibrate_fhv1_corpus(...)` and `evaluate_fhv1_input(...)`.
  2. `crates/sf-bench/src/fhv1_corpus.rs`: expanded canonical seed corpora for `python` [EN] and `receta` [ES] + generic `.txt`/`.md`/`.jsonl`/directory ingestion.
  3. `tools/augment_fhv1_corpus.py` (`uv` PEP 723, `httpx`, `pydantic`): `--provider <gemini|openai|deepseek|groq|ollama>` is **mandatory** (omitting it exits non-zero listing keys found in `.env` following `env_config.rs` precedence). Writes deterministic `data/fhv1_augmented/<policy_id>_<sha256>.jsonl` + `.manifest.json` cache.
  4. `crates/sf-bench/src/bin/fhv1_calibrate.rs`: calibrates corpora via `embed_batch_raw_f64` into `fhv1_calibration_samples` + `fhv1_profiles` (preserving `domain_hypercubes`!) and optional `--export-xlsx`.
* **TDD & Live Verification**:
  * Rust unit/integration tests with `TestRawF64Embedder` + `tools/test_augment_fhv1_corpus.py` (verifying `.env` parsing, missing `--provider` error listing detected keys, mocked HTTP OpenAI-compatible response, and deterministic SHA-256 JSONL cache hit).
  * **Live deterministic run against `:8080` (WITHOUT `--augment-llm`)**: start `:8080` non-interactively, run `fhv1_calibrate` for `python` and `receta` into `data/sf-lancedb`, verify `fhv1_profiles` + `fhv1_calibration_samples` created while `domain_hypercubes` remains 66 intact rows, then stop `:8080`.
  * Run: `cargo fmt --all -- --check && cargo clippy --workspace --all-targets -- -D warnings && cargo test --workspace && uv run --script tools/test_augment_fhv1_corpus.py`.

---

### Slice 4 — Offline 4-Quadrant Adversarial Benchmark Generator, Runner & Efficacy Analytics
* **Commit Scope**: `feat(bench,tools): add offline 4-quadrant fhv1 benchmark suite and efficacy analytics`
* **Files to Create**:
  * `tools/fhv1_benchmark_banks.json` (curated offline real-text banks)
  * `tools/generate_fhv1_benchmark.py` (`uv` PEP 723)
  * `tools/test_generate_fhv1_benchmark.py`
  * `crates/sf-bench/src/fhv1_eval.rs`
  * `crates/sf-bench/src/bin/fhv1_benchmark.rs`
  * `crates/sf-bench/tests/fhv1_e2e_test.rs`
* **Files to Modify**:
  * `crates/sf-bench/Cargo.toml` (`[[bin]] name = "fhv1_benchmark"`)
  * `crates/sf-bench/src/lib.rs` (export `fhv1_eval`)
* **Specification**:
  1. `tools/generate_fhv1_benchmark.py`: 100% offline deterministic by default (`--fetch-hf` strictly opt-in). Combines `CLINC OOS` + `deepset` from `suite2_prompts.json` + `tools/fhv1_benchmark_banks.json` + deterministic structural combinatorics/obfuscations to emit `>= 400` real prompts/domain (`>= 100` each: `IN_DOMAIN_VALID`, `OUT_OF_DOMAIN_BENIGN`, `HYBRID_BOUNDARY`, `ADVERSARIAL_FUZZING`), enforcing `0%` exact and NFKC-lowercased SHA-256 intersection against calibration inputs/chunks, writing JSONL + `.manifest.json`.
  2. `crates/sf-bench/src/fhv1_eval.rs` & `fhv1_benchmark.rs`:
     * Enforces the `0%` overlap check fail-closed in Rust before embedding.
     * Evaluates via `embed_batch_raw_f64(..., profile.normalize)` across `full_only`, `clauses`, and `full_mirror` (default `full_mirror`) plus `use_rogue_mask = false (1024D)` vs `true (1015D)`.
     * Computes Confusion Matrix (`TP`, `TN`, `FP`, `FN`), Accuracy, Precision, Recall, F1, `FAR/FPR`, `FRR/FNR` overall & per-category, granularity comparison table, `failed_dims_count` histogram, and 1,024D violation attribution (`in_domain_fail_counts[1024]`, `oob_catch_counts[1024]`) paired with `movement_tier_codes`.
     * Persists `fhv1_benchmark_runs`, all chunk rows in `fhv1_audit_traces` (`source_kind = "BENCHMARK"`), and `reports/fhv1_<policy>_<run_id>.json`.
* **TDD & Live Verification**:
  * `fhv1_e2e_test.rs`: overlap fail-closed test, confusion matrix & granularity differentiation (`FullOnly` vs `Clauses` vs `FullMirror`), LanceDB persistence.
  * **Live deterministic benchmark run against `:8080`**: generate datasets (`>= 400` entries each for `python` and `receta`), execute `fhv1_benchmark` against `:8080`, verify `fhv1_benchmark_runs` + `fhv1_audit_traces` populated, clean up `:8080` PID.
  * Run: `cargo fmt --all -- --check && cargo clippy --workspace --all-targets -- -D warnings && cargo test --workspace && uv run --script tools/test_generate_fhv1_benchmark.py`.

---

### Slice 5 — `sf-proxy` REST APIs (`A2`, `E1`) & `/api/v1/chat` Integration (`3A+3B`)
* **Commit Scope**: `feat(proxy): expose /api/v1/fhv1 REST APIs and backward-compatible chat integration`
* **Files to Create**:
  * `crates/sf-proxy/src/fhv1_api.rs`
  * `crates/sf-proxy/tests/fhv1_api_e2e_test.rs`
* **Files to Modify**:
  * `crates/sf-proxy/src/handler.rs` (`ProxyAppState` adds `pub fhv1_store: Option<Arc<Fhv1Store>>`; mount `/api/v1/fhv1/*` with Axum `0.8` `{profile_id}`, `{run_id}`, `{trace_id}`)
  * `crates/sf-proxy/src/cors.rs` (expose `content-disposition`, `x-sf-trace-id`, `x-sf-fhv1-decision`)
  * `crates/sf-proxy/src/chat_api.rs` (`filter_mode`, `fhv1_profile_id`, `fhv1_granularity`, `fhv1_use_rogue_mask`, `fhv1_ingress_breach`, `3hm_plus_fhv1` dual-trace persistence)
  * `crates/sf-proxy/src/lib.rs` (export `fhv1_api`)
  * `crates/sf-proxy/src/bin/sf_proxy.rs` (initialize `Some(Arc::new(Fhv1Store::new(&lancedb_uri)))` lazily)
  * `crates/sf-proxy/tests/gateway_s1_e2e.rs` (add `fhv1_store: None` to all 5 `ProxyAppState` struct literals)
  * `crates/sf-bench/src/bin/load_benchmark.rs` (add `fhv1_store: None` to `ProxyAppState` literal at L91)
* **TDD & Verification**:
  * `fhv1_api_e2e_test.rs`: lazy empty startup (`GET /profiles` -> `200 []`), calibrate -> evaluate -> trace drill-down (`observed_bits_hex` 0-ULP parity), export `.xlsx`/`.zip`/`.csv`/`.parquet`, `/api/v1/chat` in `3hm_default`, `fhv1`, and `3hm_plus_fhv1` (verifying `3HM` breach STILL persists `fhv1_audit_traces` `REALTIME_CHAT`).
  * Run: `cargo fmt --all -- --check && cargo clippy --workspace --all-targets -- -D warnings && cargo test --workspace`.

---

### Slice 6 — Frontend View 1 (`Playground Realtime` + `fhv1` Switch + Direct Lab + Live Audit Log)
* **Commit Scope**: `feat(frontend): add fhv1 mode switch, direct sentence lab, and live audit panel to Playground`
* **Files to Create**:
  * `frontend/src/domain/fhv1.ts`
  * `frontend/src/domain/fhv1.test.ts`
  * `frontend/src/gateway/fhv1Client.ts`
  * `frontend/src/ui/Fhv1LiveAuditPanel.tsx`
  * `frontend/src/ui/StudioShell.tsx`
* **Files to Modify**:
  * `frontend/src/main.tsx` (render `<StudioShell />`)
  * `frontend/src/domain/types.ts` (add `'FHV1_AABB_ENVELOPE'`, `Fhv1FilterMode`, `Fhv1EvalGranularity`, `Fhv1ChatTelemetry`)
  * `frontend/src/domain/request.ts` (omit `filter_mode` and `fhv1_*` when unset or `'3hm_default'`)
  * `frontend/src/domain/session.ts`
  * `frontend/src/domain/breach.ts` (map `fhv1_ingress_breach` in `parseChatBreach`)
  * `frontend/src/ui/BreachCard.tsx`
  * `frontend/src/ui/Playground.tsx`
* **Strict UI Guardrails**:
  * Obey `tsconfig.app.json` (`strict`, `noUncheckedIndexedAccess`, `verbatimModuleSyntax`, `erasableSyntaxOnly` — NO TS `enum`).
  * Keep all 11 protected selectors, `<ol aria-label="Messages">` (`overflow-y: auto`), `<aside aria-label="Live tuning">` (`w-60`, `overflow-y: auto`), `#root > div` (`h-[100dvh] overflow-hidden`), `Domain id` (`11` canonical options), and `formatGate` (`.toFixed(4)`) intact. `Fhv1LiveAuditPanel` starts collapsed by default. `fhv1` numbers use `formatLosslessF64` (`String(v)`, zero `.toFixed()`).
* **TDD & Verification**:
  * `fhv1.test.ts` + extended `Playground.test.tsx`.
  * Run: `pnpm --dir frontend lint && pnpm --dir frontend build && pnpm --dir frontend test`, plus live Playwright regression (`playground.spec.ts`: 9 passed) using non-interactive §1.4 runbook.

---

### Slice 7 — Frontend View 2 (`FHV1 Variance & Envelope Studio` + `echarts`)
* **Commit Scope**: `feat(frontend): add FHV1 Variance & Envelope Studio with ECharts canvas plots`
* **Files to Create**:
  * `frontend/src/ui/Fhv1EChartsCanvas.tsx` (`echarts/core` + `CanvasRenderer` + `import type`)
  * `frontend/src/ui/Fhv1VarianceStudio.tsx`
  * `frontend/src/ui/Fhv1VarianceStudio.test.tsx`
* **Files to Modify**:
  * `frontend/package.json` & `frontend/pnpm-lock.yaml` (`pnpm --dir frontend add echarts`)
  * `frontend/src/ui/StudioShell.tsx` (mount View 2)
* **Specification**:
  * Top bar: profile selector, calibrate trigger (`POST /api/v1/fhv1/calibrate` text/file upload + `normalize` + `use_rogue_mask_default`), metric toggle (`variance` | `std_dev` | `span`), editable `P25`/`P75`/`P90` quantile cutoffs, export buttons (`.xlsx`/`.csv`/`.parquet`).
  * Canvas plots (`echarts/core`): `[min_d, max_d]` envelope band + `mean_d` line with DataZoom & lossless tooltip; dimension movement ranking & tier distribution with rogue markers.
  * Full-precision 1,024-row sortable/filterable table (`dim`, `is_rogue`, `min`, `max`, `mean`, `span`, `variance`, `std_dev`, `movement_tier`) with zero `.toFixed()` and 1-click exact clipboard copy.
* **Verification**: `pnpm --dir frontend lint && pnpm --dir frontend build && pnpm --dir frontend test`.

---

### Slice 8 — Frontend View 3 (`FHV1 Benchmark & Audit Explorer`), Full Playwright E2E & Doc-Sync
* **Commit Scope**: `feat(frontend,docs): add FHV1 Benchmark & Audit Explorer, E2E suite, and sync docs`
* **Files to Create**:
  * `frontend/src/ui/Fhv1BenchmarkExplorer.tsx`
  * `frontend/src/ui/Fhv1BenchmarkExplorer.test.tsx`
  * `frontend/e2e/fhv1.spec.ts`
* **Files to Modify**:
  * `frontend/src/ui/StudioShell.tsx` (mount View 3 + trace jump link from View 1)
  * `CONTEXT.md` (add `FiltroHectorV1`, `Fhv1EnvelopeProfile`, `MovementTier`, `SymmetricInferencePipeline`, `Fhv1AuditTrace`)
  * `CONTEXT-MAP.md` (document `fhv1` responsibilities across crates)
  * `architecture_spec.md` (add ADR-006 `fhv1` strict AABB `f64` gate, `eval_granularity` contract, 4 `fhv1_*` tables, `/api/v1/fhv1/*` & extended `/api/v1/chat`)
  * `CHANGELOG.md` (append `fhv1` capabilities under `## [Unreleased]`; keep version `0.2.1`)
  * `TASKS.md` (mark all 8 slices `[x]`, `status: "DONE"`)
* **Full Milestone Verification Gate (Mandatory before Approval Gate)**:
  1. `cargo fmt --all -- --check`
  2. `cargo clippy --workspace --all-targets -- -D warnings`
  3. `cargo test --workspace`
  4. `pnpm --dir frontend lint`
  5. `pnpm --dir frontend build`
  6. `pnpm --dir frontend test`
  7. `uv run --script tools/test_bge_m3_mps_server.py && uv run --script tools/test_augment_fhv1_corpus.py && uv run --script tools/test_generate_fhv1_benchmark.py`
  8. Non-interactive `:8080` + `:8088` startup -> `pnpm --dir frontend test:e2e` (all `playground.spec.ts` 9 + `fhv1.spec.ts` tests green) -> PID cleanup
  9. `/Users/hbauzan/treepwood/fabrica_de_software/agent.sh validate --task-file TASKS.md`
  10. `/Users/hbauzan/treepwood/fabrica_de_software/agent.sh notify --task-file TASKS.md`

---

## 5. Protocol Invariants & Approval Gate
* **Exclusive Authorship**: `hbauzan <hbauzan@gmail.com>`. Zero `Co-authored-by:` trailers.
* **Lexical Hygiene**: NEVER mention external assistants, bots, models, or editors in source code, comments, tests, docs, or commit messages.
* **Git Safety**: NEVER `git add -A` (stage explicit file paths only; never stage `repomix-output.xml`, `data/`, `.env`, `.DS_Store`). NEVER `git push` or `merge` to `main` — stop at the Approval Gate after Slice 8 completes and passes all checks.
