# EXECUTION ROADMAP: `fhv1_1` I+D v3 — FULL-1,024D DIRECTIONAL DIALS, AUTO-CALIBRATED LEXICAL/SYMBOL GUARDRAIL, 1,200-DOC `1B` (`TASK-014`)

> **Single Source of Truth**: Self-contained I+D specification for `TASK-014`.  
> **Base**: `main @ 89f1cba2789ec2f0e54e149cc987fb5de8c15c6c`.  
> **Branch**: `feat/fhv1-1-id-v3-full1024d-and-lexical-guard`, cut from that `main` because `git merge-base --is-ancestor 6a0831a main` and `git merge-base --is-ancestor a89b20d main` are both true.  
> **Task Governance**: `TASK-014` in [`TASKS.md`](../TASKS.md).  
> **Delivery Fence**: 100% offline I+D. Tracked writes only under `roadmap/`, `TASKS.md`, `tools/`, `reports/`. Untracked writes only under `data/fhv1_1_research/background_embeddings_1200.parquet` (after deleting the verified obsolete `background_embeddings_1k.parquet`) and `audit_fhv1_1_id_v3_bundle.md`. **ZERO** edits to `crates/`, `frontend/`, `Cargo.toml`, `manifest.json`, `frontend/package.json`, `architecture_spec.md`, `CHANGELOG.md`. Package stays `0.2.1`. **HALT** before `git push` and before `git merge --no-ff`.

---

## 1. Phase-0 Integrity Audit (executed before this branch's first code edit)

Fail-closed gate. Every check below passed on 2026-11-23 before the branch was cut. Commands that resolve Python dependencies used `UV_CACHE_DIR=/Users/hbauzan/.cache/uv` and `uv run --offline --script`. A first attempt with the process-default `UV_CACHE_DIR` (an empty temporary directory) could not resolve `httpx`, `lancedb`, or `torch` offline; that was an environment override, not a missing repository cache. Cargo used `CARGO_TARGET_DIR=/Users/hbauzan/treepwood/3hm-dimentional-fw/target`.

### 1.1 Git topology

| Check | Verbatim result |
| :--- | :--- |
| `git status --short` before the branch | `?? audit_fhv1_1_id_bundle.md` and `?? audit_fhv1_1_id_v2_bundle.md` only |
| Tracked dirty files | `0` |
| `git rev-parse main` | `89f1cba2789ec2f0e54e149cc987fb5de8c15c6c` |
| `main` subject | `merge: integrate TASK-012 fhv1_1 x-ray/replay and TASK-013 v2 fine dials` |
| `6a0831a` ancestor of `main` | yes (`chore(fhv1): publish the fhv1_1 v2 fine-dial and scale report`) |
| `a89b20d` ancestor of `main` | yes (`chore(fhv1): publish Phase 0/2 X-ray and offline replay scientific report`) |
| Checked-out `HEAD` at audit time | `main` = `89f1cba2789ec2f0e54e149cc987fb5de8c15c6c` |

Package version field is `0.2.1` in `Cargo.toml`, `manifest.json`, and `frontend/package.json`. `Cargo.toml` also lists dependency versions; the package version itself is `0.2.1`.

### 1.2 Disk Audit #1

Both the repository and `/tmp` are `/dev/disk3s5` on `/System/Volumes/Data`.

| Moment | `df -h` Size / Used / Avail / Capacity | `df -k` Available |
| :--- | :--- | ---: |
| Before `/tmp` scratch removal | `460Gi` / `411Gi` / `12Gi` / `98%` | `12,074,392` KiB |
| After `/tmp/fhv1_*` removal | `460Gi` / `411Gi` / `12Gi` / `98%` | `12,074,264` KiB |

`du -sh` before cleanup:

| Path | Size |
| :--- | :--- |
| `data/` | `3.7G` |
| `data/sf-lancedb/` | `3.7G` |
| `data/fhv1_1_research/` | `47M` |
| `target/` | `21G` |
| `data/sf-lancedb.bak-pre-calibrate-20261121/` | `3.8M` (left untouched) |

`TASK-014` peak incremental estimate: `~60–120 MiB` for the `1,200`-doc parquet plus temporary `/tmp/fhv1_1_id_v3/` JSON. Floor: `3,145,728` KiB (`3.0 GiB`). Available space stayed above `12,074,264` KiB. Floor rule: pass.

Removed stale `/tmp/fhv1_*` scratch (logs, `fhv1_check` `312K`, `fhv1_old_reports` `400K`, and the small sibling logs listed by that glob). `df -k` Available fell by `128` KiB versus the pre-cleanup sample because other disk activity exceeded the scratch that was deleted. Both figures are recorded.

