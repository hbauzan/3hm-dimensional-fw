# EXECUTION ROADMAP: `fhv1_1` I+D v2 — DISK AUDIT, 1,000-DOC `1B`, 1,024D FINE DIALS, DOCUMENT-LEVEL CALIBRATION (`TASK-013`)

> **Single Source of Truth**: Self-contained I+D specification for `TASK-013`.  
> **Baseline**: `HEAD @ a89b20dd3fbe429c3bb12669fc0245d43cd63710` on `feat/fhv1-1-xray-offline-replay`.  
> **Branch**: `feat/fhv1-1-id-v2-fine-dials-and-scale` (created from that `HEAD`, not from `main`).  
> **Why not `main`**: `main` is `4536aaa30e521fbf70baac9c84507deef40d34c5`. `git merge-base --is-ancestor a89b20d main` is false and `reports/fhv1_1_xray_and_replay_report.md` is absent on `main`. `TASK-012` exists only on `HEAD`. This fact is intentional and must stay visible in the final report.  
> **Task Governance**: `TASK-013` in [`TASKS.md`](../TASKS.md).  
> **Delivery Fence**: 100% offline I+D. Tracked writes only under `roadmap/`, `TASKS.md`, `tools/`, `reports/`. Untracked writes only under `data/fhv1_1_research/` and `audit_fhv1_1_id_v2_bundle.md`. **ZERO** edits to `crates/`, `frontend/`, `Cargo.toml`, `manifest.json`, `frontend/package.json`, `architecture_spec.md`, `CHANGELOG.md`. Package stays `0.2.1`. **HALT** before `git push` and before `git merge --no-ff`.

---

## 1. Disk Audit #1 (executed before any test or embedding)

### 1.1 Before cleanup (`df`)

Both `/Users/hbauzan/treepwood/3hm-dimentional-fw` and `/tmp` are `/dev/disk3s5` on `/System/Volumes/Data`.

| Metric | Value |
| :--- | :--- |
| `df -h` Size / Used / Avail / Capacity | `460Gi` / `408Gi` / `14Gi` / `97%` |
| `df -k` Available | `14,924,560` KiB (`14.23 GiB`) |

`du -sh` before cleanup:

| Path | Size |
| :--- | :--- |
| `target/` | `22G` |
| `data/` | `3.7G` |
| `data/sf-lancedb/` | `3.7G` |
| `data/fhv1_augmented/` | `516K` |
| `data/fhv1_benchmarks/` | `312K` |
| `data/fhv1_1_research/` | `25M` |
| `frontend/node_modules/` | `239M` |
| `/tmp/fhv1_task011_exports` | `1,466,452 KB` |
| `/tmp/fhv1_1_id` | `16,144 KB` |
| `audit_task011_code.txt` | `736 KB` (untracked) |
| `audit_task011_inspect.txt` | `24 KB` (untracked) |
| `audit_slice8.txt` | `44 KB` (untracked) |
| `audit_task011_evidence.md` | `36 KB` (untracked) |
| `audit_fhv1_1_id_bundle.md` | `36 KB` (untracked, kept) |
| `data/fhv1_1_research/background_embeddings.parquet` | `25M` (kept until Slice 1 verifies the 1k cache) |
| `repomix-output.xml` | absent |

### 1.2 Estimate versus threshold

`TASK-013` peak estimate: `~150–300 MB`. Minimum free-space threshold: `>= 3.0 GiB`. Pre-cleanup avail `14.23 GiB` already cleared the threshold. Cleanup still ran because it was authorized and safe.

### 1.3 Deleted (authorized only)

`88017a9` is an ancestor of `main`, so the four untracked `TASK-011` audit files were removed. `a89b20d` is **not** an ancestor of `main`, so `audit_fhv1_1_id_bundle.md` was kept.

