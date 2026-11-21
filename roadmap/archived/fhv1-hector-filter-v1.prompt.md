# TASK SPECIFICATION: EXHAUSTIVE COORDINATE-WISE BOUNDING FILTER `fhv1` ("FILTRO HÉCTOR V1")

## 1. Project Context & Current State (Ground Truth)

* **Repository**: `3hm-dimensional-fw` (`Three-Headed Semantic Firewall`), baseline `v0.2.1` (`main` @ `f2ac3dd`).
* **Active Runtime Services & Ports**:
  * **Backend Gateway (`crates/sf-proxy`)**: `http://127.0.0.1:8088` (`/v1/chat/completions`, `/api/v1/chat`, `/api/v1/upstream/env`).
  * **Frontend SPA (`frontend/`)**: `http://127.0.0.1:5173` (React 19 + TypeScript + Vite 8 + Tailwind CSS v4).
  * **Native Embedder (`tools/bge_m3_mps_server.py`)**: `http://127.0.0.1:8080` (`BAAI/bge-m3`, Apple Silicon Metal `mps`, strict `torch.float32`, RFC-003). Already accepts `{"inputs": [...], "truncate": bool, "normalize": bool}`.
  * **Vector Store (`data/sf-lancedb`)**: LanceDB `0.40.0` (pinned Arrow `=58.4.1`, imported exclusively via `lancedb::arrow::{arrow_array, arrow_buffer, arrow_schema}`), existing table `domain_hypercubes` (66 canonical locks).
  * **Legacy Diagnostic Studio (`crates/sf-ui`)**: `http://127.0.0.1:3000` (embedded HTML, mock embedder — out of scope for `fhv1` GUI).
* **Canonical Toolchains (Strict — Zero Mixing)**:
  * **Rust (`rust-toolchain.toml`: `1.94.1`)**: `cargo` exclusively (`cargo fmt`, `cargo clippy`, `cargo test`, `cargo build`).
  * **Frontend (`frontend/`)**: `pnpm` (`11.8.0`) exclusively (`pnpm test`, `pnpm lint`, `pnpm build`, `pnpm test:e2e`).
  * **Python (`tools/`)**: `uv` exclusively (PEP 723 inline `# /// script` metadata). Zero `pip`/`npm`.
* **Verified Baseline Quality Gate (`v0.2.1`)**:
  * Rust workspace: `cargo fmt --all -- --check` (0), `cargo clippy --workspace --all-targets -- -D warnings` (0), `cargo test --workspace` (**111 passed, 0 failed**).
  * Frontend: `pnpm --dir frontend lint` (0), `pnpm --dir frontend build` (0), `pnpm --dir frontend test` (**44 passed**), `pnpm --dir frontend test:e2e` (**9 passed** against calibrated LanceDB + live `bge-m3` HTTP).
* **Verified Architectural Gaps Motivating `fhv1`**:
  1. `crates/sf-bench/src/canonical_corpus.rs` calibrates domains from only 16 raw sentences with zero multi-granularity expansion.
  2. `crates/sf-storage/src/calibration.rs` computes `lo`, `hi`, and `mu` (mean), but discards raw calibration rows `[N × 1024]` and `schema.rs` does not persist `mu`, `variance`, `std_dev`, or `span` in LanceDB.
  3. `crates/sf-proxy/src/tei.rs` always coerces JSON coordinates through `validate_and_normalize_f32_slice` (forcing L2 unit normalization and narrowing to `f32`).
  4. `frontend/src/domain/format.ts` (`.toFixed(4)`) truncates numeric values visually.
  5. `sf-proxy` truncates `failing_coordinates` to `SF_MAX_TELEMETRY_COORDS=8` and does not persist forensic evaluation audit traces.
  6. `SCPB-220` (`Suite 1`) is a synthetic algebraic smoke test (`ChaCha8Rng`), and `Suite 2` (`oos_benchmark.rs`) lacks a four-quadrant real-text stress suite (`ID holdout`, `OOD`, `Hybrid 50/50`, `Adversarial/Fuzzing/OWASP LLM01`).

---

## 2. Objective, Scope, Ubiquitous Terminology & Design Decisions

### 2.1 Primary Objective
Introduce an additional, strictly deterministic semantic firewall filter named **`filtro hector v1`** (short code: **`fhv1`**) to empirically and deterministically evaluate whether an **Exhaustive Coordinate-Wise Axis-Aligned Bounding Box (AABB / Strict $\ell_\infty$ Envelope)** calibrated over a maximally expanded domain spectrum separates in-domain, out-of-domain, hybrid, and adversarial inputs, and precisely identify its operational limits through lossless forensic telemetry and visual dispersion analysis.

### 2.2 Standard Industry Terminology Mapping (Aligned with `CONTEXT.md`)