Not deleted: `data/sf-lancedb/`, the pre-calibrate Lance backup, `data/fhv1_augmented/`, `data/fhv1_benchmarks/`, `data/fhv1_1_research/background_embeddings_1k.parquet`, `.env`, `~/.cache/huggingface/`, every tracked file. `audit_fhv1_1_id_bundle.md` (`34K`) and `audit_fhv1_1_id_v2_bundle.md` (`41K`) were **kept**. Both parent commits are on `main`, so removal was authorized; combined size is negligible against `~11.5 GiB` free, and they remain the closed-task evidence bundles.

External Cargo target: the process environment named a temporary `CARGO_TARGET_DIR` that did not exist. `find` under `/Users/hbauzan/treepwood` (depth 3) found only `3hm-dimentional-fw/target`. After the cargo gate that directory was still absent. Every later `cargo` invocation must export the in-repo target path so a second `target/` is never created.

### 1.3 LanceDB and corpora

`data/sf-lancedb/domain_hypercubes.lance`: `19` files, `LANCE_MISSING=[]`, `LANCE_EXTRA=[]`, `DIFF_IDENTICAL=0` against `roadmap/fhv1-task-011-hardening-falsification.roadmap.md` §2. Re-hash after `count_rows()`: `POST_CONNECT_DIFF_IDENTICAL=0`.

| Table | Rows | Expected | Result |
| :--- | ---: | ---: | :--- |
| `domain_hypercubes` | 66 | 66 | OK |
| `fhv1_profiles` | 4 | 4 | OK |
| `fhv1_calibration_samples` | 149458 | 149458 | OK |
| `fhv1_benchmark_runs` | 24 | 24 | OK |
| `fhv1_audit_traces` | 164939 | 164939 | OK |

`data/fhv1_1_research/background_embeddings_1k.parquet`: `7644` rows, `normalize=true` on all rows, `float64` shape `(7644, 1024)`, all finite, `MAX_ABS_L2_MINUS_1=1.090049e-07` (`UNIT_1E-5 PASS`). Granularity: `full_doc=1000`, `clause_opt2c=6644`.

Augmented calibration caches are SHA-named, not `{python,receta}.jsonl`. That is the writer contract in `tools/augment_fhv1_corpus.py`. Both files parsed cleanly:

| File | Rows | Manifest `count` | `holdout_overlap` |
| :--- | ---: | ---: | ---: |
| `data/fhv1_augmented/python_4d99e2e15688ac41d35e792ebbe8b237ebbe7011292e553bf2666606dff217d4.jsonl` | 600 | 600 | 0 |
| `data/fhv1_augmented/receta_6c812ff57bc7c83b950a8e767967ce278e590d71f44cc5a8b6045158d315cb40.jsonl` | 600 | 600 | 0 |

`data/fhv1_benchmarks/python.jsonl` `400`, `receta.jsonl` `400`. `tools/fhv1_1_background_corpus.jsonl` `1000` valid rows: `en=500`, `es=500`, strata `general_prose=600`, `technical_structured=200`, `near_ood_neighbor=200`.

### 1.4 Baseline health gates

`PORTS_8080_8088_CLOSED` (no `LISTEN` socket on `8080` through `8088`).

Python `uv run --offline --script` (user uv cache):

| Suite | Result |
| :--- | :--- |
| `tools/test_augment_fhv1_corpus.py` | `Ran 11 tests` `OK` |
| `tools/test_bge_m3_mps_server.py` | `Ran 13 tests` `OK` |
| `tools/test_generate_fhv1_benchmark.py` | `Ran 4 tests` `OK` |
| `tools/test_fhv1_1_background_corpus.py` | `Ran 16 tests` `OK` |
| `tools/test_fhv1_1_xray.py` | `Ran 26 tests` `OK` |
| `tools/test_fhv1_1_replay_sim.py` | `Ran 33 tests` `OK` |
| **Total** | **`103/103`**, of which **`75`** are `fhv1_1` (`16+26+33`) |

`cargo fmt --all -- --check`: `FMT=PASS`. `cargo clippy --workspace --all-targets -- -D warnings`: `CLIPPY=PASS`. `cargo test --workspace`: `46` `test result` lines, `PASSED=173`, `FAILED=0`, `IGNORED=0`, `CARGO_TEST=PASS`.

`pnpm --dir frontend lint`: `PNPM_LINT=PASS` (`oxlint`). `pnpm --dir frontend test`: `Test Files  14 passed (14)`, `Tests  70 passed (70)`.

