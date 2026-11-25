# EXECUTION ROADMAP: `fhv1_1` I+D v4 — HARDENING PRE-RUST, EJE 2 NEAR-OOD, `clause_cap` DoS, CURVA `N_cal` (`TASK-015`)

> **Single Source of Truth**: Self-contained I+D specification for `TASK-015`.  
> **Base**: `main @ 5bcab5f8bd630720809f0a8accc7d62150c851dc` (merge of `TASK-014`; tip of former feature commit `73ca190abe00f4f018662ba0a5e9642284e4606e` is an ancestor).  
> **Branch**: `feat/fhv1-1-id-v4-hardening-and-sample-curve`, cut from that `main`.  
> **Task Governance**: `TASK-015` in [`TASKS.md`](../TASKS.md).  
> **Delivery Fence**: 100% offline I+D. Tracked writes only under `roadmap/`, `TASKS.md`, `tools/`, `reports/`. Untracked writes only under `/tmp/fhv1_1_id_v4/` (JSON/embeddings scratch) and `audit_fhv1_1_id_v4_bundle.md`. **ZERO** edits to `crates/`, `frontend/`, `Cargo.toml`, `manifest.json`, `frontend/package.json`, `architecture_spec.md`, `CHANGELOG.md`. Package stays `0.2.1`. **HALT** before `git push` and before `git merge --no-ff`.

---

## 0. Closure of `TASK-014` (human `OK` already consumed)

Verified at Slice 0 start (2026-11-23):

| Check | Verbatim result |
| :--- | :--- |
| Current branch at architect entry | `main` |
| `git rev-parse HEAD` | `5bcab5f8bd630720809f0a8accc7d62150c851dc` |
| Subject | `merge: integrate TASK-014 fhv1_1 v3 full-1024D dials and lexical guardrail` |
| Author / committer | `Héctor Andrés Bauzán Saavedra <hbauzan@gmail.com>` / same |
| `Co-authored-by:` trailers on merge | `0` |
| `73ca190` is ancestor of `HEAD` | yes |
| `main...origin/main` | in sync (no ahead/behind) |
| Tracked dirty files | `0` |
| Untracked kept | `audit_fhv1_1_id_bundle.md`, `audit_fhv1_1_id_v2_bundle.md`, `audit_fhv1_1_id_v3_bundle.md` |
| `audit_task014_code.txt` | absent (already removed; not recreated) |
| `target/` before Phase-0 cargo | absent |
| `CARGO_TARGET_DIR=.../target cargo clean` | `Removed 0 files` |

No second `git merge --no-ff` and no second `git push origin main` were required: the human-authorized closure of `TASK-014` was already on `origin/main`.

---

## 1. Phase-0 Integrity Audit + Disk Audit (executed before this branch's first code edit)

Fail-closed gate. Every check below passed on 2026-11-23 before Slice 1. Commands that resolve Python dependencies used `UV_CACHE_DIR=/Users/hbauzan/.cache/uv` and `uv run --offline --script`. Cargo used `CARGO_TARGET_DIR=/Users/hbauzan/treepwood/3hm-dimentional-fw/target`.

### 1.1 Git topology

| Check | Verbatim result |
| :--- | :--- |
| Checked-out base before branch cut | `main` = `5bcab5f8bd630720809f0a8accc7d62150c851dc` |
| Feature branch | `feat/fhv1-1-id-v4-hardening-and-sample-curve` |
| Package version | `0.2.1` in `Cargo.toml`, `manifest.json`, `frontend/package.json` |

### 1.2 Disk Audit

Both the repository and `/tmp` are `/dev/disk3s5` on `/System/Volumes/Data`. Floor: `3,145,728` KiB (`3.0 GiB`).

| Moment | `df -h` Size / Used / Avail / Capacity | `df -k` Available |
| :--- | :--- | ---: |
| Architect entry (pre Phase-0; `target/` already absent) | `460Gi` / `393Gi` / `33Gi` / `93%` | `34,577,252` KiB |
| After `cargo clean` confirmation (`Removed 0 files`) | `460Gi` / `393Gi` / `33Gi` / `93%` | `34,577,252` KiB |
| After Phase-0 cargo rebuild (`target/` = `17G`) | `460Gi` / `406Gi` / `18Gi` / `96%` | `19,229,584` KiB |

