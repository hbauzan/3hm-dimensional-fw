# EXECUTION ROADMAP: `fhv1` HARDENING, LEAK-FREE SCIENTIFIC BENCHMARK, LLM CORPUS AUGMENTATION (`1B`) & EMPIRICAL FALSIFICATION (`TASK-011`)

> **Single Source of Truth**: Self-contained specification for `TASK-011`.
> **Baseline**: `main @ f239f19` (post-`TASK-009` & `TASK-010`)
> **Branch**: `feat/fhv1-task-011-hardening-falsification`
> **Task Governance**: `TASK-011` in [`TASKS.md`](../TASKS.md) (`fabrica-de-software` + `transparent-dev-protocol`)
> **Delivery Fence**: 1 fresh coding agent per Vertical Tracer Bullet Slice (`Slices 1–7`), 1 atomic local commit per Slice. **HALT after Slice 7** at the human Approval Gate before any `git push` or `git merge --no-ff`.

---

## 1. Ground Truth & Non-Negotiable Invariants

### 1.1 Authorship, Lexical & Staging Rules
* **Sole Git Authorship**: `Héctor Andrés Bauzán Saavedra <hbauzan@gmail.com>` (`hbauzan`). Strictly **ZERO** `Co-authored-by:` trailers.
* **Absolute Lexical Prohibition**: NEVER mention names of external AI assistants, bots, coding-agent brands, editors, or IDEs in source code, comments, docstrings, tests, roadmaps, ADRs, changelogs, or commit messages.
* **Secrets & Untracked Artifacts**: NEVER echo, log, read raw values of, or stage `.env`, API keys, `repomix-output.xml`, `data/`, `audit_*`, or binary `.xlsx` outputs. Stage explicit file paths only (never `git add -A`).

### 1.2 Canonical Toolchains & Version Freeze
* **Rust** (`rust-toolchain.toml`: `1.94.1`): `cargo` exclusively (`cargo fmt --all -- --check`, `cargo clippy --workspace --all-targets -- -D warnings`, `cargo test --workspace`).
* **Frontend** (`frontend/`, `pnpm` `11.8.0`): `pnpm --dir frontend lint`, `pnpm --dir frontend build`, `pnpm --dir frontend test`, `pnpm --dir frontend test:e2e`.
* **Python** (`tools/`): `uv run --script ...` (PEP 723 `# /// script` headers). Zero `pip`, zero `npm`.
* **Package Version Freeze**: Keep `0.2.1` in `Cargo.toml`, `manifest.json`, and `frontend/package.json`. Log `TASK-011` changes strictly under `## [Unreleased]` in `CHANGELOG.md`.

### 1.3 Protected Technical Contracts & LanceDB Fence
* **NEVER** delete, overwrite, mutate, or re-seed `data/sf-lancedb/domain_hypercubes.lance` (`66` calibrated `BAAI/bge-m3` locks). Pre-Slice-1 SHA-256 baseline verified at `66` rows across 19 shard/manifest/txn files; re-verify byte-identical after Slice 7.
* **Interactive Shell Ban**: NEVER invoke `./setup.sh`. Start `tools/bge_m3_mps_server.py` (`:8080`) and `sf-proxy` (`:8088`) strictly via non-interactive background processes with `/health` polling and `trap cleanup EXIT`.
* **`crates/sf-kernels`**: pure Rust, **0 runtime dependencies**, no `serde`, NEON / cfg-gated AVX2/AVX512 preserved.
* **`crates/sf-storage`**: exact pins `lancedb = "0.40.0"`, `arrow-* = "=58.4.1"`, `parquet = "=58.4.1"`.
* **`crates/sf-proxy`**: Axum `0.8` dynamic routes use `{id}` syntax (never `:id`).
* **`3HM` (`filter_mode: "3hm_default"`)**: zero regressions; `buildChatRequest` omits `filter_mode` on `"3hm_default"`.
* **`RFC-003` Extended Precision**: lossless IEEE 754 `Float64` across LanceDB `fhv1_*`, Welford `f64` moments, JSON APIs, `.xlsx`/`.csv`/`.parquet` exports, and `fhv1` GUI (`formatLosslessF64 = String(value)` — **ZERO `.toFixed(`** in `fhv1` code; preserve `.toFixed(4)` strictly in `format.ts` / `BreachCard.tsx` for `3HM`).
* **Protected `Playground.tsx` Selectors**: preserve all 11 accessible selectors (`Gateway base`, `Domain id` [11 options], `Prompt`, `Send|Sending`, `Messages`, `Live tuning` [`w-60`], `#root > div` [`h-[100dvh] overflow-hidden`], `Apply overrides`, 4 sliders, `.env` controls, 4 preset chips).
* **Out of Scope**: Egress Semantic Amplification (`v1.1+`) and width-weighted *Holistic Resonance Gate* (`roadmap/future-holistic-resonance-gate.md`).