`/Users/hbauzan/treepwood/fabrica_de_software/agent.sh validate --task-file TASKS.md` at audit time: `[OK] Task file valid: TASK-013 [DONE]`.

Phase-0 decision: **PASS**. Proceed.

---

## 2. Locked invariants

* Python: `uv run --offline --script` only (PEP 723). Export `UV_CACHE_DIR=/Users/hbauzan/.cache/uv`. Zero `pip`, zero `npm`, zero `./setup.sh`.
* `HF_HUB_OFFLINE=1` whenever the embedder runs. Zero internet. Zero reads of `.env`. Do not delete or rewrite `~/.cache/huggingface/`.
* Rust, only at Slice 4: `export CARGO_TARGET_DIR=/Users/hbauzan/treepwood/3hm-dimentional-fw/target` before every `cargo` invocation.
* Frontend, only at Slice 4: `pnpm --dir frontend lint` and `pnpm --dir frontend test`.
* Sole author and committer `Héctor Andrés Bauzán Saavedra <hbauzan@gmail.com>`. Set `GIT_AUTHOR_NAME`, `GIT_AUTHOR_EMAIL`, `GIT_COMMITTER_NAME`, and `GIT_COMMITTER_EMAIL` on the commit command. Do not change git config. Zero `Co-authored-by:` trailers. Zero mentions of external assistants, bots, agent brands, editors, IDEs, or external commercial model brands in code, comments, docstrings, test names, this roadmap, reports, or commit messages.
* Stage explicit paths only. Never `git add -A`. Never stage `.env`, `data/`, `audit_*`, `repomix-output.xml`, `.xlsx`, or `.parquet`.
* `normalize=true` on every primary embedding and every primary scorer. Statistical math is `float64`. Embedder outputs are IEEE 754 `float32` unit vectors on `S^{1023}` promoted to `float64` for scoring. `normalize=false` stays falsified; do not revive it.
* Score all `1,024` coordinates in every `F_dir1024` variant. Weights satisfy `w_d >= w_floor > 0` for every `d`.
* Standalone `fhv1_1` only. Do not implement a `3HM + fhv1_1` cascade.
* Do not route short queries onto `clause_opt2c`. That route was falsified: it lowered F1 and opened `extreme_short_punct` FAR.
* LanceDB `data/sf-lancedb/` is read-only, including the pre-calibrate backup directory. Re-check the 19 SHA-256 hashes and the five row counts at Slice 4.
* One atomic local commit per slice. Do not push. Do not merge.

### 2.1 Numerics reused from the current tools

`sep` is `tools/fhv1_1_xray.py` `coordinate_contrast_stats`:

```text
std_pool[d] = sqrt( (std_T[d]^2 + std_C[d]^2) / 2 )
sep[d]      = abs(mu_T[d] - mu_C[d]) / (std_pool[d] + eps)
```

`std_T` and `std_C` are the sample standard deviations (`ddof=1`) already produced for calibration and background moments. `eps` inside `coordinate_contrast_stats` stays that function's `EPS`. Directional margins in the v3 scorer use the same `std_pool` and add `fhv1_1_replay_sim.EPS_SIGMA` (`1e-9`) in the denominator, as specified in §6. `mu` and `std` for a regime are fit on the **same granularity** as the vectors being scored (`full_doc` or `clause_opt2c`). Background contrast language follows `V2_DOMAIN_LANG`: `python` uses `en`, `receta` uses `es`.

---

## 3. Why v3 exists (verified in `TASK-013`, not re-opened)

`reports/fhv1_1_id_v2_report.md` is the measurement record. The code facts that v3 must fix:

1. **Blind coordinates.** `polarity_score` in `tools/fhv1_1_replay_v2.py` scores only `POLARITY_FLIP_DIALS` (coordinates where `mean_T * mean_C < 0`, observed on dims `42–183` in that run). The other coordinates never enter `F_polarity`. Same-sign separators such as `dim_553` (`sep=2.21` on `receta`) and `dim_577` / `dim_104` on `python/clauses` are dropped. `python/clauses` then misses `extreme_short_punct` and `homoglyph_zwsp_fullwidth`.
2. **Fixed blend and starved anchors.** `recipe_vector(..., "polarity_plus_base")` returns `mean(F1, F2_L2, F3, F_polarity)`, so `F_polarity` is diluted to one quarter. `positive_f3_bonus` drops polarity-flip coordinates before anchor selection, which left `python/clauses` with `0` `F3` anchors and pulled `base` below the `TASK-012` level.
3. **No structural noise in `1B`, and no character telemetry.** The `1,000`-doc background has no pure punctuation, digit, or symbol stratum. Nothing in `fhv1_1` measures repeated punctuation, rare non-letters, or connector glue on the raw string. `bge-m3` is nearly language-agnostic (`0` dims with `sep_lang >= 1.0` on topic-matched EN vs ES prose, max `0.8729` at `dim_278`), so cross-language injections and symbol smuggling are invisible to the embedding alone.