| Domain Concept | Standard IT / ML / Security Term | Contract Role in `3hm-dimensional-fw` |
| :--- | :--- | :--- |
| **`filtro hector v1` (`fhv1`)** | **Exhaustive Coordinate-Wise Axis-Aligned Bounding Box (AABB / Strict $\ell_\infty$ Envelope Gate)** | Standalone selectable filter (`PASS` $\iff \forall d \in \mathcal{D}_{eval}: \min_d \le x_d \le \max_d$). Distinct from `3HM` Mode C (`SubspaceCoordinateQuorum`) and future Holistic Resonance Gate. |
| **Zero Rounding / All Engine Decimals** | **RFC-003 Lossless Native IEEE-754 Precision Policy** | Zero rounding, zero `f16`/`bf16`, zero `.toFixed(N)` across storage (`Float64`), compute, JSON API, `.xlsx`/`.csv`/`.parquet` exports, and `fhv1` GUI tables/tooltips. |
| **Target Delimited Domain** | **Target Domain Policy Scope (`Fhv1PolicyScope`)** | Versioned corpus definition representing the exact semantic domain to delimit. |
| **Exhaustive Multi-Way Processing** | **Multi-Granularity Corpus Expansion & Manifold Coverage Calibration Pipeline** | Offline pipeline extracting maximum valid coordinate spectrum per domain. |
| **Chunk-by-Dimension Spreadsheet** | **Raw Calibration Feature Matrix (`N × D`) & Lossless `.xlsx` Export** | Persisted in LanceDB (`fhv1_calibration_samples`) and exported lossless via `rust_xlsxwriter`. |
| **Min / Max / Average per Dimension** | **Per-Dimension Statistical Envelope Profile (`Fhv1EnvelopeProfile`)** | Immutable versioned bounds `[min_d, max_d]` + raw `mean_d` + dispersion (`span_d`, `variance_d`, `std_dev_d`, `movement_tier_d`). |
| **Dimension Variance / Movement Study** | **Dimensional Dispersion & Feature Volatility Profiler** | Quantile-based movement categorization (`ZERO_SPAN`, `LOW_ANCHOR`, `MODERATE`, `HIGH_VOLATILITY`, `EXTREME_MOVEMENT`). |
| **4-Category Stress-Test Suite** | **Deterministic 4-Quadrant Adversarial & Boundary Benchmark (`ID`, `OOD`, `Hybrid 50/50`, `Adversarial/Fuzzing/OWASP LLM01`)** | Real-text evaluation embedded through live `BAAI/bge-m3` FP32 (zero synthetic `ChaCha8Rng` vectors), `>= 400` entries per domain. |
| **Symmetric Input Processing** | **Symmetric Inference Pipeline (Zero Train-Serving Skew)** | Applies `InputNormalizer` + selectable `eval_granularity` (`full_only` \| `clauses` \| `full_mirror`) with strict `ALL_CHUNKS_PASS` aggregation and non-short-circuiting audit. |
| **Audit Trail for Pattern Discovery** | **Immutable Forensic Per-Dimension Audit Log (`fhv1_audit_traces`)** | Stores lossless input vectors, `profile_id`, verdict, per-chunk outcomes, violation counts, and exact per-dimension comparison on drill-down. |

### 2.3 Locked Architectural Decisions (All Approved — Do Not Reopen)

| ID | Decision | Locked Contract |
| :--- | :--- | :--- |
| **D-01 (`1C`)** | Filter boundary & Rogue Mask | `fhv1` coexists as an independent selectable filter (`filter_mode: "3hm_default" \| "fhv1" \| "3hm_plus_fhv1"`). Default evaluates **all 1,024 dimensions** (`use_rogue_mask = false`), with configurable toggle `use_rogue_mask = true` (`1015` dims pruning the 9 `UNIVERSAL_NOISE_INDICES`). Existing `3HM` path stays untouched. |
| **D-02 (`2C`)** | Calibration expansion | Mandatory deterministic multi-granularity pipeline (full text, paragraphs, sentences, `InputNormalizer`, `ClauseSegmenter`, multi-scale sliding windows, atomic terms/phrases) **plus** optional offline synthetic LLM augmentation (`--augment-llm` via `.env` providers, persisted as immutable SHA-256 JSONL prior to embedding). |
| **D-03 (`3A-cfg`)** | Evaluation symmetry & aggregation | Configurable `eval_granularity`: `full_only` \| `clauses` \| `full_mirror` (default `full_mirror` for benchmark symmetry). Verdict uses strict fail-closed `ALL_CHUNKS_PASS`. **No early-exit** in `fhv1`: every chunk is evaluated and audited, recording both `full_text_passed` and `all_chunks_passed`. |
| **D-04 (`4A` + `4.1-B`)** | Precision & L2 Normalization | Store `fhv1` vectors and statistics in lossless IEEE 754 `Float64` (`Arrow DataType::Float64`), preserving exact `f32` bits from `BAAI/bge-m3` and supporting future native `f64` engines. Per-profile configurable `normalize: bool` (default `true`, optional `false` via new raw embedder method without Rust re-normalization). Zero `.toFixed()` in `fhv1` APIs/UI/exports. |
| **D-05 (`5A` + `A2`)** | Unified GUI & Realtime modes | Extend `frontend/` SPA (`:5173`) against new `sf-proxy` (`:8088`) endpoints with 3 views: (1) **Playground Realtime** supporting both `/api/v1/chat` protection and direct LLM-free `/api/v1/fhv1/evaluate` lab + live Audit Log; (2) **FHV1 Variance & Envelope Studio**; (3) **FHV1 Benchmark & Audit Explorer**. |
| **D-06 (`6A` + `D1` + `E1`)** | Storage, `.xlsx` & Audit API | Persist all `fhv1` data in 4 dedicated LanceDB tables (`fhv1_calibration_samples`, `fhv1_profiles`, `fhv1_benchmark_runs`, `fhv1_audit_traces`) inside `data/sf-lancedb`. Export lossless 2-sheet `.xlsx` (`Summary_Envelope` + `Raw_Samples_Matrix`, auto-split when rows `> 10,000`) plus lossless `.csv`/`.parquet`. Audit API uses paginated summaries + per-`trace_id` 1024D drill-down. |
| **D-07 (`B1` + `C1`)** | Decision literalism & Variance tiers | Only `[min_d, max_d]` decides `PASS`/`FAIL` (`ALLOWLIST` default; `polarity` column preserved). `mean_d` (`average`) never alters `PASS`/`FAIL`; it is computed and audited (`delta_vs_mean_d`, side, relative position). Movement tiers use configurable quantile bands (`ZERO_SPAN`, `LOW_ANCHOR` P0–P25, `MODERATE` P25–P75, `HIGH_VOLATILITY` P75–P90, `EXTREME_MOVEMENT` P90–P100) toggleable across `variance`, `std_dev`, and `span`. |
| **D-08 (`F1`)** | Approved new dependencies | Rust: `rust_xlsxwriter` (pure Rust, raw IEEE 754 `f64` writer). Frontend (`pnpm`): one `<canvas>`-capable charting library (`echarts` or `uplot`) for 1,024+ coordinate plots with zoom/pan/full-precision tooltips. Python (`tools/`): `uv` PEP 723 scripts for offline adversarial benchmark generation and optional `--augment-llm`. |
| **D-09 (`7A` + `G1`)** | Initial scope & Benchmark floor | Generic CLI/GUI ingestion for any user-supplied domain corpus, with initial deterministic experiments calibrated on expanded canonical domains (minimum: `python` [EN] and `receta` [ES]). Mandatory **`>= 400` real text test entries per domain** (`>= 100` per quadrant), 0% overlap with calibration. |

