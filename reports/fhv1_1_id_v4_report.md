# `fhv1_1` I+D v4 — hardening, dual-axis, `clause_cap`, `N_cal` curve

**Task**: `TASK-015`
**Branch**: `feat/fhv1-1-id-v4-hardening-and-sample-curve`
**Dtype**: `float64`. **normalize**: `true`. **mode**: `v4`.

Numbers in the tables are literals copied from `/tmp/fhv1_1_id_v4` JSON. A missing key aborts the generator.

## 0. Executive

Lineage: `TASK-011` (hardening/falsification) → `TASK-012` (replay) → `TASK-013` (fine dials) → `TASK-014` (v3 full-1024D + lexical guard) → `TASK-015` (v4 hardening, Eje 2, `clause_cap`, `N_cal` curve).
Frozen recipe family on every dual-axis cell is selected under 5-fold cal OOF (`cal_oof_folds` `5`). Eje 1 preset `1B_base_tech`. Eje 2 stratum `near_ood_neighbor`. `normalize` `true`. `dtype` `float64`. dim `1024`.
Bootstrap contract on the manifest: resamples `1000`, seed `0`, `refits_thresholds` `true`. Dual-axis cell JSON stores CAL_ONLY + nested 5×5 OOF + `[ORACLE_UPPER_BOUND]`; bootstrap CI blocks are not present as separate cell fields in this scratch.
Upper-bound rows stay labeled `[ORACLE_UPPER_BOUND]` and are outside the executive F1 column.
| domain | granularity | family | frozen recipe | CAL_ONLY p10 F1 | 5x5 F1 mean | 5x5 F1 std | ROC-AUC | OOD FAR | adversarial FAR | hybrid FAR | near-OOD FAR | S_struct p50 us | S_struct p99 us |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `python` | `full_only` | `eje1_plus_struct` | `eje1_plus_struct|b=0.10|l=-|n=-|w=-` | `0.7022222222222222` | `0.7189992166038128` | `0.002795922874350561` | `0.9162999999999999` | `0.0` | `0.12` | `0.34` | `0.5833333333333334` | `25.6045` | `272.75013999999936` |
| `python` | `clauses` | `eje1_plus_struct` | `eje1_plus_struct|b=0.10|l=-|n=-|w=0.50` | `0.7488151658767772` | `0.709096886010325` | `0.0158763312555823` | `0.9171666666666667` | `0.01` | `0.13` | `0.18` | `0.6666666666666666` | `25.4795` | `277.0202199999998` |
| `receta` | `full_only` | `eje1_plus_struct` | `eje1_plus_struct|b=0.20|l=-|n=-|w=-` | `0.6629834254143646` | `0.774468085106383` | `0.0` | `0.9286666666666666` | `0.0` | `0.0` | `0.21` | `0.0` | `26.834` | `254.62280000000007` |
| `receta` | `clauses` | `eje1_plus_struct` | `eje1_plus_struct|b=0.10|l=-|n=-|w=0.20` | `0.8756756756756757` | `0.8828960879221736` | `0.01371560402362309` | `0.9830333333333333` | `0.01` | `0.0` | `0.03` | `0.0` | `27.1665` | `260.57690000000036` |
What improved / remains open (literals only):
- `python`/`full_only`: frozen `eje1_plus_struct|b=0.10|l=-|n=-|w=-` CAL_ONLY p10 F1 `0.7022222222222222` is above the best stored dual-axis gate F1 `0.6755555555555556` (`near_tag` `p10`).
- Paired `p02` F1 `0.6666666666666666` is below the headline.
- `python`/`clauses`: frozen `eje1_plus_struct|b=0.10|l=-|n=-|w=0.50` CAL_ONLY p10 F1 `0.7488151658767772` is above the best stored dual-axis gate F1 `0.7288888888888889` (`near_tag` `p10`).
- Paired `p02` F1 `0.7203389830508474` is below the headline.
- `receta`/`full_only`: frozen `eje1_plus_struct|b=0.20|l=-|n=-|w=-` CAL_ONLY p10 F1 `0.6629834254143646` is above the best stored dual-axis gate F1 `0.6263736263736264` (`near_tag` `p02`).
- Paired `p02` F1 `0.6263736263736264` is below the headline.
- `receta`/`clauses`: frozen `eje1_plus_struct|b=0.10|l=-|n=-|w=0.20` CAL_ONLY p10 F1 `0.8756756756756757` is above the best stored dual-axis gate F1 `0.850828729281768` (`near_tag` `p02`).
- Paired `p02` F1 `0.850828729281768` is below the headline.
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
/dev/disk3s5   460Gi   406Gi    16Gi    97%    3.0M  169M    2%   /System/Volumes/Data
Filesystem   1024-blocks      Used Available Capacity iused     ifree %iused  Mounted on
/dev/disk3s5   482797652 426161060  16865120    97% 2990628 168651200    2%   /System/Volumes/Data
available_kib 16865120

