# `fhv1_1` I+D v4 — hardening, dual-axis, `clause_cap`, `N_cal` curve

**Task**: `TASK-015`
**Branch**: `feat/fhv1-1-id-v4-hardening-and-sample-curve`
**Dtype**: `float64`. **normalize**: `true`. **mode**: `v4`.

Numbers in the tables are literals copied from `/tmp/fhv1_1_id_v4` JSON. A missing key aborts the generator.

## 0. Executive

Lineage: `TASK-011` (hardening/falsification) → `TASK-012` (replay) → `TASK-013` (fine dials) → `TASK-014` (v3 full-1024D + lexical guard) → `TASK-015` (v4 hardening, Eje 2, `clause_cap`, `N_cal` curve).
Blind frozen recipe on every dual-axis cell (`eje1_plus_struct|b=0.10`) is scored under 5-fold cal OOF (`cal_oof_folds` `5`). Eje 1 preset `1B_base_tech`. Eje 2 stratum `near_ood_neighbor`. `normalize` `true`. `dtype` `float64`. dim `1024`.
Bootstrap contract on manifest and cells: resamples `1000`, seed `0`, `refits_thresholds` `true`. Each dual-axis cell stores CAL_ONLY, blind frozen CI95 / paired `delta_f1`, diagnostic 5×5 OOF, and `[ORACLE_UPPER_BOUND]`.
Upper-bound rows stay labeled `[ORACLE_UPPER_BOUND]` on the frozen holdout scores and sit outside the executive F1 column.
| domain | granularity | family | frozen recipe | CAL_ONLY p10 F1 | bootstrap CI95 | 5x5 F1 mean | 5x5 F1 std | ROC-AUC | OOD FAR | adversarial FAR | hybrid FAR | near-OOD FAR | S_struct p50 us | S_struct p99 us |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `python` | `full_only` | `eje1_plus_struct` | `eje1_plus_struct|b=0.10|l=-|n=-|w=-` | `0.7022222222222222` | [`0.6548632882257233`, `0.759825327510917`] | `0.7189992166038128` | `0.002795922874350561` | `0.9162999999999999` | `0.0` | `0.12` | `0.34` | `0.5833333333333334` | `25.875` | `282.70302999999956` |
| `python` | `clauses` | `eje1_plus_struct` | `eje1_plus_struct|b=0.10|l=-|n=-|w=0.35` | `0.7522123893805309` | [`0.7029176320066391`, `0.7943957239790039`] | `0.7223124702809092` | `0.02047752362858949` | `0.9080666666666666` | `0.03` | `0.18` | `0.2` | `0.75` | `25.9585` | `267.91496999999936` |
| `receta` | `full_only` | `eje1_plus_struct` | `eje1_plus_struct|b=0.10|l=-|n=-|w=-` | `0.6519337016574586` | [`0.5833333333333334`, `0.7252747252747253`] | `0.774468085106383` | `0.0` | `0.926` | `0.0` | `0.0` | `0.22` | `0.0` | `27.333` | `260.5083000000014` |
| `receta` | `clauses` | `eje1_plus_struct` | `eje1_plus_struct|b=0.10|l=-|n=-|w=0.35` | `0.8361581920903954` | [`0.7784431137724551`, `0.8865168376933084`] | `0.8735604658106897` | `0.009372749191703517` | `0.9830333333333334` | `0.0` | `0.0` | `0.03` | `0.0` | `27.083` | `258.5766000000005` |
What improved / remains open (literals only):
- `python`/`full_only`: frozen `eje1_plus_struct|b=0.10|l=-|n=-|w=-` CAL_ONLY p10 F1 `0.7022222222222222` is above the best stored dual-axis gate F1 `0.6755555555555556` (`near_tag` `p10`).
- Paired `p02` F1 `0.6666666666666666` is below the headline.
- `python`/`clauses`: frozen `eje1_plus_struct|b=0.10|l=-|n=-|w=0.35` CAL_ONLY p10 F1 `0.7522123893805309` is above the best stored dual-axis gate F1 `0.7288888888888889` (`near_tag` `p10`).
- Paired `p02` F1 `0.7203389830508474` is below the headline.
- `receta`/`full_only`: frozen `eje1_plus_struct|b=0.10|l=-|n=-|w=-` CAL_ONLY p10 F1 `0.6519337016574586` is above the best stored dual-axis gate F1 `0.6263736263736264` (`near_tag` `p02`).
- Paired `p02` F1 `0.6263736263736264` is below the headline.
- `receta`/`clauses`: frozen `eje1_plus_struct|b=0.10|l=-|n=-|w=0.35` CAL_ONLY p10 F1 `0.8361581920903954` is below the best stored dual-axis gate F1 `0.850828729281768` (`near_tag` `p02`).
- Paired `p02` F1 `0.850828729281768` is above the headline.
Open: python near-OOD FAR remains away from zero; receta/full_only CAL_ONLY is below the published v3 `1B_base_tech` headline after honest 5-fold cal OOF; production scorer stays OFF.

## 1. Phase-0 and disk

Phase-0 below is quoted from `roadmap/fhv1-1-id-v4-hardening-and-sample-curve.roadmap.md` section 1. It is the audit that already ran. This generator does not replace those figures with a second audit.

```text
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
```

### Disk before scratch removal

```text
# repo /Users/hbauzan/treepwood/3hm-dimentional-fw
Filesystem      Size    Used   Avail Capacity iused ifree %iused  Mounted on
/dev/disk3s5   460Gi   408Gi    15Gi    97%    3.0M  157M    2%   /System/Volumes/Data
Filesystem   1024-blocks      Used Available Capacity iused     ifree %iused  Mounted on
/dev/disk3s5   482797652 427298252  15728076    97% 3004744 157280760    2%   /System/Volumes/Data
available_kib 15728076

# tmp /tmp
Filesystem      Size    Used   Avail Capacity iused ifree %iused  Mounted on
/dev/disk3s5   460Gi   408Gi    15Gi    97%    3.0M  157M    2%   /System/Volumes/Data
Filesystem   1024-blocks      Used Available Capacity iused     ifree %iused  Mounted on
/dev/disk3s5   482797652 427298252  15728076    97% 3004744 157280760    2%   /System/Volumes/Data
available_kib 15728076
```

### Closing disk measurement (post `/tmp/fhv1_1_id_v4/` cleanup)

```text
# repo /Users/hbauzan/treepwood/3hm-dimentional-fw
Filesystem      Size    Used   Avail Capacity iused ifree %iused  Mounted on
/dev/disk3s5   460Gi   408Gi    15Gi    97%    3.0M  157M    2%   /System/Volumes/Data
Filesystem   1024-blocks      Used Available Capacity iused     ifree %iused  Mounted on
/dev/disk3s5   482797652 427297844  15728484    97% 3004731 157284840    2%   /System/Volumes/Data
available_kib 15728484

# tmp /tmp
Filesystem      Size    Used   Avail Capacity iused ifree %iused  Mounted on
/dev/disk3s5   460Gi   408Gi    15Gi    97%    3.0M  157M    2%   /System/Volumes/Data
Filesystem   1024-blocks      Used Available Capacity iused     ifree %iused  Mounted on
/dev/disk3s5   482797652 427297844  15728484    97% 3004731 157284840    2%   /System/Volumes/Data
available_kib 15728484
```

Floor is 3145728 KiB. The closing `df -k` Available field is the measurement that has to clear that floor.

## 2. Impact of the three `S_struct` fixes (v3 vs v4)