### 1.4 Locked Architectural Decisions
* **Decision `1B` (Calibration Corpus Expansion)**: Combine a versioned, curated offline base corpus (`150–300` real diverse documents per domain for `python` EN and `receta` ES) WITH live `tools/augment_fhv1_corpus.py --augment-llm --provider <AUTO_FROM_ENV>` expansion to `500–1,000+` real cached SHA-256 JSONL texts per domain under `data/fhv1_augmented/` prior to calibration (`augmented_llm = true` recorded in `fhv1_profiles`). Fail closed if no live provider key is configured or provider calls fail.
* **Decision `2B` (`violation_delta` Sign on `Underflow`)**: Keep positive magnitude `violation_delta = min_d - x_d` on `Underflow` in `crates/sf-kernels/src/fhv1.rs` (`evaluate_row`), with direction explicitly encoded by `status: Underflow | Overflow`. Lock this invariant in `architecture_spec.md` (ADR-006) and render magnitude + direction unambiguously in GUI tooltips/rows.

---

## 2. Pre-Slice-1 `domain_hypercubes.lance` Integrity Baseline

* **Row count**: `66` (`domain_hypercubes`)
* **Shard & Metadata SHA-256 Checksums**:
  * `_transactions/0-274897fa-cd1e-45c5-9829-e7188513de19.txn`: `632466dd30fcd86df791201d9e3e87673f90adf7d85fadbd74954cf100d4b5c5`
  * `_transactions/1-a65ed658-6565-42b2-9982-dcf389fc0f36.txn`: `de426e830a02ec34f1378b576a5b77b2d9c74e24abfdc966e7e056038e777482`
  * `_transactions/2-61cb3773-5ecf-4cbb-a5fd-92b5f0914556.txn`: `16ee2648e242ca680c8b2e93b62f82b95dba1969e66d1c2a3c306b5a83d77429`
  * `_transactions/3-ea5a03c9-80ce-4fca-afc9-a67e6f1df8ea.txn`: `2050c7f3368e924f964456d83fa0421aaf1b18681e957c99e2c28ab822c0c13f`
  * `_transactions/4-dba9f33a-65af-406b-af38-ae34e6f85b79.txn`: `ab52f6e545857730d9c61398b0db60cb565c70a0c335bfa2c3b9c2dd6ae80ae5`
  * `_transactions/5-69d7a800-beb0-4caf-b0e2-4f438b22a94d.txn`: `46270bb923de8356fbd5acbe4ab24b2b28c9bf3a86d1666de1b4d5d5701a1578`
  * `_versions/18446744073709551609.manifest`: `74dbca8c828dedc9d0fc0e2bceee6f07cffb2047f01a945db043613967bf0a1a`
  * `_versions/18446744073709551610.manifest`: `4ae6d01694eda78bb5eaf8747fb3e9eb12a3f8d41ed17ca99a1dd52b4497aa0e`
  * `_versions/18446744073709551611.manifest`: `eb36883c6fd26430abfc6d75b618e7019a7592f41c1ccebc13bc15f3509de307`
  * `_versions/18446744073709551612.manifest`: `6af274a0465c5acfe060e3844423cd4f5292391c36392371a97f7fdadaad8688`
  * `_versions/18446744073709551613.manifest`: `ed25aad11209393b6edbc191bdf5e4b2a69b67dcd865c3919a8e1ad7ab91d3aa`
  * `_versions/18446744073709551614.manifest`: `c750de7b9a777b65425324c15e9e4af8f56267c7da188015ead64cf0feb50e0b`
  * `_versions/latest_version_hint.json`: `1e1901b2658bbbb3512c4e8867974632a030c38adb83ab4b5e3b0b39e6705ac2`
  * `data/011010010000011001101011d0ffc74ccb937e8218f9f4b05d.lance`: `7bd5186eaac43baa2c195476eb74c2bcf7326b7bca4ebaf66246ecb408c6bafb`
  * `data/1010110100111010001011106bf2bc404c87d1443b9a2168cf.lance`: `eb28f3a7d0d3812ff0dd2bb1e47ae9310d746a544b2d3d4f07d5f97b216626e8`
  * `data/1101001001010010000011110c1e954290b975e18a2915f249.lance`: `248121eca39f44369c966fd2e2a82dc670b09918c4b865b44266c30899b022a3`
  * `data/1101100110111000110110005b392b4e22ad3262871e5ff5c6.lance`: `0328413d9c98f00304b911a99e8d570d0aa06dd602ad00a50c01a17615269320`
  * `data/111000111010000011010000dbf9f74dd7994d37a969480e05.lance`: `91c751ebda14a40048806df7ccc6165a861f1acea20947a4b65facc85581e1e6`
  * `data/1110100011011001101100004ca69741899dc56c761138e5b9.lance`: `6bc02e9bc838fd16ef5305377c1b4f7ee68c662afa41eedb1386dfdb3115e6d9`