`du -sh` at Phase-0 close:

| Path | Size |
| :--- | :--- |
| `data/` | `3.7G` |
| `data/sf-lancedb/` | `3.7G` |
| `data/fhv1_1_research/` | `50M` |
| `target/` | `17G` |
| `data/sf-lancedb.bak-pre-calibrate-20261121/` | present, untouched |

Not deleted: `data/`, `data/sf-lancedb/`, the pre-calibrate Lance backup, `data/fhv1_1_research/background_embeddings_1200.parquet`, closed `audit_fhv1_1_id*_bundle.md` files. Floor rule: **PASS** (`19,229,584 >= 3,145,728`).

`TASK-015` peak incremental estimate: temporary `/tmp/fhv1_1_id_v4/` JSON + optional one-shot description embeddings. Keep available KiB above the floor after every heavy step; if free space approaches the floor, delete only `/tmp/fhv1_1_id_v4/` scratch (never LanceDB or tracked trees).

### 1.3 LanceDB and corpora

`data/sf-lancedb/domain_hypercubes.lance`: `19` files, `LANCE_MISSING=[]`, `LANCE_EXTRA=[]`, `DIFF_IDENTICAL=0` against `roadmap/fhv1-task-011-hardening-falsification.roadmap.md` §2. Re-hash after `count_rows()`: `DIFF_IDENTICAL=0`, `HASH_CHANGED_AFTER_COUNT=0`.

| Table | Rows | Expected | Result |
| :--- | ---: | ---: | :--- |
| `domain_hypercubes` | 66 | 66 | OK |
| `fhv1_profiles` | 4 | 4 | OK |
| `fhv1_calibration_samples` | 149458 | 149458 | OK |
| `fhv1_benchmark_runs` | 24 | 24 | OK |
| `fhv1_audit_traces` | 164939 | 164939 | OK |

`data/fhv1_1_research/background_embeddings_1200.parquet`:

```text
PARQUET_ROWS 8147
PARQUET_FULL_DOC 1200
PARQUET_CLAUSE 6947
PARQUET_NORMALIZE_TRUE 8147
PARQUET_FINITE True
PARQUET_MAX_ABS_L2_MINUS_1 1.090048988849901e-07
UNIT_1E-5 PASS
```

### 1.4 Baseline health gates

`PORTS_8080_8088_CLOSED` (no `LISTEN` on `8080..8088`).

Python `uv run --offline --script` (user uv cache): **`192/192`** (`suite_fails=0`).

| Suite | Result |
| :--- | :--- |
| `tools/test_augment_fhv1_corpus.py` | `Ran 11 tests` `OK` |
| `tools/test_bge_m3_mps_server.py` | `Ran 13 tests` `OK` |
| `tools/test_fhv1_1_background_corpus.py` | `Ran 23 tests` `OK` |
| `tools/test_fhv1_1_id_v3_report.py` | `Ran 2 tests` `OK` |
| `tools/test_fhv1_1_lexical_profile.py` | `Ran 38 tests` `OK` |
| `tools/test_fhv1_1_replay_sim.py` | `Ran 33 tests` `OK` |
| `tools/test_fhv1_1_replay_v3.py` | `Ran 39 tests` `OK` |
| `tools/test_fhv1_1_xray.py` | `Ran 29 tests` `OK` |
| `tools/test_generate_fhv1_benchmark.py` | `Ran 4 tests` `OK` |
| **Total** | **`192/192`** |

`cargo fmt --all -- --check`: `FMT=PASS`. `cargo clippy --workspace --all-targets -- -D warnings`: `CLIPPY=PASS`. `cargo test --workspace`: `46` `test result` lines, `PASSED=173`, `FAILED=0`, `IGNORED=0`, `CARGO_TEST=PASS`.

`pnpm --dir frontend lint`: `PNPM_LINT=PASS`. `pnpm --dir frontend test`: `Test Files  14 passed (14)`, `Tests  70 passed (70)`.

Phase-0 decision: **PASS**. Proceed.

---

## 2. Locked invariants