| Deleted path | KiB |
| :--- | ---: |
| `/tmp/fhv1_task011_exports` | 1,466,452 |
| `/tmp/fhv1_1_id` | 16,144 |
| `audit_task011_code.txt` | 736 |
| `audit_task011_inspect.txt` | 24 |
| `audit_slice8.txt` | 44 |
| `audit_task011_evidence.md` | 36 |
| **Sum `du -sk`** | **1,483,436 (`1,448.67 MiB`)** |

Not deleted: `data/sf-lancedb/`, `data/fhv1_augmented/`, `data/fhv1_benchmarks/`, `.env`, `~/.cache/huggingface/`, every git-tracked file, `background_embeddings.parquet`, `audit_fhv1_1_id_bundle.md`, and the small unrelated `/tmp/fhv1_*.log` files (outside the authorized list).

### 1.4 After cleanup

| Metric | Value |
| :--- | :--- |
| `df -h` Size / Used / Avail / Capacity | `460Gi` / `407Gi` / `16Gi` / `97%` |
| `df -k` Available | `16,575,548` KiB (`15.81 GiB`) |
| Available delta vs pre-cleanup | `+1,650,988` KiB |

`df` recovered more KiB than `du -sk` of the deleted paths (`1,650,988` vs `1,483,436`). Both figures are recorded. Avail `15.81 GiB >= 3.0 GiB`, so execution continues unattended.

---

## 2. Ground Truth & Non-Negotiable Invariants

### 2.1 Production freeze and toolchain

* Python: `uv run --offline --script` only (PEP 723). Zero `pip`, zero `npm`, zero `./setup.sh`.
* Non-regression later: `cargo` and `pnpm --dir frontend`. Do not run them in Slices 1–3.
* Sole author `Héctor Andrés Bauzán Saavedra <hbauzan@gmail.com>` (`hbauzan`). Zero coauthor trailers. Zero mentions of external assistants, bots, agent brands, editors, IDEs, or external commercial model brands in any tracked file or commit message.
* Explicit `git add` of named paths. Never `git add -A`. Never stage `.env`, `data/`, `repomix-output.xml`, `audit_*`, `.xlsx`, `.parquet`.
* `HF_HUB_OFFLINE=1`. Loopback `http://127.0.0.1:8080` only. Zero internet. Zero reads of `.env`.
* Numerics in `np.float64`. Scoring of `fhv1_1` uses `normalize=true` and all `1,024` coordinates. Bucket labels are diagnostic metadata. No coordinate is dropped from a score.
* LanceDB `data/sf-lancedb/` is read-only.

### 2.2 Pre-run LanceDB snapshot (read-only, verified this session)

| Table | Rows |
| :--- | ---: |
| `domain_hypercubes` | 66 |
| `fhv1_profiles` | 4 |
| `fhv1_calibration_samples` | 149,458 |
| `fhv1_benchmark_runs` | 24 |
| `fhv1_audit_traces` | 164,939 |

`python-v1-42270ed8870d` / `receta-v1-5c820b9b36b3`: `600` `full_doc` each, `3,579` / `4,066` `clause_opt2c`. The `v2` profiles (`normalize=false`) mirror those row counts. Holdout files: `data/fhv1_benchmarks/python.jsonl` `400` + `receta.jsonl` `400` = **`800` prompts**, **`57` distinct `subtype` keys** (the requested "37" does not match the files; Slice 4 tables every measured key).

`domain_hypercubes.lance` SHA-256 (`19` files, `DIFF` baseline):

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

Ports at preflight: `PORTS_8080_8088_CLOSED`. Tracked worktree was clean. Only untracked file left: `audit_fhv1_1_id_bundle.md`.

### 2.3 Document-bundle join (ground-truth correction)

`fhv1_calibration_samples.source_ref` is the policy id (`python` or `receta`) on every row of that profile. It is **not** a per-document key (`600` python-v1 `full_doc` rows share one `source_ref`). `sample_id` is `{global_index:06}-{strategy_tag}` from `expand_corpus`: each source document is expanded contiguously and begins with `full_doc`.