---

## 3. Vertical Tracer Bullet Slices (Sequential Execution)

### Slice 1 — Kernel Polarity Fail-Closed (`P2-13`), ADR-006 `violation_delta` Lock (`P2-9` / `2B`), LanceDB Predicate Pushdown & Pagination (`P2-12`)
* **Files**:
  * `crates/sf-kernels/src/fhv1.rs`
  * `crates/sf-kernels/tests/fhv1_precision_test.rs`
  * `architecture_spec.md`
  * `crates/sf-storage/src/fhv1_calibration.rs`
  * `crates/sf-storage/src/fhv1_store.rs`
  * `crates/sf-storage/tests/fhv1_roundtrip_test.rs`
  * `crates/sf-proxy/src/fhv1_api.rs`
  * `crates/sf-bench/tests/fhv1_e2e_test.rs`
* **Requirements**:
  1. **`P2-13`**: Add `Fhv1Error::UnsupportedPolarity(u8)` in `crates/sf-kernels/src/fhv1.rs`. Enforce `polarity == 0` (`ALLOWLIST`) inside `compute_fhv1_profile_stats` AND `evaluate_row` (`evaluate_fhv1_chunk` / `evaluate_fhv1_batch`); reject any non-zero polarity fail-closed. Add unit tests covering `polarity = 1` and `polarity = 255`.
  2. **`P2-9` (`2B`)**: Document and lock in `architecture_spec.md` (ADR-006) that `violation_delta` is strictly a non-negative magnitude (`min_d - x_d` on `Underflow`, `x_d - max_d` on `Overflow`, `0.0` on `InBounds`/`PrunedRogue`), with direction encoded by `status: Underflow | Overflow`.
  3. **`P2-12`**: In `crates/sf-storage/src/fhv1_store.rs`, remove silent `.limit(1_000_000)` truncation in `read_batches`. Extend `Fhv1TraceQuery` with `pub trace_id: Option<String>` (and wire `trace_id` query param in `fhv1_api.rs::TraceQuery`). In `query_audit_trace_summaries`, push down LanceDB `.only_if(...)` predicates (`run_id`, `profile_id`, `category`, `passed` -> `overall_passed`, `source_kind`, `trace_id`), use `table.count_rows(filter)` for exact `total`, and execute deterministic pagination via LanceDB `order_by` (`created_at_ms DESC`, `chunk_index ASC`, `trace_id ASC`) + `.offset(...)` + `.limit(...)` without full-table row loading. Add pagination/scale unit tests (`>1,000` rows, `trace_id` filter, out-of-range page preserving `total`) in `fhv1_roundtrip_test.rs`.