### 2.4 Out of Scope (Explicitly Forbidden in This Milestone)
* Modifying scoring logic, thresholds, `domain_hypercubes` schema, or published rates of `3HM` (`L1`, `L2`, `L3 Mode A/B/C`, `PairwiseDifferentialLock`, `Suite 1`, `Suite 2`).
* Implementing width-weighted *Holistic Resonance Gate* (`roadmap/future-holistic-resonance-gate.md`) or *Egress Semantic Amplification* (`v1.1+`).
* Modifying `crates/sf-ui` (`:3000`) beyond keeping workspace compilation and tests green.

---

## 3. Ground Truth: Files, Contracts & Invariants

### 3.1 Primary Files to Create / Modify

| Subsystem | New Files | Modified Files |
| :--- | :--- | :--- |
| **`sf-kernels`** | `crates/sf-kernels/src/fhv1.rs`, `crates/sf-kernels/tests/fhv1_precision_test.rs` | `crates/sf-kernels/src/lib.rs` |
| **`sf-storage`** | `crates/sf-storage/src/fhv1_schema.rs`, `crates/sf-storage/src/fhv1_calibration.rs`, `crates/sf-storage/src/fhv1_store.rs`, `crates/sf-storage/src/fhv1_export.rs`, `crates/sf-storage/tests/fhv1_roundtrip_test.rs` | `crates/sf-storage/src/lib.rs`, `crates/sf-storage/Cargo.toml`, root `Cargo.toml` |
| **`sf-proxy`** | `crates/sf-proxy/src/fhv1_api.rs`, `crates/sf-proxy/src/fhv1_pipeline.rs`, `crates/sf-proxy/tests/fhv1_api_e2e_test.rs` | `crates/sf-proxy/src/embedder.rs`, `crates/sf-proxy/src/tei.rs`, `crates/sf-proxy/src/normalize.rs`, `crates/sf-proxy/src/chat_api.rs`, `crates/sf-proxy/src/handler.rs`, `crates/sf-proxy/src/lib.rs`, `crates/sf-proxy/src/bin/sf_proxy.rs` |
| **`sf-bench`** | `crates/sf-bench/src/fhv1_corpus.rs`, `crates/sf-bench/src/fhv1_eval.rs`, `crates/sf-bench/src/bin/fhv1_calibrate.rs`, `crates/sf-bench/src/bin/fhv1_benchmark.rs`, `crates/sf-bench/tests/fhv1_e2e_test.rs` | `crates/sf-bench/src/lib.rs`, `crates/sf-bench/Cargo.toml` |
| **`tools/` (`uv`)** | `tools/augment_fhv1_corpus.py`, `tools/generate_fhv1_benchmark.py` | — |
| **`frontend/` (`pnpm`)** | `frontend/src/domain/fhv1.ts`, `frontend/src/domain/fhv1.test.ts`, `frontend/src/gateway/fhv1Client.ts`, `frontend/src/ui/Fhv1VarianceStudio.tsx`, `frontend/src/ui/Fhv1BenchmarkExplorer.tsx`, `frontend/src/ui/Fhv1LiveAuditPanel.tsx`, `frontend/e2e/fhv1.spec.ts` | `frontend/package.json`, `frontend/src/ui/Playground.tsx`, `frontend/src/domain/types.ts`, `frontend/src/domain/request.ts`, `frontend/src/domain/session.ts` |
| **Docs & Governance** | `roadmap/fhv1-hector-filter-v1.prompt.md` | `CONTEXT.md`, `CONTEXT-MAP.md`, `architecture_spec.md`, `TASKS.md`, `CHANGELOG.md` |

### 3.2 Non-Negotiable Engineering Invariants

1. **Zero-Rounding End-to-End (RFC-003 Extended)**:
   * Every coordinate, bound (`min`, `max`), average (`mean`), dispersion (`span`, `variance`, `std_dev`), and delta MUST retain full native IEEE 754 precision.
   * Reject `NaN` / `Inf` fail-closed at every boundary (calibration ingestion, embedder response, evaluation input).
   * Unit test MUST verify a 1-ULP / 16-ULP micro-gap in `fhv1` rejects deterministically and survives LanceDB write->read, HTTP JSON serialization, and `.xlsx` export->read with **0 ULP loss** (`to_bits()` equality).
2. **Zero Regressions on Existing `3HM` & Frontend Testing Contract**:
   * All **111 Rust tests**, **44 Vitest tests**, and **9 Playwright E2E tests** MUST pass without weakening assertions.
   * Existing `Playground.tsx` default view MUST preserve **verbatim** all accessible selectors required by `frontend/src/ui/Playground.test.tsx` and `frontend/e2e/playground.spec.ts`:
     | Control | Required Accessible Selector | Invariant |
     | :--- | :--- | :--- |
     | Gateway base | `getByRole('textbox', { name: 'Gateway base' })` | Immutable name & default `http://127.0.0.1:8088` |
     | Domain selector | `getByRole('combobox', { name: 'Domain id' })` | 11 canonical options + custom preservation |
     | Prompt box | `getByRole('textbox', { name: 'Prompt' })` | Immutable name; Enter sends, Shift+Enter newline |
     | Send button | `getByRole('button', { name: /Send\|Sending/ })` | Exact text |
     | Messages list | `getByRole('list', { name: 'Messages' })` | `<ol>` with `overflow-y: auto` |
     | Live tuning drawer | `getByRole('complementary', { name: 'Live tuning' })` | Fixed `w-60` (`240px`), `overflow-y: auto` |
     | Viewport shell | `#root > div` | `h-[100dvh]`, `overflow: hidden` |
     | Apply overrides | `getByRole('checkbox', { name: 'Apply overrides' })` | Default `false` (`overrides` omitted when unarmed) |
     | Sliders | `L1 cosine threshold`, `L2 clause threshold`, `Quorum K`, `Epsilon` | Immutable accessible names & ranges |
     | Env controls | `Usar keys de .env`, `Cargar de .env`, `Provider`, `Base URL`, `Model`, `API key` | Immutable accessible names |
     | Preset chips | `Python generator`, `Risotto L1`, `Piggyback L2`, `Spectral L3` | Immutable names & payloads |