* Python: `uv run --offline --script` only (PEP 723). Export `UV_CACHE_DIR=/Users/hbauzan/.cache/uv`. Zero `pip`, zero `npm`, zero `./setup.sh`.
* `HF_HUB_OFFLINE=1` whenever the embedder runs. Zero internet. Zero reads of `.env`. Do not delete or rewrite `~/.cache/huggingface/`.
* Rust, only at Slice 0 Phase-0 and Slice 4: `export CARGO_TARGET_DIR=/Users/hbauzan/treepwood/3hm-dimentional-fw/target` before every `cargo` invocation.
* Frontend, only at Slice 0 Phase-0 and Slice 4: `pnpm --dir frontend lint` and `pnpm --dir frontend test`.
* Sole author and committer `Héctor Andrés Bauzán Saavedra <hbauzan@gmail.com>`. Set `GIT_AUTHOR_NAME`, `GIT_AUTHOR_EMAIL`, `GIT_COMMITTER_NAME`, and `GIT_COMMITTER_EMAIL` on the commit command. Do not change git config. Zero `Co-authored-by:` trailers. Zero mentions of external assistants, bots, agent brands, editors, IDEs, or external commercial model brands in code, comments, docstrings, test names, this roadmap, reports, or commit messages.
* Stage explicit paths only. Never `git add -A`. Never stage `.env`, `data/`, `audit_*`, `repomix-output.xml`, `.xlsx`, or `.parquet`.
* `normalize=true` on every primary embedding and every primary scorer. Statistical math is `float64`.
* Standalone `fhv1_1` only. Production scorer path stays **OFF** in `TASK-015`.
* LanceDB `data/sf-lancedb/` is read-only, including the pre-calibrate backup. Re-check the 19 SHA-256 hashes and the five row counts at Slice 4.
* One atomic local commit per slice. Do not push. Do not merge. **HALT** after Slice 4.

### 2.1 Numerics reused from current tools

`sep` / `std_pool` stay as in `tools/fhv1_1_xray.py` `coordinate_contrast_stats` and `tools/fhv1_1_replay_sim.py` (`EPS_SIGMA = 1e-9`). Background language lock: `python` → `en`, `receta` → `es` (`V2_DOMAIN_LANG`).

---

## 3. Why v4 exists (verified in `TASK-014`, not re-opened)

`reports/fhv1_1_id_v3_report.md` is the measurement record. Code facts that v4 must fix:

1. **Friendly fire in `S_struct`.** `receta/consulta_corta` mean `S_struct ≈ 0.0289`; `sustitucion_ingredientes ≈ 0.01426`. Drivers in the report: bilateral excess on `punct_ratio` / `digit_ratio` / `symbol_ratio` for short Spanish queries with zero punctuation; Latin letters with tildes counted inside `symbol_n` because `_feature_map` only subtracts ASCII letters; rare-rate denominators collapse a single `¿...?` against declarative calibration into `excess ≈ 20`.
2. **`python` short-idiom / snippet false alarms.** `short_idiom_query` `16/20` below `1.0`; `code_snippet` `6/6` below `1.0` on structural channels that should be upper-tail only.
3. **Near-OOD mixed into Eje 1.** v3 contrast presets that fold `near_ood_neighbor` (and structural noise) into the same dial as general contrast blur the decision surface. v4 separates **Eje 1 (`S_general`)** against `1B_base_tech` from **Eje 2 (`S_near`)** against pure `near_ood_neighbor`.
4. **In-sample threshold bias.** Document-level `CAL_ONLY` on scores fit with the same 600 bundles used for `mu_T`/`LexicalProfile` inflated thresholds (visible on `receta/full_only`). v4 forces **5-fold OOF** for all calibration scores used for thresholds and recipe selection.
5. **DoS / flooding budget still open.** Need an auditable `clause_cap ∈ {None, 16, 24, 32}` with deterministic `edge_plus_struct` selection and real end-to-end latency on `long_context_flooding`.
6. **Sample efficiency unknown.** Need the `N_cal` ladder from description-only through `600` to decide whether `TASK-016` should extend to `800–1,000`.

---

## 4. Slice 1 — Surgical repair of the three verified `S_struct` bugs

Files: `tools/fhv1_1_lexical_profile.py`, `tools/test_fhv1_1_lexical_profile.py` (`>= 44` tests). **No hard-coded domain symbol lists.**

### 4.1 Unidirectional channel penalties (`_outside_excess` / `_evaluate`)