* **Verification Gate**: `cargo fmt --all -- --check && cargo clippy --workspace --all-targets -- -D warnings && cargo test --workspace`

---

### Slice 2 — `atomic_phrases()` Stopword Fix (`P0-2`), `FullOnly` Base64 Consistency (`P2-10`), Default `variance` Metric in Rust (`P2-8`), Lossless `3hm_plus_fhv1` Dual Embedder Seam (`P1-3`)
* **Files**:
  * `crates/sf-proxy/src/fhv1_pipeline.rs`
  * `crates/sf-proxy/src/embedder.rs`
  * `crates/sf-proxy/src/tei.rs`
  * `crates/sf-proxy/src/chat_api.rs`
  * `crates/sf-proxy/src/fhv1_api.rs`
  * `crates/sf-storage/src/fhv1_calibration.rs`
  * `crates/sf-bench/src/bin/fhv1_calibrate.rs`
  * `crates/sf-proxy/tests/fhv1_api_e2e_test.rs`
* **Requirements**:
  1. **`P0-2` (`atomic_phrases`)**: Replace single-token `chars().count() >= 2` emission and raw `windows(2)` stopword pollution in `crates/sf-proxy/src/fhv1_pipeline.rs`. Strip leading/trailing punctuation cleanly per token before stopword checks and deduplication. Using compact deterministic EN + ES stopword sets, extract strictly meaningful multi-token content phrases (`2..=4` tokens within clause/sentence punctuation boundaries) such that phrases never start or end on a stopword and never consist exclusively of stopwords/punctuation/numbers (`"revolver de"`, `"de más."`, `"of the"`, `"in a"`, `"digest without"` excluded). Add deterministic EN + ES unit tests.
  2. **`P2-10`**: Update `expand_for_granularity` (`FullOnly` and `Clauses`) in `crates/sf-proxy/src/fhv1_pipeline.rs` so Base64 `decoded_payloads` are emitted as `full_doc` chunks consistently with `FullMirror`. Add deterministic unit test proving `FullOnly` evaluates Base64 decoded payloads.
  3. **`P2-8` (Rust)**: Set default `MovementMetric::Variance` in `crates/sf-bench/src/bin/fhv1_calibrate.rs` (add `--metric <variance|std_dev|span>` defaulting to `variance`, and `--augmented-llm <bool>` defaulting to `false`), `crates/sf-proxy/src/fhv1_api.rs` (`parse_metric` default `"variance"` and `calibrate` handler `MovementMetric::Variance`), and `crates/sf-storage/src/fhv1_calibration.rs` (`stats_from_profile`).
  4. **`P1-3`**: Eliminate `promote_f32` in `crates/sf-proxy/src/fhv1_api.rs`. Add `DualEmbedBatch` and `BatchEmbedderClient::embed_batch_f32_and_raw_f64` (`embedder.rs`). In `TeiHttpEmbedder` (`tei.rs`), make **one** `POST /embed` (`normalize: true`) HTTP call and derive both `AlignedVec1024` (`f32`) and exact raw JSON `[f64; DIM]` from the same JSON response. In `chat_api.rs`, call `embed_batch_f32_and_raw_f64` when `filter_mode == "3hm_plus_fhv1"` (keeping `3hm_default` untouched). In `fhv1_api.rs::score_realtime`, reuse `raw_f64_vectors` ONLY when `profile.normalize && granularity != FullMirror` and chunk texts match; whenever `profile.normalize == false` or `granularity == FullMirror` or `raw_f64_vectors` is absent, execute `evaluate_fhv1_input` (`embed_batch_raw_f64(..., profile.normalize)`). Add a deterministic 1-ULP boundary test over HTTP `TcpListener` proving bit-identical (`to_bits()`) `fhv1` vector bits and decisions between standalone `fhv1` and `3hm_plus_fhv1` in a single HTTP `/embed` call.