3. **Strict Train/Test Isolation**:
   * Benchmark generator and runner MUST enforce **0% text intersection** (exact and NFKC-lowercased SHA-256) between `fhv1_calibration_samples` and `IN_DOMAIN_VALID` test entries.
4. **Reuse Design Tokens (`frontend/src/index.css`)**:
   * `--color-studio-bg` (`#0b0f17`), `--color-studio-panel` (`#111827`), `--color-studio-card` (`#161f30`), `--color-studio-line` (`#273549`), `--color-studio-text` (`#f1f5f9`), `--color-studio-muted` (`#94a3b8`), `--color-studio-accent` (`#38bdf8`), `--color-studio-pass` (`#10b981`), `--color-studio-breach` (`#ef4444`), `--color-studio-warn` (`#f59e0b`).

---

## 4. Architectural Layout, Data Contracts & Algorithmic Specification

### 4.1 System Topology

```text
+---------------------------------------------------------------------------------+
| Frontend SPA (:5173 — React 19 + Vite 8 + Tailwind v4 + ECharts/uPlot, pnpm)    |
|  [Tab 1: Playground Realtime]  [Tab 2: FHV1 Variance Studio]  [Tab 3: Benchmark]|
|   - 3HM / fhv1 Filter Switch    - 1024D Exact Precision Table  - 4-Quad Metrics |
|   - Chat SSE + Direct Lab       - [min,mean,max] & Var Charts  - Trace Drilldown|
|   - Live Audit Log Panel        - Movement Tier Classifier     - Vector Overlay |
+----------------------------------------+----------------------------------------+
                                         | HTTP JSON / SSE / XLSX download
                                         v
+---------------------------------------------------------------------------------+
| Backend Gateway: sf-proxy (:8088 — Rust 1.94.1 + Axum + Tokio)                  |
|  Existing 3HM Routes: /v1/chat/completions, /api/v1/chat, /api/v1/upstream/env  |
|  New FHV1 Routes:     /api/v1/fhv1/{profiles,calibrate,evaluate,benchmarks,     |
|                                     traces,export}                              |
|  Pipeline: InputNormalizer -> Symmetric Chunker -> Embedder -> fhv1 Gate        |
+------------------+----------------------------------+---------------------------+
                   | POST /embed (normalize: true|false)  | Arrow =58.4.1 columnar
                   v                                      v
+---------------------------------------+  +--------------------------------------+
| tools/bge_m3_mps_server.py (:8080)    |  | LanceDB (data/sf-lancedb)            |
| BAAI/bge-m3 Metal MPS torch.float32   |  |  - domain_hypercubes (3HM unchanged) |
|                                       |  |  - fhv1_calibration_samples          |
+---------------------------------------+  |  - fhv1_profiles                     |
                                           |  - fhv1_benchmark_runs               |
Offline Tools (uv PEP 723 + sf-bench CLI): |  - fhv1_audit_traces                 |
 - tools/augment_fhv1_corpus.py (optional) +------------------+-------------------+
 - tools/generate_fhv1_benchmark.py                           | rust_xlsxwriter
 - sf-bench: fhv1_calibrate / fhv1_benchmark                  v
                                           Lossless .xlsx (2 sheets) / .csv / .parquet
```

### 4.2 Core Mathematical & Algorithmic Specification (`crates/sf-kernels/src/fhv1.rs`)

#### 4.2.1 Profile Computation (Lossless `f64`, Numerically Stable)
Given $N \ge 1$ calibration vectors $\mathbf{V} \in \mathbb{R}^{N \times 1024}$ (all finite `f64`):
For each dimension $d \in \{0, \dots, 1023\}$:
* `min_d` $= \min_{i=0..N-1} V_{i,d}$
* `max_d` $= \max_{i=0..N-1} V_{i,d}$
* `mean_d` $= \frac{1}{N} \sum_{i=0}^{N-1} V_{i,d}$ (computed via Welford online algorithm in `f64` for numerical stability)
* `span_d` $= \text{max}_d - \text{min}_d$
* `variance_d` $= \frac{1}{N} \sum_{i=0}^{N-1} (V_{i,d} - \text{mean}_d)^2$ (population variance in `f64`, accumulated via Welford `M2 / N`)
* `std_dev_d` $= \sqrt{\text{variance}_d}$

#### 4.2.2 Quantile Movement Categorization (`B1`)
Given metric $m_d \in \{\text{variance}_d, \text{std\_dev}_d, \text{span}_d\}$ (default `variance_d`) across all 1,024 dimensions:
1. If `max_d == min_d` (`span_d == 0.0`) $\implies$ `ZERO_SPAN` (`code = 0`).
2. Otherwise compute empirical quantiles $P_{25}, P_{75}, P_{90}$ over non-zero dimensions (customizable cutoffs in GUI):
   * $m_d \le P_{25} \implies$ `LOW_ANCHOR` (`code = 1`)
   * $P_{25} < m_d \le P_{75} \implies$ `MODERATE` (`code = 2`)
   * $P_{75} < m_d \le P_{90} \implies$ `HIGH_VOLATILITY` (`code = 3`)
   * $m_d > P_{90} \implies$ `EXTREME_MOVEMENT` (`code = 4`)

#### 4.2.3 Strict `fhv1` Decision Gate & Forensic Per-Dimension Comparison (`C1`, `1C`)
For one vector $x \in \mathbb{R}^{1024}$, profile $P$, and flag `use_rogue_mask: bool`:
```rust
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum DimBoundStatus {
    InBounds,
    Underflow, // x_d < min_d
    Overflow,  // x_d > max_d
    PrunedRogue,
}

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct Fhv1DimComparison {
    pub dim: u16,
    pub status: DimBoundStatus,
    pub observed: f64,
    pub observed_bits_hex: [u8; 18], // or String "0x..." in DTO
    pub min: f64,
    pub max: f64,
    pub mean: f64,
    /// 0.0 if InBounds/PrunedRogue; (x_d - min_d) < 0 if Underflow; (x_d - max_d) > 0 if Overflow
    pub violation_delta: f64,
    /// Exact signed deviation from calibrated average: x_d - mean_d
    pub delta_vs_mean: f64,
    /// Relative position in [min, max]: (x_d - min_d) / (max_d - min_d); None if span == 0
    pub norm_pos: Option<f64>,
}
```
* **Coordinate Check (Fail-Closed on Non-Finite)**:
  * If `!x_d.is_finite()` $\implies$ immediate fail-closed error (`NonFiniteInput`).
  * If `use_rogue_mask && UNIVERSAL_NOISE_INDICES.contains(&(d as u16))` $\implies$ `PrunedRogue` (excluded from decision count).
  * Else if `x_d < min_d` $\implies$ `Underflow`, `violation_delta = x_d - min_d` (negative).
  * Else if `x_d > max_d` $\implies$ `Overflow`, `violation_delta = x_d - max_d` (positive).
  * Else $\implies$ `InBounds`, `violation_delta = 0.0`.