**Operational bundle key**: sort the profile's `full_doc` and `clause_opt2c` rows by the numeric `sample_id` prefix. Each `full_doc` opens a bundle; following `clause_opt2c` rows belong to it until the next `full_doc`. This matches `assign_calibration_folds` in `tools/fhv1_1_replay_sim.py`. Do not group by the constant `source_ref` string. State this correction in the Slice 4 report.

### 2.4 Separation statistic (reuse)

For coordinate `d`, with population or sample std used consistently inside one function and `eps = 1e-12` (existing `classify_dimensions`):

```text
sep = |mu_T - mu_C| / (sqrt((std_T^2 + std_C^2) / 2) + eps)
snr = |mu| / (std + eps)
```

`Tail-Z` is the exception: `z_d = |x_d - mu_d| / (sigma_d + 1e-9)`.

### 2.5 Current test counts (must not regress)

| Script | `def test_` now | Floor after this task |
| :--- | ---: | ---: |
| `tools/test_fhv1_1_background_corpus.py` | 5 | `>= 12` |
| `tools/test_fhv1_1_xray.py` | 16 | `>= 26` |
| `tools/test_fhv1_1_replay_sim.py` | 7 | `>= 24` |
| `tools/test_bge_m3_mps_server.py` | 13 | 13, still green |
| `tools/test_augment_fhv1_corpus.py` | 11 | 11, still green |
| `tools/test_generate_fhv1_benchmark.py` | 4 | 4, still green |

`fhv1_1` sum floor `>= 62`. Six-script sum floor `>= 90`. Modes `1a`, `embed-bg`, and `1b` stay behavior-compatible for the existing tests. New work is `--mode v2`.

---

## 3. Objective & Scope

Replace the 500-doc same-language background with a 1,000-doc, three-stratum, leak-free `1B`, then label all `1,024` coordinates (language sweet spot, six empirical buckets, polarity-flip dials, hypothesis `2.3`) and replay `fhv1_1` with `Tail-Z`, `F_polarity`, optional language-lock, document-level `CAL_ONLY`, short-query routing, and a `long_context_flooding` closure. Every published row carries `CAL_ONLY` (document-level, `0` holdout), `5×5` repeated stratified OOF (`mean ± std`), bootstrap `95%` CI (`1,000` resamples), `ROC-AUC`, `PR-AUC`, and an explicitly marked `[ORACLE_UPPER_BOUND]` when an in-sample ceiling is shown.

Out of scope: Rust changes, frontend changes, version bump, LanceDB writes, persisting `normalize=false` except the Slice 1–2 temp file, and any push or merge to `main`.

---

## 4. Vertical Slices

### Slice 0 — Architect: disk audit, roadmap, governance

Delivered by this file plus `TASKS.md` (`IN_PROGRESS`, `active_slice: "Slice 1"`). Gate: `agent.sh validate --task-file TASKS.md` and one local commit.

### Slice 1 — Background `1B` at 1,000 docs + `normalize=true` cache

**Tracked**: `tools/fhv1_1_background_corpus.jsonl`, `tools/test_fhv1_1_background_corpus.py`, and the `embed-bg` path in `tools/fhv1_1_xray.py` only as far as needed to emit the new cache.  
**Untracked**: `data/fhv1_1_research/background_embeddings_1k.parquet`, `/tmp/fhv1_1_id_v2/bg_general_unnorm.parquet`.

Corpus contract, exactly `1,000` rows, keys `{id, lang, stratum, topic, text}`:

| Order | `lang` | `stratum` | `n` | `id` |
| :--- | :--- | :--- | ---: | :--- |
| 1 | `en` | `general_prose` | 300 | `bg-en-0001` … `bg-en-0300` |
| 2 | `en` | `technical_structured` | 100 | `bg-en-0301` … `bg-en-0400` |
| 3 | `en` | `near_ood_neighbor` | 100 | `bg-en-0401` … `bg-en-0500` |
| 4 | `es` | `general_prose` | 300 | `bg-es-0001` … `bg-es-0300` |
| 5 | `es` | `technical_structured` | 100 | `bg-es-0301` … `bg-es-0400` |
| 6 | `es` | `near_ood_neighbor` | 100 | `bg-es-0401` … `bg-es-0500` |