Locked operating results that v3 must not undo: document-level `CAL_ONLY` (group calibration `sample_id` intervals opened by `full_doc`); `normalize=true`; no short-query clause routing; standalone `fhv1_1`.

---

## 4. Slice 1 — Stratum 4 and the `1,200`-doc cache

### 4.1 Corpus

Keep the existing `1,000` lines of `tools/fhv1_1_background_corpus.jsonl` **byte-identical**. Append `200` rows and nothing else:

* `100` EN rows `bg-en-0501` … `bg-en-0600`, then `100` ES rows `bg-es-0501` … `bg-es-0600`.
* `lang` is `en` or `es`. `stratum` is `structural_symbol_noise`.
* Keys stay exactly `{id, lang, stratum, topic, text}`.
* `topic` is the sub-pattern, `25` rows per topic per language: `punct_burst`, `digit_dump`, `symbol_operator`, `mixed_low_lexical`.

Sub-pattern content:

1. `punct_burst`: ASCII punctuation and delimiter runs (`?`, `!`, `.`, `-`, `;`, brackets, quotes). No alphabetic token is required. Sequences must not be copies of any holdout string.
2. `digit_dump`: dates, timestamps, measurements, IPv4/port pairs, hex, UUID-shaped ids, checksum-shaped hex, numeric tables, ratios, version strings. Invent the numbers; do not copy a holdout.
3. `symbol_operator`: braces, pipes, arrows (`=>`, `->`, `::`), slashes, and structural tokens that appear in markup or non-Python syntax. EN rows must not match `PYTHON_LEAK_RE` in `tools/test_fhv1_1_background_corpus.py` (no Python keywords, no `def name(`, no `__init__`).
4. `mixed_low_lexical`: sparse non-domain words mixed with symbols and digits. EN: zero Python keywords/syntax. ES: zero culinary/recipe terms under `ES_CULINARY_LEAK_RE`. Existing EN and ES purity regexes still apply to this stratum.

Anti-template rule: every `text` is unique inside the file; pairwise alphabetic Jaccard stays `< 0.72` where both sides have alphabetic tokens (the current test); raw prefixes of the first `24` non-whitespace characters are unique per language inside this stratum. Do not stuff a shared alphabetic nonce into `punct_burst` rows just to satisfy the old word-prefix function. Update that test so an empty alphabetic prefix is legal only for `structural_symbol_noise`, and add the raw-prefix assertion.

### 4.2 Tests (`tools/test_fhv1_1_background_corpus.py`, `>= 22` tests, all passing)

Update the `16` existing tests so they accept `1,200` rows (`600` EN + `600` ES) and the four strata per language (`300 / 100 / 100 / 100`). Length quotas and sentence-uniqueness rules that describe prose stay on the original three strata. Add tests that prove, for every new row and every reference string:

* `0` exact raw equality,
* `0` NFKC-casefold equality,
* `0` shared 4-word windows,
* `0` shared 5-word windows,
* `0` exact stripped-character-sequence equality,

against all of: `data/fhv1_benchmarks/{python,receta}.jsonl` (this includes `extreme_short_punct` and `extreme_high_entropy_gibberish`), `crates/sf-bench/src/suite2_prompts.json`, the `1A` curated fixtures `crates/sf-bench/fixtures/fhv1_corpus_*.jsonl` plus quoted strings already harvested from `crates/sf-bench/src/canonical_corpus.rs`, and `data/fhv1_augmented/*.jsonl`.

**Stripped-character-sequence**: delete every Unicode whitespace character, then compare the remaining string exactly, and also compare the NFKC-casefold of that remaining string. A punctuation burst that becomes identical to a holdout after space removal is a failure.

Also assert the `25/25/25/25` topic quota, id continuity, and that the first `1,000` parsed rows still match the pre-slice id/stratum/topic/text values (load the expected prefix from the test, or hard-lock the id sequence `bg-en-0001..0500` then `bg-es-0001..0500` in the original block order).

### 4.3 Embeddings