* **Chunk Verdict (`polarity == 0`, ALLOWLIST)**:
  * `chunk_passed = (underflow_count == 0) && (overflow_count == 0)` (strictly 100% of evaluated dimensions inside `[min_d, max_d]`).
* **Input Verdict (Multi-Chunk `ALL_CHUNKS_PASS`, Non-Short-Circuiting)**:
  * Evaluate **every** chunk in the batch (`chunk[0]` is always `normalized_full_text`).
  * `full_text_passed = chunks[0].chunk_passed`
  * `all_chunks_passed = chunks.iter().all(|c| c.chunk_passed)`
  * `overall_passed` follows `eval_granularity`:
    * `full_only` $\implies$ `full_text_passed`
    * `clauses` | `full_mirror` $\implies$ `all_chunks_passed`

### 4.3 Raw Precision Embedder Seam (`4A`, `4.1-B`)
* In `crates/sf-proxy/src/normalize.rs`, add `validate_raw_f64_slice(src: &[f64]) -> Result<[f64; DIM], NormalizeError>`: verifies `src.len() == 1024` and every coordinate `is_finite()`, **without** dividing by L2 norm and **without** narrowing to `f32`.
* In `crates/sf-proxy/src/embedder.rs` (`BatchEmbedderClient`), add default-overridable method:
  ```rust
  async fn embed_batch_raw_f64(
      &self,
      texts: &[&str],
      normalize: bool,
  ) -> Result<Vec<[f64; 1024]>, String>;
  ```
* In `crates/sf-proxy/src/tei.rs` (`TeiHttpEmbedder`), implement `embed_batch_raw_f64` posting `{"inputs": texts, "normalize": normalize}` to `POST /embed`, reading JSON numbers directly as `f64` (`number.as_f64()`), and validating via `validate_raw_f64_slice` (no `as f32` cast, no forced re-normalization).
* Existing `embed_batch_f32` remains 100% unchanged for `3HM`.

### 4.4 Exhaustive Calibration Pipeline (`2C`)
Binary `crates/sf-bench/src/bin/fhv1_calibrate.rs` and shared Rust module `crates/sf-proxy/src/fhv1_pipeline.rs`:
1. **Input Sources**: plain text file(s), directory of `.txt`/`.md`/`.jsonl`, canonical domain seed expansion, or GUI text/file upload.
2. **Deterministic Multi-Granularity Expansion (Always Executed)**:
   Each emitted chunk is tagged with `strategy_tag` and deduplicated by `(strategy_tag, text_sha256)` while retaining provenance:
   * `full_doc`: entire document/entry (after `InputNormalizer`)
   * `paragraph`: blank-line separated blocks
   * `sentence`: sentence-level splits (`.`, `!`, `?`, `\n`)
   * `clause_opt2c`: `InputNormalizer::normalize(text).segment_all_clauses()` (Option 2C)
   * `window_w5_s3`, `window_w10_s5`, `window_w20_s10`, `window_w40_s20`: multi-scale overlapping word windows
   * `atomic_phrase`: comma/semicolon/colon delimited sub-phrases and domain key-term extractions (`>= 2` tokens)
   * `surface_norm_variant`: lowercased / punctuation-stripped deterministic surface variants
3. **Optional Synthetic LLM Augmentation (`--augment-llm`, `tools/augment_fhv1_corpus.py`, `uv` PEP 723)**:
   * Uses configured `.env` provider (`env_config.rs` schema) offline to generate domain paraphrases, Q&A reformulations, formal/technical/colloquial registers, and synonym substitutions.
   * Persists augmented outputs to `data/fhv1_augmented/<policy_id>_<sha256>.jsonl` with manifest hash so repeated calibration runs are 100% deterministic without re-calling the LLM.
4. **Vectorization & Persistence**:
   * Batches all chunks through `embed_batch_raw_f64(batch, profile_normalize)` against `BAAI/bge-m3`.
   * Writes every row to `fhv1_calibration_samples` in LanceDB, computes `Fhv1EnvelopeProfile`, writes immutable versioned row to `fhv1_profiles`, and optionally triggers lossless `.xlsx` export.

### 4.5 LanceDB Arrow `=58.4.1` Schemas (`crates/sf-storage/src/fhv1_schema.rs`)
All 4 new tables live inside `data/sf-lancedb` alongside untouched `domain_hypercubes`.

1. **`fhv1_calibration_samples`**:
   * `sample_id: Utf8`, `profile_id: Utf8`, `policy_id: Utf8`, `version: UInt64`, `source_ref: Utf8`, `strategy_tag: Utf8`, `raw_text: Utf8`, `text_sha256: FixedSizeBinary(32)`, `normalize: Boolean`, `model_id: Utf8`, `source_dtype: Utf8`, `vector: FixedSizeList(Float64, 1024)`, `created_at_ms: Int64`.
2. **`fhv1_profiles`**:
   * `profile_id: Utf8` (unique immutable ID, e.g. `python-v1-<short_sha>`), `policy_id: Utf8`, `version: UInt64`, `polarity: UInt8` (`0` = ALLOWLIST), `normalize: Boolean`, `use_rogue_mask_default: Boolean`, `sample_count: UInt64`, `corpus_sha256: FixedSizeBinary(32)`, `model_id: Utf8`, `source_dtype: Utf8`, `augmented_llm: Boolean`, `min_vector: FixedSizeList(Float64, 1024)`, `max_vector: FixedSizeList(Float64, 1024)`, `mean_vector: FixedSizeList(Float64, 1024)`, `span_vector: FixedSizeList(Float64, 1024)`, `variance_vector: FixedSizeList(Float64, 1024)`, `std_dev_vector: FixedSizeList(Float64, 1024)`, `movement_tier_codes: FixedSizeList(UInt8, 1024)`, `created_at_ms: Int64`.