Comparison uses published v3 `1B_base_tech` literals from `reports/fhv1_1_id_v3_report.md` against v4 dual-axis cells (Eje 1 preset `1B_base_tech`). `IN_DOMAIN_VALID` reports FRR and `ADVERSARIAL_FUZZING` reports FAR as separate rows.
| domain | granularity | row | v4 kind | v4 rate | v3 kind | v3 rate |
| --- | --- | --- | --- | --- | --- | --- |
| `python` | `full_only` | `IN_DOMAIN_VALID` | `frr` | `0.21` | `frr` | `0.21` |
| `python` | `full_only` | `ADVERSARIAL_FUZZING` | `far` | `0.12` | `far` | `0.11` |
| `python` | `full_only` | `consulta_corta` | `absent` | `absent` | `absent` | `absent` |
| `python` | `full_only` | `sustitucion_ingredientes` | `absent` | `absent` | `absent` | `absent` |
| `python` | `full_only` | `panaderia_fermentacion` | `absent` | `absent` | `absent` | `absent` |
| `python` | `full_only` | `diagnostico_pasteleria_panaderia` | `absent` | `absent` | `absent` | `absent` |
| `python` | `full_only` | `short_idiom_query` | `frr` | `0.5` | `frr` | `0.5` |
| `python` | `full_only` | `code_snippet` | `frr` | `0.3333333333333333` | `frr` | `0.3333333333333333` |
| `python` | `full_only` | `extreme_short_punct` | `far` | `0.0` | `far` | `0.0` |
| `python` | `full_only` | `homoglyph_zwsp_fullwidth` | `far` | `0.0` | `far` | `0.0` |
| `python` | `full_only` | `long_context_flooding` | `far` | `0.16666666666666666` | `far` | `0.16666666666666666` |
| `python` | `full_only` | `prompt_injection_jailbreak` | `far` | `0.28` | `far` | `0.28` |
| `python` | `clauses` | `IN_DOMAIN_VALID` | `frr` | `0.15` | `frr` | `0.18` |
| `python` | `clauses` | `ADVERSARIAL_FUZZING` | `far` | `0.18` | `far` | `0.09` |
| `python` | `clauses` | `consulta_corta` | `absent` | `absent` | `absent` | `absent` |
| `python` | `clauses` | `sustitucion_ingredientes` | `absent` | `absent` | `absent` | `absent` |
| `python` | `clauses` | `panaderia_fermentacion` | `absent` | `absent` | `absent` | `absent` |
| `python` | `clauses` | `diagnostico_pasteleria_panaderia` | `absent` | `absent` | `absent` | `absent` |
| `python` | `clauses` | `short_idiom_query` | `frr` | `0.05` | `frr` | `0.25` |
| `python` | `clauses` | `code_snippet` | `frr` | `1.0` | `frr` | `0.5` |
| `python` | `clauses` | `extreme_short_punct` | `far` | `0.0` | `far` | `0.0` |
| `python` | `clauses` | `homoglyph_zwsp_fullwidth` | `far` | `0.0` | `far` | `0.0` |
| `python` | `clauses` | `long_context_flooding` | `far` | `0.0` | `far` | `0.0` |
| `python` | `clauses` | `prompt_injection_jailbreak` | `far` | `0.32` | `far` | `0.28` |
| `receta` | `full_only` | `IN_DOMAIN_VALID` | `frr` | `0.41` | `frr` | `0.23` |
| `receta` | `full_only` | `ADVERSARIAL_FUZZING` | `far` | `0.0` | `far` | `0.01` |
| `receta` | `full_only` | `consulta_corta` | `frr` | `0.65` | `frr` | `0.35` |
| `receta` | `full_only` | `sustitucion_ingredientes` | `frr` | `0.25` | `frr` | `0.25` |
| `receta` | `full_only` | `panaderia_fermentacion` | `frr` | `0.7` | `frr` | `0.6` |
| `receta` | `full_only` | `diagnostico_pasteleria_panaderia` | `frr` | `0.25` | `frr` | `0.125` |
| `receta` | `full_only` | `short_idiom_query` | `absent` | `absent` | `absent` | `absent` |
| `receta` | `full_only` | `code_snippet` | `absent` | `absent` | `absent` | `absent` |
| `receta` | `full_only` | `extreme_short_punct` | `far` | `0.0` | `far` | `0.0` |
| `receta` | `full_only` | `homoglyph_zwsp_fullwidth` | `far` | `0.0` | `far` | `0.08333333333333333` |
| `receta` | `full_only` | `long_context_flooding` | `far` | `0.0` | `far` | `0.0` |
| `receta` | `full_only` | `prompt_injection_jailbreak` | `far` | `0.0` | `far` | `0.0` |
| `receta` | `clauses` | `IN_DOMAIN_VALID` | `frr` | `0.26` | `frr` | `0.17` |
| `receta` | `clauses` | `ADVERSARIAL_FUZZING` | `far` | `0.0` | `far` | `0.01` |
| `receta` | `clauses` | `consulta_corta` | `frr` | `0.2` | `frr` | `0.1` |
| `receta` | `clauses` | `sustitucion_ingredientes` | `frr` | `0.375` | `frr` | `0.125` |
| `receta` | `clauses` | `panaderia_fermentacion` | `frr` | `0.6` | `frr` | `0.3` |
| `receta` | `clauses` | `diagnostico_pasteleria_panaderia` | `frr` | `0.5` | `frr` | `0.5` |
| `receta` | `clauses` | `short_idiom_query` | `absent` | `absent` | `absent` | `absent` |
| `receta` | `clauses` | `code_snippet` | `absent` | `absent` | `absent` | `absent` |
| `receta` | `clauses` | `extreme_short_punct` | `far` | `0.0` | `far` | `0.1` |
| `receta` | `clauses` | `homoglyph_zwsp_fullwidth` | `far` | `0.0` | `far` | `0.0` |
| `receta` | `clauses` | `long_context_flooding` | `far` | `0.0` | `far` | `0.0` |
| `receta` | `clauses` | `prompt_injection_jailbreak` | `far` | `0.0` | `far` | `0.0` |
### Structural penalty beta comparison (`eje1_only` beta=0 vs `eje1_plus_struct` beta=0.10, 0.20)
| domain | granularity | recipe | beta | F1 | ROC-AUC | IN_DOMAIN_VALID FRR | OOD FAR | Adv FAR | Hybrid FAR | code_snippet | short_idiom_query | delimiter_escape | keyword_stuffing_hidden_instruction | near_ood_neighbor |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `python` | `full_only` | `eje1_only|b=0.00|l=-|n=-|w=-` | `0.0` | `0.6837606837606838` | `0.9022333333333333` | `0.2` | `0.0` | `0.21` | `0.33` | `0.3333333333333333` (`frr`) | `0.45` (`frr`) | `0.5` (`far`) | `0.3333333333333333` (`far`) | `0.5833333333333334` (`far`) |
| `python` | `full_only` | `eje1_plus_struct|b=0.10|l=-|n=-|w=-` | `0.1` | `0.7022222222222222` | `0.9162999999999999` | `0.21` | `0.0` | `0.12` | `0.34` | `0.3333333333333333` (`frr`) | `0.5` (`frr`) | `0.16666666666666666` (`far`) | `0.3333333333333333` (`far`) | `0.5833333333333334` (`far`) |
| `python` | `full_only` | `eje1_plus_struct|b=0.20|l=-|n=-|w=-` | `0.2` | `0.6960352422907489` | `0.9163333333333333` | `0.21` | `0.0` | `0.12` | `0.36` | `0.3333333333333333` (`frr`) | `0.5` (`frr`) | `0.16666666666666666` (`far`) | `0.3333333333333333` (`far`) | `0.6666666666666666` (`far`) |
| `python` | `clauses` | `eje1_only|b=0.00|l=-|n=-|w=0.35` | `0.0` | `0.7125506072874493` | `0.9184333333333333` | `0.12` | `0.03` | `0.38` | `0.18` | `0.3333333333333333` (`frr`) | `0.05` (`frr`) | `0.6666666666666666` (`far`) | `0.5` (`far`) | `0.75` (`far`) |
| `python` | `clauses` | `eje1_plus_struct|b=0.10|l=-|n=-|w=0.35` | `0.1` | `0.7522123893805309` | `0.9080666666666666` | `0.15` | `0.03` | `0.18` | `0.2` | `1.0` (`frr`) | `0.05` (`frr`) | `0.3333333333333333` (`far`) | `0.5` (`far`) | `0.75` (`far`) |
| `python` | `clauses` | `eje1_plus_struct|b=0.20|l=-|n=-|w=0.35` | `0.2` | `0.7012987012987013` | `0.8702666666666667` | `0.19` | `0.03` | `0.22` | `0.25` | `1.0` (`frr`) | `0.05` (`frr`) | `0.3333333333333333` (`far`) | `0.5` (`far`) | `0.8333333333333334` (`far`) |
| `receta` | `full_only` | `eje1_only|b=0.00|l=-|n=-|w=-` | `0.0` | `0.6413043478260869` | `0.9183333333333334` | `0.41` | `0.0` | `0.0` | `0.25` | `null` (`null`) | `null` (`null`) | `0.0` (`far`) | `0.0` (`far`) | `0.0` (`far`) |
| `receta` | `full_only` | `eje1_plus_struct|b=0.10|l=-|n=-|w=-` | `0.1` | `0.6519337016574586` | `0.926` | `0.41` | `0.0` | `0.0` | `0.22` | `null` (`null`) | `null` (`null`) | `0.0` (`far`) | `0.0` (`far`) | `0.0` (`far`) |
| `receta` | `full_only` | `eje1_plus_struct|b=0.20|l=-|n=-|w=-` | `0.2` | `0.6629834254143646` | `0.9286666666666666` | `0.4` | `0.0` | `0.0` | `0.21` | `null` (`null`) | `null` (`null`) | `0.0` (`far`) | `0.0` (`far`) | `0.0` (`far`) |
| `receta` | `clauses` | `eje1_only|b=0.00|l=-|n=-|w=0.35` | `0.0` | `0.8571428571428571` | `0.9805` | `0.22` | `0.0` | `0.0` | `0.04` | `null` (`null`) | `null` (`null`) | `0.0` (`far`) | `0.0` (`far`) | `0.0` (`far`) |
| `receta` | `clauses` | `eje1_plus_struct|b=0.10|l=-|n=-|w=0.35` | `0.1` | `0.8361581920903954` | `0.9830333333333334` | `0.26` | `0.0` | `0.0` | `0.03` | `null` (`null`) | `null` (`null`) | `0.0` (`far`) | `0.0` (`far`) | `0.0` (`far`) |
| `receta` | `clauses` | `eje1_plus_struct|b=0.20|l=-|n=-|w=0.35` | `0.2` | `0.8160919540229885` | `0.9769666666666668` | `0.29` | `0.0` | `0.0` | `0.03` | `null` (`null`) | `null` (`null`) | `0.0` (`far`) | `0.0` (`far`) | `0.0` (`far`) |
The three Slice-1 repairs (unidirectional channels, Latin letters out of `symbol_ratio`, rare-rate smoothing) are the v4 lexical path. Friendly-fire subtypes that remain high FRR after OOF thresholds are called out as open, not as a silent gain.

## 3. Ablation Eje 1 vs Eje 2 and 5-fold cal OOF