* **Verification Gate**: `cargo fmt --all -- --check && cargo clippy --workspace --all-targets -- -D warnings && cargo test --workspace`

---

### Slice 3 — Shared Eval Engine with Per-Category Histograms/Percentiles/Subtype Stats (`P0-3`) & Full REST `/benchmarks/run` Parity (`P1-2`)
* **Files**:
  * `crates/sf-proxy/src/fhv1_eval.rs` (new shared evaluation engine)
  * `crates/sf-proxy/src/lib.rs`
  * `crates/sf-proxy/src/fhv1_pipeline.rs` (share `EMBED_BATCH_SIZE = 64` batched embedding helper)
  * `crates/sf-proxy/src/fhv1_api.rs`
  * `crates/sf-bench/src/fhv1_eval.rs` (re-export shared engine from `sf_proxy` — zero logic duplication)
  * `crates/sf-bench/src/bin/fhv1_benchmark.rs`
  * `crates/sf-proxy/tests/fhv1_api_e2e_test.rs`
* **Requirements**:
  1. **`P0-3` Metrics**: Keep global `failed_dims_count_histogram` AND add:
     - `failed_dims_count_histogram_by_category`: per-quadrant (`IN_DOMAIN_VALID`, `OUT_OF_DOMAIN_BENIGN`, `HYBRID_BOUNDARY`, `ADVERSARIAL_FUZZING`) histograms of `failed_dims_count`.
     - `failed_dims_stats_by_category`: per-quadrant `{ min, p25, median, p75, p90, max, zero_fail_count, chunk_count, prompt_count, prompt_zero_fail_count }`.
     - `per_subtype`: pass/fail counts + confusion metrics for every prompt `subtype` when `Fhv1Prompt.subtype` is present (`#[serde(default)]`).
  2. **`P1-2` REST Parity & Batched Embedding**: Unify CLI (`fhv1_benchmark`) and REST (`POST /api/v1/fhv1/benchmarks/run`) onto the single `sf_proxy::fhv1_eval` module so zero duplication exists. Replace 1-prompt-at-a-time embedding in REST `run_benchmark` with bounded batched `embed_batch_raw_f64` (`EMBED_BATCH_SIZE = 64`), prompt-scoped `trace_id = {run_id}-{input_id}`, and full `summary_metrics` (`confusion`, rates, `per_category`, `per_subtype`, `failed_dims_count_histogram`, `failed_dims_count_histogram_by_category`, `failed_dims_stats_by_category`, `attribution`, `granularity_comparison`). Cover schema, batching count, and trace IDs in `fhv1_api_e2e_test.rs`.
* **Verification Gate**: `cargo fmt --all -- --check && cargo clippy --workspace --all-targets -- -D warnings && cargo test --workspace`

---

### Slice 4 — Curated Offline Base Corpus (`150–300`/Domain, `1A`), Leak-Free 400-Prompt/Domain Benchmark (`P0-1`) & LLM Augmentation CLI (`1B` Tooling)
* **Files**:
  * `crates/sf-bench/fixtures/fhv1_corpus_python.jsonl` (new: `200–240` curated EN Python docs)
  * `crates/sf-bench/fixtures/fhv1_corpus_receta.jsonl` (new: `200–240` curated ES culinary docs)
  * `crates/sf-bench/src/fhv1_corpus.rs`
  * `tools/fhv1_benchmark_banks.json`
  * `tools/generate_fhv1_benchmark.py`
  * `tools/test_generate_fhv1_benchmark.py`
  * `tools/augment_fhv1_corpus.py`
  * `tools/test_augment_fhv1_corpus.py`