# tmp /tmp
Filesystem      Size    Used   Avail Capacity iused ifree %iused  Mounted on
/dev/disk3s5   460Gi   406Gi    16Gi    97%    3.0M  169M    2%   /System/Volumes/Data
Filesystem   1024-blocks      Used Available Capacity iused     ifree %iused  Mounted on
/dev/disk3s5   482797652 426161060  16865120    97% 2990628 168651200    2%   /System/Volumes/Data
available_kib 16865120
```

### Closing disk measurement (post `/tmp/fhv1_1_id_v4/` cleanup)

```text
# repo /Users/hbauzan/treepwood/3hm-dimentional-fw
Filesystem      Size    Used   Avail Capacity iused ifree %iused  Mounted on
/dev/disk3s5   460Gi   406Gi    16Gi    97%    3.0M  169M    2%   /System/Volumes/Data
Filesystem   1024-blocks      Used Available Capacity iused     ifree %iused  Mounted on
/dev/disk3s5   482797652 426160792  16865388    97% 2990616 168653880    2%   /System/Volumes/Data
available_kib 16865388

# tmp /tmp
Filesystem      Size    Used   Avail Capacity iused ifree %iused  Mounted on
/dev/disk3s5   460Gi   406Gi    16Gi    97%    3.0M  169M    2%   /System/Volumes/Data
Filesystem   1024-blocks      Used Available Capacity iused     ifree %iused  Mounted on
/dev/disk3s5   482797652 426160792  16865388    97% 2990616 168653880    2%   /System/Volumes/Data
available_kib 16865388
```

Floor is 3145728 KiB. The closing `df -k` Available field is the measurement that has to clear that floor.

## 2. Impact of the three `S_struct` fixes (v3 vs v4)

Comparison uses published v3 `1B_base_tech` subtype literals from `reports/fhv1_1_id_v3_report.md` against v4 dual-axis cells (Eje 1 preset `1B_base_tech`). Rates are FRR on `IN_DOMAIN_VALID` and FAR on adversarial subtypes.
| domain | granularity | row | v4 kind | v4 rate | v3 kind | v3 rate |
| --- | --- | --- | --- | --- | --- | --- |
| `python` | `full_only` | `IN_DOMAIN_VALID` | `frr` | `0.21` | `far` | `0.12` |
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
| `python` | `clauses` | `IN_DOMAIN_VALID` | `frr` | `0.21` | `far` | `0.13` |
| `python` | `clauses` | `consulta_corta` | `absent` | `absent` | `absent` | `absent` |
| `python` | `clauses` | `sustitucion_ingredientes` | `absent` | `absent` | `absent` | `absent` |
| `python` | `clauses` | `panaderia_fermentacion` | `absent` | `absent` | `absent` | `absent` |
| `python` | `clauses` | `diagnostico_pasteleria_panaderia` | `absent` | `absent` | `absent` | `absent` |
| `python` | `clauses` | `short_idiom_query` | `frr` | `0.1` | `frr` | `0.25` |
| `python` | `clauses` | `code_snippet` | `frr` | `1.0` | `frr` | `0.5` |
| `python` | `clauses` | `extreme_short_punct` | `far` | `0.0` | `far` | `0.0` |
| `python` | `clauses` | `homoglyph_zwsp_fullwidth` | `far` | `0.0` | `far` | `0.0` |
| `python` | `clauses` | `long_context_flooding` | `far` | `0.0` | `far` | `0.0` |
| `python` | `clauses` | `prompt_injection_jailbreak` | `far` | `0.28` | `far` | `0.28` |
| `receta` | `full_only` | `IN_DOMAIN_VALID` | `frr` | `0.4` | `far` | `0.0` |
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
| `receta` | `clauses` | `IN_DOMAIN_VALID` | `frr` | `0.19` | `far` | `0.0` |
| `receta` | `clauses` | `consulta_corta` | `frr` | `0.1` | `frr` | `0.1` |
| `receta` | `clauses` | `sustitucion_ingredientes` | `frr` | `0.25` | `frr` | `0.125` |
| `receta` | `clauses` | `panaderia_fermentacion` | `frr` | `0.3` | `frr` | `0.3` |
| `receta` | `clauses` | `diagnostico_pasteleria_panaderia` | `frr` | `0.5` | `frr` | `0.5` |
| `receta` | `clauses` | `short_idiom_query` | `absent` | `absent` | `absent` | `absent` |
| `receta` | `clauses` | `code_snippet` | `absent` | `absent` | `absent` | `absent` |
| `receta` | `clauses` | `extreme_short_punct` | `far` | `0.0` | `far` | `0.1` |
| `receta` | `clauses` | `homoglyph_zwsp_fullwidth` | `far` | `0.0` | `far` | `0.0` |
| `receta` | `clauses` | `long_context_flooding` | `far` | `0.0` | `far` | `0.0` |
| `receta` | `clauses` | `prompt_injection_jailbreak` | `far` | `0.0` | `far` | `0.0` |
The three Slice-1 repairs (unidirectional channels, Latin letters out of `symbol_ratio`, rare-rate smoothing) are the v4 lexical path. Friendly-fire subtypes that remain high FRR after OOF thresholds are called out as open, not as a silent gain.

## 3. Ablation Eje 1 vs Eje 2 and 5-fold cal OOF

Eje 1 is the frozen `eje1_plus_struct` / `eje1_only` catalog under 5-fold cal OOF. Eje 2 appears as stored `dual_axis_and_cal_only` gate rows (`near_tag` / `near_prob`). The nested 5×5 means are `frozen.nested_oof`.
### python / full_only
Frozen `eje1_plus_struct|b=0.10|l=-|n=-|w=-` family `eje1_plus_struct` beta `0.1` w_f `null`. modal_column `1`. CAL_ONLY p10 F1 `0.7022222222222222`. 5x5 F1 mean `0.7189992166038128` std `0.002795922874350561`.
- Eje2 gate `near_tag` `p02` F1 `0.6666666666666666` is below the frozen CAL_ONLY p10 `0.7022222222222222`.
- Eje2 gate `near_tag` `p05` F1 `0.6724890829694323` is below the frozen CAL_ONLY p10 `0.7022222222222222`.
- Eje2 gate `near_tag` `p10` F1 `0.6755555555555556` is below the frozen CAL_ONLY p10 `0.7022222222222222`.
### python / clauses
Frozen `eje1_plus_struct|b=0.10|l=-|n=-|w=0.50` family `eje1_plus_struct` beta `0.1` w_f `0.5`. modal_column `25`. CAL_ONLY p10 F1 `0.7488151658767772`. 5x5 F1 mean `0.709096886010325` std `0.0158763312555823`.
- Eje2 gate `near_tag` `p02` F1 `0.7203389830508474` is below the frozen CAL_ONLY p10 `0.7488151658767772`.
- Eje2 gate `near_tag` `p05` F1 `0.7272727272727273` is below the frozen CAL_ONLY p10 `0.7488151658767772`.
- Eje2 gate `near_tag` `p10` F1 `0.7288888888888889` is below the frozen CAL_ONLY p10 `0.7488151658767772`.
### receta / full_only
Frozen `eje1_plus_struct|b=0.20|l=-|n=-|w=-` family `eje1_plus_struct` beta `0.2` w_f `null`. modal_column `2`. CAL_ONLY p10 F1 `0.6629834254143646`. 5x5 F1 mean `0.774468085106383` std `0.0`.
- Eje2 gate `near_tag` `p02` F1 `0.6263736263736264` is below the frozen CAL_ONLY p10 `0.6629834254143646`.
- Eje2 gate `near_tag` `p05` F1 `0.6145251396648045` is below the frozen CAL_ONLY p10 `0.6629834254143646`.
- Eje2 gate `near_tag` `p10` F1 `0.5714285714285714` is below the frozen CAL_ONLY p10 `0.6629834254143646`.
receta/full_only after 5-fold cal OOF: CAL_ONLY p10 F1 `0.6629834254143646`, 5x5 mean `0.774468085106383`. This is the honest operating point; it is not the in-sample v3 inflation figure.
### receta / clauses
Frozen `eje1_plus_struct|b=0.10|l=-|n=-|w=0.20` family `eje1_plus_struct` beta `0.1` w_f `0.2`. modal_column `1`. CAL_ONLY p10 F1 `0.8756756756756757`. 5x5 F1 mean `0.8828960879221736` std `0.01371560402362309`.
- Eje2 gate `near_tag` `p02` F1 `0.850828729281768` is below the frozen CAL_ONLY p10 `0.8756756756756757`.
- Eje2 gate `near_tag` `p05` F1 `0.8426966292134831` is below the frozen CAL_ONLY p10 `0.8756756756756757`.
- Eje2 gate `near_tag` `p10` F1 `0.8023255813953488` is below the frozen CAL_ONLY p10 `0.8756756756756757`.

## 4. `clause_cap` DoS and flooding latency

`clause_cap` ∈ {`null`, 16, 24, 32}. FAR/F1 on dilution/smuggle/flooding come from `*_clause_cap_eval.json`. Flooding wall-clock p50/p99 ms come from `flooding_latency_v4.json`.
### python
Eval recipe `eje1_only|b=0.00|l=-|n=-|w=-` w_f `0.35`.
| clause_cap | mean_selected_clauses | F1 | FRR | FAR | dilution_80_20 FAR | smuggle FAR | flooding FAR |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `null` | `4.3925` | `0.7125506072874493` | `0.12` | `0.19666666666666666` | `0.0` | `null` | `0.0` |
| `16` | `3.985` | `0.7228915662650602` | `0.1` | `0.19666666666666666` | `0.0` | `null` | `0.0` |
| `24` | `4.2525` | `0.7125506072874493` | `0.12` | `0.19666666666666666` | `0.0` | `null` | `0.0` |
| `32` | `4.3675` | `0.7125506072874493` | `0.12` | `0.19666666666666666` | `0.0` | `null` | `0.0` |
### receta
Eval recipe `eje1_only|b=0.00|l=-|n=-|w=-` w_f `0.35`.
| clause_cap | mean_selected_clauses | F1 | FRR | FAR | dilution_80_20 FAR | smuggle FAR | flooding FAR |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `null` | `4.475` | `0.8571428571428571` | `0.22` | `0.013333333333333334` | `0.0` | `0.2` | `0.0` |
| `16` | `4.09` | `0.8571428571428571` | `0.22` | `0.013333333333333334` | `0.0` | `0.2` | `0.0` |
| `24` | `4.4125` | `0.8571428571428571` | `0.22` | `0.013333333333333334` | `0.0` | `0.2` | `0.0` |
| `32` | `4.475` | `0.8571428571428571` | `0.22` | `0.013333333333333334` | `0.0` | `0.2` | `0.0` |
`PORTS_8080_8088_CLOSED` `true`.
### flooding latency ms — python
| cap | n_texts | repeats | p50_ms | p99_ms |
| --- | --- | --- | --- | --- |
| `uncapped` | `6` | `3` | `1553.8348339905497` | `1579.556607833365` |
| `cap_16` | `96` | `3` | `723.8832500006538` | `736.2045450130245` |
| `cap_24` | `144` | `3` | `1058.7415409972891` | `1080.1711608131882` |
| `cap_32` | `192` | `3` | `1422.4732920120005` | `1429.6869896660792` |
### flooding latency ms — receta
| cap | n_texts | repeats | p50_ms | p99_ms |
| --- | --- | --- | --- | --- |
| `uncapped` | `6` | `3` | `1434.1237090120558` | `1437.0449655107222` |
| `cap_16` | `96` | `3` | `787.702416011598` | `789.6439596492564` |
| `cap_24` | `144` | `3` | `1154.9850419978611` | `1165.5101606517565` |
| `cap_32` | `192` | `3` | `1533.837750001112` | `1541.1473249853589` |

## 5. `N_cal` volume curve

Volume curve `N_cal` from description-only (`n_cal=1`) through the stored ladder. Means and stds are literals from `*_n_cal_volume_curve.json`.
### python
description_only F1 `0.0` FRR `1.0` FAR `0.0` ROC-AUC `0.8234` threshold_relative_1b `0.6353441865160234`.
| N_cal | n_seeds | p10 F1 mean | p10 F1 std | ROC-AUC mean | ROC-AUC std | FRR mean | FAR mean | threshold_stability_std |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `1` | `5` | `0.0` | `0.0` | `0.77456` | `0.059897108073391665` | `1.0` | `0.0` | `0.009638751707908351` |
| `5` | `5` | `0.0039603960396039604` | `0.008855714762375405` | `0.8765666666666668` | `0.021228296105800785` | `0.998` | `0.0` | `0.0064517285376736525` |
| `10` | `5` | `0.087688296305837` | `0.071779349955861` | `0.8866533333333333` | `0.014851198978907753` | `0.952` | `0.002666666666666667` | `0.005100192717135912` |
| `25` | `5` | `0.6378243026103521` | `0.04346618968041802` | `0.8988200000000001` | `0.006356737458092099` | `0.44000000000000006` | `0.06333333333333332` | `0.003016176317997699` |
| `50` | `5` | `0.6825094741603395` | `0.022905522063274987` | `0.8971` | `0.010124969135755372` | `0.312` | `0.10933333333333332` | `0.001979821141010002` |
| `100` | `5` | `0.7017254293774486` | `0.009329171253619822` | `0.9003733333333332` | `0.0010296709290944566` | `0.238` | `0.1366666666666667` | `0.0017314760901708341` |
| `200` | `5` | `0.6872577524160774` | `0.014164374385437141` | `0.9008666666666667` | `0.004707145867956774` | `0.21000000000000002` | `0.16999999999999998` | `0.0022246017258342656` |
| `400` | `5` | `0.684886931646952` | `0.001559907293850951` | `0.8989733333333334` | `0.0009283797115883479` | `0.198` | `0.18` | `0.0008931592197615376` |
| `600` | `1` | `0.6810344827586207` | `0.0` | `0.8993666666666668` | `0.0` | `0.21` | `0.17666666666666667` | `0.0` |
| from_n | to_n | delta_f1 | delta_auc | delta_frr | delta_far |
| --- | --- | --- | --- | --- | --- |
| `1` | `5` | `0.0039603960396039604` | `0.1020066666666668` | `-0.0020000000000000018` | `0.0` |
| `5` | `10` | `0.08372790026623303` | `0.010086666666666466` | `-0.04600000000000004` | `0.002666666666666667` |
| `10` | `25` | `0.5501360063045151` | `0.01216666666666677` | `-0.5119999999999999` | `0.06066666666666666` |
| `25` | `50` | `0.04468517154998741` | `-0.0017200000000000548` | `-0.12800000000000006` | `0.046` |
| `50` | `100` | `0.01921595521710917` | `0.0032733333333332393` | `-0.07400000000000001` | `0.027333333333333362` |
| `100` | `200` | `-0.01446767696137119` | `0.0004933333333334566` | `-0.02799999999999997` | `0.0333333333333333` |
| `200` | `400` | `-0.0023708207691254257` | `-0.0018933333333333024` | `-0.01200000000000001` | `0.010000000000000009` |
| `400` | `600` | `-0.0038524488883313612` | `0.00039333333333335663` | `0.011999999999999983` | `-0.003333333333333327` |
### receta
description_only F1 `0.0` FRR `1.0` FAR `0.0` ROC-AUC `0.8683000000000001` threshold_relative_1b `0.6381267414242447`.
| N_cal | n_seeds | p10 F1 mean | p10 F1 std | ROC-AUC mean | ROC-AUC std | FRR mean | FAR mean | threshold_stability_std |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `1` | `5` | `0.0` | `0.0` | `0.8844733333333332` | `0.023837766487469263` | `1.0` | `0.0` | `0.005061792252602486` |
| `5` | `5` | `0.007920792079207921` | `0.010845991237726062` | `0.9137066666666668` | `0.011334617574296756` | `0.9960000000000001` | `0.0` | `0.00463154878206502` |
| `10` | `5` | `0.2593251593856312` | `0.14179756646002406` | `0.91654` | `0.006121610173076226` | `0.8380000000000001` | `0.012` | `0.005429256128473947` |
| `25` | `5` | `0.4488790583271577` | `0.04976600927068722` | `0.9178466666666667` | `0.006116307891385278` | `0.6839999999999999` | `0.028666666666666667` | `0.0029285598889575927` |
| `50` | `5` | `0.5484166425634835` | `0.057277489326590124` | `0.9157333333333334` | `0.004022920442774031` | `0.55` | `0.06133333333333333` | `0.004643594056430172` |
| `100` | `5` | `0.616779853602024` | `0.021105841356713142` | `0.9170733333333334` | `0.0028020230786581974` | `0.45999999999999996` | `0.07` | `0.0022029005185644195` |
| `200` | `5` | `0.6065132635346118` | `0.01732310588949293` | `0.9164933333333334` | `0.0006529420597061804` | `0.47400000000000003` | `0.06933333333333333` | `0.0019729513046468413` |
| `400` | `5` | `0.6330989961913914` | `0.00998287643271455` | `0.9169866666666667` | `0.0003826806036950556` | `0.43200000000000005` | `0.07533333333333334` | `0.001001512984604985` |
| `600` | `1` | `0.6298342541436464` | `0.0` | `0.917` | `0.0` | `0.43` | `0.08` | `0.0` |
| from_n | to_n | delta_f1 | delta_auc | delta_frr | delta_far |
| --- | --- | --- | --- | --- | --- |
| `1` | `5` | `0.007920792079207921` | `0.029233333333333555` | `-0.0039999999999998925` | `0.0` |
| `5` | `10` | `0.2514043673064233` | `0.0028333333333332433` | `-0.15800000000000003` | `0.012` |
| `10` | `25` | `0.18955389894152647` | `0.0013066666666666782` | `-0.15400000000000014` | `0.016666666666666666` |
| `25` | `50` | `0.09953758423632586` | `-0.0021133333333333004` | `-0.1339999999999999` | `0.03266666666666666` |
| `50` | `100` | `0.06836321103854048` | `0.0013400000000000079` | `-0.09000000000000008` | `0.008666666666666677` |
| `100` | `200` | `-0.010266590067412262` | `-0.0005800000000000249` | `0.014000000000000068` | `-0.0006666666666666765` |
| `200` | `400` | `0.02658573265677966` | `0.0004933333333333456` | `-0.04199999999999998` | `0.006000000000000005` |
| `400` | `600` | `-0.003264742047745073` | `1.333333333330966e-05` | `-0.0020000000000000573` | `0.004666666666666666` |
### Recommendation on 800–1,000
- `python` marginal `400`→`600` delta_f1 `-0.0038524488883313612` delta_auc `0.00039333333333335663`.
- `receta` marginal `400`→`600` delta_f1 `-0.003264742047745073` delta_auc `1.333333333330966e-05`.
On both domains the 400→600 marginal F1 is near zero or negative. The ladder has plateaued for F1 gain by `N_cal≈100–400`. Extending to 800–1,000 is not justified for headline F1 on this holdout; revisit only inside `TASK-016` if cold domains need more calibration volume.

## 6. Master tables

CAL_ONLY p05/p10/p15, nested 5×5, and `[ORACLE_UPPER_BOUND]` are copied from dual-axis cells. Manifest bootstrap contract: n `1000`, seed `0`, `refits_thresholds` `true`.
### python / full_only
catalog_size `12`, cal_oof `true`, dir_variant `dir1024_sig_sep`.
CAL_ONLY on the frozen recipe:
| tag | F1 | FRR | FAR | precision | recall | threshold | ROC-AUC | tp | fn | tn | fp |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `p05` | `0.6923076923076923` | `0.1` | `0.23333333333333334` | `0.5625` | `0.9` | `0.5151544676877559` | `0.9162999999999999` | `90` | `10` | `230` | `70` |
| `p10` | `0.7022222222222222` | `0.21` | `0.15333333333333332` | `0.632` | `0.79` | `0.5272183609200629` | `0.9162999999999999` | `79` | `21` | `254` | `46` |
| `p15` | `0.7358490566037735` | `0.22` | `0.11333333333333333` | `0.6964285714285714` | `0.78` | `0.5322883998048449` | `0.9162999999999999` | `78` | `22` | `266` | `34` |
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
[ORACLE_UPPER_BOUND] source `seed0_mixed_scores_fit_on_all_holdout_labels` F1 `0.7428571428571429` FRR `0.22` FAR `0.10666666666666667` threshold `0.5344316856798338`.
### python / clauses
catalog_size `36`, cal_oof `true`, dir_variant `dir1024_sig_sep`.
CAL_ONLY on the frozen recipe:
| tag | F1 | FRR | FAR | precision | recall | threshold | ROC-AUC | tp | fn | tn | fp |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `p05` | `0.7058823529411765` | `0.1` | `0.21666666666666667` | `0.5806451612903226` | `0.9` | `0.4901021271687567` | `0.9171666666666667` | `90` | `10` | `235` | `65` |
| `p10` | `0.7488151658767772` | `0.21` | `0.10666666666666667` | `0.7117117117117117` | `0.79` | `0.5023519096786156` | `0.9171666666666667` | `79` | `21` | `268` | `32` |
| `p15` | `0.77` | `0.23` | `0.07666666666666666` | `0.77` | `0.77` | `0.507337824034455` | `0.9171666666666667` | `77` | `23` | `277` | `23` |
nested 5x5:
| metric | mean | std |
| --- | --- | --- |
| `f1` | `0.709096886010325` | `0.0158763312555823` |
| `frr` | `0.28` | `0.04000000000000001` |
| `far` | `0.10333333333333332` | `0.0158113883008419` |
| `roc_auc` | `0.8720266666666665` | `0.007235537298639322` |
| seed | F1 | FRR | FAR | ROC-AUC |
| --- | --- | --- | --- | --- |
| `0` | `0.7136150234741784` | `0.24` | `0.12333333333333334` | `0.8810333333333333` |
| `1` | `0.7342995169082126` | `0.24` | `0.10333333333333333` | `0.8783333333333334` |
| `2` | `0.7046632124352331` | `0.32` | `0.08333333333333333` | `0.8653666666666666` |
| `3` | `0.6938775510204082` | `0.32` | `0.09333333333333334` | `0.8695333333333333` |
| `4` | `0.6990291262135923` | `0.28` | `0.11333333333333333` | `0.8658666666666666` |
[ORACLE_UPPER_BOUND] source `seed0_mixed_scores_fit_on_all_holdout_labels` F1 `0.7487179487179487` FRR `0.27` FAR `0.07333333333333333` threshold `0.5137667068248652`.
### receta / full_only
catalog_size `12`, cal_oof `true`, dir_variant `dir1024_sig_sep`.
CAL_ONLY on the frozen recipe:
| tag | F1 | FRR | FAR | precision | recall | threshold | ROC-AUC | tp | fn | tn | fp |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `p05` | `0.7227722772277227` | `0.27` | `0.09666666666666666` | `0.7156862745098039` | `0.73` | `0.533463934181979` | `0.9286666666666666` | `73` | `27` | `271` | `29` |
| `p10` | `0.6629834254143646` | `0.4` | `0.07` | `0.7407407407407407` | `0.6` | `0.5466213497097229` | `0.9286666666666666` | `60` | `40` | `279` | `21` |
| `p15` | `0.593939393939394` | `0.51` | `0.05333333333333334` | `0.7538461538461538` | `0.49` | `0.5530494307135471` | `0.9286666666666666` | `49` | `51` | `284` | `16` |
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
[ORACLE_UPPER_BOUND] source `seed0_mixed_scores_fit_on_all_holdout_labels` F1 `0.7796610169491526` FRR `0.08` FAR `0.14666666666666667` threshold `0.5122363638574108`.
### receta / clauses
catalog_size `36`, cal_oof `true`, dir_variant `dir1024_sig_sep`.
CAL_ONLY on the frozen recipe:
| tag | F1 | FRR | FAR | precision | recall | threshold | ROC-AUC | tp | fn | tn | fp |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `p05` | `0.8725490196078431` | `0.11` | `0.05` | `0.8557692307692307` | `0.89` | `0.48613569835697995` | `0.9830333333333333` | `89` | `11` | `285` | `15` |
| `p10` | `0.8756756756756757` | `0.19` | `0.013333333333333334` | `0.9529411764705882` | `0.81` | `0.4935387438058225` | `0.9830333333333333` | `81` | `19` | `296` | `4` |
| `p15` | `0.8361581920903954` | `0.26` | `0.01` | `0.961038961038961` | `0.74` | `0.4976131354291359` | `0.9830333333333333` | `74` | `26` | `297` | `3` |
nested 5x5:
| metric | mean | std |
| --- | --- | --- |
| `f1` | `0.8828960879221736` | `0.01371560402362309` |
| `frr` | `0.126` | `0.0151657508881031` |
| `far` | `0.03533333333333334` | `0.008692269873603532` |
| `roc_auc` | `0.9784666666666666` | `0.002733841416192481` |
| seed | F1 | FRR | FAR | ROC-AUC |
| --- | --- | --- | --- | --- |
| `0` | `0.8923076923076924` | `0.13` | `0.02666666666666667` | `0.9810333333333334` |
| `1` | `0.8768472906403941` | `0.11` | `0.04666666666666667` | `0.9774666666666666` |
| `2` | `0.8629441624365483` | `0.15` | `0.04` | `0.9743999999999999` |
| `3` | `0.8844221105527639` | `0.12` | `0.03666666666666667` | `0.9785666666666667` |
| `4` | `0.8979591836734694` | `0.12` | `0.02666666666666667` | `0.9808666666666668` |
[ORACLE_UPPER_BOUND] source `seed0_mixed_scores_fit_on_all_holdout_labels` F1 `0.9035532994923858` FRR `0.11` FAR `0.02666666666666667` threshold `0.4876411650997549`.
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
| `python` | `clauses` | `asyncio_concurrency` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.125` |
| `python` | `clauses` | `code_snippet` | `IN_DOMAIN_VALID` | `6` | `frr` | `1.0` |
| `python` | `clauses` | `data_structures_oop` | `IN_DOMAIN_VALID` | `6` | `frr` | `0.3333333333333333` |
| `python` | `clauses` | `delimiter_escape` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.25` |
| `python` | `clauses` | `dilution_20_80` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `python` | `clauses` | `dilution_50_50` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `python` | `clauses` | `dilution_80_20` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `python` | `clauses` | `extreme_high_entropy_gibberish` | `ADVERSARIAL_FUZZING` | `7` | `far` | `0.0` |
| `python` | `clauses` | `extreme_short_punct` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.0` |
| `python` | `clauses` | `homoglyph_zwsp_fullwidth` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `python` | `clauses` | `keyword_stuffing_hidden_instruction` | `ADVERSARIAL_FUZZING` | `6` | `far` | `0.3333333333333333` |
| `python` | `clauses` | `long_architecture_guide` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.2` |
| `python` | `clauses` | `long_context_flooding` | `ADVERSARIAL_FUZZING` | `6` | `far` | `0.0` |
| `python` | `clauses` | `long_debugging_walkthrough` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.5` |
| `python` | `clauses` | `near_ood_neighbor` | `HYBRID_BOUNDARY` | `12` | `far` | `0.6666666666666666` |
| `python` | `clauses` | `obfuscation_base64` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `python` | `clauses` | `obfuscation_hex_rot13_leet` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.1` |
| `python` | `clauses` | `ood_architecture_music_hardware` | `OUT_OF_DOMAIN_BENIGN` | `8` | `far` | `0.125` |
| `python` | `clauses` | `ood_astronomy_geology` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `python` | `clauses` | `ood_finance_law` | `OUT_OF_DOMAIN_BENIGN` | `12` | `far` | `0.0` |
| `python` | `clauses` | `ood_history_literature_philosophy` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `python` | `clauses` | `ood_medicine_biology` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `python` | `clauses` | `ood_suite2_clinc` | `OUT_OF_DOMAIN_BENIGN` | `40` | `far` | `0.0` |
| `python` | `clauses` | `ood_travel_weather_sports` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `python` | `clauses` | `packaging_env` | `IN_DOMAIN_VALID` | `6` | `frr` | `0.0` |
| `python` | `clauses` | `pivot_middle` | `HYBRID_BOUNDARY` | `10` | `far` | `0.4` |
| `python` | `clauses` | `pivot_prefix` | `HYBRID_BOUNDARY` | `10` | `far` | `0.2` |
| `python` | `clauses` | `pivot_suffix` | `HYBRID_BOUNDARY` | `10` | `far` | `0.1` |
| `python` | `clauses` | `polarity_flip_indirect` | `HYBRID_BOUNDARY` | `8` | `far` | `0.25` |
| `python` | `clauses` | `prompt_injection_jailbreak` | `ADVERSARIAL_FUZZING` | `25` | `far` | `0.28` |
| `python` | `clauses` | `pytest_testing` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.0` |
| `python` | `clauses` | `short_idiom_query` | `IN_DOMAIN_VALID` | `20` | `frr` | `0.1` |
| `python` | `clauses` | `smuggle_comment_docstring` | `HYBRID_BOUNDARY` | `10` | `far` | `0.1` |
| `python` | `clauses` | `smuggle_json_yaml` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `python` | `clauses` | `stdlib_idiom` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.1` |
| `python` | `clauses` | `traceback_debugging` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.125` |
| `python` | `clauses` | `typing_protocol` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.125` |
| `receta` | `full_only` | `cocina_regional` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.375` |
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
| `receta` | `full_only` | `smuggle_recipe_footnote` | `HYBRID_BOUNDARY` | `10` | `far` | `0.6` |
| `receta` | `full_only` | `sustitucion_ingredientes` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.25` |
| `receta` | `full_only` | `tecnica_culinaria` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.5` |
| `receta` | `full_only` | `temperatura_tiempos` | `IN_DOMAIN_VALID` | `6` | `frr` | `0.8333333333333334` |
| `receta` | `clauses` | `cocina_regional` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.5` |
| `receta` | `clauses` | `consulta_corta` | `IN_DOMAIN_VALID` | `20` | `frr` | `0.1` |
| `receta` | `clauses` | `delimiter_escape` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `receta` | `clauses` | `diagnostico_pasteleria_panaderia` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.5` |
| `receta` | `clauses` | `dilution_20_80` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `receta` | `clauses` | `dilution_50_50` | `HYBRID_BOUNDARY` | `10` | `far` | `0.1` |
| `receta` | `clauses` | `dilution_80_20` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `receta` | `clauses` | `extreme_high_entropy_gibberish` | `ADVERSARIAL_FUZZING` | `7` | `far` | `0.0` |
| `receta` | `clauses` | `extreme_short_punct` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.0` |
| `receta` | `clauses` | `guia_culinaria_larga` | `IN_DOMAIN_VALID` | `12` | `frr` | `0.08333333333333333` |
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
| `receta` | `clauses` | `ood_suite2_es_oos` | `OUT_OF_DOMAIN_BENIGN` | `20` | `far` | `0.05` |
| `receta` | `clauses` | `ood_viajes_clima_deportes` | `OUT_OF_DOMAIN_BENIGN` | `12` | `far` | `0.0` |
| `receta` | `clauses` | `panaderia_fermentacion` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.3` |
| `receta` | `clauses` | `pivot_middle` | `HYBRID_BOUNDARY` | `10` | `far` | `0.1` |
| `receta` | `clauses` | `pivot_prefix` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `receta` | `clauses` | `pivot_suffix` | `HYBRID_BOUNDARY` | `10` | `far` | `0.1` |
| `receta` | `clauses` | `polarity_flip_indirect` | `HYBRID_BOUNDARY` | `8` | `far` | `0.0` |
| `receta` | `clauses` | `prompt_injection_jailbreak` | `ADVERSARIAL_FUZZING` | `25` | `far` | `0.0` |
| `receta` | `clauses` | `receta_completa` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.0` |
| `receta` | `clauses` | `salsas_emulsiones` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.125` |
| `receta` | `clauses` | `smuggle_json_yaml` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `receta` | `clauses` | `smuggle_recipe_footnote` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `receta` | `clauses` | `sustitucion_ingredientes` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.25` |
| `receta` | `clauses` | `tecnica_culinaria` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.1` |
| `receta` | `clauses` | `temperatura_tiempos` | `IN_DOMAIN_VALID` | `6` | `frr` | `0.16666666666666666` |
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
- receta/full_only CAL_ONLY p10 F1 `0.6629834254143646` after honest 5-fold OOF; friendly-fire subtypes (`consulta_corta`, `panaderia_fermentacion`) remain non-zero FRR.
- Volume curve has plateaued for F1; 800–1,000 is not a forced next step for gain.
- Scorer stays **OFF** in production for `TASK-015`.
Research serialization of the frozen offline recipe may be discussed after human review, but that is not a production enablement GO.