`general_prose` topics are the existing 13 (`finance`, `law`, `medicine`, `biology`, `astronomy`, `geology`, `history`, `philosophy`, `architecture`, `music`, `travel_weather`, `sports`, `electronics_hardware`), same set in EN and ES. Twelve topics have `23` docs and `electronics_hardware` has `24`. Each of those topics has at least one short, one medium, and one long doc. Lengths per language: short `60` (`5–15` words, no `\n\n`), medium `180` (`20–65`), long `60` (`80–160`, exactly two paragraphs split by `\n\n`).

`technical_structured` topics, `20` each: `business_json_yaml`, `server_network_logs`, `technical_manuals`, `tables_schemas`, `imperative_instructions`. Lengths: short `20`, medium `50`, long `30` (same word bands). EN has zero Python. ES has zero recipes and zero kitchen procedure.

`near_ood_neighbor` EN, `10` each: `javascript_typescript`, `rust`, `go`, `java`, `cpp`, `csharp`, `sql`, `bash_shell`, `ruby`, `docker_terraform`. Zero Python. Lengths: short `20`, medium `50`, long `30`.

`near_ood_neighbor` ES, `20` each: `nutricion_clinica`, `quimica_alimentos`, `finanzas_restaurante`, `hornos_electricos`, `agronomia_cosecha`. These rows may discuss clinical nutrition, industrial food chemistry, restaurant licensing finance, commercial-oven electrical specs, and agronomy. They must not be cooking recipes. Lengths: short `20`, medium `50`, long `30`.

Purity:

* Every EN row: no Spanish diacritics or Spanish function words (keep the current EN Spanish-leak check).
* Every ES row: no English function-word hits (keep the current ES English-leak check). Loan tokens `JSON`, `YAML`, `kW`, `IEC`, `pH` are allowed. Avoid banned English words such as `hardware`, `software`, `test`, `set`.
* Every EN row rejects a Python-specific denylist: `python`, `pythonic`, `cpython`, `pypi`, `pip`, `venv`, `conda`, `pytest`, `asyncio`, `itertools`, `functools`, `pathlib`, `hashlib`, `pickle`, `dataclass`, `dataclasses`, `numpy`, `scipy`, `pandas`, `matplotlib`, `django`, `flask`, `fastapi`, `uvicorn`, `isinstance`, `traceback`, `gil`, plus `__init__` / `def name(`. Do **not** ban `import`, `yield`, or `lambda` (they occur in the non-Python neighbor languages).
* Every ES row rejects `\brecetas?\b` and `\brecetario\b`.
* `general_prose` and `technical_structured` ES also reject the existing culinary procedure lexicon (kitchen verbs, ingredient lists, cookware). `near_ood_neighbor` ES does not use that broad lexicon ban.

Diversity and firewall (`>= 12` tests):

* Unique normalized prefix of `min(6, n_tokens)` within each language. Pairwise token-set Jaccard `< 0.72` within each language.
* Zero raw equality, zero NFKC-lowercase equality, and zero shared sliding windows of `4` and of `5` tokens against `data/fhv1_benchmarks/*.jsonl`, `tools/fhv1_benchmark_banks.json`, `crates/sf-bench/src/suite2_prompts.json`, `crates/sf-bench/fixtures/fhv1_corpus_*.jsonl`, `data/fhv1_augmented/*.jsonl`, and the quoted strings of `crates/sf-bench/src/canonical_corpus.rs` already harvested by the current test helper.

Embedding:

* Start `HF_HUB_OFFLINE=1 uv run --offline --script tools/bge_m3_mps_server.py` in the background with `trap cleanup EXIT`, poll `http://127.0.0.1:8080/health`, then stop that PID on exit.
* Persist `normalize=true` only: `1,000` `full_doc` plus deduped `clause_opt2c`, into `data/fhv1_1_research/background_embeddings_1k.parquet`. Add a `stratum` column. `write_background_embeddings_parquet` must still accept rows that omit `stratum` (empty string) so the current xray tests stay green.
* Persist `normalize=false` only for the `600` `general_prose` full documents, to `/tmp/fhv1_1_id_v2/bg_general_unnorm.parquet`. Do not put those rows in the 1k file.
* Reload both files. Require finite `float64` vectors of length `1,024`, unit L2 on `normalize=true` (max abs error `<= 1e-3`), and unnormalized L2 `> 1.5`.
* Then delete `data/fhv1_1_research/background_embeddings.parquet` and record its `du -sk`.
* Confirm `PORTS_8080_8088_CLOSED`.

Gate: `uv run --offline --script tools/test_fhv1_1_background_corpus.py` (`>= 12` PASS) and `uv run --offline --script tools/test_fhv1_1_xray.py` still PASS. One local commit. Do not stage parquet or `data/`.

### Slice 2 — X-ray v2: Prueba A, six buckets, hypothesis `2.3`

Extend `tools/fhv1_1_xray.py` with `--mode v2` and raise `tools/test_fhv1_1_xray.py` to `>= 26` tests. Modes `1a` / `1b` / `embed-bg` keep their current bucket names and JSON shape.

`--mode v2` reads `background_embeddings_1k.parquet` plus `/tmp/fhv1_1_id_v2/bg_general_unnorm.parquet` and LanceDB read-only. Write `/tmp/fhv1_1_id_v2/xray_v2.json`, then delete the unnorm parquet in the same process after the JSON is on disk.

**Prueba A** (`300` EN vs `300` ES `general_prose` `full_doc`, all `1,024` dims):

* `sep_lang` on `normalize=true` and, in memory, on `normalize=false`.
* `LOCALE_LANG_DIMS`: `sep_lang >= 1.0` on `normalize=true`. Also record the secondary band `0.65 <= sep_lang < 1.0`.
* Jaccard of the top `{16, 32, 64, 128}` language dims between the two normalizations, mean `sep_lang`, mean SNR ratio, and any dim that ranks in the `normalize=false` top-128 but not the `normalize=true` top-128.
* Top-20 EN-high and top-20 ES-high with signed `float64` and signed `float32` (cast) in both normalizations. Render `+` and `-` explicitly.

**Prueba B** labels every coordinate for `python-v1` and `receta-v1`, `full_doc` and `clause_opt2c`, under `1B_base_tech` (`general_prose + technical_structured`, `400` docs) and `1B_full` (`+ near_ood_neighbor`, `500` docs). Exclusive priority:

1. `BACKBONE_UNIVERSAL` — active on target and contrast (`snr >= 1.5` both), same sign, `sep < 0.75`, and the same sign pattern on EN and ES `general_prose`.
2. `LOCALE_LANG_DIMS` — primary Prueba A set.
3. `POLARITY_FLIP_DIALS` — `mu_T * mu_C < 0` and `sep >= 0.35`. Record strong (`sep >= 1`) and fine (`0.35 <= sep < 1`) with `mean_T`, `std_T`, `mean_C`, `std_C`, `sep`, `sign_consistency_T` (fraction of target rows whose sign matches `sign(mu_T)`; zeros do not count as consistent).
4. `FIRM_DOMAIN_ANCHOR` — not the above, `sep >= 1.0`, and (`snr_T >= 1.0` or `|mu_T| > |mu_C|`).
5. `NEGATIVE_INTRUDER_SENSOR` — quiet near `0` on `T` and active on `C` by the existing mean-shift or variance-energy rule.
6. Else `SUBTLE_DISCRIMINATORS` if `0.35 <= sep < 1.0`, else `LOW_SIGNAL_NOISE`.

Also count how many dims are `LOW_SIGNAL_NOISE` under `1B_base_tech` and leave that bucket under `1B_full` (they "turn on" against `near_ood_neighbor`).