* **Requirements**:
  1. **`1A` Curated Base Corpus**: Replace the 17-doc seed in `crates/sf-bench/src/fhv1_corpus.rs` (while leaving `canonical_corpus.rs` untouched for 3HM!) with deterministic offline JSONL fixtures (`150–300` distinct docs per domain for `python` EN and `receta` ES) spanning short tips, medium Q&A, code/procedure snippets, and multi-paragraph guides. Add unit test in `fhv1_corpus.rs` asserting `(150..=300)` count, 0 duplicates, and 0 overlap with benchmark holdout.
  2. **`P0-1` Leak-Free 400-Prompt Benchmark**: Eliminate all mechanical cloning templates (`"Follow-up ..."`, `"Boundary note ..."`, `"Unrelated request ..."`, `"Marker ..."`) and English boilerplate inside Spanish `receta` prompts. Never put `suite2["deepset_english"]` or `suite2["es_injections"]` in `OUT_OF_DOMAIN_BENIGN`. Build `400` genuinely distinct prompts per domain (`100` per quadrant) with `subtype` metadata:
     - `IN_DOMAIN_VALID` (`100`): 100% matching language (`EN` for `python`, `ES` for `receta`), zero EN leakage in `receta`, spanning short (`4–8` words), medium (`20–60` words), and long (`100–250+` words).
     - `OUT_OF_DOMAIN_BENIGN` (`100`): 100% benign non-adversarial prompts (matching-language EN/ES benign topics + other 9 canonical domains + benign `clinc_oos`/`es_oos`), zero injections/jailbreaks.
     - `HYBRID_BOUNDARY` (`100`): multi-technique blends (`80/20`, `50/50`, `20/80` dilution; prefix/middle/suffix pivots; comments/docstrings/JSON/YAML/recipe footnotes; near-OOD neighbors JS/TS/Rust/Go/SQL/Bash or nutrition/food-chemistry/restaurant-finance/appliance-sales; polarity flips).
     - `ADVERSARIAL_FUZZING` (`100`): explicit injections (`deepset_english` / `es_injections` + domain injections), Base64/Hex/ROT13/leet, Cyrillic/Greek homoglyphs + ZWSP/ZWNJ/ZWJ/BOM + fullwidth, delimiter breakouts (`###`, `"""`, `<|system|>`, `</prompt>`), short/punct edge inputs (`<= 5` chars), high-entropy gibberish, long-context flooding (`>= 2,000` chars / `400–1,000+` words), keyword stuffing + hidden instruction.
     - Enforce strict leak-free split against `canonical_corpus.rs`, `fhv1_corpus_*.jsonl`, AND any `data/fhv1_augmented/` files. Add strict tests in `test_generate_fhv1_benchmark.py`.
  3. **`1B` LLM Augmentation CLI (`tools/augment_fhv1_corpus.py`)**: Add `--augment-llm`, `--provider auto` (resolving `.env` without echoing keys, failing closed when no live provider key exists or HTTP fails — never falling back to template cloning), `--target-count` (`500–1,000+`), multi-variant generation, SHA-256 JSONL caching, deduplication, language purity check, and holdout-overlap guard. Cover offline with `httpx.MockTransport` tests in `test_augment_fhv1_corpus.py`.
* **Verification Gate**: `cargo test -p sf-bench && uv run --script tools/test_generate_fhv1_benchmark.py && uv run --script tools/test_augment_fhv1_corpus.py`

---

### Slice 5 — Frontend View 3 Completion (`P1-1`), Variance Studio Default (`P2-8`), and E2E Spec Assertions (`P2-11`)
* **Files**:
  * `frontend/src/domain/fhv1.ts`
  * `frontend/src/domain/fhv1.test.ts`
  * `frontend/src/gateway/fhv1Client.ts`
  * `frontend/src/ui/fhv1Charts.ts`
  * `frontend/src/ui/Fhv1BenchmarkExplorer.tsx`
  * `frontend/src/ui/Fhv1BenchmarkExplorer.test.tsx`
  * `frontend/src/ui/Fhv1VarianceStudio.tsx`
  * `frontend/src/ui/Fhv1VarianceStudio.test.tsx`
  * `frontend/src/ui/StudioShell.test.tsx`
  * `frontend/e2e/fhv1.spec.ts`