| Side | Channels |
| :--- | :--- |
| Upper only (`value > p99`) | `digit_ratio`, `punct_ratio`, `symbol_ratio`, `non_latin_or_control_unicode_ratio`, `max_repeated_punct_run`, `rare_nonletter_char_rate`, `rare_nonletter_bigram_rate`, `foreign_connector_ratio` |
| Lower only (`value < p01`) | `letter_ratio`, `target_connector_ratio` (keep exemption when `alpha_word_count < 6`) |
| Bilateral | `char_shannon_entropy` only; exempt or soften when `len(text) < 20` so short valid queries are not false-alarmed while `letter_ratio=0` and `punct_ratio` still stop `???!!!` |

Zero punctuation or zero digits on a short Spanish query must never create excess.

### 4.2 Latin letters out of `symbol_ratio`

In `_feature_map`, define `_is_latin_letter(char)` as `char.isalpha()` and `"LATIN" in unicodedata.name(char, "")` (covers `áéíóúüñ` and uppercase). Subtract Latin letters from `symbol_n`. Keep `_is_non_latin_or_control` intact so Cyrillic, Greek, fullwidth, and `Cf` (`\u200b`) still fire at full strength.

### 4.3 Kill the `20×` collapse on short `¿?¡!`

Smooth denominators of `rare_nonletter_char_rate` and `rare_nonletter_bigram_rate` (e.g. `rare_count / max(total_items, SMOOTH_DENOM)` or length-proportional weighting). Document the exact formula and constant in the module. One or two interrogative marks in a Spanish question against declarative calibration must not mark `1.0` (`excess = 20`); bursts of rare operators (`{}=>;::&&`, `???!!!`, JSON smuggling) must still fire strongly.

### 4.4 Regression tests (add while keeping existing coverage)

* `"como hacer salsa blanca"` (0 punctuation, Spanish) → `S_struct == 1.0`
* Spanish rich in tildes (`áéíóúñü`) → `symbol_ratio == 0.0`
* Short `¿...?` question against declarative calibration (no `¿?`) does not collapse to `~0.014` (null or negligible penalty)
* `homoglyph_zwsp_fullwidth`, `extreme_short_punct` (`???`, `!!!`), `_SMUGGLE`, and keyword stuffing still fire strongly

### 4.5 Slice 1 commit

`fix(fhv1): repair unidirectional S_struct channels, Latin symbols, and rare-rate smoothing`

---

## 5. Slice 2 — Motor `fhv1_1` v4

Files: `tools/fhv1_1_replay_v4.py`, dispatch from `tools/fhv1_1_replay_sim.py --mode v4`, `tools/test_fhv1_1_replay_v4.py` (`>= 32` tests). Keep `--mode default`, `v2`, and `v3` behavior-identical.

### 5.1 Dual-axis geometry

1. **Eje 1 (`S_general`)**: `dir1024_sig_sep` (1,024D, `normalize=true`, `w_d = max(sep_d, 0.05)`) against **`1B_base_tech`** only (400 `full_doc` + clauses per language). Do **not** mix `structural_symbol_noise` or `near_ood_neighbor` into `S_general`.
2. **Eje 2 (`S_near`)**: second `dir1024_sig_sep` dial against pure **`near_ood_neighbor`** (100 docs of the domain language from `background_embeddings_1200.parquet`: `en` for `python`, `es` for `receta`). Axes stay fully separated.

### 5.2 Compact recipe catalog (`<= 12` fixed candidates — no combinatorial grids on holdout)

* `eje1_only`: `S_general` only (`beta = 0`)
* `eje1_plus_struct`: `S_general` + `S_struct` v4 (`beta ∈ {0.10, 0.20}`)
* `dual_axis_and`: independent `CAL_ONLY` gates `S_general >= T_gen_p10 AND S_near >= T_near_pX` with `pX ∈ {p02, p05, p10}`
* `dual_axis_blend`: `(1 - lambda) * S_general + lambda * S_near` (`lambda ∈ {0.20, 0.35}`), with and without `S_struct` v4 (`beta = 0.15`)
* `dual_axis_min`: `min(S_general, S_near)` with and without `S_struct` v4

Clauses: fixed auditable `w_f ∈ {0.20, 0.35, 0.50}`. Freeze **one** simple winning recipe with zero holdout leakage.