Start `tools/bge_m3_mps_server.py` as a background process:

```text
HF_HUB_OFFLINE=1 UV_CACHE_DIR=/Users/hbauzan/.cache/uv \
  uv run --offline --script tools/bge_m3_mps_server.py
```

Poll `http://127.0.0.1:8080/health` until `status=ok` and `dim=1024`. Install `trap cleanup EXIT` that kills that PID and its children. Do not call `./setup.sh`.

Embed all `1,200` documents at `normalize=true` for `full_doc` and `clause_opt2c` by reusing `fhv1_1_xray.run_mode_embed_bg` (no unnormalized sidecar). Write `data/fhv1_1_research/background_embeddings_1200.parquet`. Verify:

* row count equals the segmenter output (record `full_doc` and `clause_opt2c` counts; `full_doc` must be `1200`),
* zero NaN/Inf,
* every row `normalize=true`,
* `max |L2 - 1| < 1e-5`.

Only after that verification, delete `data/fhv1_1_research/background_embeddings_1k.parquet`. Shut the server down and confirm `PORTS_8080_8088_CLOSED`.

### 4.4 Contrast presets in `tools/fhv1_1_xray.py`

Preserve `--mode` paths that implement v1 and v2. Do not change the meaning of the existing presets when they are fed the legacy three strata:

| Preset | Strata | `full_doc` rows per language on the `1,200` cache |
| :--- | :--- | ---: |
| `1B_base_tech` | `general_prose`, `technical_structured` | 400 |
| `1B_base_tech_noise` | those two, plus `structural_symbol_noise` | 500 |
| `1B_full` | `general_prose`, `technical_structured`, `near_ood_neighbor` | 500 |
| `1B_full_v3` | `1B_full` plus `structural_symbol_noise` | 600 |

`1B_full` does **not** include `structural_symbol_noise`. That keeps the `TASK-013` contrast comparable. Add unit coverage in `tools/test_fhv1_1_xray.py` until that file has `>= 28` tests. Tests construct synthetic groups; they must not open LanceDB or the network. A parquet contract test may read `background_embeddings_1200.parquet` because this repository already requires the local `data/` tree.

### 4.5 Slice 1 commit

`feat(fhv1): add 200-doc structural_symbol_noise stratum to 1B background corpus`

Stage only the tracked `tools/` files that this slice changed (and `TASKS.md` if the slice checkbox is updated). Do not stage the parquet.

---

## 5. Slice 2 — Auto-calibrated structural guardrail

New module `tools/fhv1_1_lexical_profile.py`. PEP 723 header, `float64`, no ML dependencies, no network. Execution target is microseconds per prompt on CPU. **No hand-written domain symbol allowlist or blocklist.** Every rare-character threshold comes from the `600` calibration documents of the domain being scored.

### 5.1 Features (raw text, before NFKC)

Compute at least:

* `letter_ratio`, `digit_ratio`, `punct_ratio`, `symbol_ratio` (characters that are not ASCII letters, digits, whitespace, or basic ASCII punctuation),
* `non_latin_or_control_unicode_ratio` (category `Cf`, fullwidth forms, Cyrillic, Greek, and other non-Latin scripts),
* `max_repeated_punct_run` (`???` → `3`),
* `char_shannon_entropy`,
* `alpha_word_count`.

Rare non-letters, fit separately on `full_doc` texts and on `clause_opt2c` texts:

* `df(c)` = fraction of calibration documents containing non-letter character `c` (`not c.isalpha() and not c.isspace()`).
* `df(b)` = fraction containing each 2-character non-letter bigram `b`.
* At inference, `rare_nonletter_char_rate` and `rare_nonletter_bigram_rate` are the weighted surprise of characters/bigrams whose calibration document frequency is `< 0.01`. A character that appears in `>= 1%` of calibration docs contributes `0`. Weights are the in-prompt relative frequency of those rare items. The intended consequence, which tests must lock with calibration fixtures rather than with a symbol list in production code: `{ } ; =>` are rare in `receta` calibration and common cooking marks (`1/4`, `2g`, `?`, `,`) are not; `;`, `=>`, `::`, `&&`, `/*` are rare in `python` calibration and `_ : ( ) [ ] { }` are not, if the real calibration corpus actually has those frequencies. If a fixture's empirical `df` disagrees with that story, the empirical `df` wins. Do not hardcode the story.

Connectors (closed sets, not domain maps):

* EN: `the, of, to, and, in, a, an, for, is, on, with, that, as, by, from, or, at, this, it, be, are, was, if, not`
* ES: `de, la, el, y, en, con, para, un, una, los, las, del, al, por, que, se, es, su, como, más, o, pero, sin, sobre`