* **Requirements**:
  1. **`P1-1` (`fhv1.ts`, `fhv1Charts.ts`, `fhv1Client.ts`, `Fhv1BenchmarkExplorer.tsx`)**:
     - Parse `failed_dims_count_histogram` and `failed_dims_count_histogram_by_category` in `parseFhv1BenchmarkDetail`.
     - Render modular ECharts canvas (`aria-label="fhv1 failed dimensions histogram"`) with toggle between Global and Per-Category Overlay.
     - Update `parseFhv1Drilldown` to preserve `mean`, `delta_vs_mean`, and `norm_pos` (`number | null`), rendering all floats losslessly via `formatLosslessF64` (**ZERO `.toFixed(`**).
     - Render 1,024D Input Vector Overlay ECharts canvas (`aria-label="fhv1 input vector overlay"`) inside drill-down: overlays `x` across `[min, max]` band + `mean` baseline (`0..1023`, honoring `use_rogue_mask`), highlighting `UNDERFLOW` and `OVERFLOW` breaches with crimson markers and lossless tooltips (`dim`, `x`, `min`, `max`, `mean`, `violation_delta` magnitude + direction, `delta_vs_mean`, `norm_pos`, `status`).
     - Add Category (`ALL | IN_DOMAIN_VALID | OUT_OF_DOMAIN_BENIGN | HYBRID_BOUNDARY | ADVERSARIAL_FUZZING`) and Verdict (`ALL | PASS | FAIL`) controls wired to `listFhv1Traces` (`category`, `passed` query params).
     - Add Vitest coverage for parsers, chart option builders, filters, and lossless formatting.
  2. **`P2-8` (`Fhv1VarianceStudio.tsx`)**: Set default `metric` to `'variance'` and update `Fhv1VarianceStudio.test.tsx`.
  3. **`P2-11` & View 3 E2E (`frontend/e2e/fhv1.spec.ts`)**: Fix line 43 regex `/lab-\d+/` -> `/lab-\d+-\d+/`. Extend `fhv1.spec.ts` (zero `page.route` mocks) to assert histogram canvas + mode toggle, Category + Verdict filters, and 1,024D Input Vector Overlay canvas + lossless drill-down fields (`mean`, `delta_vs_mean`, `norm_pos`).
* **Verification Gate**: `pnpm --dir frontend lint && pnpm --dir frontend build && pnpm --dir frontend test` + grep check confirming zero `.toFixed(` in `fhv1` files.

---

### Slice 6 — Live `1B` Augmentation, Clean `fhv1_*` Reset, 4-Profile Calibration, 24-Run Matrix & 0-ULP On-Disk Export Verification (`P0-2`, `P0-3`)
* **Files**:
  * `tools/verify_fhv1_exports_0ulp.py` (new PEP 723 `uv` verifier using `lancedb`, `openpyxl`, `pyarrow`, `httpx`)
  * `reports/fhv1_task011_empirical_report.md` (new tracked markdown empirical report)