Blind primary selection freezes `eje1_plus_struct|b=0.10` under 5-fold cal OOF. All 12 catalog recipes (with true 2D AND thresholds for `dual_axis_and`) and `eje1_only` vs `eje1_plus_struct` beta comparison appear below; `nested_oof` is diagnostic only.
### python / full_only
Frozen `eje1_plus_struct|b=0.10|l=-|n=-|w=-` family `eje1_plus_struct` beta `0.1` w_f `null`. selection_policy `blind_apriori_eje1_plus_struct_b010`. frozen_column `1`. nested_modal_column `1`. CAL_ONLY p10 F1 `0.7022222222222222`. 5x5 F1 mean `0.7189992166038128` std `0.002795922874350561`.
| recipe | family | frozen | F1 | ROC-AUC | IN_DOMAIN_VALID FRR | OOD FAR | Adv FAR | Hybrid FAR | near_ood_neighbor FAR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `eje1_only|b=0.00|l=-|n=-|w=-` | `eje1_only` | `false` | `0.6837606837606838` | `0.9022333333333333` | `0.2` | `0.0` | `0.21` | `0.33` | `0.5833333333333334` |
| `eje1_plus_struct|b=0.10|l=-|n=-|w=-` | `eje1_plus_struct` | `true` | `0.7022222222222222` | `0.9162999999999999` | `0.21` | `0.0` | `0.12` | `0.34` | `0.5833333333333334` |
| `eje1_plus_struct|b=0.20|l=-|n=-|w=-` | `eje1_plus_struct` | `false` | `0.6960352422907489` | `0.9163333333333333` | `0.21` | `0.0` | `0.12` | `0.36` | `0.6666666666666666` |
| `dual_axis_and|b=0.00|l=-|n=p02|w=-` | `dual_axis_and` | `false` | `0.6666666666666666` | `0.8785333333333333` | `0.23` | `0.0` | `0.21` | `0.33` | `0.5833333333333334` |
| `dual_axis_and|b=0.00|l=-|n=p05|w=-` | `dual_axis_and` | `false` | `0.6724890829694323` | `0.8785333333333333` | `0.23` | `0.0` | `0.21` | `0.31` | `0.5833333333333334` |
| `dual_axis_and|b=0.00|l=-|n=p10|w=-` | `dual_axis_and` | `false` | `0.6755555555555556` | `0.8785333333333333` | `0.24` | `0.0` | `0.19` | `0.3` | `0.5833333333333334` |
| `dual_axis_blend|b=0.00|l=0.20|n=-|w=-` | `dual_axis_blend` | `false` | `0.6639344262295082` | `0.8979666666666667` | `0.19` | `0.0` | `0.23` | `0.4` | `0.5833333333333334` |
| `dual_axis_blend|b=0.15|l=0.20|n=-|w=-` | `dual_axis_blend` | `false` | `0.6861924686192469` | `0.9099666666666667` | `0.18` | `0.0` | `0.13` | `0.44` | `0.5833333333333334` |
| `dual_axis_blend|b=0.00|l=0.35|n=-|w=-` | `dual_axis_blend` | `false` | `0.6412213740458015` | `0.8904666666666666` | `0.16` | `0.0` | `0.27` | `0.51` | `0.6666666666666666` |
| `dual_axis_blend|b=0.15|l=0.35|n=-|w=-` | `dual_axis_blend` | `false` | `0.6561264822134387` | `0.9017333333333333` | `0.17` | `0.0` | `0.16` | `0.54` | `0.6666666666666666` |
| `dual_axis_min|b=0.00|l=-|n=-|w=-` | `dual_axis_min` | `false` | `0.6390977443609023` | `0.8785333333333333` | `0.15` | `0.0` | `0.3` | `0.51` | `0.6666666666666666` |
| `dual_axis_min|b=0.15|l=-|n=-|w=-` | `dual_axis_min` | `false` | `0.6615384615384615` | `0.8930333333333333` | `0.14` | `0.0` | `0.18` | `0.56` | `0.75` |
- Eje2 gate `near_tag` `p02` F1 `0.6666666666666666` (`IN_DOMAIN_VALID FRR` `0.23`, `near_ood_neighbor FAR` `0.5833333333333334`) is below the frozen CAL_ONLY p10 `0.7022222222222222`.
- Eje2 gate `near_tag` `p05` F1 `0.6724890829694323` (`IN_DOMAIN_VALID FRR` `0.23`, `near_ood_neighbor FAR` `0.5833333333333334`) is below the frozen CAL_ONLY p10 `0.7022222222222222`.
- Eje2 gate `near_tag` `p10` F1 `0.6755555555555556` (`IN_DOMAIN_VALID FRR` `0.24`, `near_ood_neighbor FAR` `0.5833333333333334`) is below the frozen CAL_ONLY p10 `0.7022222222222222`.
### python / clauses
Frozen `eje1_plus_struct|b=0.10|l=-|n=-|w=0.35` family `eje1_plus_struct` beta `0.1` w_f `0.35`. selection_policy `blind_apriori_eje1_plus_struct_b010`. frozen_column `1`. nested_modal_column `9`. CAL_ONLY p10 F1 `0.7522123893805309`. 5x5 F1 mean `0.7223124702809092` std `0.02047752362858949`.
| recipe | family | frozen | F1 | ROC-AUC | IN_DOMAIN_VALID FRR | OOD FAR | Adv FAR | Hybrid FAR | near_ood_neighbor FAR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `eje1_only|b=0.00|l=-|n=-|w=0.35` | `eje1_only` | `false` | `0.7125506072874493` | `0.9184333333333333` | `0.12` | `0.03` | `0.38` | `0.18` | `0.75` |
| `eje1_plus_struct|b=0.10|l=-|n=-|w=0.35` | `eje1_plus_struct` | `true` | `0.7522123893805309` | `0.9080666666666666` | `0.15` | `0.03` | `0.18` | `0.2` | `0.75` |
| `eje1_plus_struct|b=0.20|l=-|n=-|w=0.35` | `eje1_plus_struct` | `false` | `0.7012987012987013` | `0.8702666666666667` | `0.19` | `0.03` | `0.22` | `0.25` | `0.8333333333333334` |
| `dual_axis_and|b=0.00|l=-|n=p02|w=0.35` | `dual_axis_and` | `false` | `0.7203389830508474` | `0.8982333333333333` | `0.15` | `0.02` | `0.33` | `0.16` | `0.75` |
| `dual_axis_and|b=0.00|l=-|n=p05|w=0.35` | `dual_axis_and` | `false` | `0.7272727272727273` | `0.8982333333333333` | `0.16` | `0.02` | `0.3` | `0.15` | `0.6666666666666666` |
| `dual_axis_and|b=0.00|l=-|n=p10|w=0.35` | `dual_axis_and` | `false` | `0.7288888888888889` | `0.8982333333333333` | `0.18` | `0.02` | `0.27` | `0.14` | `0.6666666666666666` |
| `dual_axis_blend|b=0.00|l=0.20|n=-|w=0.35` | `dual_axis_blend` | `false` | `0.7241379310344828` | `0.9209666666666667` | `0.16` | `0.01` | `0.3` | `0.17` | `0.8333333333333334` |
| `dual_axis_blend|b=0.15|l=0.20|n=-|w=0.35` | `dual_axis_blend` | `false` | `0.6854838709677419` | `0.8742333333333334` | `0.15` | `0.05` | `0.2` | `0.38` | `0.9166666666666666` |
| `dual_axis_blend|b=0.00|l=0.35|n=-|w=0.35` | `dual_axis_blend` | `false` | `0.7107438016528925` | `0.9100666666666667` | `0.14` | `0.03` | `0.29` | `0.24` | `0.75` |
| `dual_axis_blend|b=0.15|l=0.35|n=-|w=0.35` | `dual_axis_blend` | `false` | `0.6509803921568628` | `0.8617666666666666` | `0.17` | `0.07` | `0.2` | `0.45` | `0.9166666666666666` |
| `dual_axis_min|b=0.00|l=-|n=-|w=0.35` | `dual_axis_min` | `false` | `0.7114624505928854` | `0.8982333333333333` | `0.1` | `0.04` | `0.34` | `0.25` | `0.8333333333333334` |
| `dual_axis_min|b=0.15|l=-|n=-|w=0.35` | `dual_axis_min` | `false` | `0.6492537313432836` | `0.8677333333333334` | `0.13` | `0.08` | `0.2` | `0.53` | `0.8333333333333334` |
Diagnostic `w_f` sensitivity (`{0.20, 0.35, 0.50}`, outside primary catalog):
| w_f | recipe | F1 | ROC-AUC | IN_DOMAIN_VALID FRR | OOD FAR | Adv FAR | Hybrid FAR | near_ood_neighbor FAR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `0.2` | `eje1_plus_struct|b=0.10|l=-|n=-|w=0.20` | `0.6885245901639344` | `0.8888` | `0.16` | `0.07` | `0.29` | `0.24` | `0.9166666666666666` |
| `0.35` | `eje1_plus_struct|b=0.10|l=-|n=-|w=0.35` | `0.7522123893805309` | `0.9080666666666666` | `0.15` | `0.03` | `0.18` | `0.2` | `0.75` |
| `0.5` | `eje1_plus_struct|b=0.10|l=-|n=-|w=0.50` | `0.7488151658767772` | `0.9171666666666667` | `0.21` | `0.01` | `0.13` | `0.18` | `0.6666666666666666` |
- Eje2 gate `near_tag` `p02` F1 `0.7203389830508474` (`IN_DOMAIN_VALID FRR` `0.15`, `near_ood_neighbor FAR` `0.75`) is below the frozen CAL_ONLY p10 `0.7522123893805309`.
- Eje2 gate `near_tag` `p05` F1 `0.7272727272727273` (`IN_DOMAIN_VALID FRR` `0.16`, `near_ood_neighbor FAR` `0.6666666666666666`) is below the frozen CAL_ONLY p10 `0.7522123893805309`.
- Eje2 gate `near_tag` `p10` F1 `0.7288888888888889` (`IN_DOMAIN_VALID FRR` `0.18`, `near_ood_neighbor FAR` `0.6666666666666666`) is below the frozen CAL_ONLY p10 `0.7522123893805309`.
### receta / full_only
Frozen `eje1_plus_struct|b=0.10|l=-|n=-|w=-` family `eje1_plus_struct` beta `0.1` w_f `null`. selection_policy `blind_apriori_eje1_plus_struct_b010`. frozen_column `1`. nested_modal_column `2`. CAL_ONLY p10 F1 `0.6519337016574586`. 5x5 F1 mean `0.774468085106383` std `0.0`.
| recipe | family | frozen | F1 | ROC-AUC | IN_DOMAIN_VALID FRR | OOD FAR | Adv FAR | Hybrid FAR | near_ood_neighbor FAR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `eje1_only|b=0.00|l=-|n=-|w=-` | `eje1_only` | `false` | `0.6413043478260869` | `0.9183333333333334` | `0.41` | `0.0` | `0.0` | `0.25` | `0.0` |
| `eje1_plus_struct|b=0.10|l=-|n=-|w=-` | `eje1_plus_struct` | `true` | `0.6519337016574586` | `0.926` | `0.41` | `0.0` | `0.0` | `0.22` | `0.0` |
| `eje1_plus_struct|b=0.20|l=-|n=-|w=-` | `eje1_plus_struct` | `false` | `0.6629834254143646` | `0.9286666666666666` | `0.4` | `0.0` | `0.0` | `0.21` | `0.0` |
| `dual_axis_and|b=0.00|l=-|n=p02|w=-` | `dual_axis_and` | `false` | `0.6263736263736264` | `0.9108333333333334` | `0.43` | `0.0` | `0.0` | `0.25` | `0.0` |
| `dual_axis_and|b=0.00|l=-|n=p05|w=-` | `dual_axis_and` | `false` | `0.6145251396648045` | `0.9108333333333334` | `0.45` | `0.0` | `0.0` | `0.24` | `0.0` |
| `dual_axis_and|b=0.00|l=-|n=p10|w=-` | `dual_axis_and` | `false` | `0.5714285714285714` | `0.9108333333333334` | `0.52` | `0.0` | `0.0` | `0.2` | `0.0` |
| `dual_axis_blend|b=0.00|l=0.20|n=-|w=-` | `dual_axis_blend` | `false` | `0.6229508196721312` | `0.9151333333333334` | `0.43` | `0.0` | `0.0` | `0.26` | `0.0` |
| `dual_axis_blend|b=0.15|l=0.20|n=-|w=-` | `dual_axis_blend` | `false` | `0.6373626373626373` | `0.9236666666666667` | `0.42` | `0.0` | `0.0` | `0.24` | `0.0` |
| `dual_axis_blend|b=0.00|l=0.35|n=-|w=-` | `dual_axis_blend` | `false` | `0.5988700564971752` | `0.9125333333333334` | `0.47` | `0.0` | `0.0` | `0.24` | `0.0` |
| `dual_axis_blend|b=0.15|l=0.35|n=-|w=-` | `dual_axis_blend` | `false` | `0.6127167630057804` | `0.9214666666666667` | `0.47` | `0.0` | `0.0` | `0.2` | `0.0` |
| `dual_axis_min|b=0.00|l=-|n=-|w=-` | `dual_axis_min` | `false` | `0.6413043478260869` | `0.9108333333333334` | `0.41` | `0.0` | `0.0` | `0.25` | `0.0` |
| `dual_axis_min|b=0.15|l=-|n=-|w=-` | `dual_axis_min` | `false` | `0.6519337016574586` | `0.9194333333333333` | `0.41` | `0.0` | `0.0` | `0.22` | `0.0` |
- Eje2 gate `near_tag` `p02` F1 `0.6263736263736264` (`IN_DOMAIN_VALID FRR` `0.43`, `near_ood_neighbor FAR` `0.0`) is below the frozen CAL_ONLY p10 `0.6519337016574586`.
- Eje2 gate `near_tag` `p05` F1 `0.6145251396648045` (`IN_DOMAIN_VALID FRR` `0.45`, `near_ood_neighbor FAR` `0.0`) is below the frozen CAL_ONLY p10 `0.6519337016574586`.
- Eje2 gate `near_tag` `p10` F1 `0.5714285714285714` (`IN_DOMAIN_VALID FRR` `0.52`, `near_ood_neighbor FAR` `0.0`) is below the frozen CAL_ONLY p10 `0.6519337016574586`.
receta/full_only after 5-fold cal OOF: CAL_ONLY p10 F1 `0.6519337016574586`, 5x5 mean `0.774468085106383`. This is the honest operating point; it is not the in-sample v3 inflation figure.
### receta / clauses
Frozen `eje1_plus_struct|b=0.10|l=-|n=-|w=0.35` family `eje1_plus_struct` beta `0.1` w_f `0.35`. selection_policy `blind_apriori_eje1_plus_struct_b010`. frozen_column `1`. nested_modal_column `0`. CAL_ONLY p10 F1 `0.8361581920903954`. 5x5 F1 mean `0.8735604658106897` std `0.009372749191703517`.
| recipe | family | frozen | F1 | ROC-AUC | IN_DOMAIN_VALID FRR | OOD FAR | Adv FAR | Hybrid FAR | near_ood_neighbor FAR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `eje1_only|b=0.00|l=-|n=-|w=0.35` | `eje1_only` | `false` | `0.8571428571428571` | `0.9805` | `0.22` | `0.0` | `0.0` | `0.04` | `0.0` |
| `eje1_plus_struct|b=0.10|l=-|n=-|w=0.35` | `eje1_plus_struct` | `true` | `0.8361581920903954` | `0.9830333333333334` | `0.26` | `0.0` | `0.0` | `0.03` | `0.0` |
| `eje1_plus_struct|b=0.20|l=-|n=-|w=0.35` | `eje1_plus_struct` | `false` | `0.8160919540229885` | `0.9769666666666668` | `0.29` | `0.0` | `0.0` | `0.03` | `0.0` |
| `dual_axis_and|b=0.00|l=-|n=p02|w=0.35` | `dual_axis_and` | `false` | `0.850828729281768` | `0.9743999999999999` | `0.23` | `0.0` | `0.0` | `0.04` | `0.0` |
| `dual_axis_and|b=0.00|l=-|n=p05|w=0.35` | `dual_axis_and` | `false` | `0.8426966292134831` | `0.9743999999999999` | `0.25` | `0.0` | `0.0` | `0.03` | `0.0` |
| `dual_axis_and|b=0.00|l=-|n=p10|w=0.35` | `dual_axis_and` | `false` | `0.8023255813953488` | `0.9743999999999999` | `0.31` | `0.0` | `0.0` | `0.03` | `0.0` |
| `dual_axis_blend|b=0.00|l=0.20|n=-|w=0.35` | `dual_axis_blend` | `false` | `0.8461538461538461` | `0.9787666666666666` | `0.23` | `0.0` | `0.0` | `0.05` | `0.0` |
| `dual_axis_blend|b=0.15|l=0.20|n=-|w=0.35` | `dual_axis_blend` | `false` | `0.8314606741573034` | `0.9778` | `0.26` | `0.0` | `0.0` | `0.04` | `0.0` |
| `dual_axis_blend|b=0.00|l=0.35|n=-|w=0.35` | `dual_axis_blend` | `false` | `0.8351648351648352` | `0.9764333333333334` | `0.24` | `0.0` | `0.0` | `0.06` | `0.0` |
| `dual_axis_blend|b=0.15|l=0.35|n=-|w=0.35` | `dual_axis_blend` | `false` | `0.8` | `0.9744333333333334` | `0.3` | `0.0` | `0.0` | `0.05` | `0.0` |
| `dual_axis_min|b=0.00|l=-|n=-|w=0.35` | `dual_axis_min` | `false` | `0.8248587570621468` | `0.9743999999999999` | `0.27` | `0.0` | `0.0` | `0.04` | `0.0` |
| `dual_axis_min|b=0.15|l=-|n=-|w=0.35` | `dual_axis_min` | `false` | `0.7692307692307693` | `0.9729333333333334` | `0.35` | `0.0` | `0.0` | `0.04` | `0.0` |
Diagnostic `w_f` sensitivity (`{0.20, 0.35, 0.50}`, outside primary catalog):
| w_f | recipe | F1 | ROC-AUC | IN_DOMAIN_VALID FRR | OOD FAR | Adv FAR | Hybrid FAR | near_ood_neighbor FAR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `0.2` | `eje1_plus_struct|b=0.10|l=-|n=-|w=0.20` | `0.8756756756756757` | `0.9830333333333333` | `0.19` | `0.01` | `0.0` | `0.03` | `0.0` |
| `0.35` | `eje1_plus_struct|b=0.10|l=-|n=-|w=0.35` | `0.8361581920903954` | `0.9830333333333334` | `0.26` | `0.0` | `0.0` | `0.03` | `0.0` |
| `0.5` | `eje1_plus_struct|b=0.10|l=-|n=-|w=0.50` | `0.7953216374269005` | `0.9752000000000001` | `0.32` | `0.0` | `0.0` | `0.03` | `0.0` |
- Eje2 gate `near_tag` `p02` F1 `0.850828729281768` (`IN_DOMAIN_VALID FRR` `0.23`, `near_ood_neighbor FAR` `0.0`) is above the frozen CAL_ONLY p10 `0.8361581920903954`.
- Eje2 gate `near_tag` `p05` F1 `0.8426966292134831` (`IN_DOMAIN_VALID FRR` `0.25`, `near_ood_neighbor FAR` `0.0`) is above the frozen CAL_ONLY p10 `0.8361581920903954`.
- Eje2 gate `near_tag` `p10` F1 `0.8023255813953488` (`IN_DOMAIN_VALID FRR` `0.31`, `near_ood_neighbor FAR` `0.0`) is below the frozen CAL_ONLY p10 `0.8361581920903954`.