3. **`fhv1_benchmark_runs`**:
   * `run_id: Utf8`, `profile_id: Utf8`, `policy_id: Utf8`, `dataset_name: Utf8`, `dataset_sha256: FixedSizeBinary(32)`, `eval_granularity: Utf8`, `use_rogue_mask: Boolean`, `total_inputs: UInt64`, `total_chunks: UInt64`, `summary_metrics_json: Utf8` (full confusion matrix, per-category FAR/FRR/Recall/F1, `full_only` vs `all_chunks` comparison, per-dimension failure attribution counts), `created_at_ms: Int64`.
4. **`fhv1_audit_traces`**:
   * `trace_id: Utf8`, `run_id: Utf8` (empty string for realtime), `source_kind: Utf8` (`"BENCHMARK"` \| `"REALTIME_CHAT"` \| `"REALTIME_LAB"`), `profile_id: Utf8`, `policy_id: Utf8`, `category: Utf8` (`IN_DOMAIN_VALID` \| `OUT_OF_DOMAIN_BENIGN` \| `HYBRID_BOUNDARY` \| `ADVERSARIAL_FUZZING` \| `REALTIME`), `expected_pass: Boolean` (nullable), `input_id: Utf8`, `raw_text: Utf8`, `eval_granularity: Utf8`, `use_rogue_mask: Boolean`, `chunk_index: UInt32`, `chunk_strategy: Utf8`, `chunk_text: Utf8`, `input_vector: FixedSizeList(Float64, 1024)`, `chunk_passed: Boolean`, `overall_passed: Boolean`, `full_text_passed: Boolean`, `all_chunks_passed: Boolean`, `evaluated_dims: UInt16`, `failed_dims_count: UInt16`, `underflow_count: UInt16`, `overflow_count: UInt16`, `max_violation_delta: Float64`, `mean_abs_delta_vs_mean: Float64`, `eval_latency_ns: UInt64`, `embedding_ms: Float64`, `created_at_ms: Int64`.

### 4.6 Lossless Excel & Data Exporter (`crates/sf-storage/src/fhv1_export.rs`, `D1`, `F1`)
* Uses pure-Rust `rust_xlsxwriter` writing native IEEE 754 `f64` numbers (`worksheet.write_number(...)`, zero string truncation, zero rounding format).
* **Workbook Layout**:
  1. Sheet `Summary_Envelope`: 1,024 rows (`dim`, `is_rogue_dim`, `min`, `max`, `mean`, `span`, `variance`, `std_dev`, `movement_tier`).
  2. Sheet `Raw_Samples_Matrix`: columns `sample_id`, `policy_id`, `strategy_tag`, `source_ref`, `raw_text`, `dim_0` .. `dim_1023`.
* **Scale Protection**: configurable `max_rows_per_xlsx` (default `10,000`). If sample count exceeds `max_rows_per_xlsx`, automatically partitions `Raw_Samples_Matrix` into part files (`part_001.xlsx`, `part_002.xlsx`, ...) or packages them into a single download, while also offering lossless `.csv` (full `f64::to_string()` precision) and native `.parquet` exports.

### 4.7 Strong 4-Quadrant Adversarial Benchmark Suite (`G1`)
Generator `tools/generate_fhv1_benchmark.py` (`uv` PEP 723) + Rust runner `crates/sf-bench/src/bin/fhv1_benchmark.rs`:
* **Minimum Floor**: `>= 400` real text prompts per target domain (seed-deterministic JSONL manifest with SHA-256), strictly verified for **0% overlap** with calibration samples, embedded via live `BAAI/bge-m3` FP32 MPS:
  1. **`IN_DOMAIN_VALID` (`>= 100`)**: unseen legitimate domain queries, indirect phrasing, edge-case valid domain questions, formal/informal registers, short (4–8 words) to long (100+ words).
  2. **`OUT_OF_DOMAIN_BENIGN` (`>= 100`)**: samples from disjoint canonical domains + `CLINC OOS` + clean everyday off-topic text in matching language(s).
  3. **`HYBRID_BOUNDARY` (`>= 100`)**:
     * 50/50 and 80/20 mixed payloads (off-topic or adversarial clause placed at beginning, middle, and end).
     * Context dilution & code/comment/docstring smuggling.
     * Near-OOD adjacent topics (e.g., for `python`: JavaScript/Rust/SQL snippets; for `receta`: nutrition/food chemistry/restaurant finance).
     * Polarity/intent flips sharing domain vocabulary.
  4. **`ADVERSARIAL_FUZZING` (`>= 100`)**:
     * Random noise, gibberish, keyboard mash, high/low Shannon entropy strings, repeated characters.
     * Extreme lengths: 1 char, 1 word, empty-like punctuation, token flooding (2,000–4,000+ tokens).
     * Obfuscation: Cyrillic/Greek/fullwidth homoglyphs, zero-width control chars, Base64, hex, ROT13, leetspeak, mixed scripts.
     * OWASP LLM01 attacks: `deepset/prompt-injections`, direct/indirect prompt injection, jailbreak framings, roleplay overrides, delimiter escapes (`###`, `"""`, `<|system|>`), system-prompt extraction, allowed-keyword padding around forbidden payloads.
* **Efficacy Analytics Engine** (persisted in `fhv1_benchmark_runs.summary_metrics_json` and `reports/fhv1_<policy>_<run_id>.json`):
  * Overall and **per-category** Confusion Matrix (`TP`, `TN`, `FP`, `FN`), Accuracy, Precision, Recall, F1, **FAR/FPR** (security leak rate on `OOD`, `HYBRID`, `ADVERSARIAL`), **FRR/FNR** (false rejection rate on `IN_DOMAIN_VALID`).
  * Automatic side-by-side efficacy matrix comparing `full_only` vs `clauses` vs `full_mirror` and `use_rogue_mask=false (1024D)` vs `use_rogue_mask=true (1015D)`.
  * **Per-Dimension Violation Attribution**: for each dim `0..1023`, count of how many `IN_DOMAIN_VALID` inputs failed on dim $d$ (false-rejection culprits) vs how many `OOD`/`HYBRID`/`ADVERSARIAL` inputs were caught by dim $d$ (high-signal discriminators), cross-referenced against `movement_tier`.