### 5.3 Mandatory 5-fold OOF for calibration scores

All `cal_scores` for Eje 1, Eje 2, and `S_struct` use **5-fold OOF over the 600 document bundles** (same scheme as `fit_geometry_level`): each calibration bundle is scored only with parameters (`mu_T`, `std_T`, `LexicalProfile`) fit on the other 4 folds (480 bundles). This must remove the in-sample threshold inflation observed on `receta/full_only` in `TASK-014`.

### 5.4 `clause_cap` Anti-Flooding + real latency

Evaluate `clause_cap ∈ {None, 16, 24, 32}` on `clauses` with deterministic `edge_plus_struct` when `n_clauses > cap`: reserve edge clauses (start + end) + mid samples + top-K lowest `S_struct` (CPU pre-filter before embedding).

Start `tools/bge_m3_mps_server.py` (`127.0.0.1:8080`, `HF_HUB_OFFLINE=1`, `trap cleanup EXIT`) **only** to measure real end-to-end `p50/p99` ms on `long_context_flooding` (`python` and `receta`) for uncapped vs `16/24/32`. Kill the exact PID; certify `PORTS_8080_8088_CLOSED`.

### 5.5 Metrics (zero leakage)

Report `CAL_ONLY p05/p10/p15`, `5×5` repeated stratified OOF, bootstrap `1,000` (`seed=0`, `refits_thresholds=True`), `ROC-AUC`, `PR-AUC`, `[ORACLE_UPPER_BOUND]` strictly separated, per-quadrant, per-subtype (including `near_ood_neighbor`, `prompt_injection_jailbreak`, `short_idiom_query`, `code_snippet`, `consulta_corta`, `sustitucion_ingredientes`, `panaderia_fermentacion`, `diagnostico_pasteleria_panaderia`, `smuggle_recipe_footnote`, `dilution_80_20`, `long_context_flooding`), canary `sqlite3/subprocess/json` (explicit `kind` and `F1` vs `FRR`), and latencies `S_struct` (µs) + flooding (ms).

### 5.6 Tests

`tools/test_fhv1_1_replay_v4.py` `>= 32`: 5-fold cal OOF anti-in-sample; isolated Eje 2; dual `CAL_ONLY` gate; deterministic `clause_cap` + `S_struct` prioritization; anti-leakage in thresholds/selection; bit-stability seed `0`; zero NaN/Inf.

### 5.7 Slice 2 commit

`feat(fhv1): add dual-axis v4 replay with OOF calibration and clause_cap`

---

## 6. Slice 3 — Volume curve `N_cal`

Integrate into `--mode v4` (or a subcommand in `tools/fhv1_1_replay_v4.py`). Always evaluate against the fixed 400-prompt holdout (0 leakage). Domains: `python` and `receta`.

### 6.1 `N = 1` description-only

Write one clean realistic paragraph per domain (`python` EN, `receta` ES). Verify `0` overlap with holdout and with the 600 calibration docs. Embed offline via `bge_m3_mps_server.py` (`normalize=true`), store the temporary embedding only under `/tmp/fhv1_1_id_v4/`. Score with explicit fallback `std_T = 0 -> std_pool = std_C` against `1B_base_tech`. Report `ROC-AUC`, `PR-AUC`, threshold relative to `1B` (no holdout), and labeled `[ORACLE_UPPER_BOUND]`.

### 6.2 Real ladder `N ∈ {1 (real doc), 5, 10, 25, 50, 100, 200, 400, 600}`

For each `N < 600`, run **5 deterministic subsample seeds** over the 600 calibration bundles (reuse LanceDB embeddings + raw texts from `data/fhv1_augmented/`). Record `mean ± std` across seeds of: `CAL_ONLY p05/p10 F1`, `FRR`, `FAR`, `ROC-AUC`, `OOD FAR`, `Adv FAR`, `Near-OOD FAR`, threshold `T` stability, and count of coordinates with `sep >= 1.0`. Compute marginal deltas (`ΔF1`, `ΔAUC`, `ΔFRR`, `ΔFAR`) between consecutive rungs to locate saturation and whether `TASK-016` should extend to `800–1,000`.

### 6.3 Full v4 run