* **Live Execution Steps**:
  1. Generate clean 400-prompt holdout datasets (`data/fhv1_benchmarks/{python,receta}.jsonl`).
  2. Run `tools/augment_fhv1_corpus.py --augment-llm --provider auto` for `python` and `receta` against `.env` (never echoing keys!) expanding to `500–1,000+` unique cached SHA-256 JSONL texts per domain in `data/fhv1_augmented/`. Re-verify **0 overlap** against holdout benchmarks.
  3. Verify `domain_hypercubes` `66` rows + SHA-256 baseline; purge ONLY `fhv1_profiles.lance`, `fhv1_calibration_samples.lance`, `fhv1_benchmark_runs.lance`, `fhv1_audit_traces.lance` in `data/sf-lancedb/`. Re-verify `domain_hypercubes` untouched.
  4. Start `tools/bge_m3_mps_server.py` (`:8080`) non-interactively (`HF_HUB_OFFLINE=1`, `/health` loop, `trap cleanup EXIT`).
  5. Calibrate 4 fresh profiles (`--augmented-llm true`, default metric `variance`):
     - `python` (`normalize = true` and `normalize = false`)
     - `receta` (`normalize = true` and `normalize = false`)
  6. Execute all **24 benchmark runs** (`4 profiles × {full_only, clauses, full_mirror} × {use_rogue_mask=false, true}`) via `fhv1_benchmark`. Record `p50`/`p99` ms/prompt and chunks/sec; verify `json_equal=True` LanceDB vs `reports/fhv1_*.json`; verify 100% prompt-scoped `trace_id = {run_id}-{input_id}`.
  7. Start `sf-proxy` (`:8088`) non-interactively, fetch `/api/v1/fhv1/profiles/{profile_id}/export?format={xlsx,csv,parquet}` and profile JSON for live `normalize=true` and `normalize=false` profiles to `/tmp/fhv1_task011_exports/`, and run `uv run --script tools/verify_fhv1_exports_0ulp.py` asserting exact 0-ULP (`struct.pack('!d', a) == struct.pack('!d', b)`) parity across all `1,024` dims × `{min, max, mean, variance, std_dev, span}`. Clean up PIDs.
  8. Write `reports/fhv1_task011_empirical_report.md` with complete 24-run tables, per-category distributions, subtype analysis, `atomic_phrase` share, latency, and empirical verdict / `vNext` parameterization.
* **Verification Gate**: Verbatim stdout of augmentation counts, overlap=0, 4 calibrations, 24 benchmark runs, LanceDB parity, `verify_fhv1_exports_0ulp.py`, and `domain_hypercubes` integrity check.

---

### Slice 7 — Live Playwright E2E Certification (`P1-4`), Full Gate Re-Verification, Docs Sync & Forensic Evidence Bundle
* **Files**:
  * `CHANGELOG.md` (add concise `TASK-011` bullet under `## [Unreleased]`; freeze `0.2.1`)
  * `TASKS.md` (mark Slice 7 `[x]` and `status: "DONE"`)
  * Untracked (NEVER staged): `audit_task011_evidence.md`
* **Execution Steps**:
  1. Start `:8080` and `:8088` non-interactively with `/health` polling and `trap cleanup EXIT`, execute `PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-$HOME/Library/Caches/ms-playwright}" pnpm --dir frontend test:e2e` live (`9` `playground.spec.ts` + expanded `fhv1.spec.ts`), confirm PIDs stopped.
  2. Run ALL workspace gates and record verbatim stdout:
     - `cargo fmt --all -- --check`
     - `cargo clippy --workspace --all-targets -- -D warnings`
     - `cargo test --workspace`
     - `pnpm --dir frontend lint`
     - `pnpm --dir frontend build`
     - `pnpm --dir frontend test`
     - `uv run --script tools/test_bge_m3_mps_server.py && uv run --script tools/test_augment_fhv1_corpus.py && uv run --script tools/test_generate_fhv1_benchmark.py`
  3. Verify `domain_hypercubes.lance` (`66` rows, byte-identical 19 SHA-256 hashes) and `0.2.1` version freeze.
  4. Update `CHANGELOG.md` (`## [Unreleased]`) and `TASKS.md`, run `agent.sh validate` and `agent.sh notify`, commit Slice 7 atomically (`hbauzan <hbauzan@gmail.com>`).
  5. Audit `git log f239f19..HEAD --stat --format=fuller` (authorship, zero `Co-authored-by:`, zero forbidden lexical mentions, zero staged `.env`/`data/`/`repomix-output.xml`/`audit_*`/`.xlsx`) and assemble untracked `audit_task011_evidence.md`.
  6. **HALT** for human audit and explicit `"OK"` before any `git push` or `git merge --no-ff`.