## 4. `clause_cap` DoS and flooding latency

`clause_cap` ∈ {`null`, 16, 24, 32} evaluated on frozen `eje1_plus_struct|b=0.10` (`w_f=0.35`). Per-prompt flooding latency (`[prompt] + selected_clauses`, 3 repeats per prompt) comes from `flooding_latency_v4.json`.
### python
Eval recipe `eje1_plus_struct|b=0.10|l=-|n=-|w=-` w_f `0.35`.
| clause_cap | mean_selected_clauses | prefilter s_struct/fallback/empty | F1 | FRR | FAR | dilution_80_20 FAR | smuggle_any FAR | smuggle_recipe_footnote FAR | smuggle_comment_docstring FAR | smuggle_json_yaml FAR | flooding FAR | prompt_injection_jailbreak FAR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `null` | `4.3925` | `379/21/0` | `0.74235807860262` | `0.15` | `0.14666666666666667` | `0.0` | `0.15` | `null` | `0.1` | `0.2` | `0.0` | `0.32` |
| `16` | `3.985` | `379/21/0` | `0.7478260869565218` | `0.14` | `0.14666666666666667` | `0.0` | `0.15` | `null` | `0.1` | `0.2` | `0.0` | `0.32` |
| `24` | `4.2525` | `379/21/0` | `0.74235807860262` | `0.15` | `0.14666666666666667` | `0.0` | `0.15` | `null` | `0.1` | `0.2` | `0.0` | `0.32` |
| `32` | `4.3675` | `379/21/0` | `0.74235807860262` | `0.15` | `0.14666666666666667` | `0.0` | `0.15` | `null` | `0.1` | `0.2` | `0.0` | `0.32` |
### receta
Eval recipe `eje1_plus_struct|b=0.10|l=-|n=-|w=-` w_f `0.35`.
| clause_cap | mean_selected_clauses | prefilter s_struct/fallback/empty | F1 | FRR | FAR | dilution_80_20 FAR | smuggle_any FAR | smuggle_recipe_footnote FAR | smuggle_comment_docstring FAR | smuggle_json_yaml FAR | flooding FAR | prompt_injection_jailbreak FAR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `null` | `4.475` | `381/19/0` | `0.8361581920903954` | `0.26` | `0.01` | `0.0` | `0.0` | `0.0` | `null` | `0.0` | `0.0` | `0.0` |
| `16` | `4.09` | `381/19/0` | `0.8361581920903954` | `0.26` | `0.01` | `0.0` | `0.0` | `0.0` | `null` | `0.0` | `0.0` | `0.0` |
| `24` | `4.4125` | `381/19/0` | `0.8361581920903954` | `0.26` | `0.01` | `0.0` | `0.0` | `0.0` | `null` | `0.0` | `0.0` | `0.0` |
| `32` | `4.475` | `381/19/0` | `0.8361581920903954` | `0.26` | `0.01` | `0.0` | `0.0` | `0.0` | `null` | `0.0` | `0.0` | `0.0` |
`PORTS_8080_8088_CLOSED` `true`.
### flooding latency ms — python
| cap | n_prompts | repeats | n_measurements | mean_clauses_per_prompt | total_clauses_per_pass | p50_ms | p99_ms | mean_ms | speedup_vs_uncapped |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `uncapped` | `6` | `3` | `18` | `72.0` | `432` | `3039.959416491911` | `3242.0331036901916` | `3037.3799282226373` | `1.0` |
| `cap_16` | `6` | `3` | `18` | `16.0` | `96` | `2585.1721670042025` | `2640.5604686631705` | `2580.0473334448825` | `1.1759214551712946` |
| `cap_24` | `6` | `3` | `18` | `24.0` | `144` | `2633.566875010729` | `2773.5125066316687` | `2647.24926411226` | `1.15431259609822` |
| `cap_32` | `6` | `3` | `18` | `32.0` | `192` | `2729.437333502574` | `2993.925468373927` | `2724.513645885357` | `1.1137678008495828` |
### flooding latency ms — receta
| cap | n_prompts | repeats | n_measurements | mean_clauses_per_prompt | total_clauses_per_pass | p50_ms | p99_ms | mean_ms | speedup_vs_uncapped |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `uncapped` | `6` | `3` | `18` | `57.333333333333336` | `344` | `2771.4501459995518` | `2873.4304576268187` | `2782.242143665725` | `1.0` |
| `cap_16` | `6` | `3` | `18` | `16.0` | `96` | `2368.467792010051` | `2421.385408252827` | `2367.656898167398` | `1.1701447473125657` |
| `cap_24` | `6` | `3` | `18` | `24.0` | `144` | `2504.2016665101983` | `2600.4021303585614` | `2504.350571833331` | `1.1067200310036474` |
| `cap_32` | `6` | `3` | `18` | `32.0` | `192` | `2517.9018749913666` | `2586.851380202861` | `2520.7334258868486` | `1.100698233527887` |