**Hypothesis `2.3`**: `python-v1` `600` `full_doc` vs EN `near_ood_neighbor` `100`, and `receta-v1` `600` `full_doc` vs ES `near_ood_neighbor` `100`. Report counts of `sep >= 1`, `0.5 <= sep < 1`, `0.35 <= sep < 0.5`, median / p90 / max `sep`, polarity-flip count, and top-20 dims per pair.

Gate: xray tests `>= 26` PASS, real `--mode v2 --out /tmp/fhv1_1_id_v2/xray_v2.json`, unnorm parquet absent afterward, one local commit.

### Slice 3 — Offline replay `--mode v2`

Extend `tools/fhv1_1_replay_sim.py` and raise `tools/test_fhv1_1_replay_sim.py` to `>= 24` tests. Existing mode stays green. New experiments use persisted `normalize=true` traces and always all `1,024` dims.

1. Contrast `1B_base_tech` (no hypothesis `2.3`) vs `1B_full` (with `2.3`), plus frozen `TASK-011` / `TASK-012` reference rows from the committed reports (the old `/tmp/fhv1_1_id` JSON was removed in the authorized cleanup). Break out `near_ood_neighbor`, `HYBRID_BOUNDARY`, `ADVERSARIAL_FUZZING`, `IN_DOMAIN_VALID`. Specifically measure whether Rust/SQL/Bash inside `1B_full` moves valid Python prompts whose text mentions `sqlite3`, `subprocess`, or `json`.
2. `Tail-Z`: per chunk, `z_d` on all `1,024` dims, mean of the worst `P` in `{1, 3, 5, 10, 25}`, map to `(0, 1]` with an OOF `q90` scale fit on calibration only (`S_tail_P`). Report alone and combined with `F1 + F2_L2 + F3`.
3. `F_polarity`: fraction of `POLARITY_FLIP_DIALS` (`sep >= 0.35`, opposite signs) that keep the domain sign, times the normalized margin on the correct side of zero. Alone and combined. Break out `near_ood_neighbor` and `HYBRID_BOUNDARY`.
4. Language-lock, optional: (i) drop `LOCALE_LANG_DIMS` from the positive `F3` bonus only; (ii) add a monolingual consistency check on those dims. Off must be neutral.
5. `3.1` Document-level `CAL_ONLY`: one bundle per calibration `full_doc` plus its interval `clause_opt2c` (§2.3). `5`-fold OOF grouped on the `600` bundles. Percentiles `p05`, `p10`, `p15` of the document-level statistics `blend_full_min_clause`, `p10_clause_min_full`, `hard_kill`, and `dual_zone`. Show whether document-level `CAL_ONLY` FRR stops sitting in the `47–60%` chunk-level band and lines up with OOF. Thresholds never see holdout.
6. `3.2` Short-query route: if `word_count <= L` or `num_clauses == 1`, score with `clause_opt2c`. Sweep `L ∈ {0, 8, 12, 16, 20}` on `full_only` and `clauses`. Report FRR on `short_idiom_query` (`n=20`) and `consulta_corta` (`n=20`), FAR on `extreme_short_punct` (`n=10`), and global `ΔF1`.
7. `3.3` `long_context_flooding` on `python/clauses`: replace the `max_gray_frac = 0.35` cap with absolute `max_gray_count ∈ {0, 1, 2}`, `blend_full_min_clause` at `w_f ∈ {0.3, 0.5, 0.7}`, and `hard_kill`. Report measured FAR (the `66.7% → 0%` figure is a hypothesis, not a constant to print) and keep informative `cap=24` (`8+8+8`, Base64 fail-closed).
8. `5×5` repeated stratified OOF (seeds `0..4`, `5` folds): `mean ± std` of OOF `F1`, `FRR`, `FAR`, `ROC-AUC`, `PR-AUC`. Bootstrap `95%` CI, `1,000` stratified resamples, for the best candidates and for paired `ΔF1` against the frozen `TASK-012` and `TASK-011` rows. Full subtype table: `TASK-011` vs `TASK-012` vs best `TASK-013`, both document-level `CAL_ONLY` and repeated OOF.