### 4.8 Gateway REST API Contracts (`crates/sf-proxy/src/fhv1_api.rs`, `:8088`)

| Method & Path | Purpose | Precision & Payload Contract |
| :--- | :--- | :--- |
| `GET /api/v1/fhv1/profiles` | List calibrated `Fhv1EnvelopeProfile` versions | Summary metadata (`profile_id`, `policy_id`, `version`, `sample_count`, `normalize`, `created_at_ms`). |
| `GET /api/v1/fhv1/profiles/:profile_id` | Full 1,024D envelope & variance profile | Exact full-precision `f64` arrays (`min`, `max`, `mean`, `span`, `variance`, `std_dev`, `movement_tier_codes`, quantile cutoffs). Supports query `?metric=variance\|std_dev\|span`. |
| `POST /api/v1/fhv1/calibrate` | Trigger calibration over submitted corpus texts/docs | Accepts `policy_id`, `texts[]`, `normalize`, `use_rogue_mask_default`. Runs deterministic expansion + `bge-m3` raw embed + LanceDB persistence. Returns created `profile_id` + summary. |
| `GET /api/v1/fhv1/profiles/:profile_id/export` | Download lossless calibration dataset | Query `?format=xlsx\|csv\|parquet`. Streams lossless 2-sheet `.xlsx` (or `.zip` if split) with exact IEEE 754 `f64` cells. |
| `POST /api/v1/fhv1/evaluate` | **Realtime Sentence Lab (A2)** — direct evaluation without upstream LLM | Body: `{ profile_id, text, eval_granularity, use_rogue_mask }`. Persists full trace to `fhv1_audit_traces` (`source_kind = "REALTIME_LAB"`). Returns `trace_id`, `overall_passed`, `full_text_passed`, `all_chunks_passed`, per-chunk summary, latency, and full 1,024D exact comparison array for selected chunk. |
| `POST /api/v1/chat` (extended, backward-compatible) | **Chat Protected Mode (A2)** | Optional fields: `filter_mode?: "3hm_default" \| "fhv1" \| "3hm_plus_fhv1"`, `fhv1_profile_id?`, `fhv1_granularity?`, `fhv1_use_rogue_mask?`. Omitting `filter_mode` keeps exact `v0.2.1` `3HM` behavior. When `fhv1` blocks -> HTTP `403` with structured `fhv1` breach DTO + persisted trace (`REALTIME_CHAT`). |
| `GET /api/v1/fhv1/benchmarks` | List persisted benchmark runs | Run metadata + headline efficacy rates. |
| `POST /api/v1/fhv1/benchmarks/run` | Execute benchmark run against a profile & dataset | Persists run in `fhv1_benchmark_runs` + all traces in `fhv1_audit_traces`. |
| `GET /api/v1/fhv1/benchmarks/:run_id` | Run efficacy dashboard payload | Confusion matrix, per-category FAR/FRR/Recall/F1, `failed_dims_count` histogram, and 1,024D attribution stats. |
| `GET /api/v1/fhv1/traces` | Paginated audit trace list (`E1`) | Query: `?run_id=...&profile_id=...&source_kind=...&category=...&passed=true\|false&page=1&page_size=50`. Returns compact summary rows (no 1024-float vectors in list payload). |
| `GET /api/v1/fhv1/traces/:trace_id` | **1,024D Forensic Drill-Down (`E1`)** | Joins `fhv1_audit_traces` (all chunks of that evaluation) with immutable `fhv1_profiles`, returning exact unrounded `f64` vectors, `[min, max, mean]`, `status`, `violation_delta`, `delta_vs_mean`, and `norm_pos` for all 1,024 dims. |

### 4.9 Frontend SPA Architectural Layout (`frontend/`, `:5173`)

```text
Root (<div className="h-[100dvh] flex flex-col overflow-hidden bg-studio-bg text-studio-text">)
├── <header> SF-PROXY PLAYGROUND + View Tabs:
│     [Playground Realtime (default)] | [FHV1 Variance Studio] | [FHV1 Benchmark & Audit]
└── <main className="flex-1 flex overflow-hidden">
      ├── Tab 1: Playground Realtime (preserves ALL existing Playground.tsx DOM contracts)
      │     ├── Chat Thread / Direct FHV1 Sentence Lab toggle (A2)
      │     ├── Live Audit Log collapsible bottom/side drawer (realtime traces + click to inspect 1024D)
      │     └── Live Tuning Drawer (w-60 fixed, adds Filter Engine: 3HM | fhv1 | 3HM+fhv1 + profile/granularity)
      ├── Tab 2: FHV1 Variance & Envelope Studio
      │     ├── Top Bar: Policy/Profile selector, Metric (variance|std_dev|span), Quantile controls, Export (.xlsx/.csv/.parquet)
      │     ├── Visual Charts (ECharts/uPlot <canvas>, zoom/pan, exact full-precision tooltips):
      │     │     1) 1024D Envelope Band Chart ([min, max] ribbon + mean line)
      │     │     2) Dimension Movement Ranking & Tier Distribution (ZERO_SPAN / LOW_ANCHOR / MODERATE / HIGH / EXTREME)
      │     └── Full-Precision 1024-Row Sortable/Filterable Table (zero .toFixed(), 1-click exact copy)
      └── Tab 3: FHV1 Benchmark & Audit Explorer
            ├── Top Bar: Run selector, Category filter, Verdict filter, Granularity comparison summary
            ├── Efficacy Dashboard: 4-Quadrant Confusion Matrix, FAR/FRR bars, Failed-Dims Histogram, Dim Attribution Chart
            └── Paginated Trace Table -> Drill-Down Drawer/Split Pane:
                  - Chunk selector for the input
                  - Input Vector x overlaid on [min, max, mean] envelope chart (UNDERFLOW/OVERFLOW highlighted in crimson)
                  - Exact full-precision 1024D comparison table
```