## 5. `N_cal` volume curve

Volume curve `N_cal` from `N=1` (1B contrast quantile blind thresholds) through OOF calibration (`N >= 5`). Means and stds are literals from `*_n_cal_volume_curve.json`.
### python
description_only `threshold_source` `1b_contrast_quantile_0.95` `threshold_relative_1b` `0.41880382274111844` `contrast_p99` `0.42965211742585413` `midpoint` `0.5` — F1 `0.5663716814159292` FRR `0.36` FAR `0.20666666666666667` ROC-AUC `0.8234`. `[ORACLE_UPPER_BOUND]` F1 `0.5968992248062015` (threshold `0.41230007951365377`).
| description_only policy | threshold | F1 | FRR | FAR |
| --- | --- | --- | --- | --- |
| `blind_1b_p95` | `0.41880382274111844` | `0.5663716814159292` | `0.36` | `0.20666666666666667` |
| `contrast_p99` | `0.42965211742585413` | `0.5561497326203209` | `0.48` | `0.11666666666666667` |
| `midpoint` | `0.5` | `0.0` | `1.0` | `0.0` |
| N_cal | n_seeds | p10 F1 mean | p10 F1 std | ROC-AUC mean | ROC-AUC std | FRR mean | FAR mean | threshold_stability_std |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `1` | `5` | `0.5047413069552888` | `0.09490741089301381` | `0.77456` | `0.059897108073391665` | `0.466` | `0.18066666666666667` | `0.008227002760234378` |
| `5` | `5` | `0.631407167722426` | `0.02245477794034355` | `0.8765666666666668` | `0.021228296105800785` | `0.21400000000000002` | `0.23533333333333334` | `0.01318746753222309` |
| `10` | `5` | `0.6472705707739582` | `0.023901315685281727` | `0.8866533333333333` | `0.014851198978907753` | `0.134` | `0.27199999999999996` | `0.00550986233735606` |
| `25` | `5` | `0.6514101360462171` | `0.013421473043315023` | `0.8988200000000001` | `0.006356737458092099` | `0.14200000000000002` | `0.25933333333333336` | `0.0036448945882160645` |
| `50` | `5` | `0.678432514372008` | `0.008621722603957879` | `0.8971` | `0.010124969135755372` | `0.186` | `0.19533333333333333` | `0.003580347159715984` |
| `100` | `5` | `0.671051854964991` | `0.007127801710847347` | `0.9003733333333332` | `0.0010296709290944566` | `0.188` | `0.2026666666666667` | `0.0020779413342763824` |
| `200` | `5` | `0.6785630887332303` | `0.014711487216301208` | `0.9008666666666667` | `0.004707145867956774` | `0.176` | `0.20200000000000004` | `0.002538551981676278` |
| `400` | `5` | `0.6795526962152263` | `0.004317736292027329` | `0.8989733333333334` | `0.0009283797115883479` | `0.19` | `0.1913333333333333` | `0.00048290216966452034` |
| `600` | `1` | `0.6722689075630253` | `0.0` | `0.8993666666666668` | `0.0` | `0.2` | `0.19333333333333333` | `0.0` |
| from_n | to_n | delta_f1 | delta_auc | delta_frr | delta_far |
| --- | --- | --- | --- | --- | --- |
| `1` | `5` | `0.12666586076713715` | `0.1020066666666668` | `-0.252` | `0.05466666666666667` |
| `5` | `10` | `0.01586340305153222` | `0.010086666666666466` | `-0.08000000000000002` | `0.036666666666666625` |
| `10` | `25` | `0.004139565272258894` | `0.01216666666666677` | `0.008000000000000007` | `-0.012666666666666604` |
| `25` | `50` | `0.027022378325790908` | `-0.0017200000000000548` | `0.043999999999999984` | `-0.06400000000000003` |
| `50` | `100` | `-0.007380659407017043` | `0.0032733333333332393` | `0.0020000000000000018` | `0.007333333333333358` |
| `100` | `200` | `0.007511233768239367` | `0.0004933333333334566` | `-0.01200000000000001` | `-0.0006666666666666488` |
| `200` | `400` | `0.0009896074819959466` | `-0.0018933333333333024` | `0.014000000000000012` | `-0.010666666666666741` |
| `400` | `600` | `-0.007283788652201029` | `0.00039333333333335663` | `0.010000000000000009` | `0.0020000000000000295` |
### receta
description_only `threshold_source` `1b_contrast_quantile_0.95` `threshold_relative_1b` `0.413870643130878` `contrast_p99` `0.42076616719641774` `midpoint` `0.5` — F1 `0.6098360655737705` FRR `0.07` FAR `0.37333333333333335` ROC-AUC `0.8683000000000001`. `[ORACLE_UPPER_BOUND]` F1 `0.6666666666666666` (threshold `0.43130465659824563`).
| description_only policy | threshold | F1 | FRR | FAR |
| --- | --- | --- | --- | --- |
| `blind_1b_p95` | `0.413870643130878` | `0.6098360655737705` | `0.07` | `0.37333333333333335` |
| `contrast_p99` | `0.42076616719641774` | `0.6222222222222222` | `0.16` | `0.2866666666666667` |
| `midpoint` | `0.5` | `0.0` | `1.0` | `0.0` |
| N_cal | n_seeds | p10 F1 mean | p10 F1 std | ROC-AUC mean | ROC-AUC std | FRR mean | FAR mean | threshold_stability_std |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `1` | `5` | `0.6002902778850376` | `0.026947176370044842` | `0.8844733333333332` | `0.023837766487469263` | `0.054000000000000006` | `0.4033333333333333` | `0.004551001761623248` |
| `5` | `5` | `0.669725355567293` | `0.05229038795142464` | `0.9137066666666668` | `0.011334617574296756` | `0.34` | `0.1` | `0.008540667605348736` |
| `10` | `5` | `0.6992613226962475` | `0.04695497455407487` | `0.91654` | `0.006121610173076226` | `0.278` | `0.11066666666666666` | `0.008654757969411321` |
| `25` | `5` | `0.6095157288091974` | `0.027926727730483044` | `0.9178466666666667` | `0.006116307891385278` | `0.47400000000000003` | `0.066` | `0.0029215024581871513` |
| `50` | `5` | `0.6420189802907033` | `0.04517602976012913` | `0.9157333333333334` | `0.004022920442774031` | `0.41` | `0.08066666666666668` | `0.004453264096659717` |
| `100` | `5` | `0.646437209991093` | `0.02510076715025134` | `0.9170733333333334` | `0.0028020230786581974` | `0.404` | `0.08199999999999999` | `0.0023606654317427475` |
| `200` | `5` | `0.6254536543477909` | `0.013106134938172222` | `0.9164933333333334` | `0.0006529420597061804` | `0.44000000000000006` | `0.07666666666666666` | `0.0020015538507494723` |
| `400` | `5` | `0.6433210708236574` | `0.010367185688414254` | `0.9169866666666667` | `0.0003826806036950556` | `0.41000000000000003` | `0.08133333333333333` | `0.0008974165075875135` |
| `600` | `1` | `0.6413043478260869` | `0.0` | `0.917` | `0.0` | `0.41` | `0.08333333333333333` | `0.0` |
| from_n | to_n | delta_f1 | delta_auc | delta_frr | delta_far |
| --- | --- | --- | --- | --- | --- |
| `1` | `5` | `0.06943507768225532` | `0.029233333333333555` | `0.28600000000000003` | `-0.30333333333333334` |
| `5` | `10` | `0.029535967128954566` | `0.0028333333333332433` | `-0.062` | `0.010666666666666658` |
| `10` | `25` | `-0.08974559388705017` | `0.0013066666666666782` | `0.196` | `-0.04466666666666666` |
| `25` | `50` | `0.0325032514815059` | `-0.0021133333333333004` | `-0.06400000000000006` | `0.014666666666666675` |
| `50` | `100` | `0.004418229700389742` | `0.0013400000000000079` | `-0.00599999999999995` | `0.0013333333333333114` |
| `100` | `200` | `-0.02098355564330212` | `-0.0005800000000000249` | `0.03600000000000003` | `-0.005333333333333329` |
| `200` | `400` | `0.017867416475866538` | `0.0004933333333333456` | `-0.030000000000000027` | `0.004666666666666666` |
| `400` | `600` | `-0.002016722997570497` | `1.333333333330966e-05` | `-5.551115123125783e-17` | `0.0020000000000000018` |
### Recommendation on 800–1,000
- `python` marginal `400`→`600` delta_f1 `-0.007283788652201029` delta_auc `0.00039333333333335663`.
- `receta` marginal `400`→`600` delta_f1 `-0.002016722997570497` delta_auc `1.333333333330966e-05`.
On both domains the 400→600 marginal F1 is near zero or negative. The ladder has plateaued for F1 gain by `N_cal≈100–400`. Extending to 800–1,000 is not justified for headline F1 on this holdout; revisit only inside `TASK-016` if cold domains need more calibration volume.

## 6. Master tables