Required tests: one fired dim among `1,024` is detected and `S_tail_P` is monotone in `P`; a sign flip is penalized and the domain sign is rewarded; language-lock sees an EN↔ES flip and is neutral when off; bundle folds do not split a `full_doc` from its interval clauses; short-query boundaries `L-1`, `L`, `L+1` plus `extreme_short_punct` and Base64 fail-closed stay closed; a synthetic `long_context_flooding` case (`1` poisoned clause among `40` clean ones) is blocked by `max_gray_count <= 1` and by `blend_full_min_clause`; bootstrap and `5×5` repeats are bit-stable in `float64` for a fixed seed and do not leak a fold.

Gate: replay tests `>= 24` PASS, real `--mode v2 --out /tmp/fhv1_1_id_v2/replay_v2.json`, one local commit. Sum of the three `fhv1_1` suites `>= 62`.

### Slice 4 — Report, gates, cleanup, approval halt

Tracked: `reports/fhv1_1_id_v2_report.md`, `TASKS.md` (`DONE`). Untracked: `audit_fhv1_1_id_v2_bundle.md`.

Report sections, in order: disk audit (this file's numbers plus Slice 1 parquet deletion and final `df`); Prueba A with signed top-20; Prueba B six buckets plus top-20 polarity flips and subtle discriminators; hypothesis `2.3` and `1B_base_tech` vs `1B_full`; `Tail-Z` / `F_polarity` / language-lock ablations; the three fixes; master tables with repeated OOF `mean ± std`, bootstrap `95%` CI, document-level `CAL_ONLY`, and `[ORACLE_UPPER_BOUND]`; subtype table against `TASK-011` and `TASK-012`; objective I+D status (what closed, what ceiling remains on Python vs Receta, what stays open). No Rust edits and no version bump.

Then:

1. `uv run --offline --script` on the six Python suites. Floors: `>= 90` tests, `>= 62` of them `fhv1_1`, `0` failures.
2. `cargo fmt --all -- --check && cargo clippy --workspace --all-targets -- -D warnings && cargo test --workspace` (baseline `173` tests; record the actual count; `0` failures).
3. `pnpm --dir frontend lint && pnpm --dir frontend test` (baseline `70`; record the actual count; `0` failures).
4. `git diff --name-only a89b20dd3fbe429c3bb12669fc0245d43cd63710..HEAD -- crates/ frontend/ Cargo.toml manifest.json frontend/package.json architecture_spec.md CHANGELOG.md` empty. Version `0.2.1` unchanged.
5. LanceDB: the `19` SHA-256 digests identical (`DIFF_IDENTICAL=0`) and the five row counts unchanged.
6. `PORTS_8080_8088_CLOSED`. Author `hbauzan <hbauzan@gmail.com>` on every `TASK-013` commit. Zero coauthor trailers. Zero forbidden lexical mentions. Zero forbidden paths staged.

Delete `/tmp/fhv1_1_id_v2/` only after the report contains the numbers those JSON files carried. Record final `df -h`. Run `agent.sh validate` and `agent.sh notify`. One local Slice 4 commit. Write `audit_fhv1_1_id_v2_bundle.md` with `git log`, `git status`, the disk audit, and the literal gate stdout. **Stop. Do not push. Do not merge.**

---

## 5. Definition of Done

- [x] Disk audit recorded and free space `>= 3.0 GiB` after authorized cleanup.
- [ ] Slice 1 corpus, tests, 1k cache, old parquet removed, ports closed, local commit.
- [ ] Slice 2 `--mode v2` JSON, unnorm parquet deleted, `>= 26` xray tests, local commit.
- [ ] Slice 3 `--mode v2` replay JSON, `>= 24` replay tests, `>= 62` `fhv1_1` tests, local commit.
- [ ] Slice 4 report, full gates, LanceDB unchanged, `TASKS.md` `DONE`, untracked audit bundle, human approval halt.