Primary language is whichever of those two sets has the higher total count across the `600` calibration documents. No `python→en` / `receta→es` table.

`target_connector_ratio` and `foreign_connector_ratio` are ratios over alphabetic word tokens.

**Short-text rule:** if `alpha_word_count < 6`, the missing-connector penalty is `0.0`. Still compute `letter_ratio`, `punct_ratio`, `max_repeated_punct_run`, `non_latin_or_control_unicode_ratio`, `rare_nonletter_char_rate`, and `foreign_connector_ratio`.

### 5.2 Score `S_struct ∈ (0, 1]`

Fit on the `600` calibration docs only (the granularity's own texts). For each structural channel, store a normal envelope: lower/upper as `p01` / `p99`, and a robust scale `max(p95 - median, IQR, floor)` with a positive numerical floor so the scale cannot be zero. Holdout text never enters `fit`.

`excess_f >= 0` is the one-sided distance outside that envelope, divided by the robust scale. Inside the envelope, `excess_f = 0`. Then

```text
S_struct = 1.0                                              if every excess_f == 0
S_struct = exp( -sum(w_f * excess_f) / scale )             otherwise
```

`S_struct` is in `(0, 1]`. In-envelope calibration prompts score exactly `1.0`. Support `full_doc` and a clause reduction `min` over clause scores. Return `top_triggered_features` (name, excess, weight) sorted by descending contribution. Provide a deterministic latency function that reports `p50` and `p99` microseconds per prompt over a fixed repeated input (no wall-clock assertion tighter than "finite and non-negative"; the benchmark must be callable and deterministic in its iteration count).

Channel weights `w_f` are constants in the module, not fit on holdout. Document them next to the formula. `scale` in the exponential is a positive constant (not the per-channel robust scale).

### 5.3 Tests

`tools/test_fhv1_1_lexical_profile.py` with `>= 26` tests. Cover: calibration uses only the supplied fit texts; EN vs ES detection from connector counts with no domain map; a benign recipe fragment containing `1/4`, `2g`, and `?` stays at `S_struct == 1.0` when those marks are common in the fit set; code/JSON/delimiter text fitted on recipe-like prose fires strongly; `???` / `!!!` and zero-letter strings fire; Cyrillic, ZWSP, and fullwidth homoglyphs fire on the raw string even if an NFKC fold would hide them; short valid queries (`< 6` alphabetic words) take no missing-connector penalty; a long keyword list without connectors does; an EN connector run inside an ES-fitted recipe raises `foreign_connector_ratio`; `=>`, `::`, `&&` fire when they are rare in the python-like fit set and stay quiet when they are common; empty string, one character, and emoji-only input produce finite scores and no NaN/Inf.

### 5.4 Slice 2 commit

`feat(fhv1): add auto-calibrated character, symbol, and connector structural guardrail`

---

## 6. Slice 3 — `F_dir1024`, swept hooks, v3 replay

### 6.1 Dispatch

`tools/fhv1_1_replay_sim.py --mode v3` imports `tools/fhv1_1_replay_v3.py` and calls it. `--mode` default (v1) and `--mode v2` stay behavior-identical. Existing tests in `tools/test_fhv1_1_replay_sim.py` must still pass.

### 6.2 Directional scorers

Fit `mu_T`, `std_T` on calibration and `mu_C`, `std_C` on the selected `1B` preset. Zero holdout rows in that fit. For every `d ∈ {0..1023}`:

```text
dir_d = sign(mu_T[d] - mu_C[d])     # 0.0 only on exact equality
m_d   = 0.5 * (mu_T[d] + mu_C[d])
u_d   = dir_d * (x_d - m_d) / (std_pool[d] + EPS_SIGMA)
```

`std_pool` is the formula in §2.1. Three variants, each with strictly positive weights on all `1,024` dims:

1. `dir1024_sig_sep`: `sum_d w_d * sigmoid(u_d) / sum_d w_d` with `w_d = max(sep_d, 0.05)`.
2. `dir1024_sig_sep2`: same with `w_d = max(sep_d^2, 0.01)`.
3. `dir1024_clip_polboost`: `clip(0.5 + 0.5 * u_d, 0, 1)` with `w_d = max(sep_d, 0.05) * (1.5 if mu_T[d] * mu_C[d] < 0 else 1.0)`.

Same-sign coordinates stay in the sum. A unit test with `mu_T = +0.06`, `mu_C = +0.01` on one coordinate (and a non-tied contrast on the others) must change the score when that coordinate moves. A second test mutates each coordinate `0..1023` on a no-tie fixture and asserts the score changes. Exact `dir_d = 0` remains the specified tie rule; the coverage fixture simply contains no ties. Record the tie count if a real preset produces one.

Mandatory baselines in the same harness, not in a side script:

* `polarity_v2_subset`: call the existing `polarity_score` definition (same formula as `TASK-013`).
* `base_repaired`: `F1`, `F2_L2`, and an `F3` that keeps every anchor with `sep >= 1.0` regardless of sign-flip. Do not drop `POLARITY_FLIP_DIALS` before `F3`.
* `Tail-Z` for `P ∈ {3, 5, 10, 25}` and standalone `F2_L2`, using the existing tail and L2 implementations.

### 6.3 Sweeps (no fixed 25/75 blend)

`alpha_guard ∈ {0.00, 0.05, 0.10, 0.15, 0.20, 0.30}` for both

```text
S = (1 - a) * S_dir + a * S_guard
S = (S_dir ** (1 - a)) * (S_guard ** a)
```

`S_guard` is each of `F2_L2` and `Tail-Z` at `P ∈ {5, 10, 25}`.

`beta_struct ∈ {0.00, 0.05, 0.10, 0.15, 0.20, 0.30}`:

```text
S_final = S_sem * (1.0 - beta_struct * (1.0 - S_struct))
```

and the multiplicative comparison `S_sem * (S_struct ** gamma)` for `gamma ∈ {0.10, 0.25, 0.50}`.

When `S_struct == 1`, both hooks are the identity (`S_final == S_sem`). In `clauses` mode, report both `S_struct(full_doc)` and `min(S_struct(full_doc), min_clause S_struct)`.

Clause blend `w_f ∈ {0.20, 0.35, 0.50, 0.70}` via the existing `blend_full_min_clause`. The report must show the effect on `smuggle_recipe_footnote` and `dilution_80_20` against `IN_DOMAIN_VALID` FRR. `TASK-013` measured `80%` and `74%` FAR on those two subtypes; v3 records the new rates rather than assuming those percentages still hold.

### 6.4 Contrasts, thresholds, uncertainty

Run the ablation on `1B_base_tech`, `1B_base_tech_noise`, `1B_full`, and `1B_full_v3`, each for `python/full_only`, `python/clauses`, `receta/full_only`, `receta/clauses`.

* **Primary:** document-level `CAL_ONLY` at `p05`, `p10`, and `p15`. The threshold is a percentile of the `600` calibration document bundles only. Group bundles the way v2 does (`assign_document_bundle_ids`: a `full_doc` row opens an interval of following `clause_opt2c` rows). Holdout labels are not an input to that percentile.
* **Secondary:** `5×5` repeated stratified OOF. For the nested auto-selected row, both the recipe/blend choice and the decision threshold are fit inside the training fold only. A test must fail if a fold's selector reads the held-out fold.
* **Paired bootstrap:** `1,000` resamples, seed `0`, `95%` CI for F1, FRR, FAR, ROC-AUC, and for paired `ΔF1` against the frozen `TASK-013` and `TASK-012` headline numbers. Document `bootstrap_refits_thresholds` as true when each resample refits the threshold on that resample's calibration (or training) scores, and false only if a method truly reuses a frozen threshold. Do not silently mix the two.
* `[ORACLE_UPPER_BOUND]` rows are computed if useful and always labeled. They are not the primary table.
* Emit the full subtype breakdown that the benchmark files actually contain, the four quadrants `IN_DOMAIN_VALID`, `OUT_OF_DOMAIN_BENIGN`, `HYBRID_BOUNDARY`, `ADVERSARIAL_FUZZING`, the `sqlite3` / `subprocess` / `json` canary (the benchmark rows that carry those markers; record `n`), per-subtype `S_struct` firing diagnostics, and `S_struct` `p50`/`p99` microseconds.

Write JSON under `/tmp/fhv1_1_id_v3/` only. Slice 4 reads that directory and then deletes it. Do not write those JSON files under `reports/` or `data/`.

### 6.5 Tests

`tools/test_fhv1_1_replay_v3.py` with `>= 30` tests: 1,024D mutation coverage; same-sign sensitivity; `base_repaired` keeps a `sep >= 1.0` anchor that is also a sign flip; additive versus multiplicative guardrail numerics; `S_struct == 1` identity; a single poisoned clause moves `min(full, min_clause)` and does not move the full-doc-only hook; nested selector ignores the held-out fold; `CAL_ONLY` percentile ignores holdout scores; Base64 fail-closed behavior stays as in v2 (`fail_closed_min`); `5×5` OOF and bootstrap are bit-stable across two calls with seed `0`; empty and non-finite inputs raise or return a documented finite fail-closed score with zero NaN/Inf in the public arrays.

### 6.6 Slice 3 commit

`feat(fhv1): implement 1024D directional dials, structural hook, and v3 replay`

Run `--mode v3` to completion so `/tmp/fhv1_1_id_v3/` exists for Slice 4. If a full grid is too large to finish in one process, split by domain/regime into separate JSON files in that directory, but every cell the report claims must be present on disk before the Slice 3 commit. The commit itself does not include `/tmp`.

---

## 7. Slice 4 — Report, cleanup, gates

Write `reports/fhv1_1_id_v3_report.md` by reading `/tmp/fhv1_1_id_v3/*.json`. Do not hand-copy numbers. The generator is a Python script under `tools/` (PEP 723) or a function in `fhv1_1_replay_v3.py` invoked once; the markdown is the tracked artifact.

Required sections:

* **§0** one-page executive table: `TASK-011` → `TASK-012` → `TASK-013` → `TASK-014` with `CAL_ONLY p10`, `5×5` OOF mean±std, ROC-AUC, OOD / adversarial / hybrid / near-OOD FAR, `S_struct` `p50`/`p99` microseconds, and a short list of what improved and what did not.
* **§1–§9**: this Phase-0 audit plus Disk Audit #1, a closing disk measurement, Stratum 4 impact across the four presets, `F_dir1024` versus `polarity_v2_subset` versus `base_repaired`, guardrail and `S_struct` ablations with per-feature firing, `w_f` on `smuggle_recipe_footnote` and `dilution_80_20`, the `5×5` / bootstrap / `CAL_ONLY` master tables, subtype deltas (include `extreme_short_punct`, `homoglyph_zwsp_fullwidth`, `near_ood_neighbor`, `panaderia_fermentacion`, `diagnostico_pasteleria_panaderia`, `long_debugging_walkthrough`, `smuggle_recipe_footnote`, `dilution_80_20`, and the `sqlite3`/`subprocess`/`json` canary), and an honest closed-versus-open status.

Then delete `/tmp/fhv1_1_id_v3/` completely. Record post-cleanup `df -h` and `df -k`. Available space must stay `>= 3,145,728` KiB.

Set `TASK-014` to `DONE` in `TASKS.md`. Run:

* every `tools/test_*.py` via `uv run --offline --script` (`>= 150` Python tests, `>= 125` of them `fhv1_1`, `0` failures),
* `cargo fmt --all -- --check`, `cargo clippy --workspace --all-targets -- -D warnings`, `cargo test --workspace` (`173/173`),
* `pnpm --dir frontend lint`, `pnpm --dir frontend test` (`70/70`),
* `git diff --stat <base>..HEAD` and `git diff --name-only 89f1cba..HEAD -- crates/ frontend/ Cargo.toml manifest.json frontend/package.json architecture_spec.md CHANGELOG.md` (the second command must print nothing),
* version `0.2.1` on the three manifests,
* LanceDB `19/19`, `DIFF_IDENTICAL=0`, counts `66 / 4 / 149458 / 24 / 164939`,
* `PORTS_8080_8088_CLOSED`,
* `git log` author/committer on every `TASK-014` commit equals `Héctor Andrés Bauzán Saavedra <hbauzan@gmail.com>` and the messages contain zero `Co-authored-by:`,
* a word-boundary scan of added and modified tracked files for forbidden external helpers, editing tools, and commercial model names (zero hits),
* `agent.sh validate --task-file TASKS.md` and `agent.sh notify --task-file TASKS.md`.

Commit: `chore(fhv1): publish the fhv1_1 v3 full-1024D and lexical guardrail report`

Write untracked `audit_fhv1_1_id_v3_bundle.md` **after** that commit so the bundle can quote the final commit header and body. Include verbatim gate stdout, the Phase-0 summary, the disk table, `git diff --stat`, every `TASK-014` commit header and body, parquet/JSONL counts, and `file:line` citations for `F_dir1024`, `S_struct`, and the nested OOF / `CAL_ONLY` functions. Do not stage the bundle.

Stop. Do not `git push`. Do not `git merge`.

---

## 8. Approval gate

The human reviews `reports/fhv1_1_id_v3_report.md` and `audit_fhv1_1_id_v3_bundle.md`. Integration waits for an explicit `OK`.