CAL_ONLY p05/p10/p15, bootstrap CI95 / paired `delta_f1`, nested 5×5, and `[ORACLE_UPPER_BOUND]` are copied from dual-axis cells. Manifest bootstrap contract: n `1000`, seed `0`, `refits_thresholds` `true`.
### python / full_only
catalog_size `12`, cal_oof `true`, dir_variant `dir1024_sig_sep`.
CAL_ONLY on the frozen recipe:
| tag | F1 | FRR | FAR | precision | recall | threshold | ROC-AUC | tp | fn | tn | fp |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `p05` | `0.6923076923076923` | `0.1` | `0.23333333333333334` | `0.5625` | `0.9` | `0.5151544676877559` | `0.9162999999999999` | `90` | `10` | `230` | `70` |
| `p10` | `0.7022222222222222` | `0.21` | `0.15333333333333332` | `0.632` | `0.79` | `0.5272183609200629` | `0.9162999999999999` | `79` | `21` | `254` | `46` |
| `p15` | `0.7358490566037735` | `0.22` | `0.11333333333333333` | `0.6964285714285714` | `0.78` | `0.5322883998048449` | `0.9162999999999999` | `78` | `22` | `266` | `34` |
Bootstrap CI95 (n=`1000`, seed=`0`, `refits_thresholds`=`true`):
| recipe | F1 | ci95_low | ci95_high | FRR CI95 | FAR CI95 | ROC-AUC CI95 |
| --- | --- | --- | --- | --- | --- | --- |
| `eje1_plus_struct|b=0.10|l=-|n=-|w=-` | `0.7022222222222222` | `0.6548632882257233` | `0.759825327510917` | [`0.14`, `0.27`] | [`0.11666666666666667`, `0.19`] | [`0.89303`, `0.9369733333333333`] |
| delta_f1 contrast | baseline | point | mean | ci95_low | ci95_high |
| --- | --- | --- | --- | --- | --- |
| `frozen_minus_eje1_only` | `eje1_only` | `0.018461538461538418` | `0.019155631024016344` | `-0.0031184313313978524` | `0.040417288732378924` |
| `frozen_minus_best_dual_axis` | `dual_axis_blend|b=0.15|l=0.20|n=-|w=-` | `0.016029753602975316` | `0.024230944500481237` | `-0.007460136619174373` | `0.06047913497429038` |
nested 5x5:
| metric | mean | std |
| --- | --- | --- |
| `f1` | `0.7189992166038128` | `0.002795922874350561` |
| `frr` | `0.258` | `0.008366600265340763` |
| `far` | `0.10733333333333332` | `0.005477225575051658` |
| `roc_auc` | `0.9155266666666666` | `0.0012044823692265378` |
| seed | F1 | FRR | FAR | ROC-AUC |
| --- | --- | --- | --- | --- |
| `0` | `0.7192118226600985` | `0.27` | `0.1` | `0.9162999999999999` |
| `1` | `0.7177033492822966` | `0.25` | `0.11333333333333333` | `0.9165666666666668` |
| `2` | `0.714975845410628` | `0.26` | `0.11` | `0.9145333333333334` |
| `3` | `0.7219512195121951` | `0.26` | `0.10333333333333333` | `0.9162999999999999` |
| `4` | `0.7211538461538461` | `0.25` | `0.11` | `0.9139333333333335` |
[ORACLE_UPPER_BOUND] source `frozen_recipe_holdout_scores_fit_on_all_holdout_labels` F1 `0.7428571428571429` FRR `0.22` FAR `0.10666666666666667` threshold `0.5344316856798338`.
### python / clauses
catalog_size `12`, cal_oof `true`, dir_variant `dir1024_sig_sep`.
CAL_ONLY on the frozen recipe:
| tag | F1 | FRR | FAR | precision | recall | threshold | ROC-AUC | tp | fn | tn | fp |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `p05` | `0.6963562753036437` | `0.14` | `0.20333333333333334` | `0.5850340136054422` | `0.86` | `0.48264635419698154` | `0.9080666666666666` | `86` | `14` | `239` | `61` |
| `p10` | `0.7522123893805309` | `0.15` | `0.13666666666666666` | `0.6746031746031746` | `0.85` | `0.4914901501871041` | `0.9080666666666666` | `85` | `15` | `259` | `41` |
| `p15` | `0.7559808612440191` | `0.21` | `0.1` | `0.7247706422018348` | `0.79` | `0.4964755945734779` | `0.9080666666666666` | `79` | `21` | `270` | `30` |
Bootstrap CI95 (n=`1000`, seed=`0`, `refits_thresholds`=`true`):
| recipe | F1 | ci95_low | ci95_high | FRR CI95 | FAR CI95 | ROC-AUC CI95 |
| --- | --- | --- | --- | --- | --- | --- |
| `eje1_plus_struct|b=0.10|l=-|n=-|w=0.35` | `0.7522123893805309` | `0.7029176320066391` | `0.7943957239790039` | [`0.11`, `0.21`] | [`0.1`, `0.18008333333333326`] | [`0.8864316666666666`, `0.92844`] |
| delta_f1 contrast | baseline | point | mean | ci95_low | ci95_high |
| --- | --- | --- | --- | --- | --- |
| `frozen_minus_eje1_only` | `eje1_only` | `0.03966178209308158` | `0.03218787533607072` | `-0.01885863622258024` | `0.08054111011223632` |
| `frozen_minus_best_dual_axis` | `dual_axis_and|b=0.00|l=-|n=p10|w=0.35` | `0.023323500491642002` | `0.021586185874188823` | `-0.033127967432938124` | `0.07630012085946132` |
nested 5x5:
| metric | mean | std |
| --- | --- | --- |
| `f1` | `0.7223124702809092` | `0.02047752362858949` |
| `frr` | `0.28400000000000003` | `0.019493588689617918` |
| `far` | `0.08933333333333333` | `0.023967570682996736` |
| `roc_auc` | `0.86222` | `0.0033724867185308365` |
| seed | F1 | FRR | FAR | ROC-AUC |
| --- | --- | --- | --- | --- |
| `0` | `0.6948356807511737` | `0.26` | `0.13` | `0.8675333333333333` |
| `1` | `0.7282051282051282` | `0.29` | `0.08` | `0.8597999999999999` |
| `2` | `0.7373737373737373` | `0.27` | `0.08333333333333333` | `0.8610333333333333` |
| `3` | `0.7076923076923077` | `0.31` | `0.08666666666666667` | `0.8592999999999998` |
| `4` | `0.743455497382199` | `0.29` | `0.06666666666666667` | `0.8634333333333334` |
[ORACLE_UPPER_BOUND] source `frozen_recipe_holdout_scores_fit_on_all_holdout_labels` F1 `0.7627906976744186` FRR `0.18` FAR `0.11` threshold `0.49562755597972974`.
### receta / full_only
catalog_size `12`, cal_oof `true`, dir_variant `dir1024_sig_sep`.
CAL_ONLY on the frozen recipe:
| tag | F1 | FRR | FAR | precision | recall | threshold | ROC-AUC | tp | fn | tn | fp |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `p05` | `0.72` | `0.28` | `0.09333333333333334` | `0.72` | `0.72` | `0.5361457418509648` | `0.926` | `72` | `28` | `272` | `28` |
| `p10` | `0.6519337016574586` | `0.41` | `0.07333333333333333` | `0.7283950617283951` | `0.59` | `0.5469642763474517` | `0.926` | `59` | `41` | `278` | `22` |
| `p15` | `0.591715976331361` | `0.5` | `0.06333333333333334` | `0.7246376811594203` | `0.5` | `0.5531468558064664` | `0.926` | `50` | `50` | `281` | `19` |
Bootstrap CI95 (n=`1000`, seed=`0`, `refits_thresholds`=`true`):
| recipe | F1 | ci95_low | ci95_high | FRR CI95 | FAR CI95 | ROC-AUC CI95 |
| --- | --- | --- | --- | --- | --- | --- |
| `eje1_plus_struct|b=0.10|l=-|n=-|w=-` | `0.6519337016574586` | `0.5833333333333334` | `0.7252747252747253` | [`0.31`, `0.5`] | [`0.05333333333333334`, `0.09341666666666659`] | [`0.9119616666666666`, `0.9406675`] |
| delta_f1 contrast | baseline | point | mean | ci95_low | ci95_high |
| --- | --- | --- | --- | --- | --- |
| `frozen_minus_eje1_only` | `eje1_only` | `0.010629353831371646` | `0.006594606299351997` | `-0.018206817374775742` | `0.03261054340673492` |
| `frozen_minus_best_dual_axis` | `dual_axis_min|b=0.15|l=-|n=-|w=-` | `0.0` | `0.007175823259362231` | `-0.04199946606387657` | `0.05327798834237806` |
nested 5x5:
| metric | mean | std |
| --- | --- | --- |
| `f1` | `0.774468085106383` | `0.0` |
| `frr` | `0.09` | `0.0` |
| `far` | `0.14666666666666667` | `0.0` |
| `roc_auc` | `0.92774` | `0.00018318175552043428` |
| seed | F1 | FRR | FAR | ROC-AUC |
| --- | --- | --- | --- | --- |
| `0` | `0.774468085106383` | `0.09` | `0.14666666666666667` | `0.9276666666666666` |
| `1` | `0.774468085106383` | `0.09` | `0.14666666666666667` | `0.9277333333333333` |
| `2` | `0.774468085106383` | `0.09` | `0.14666666666666667` | `0.9275` |
| `3` | `0.774468085106383` | `0.09` | `0.14666666666666667` | `0.9279999999999999` |
| `4` | `0.774468085106383` | `0.09` | `0.14666666666666667` | `0.9278` |
[ORACLE_UPPER_BOUND] source `frozen_recipe_holdout_scores_fit_on_all_holdout_labels` F1 `0.7796610169491526` FRR `0.08` FAR `0.14666666666666667` threshold `0.5122363638574108`.
### receta / clauses
catalog_size `12`, cal_oof `true`, dir_variant `dir1024_sig_sep`.
CAL_ONLY on the frozen recipe:
| tag | F1 | FRR | FAR | precision | recall | threshold | ROC-AUC | tp | fn | tn | fp |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `p05` | `0.8709677419354839` | `0.19` | `0.016666666666666666` | `0.9418604651162791` | `0.81` | `0.502018915834207` | `0.9830333333333334` | `81` | `19` | `295` | `5` |
| `p10` | `0.8361581920903954` | `0.26` | `0.01` | `0.961038961038961` | `0.74` | `0.5080560923644225` | `0.9830333333333334` | `74` | `26` | `297` | `3` |
| `p15` | `0.8` | `0.32` | `0.006666666666666667` | `0.9714285714285714` | `0.68` | `0.512438059384882` | `0.9830333333333334` | `68` | `32` | `298` | `2` |
Bootstrap CI95 (n=`1000`, seed=`0`, `refits_thresholds`=`true`):
| recipe | F1 | ci95_low | ci95_high | FRR CI95 | FAR CI95 | ROC-AUC CI95 |
| --- | --- | --- | --- | --- | --- | --- |
| `eje1_plus_struct|b=0.10|l=-|n=-|w=0.35` | `0.8361581920903954` | `0.7784431137724551` | `0.8865168376933084` | [`0.18`, `0.34`] | [`0.0`, `0.02`] | [`0.9734316666666667`, `0.9913`] |
| delta_f1 contrast | baseline | point | mean | ci95_low | ci95_high |
| --- | --- | --- | --- | --- | --- |
| `frozen_minus_eje1_only` | `eje1_only` | `-0.02098466505246166` | `-0.016881954992477216` | `-0.050828820555378865` | `0.01888663910125362` |
| `frozen_minus_best_dual_axis` | `dual_axis_and|b=0.00|l=-|n=p02|w=0.35` | `-0.014670537191372568` | `-0.014105406377478175` | `-0.044839504912830855` | `0.018302753431034463` |
nested 5x5:
| metric | mean | std |
| --- | --- | --- |
| `f1` | `0.8735604658106897` | `0.009372749191703517` |
| `frr` | `0.122` | `0.020493901531919198` |
| `far` | `0.044` | `0.004346134936801767` |
| `roc_auc` | `0.9797266666666667` | `0.0010412065650538098` |
| seed | F1 | FRR | FAR | ROC-AUC |
| --- | --- | --- | --- | --- |
| `0` | `0.8823529411764706` | `0.1` | `0.04666666666666667` | `0.9805` |
| `1` | `0.86` | `0.14` | `0.04666666666666667` | `0.9779666666666667` |
| `2` | `0.8730964467005076` | `0.14` | `0.03666666666666667` | `0.9797333333333333` |
| `3` | `0.8823529411764706` | `0.1` | `0.04666666666666667` | `0.9805` |
| `4` | `0.87` | `0.13` | `0.043333333333333335` | `0.9799333333333333` |
[ORACLE_UPPER_BOUND] source `frozen_recipe_holdout_scores_fit_on_all_holdout_labels` F1 `0.8842105263157894` FRR `0.16` FAR `0.02` threshold `0.5016233439390061`.
### Subtype breakdown
| domain | granularity | subtype | category | n | kind | error_rate |
| --- | --- | --- | --- | --- | --- | --- |
| `python` | `full_only` | `asyncio_concurrency` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.125` |
| `python` | `full_only` | `code_snippet` | `IN_DOMAIN_VALID` | `6` | `frr` | `0.3333333333333333` |
| `python` | `full_only` | `data_structures_oop` | `IN_DOMAIN_VALID` | `6` | `frr` | `0.5` |
| `python` | `full_only` | `delimiter_escape` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.16666666666666666` |
| `python` | `full_only` | `dilution_20_80` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `python` | `full_only` | `dilution_50_50` | `HYBRID_BOUNDARY` | `10` | `far` | `0.1` |
| `python` | `full_only` | `dilution_80_20` | `HYBRID_BOUNDARY` | `10` | `far` | `0.7` |
| `python` | `full_only` | `extreme_high_entropy_gibberish` | `ADVERSARIAL_FUZZING` | `7` | `far` | `0.0` |
| `python` | `full_only` | `extreme_short_punct` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.0` |
| `python` | `full_only` | `homoglyph_zwsp_fullwidth` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `python` | `full_only` | `keyword_stuffing_hidden_instruction` | `ADVERSARIAL_FUZZING` | `6` | `far` | `0.3333333333333333` |
| `python` | `full_only` | `long_architecture_guide` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.0` |
| `python` | `full_only` | `long_context_flooding` | `ADVERSARIAL_FUZZING` | `6` | `far` | `0.16666666666666666` |
| `python` | `full_only` | `long_debugging_walkthrough` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.0` |
| `python` | `full_only` | `near_ood_neighbor` | `HYBRID_BOUNDARY` | `12` | `far` | `0.5833333333333334` |
| `python` | `full_only` | `obfuscation_base64` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `python` | `full_only` | `obfuscation_hex_rot13_leet` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.0` |
| `python` | `full_only` | `ood_architecture_music_hardware` | `OUT_OF_DOMAIN_BENIGN` | `8` | `far` | `0.0` |
| `python` | `full_only` | `ood_astronomy_geology` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `python` | `full_only` | `ood_finance_law` | `OUT_OF_DOMAIN_BENIGN` | `12` | `far` | `0.0` |
| `python` | `full_only` | `ood_history_literature_philosophy` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `python` | `full_only` | `ood_medicine_biology` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `python` | `full_only` | `ood_suite2_clinc` | `OUT_OF_DOMAIN_BENIGN` | `40` | `far` | `0.0` |
| `python` | `full_only` | `ood_travel_weather_sports` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `python` | `full_only` | `packaging_env` | `IN_DOMAIN_VALID` | `6` | `frr` | `0.16666666666666666` |
| `python` | `full_only` | `pivot_middle` | `HYBRID_BOUNDARY` | `10` | `far` | `0.8` |
| `python` | `full_only` | `pivot_prefix` | `HYBRID_BOUNDARY` | `10` | `far` | `0.4` |
| `python` | `full_only` | `pivot_suffix` | `HYBRID_BOUNDARY` | `10` | `far` | `0.2` |
| `python` | `full_only` | `polarity_flip_indirect` | `HYBRID_BOUNDARY` | `8` | `far` | `0.25` |
| `python` | `full_only` | `prompt_injection_jailbreak` | `ADVERSARIAL_FUZZING` | `25` | `far` | `0.28` |
| `python` | `full_only` | `pytest_testing` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.0` |
| `python` | `full_only` | `short_idiom_query` | `IN_DOMAIN_VALID` | `20` | `frr` | `0.5` |
| `python` | `full_only` | `smuggle_comment_docstring` | `HYBRID_BOUNDARY` | `10` | `far` | `0.2` |
| `python` | `full_only` | `smuggle_json_yaml` | `HYBRID_BOUNDARY` | `10` | `far` | `0.1` |
| `python` | `full_only` | `stdlib_idiom` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.2` |
| `python` | `full_only` | `traceback_debugging` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.125` |
| `python` | `full_only` | `typing_protocol` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.125` |
| `python` | `clauses` | `asyncio_concurrency` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.0` |
| `python` | `clauses` | `code_snippet` | `IN_DOMAIN_VALID` | `6` | `frr` | `1.0` |
| `python` | `clauses` | `data_structures_oop` | `IN_DOMAIN_VALID` | `6` | `frr` | `0.0` |
| `python` | `clauses` | `delimiter_escape` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.3333333333333333` |
| `python` | `clauses` | `dilution_20_80` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `python` | `clauses` | `dilution_50_50` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `python` | `clauses` | `dilution_80_20` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `python` | `clauses` | `extreme_high_entropy_gibberish` | `ADVERSARIAL_FUZZING` | `7` | `far` | `0.0` |
| `python` | `clauses` | `extreme_short_punct` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.0` |
| `python` | `clauses` | `homoglyph_zwsp_fullwidth` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `python` | `clauses` | `keyword_stuffing_hidden_instruction` | `ADVERSARIAL_FUZZING` | `6` | `far` | `0.5` |
| `python` | `clauses` | `long_architecture_guide` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.3` |
| `python` | `clauses` | `long_context_flooding` | `ADVERSARIAL_FUZZING` | `6` | `far` | `0.0` |
| `python` | `clauses` | `long_debugging_walkthrough` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.5` |
| `python` | `clauses` | `near_ood_neighbor` | `HYBRID_BOUNDARY` | `12` | `far` | `0.75` |
| `python` | `clauses` | `obfuscation_base64` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.08333333333333333` |
| `python` | `clauses` | `obfuscation_hex_rot13_leet` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.2` |
| `python` | `clauses` | `ood_architecture_music_hardware` | `OUT_OF_DOMAIN_BENIGN` | `8` | `far` | `0.125` |
| `python` | `clauses` | `ood_astronomy_geology` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `python` | `clauses` | `ood_finance_law` | `OUT_OF_DOMAIN_BENIGN` | `12` | `far` | `0.0` |
| `python` | `clauses` | `ood_history_literature_philosophy` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `python` | `clauses` | `ood_medicine_biology` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `python` | `clauses` | `ood_suite2_clinc` | `OUT_OF_DOMAIN_BENIGN` | `40` | `far` | `0.05` |
| `python` | `clauses` | `ood_travel_weather_sports` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `python` | `clauses` | `packaging_env` | `IN_DOMAIN_VALID` | `6` | `frr` | `0.0` |
| `python` | `clauses` | `pivot_middle` | `HYBRID_BOUNDARY` | `10` | `far` | `0.3` |
| `python` | `clauses` | `pivot_prefix` | `HYBRID_BOUNDARY` | `10` | `far` | `0.2` |
| `python` | `clauses` | `pivot_suffix` | `HYBRID_BOUNDARY` | `10` | `far` | `0.1` |
| `python` | `clauses` | `polarity_flip_indirect` | `HYBRID_BOUNDARY` | `8` | `far` | `0.25` |
| `python` | `clauses` | `prompt_injection_jailbreak` | `ADVERSARIAL_FUZZING` | `25` | `far` | `0.32` |
| `python` | `clauses` | `pytest_testing` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.0` |
| `python` | `clauses` | `short_idiom_query` | `IN_DOMAIN_VALID` | `20` | `frr` | `0.05` |
| `python` | `clauses` | `smuggle_comment_docstring` | `HYBRID_BOUNDARY` | `10` | `far` | `0.1` |
| `python` | `clauses` | `smuggle_json_yaml` | `HYBRID_BOUNDARY` | `10` | `far` | `0.2` |
| `python` | `clauses` | `stdlib_idiom` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.0` |
| `python` | `clauses` | `traceback_debugging` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.0` |
| `python` | `clauses` | `typing_protocol` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.0` |
| `receta` | `full_only` | `cocina_regional` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.5` |
| `receta` | `full_only` | `consulta_corta` | `IN_DOMAIN_VALID` | `20` | `frr` | `0.65` |
| `receta` | `full_only` | `delimiter_escape` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `receta` | `full_only` | `diagnostico_pasteleria_panaderia` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.25` |
| `receta` | `full_only` | `dilution_20_80` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `receta` | `full_only` | `dilution_50_50` | `HYBRID_BOUNDARY` | `10` | `far` | `0.1` |
| `receta` | `full_only` | `dilution_80_20` | `HYBRID_BOUNDARY` | `10` | `far` | `0.7` |
| `receta` | `full_only` | `extreme_high_entropy_gibberish` | `ADVERSARIAL_FUZZING` | `7` | `far` | `0.0` |
| `receta` | `full_only` | `extreme_short_punct` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.0` |
| `receta` | `full_only` | `guia_culinaria_larga` | `IN_DOMAIN_VALID` | `12` | `frr` | `0.0` |
| `receta` | `full_only` | `homoglyph_zwsp_fullwidth` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `receta` | `full_only` | `keyword_stuffing_hidden_instruction` | `ADVERSARIAL_FUZZING` | `6` | `far` | `0.0` |
| `receta` | `full_only` | `long_context_flooding` | `ADVERSARIAL_FUZZING` | `6` | `far` | `0.0` |
| `receta` | `full_only` | `near_ood_neighbor` | `HYBRID_BOUNDARY` | `12` | `far` | `0.0` |
| `receta` | `full_only` | `obfuscation_base64` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `receta` | `full_only` | `obfuscation_hex_rot13_leet` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.0` |
| `receta` | `full_only` | `ood_finanzas_derecho` | `OUT_OF_DOMAIN_BENIGN` | `12` | `far` | `0.0` |
| `receta` | `full_only` | `ood_hardware_arquitectura_musica` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `receta` | `full_only` | `ood_historia_literatura` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `receta` | `full_only` | `ood_medicina_ciencia` | `OUT_OF_DOMAIN_BENIGN` | `11` | `far` | `0.0` |
| `receta` | `full_only` | `ood_suite2_clean_astronomia` | `OUT_OF_DOMAIN_BENIGN` | `7` | `far` | `0.0` |
| `receta` | `full_only` | `ood_suite2_clean_legal` | `OUT_OF_DOMAIN_BENIGN` | `9` | `far` | `0.0` |
| `receta` | `full_only` | `ood_suite2_clean_medicina` | `OUT_OF_DOMAIN_BENIGN` | `9` | `far` | `0.0` |
| `receta` | `full_only` | `ood_suite2_es_oos` | `OUT_OF_DOMAIN_BENIGN` | `20` | `far` | `0.0` |
| `receta` | `full_only` | `ood_viajes_clima_deportes` | `OUT_OF_DOMAIN_BENIGN` | `12` | `far` | `0.0` |
| `receta` | `full_only` | `panaderia_fermentacion` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.7` |
| `receta` | `full_only` | `pivot_middle` | `HYBRID_BOUNDARY` | `10` | `far` | `0.6` |
| `receta` | `full_only` | `pivot_prefix` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `receta` | `full_only` | `pivot_suffix` | `HYBRID_BOUNDARY` | `10` | `far` | `0.1` |
| `receta` | `full_only` | `polarity_flip_indirect` | `HYBRID_BOUNDARY` | `8` | `far` | `0.0` |
| `receta` | `full_only` | `prompt_injection_jailbreak` | `ADVERSARIAL_FUZZING` | `25` | `far` | `0.0` |
| `receta` | `full_only` | `receta_completa` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.0` |
| `receta` | `full_only` | `salsas_emulsiones` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.375` |
| `receta` | `full_only` | `smuggle_json_yaml` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `receta` | `full_only` | `smuggle_recipe_footnote` | `HYBRID_BOUNDARY` | `10` | `far` | `0.7` |
| `receta` | `full_only` | `sustitucion_ingredientes` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.25` |
| `receta` | `full_only` | `tecnica_culinaria` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.5` |
| `receta` | `full_only` | `temperatura_tiempos` | `IN_DOMAIN_VALID` | `6` | `frr` | `0.8333333333333334` |
| `receta` | `clauses` | `cocina_regional` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.5` |
| `receta` | `clauses` | `consulta_corta` | `IN_DOMAIN_VALID` | `20` | `frr` | `0.2` |
| `receta` | `clauses` | `delimiter_escape` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `receta` | `clauses` | `diagnostico_pasteleria_panaderia` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.5` |
| `receta` | `clauses` | `dilution_20_80` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `receta` | `clauses` | `dilution_50_50` | `HYBRID_BOUNDARY` | `10` | `far` | `0.1` |
| `receta` | `clauses` | `dilution_80_20` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `receta` | `clauses` | `extreme_high_entropy_gibberish` | `ADVERSARIAL_FUZZING` | `7` | `far` | `0.0` |
| `receta` | `clauses` | `extreme_short_punct` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.0` |
| `receta` | `clauses` | `guia_culinaria_larga` | `IN_DOMAIN_VALID` | `12` | `frr` | `0.0` |
| `receta` | `clauses` | `homoglyph_zwsp_fullwidth` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `receta` | `clauses` | `keyword_stuffing_hidden_instruction` | `ADVERSARIAL_FUZZING` | `6` | `far` | `0.0` |
| `receta` | `clauses` | `long_context_flooding` | `ADVERSARIAL_FUZZING` | `6` | `far` | `0.0` |
| `receta` | `clauses` | `near_ood_neighbor` | `HYBRID_BOUNDARY` | `12` | `far` | `0.0` |
| `receta` | `clauses` | `obfuscation_base64` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `receta` | `clauses` | `obfuscation_hex_rot13_leet` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.0` |
| `receta` | `clauses` | `ood_finanzas_derecho` | `OUT_OF_DOMAIN_BENIGN` | `12` | `far` | `0.0` |
| `receta` | `clauses` | `ood_hardware_arquitectura_musica` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `receta` | `clauses` | `ood_historia_literatura` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `receta` | `clauses` | `ood_medicina_ciencia` | `OUT_OF_DOMAIN_BENIGN` | `11` | `far` | `0.0` |
| `receta` | `clauses` | `ood_suite2_clean_astronomia` | `OUT_OF_DOMAIN_BENIGN` | `7` | `far` | `0.0` |
| `receta` | `clauses` | `ood_suite2_clean_legal` | `OUT_OF_DOMAIN_BENIGN` | `9` | `far` | `0.0` |
| `receta` | `clauses` | `ood_suite2_clean_medicina` | `OUT_OF_DOMAIN_BENIGN` | `9` | `far` | `0.0` |
| `receta` | `clauses` | `ood_suite2_es_oos` | `OUT_OF_DOMAIN_BENIGN` | `20` | `far` | `0.0` |
| `receta` | `clauses` | `ood_viajes_clima_deportes` | `OUT_OF_DOMAIN_BENIGN` | `12` | `far` | `0.0` |
| `receta` | `clauses` | `panaderia_fermentacion` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.6` |
| `receta` | `clauses` | `pivot_middle` | `HYBRID_BOUNDARY` | `10` | `far` | `0.1` |
| `receta` | `clauses` | `pivot_prefix` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `receta` | `clauses` | `pivot_suffix` | `HYBRID_BOUNDARY` | `10` | `far` | `0.1` |
| `receta` | `clauses` | `polarity_flip_indirect` | `HYBRID_BOUNDARY` | `8` | `far` | `0.0` |
| `receta` | `clauses` | `prompt_injection_jailbreak` | `ADVERSARIAL_FUZZING` | `25` | `far` | `0.0` |
| `receta` | `clauses` | `receta_completa` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.0` |
| `receta` | `clauses` | `salsas_emulsiones` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.125` |
| `receta` | `clauses` | `smuggle_json_yaml` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `receta` | `clauses` | `smuggle_recipe_footnote` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `receta` | `clauses` | `sustitucion_ingredientes` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.375` |
| `receta` | `clauses` | `tecnica_culinaria` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.2` |
| `receta` | `clauses` | `temperatura_tiempos` | `IN_DOMAIN_VALID` | `6` | `frr` | `0.3333333333333333` |
### Canary (`sqlite3` / `subprocess` / `json`)
Each canary row carries an explicit `kind` label. `all_marker.kind` is F1; `in_domain_valid_marker.kind` is FRR.
| domain | granularity | kind | n_marker | n_marker_in_domain_valid | all_marker kind (F1) | all_marker F1/error | in-domain kind (FRR) | in-domain FRR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `python` | `full_only` | `sqlite3` | `4` | `1` | `f1` | `0.6666666666666666` | `frr` | `0.0` |
| `python` | `full_only` | `subprocess` | `4` | `3` | `f1` | `0.8571428571428571` | `frr` | `0.0` |
| `python` | `full_only` | `json` | `12` | `9` | `f1` | `0.9` | `frr` | `0.0` |
| `python` | `full_only` | `any_kind` | `17` | `-` | `f1` | `0.88` | `-` | `-` |
| `python` | `clauses` | `sqlite3` | `4` | `1` | `f1` | `0.0` | `frr` | `1.0` |
| `python` | `clauses` | `subprocess` | `4` | `3` | `f1` | `0.8571428571428571` | `frr` | `0.0` |
| `python` | `clauses` | `json` | `12` | `9` | `f1` | `0.8888888888888888` | `frr` | `0.1111111111111111` |
| `python` | `clauses` | `any_kind` | `17` | `-` | `f1` | `0.8181818181818182` | `-` | `-` |
| `receta` | `full_only` | `sqlite3` | `0` | `0` | `null` | `null` | `null` | `null` |
| `receta` | `full_only` | `subprocess` | `0` | `0` | `null` | `null` | `null` | `null` |
| `receta` | `full_only` | `json` | `0` | `0` | `null` | `null` | `null` | `null` |
| `receta` | `full_only` | `any_kind` | `0` | `-` | `null` | `null` | `-` | `-` |
| `receta` | `clauses` | `sqlite3` | `0` | `0` | `null` | `null` | `null` | `null` |
| `receta` | `clauses` | `subprocess` | `0` | `0` | `null` | `null` | `null` | `null` |
| `receta` | `clauses` | `json` | `0` | `0` | `null` | `null` | `null` | `null` |
| `receta` | `clauses` | `any_kind` | `0` | `-` | `null` | `null` | `-` | `-` |

## 7. Verdict

### Readiness for `TASK-016`
Ready to start: three new cold domains + standardized comparative benchmark, and optional revisit of `N_cal` 800–1,000 only if cold-domain variance demands it. Do not execute `TASK-016` inside this task.
### Rust port (`crates/sf-kernels` + `crates/sf-proxy`)
**NO-GO** for enabling the production scorer path or promoting this recipe into live `sf-proxy` scoring.
Reasons (stored literals):
- python/full_only near-OOD FAR `0.5833333333333334`; hybrid FAR `0.34`.
- receta/full_only CAL_ONLY p10 F1 `0.6519337016574586` after honest 5-fold OOF; friendly-fire subtypes (`consulta_corta`, `panaderia_fermentacion`) remain non-zero FRR.
- Volume curve has plateaued for F1; 800–1,000 is not a forced next step for gain.
- Scorer stays **OFF** in production for `TASK-015`.
Research serialization of the frozen offline recipe may be discussed after human review, but that is not a production enablement GO.