Execute `--mode v4` to completion writing JSON only under `/tmp/fhv1_1_id_v4/`. Shut `:8080` and confirm `PORTS_8080_8088_CLOSED`.

### 6.4 Slice 3 commit

`feat(fhv1): run v4 dual-axis replay and N_cal volume curve`

---

## 7. Slice 4 — Report, cleanup, full gates, Approval Gate

### 7.1 Report generator

`tools/fhv1_1_id_v4_report.py` + `tools/test_fhv1_1_id_v4_report.py`. Build `reports/fhv1_1_id_v4_report.md` from `/tmp/fhv1_1_id_v4/*.json` with numeric literals copied verbatim. Fix the two cosmetic v3 generator bugs: correct verbal direction of `"above"`/`"below"`, and explicit `kind` label in the canary table.

Mandatory sections:

* **§0** Executive summary (`TASK-011 → 012 → 013 → 014 → 015`, frozen recipe, what improved, what remains open).
* **§1** Phase-0, disk recovery (`cargo clean`), post-cleanup disk for `/tmp/fhv1_1_id_v4/`.
* **§2** Impact of the three `S_struct` fixes (v3 before vs v4 after on `IN_DOMAIN_VALID` and adversarial subtypes).
* **§3** Eje 1 vs Eje 2 ablation, 5-fold cal OOF impact (especially `receta/full_only`), frozen recipe.
* **§4** DoS `clause_cap` (`None/16/24/32`): F1/FAR on `dilution_80_20`, `smuggle`, `flooding`; real `p50/p99` ms.
* **§5** Volume curve `N_cal = 1 (description) .. 600` (`mean ± std`, marginal deltas, objective recommendation on `800–1,000`).
* **§6** Master tables (`CAL_ONLY p05/p10/p15`, `5×5`, bootstrap `1,000` with `refits_thresholds=true`, separated `[ORACLE_UPPER_BOUND]`) + full subtype breakdown + canary.
* **§7** Honest verdict: readiness for **`TASK-016`** (3 new cold domains + comparative benchmark) and exact **GO / NO-GO** for Rust port (`crates/sf-kernels` + `crates/sf-proxy`). Scorer stays **OFF** production in `TASK-015`.

### 7.2 Cleanup and DONE

Delete `/tmp/fhv1_1_id_v4/` completely. Record post-cleanup `df -h` / `df -k` (`>= 3,145,728` KiB). Mark `TASK-015` `DONE` in `TASKS.md`.

### 7.3 Final gates (verbatim evidence in the untracked audit bundle)

* All `tools/test_*.py` via `UV_CACHE_DIR=/Users/hbauzan/.cache/uv uv run --offline --script`
* `CARGO_TARGET_DIR=.../target cargo fmt --all -- --check`, `clippy --workspace --all-targets -- -D warnings`, `test --workspace` (`173/173`)
* `pnpm --dir frontend lint` and `pnpm --dir frontend test` (`70/70`)
* `git diff --name-only <main_base>..HEAD -- crates/ frontend/ Cargo.toml manifest.json frontend/package.json architecture_spec.md CHANGELOG.md` empty; version `0.2.1`
* LanceDB `19/19` `DIFF_IDENTICAL=0` + `HASH_CHANGED_AFTER_COUNT=0` + counts `66 / 4 / 149458 / 24 / 164939`
* `PORTS_8080_8088_CLOSED`
* Authorship scan (`hbauzan` only, 0 trailers) and `word_boundary_hits = 0` on all added lines
* `agent.sh validate --task-file TASKS.md` and `agent.sh notify --task-file TASKS.md`

### 7.4 Slice 4 commit + halt

Commit: `chore(fhv1): publish the fhv1_1 v4 hardening and sample-curve report`

Write untracked `audit_fhv1_1_id_v4_bundle.md` **after** that commit (verbatim gate stdout, `git log`, `file:line` citations). **STOP.** Do not `git push`. Do not `git merge`. Wait for human `"OK"`.

### 7.5 Anexo Slice 5 — Remediación quirúrgica pre-merge (sobre `f52a693`)

Tras la auditoría forense de `f52a693`, `TASK-015` aplicó un único Slice 5 atómico antes del cierre definitivo:

1. **Fix 1 (`tools/fhv1_1_id_v4_report.py`, `tools/test_fhv1_1_id_v4_report.py`)**: `parse_v3_baseline` extrae `ADVERSARIAL_FUZZING` FAR (§0 `1B_base_tech`) e `IN_DOMAIN_VALID` FRR (§6 `1B_base_tech` `p10` con `tp + fn == 100`) directamente desde `reports/fhv1_1_id_v3_report.md`; `s_struct_lines` emite filas separadas para ambos cuadrantes sin rellenar columnas v3 con datos de v4.
2. **Fix 2 (`tools/fhv1_1_replay_v4.py`, `tools/fhv1_1_id_v4_report.py`)**: calibración previa de `clause_profile` sobre los 600 documentos por dominio; medición de latencia de `long_context_flooding` por prompt (`6` prompts × `3` repeticiones = `18` mediciones con payload `[prompt] + selected_clauses`) para `uncapped` (todas las cláusulas `clause_opt2c`) vs `cap_16`/`cap_24`/`cap_32` (`speedup_vs_uncapped`); evaluación `evaluate_clause_cap_cell` con receta ciega congelada (`eje1_plus_struct|b=0.10`, `w_f=0.35`), conteo `s_struct`/`fallback`/`empty_clauses`, y cobertura de `smuggle_any` + subtipos `smuggle_*`.
3. **Fix 3 (`tools/fhv1_1_replay_v4.py`, `tools/test_fhv1_1_replay_v4.py`)**: `cal_scores` vía `score_axis_oof(..., n_folds=5)` para `N >= 10` y 5-fold LOO para `N = 5`; en `N = 1` (`description_only` y subsample `N=1`) umbral ciego exclusivo desde el contraste `1B_base_tech` (`threshold_relative_1b = q_0.95`, `contrast_p99`, `midpoint = 0.50`, nunca auto-score ni holdout), con `[ORACLE_UPPER_BOUND]` separado.
4. **Fix 4 (`tools/fhv1_1_replay_v4.py`, `tools/test_fhv1_1_replay_v4.py`, `tools/fhv1_1_id_v4_report.py`)**: catálogo compacto bloqueado en exactamente `12` recetas por granularidad (`w_f=0.35` default en `clauses`; sensibilidad `w_f ∈ {0.20, 0.35, 0.50}` en bloque diagnóstico separado); congelamiento 100% ciego de `eje1_plus_struct|b=0.10` (`nested_oof` solo diagnóstico); `[ORACLE_UPPER_BOUND]` calculado sobre el vector holdout de la receta congelada (`oracle_f1 >= cal_only_f1`); ejecución efectiva de `bootstrap_cal_only` (`n_resamples=1000`, `seed=0`, `refits_thresholds=True`) con IC 95% y `delta_f1` pareado en §0 y §6.
5. **Fix 5 (`tools/fhv1_1_replay_v4.py`, `tools/fhv1_1_id_v4_report.py`)**: tabla completa de las 12 recetas en §3 (`F1`, `IN_DOMAIN_VALID FRR`, `OOD FAR`, `Adv FAR`, `Hybrid FAR`, `near_ood_neighbor FAR`, con gate 2D verdadero para `dual_axis_and`) y comparación explícita de literales `beta ∈ {0.00, 0.10, 0.20}` en §2.

Commit Slice 5: `fix(fhv1): remediate v4 report baseline, flooding latency, N_cal OOF, and blind recipe selection`, regeneración de `audit_fhv1_1_id_v4_bundle.md` posterior al commit, `agent.sh validate` / `notify`, y **HALT** pre-merge (`0.2.1` congelado, sin `git push` ni `git merge --no-ff`).

---

## 8. Backlog `TASK-016` (DO NOT execute inside `TASK-015`)

Reserved for a later task after the human reviews `TASK-015`:

1. Incorporate **3 new domain corpora** and cold-validate across **5 domains total**.
2. If the `TASK-015` volume curve has **not** saturated by `N = 600`, evaluate extending calibration volume to `N = 800..1,000`.
3. Run a **standardized comparative benchmark** against reference guardrail methodologies (offline, same holdout contracts, no production enablement).

---

## 9. Approval gate

The human reviews `reports/fhv1_1_id_v4_report.md` and `audit_fhv1_1_id_v4_bundle.md`. Integration waits for an explicit `OK`.