### 4.10 Guidance for Vertical Tracer Bullet Decomposition (For the Architect Agent)
Decompose implementation into atomic, independently testable vertical slices under `TASKS.md` (each ending in green `cargo test`, `clippy`, `fmt`, and `pnpm` checks):
1. **Slice 1 — Core `fhv1` Kernel & Raw Precision Embedder Seam**: `sf-kernels/src/fhv1.rs` (Welford stats, quantile tiers, strict AABB gate, 1-ULP/16-ULP purity tests) + `TeiHttpEmbedder::embed_batch_raw_f64` (`normalize: bool` configurable).
2. **Slice 2 — LanceDB `fhv1_*` Schemas, Store & Lossless `.xlsx` Exporter**: `sf-storage` 4 tables (`Arrow =58.4.1`, `Float64`), `rust_xlsxwriter` 2-sheet exporter + auto-split + 0-ULP round-trip tests (LanceDB & `.xlsx`).
3. **Slice 3 — Exhaustive Calibration Pipeline & CLI (`fhv1_calibrate` + optional `--augment-llm`)**: deterministic multi-granularity chunker/expander in Rust + `tools/augment_fhv1_corpus.py` (`uv` PEP 723) + calibration of expanded `python` and `receta` corpora against live `BAAI/bge-m3`.
4. **Slice 4 — Strong 4-Quadrant Adversarial Benchmark Generator, Runner & Efficacy Analytics**: `tools/generate_fhv1_benchmark.py` (`>= 400` real prompts/domain, 0% overlap gate) + `fhv1_benchmark` CLI persisting runs & full traces to LanceDB + JSON report.
5. **Slice 5 — `sf-proxy` REST APIs & Chat Integration (`A2`, `E1`)**: `/api/v1/fhv1/*` endpoints (profiles, calibrate, evaluate, export, benchmarks, paginated traces, 1024D drill-down) + backward-compatible `filter_mode` on `/api/v1/chat` + E2E tests.
6. **Slice 6 — Frontend SPA View 1 (`Playground Realtime` + `fhv1` Switch + Live Audit Log)**: non-breaking extension of `Playground.tsx` + Vitest & Playwright regression checks.
7. **Slice 7 — Frontend SPA View 2 (`FHV1 Variance & Envelope Studio`)**: `<canvas>` charts (`echarts`/`uplot`), full-precision 1,024-row table, movement tier controls, `.xlsx`/`.csv` download.
8. **Slice 8 — Frontend SPA View 3 (`FHV1 Benchmark & Audit Explorer`) + Full E2E & Docs**: 4-quadrant efficacy dashboard, paginated audit explorer, 1,024D vector-overlay drill-down, `frontend/e2e/fhv1.spec.ts`, and updates to `CONTEXT.md`, `architecture_spec.md`, `CHANGELOG.md`.

---

## 5. Development Protocol, Quality Gate & Definition of Done

### 5.1 Protocol Invariants
* **Workflow**: `transparent-dev-protocol` + `fabrica-de-software` (`TASKS.md` validated with `agent.sh validate --task-file TASKS.md`).
* **Git Branching**: Dedicated `<type>/<short-name>` branch per slice from `main`. Local commit + audit report + explicit human `"OK"` before `push` / `merge --no-ff`.
* **Exclusive Authorship**: Sole commit author `hbauzan` (`Héctor Andrés Bauzán Saavedra <hbauzan@gmail.com>`). Zero `Co-authored-by:` trailers.
* **Lexical Hygiene**: Strictly forbid naming external assistants, bots, or editors in source code, comments, tests, roadmaps, changelogs, or commit messages.
* **Evidence Discipline**: Never report a gate as passing without executing it after the last file edit.

### 5.2 Canonical Verification Commands
```bash
# 1. Rust formatting, strict Clippy, and full workspace tests
cargo fmt --all -- --check
cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace

# 2. Frontend linter, typecheck/build, and unit tests
pnpm --dir frontend lint
pnpm --dir frontend build
pnpm --dir frontend test

# 3. Python uv script checks (offline tests / syntax)
uv run tools/test_bge_m3_mps_server.py

# 4. Playwright E2E (with live bge_m3_mps_server :8080 and sf-proxy :8088)
pnpm --dir frontend test:e2e
```

### 5.3 Definition of Done (Falsifiable Checklist)
- [ ] `fhv1` evaluates strictly `min_d <= x_d <= max_d` across all 1,024 dims by default (and 1,015 when `use_rogue_mask = true`), with `mean_d` audited without altering PASS/FAIL.
- [ ] Zero rounding verified end-to-end: 0-ULP round-trip test passes across `sf-kernels`, LanceDB `Float64`, HTTP JSON API, `rust_xlsxwriter` `.xlsx` export, and `fhv1` GUI tables/tooltips (zero `.toFixed()` in `fhv1` numeric displays).
- [ ] `normalize: true` and `normalize: false` both execute cleanly against `tools/bge_m3_mps_server.py` via `embed_batch_raw_f64` without breaking `3HM`.
- [ ] Deterministic multi-granularity calibration + optional `--augment-llm` persist raw samples to `fhv1_calibration_samples`, versioned profiles to `fhv1_profiles`, and export lossless 2-sheet `.xlsx` (auto-split `> 10,000` rows) + `.csv`/`.parquet`.
- [ ] Strong 4-quadrant real-text benchmark (`>= 400` entries/domain, 0% calibration overlap, live `BAAI/bge-m3` FP32) runs end-to-end, persists full lossless traces to `fhv1_audit_traces`, and reports confusion matrix, per-category FAR/FRR/Recall/F1, `full_only` vs `clauses` vs `full_mirror`, and 1,024D attribution.
- [ ] Frontend SPA (`:5173`) delivers all 3 views: Playground Realtime (`3HM` + `fhv1` chat & direct lab + live Audit Log), FHV1 Variance Studio (interactive 1024D charts + quantile tiers + full-precision table + `.xlsx` export), and FHV1 Benchmark & Audit Explorer (efficacy dashboard + paginated list + 1024D vector overlay drill-down).
- [ ] Zero regressions: all 111+ Rust tests, 44+ Vitest tests, 9+ Playwright E2E tests, `cargo fmt`, `cargo clippy -D warnings`, `pnpm lint`, and `pnpm build` exit 0.