# `fhv1_1` I+D v3 — full-1024D directional dials and lexical guardrail

**Task**: `TASK-014`
**Branch**: `feat/fhv1-1-id-v3-full1024d-and-lexical-guard`
**Dtype**: `float64`. **normalize**: `true`. **mode**: `v3`.

Numbers in the tables are literals copied from `/tmp/fhv1_1_id_v3` JSON. A missing key aborts the generator.

## 0. Executive

Headline label on every cell is `nested_modal_recipe_cal_only_p10`. The manifest field is `nested_modal_recipe_cal_only_p10` when that is the stored label.
Primary rule `document_level_CAL_ONLY`. `bootstrap.refits_thresholds` is `true`. Resamples `1000`, seed `0`, dim `1024`.
TASK-011 m0 F1 is the published column in `reports/fhv1_1_xray_and_replay_report.md`. It is not a field of this JSON, so the table does not repeat it. TASK-012 and TASK-013 F1 values below are the `bootstrap.frozen_f1` literals stored in each cell.
Upper-bound rows that were fit on holdout labels are outside this table. They are not columns here.
| domain | granularity | preset | family | CAL_ONLY p10 F1 | 5x5 F1 mean | 5x5 F1 std | ROC-AUC | OOD FAR | adversarial FAR | hybrid FAR | near-OOD FAR | S_struct p50 us | S_struct p99 us | TASK-012 F1 | TASK-013 CAL_ONLY p10 F1 | TASK-013 5x5 F1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `python` | `full_only` | `1B_base_tech` | `dir1024_sig_sep` | `0.728110599078341` | `0.7125885632538125` | `0.004458970520057445` | `0.9179666666666666` | `0.0` | `0.11` | `0.27` | `0.3333333333333333` | `19.125` | `194.42477999999988` | `0.5606` | `0.6338028169014085` | `0.6277631674623869` |
| `python` | `clauses` | `1B_base_tech` | `dir1024_sig_sep` | `0.8159203980099502` | `0.7804607956366759` | `0.006974253924474721` | `0.9500333333333334` | `0.0` | `0.09` | `0.1` | `0.5` | `19.125` | `194.42477999999988` | `0.6723` | `0.6714801444043321` | `0.6922652099467881` |
| `python` | `full_only` | `1B_base_tech_noise` | `dir1024_sig_sep` | `0.6991150442477876` | `0.6981847084656871` | `0.010828163080099068` | `0.9050666666666667` | `0.0` | `0.13` | `0.34` | `0.3333333333333333` | `19.125` | `194.42477999999988` | `0.5606` | `0.6338028169014085` | `0.6277631674623869` |
| `python` | `clauses` | `1B_base_tech_noise` | `dir1024_clip_polboost` | `0.8118811881188119` | `0.7648457678409377` | `0.014797125814703481` | `0.9477` | `0.01` | `0.09` | `0.1` | `0.5833333333333334` | `19.125` | `194.42477999999988` | `0.6723` | `0.6714801444043321` | `0.6922652099467881` |
| `python` | `full_only` | `1B_full` | `dir1024_sig_sep` | `0.6956521739130435` | `0.7210721319540588` | `0.01229710364155884` | `0.909` | `0.0` | `0.12` | `0.38` | `0.4166666666666667` | `19.125` | `194.42477999999988` | `0.5606` | `0.6338028169014085` | `0.6277631674623869` |
| `python` | `clauses` | `1B_full` | `dir1024_sig_sep` | `0.8133971291866029` | `0.7619373229937537` | `0.007362726152493284` | `0.9428666666666666` | `0.01` | `0.11` | `0.12` | `0.5833333333333334` | `19.125` | `194.42477999999988` | `0.6723` | `0.6714801444043321` | `0.6922652099467881` |
| `python` | `full_only` | `1B_full_v3` | `dir1024_sig_sep` | `0.6583333333333333` | `0.6883696601962811` | `0.009839488996404246` | `0.9038333333333333` | `0.0` | `0.18` | `0.43` | `0.4166666666666667` | `19.125` | `194.42477999999988` | `0.5606` | `0.6338028169014085` | `0.6277631674623869` |
| `python` | `clauses` | `1B_full_v3` | `dir1024_sig_sep2` | `0.7941176470588235` | `0.7920621458570938` | `0.011215522604976116` | `0.9444666666666667` | `0.01` | `0.1` | `0.12` | `0.5833333333333334` | `19.125` | `194.42477999999988` | `0.6723` | `0.6714801444043321` | `0.6922652099467881` |
| `receta` | `full_only` | `1B_base_tech` | `polarity_v2_subset` | `0.7403846153846154` | `0.742755666816479` | `0.009854602771124779` | `0.9178` | `0.0` | `0.01` | `0.3` | `0.0` | `20.625` | `200.49970000000062` | `0.6975` | `0.7403846153846154` | `0.7513565819177839` |
| `receta` | `clauses` | `1B_base_tech` | `dir1024_sig_sep` | `0.8783068783068783` | `0.8632849426609299` | `0.01703571400939901` | `0.9792000000000001` | `0.01` | `0.01` | `0.04` | `0.0` | `20.625` | `200.49970000000062` | `0.7257` | `0.7981220657276995` | `0.7845709402740869` |
| `receta` | `full_only` | `1B_base_tech_noise` | `dir1024_clip_polboost` | `0.6136363636363636` | `0.7449303201506592` | `0.010997248911401034` | `0.9180333333333333` | `0.0` | `0.0` | `0.22` | `0.0` | `20.625` | `200.49970000000062` | `0.6975` | `0.7403846153846154` | `0.7513565819177839` |
| `receta` | `clauses` | `1B_base_tech_noise` | `dir1024_sig_sep` | `0.8648648648648649` | `0.8708893003272469` | `0.0106366386154175` | `0.9802333333333333` | `0.01` | `0.0` | `0.04` | `0.0` | `20.625` | `200.49970000000062` | `0.7257` | `0.7981220657276995` | `0.7845709402740869` |
| `receta` | `full_only` | `1B_full` | `dir1024_clip_polboost` | `0.6222222222222222` | `0.7588019823313941` | `0.009249697573858396` | `0.9164666666666667` | `0.0` | `0.0` | `0.24` | `0.0` | `20.625` | `200.49970000000062` | `0.6975` | `0.7403846153846154` | `0.7513565819177839` |
| `receta` | `clauses` | `1B_full` | `dir1024_sig_sep` | `0.8829787234042553` | `0.8779304506282788` | `0.009681912428697568` | `0.9791666666666666` | `0.01` | `0.0` | `0.04` | `0.0` | `20.625` | `200.49970000000062` | `0.7257` | `0.7981220657276995` | `0.7845709402740869` |
| `receta` | `full_only` | `1B_full_v3` | `polarity_v2_subset` | `0.7164179104477612` | `0.7453808183346586` | `0.00666037412425954` | `0.9227666666666666` | `0.0` | `0.0` | `0.29` | `0.0` | `20.625` | `200.49970000000062` | `0.6975` | `0.7403846153846154` | `0.7513565819177839` |
| `receta` | `clauses` | `1B_full_v3` | `dir1024_sig_sep` | `0.8770053475935828` | `0.8602960108810551` | `0.004088619685136745` | `0.9802333333333333` | `0.01` | `0.0` | `0.04` | `0.0` | `20.625` | `200.49970000000062` | `0.7257` | `0.7981220657276995` | `0.7845709402740869` |
Stored headline recipes:
- `python` `full_only` `1B_base_tech` `dir1024_sig_sep|identity|a=0.00|g=-|gamma|b=0.00|y=0.10|r=full_doc|w=-` CAL_ONLY p10 F1 `0.728110599078341` is above the frozen TASK-013 F_polarity CAL_ONLY p10 `0.6338028169014085`. 5x5 F1 `0.7125885632538125` is above the frozen TASK-013 5x5 F1 `0.6277631674623869`.
- `python` `clauses` `1B_base_tech` `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.20|y=-|r=full_doc|w=0.50` CAL_ONLY p10 F1 `0.8159203980099502` is above the frozen TASK-013 F_polarity CAL_ONLY p10 `0.6714801444043321`. 5x5 F1 `0.7804607956366759` is above the frozen TASK-013 5x5 F1 `0.6922652099467881`.
- `python` `full_only` `1B_base_tech_noise` `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.05|y=-|r=full_doc|w=-` CAL_ONLY p10 F1 `0.6991150442477876` is above the frozen TASK-013 F_polarity CAL_ONLY p10 `0.6338028169014085`. 5x5 F1 `0.6981847084656871` is above the frozen TASK-013 5x5 F1 `0.6277631674623869`.
- `python` `clauses` `1B_base_tech_noise` `dir1024_clip_polboost|multiplicative|a=0.05|g=tail_p5|beta|b=0.30|y=-|r=full_doc|w=0.35` CAL_ONLY p10 F1 `0.8118811881188119` is above the frozen TASK-013 F_polarity CAL_ONLY p10 `0.6714801444043321`. 5x5 F1 `0.7648457678409377` is above the frozen TASK-013 5x5 F1 `0.6922652099467881`.
- `python` `full_only` `1B_full` `dir1024_sig_sep|additive|a=0.05|g=f2_l2|beta|b=0.20|y=-|r=full_doc|w=-` CAL_ONLY p10 F1 `0.6956521739130435` is above the frozen TASK-013 F_polarity CAL_ONLY p10 `0.6338028169014085`. 5x5 F1 `0.7210721319540588` is above the frozen TASK-013 5x5 F1 `0.6277631674623869`.
- `python` `clauses` `1B_full` `dir1024_sig_sep|multiplicative|a=0.20|g=tail_p5|gamma|b=0.00|y=0.10|r=full_doc|w=0.35` CAL_ONLY p10 F1 `0.8133971291866029` is above the frozen TASK-013 F_polarity CAL_ONLY p10 `0.6714801444043321`. 5x5 F1 `0.7619373229937537` is above the frozen TASK-013 5x5 F1 `0.6922652099467881`.
- `python` `full_only` `1B_full_v3` `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.10|y=-|r=full_doc|w=-` CAL_ONLY p10 F1 `0.6583333333333333` is above the frozen TASK-013 F_polarity CAL_ONLY p10 `0.6338028169014085`. 5x5 F1 `0.6883696601962811` is above the frozen TASK-013 5x5 F1 `0.6277631674623869`.
- `python` `clauses` `1B_full_v3` `dir1024_sig_sep2|multiplicative|a=0.10|g=f2_l2|gamma|b=0.00|y=0.10|r=full_doc|w=0.35` CAL_ONLY p10 F1 `0.7941176470588235` is above the frozen TASK-013 F_polarity CAL_ONLY p10 `0.6714801444043321`. 5x5 F1 `0.7920621458570938` is above the frozen TASK-013 5x5 F1 `0.6922652099467881`.
- `receta` `full_only` `1B_base_tech` `polarity_v2_subset|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` CAL_ONLY p10 F1 `0.7403846153846154` is tied with the frozen TASK-013 F_polarity CAL_ONLY p10 `0.7403846153846154`. 5x5 F1 `0.742755666816479` is below the frozen TASK-013 5x5 F1 `0.7513565819177839`.
- `receta` `clauses` `1B_base_tech` `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` CAL_ONLY p10 F1 `0.8783068783068783` is above the frozen TASK-013 F_polarity CAL_ONLY p10 `0.7981220657276995`. 5x5 F1 `0.8632849426609299` is above the frozen TASK-013 5x5 F1 `0.7845709402740869`.
- `receta` `full_only` `1B_base_tech_noise` `dir1024_clip_polboost|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` CAL_ONLY p10 F1 `0.6136363636363636` is below the frozen TASK-013 F_polarity CAL_ONLY p10 `0.7403846153846154`. 5x5 F1 `0.7449303201506592` is below the frozen TASK-013 5x5 F1 `0.7513565819177839`.
- `receta` `clauses` `1B_base_tech_noise` `dir1024_sig_sep|additive|a=0.10|g=tail_p10|beta|b=0.00|y=-|r=full_doc|w=0.20` CAL_ONLY p10 F1 `0.8648648648648649` is above the frozen TASK-013 F_polarity CAL_ONLY p10 `0.7981220657276995`. 5x5 F1 `0.8708893003272469` is above the frozen TASK-013 5x5 F1 `0.7845709402740869`.
- `receta` `full_only` `1B_full` `dir1024_clip_polboost|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` CAL_ONLY p10 F1 `0.6222222222222222` is below the frozen TASK-013 F_polarity CAL_ONLY p10 `0.7403846153846154`. 5x5 F1 `0.7588019823313941` is above the frozen TASK-013 5x5 F1 `0.7513565819177839`.
- `receta` `clauses` `1B_full` `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` CAL_ONLY p10 F1 `0.8829787234042553` is above the frozen TASK-013 F_polarity CAL_ONLY p10 `0.7981220657276995`. 5x5 F1 `0.8779304506282788` is above the frozen TASK-013 5x5 F1 `0.7845709402740869`.
- `receta` `full_only` `1B_full_v3` `polarity_v2_subset|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` CAL_ONLY p10 F1 `0.7164179104477612` is below the frozen TASK-013 F_polarity CAL_ONLY p10 `0.7403846153846154`. 5x5 F1 `0.7453808183346586` is below the frozen TASK-013 5x5 F1 `0.7513565819177839`.
- `receta` `clauses` `1B_full_v3` `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` CAL_ONLY p10 F1 `0.8770053475935828` is above the frozen TASK-013 F_polarity CAL_ONLY p10 `0.7981220657276995`. 5x5 F1 `0.8602960108810551` is above the frozen TASK-013 5x5 F1 `0.7845709402740869`.
What moved, using only stored literals:
four python/full_only headline(s) above the frozen TASK-013 F_polarity CAL_ONLY p10: `1B_base_tech`, `1B_base_tech_noise`, `1B_full`, `1B_full_v3`.
four python/clauses headline(s) above the frozen TASK-013 F_polarity CAL_ONLY p10: `1B_base_tech`, `1B_base_tech_noise`, `1B_full`, `1B_full_v3`.
one receta/full_only headline(s) equal the frozen TASK-013 F_polarity CAL_ONLY p10: `1B_base_tech`.
three receta/full_only headline(s) below the frozen TASK-013 F_polarity CAL_ONLY p10: `1B_base_tech_noise`, `1B_full`, `1B_full_v3`.
four receta/clauses headline(s) above the frozen TASK-013 F_polarity CAL_ONLY p10: `1B_base_tech`, `1B_base_tech_noise`, `1B_full`, `1B_full_v3`.
two receta/full_only cell(s) selected `polarity_v2_subset` rather than a dir1024 family: `1B_base_tech`, `1B_full_v3`.
five python/full_only alpha=0 rows are below the frozen TASK-013 F_polarity CAL_ONLY p10. That set includes `base_repaired` and, where the stored row is below, `polarity_v2_subset`. A nested headline that is above that frozen value stays above it; the alpha=0 row is a different stored score.
- `1B_base_tech` `polarity_v2_subset` w_f `null` CAL_ONLY p10 F1 `0.6044776119402985` is below `0.6338028169014085`.
- `1B_base_tech` `base_repaired` w_f `null` CAL_ONLY p10 F1 `0.5547445255474452` is below `0.6338028169014085`.
- `1B_base_tech_noise` `base_repaired` w_f `null` CAL_ONLY p10 F1 `0.5401459854014599` is below `0.6338028169014085`.
- `1B_full` `base_repaired` w_f `null` CAL_ONLY p10 F1 `0.5591397849462365` is below `0.6338028169014085`.
- `1B_full_v3` `base_repaired` w_f `null` CAL_ONLY p10 F1 `0.5576208178438662` is below `0.6338028169014085`.
On those receta/full_only cells the nested selector did not pick a dir1024 family. The stored headline is the polarity subset score, so a dir1024 gain is not what this run selected.

## 1. Phase-0 and disk

Phase-0 below is quoted from `roadmap/fhv1-1-id-v3-full1024d-and-lexical-guard.roadmap.md` section 1. It is the audit that already ran. This generator does not replace those figures with a second audit.

```text
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
```

### Disk before scratch removal

```text
# repo /Users/hbauzan/treepwood/3hm-dimentional-fw
Filesystem      Size    Used   Avail Capacity iused ifree %iused  Mounted on
/dev/disk3s5   460Gi   411Gi    12Gi    98%    2.9M  131M    2%   /System/Volumes/Data
Filesystem   1024-blocks      Used Available Capacity iused     ifree %iused  Mounted on
/dev/disk3s5   482797652 431004200  13070664    98% 2915598 130706640    2%   /System/Volumes/Data
available_kib 13070664

# tmp /tmp
Filesystem      Size    Used   Avail Capacity iused ifree %iused  Mounted on
/dev/disk3s5   460Gi   411Gi    12Gi    98%    2.9M  131M    2%   /System/Volumes/Data
Filesystem   1024-blocks      Used Available Capacity iused     ifree %iused  Mounted on
/dev/disk3s5   482797652 431004200  13070664    98% 2915598 130706640    2%   /System/Volumes/Data
available_kib 13070664
```

### Closing disk measurement

```text
# repo /Users/hbauzan/treepwood/3hm-dimentional-fw
Filesystem      Size    Used   Avail Capacity iused ifree %iused  Mounted on
/dev/disk3s5   460Gi   411Gi    13Gi    98%    2.9M  132M    2%   /System/Volumes/Data
Filesystem   1024-blocks      Used Available Capacity iused     ifree %iused  Mounted on
/dev/disk3s5   482797652 430892952  13181912    98% 2915580 131819120    2%   /System/Volumes/Data
available_kib 13181912

# tmp /tmp
Filesystem      Size    Used   Avail Capacity iused ifree %iused  Mounted on
/dev/disk3s5   460Gi   411Gi    13Gi    98%    2.9M  132M    2%   /System/Volumes/Data
Filesystem   1024-blocks      Used Available Capacity iused     ifree %iused  Mounted on
/dev/disk3s5   482797652 430892952  13181912    98% 2915580 131819120    2%   /System/Volumes/Data
available_kib 13181912
```

Floor is 3145728 KiB. The closing `df -k` Available field is the measurement that has to clear that floor.

## 2. Stratum 4 preset impact

Preset definitions stay those in the roadmap: `1B_base_tech_noise` adds `structural_symbol_noise` to `1B_base_tech`, and `1B_full_v3` adds that stratum to `1B_full`. `1B_full` adds `near_ood_neighbor` and does not include the symbol stratum. The comparison is the nested CAL_ONLY p10 F1 of each stored cell.
### python / full_only
- symbol stratum against base_tech: `1B_base_tech_noise` F1 `0.6991150442477876` (`dir1024_sig_sep`) is below `1B_base_tech` F1 `0.728110599078341` (`dir1024_sig_sep`). OOD FAR `0.0` versus `0.0`. Adversarial FAR `0.13` versus `0.11`. Hybrid FAR `0.34` versus `0.27`.
  near-OOD FAR `0.3333333333333333` on `1B_base_tech_noise` and `0.3333333333333333` on `1B_base_tech`.
- symbol stratum against 1B_full: `1B_full_v3` F1 `0.6583333333333333` (`dir1024_sig_sep`) is below `1B_full` F1 `0.6956521739130435` (`dir1024_sig_sep`). OOD FAR `0.0` versus `0.0`. Adversarial FAR `0.18` versus `0.12`. Hybrid FAR `0.43` versus `0.38`.
  near-OOD FAR `0.4166666666666667` on `1B_full_v3` and `0.4166666666666667` on `1B_full`.
- near_ood_neighbor against base_tech: `1B_full` F1 `0.6956521739130435` (`dir1024_sig_sep`) is below `1B_base_tech` F1 `0.728110599078341` (`dir1024_sig_sep`). OOD FAR `0.0` versus `0.0`. Adversarial FAR `0.12` versus `0.11`. Hybrid FAR `0.38` versus `0.27`.
  near-OOD FAR `0.4166666666666667` on `1B_full` and `0.3333333333333333` on `1B_base_tech`.
### python / clauses
- symbol stratum against base_tech: `1B_base_tech_noise` F1 `0.8118811881188119` (`dir1024_clip_polboost`) is below `1B_base_tech` F1 `0.8159203980099502` (`dir1024_sig_sep`). OOD FAR `0.01` versus `0.0`. Adversarial FAR `0.09` versus `0.09`. Hybrid FAR `0.1` versus `0.1`.
  near-OOD FAR `0.5833333333333334` on `1B_base_tech_noise` and `0.5` on `1B_base_tech`.
- symbol stratum against 1B_full: `1B_full_v3` F1 `0.7941176470588235` (`dir1024_sig_sep2`) is below `1B_full` F1 `0.8133971291866029` (`dir1024_sig_sep`). OOD FAR `0.01` versus `0.01`. Adversarial FAR `0.1` versus `0.11`. Hybrid FAR `0.12` versus `0.12`.
  near-OOD FAR `0.5833333333333334` on `1B_full_v3` and `0.5833333333333334` on `1B_full`.
- near_ood_neighbor against base_tech: `1B_full` F1 `0.8133971291866029` (`dir1024_sig_sep`) is below `1B_base_tech` F1 `0.8159203980099502` (`dir1024_sig_sep`). OOD FAR `0.01` versus `0.0`. Adversarial FAR `0.11` versus `0.09`. Hybrid FAR `0.12` versus `0.1`.
  near-OOD FAR `0.5833333333333334` on `1B_full` and `0.5` on `1B_base_tech`.
### receta / full_only
- symbol stratum against base_tech: `1B_base_tech_noise` F1 `0.6136363636363636` (`dir1024_clip_polboost`) is below `1B_base_tech` F1 `0.7403846153846154` (`polarity_v2_subset`). OOD FAR `0.0` versus `0.0`. Adversarial FAR `0.0` versus `0.01`. Hybrid FAR `0.22` versus `0.3`.
  near-OOD FAR `0.0` on `1B_base_tech_noise` and `0.0` on `1B_base_tech`.
- symbol stratum against 1B_full: `1B_full_v3` F1 `0.7164179104477612` (`polarity_v2_subset`) is above `1B_full` F1 `0.6222222222222222` (`dir1024_clip_polboost`). OOD FAR `0.0` versus `0.0`. Adversarial FAR `0.0` versus `0.0`. Hybrid FAR `0.29` versus `0.24`.
  near-OOD FAR `0.0` on `1B_full_v3` and `0.0` on `1B_full`.
- near_ood_neighbor against base_tech: `1B_full` F1 `0.6222222222222222` (`dir1024_clip_polboost`) is below `1B_base_tech` F1 `0.7403846153846154` (`polarity_v2_subset`). OOD FAR `0.0` versus `0.0`. Adversarial FAR `0.0` versus `0.01`. Hybrid FAR `0.24` versus `0.3`.
  near-OOD FAR `0.0` on `1B_full` and `0.0` on `1B_base_tech`.
### receta / clauses
- symbol stratum against base_tech: `1B_base_tech_noise` F1 `0.8648648648648649` (`dir1024_sig_sep`) is below `1B_base_tech` F1 `0.8783068783068783` (`dir1024_sig_sep`). OOD FAR `0.01` versus `0.01`. Adversarial FAR `0.0` versus `0.01`. Hybrid FAR `0.04` versus `0.04`.
  near-OOD FAR `0.0` on `1B_base_tech_noise` and `0.0` on `1B_base_tech`.
- symbol stratum against 1B_full: `1B_full_v3` F1 `0.8770053475935828` (`dir1024_sig_sep`) is below `1B_full` F1 `0.8829787234042553` (`dir1024_sig_sep`). OOD FAR `0.01` versus `0.01`. Adversarial FAR `0.0` versus `0.0`. Hybrid FAR `0.04` versus `0.04`.
  near-OOD FAR `0.0` on `1B_full_v3` and `0.0` on `1B_full`.
- near_ood_neighbor against base_tech: `1B_full` F1 `0.8829787234042553` (`dir1024_sig_sep`) is above `1B_base_tech` F1 `0.8783068783068783` (`dir1024_sig_sep`). OOD FAR `0.01` versus `0.01`. Adversarial FAR `0.0` versus `0.01`. Hybrid FAR `0.04` versus `0.04`.
  near-OOD FAR `0.0` on `1B_full` and `0.0` on `1B_base_tech`.

## 3. F_dir1024 versus polarity_v2_subset versus base_repaired

Rows here are the stored alpha=0, beta=0 reference scores (`primary.dir1024_alpha0_beta0` and `primary.baselines_alpha0_beta0`). They are not the nested headline unless the headline recipe is that same alpha=0 beta=0 name.
### python / full_only / 1B_base_tech
Nested family `dir1024_sig_sep`, wins `10`, recipe `dir1024_sig_sep|identity|a=0.00|g=-|gamma|b=0.00|y=0.10|r=full_doc|w=-`, CAL_ONLY p10 F1 `0.728110599078341`.
- anchors `full_doc`: sep_ge_1 `23`, sep_ge_1_and_sign_flip `6`, polarity_dials `128`, tie_count `0`.
- anchors `clause_opt2c`: sep_ge_1 `0`, sep_ge_1_and_sign_flip `0`, polarity_dials `81`, tie_count `0`.
| family | w_f | CAL_ONLY p10 F1 | FRR | FAR | ROC-AUC | 5x5 F1 mean | 5x5 F1 std | versus TASK-013 CAL p10 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `dir1024_sig_sep` | `null` | `0.6929824561403509` | `0.21` | `0.16333333333333333` | `0.9022333333333333` | `0.7001886407384414` | `0.001696098855860996` | above |
| `dir1024_sig_sep2` | `null` | `0.6869565217391305` | `0.21` | `0.17` | `0.9012333333333333` | `0.6950578223230977` | `0.0052272797162511465` | above |
| `dir1024_clip_polboost` | `null` | `0.6837606837606838` | `0.2` | `0.18` | `0.8990999999999999` | `0.6888222917295413` | `0.009705513086031977` | above |
| `polarity_v2_subset` | `null` | `0.6044776119402985` | `0.19` | `0.29` | `0.848` | `0.5681792717086835` | `0.014854617701796574` | below |
| `base_repaired` | `null` | `0.5547445255474452` | `0.24` | `0.32666666666666666` | `0.7871333333333334` | `0.5217975579494832` | `0.009616961837684969` | below |
| `f2_l2` | `null` | `0.44642857142857145` | `0.5` | `0.24666666666666667` | `0.7583333333333333` | `0.5396087123545541` | `0.01080999482250534` | below |
| `tail_p3` | `null` | `0.5274725274725275` | `0.28` | `0.33666666666666667` | `0.7702333333333333` | `0.5121487396883575` | `0.009140598209572049` | below |
| `tail_p5` | `null` | `0.5298507462686567` | `0.29` | `0.3233333333333333` | `0.7728333333333333` | `0.5380410504404959` | `0.0095551554421979` | below |
| `tail_p10` | `null` | `0.5294117647058824` | `0.28` | `0.3333333333333333` | `0.7696666666666666` | `0.5163007757023452` | `0.016349072343131238` | below |
| `tail_p25` | `null` | `0.49382716049382713` | `0.4` | `0.27666666666666667` | `0.7652000000000001` | `0.5293786778105354` | `0.007836339810658342` | below |
### python / clauses / 1B_base_tech
Nested family `dir1024_sig_sep`, wins `4`, recipe `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.20|y=-|r=full_doc|w=0.50`, CAL_ONLY p10 F1 `0.8159203980099502`.
- anchors `full_doc`: sep_ge_1 `23`, sep_ge_1_and_sign_flip `6`, polarity_dials `128`, tie_count `0`.
- anchors `clause_opt2c`: sep_ge_1 `0`, sep_ge_1_and_sign_flip `0`, polarity_dials `81`, tie_count `0`.
| family | w_f | CAL_ONLY p10 F1 | FRR | FAR | ROC-AUC | 5x5 F1 mean | 5x5 F1 std | versus TASK-013 CAL p10 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `dir1024_sig_sep` | `0.2` | `0.6844106463878327` | `0.1` | `0.24333333333333335` | `0.8993333333333333` | `0.6985428729685195` | `0.004400715215100583` | above |
| `dir1024_sig_sep` | `0.35` | `0.7073170731707317` | `0.13` | `0.19666666666666666` | `0.9184333333333333` | `0.7209162218234854` | `0.003947064205678507` | above |
| `dir1024_sig_sep` | `0.5` | `0.7420814479638009` | `0.18` | `0.13` | `0.9287666666666666` | `0.7164722124722125` | `0.0072633185634130406` | above |
| `dir1024_sig_sep` | `0.7` | `0.7601809954751131` | `0.16` | `0.12333333333333334` | `0.9284666666666668` | `0.7511617251168821` | `0.007715532120450008` | above |
| `dir1024_sig_sep2` | `0.2` | `0.6920152091254753` | `0.09` | `0.24` | `0.9` | `0.6830885392109496` | `0.011467864138648948` | above |
| `dir1024_sig_sep2` | `0.35` | `0.7088607594936709` | `0.16` | `0.17666666666666667` | `0.9193333333333333` | `0.6971950467201027` | `0.006099716770899148` | above |
| `dir1024_sig_sep2` | `0.5` | `0.7454545454545455` | `0.18` | `0.12666666666666668` | `0.9289666666666667` | `0.7243132783557534` | `0.005550007208474855` | above |
| `dir1024_sig_sep2` | `0.7` | `0.7671232876712328` | `0.16` | `0.11666666666666667` | `0.9286333333333334` | `0.7573111683111683` | `0.010455800085694411` | above |
| `dir1024_clip_polboost` | `0.2` | `0.674074074074074` | `0.09` | `0.2633333333333333` | `0.8956333333333333` | `0.6730285208372857` | `0.008711356284385489` | above |
| `dir1024_clip_polboost` | `0.35` | `0.7096774193548387` | `0.12` | `0.2` | `0.9145666666666666` | `0.6977712061951717` | `0.009139099549546847` | above |
| `dir1024_clip_polboost` | `0.5` | `0.7433628318584071` | `0.16` | `0.14` | `0.9253333333333333` | `0.7205363609683807` | `0.01334603387861067` | above |
| `dir1024_clip_polboost` | `0.7` | `0.7699115044247787` | `0.13` | `0.13` | `0.9252` | `0.7613218855832196` | `0.002447276190092386` | above |
| `polarity_v2_subset` | `0.2` | `0.5661538461538461` | `0.08` | `0.44333333333333336` | `0.8586` | `0.6392754780990075` | `0.0099738051345903` | below |
| `polarity_v2_subset` | `0.35` | `0.643598615916955` | `0.07` | `0.32` | `0.8784333333333334` | `0.6479061537425617` | `0.00876221753648061` | below |
| `polarity_v2_subset` | `0.5` | `0.6714801444043321` | `0.07` | `0.28` | `0.8888666666666667` | `0.6922652099467881` | `0.00978568062552237` | equal |
| `polarity_v2_subset` | `0.7` | `0.6616541353383458` | `0.12` | `0.26` | `0.8851333333333333` | `0.710826393337604` | `0.0031579135282168284` | below |
| `base_repaired` | `0.2` | `0.5486725663716814` | `0.07` | `0.4866666666666667` | `0.7724` | `0.5538064516129032` | `0.013849195215482581` | below |
| `base_repaired` | `0.35` | `0.5760517799352751` | `0.11` | `0.4` | `0.8098333333333333` | `0.5808176064939116` | `0.01213270671346006` | below |
| `base_repaired` | `0.5` | `0.6056338028169014` | `0.14` | `0.32666666666666666` | `0.8323666666666667` | `0.5927033304755098` | `0.013087947361604867` | below |
| `base_repaired` | `0.7` | `0.5977011494252874` | `0.22` | `0.27666666666666667` | `0.8214666666666666` | `0.5807366649202171` | `0.0087610783691672` | below |
| `f2_l2` | `0.2` | `0.6454545454545455` | `0.29` | `0.16333333333333333` | `0.8566666666666667` | `0.6254950034377624` | `0.008917169188659521` | below |
| `f2_l2` | `0.35` | `0.6206896551724138` | `0.37` | `0.13333333333333333` | `0.8644333333333334` | `0.6638647011833515` | `0.010816966789802094` | below |
| `f2_l2` | `0.5` | `0.6048780487804878` | `0.38` | `0.14333333333333334` | `0.8513` | `0.6351412936593015` | `0.006446054482363597` | below |
| `f2_l2` | `0.7` | `0.5023696682464455` | `0.47` | `0.19333333333333333` | `0.8114333333333333` | `0.5542139140093805` | `0.008152000571992416` | below |
| `tail_p3` | `0.2` | `0.5477707006369427` | `0.14` | `0.4266666666666667` | `0.7667666666666666` | `0.5368628771673575` | `0.024957034800817776` | below |
| `tail_p3` | `0.35` | `0.5664335664335665` | `0.19` | `0.35` | `0.7940666666666667` | `0.5417825650877324` | `0.006545044187069277` | below |
| `tail_p3` | `0.5` | `0.5660377358490566` | `0.25` | `0.3` | `0.8065333333333333` | `0.5382304427573178` | `0.014977471780511198` | below |
| `tail_p3` | `0.7` | `0.5413533834586466` | `0.28` | `0.31333333333333335` | `0.8022333333333334` | `0.5335132672956104` | `0.01312982347214918` | below |
| `tail_p5` | `0.2` | `0.5618729096989966` | `0.16` | `0.38333333333333336` | `0.7827999999999999` | `0.568970261216329` | `0.013617250792522432` | below |
| `tail_p5` | `0.35` | `0.5767790262172284` | `0.23` | `0.3` | `0.8069333333333333` | `0.5837936483928889` | `0.013472305929956612` | below |
| `tail_p5` | `0.5` | `0.5928853754940712` | `0.25` | `0.26` | `0.8167` | `0.5736247747919976` | `0.021171880856351032` | below |
| `tail_p5` | `0.7` | `0.5418326693227091` | `0.32` | `0.27666666666666667` | `0.8100666666666667` | `0.5436504911640216` | `0.007734704822555832` | below |
| `tail_p10` | `0.2` | `0.5934065934065934` | `0.19` | `0.30666666666666664` | `0.8006333333333333` | `0.57212100029048` | `0.0010236150845098458` | below |
| `tail_p10` | `0.35` | `0.5555555555555556` | `0.3` | `0.2733333333333333` | `0.8210999999999999` | `0.598033114438401` | `0.0049457470304813105` | below |
| `tail_p10` | `0.5` | `0.5589519650655022` | `0.36` | `0.21666666666666667` | `0.8266` | `0.5800598883800064` | `0.008615919701945867` | below |
| `tail_p10` | `0.7` | `0.5365853658536586` | `0.34` | `0.26666666666666666` | `0.8107333333333333` | `0.5682896962645246` | `0.013270737777131572` | below |
| `tail_p25` | `0.2` | `0.6040816326530613` | `0.26` | `0.23666666666666666` | `0.8323333333333334` | `0.5939038151076249` | `0.009169227663376607` | below |
| `tail_p25` | `0.35` | `0.5929203539823009` | `0.33` | `0.19666666666666666` | `0.8486` | `0.6040971761468075` | `0.00823833503709704` | below |
| `tail_p25` | `0.5` | `0.5855855855855856` | `0.35` | `0.19` | `0.8436333333333333` | `0.6320450020362912` | `0.005647210889293991` | below |
| `tail_p25` | `0.7` | `0.5327510917030568` | `0.39` | `0.22666666666666666` | `0.8156666666666667` | `0.5889563538776119` | `0.012062790451317277` | below |
### python / full_only / 1B_base_tech_noise
Nested family `dir1024_sig_sep`, wins `17`, recipe `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.05|y=-|r=full_doc|w=-`, CAL_ONLY p10 F1 `0.6991150442477876`.
- anchors `full_doc`: sep_ge_1 `17`, sep_ge_1_and_sign_flip `4`, polarity_dials `123`, tie_count `0`.
- anchors `clause_opt2c`: sep_ge_1 `0`, sep_ge_1_and_sign_flip `0`, polarity_dials `70`, tie_count `0`.
| family | w_f | CAL_ONLY p10 F1 | FRR | FAR | ROC-AUC | 5x5 F1 mean | 5x5 F1 std | versus TASK-013 CAL p10 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `dir1024_sig_sep` | `null` | `0.6810344827586207` | `0.21` | `0.17666666666666667` | `0.8975` | `0.7025208470487062` | `0.013042694317110349` | above |
| `dir1024_sig_sep2` | `null` | `0.6752136752136753` | `0.21` | `0.18333333333333332` | `0.8944333333333333` | `0.6794146242458219` | `0.01001681412013808` | above |
| `dir1024_clip_polboost` | `null` | `0.6694915254237288` | `0.21` | `0.19` | `0.8973666666666666` | `0.6800530421016681` | `0.010360815115102836` | above |
| `polarity_v2_subset` | `null` | `0.6613545816733067` | `0.17` | `0.22666666666666666` | `0.8917999999999999` | `0.6195136994334005` | `0.013111599527257932` | above |
| `base_repaired` | `null` | `0.5401459854014599` | `0.26` | `0.3333333333333333` | `0.7841666666666666` | `0.523783010659596` | `0.010805737851144966` | below |
| `f2_l2` | `null` | `0.44642857142857145` | `0.5` | `0.24666666666666667` | `0.7583333333333333` | `0.5396087123545541` | `0.01080999482250534` | below |
| `tail_p3` | `null` | `0.5274725274725275` | `0.28` | `0.33666666666666667` | `0.7702333333333333` | `0.5121487396883575` | `0.009140598209572049` | below |
| `tail_p5` | `null` | `0.5298507462686567` | `0.29` | `0.3233333333333333` | `0.7728333333333333` | `0.5380410504404959` | `0.0095551554421979` | below |
| `tail_p10` | `null` | `0.5294117647058824` | `0.28` | `0.3333333333333333` | `0.7696666666666666` | `0.5163007757023452` | `0.016349072343131238` | below |
| `tail_p25` | `null` | `0.49382716049382713` | `0.4` | `0.27666666666666667` | `0.7652000000000001` | `0.5293786778105354` | `0.007836339810658342` | below |
### python / clauses / 1B_base_tech_noise
Nested family `dir1024_clip_polboost`, wins `2`, recipe `dir1024_clip_polboost|multiplicative|a=0.05|g=tail_p5|beta|b=0.30|y=-|r=full_doc|w=0.35`, CAL_ONLY p10 F1 `0.8118811881188119`.
- anchors `full_doc`: sep_ge_1 `17`, sep_ge_1_and_sign_flip `4`, polarity_dials `123`, tie_count `0`.
- anchors `clause_opt2c`: sep_ge_1 `0`, sep_ge_1_and_sign_flip `0`, polarity_dials `70`, tie_count `0`.
| family | w_f | CAL_ONLY p10 F1 | FRR | FAR | ROC-AUC | 5x5 F1 mean | 5x5 F1 std | versus TASK-013 CAL p10 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `dir1024_sig_sep` | `0.2` | `0.7183673469387755` | `0.12` | `0.19` | `0.9080666666666666` | `0.7044238770447867` | `0.004351001394274266` | above |
| `dir1024_sig_sep` | `0.35` | `0.748898678414097` | `0.15` | `0.14` | `0.9280666666666666` | `0.7272028181819303` | `0.015529685230894971` | above |
| `dir1024_sig_sep` | `0.5` | `0.7663551401869159` | `0.18` | `0.10666666666666667` | `0.9361999999999999` | `0.7447070729878259` | `0.011838674495849109` | above |
| `dir1024_sig_sep` | `0.7` | `0.7476635514018691` | `0.2` | `0.11333333333333333` | `0.9308000000000001` | `0.7372833951975851` | `0.006847039400871391` | above |
| `dir1024_sig_sep2` | `0.2` | `0.717741935483871` | `0.11` | `0.19666666666666666` | `0.9086` | `0.7091666691589499` | `0.0054702885173062874` | above |
| `dir1024_sig_sep2` | `0.35` | `0.7433628318584071` | `0.16` | `0.14` | `0.9292` | `0.7237734019748636` | `0.010454825774799323` | above |
| `dir1024_sig_sep2` | `0.5` | `0.7677725118483413` | `0.19` | `0.1` | `0.9374` | `0.7479303856643505` | `0.0053118835853997685` | above |
| `dir1024_sig_sep2` | `0.7` | `0.7534883720930232` | `0.19` | `0.11333333333333333` | `0.9304333333333333` | `0.7475325547296323` | `0.008897430535083002` | above |
| `dir1024_clip_polboost` | `0.2` | `0.714859437751004` | `0.11` | `0.2` | `0.9054333333333333` | `0.7068081000081818` | `0.011216761386565965` | above |
| `dir1024_clip_polboost` | `0.35` | `0.7413793103448276` | `0.14` | `0.15333333333333332` | `0.9259999999999999` | `0.74026970759864` | `0.016575114596444576` | above |
| `dir1024_clip_polboost` | `0.5` | `0.7685185185185185` | `0.17` | `0.11` | `0.9348000000000001` | `0.7450522904064013` | `0.00507286010041029` | above |
| `dir1024_clip_polboost` | `0.7` | `0.7465437788018433` | `0.19` | `0.12` | `0.9304666666666666` | `0.7683213773314204` | `0.0033004802604328903` | above |
| `polarity_v2_subset` | `0.2` | `0.5942492012779552` | `0.07` | `0.4` | `0.8747` | `0.645271467813607` | `0.01030950500778527` | below |
| `polarity_v2_subset` | `0.35` | `0.6619718309859155` | `0.06` | `0.3` | `0.9052333333333333` | `0.7167080654751887` | `0.007632867886446378` | below |
| `polarity_v2_subset` | `0.5` | `0.6796875` | `0.13` | `0.23` | `0.9187000000000001` | `0.7262713342893585` | `0.0055259746565913676` | above |
| `polarity_v2_subset` | `0.7` | `0.6935483870967742` | `0.14` | `0.20666666666666667` | `0.9189666666666667` | `0.6919383757614764` | `0.01793932745663296` | above |
| `base_repaired` | `0.2` | `0.5585585585585585` | `0.07` | `0.4666666666666667` | `0.7727333333333333` | `0.557197280298152` | `0.003352849064157132` | below |
| `base_repaired` | `0.35` | `0.5825242718446602` | `0.1` | `0.39666666666666667` | `0.8113333333333332` | `0.5705498266552516` | `0.011146007369018471` | below |
| `base_repaired` | `0.5` | `0.6028368794326241` | `0.15` | `0.3233333333333333` | `0.8305666666666667` | `0.6153106376995546` | `0.006989375458556245` | below |
| `base_repaired` | `0.7` | `0.5813953488372093` | `0.25` | `0.27666666666666667` | `0.8184333333333333` | `0.5787249304088985` | `0.0033568907229261148` | below |
| `f2_l2` | `0.2` | `0.6454545454545455` | `0.29` | `0.16333333333333333` | `0.8566666666666667` | `0.6254950034377624` | `0.008917169188659521` | below |
| `f2_l2` | `0.35` | `0.6206896551724138` | `0.37` | `0.13333333333333333` | `0.8644333333333334` | `0.6638647011833515` | `0.010816966789802094` | below |
| `f2_l2` | `0.5` | `0.6048780487804878` | `0.38` | `0.14333333333333334` | `0.8513` | `0.6351412936593015` | `0.006446054482363597` | below |
| `f2_l2` | `0.7` | `0.5023696682464455` | `0.47` | `0.19333333333333333` | `0.8114333333333333` | `0.5542139140093805` | `0.008152000571992416` | below |
| `tail_p3` | `0.2` | `0.5477707006369427` | `0.14` | `0.4266666666666667` | `0.7667666666666666` | `0.5368628771673575` | `0.024957034800817776` | below |
| `tail_p3` | `0.35` | `0.5664335664335665` | `0.19` | `0.35` | `0.7940666666666667` | `0.5417825650877324` | `0.006545044187069277` | below |
| `tail_p3` | `0.5` | `0.5660377358490566` | `0.25` | `0.3` | `0.8065333333333333` | `0.5382304427573178` | `0.014977471780511198` | below |
| `tail_p3` | `0.7` | `0.5413533834586466` | `0.28` | `0.31333333333333335` | `0.8022333333333334` | `0.5335132672956104` | `0.01312982347214918` | below |
| `tail_p5` | `0.2` | `0.5618729096989966` | `0.16` | `0.38333333333333336` | `0.7827999999999999` | `0.568970261216329` | `0.013617250792522432` | below |
| `tail_p5` | `0.35` | `0.5767790262172284` | `0.23` | `0.3` | `0.8069333333333333` | `0.5837936483928889` | `0.013472305929956612` | below |
| `tail_p5` | `0.5` | `0.5928853754940712` | `0.25` | `0.26` | `0.8167` | `0.5736247747919976` | `0.021171880856351032` | below |
| `tail_p5` | `0.7` | `0.5418326693227091` | `0.32` | `0.27666666666666667` | `0.8100666666666667` | `0.5436504911640216` | `0.007734704822555832` | below |
| `tail_p10` | `0.2` | `0.5934065934065934` | `0.19` | `0.30666666666666664` | `0.8006333333333333` | `0.57212100029048` | `0.0010236150845098458` | below |
| `tail_p10` | `0.35` | `0.5555555555555556` | `0.3` | `0.2733333333333333` | `0.8210999999999999` | `0.598033114438401` | `0.0049457470304813105` | below |
| `tail_p10` | `0.5` | `0.5589519650655022` | `0.36` | `0.21666666666666667` | `0.8266` | `0.5800598883800064` | `0.008615919701945867` | below |
| `tail_p10` | `0.7` | `0.5365853658536586` | `0.34` | `0.26666666666666666` | `0.8107333333333333` | `0.5682896962645246` | `0.013270737777131572` | below |
| `tail_p25` | `0.2` | `0.6040816326530613` | `0.26` | `0.23666666666666666` | `0.8323333333333334` | `0.5939038151076249` | `0.009169227663376607` | below |
| `tail_p25` | `0.35` | `0.5929203539823009` | `0.33` | `0.19666666666666666` | `0.8486` | `0.6040971761468075` | `0.00823833503709704` | below |
| `tail_p25` | `0.5` | `0.5855855855855856` | `0.35` | `0.19` | `0.8436333333333333` | `0.6320450020362912` | `0.005647210889293991` | below |
| `tail_p25` | `0.7` | `0.5327510917030568` | `0.39` | `0.22666666666666666` | `0.8156666666666667` | `0.5889563538776119` | `0.012062790451317277` | below |
### python / full_only / 1B_full
Nested family `dir1024_sig_sep`, wins `13`, recipe `dir1024_sig_sep|additive|a=0.05|g=f2_l2|beta|b=0.20|y=-|r=full_doc|w=-`, CAL_ONLY p10 F1 `0.6956521739130435`.
- anchors `full_doc`: sep_ge_1 `7`, sep_ge_1_and_sign_flip `2`, polarity_dials `101`, tie_count `0`.
- anchors `clause_opt2c`: sep_ge_1 `0`, sep_ge_1_and_sign_flip `0`, polarity_dials `42`, tie_count `0`.
| family | w_f | CAL_ONLY p10 F1 | FRR | FAR | ROC-AUC | 5x5 F1 mean | 5x5 F1 std | versus TASK-013 CAL p10 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `dir1024_sig_sep` | `null` | `0.675` | `0.19` | `0.19666666666666666` | `0.8991333333333333` | `0.7058486680056963` | `0.008099067791337605` | above |
| `dir1024_sig_sep2` | `null` | `0.6611570247933884` | `0.2` | `0.20666666666666667` | `0.8982` | `0.70904071773637` | `0.005108835203125374` | above |
| `dir1024_clip_polboost` | `null` | `0.6721991701244814` | `0.19` | `0.2` | `0.8981333333333333` | `0.6901201705629305` | `0.015230547873409044` | above |
| `polarity_v2_subset` | `null` | `0.6338028169014085` | `0.1` | `0.31333333333333335` | `0.8613333333333333` | `0.6277631674623869` | `0.008243664016640392` | equal |
| `base_repaired` | `null` | `0.5591397849462365` | `0.22` | `0.33666666666666667` | `0.7917666666666667` | `0.5338359293922763` | `0.016360522521898034` | below |
| `f2_l2` | `null` | `0.44642857142857145` | `0.5` | `0.24666666666666667` | `0.7583333333333333` | `0.5396087123545541` | `0.01080999482250534` | below |
| `tail_p3` | `null` | `0.5274725274725275` | `0.28` | `0.33666666666666667` | `0.7702333333333333` | `0.5121487396883575` | `0.009140598209572049` | below |
| `tail_p5` | `null` | `0.5298507462686567` | `0.29` | `0.3233333333333333` | `0.7728333333333333` | `0.5380410504404959` | `0.0095551554421979` | below |
| `tail_p10` | `null` | `0.5294117647058824` | `0.28` | `0.3333333333333333` | `0.7696666666666666` | `0.5163007757023452` | `0.016349072343131238` | below |
| `tail_p25` | `null` | `0.49382716049382713` | `0.4` | `0.27666666666666667` | `0.7652000000000001` | `0.5293786778105354` | `0.007836339810658342` | below |
### python / clauses / 1B_full
Nested family `dir1024_sig_sep`, wins `3`, recipe `dir1024_sig_sep|multiplicative|a=0.20|g=tail_p5|gamma|b=0.00|y=0.10|r=full_doc|w=0.35`, CAL_ONLY p10 F1 `0.8133971291866029`.
- anchors `full_doc`: sep_ge_1 `7`, sep_ge_1_and_sign_flip `2`, polarity_dials `101`, tie_count `0`.
- anchors `clause_opt2c`: sep_ge_1 `0`, sep_ge_1_and_sign_flip `0`, polarity_dials `42`, tie_count `0`.
| family | w_f | CAL_ONLY p10 F1 | FRR | FAR | ROC-AUC | 5x5 F1 mean | 5x5 F1 std | versus TASK-013 CAL p10 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `dir1024_sig_sep` | `0.2` | `0.6976744186046512` | `0.1` | `0.22666666666666666` | `0.9027666666666667` | `0.7158539435372229` | `0.003781141974201825` | above |
| `dir1024_sig_sep` | `0.35` | `0.7510548523206751` | `0.11` | `0.16` | `0.9231333333333334` | `0.7495178032132809` | `0.004595159769650113` | above |
| `dir1024_sig_sep` | `0.5` | `0.7685589519650655` | `0.12` | `0.13666666666666666` | `0.9309333333333334` | `0.7649980089746408` | `0.011048706414825579` | above |
| `dir1024_sig_sep` | `0.7` | `0.7363636363636363` | `0.19` | `0.13` | `0.9277` | `0.7525316335207443` | `0.00860575538109031` | above |
| `dir1024_sig_sep2` | `0.2` | `0.6953125` | `0.11` | `0.22333333333333333` | `0.9018333333333334` | `0.7216271257950767` | `0.0027436219087049146` | above |
| `dir1024_sig_sep2` | `0.35` | `0.7394957983193278` | `0.12` | `0.16666666666666666` | `0.9218333333333333` | `0.7461176863303469` | `0.007626024930304003` | above |
| `dir1024_sig_sep2` | `0.5` | `0.775330396475771` | `0.12` | `0.13` | `0.9305333333333333` | `0.7563575780014137` | `0.005369554188048945` | above |
| `dir1024_sig_sep2` | `0.7` | `0.7488584474885844` | `0.18` | `0.12333333333333334` | `0.9269000000000001` | `0.7311085997111174` | `0.008615562495491296` | above |
| `dir1024_clip_polboost` | `0.2` | `0.6920152091254753` | `0.09` | `0.24` | `0.9009333333333334` | `0.7118721467657638` | `0.007930462044894419` | above |
| `dir1024_clip_polboost` | `0.35` | `0.75` | `0.1` | `0.16666666666666666` | `0.9204000000000001` | `0.7408708260995225` | `0.004387316979739519` | above |
| `dir1024_clip_polboost` | `0.5` | `0.7565217391304347` | `0.13` | `0.14333333333333334` | `0.9293` | `0.7474674682584442` | `0.005528004656060401` | above |
| `dir1024_clip_polboost` | `0.7` | `0.7533632286995515` | `0.16` | `0.13` | `0.9263000000000001` | `0.727461678068999` | `0.009130535612515492` | above |
| `polarity_v2_subset` | `0.2` | `0.5661538461538461` | `0.08` | `0.44333333333333336` | `0.8513333333333334` | `0.6375602332596944` | `0.0024718091031877593` | below |
| `polarity_v2_subset` | `0.35` | `0.636986301369863` | `0.07` | `0.33` | `0.8798999999999999` | `0.6816922752364546` | `0.00541134950412451` | below |
| `polarity_v2_subset` | `0.5` | `0.6788321167883211` | `0.07` | `0.27` | `0.8951333333333333` | `0.6912524098076905` | `0.013251411462411518` | above |
| `polarity_v2_subset` | `0.7` | `0.6863468634686347` | `0.07` | `0.26` | `0.8937333333333333` | `0.6643269341805829` | `0.016799157605298976` | above |
| `base_repaired` | `0.2` | `0.5558912386706949` | `0.08` | `0.4633333333333333` | `0.7752333333333332` | `0.556729679709397` | `0.003211557180479178` | below |
| `base_repaired` | `0.35` | `0.5789473684210527` | `0.12` | `0.38666666666666666` | `0.8160666666666667` | `0.5735485524693378` | `0.008437482330101602` | below |
| `base_repaired` | `0.5` | `0.6209386281588448` | `0.14` | `0.30333333333333334` | `0.8364333333333334` | `0.6040783340872666` | `0.003863605408668033` | below |
| `base_repaired` | `0.7` | `0.5954198473282443` | `0.22` | `0.28` | `0.8254999999999999` | `0.5766554644520363` | `0.009538070881187837` | below |
| `f2_l2` | `0.2` | `0.6454545454545455` | `0.29` | `0.16333333333333333` | `0.8566666666666667` | `0.6254950034377624` | `0.008917169188659521` | below |
| `f2_l2` | `0.35` | `0.6206896551724138` | `0.37` | `0.13333333333333333` | `0.8644333333333334` | `0.6638647011833515` | `0.010816966789802094` | below |
| `f2_l2` | `0.5` | `0.6048780487804878` | `0.38` | `0.14333333333333334` | `0.8513` | `0.6351412936593015` | `0.006446054482363597` | below |
| `f2_l2` | `0.7` | `0.5023696682464455` | `0.47` | `0.19333333333333333` | `0.8114333333333333` | `0.5542139140093805` | `0.008152000571992416` | below |
| `tail_p3` | `0.2` | `0.5477707006369427` | `0.14` | `0.4266666666666667` | `0.7667666666666666` | `0.5368628771673575` | `0.024957034800817776` | below |
| `tail_p3` | `0.35` | `0.5664335664335665` | `0.19` | `0.35` | `0.7940666666666667` | `0.5417825650877324` | `0.006545044187069277` | below |
| `tail_p3` | `0.5` | `0.5660377358490566` | `0.25` | `0.3` | `0.8065333333333333` | `0.5382304427573178` | `0.014977471780511198` | below |
| `tail_p3` | `0.7` | `0.5413533834586466` | `0.28` | `0.31333333333333335` | `0.8022333333333334` | `0.5335132672956104` | `0.01312982347214918` | below |
| `tail_p5` | `0.2` | `0.5618729096989966` | `0.16` | `0.38333333333333336` | `0.7827999999999999` | `0.568970261216329` | `0.013617250792522432` | below |
| `tail_p5` | `0.35` | `0.5767790262172284` | `0.23` | `0.3` | `0.8069333333333333` | `0.5837936483928889` | `0.013472305929956612` | below |
| `tail_p5` | `0.5` | `0.5928853754940712` | `0.25` | `0.26` | `0.8167` | `0.5736247747919976` | `0.021171880856351032` | below |
| `tail_p5` | `0.7` | `0.5418326693227091` | `0.32` | `0.27666666666666667` | `0.8100666666666667` | `0.5436504911640216` | `0.007734704822555832` | below |
| `tail_p10` | `0.2` | `0.5934065934065934` | `0.19` | `0.30666666666666664` | `0.8006333333333333` | `0.57212100029048` | `0.0010236150845098458` | below |
| `tail_p10` | `0.35` | `0.5555555555555556` | `0.3` | `0.2733333333333333` | `0.8210999999999999` | `0.598033114438401` | `0.0049457470304813105` | below |
| `tail_p10` | `0.5` | `0.5589519650655022` | `0.36` | `0.21666666666666667` | `0.8266` | `0.5800598883800064` | `0.008615919701945867` | below |
| `tail_p10` | `0.7` | `0.5365853658536586` | `0.34` | `0.26666666666666666` | `0.8107333333333333` | `0.5682896962645246` | `0.013270737777131572` | below |
| `tail_p25` | `0.2` | `0.6040816326530613` | `0.26` | `0.23666666666666666` | `0.8323333333333334` | `0.5939038151076249` | `0.009169227663376607` | below |
| `tail_p25` | `0.35` | `0.5929203539823009` | `0.33` | `0.19666666666666666` | `0.8486` | `0.6040971761468075` | `0.00823833503709704` | below |
| `tail_p25` | `0.5` | `0.5855855855855856` | `0.35` | `0.19` | `0.8436333333333333` | `0.6320450020362912` | `0.005647210889293991` | below |
| `tail_p25` | `0.7` | `0.5327510917030568` | `0.39` | `0.22666666666666666` | `0.8156666666666667` | `0.5889563538776119` | `0.012062790451317277` | below |
### python / full_only / 1B_full_v3
Nested family `dir1024_sig_sep`, wins `7`, recipe `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.10|y=-|r=full_doc|w=-`, CAL_ONLY p10 F1 `0.6583333333333333`.
- anchors `full_doc`: sep_ge_1 `8`, sep_ge_1_and_sign_flip `1`, polarity_dials `96`, tie_count `0`.
- anchors `clause_opt2c`: sep_ge_1 `0`, sep_ge_1_and_sign_flip `0`, polarity_dials `41`, tie_count `0`.
| family | w_f | CAL_ONLY p10 F1 | FRR | FAR | ROC-AUC | 5x5 F1 mean | 5x5 F1 std | versus TASK-013 CAL p10 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `dir1024_sig_sep` | `null` | `0.6530612244897959` | `0.2` | `0.21666666666666667` | `0.8934666666666666` | `0.6786740983172042` | `0.012079912613757345` | above |
| `dir1024_sig_sep2` | `null` | `0.6557377049180327` | `0.2` | `0.21333333333333335` | `0.8906333333333334` | `0.6863162739320369` | `0.005874917980463324` | above |
| `dir1024_clip_polboost` | `null` | `0.6477732793522267` | `0.2` | `0.22333333333333333` | `0.8943` | `0.6850693116375021` | `0.004806752468665195` | above |
| `polarity_v2_subset` | `null` | `0.6428571428571429` | `0.19` | `0.23666666666666666` | `0.8787666666666667` | `0.6291360677796461` | `0.011228517385450217` | above |
| `base_repaired` | `null` | `0.5576208178438662` | `0.25` | `0.31333333333333335` | `0.7856333333333332` | `0.53101470072782` | `0.008149581381244634` | below |
| `f2_l2` | `null` | `0.44642857142857145` | `0.5` | `0.24666666666666667` | `0.7583333333333333` | `0.5396087123545541` | `0.01080999482250534` | below |
| `tail_p3` | `null` | `0.5274725274725275` | `0.28` | `0.33666666666666667` | `0.7702333333333333` | `0.5121487396883575` | `0.009140598209572049` | below |
| `tail_p5` | `null` | `0.5298507462686567` | `0.29` | `0.3233333333333333` | `0.7728333333333333` | `0.5380410504404959` | `0.0095551554421979` | below |
| `tail_p10` | `null` | `0.5294117647058824` | `0.28` | `0.3333333333333333` | `0.7696666666666666` | `0.5163007757023452` | `0.016349072343131238` | below |
| `tail_p25` | `null` | `0.49382716049382713` | `0.4` | `0.27666666666666667` | `0.7652000000000001` | `0.5293786778105354` | `0.007836339810658342` | below |
### python / clauses / 1B_full_v3
Nested family `dir1024_sig_sep2`, wins `4`, recipe `dir1024_sig_sep2|multiplicative|a=0.10|g=f2_l2|gamma|b=0.00|y=0.10|r=full_doc|w=0.35`, CAL_ONLY p10 F1 `0.7941176470588235`.
- anchors `full_doc`: sep_ge_1 `8`, sep_ge_1_and_sign_flip `1`, polarity_dials `96`, tie_count `0`.
- anchors `clause_opt2c`: sep_ge_1 `0`, sep_ge_1_and_sign_flip `0`, polarity_dials `41`, tie_count `0`.
| family | w_f | CAL_ONLY p10 F1 | FRR | FAR | ROC-AUC | 5x5 F1 mean | 5x5 F1 std | versus TASK-013 CAL p10 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `dir1024_sig_sep` | `0.2` | `0.7044534412955465` | `0.13` | `0.2` | `0.9017666666666666` | `0.7511436181456898` | `0.0025713883646046954` | above |
| `dir1024_sig_sep` | `0.35` | `0.7610619469026548` | `0.14` | `0.13333333333333333` | `0.9245` | `0.7455870483890414` | `0.010787286130807747` | above |
| `dir1024_sig_sep` | `0.5` | `0.7727272727272727` | `0.15` | `0.11666666666666667` | `0.9321999999999999` | `0.7506802169093876` | `0.004701525281756273` | above |
| `dir1024_sig_sep` | `0.7` | `0.7387387387387387` | `0.18` | `0.13333333333333333` | `0.9259666666666666` | `0.7393456109016858` | `0.007277506469441434` | above |
| `dir1024_sig_sep2` | `0.2` | `0.6987951807228916` | `0.13` | `0.20666666666666667` | `0.9002666666666668` | `0.7124629357672452` | `0.006727214599716342` | above |
| `dir1024_sig_sep2` | `0.35` | `0.7699115044247787` | `0.13` | `0.13` | `0.9239999999999999` | `0.7514777500519859` | `0.008261142387391968` | above |
| `dir1024_sig_sep2` | `0.5` | `0.7488584474885844` | `0.18` | `0.12333333333333334` | `0.9318333333333333` | `0.748827450000748` | `0.004475233286289437` | above |
| `dir1024_sig_sep2` | `0.7` | `0.7397260273972602` | `0.19` | `0.12666666666666668` | `0.9254` | `0.7347982199704836` | `0.008686708588191634` | above |
| `dir1024_clip_polboost` | `0.2` | `0.6987951807228916` | `0.13` | `0.20666666666666667` | `0.9013333333333332` | `0.7375973258326199` | `0.0025522768484772212` | above |
| `dir1024_clip_polboost` | `0.35` | `0.7719298245614035` | `0.12` | `0.13333333333333333` | `0.9233333333333333` | `0.7481942116875175` | `0.008469776320980634` | above |
| `dir1024_clip_polboost` | `0.5` | `0.7623318385650224` | `0.15` | `0.12666666666666668` | `0.9323999999999999` | `0.7664804146297063` | `0.0030380502121440845` | above |
| `dir1024_clip_polboost` | `0.7` | `0.7377777777777778` | `0.17` | `0.14` | `0.9266666666666665` | `0.7449714104802656` | `0.00595734664546186` | above |
| `polarity_v2_subset` | `0.2` | `0.6072607260726073` | `0.08` | `0.37` | `0.8639666666666665` | `0.6702894654365242` | `0.0025394915603728636` | below |
| `polarity_v2_subset` | `0.35` | `0.6642335766423357` | `0.09` | `0.27666666666666667` | `0.8943` | `0.7122221394537835` | `0.0048954858588815325` | below |
| `polarity_v2_subset` | `0.5` | `0.7086614173228346` | `0.1` | `0.21333333333333335` | `0.9084000000000001` | `0.7429044084771528` | `0.0032570464163545897` | above |
| `polarity_v2_subset` | `0.7` | `0.6932270916334662` | `0.13` | `0.21333333333333335` | `0.9067` | `0.6925373062152953` | `0.007998630607292065` | above |
| `base_repaired` | `0.2` | `0.5558912386706949` | `0.08` | `0.4633333333333333` | `0.7750999999999999` | `0.5447056063459849` | `0.004363080627304338` | below |
| `base_repaired` | `0.35` | `0.5863192182410424` | `0.1` | `0.39` | `0.8140666666666666` | `0.569441468992688` | `0.009639808661313618` | below |
| `base_repaired` | `0.5` | `0.6071428571428571` | `0.15` | `0.31666666666666665` | `0.8304333333333334` | `0.607238178932674` | `0.01029232853936612` | below |
| `base_repaired` | `0.7` | `0.5811320754716981` | `0.23` | `0.29333333333333333` | `0.8187333333333333` | `0.5683610542040105` | `0.00805751927346807` | below |
| `f2_l2` | `0.2` | `0.6454545454545455` | `0.29` | `0.16333333333333333` | `0.8566666666666667` | `0.6254950034377624` | `0.008917169188659521` | below |
| `f2_l2` | `0.35` | `0.6206896551724138` | `0.37` | `0.13333333333333333` | `0.8644333333333334` | `0.6638647011833515` | `0.010816966789802094` | below |
| `f2_l2` | `0.5` | `0.6048780487804878` | `0.38` | `0.14333333333333334` | `0.8513` | `0.6351412936593015` | `0.006446054482363597` | below |
| `f2_l2` | `0.7` | `0.5023696682464455` | `0.47` | `0.19333333333333333` | `0.8114333333333333` | `0.5542139140093805` | `0.008152000571992416` | below |
| `tail_p3` | `0.2` | `0.5477707006369427` | `0.14` | `0.4266666666666667` | `0.7667666666666666` | `0.5368628771673575` | `0.024957034800817776` | below |
| `tail_p3` | `0.35` | `0.5664335664335665` | `0.19` | `0.35` | `0.7940666666666667` | `0.5417825650877324` | `0.006545044187069277` | below |
| `tail_p3` | `0.5` | `0.5660377358490566` | `0.25` | `0.3` | `0.8065333333333333` | `0.5382304427573178` | `0.014977471780511198` | below |
| `tail_p3` | `0.7` | `0.5413533834586466` | `0.28` | `0.31333333333333335` | `0.8022333333333334` | `0.5335132672956104` | `0.01312982347214918` | below |
| `tail_p5` | `0.2` | `0.5618729096989966` | `0.16` | `0.38333333333333336` | `0.7827999999999999` | `0.568970261216329` | `0.013617250792522432` | below |
| `tail_p5` | `0.35` | `0.5767790262172284` | `0.23` | `0.3` | `0.8069333333333333` | `0.5837936483928889` | `0.013472305929956612` | below |
| `tail_p5` | `0.5` | `0.5928853754940712` | `0.25` | `0.26` | `0.8167` | `0.5736247747919976` | `0.021171880856351032` | below |
| `tail_p5` | `0.7` | `0.5418326693227091` | `0.32` | `0.27666666666666667` | `0.8100666666666667` | `0.5436504911640216` | `0.007734704822555832` | below |
| `tail_p10` | `0.2` | `0.5934065934065934` | `0.19` | `0.30666666666666664` | `0.8006333333333333` | `0.57212100029048` | `0.0010236150845098458` | below |
| `tail_p10` | `0.35` | `0.5555555555555556` | `0.3` | `0.2733333333333333` | `0.8210999999999999` | `0.598033114438401` | `0.0049457470304813105` | below |
| `tail_p10` | `0.5` | `0.5589519650655022` | `0.36` | `0.21666666666666667` | `0.8266` | `0.5800598883800064` | `0.008615919701945867` | below |
| `tail_p10` | `0.7` | `0.5365853658536586` | `0.34` | `0.26666666666666666` | `0.8107333333333333` | `0.5682896962645246` | `0.013270737777131572` | below |
| `tail_p25` | `0.2` | `0.6040816326530613` | `0.26` | `0.23666666666666666` | `0.8323333333333334` | `0.5939038151076249` | `0.009169227663376607` | below |
| `tail_p25` | `0.35` | `0.5929203539823009` | `0.33` | `0.19666666666666666` | `0.8486` | `0.6040971761468075` | `0.00823833503709704` | below |
| `tail_p25` | `0.5` | `0.5855855855855856` | `0.35` | `0.19` | `0.8436333333333333` | `0.6320450020362912` | `0.005647210889293991` | below |
| `tail_p25` | `0.7` | `0.5327510917030568` | `0.39` | `0.22666666666666666` | `0.8156666666666667` | `0.5889563538776119` | `0.012062790451317277` | below |
### receta / full_only / 1B_base_tech
Nested family `polarity_v2_subset`, wins `8`, recipe `polarity_v2_subset|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-`, CAL_ONLY p10 F1 `0.7403846153846154`.
- anchors `full_doc`: sep_ge_1 `113`, sep_ge_1_and_sign_flip `59`, polarity_dials `183`, tie_count `0`.
- anchors `clause_opt2c`: sep_ge_1 `4`, sep_ge_1_and_sign_flip `2`, polarity_dials `103`, tie_count `0`.
| family | w_f | CAL_ONLY p10 F1 | FRR | FAR | ROC-AUC | 5x5 F1 mean | 5x5 F1 std | versus TASK-013 CAL p10 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `dir1024_sig_sep` | `null` | `0.6298342541436464` | `0.43` | `0.08` | `0.9183333333333334` | `0.7576468022352496` | `0.007807769158098504` | below |
| `dir1024_sig_sep2` | `null` | `0.6630434782608695` | `0.39` | `0.07666666666666666` | `0.9208666666666667` | `0.761729444370299` | `0.004428530470952874` | below |
| `dir1024_clip_polboost` | `null` | `0.6373626373626373` | `0.42` | `0.08` | `0.9187333333333334` | `0.7672667757774141` | `0.0017928725286585076` | below |
| `polarity_v2_subset` | `null` | `0.7403846153846154` | `0.23` | `0.10333333333333333` | `0.9178` | `0.7513565819177839` | `0.01317622075551062` | equal |
| `base_repaired` | `null` | `0.5306122448979592` | `0.48` | `0.14666666666666667` | `0.8391` | `0.6240037187798382` | `0.008082653321499308` | below |
| `f2_l2` | `null` | `0.5` | `0.58` | `0.08666666666666667` | `0.8255` | `0.6119856972955663` | `0.005338406814710966` | below |
| `tail_p3` | `null` | `0.5454545454545454` | `0.46` | `0.14666666666666667` | `0.8090333333333333` | `0.5895429036270576` | `0.009134916054161581` | below |
| `tail_p5` | `null` | `0.5268817204301075` | `0.51` | `0.12333333333333334` | `0.8167666666666668` | `0.601112978993398` | `0.004628444149112287` | below |
| `tail_p10` | `null` | `0.5222222222222223` | `0.53` | `0.11` | `0.8238666666666665` | `0.6287598857861901` | `0.002872512072625054` | below |
| `tail_p25` | `null` | `0.48554913294797686` | `0.58` | `0.10333333333333333` | `0.8273666666666668` | `0.6188589085464086` | `0.010856866309680675` | below |
### receta / clauses / 1B_base_tech
Nested family `dir1024_sig_sep`, wins `6`, recipe `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20`, CAL_ONLY p10 F1 `0.8783068783068783`.
- anchors `full_doc`: sep_ge_1 `113`, sep_ge_1_and_sign_flip `59`, polarity_dials `183`, tie_count `0`.
- anchors `clause_opt2c`: sep_ge_1 `4`, sep_ge_1_and_sign_flip `2`, polarity_dials `103`, tie_count `0`.
| family | w_f | CAL_ONLY p10 F1 | FRR | FAR | ROC-AUC | 5x5 F1 mean | 5x5 F1 std | versus TASK-013 CAL p10 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `dir1024_sig_sep` | `0.2` | `0.8783068783068783` | `0.17` | `0.02` | `0.9792000000000001` | `0.8876191641515078` | `0.01354106871240532` | above |
| `dir1024_sig_sep` | `0.35` | `0.8571428571428571` | `0.22` | `0.013333333333333334` | `0.9805` | `0.8840915676615474` | `0.002380712362381221` | above |
| `dir1024_sig_sep` | `0.5` | `0.8135593220338984` | `0.28` | `0.016666666666666666` | `0.9721` | `0.7932653363736197` | `0.010045240494416853` | above |
| `dir1024_sig_sep` | `0.7` | `0.7374301675977654` | `0.34` | `0.043333333333333335` | `0.9530666666666667` | `0.7788900081795999` | `0.007540464921245311` | below |
| `dir1024_sig_sep2` | `0.2` | `0.8586387434554974` | `0.18` | `0.03` | `0.9785` | `0.8951332158021504` | `0.0031488909596789185` | above |
| `dir1024_sig_sep2` | `0.35` | `0.8524590163934426` | `0.22` | `0.016666666666666666` | `0.9802333333333333` | `0.884573984047446` | `0.00761143185498632` | above |
| `dir1024_sig_sep2` | `0.5` | `0.8` | `0.3` | `0.016666666666666666` | `0.9728666666666667` | `0.8158493568827601` | `0.005472683843628935` | above |
| `dir1024_sig_sep2` | `0.7` | `0.7540983606557377` | `0.31` | `0.04666666666666667` | `0.9543666666666667` | `0.7980562299081676` | `0.015073758188375001` | below |
| `dir1024_clip_polboost` | `0.2` | `0.8877551020408163` | `0.13` | `0.03` | `0.9778333333333333` | `0.8705569023235871` | `0.008787039291174713` | above |
| `dir1024_clip_polboost` | `0.35` | `0.8478260869565217` | `0.22` | `0.02` | `0.9786333333333332` | `0.8528382215324409` | `0.012970828948074133` | above |
| `dir1024_clip_polboost` | `0.5` | `0.7932960893854749` | `0.29` | `0.02666666666666667` | `0.9712999999999999` | `0.8083720175812354` | `0.01222075935120314` | below |
| `dir1024_clip_polboost` | `0.7` | `0.7540983606557377` | `0.31` | `0.04666666666666667` | `0.9521000000000001` | `0.78606730068296` | `0.013165216158357688` | below |
| `polarity_v2_subset` | `0.2` | `0.6854838709677419` | `0.15` | `0.21` | `0.9177666666666667` | `0.7228217960090394` | `0.010385126464211513` | below |
| `polarity_v2_subset` | `0.35` | `0.7904761904761904` | `0.17` | `0.09` | `0.9478` | `0.7867686991468994` | `0.010636259260183512` | below |
| `polarity_v2_subset` | `0.5` | `0.7981220657276995` | `0.15` | `0.09333333333333334` | `0.9525666666666667` | `0.7845709402740869` | `0.01054810935361685` | equal |
| `polarity_v2_subset` | `0.7` | `0.7684729064039408` | `0.22` | `0.08333333333333333` | `0.9429` | `0.7844715689822521` | `0.004776863970595715` | below |
| `base_repaired` | `0.2` | `0.6093189964157706` | `0.15` | `0.31333333333333335` | `0.8456333333333333` | `0.5846582328344226` | `0.005264764118864679` | below |
| `base_repaired` | `0.35` | `0.6468085106382979` | `0.24` | `0.19666666666666666` | `0.8791666666666667` | `0.6317149743643241` | `0.012748393174033775` | below |
| `base_repaired` | `0.5` | `0.6763285024154589` | `0.3` | `0.12333333333333334` | `0.8900666666666667` | `0.6693686177872225` | `0.012060600834223886` | below |
| `base_repaired` | `0.7` | `0.6082474226804123` | `0.41` | `0.11666666666666667` | `0.8752` | `0.6522784016171681` | `0.018263514537831604` | below |
| `f2_l2` | `0.2` | `0.6810810810810811` | `0.37` | `0.07333333333333333` | `0.8735333333333333` | `0.6640142270858445` | `0.0133475640441823` | below |
| `f2_l2` | `0.35` | `0.5620915032679739` | `0.57` | `0.03333333333333333` | `0.8832` | `0.7139972820811493` | `0.001541832087715984` | below |
| `f2_l2` | `0.5` | `0.5384615384615384` | `0.58` | `0.04666666666666667` | `0.8731666666666666` | `0.6778721652744261` | `0.009679889703171966` | below |
| `f2_l2` | `0.7` | `0.5365853658536586` | `0.56` | `0.06666666666666667` | `0.8523000000000001` | `0.6404338346286214` | `0.010804196687579743` | below |
| `tail_p3` | `0.2` | `0.5603112840466926` | `0.28` | `0.2833333333333333` | `0.7983666666666667` | `0.5800023055519671` | `0.00327148488371447` | below |
| `tail_p3` | `0.35` | `0.5643564356435643` | `0.43` | `0.15` | `0.8401333333333333` | `0.5835507485166415` | `0.007484448629323772` | below |
| `tail_p3` | `0.5` | `0.5979381443298969` | `0.42` | `0.12` | `0.845` | `0.6346334329979884` | `0.010221396237278258` | below |
| `tail_p3` | `0.7` | `0.59375` | `0.43` | `0.11666666666666667` | `0.8314333333333335` | `0.6021102449698875` | `0.007652415549268567` | below |
| `tail_p5` | `0.2` | `0.5702127659574469` | `0.33` | `0.22666666666666666` | `0.8213666666666667` | `0.5755832348049564` | `0.014458656051359646` | below |
| `tail_p5` | `0.35` | `0.59375` | `0.43` | `0.11666666666666667` | `0.8563666666666666` | `0.5937389865676719` | `0.014945143880921934` | below |
| `tail_p5` | `0.5` | `0.5978260869565217` | `0.45` | `0.09666666666666666` | `0.8574333333333333` | `0.6643311296145895` | `0.007136959741856059` | below |
| `tail_p5` | `0.7` | `0.5168539325842697` | `0.54` | `0.10666666666666667` | `0.8412333333333333` | `0.6388757978290608` | `0.006001064616545495` | below |
| `tail_p10` | `0.2` | `0.6037735849056604` | `0.36` | `0.16` | `0.8518333333333334` | `0.6000448362632061` | `0.00604679400646644` | below |
| `tail_p10` | `0.35` | `0.632183908045977` | `0.45` | `0.06333333333333334` | `0.8746666666666667` | `0.6567448153364049` | `0.010801597711728131` | below |
| `tail_p10` | `0.5` | `0.6101694915254238` | `0.46` | `0.07666666666666666` | `0.8689` | `0.6546797531470012` | `0.009262472282028516` | below |
| `tail_p10` | `0.7` | `0.5146198830409356` | `0.56` | `0.09` | `0.8486666666666667` | `0.6534135789062651` | `0.004992946196905659` | below |
| `tail_p25` | `0.2` | `0.6666666666666666` | `0.35` | `0.1` | `0.8749666666666667` | `0.6447690195338687` | `0.014194397121667783` | below |
| `tail_p25` | `0.35` | `0.6265060240963856` | `0.48` | `0.04666666666666667` | `0.8863666666666667` | `0.7126992647916909` | `0.0111894730861467` | below |
| `tail_p25` | `0.5` | `0.6153846153846154` | `0.48` | `0.056666666666666664` | `0.8762` | `0.6788115322346716` | `0.016584130937698123` | below |
| `tail_p25` | `0.7` | `0.5308641975308642` | `0.57` | `0.06333333333333334` | `0.8541666666666666` | `0.6649742148858907` | `0.004694298483032759` | below |
### receta / full_only / 1B_base_tech_noise
Nested family `dir1024_clip_polboost`, wins `16`, recipe `dir1024_clip_polboost|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-`, CAL_ONLY p10 F1 `0.6136363636363636`.
- anchors `full_doc`: sep_ge_1 `103`, sep_ge_1_and_sign_flip `52`, polarity_dials `182`, tie_count `0`.
- anchors `clause_opt2c`: sep_ge_1 `4`, sep_ge_1_and_sign_flip `1`, polarity_dials `102`, tie_count `0`.
| family | w_f | CAL_ONLY p10 F1 | FRR | FAR | ROC-AUC | 5x5 F1 mean | 5x5 F1 std | versus TASK-013 CAL p10 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `dir1024_sig_sep` | `null` | `0.6011560693641619` | `0.48` | `0.07` | `0.9169` | `0.7525121363031392` | `0.004381901383320419` | below |
| `dir1024_sig_sep2` | `null` | `0.6285714285714286` | `0.45` | `0.06666666666666667` | `0.9196` | `0.7582390669259412` | `0.004358223061938382` | below |
| `dir1024_clip_polboost` | `null` | `0.6136363636363636` | `0.46` | `0.07333333333333333` | `0.9180333333333333` | `0.7631017818257231` | `0.003814173208194929` | below |
| `polarity_v2_subset` | `null` | `0.7281553398058253` | `0.25` | `0.10333333333333333` | `0.9166333333333333` | `0.7369681785321662` | `0.011434096190879366` | below |
| `base_repaired` | `null` | `0.5333333333333333` | `0.48` | `0.14333333333333334` | `0.8411333333333333` | `0.6448105210889856` | `0.006893230875845998` | below |
| `f2_l2` | `null` | `0.5` | `0.58` | `0.08666666666666667` | `0.8255` | `0.6119856972955663` | `0.005338406814710966` | below |
| `tail_p3` | `null` | `0.5454545454545454` | `0.46` | `0.14666666666666667` | `0.8090333333333333` | `0.5895429036270576` | `0.009134916054161581` | below |
| `tail_p5` | `null` | `0.5268817204301075` | `0.51` | `0.12333333333333334` | `0.8167666666666668` | `0.601112978993398` | `0.004628444149112287` | below |
| `tail_p10` | `null` | `0.5222222222222223` | `0.53` | `0.11` | `0.8238666666666665` | `0.6287598857861901` | `0.002872512072625054` | below |
| `tail_p25` | `null` | `0.48554913294797686` | `0.58` | `0.10333333333333333` | `0.8273666666666668` | `0.6188589085464086` | `0.010856866309680675` | below |
### receta / clauses / 1B_base_tech_noise
Nested family `dir1024_sig_sep`, wins `6`, recipe `dir1024_sig_sep|additive|a=0.10|g=tail_p10|beta|b=0.00|y=-|r=full_doc|w=0.20`, CAL_ONLY p10 F1 `0.8648648648648649`.
- anchors `full_doc`: sep_ge_1 `103`, sep_ge_1_and_sign_flip `52`, polarity_dials `182`, tie_count `0`.
- anchors `clause_opt2c`: sep_ge_1 `4`, sep_ge_1_and_sign_flip `1`, polarity_dials `102`, tie_count `0`.
| family | w_f | CAL_ONLY p10 F1 | FRR | FAR | ROC-AUC | 5x5 F1 mean | 5x5 F1 std | versus TASK-013 CAL p10 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `dir1024_sig_sep` | `0.2` | `0.8770053475935828` | `0.18` | `0.016666666666666666` | `0.9808000000000001` | `0.8732215523805242` | `0.006605774854488848` | above |
| `dir1024_sig_sep` | `0.35` | `0.8444444444444444` | `0.24` | `0.013333333333333334` | `0.9806333333333332` | `0.8701087030797907` | `0.009177293073064249` | above |
| `dir1024_sig_sep` | `0.5` | `0.7906976744186046` | `0.32` | `0.013333333333333334` | `0.9719333333333333` | `0.8024974355807493` | `0.01035161902979946` | below |
| `dir1024_sig_sep` | `0.7` | `0.72` | `0.37` | `0.04` | `0.9525` | `0.7992889983263758` | `0.003852185638267321` | below |
| `dir1024_sig_sep2` | `0.2` | `0.8677248677248677` | `0.18` | `0.023333333333333334` | `0.9797333333333333` | `0.8905947108429798` | `0.007518723207685051` | above |
| `dir1024_sig_sep2` | `0.35` | `0.8314606741573034` | `0.26` | `0.013333333333333334` | `0.9804999999999999` | `0.8546759924381989` | `0.004444534460491762` | above |
| `dir1024_sig_sep2` | `0.5` | `0.7764705882352941` | `0.34` | `0.013333333333333334` | `0.9728666666666667` | `0.8077976420405559` | `0.0037345339645282333` | below |
| `dir1024_sig_sep2` | `0.7` | `0.7272727272727273` | `0.36` | `0.04` | `0.9532333333333334` | `0.8118961968335802` | `0.0007398643635995844` | below |
| `dir1024_clip_polboost` | `0.2` | `0.8571428571428571` | `0.19` | `0.02666666666666667` | `0.9785333333333335` | `0.8875817637399788` | `0.0037308422458504206` | above |
| `dir1024_clip_polboost` | `0.35` | `0.8444444444444444` | `0.24` | `0.013333333333333334` | `0.9795` | `0.8679050507477758` | `0.017182955191349318` | above |
| `dir1024_clip_polboost` | `0.5` | `0.7701149425287356` | `0.33` | `0.023333333333333334` | `0.9706666666666667` | `0.813806088560502` | `0.01687319082571311` | below |
| `dir1024_clip_polboost` | `0.7` | `0.7052023121387283` | `0.39` | `0.04` | `0.9513666666666667` | `0.7854927288723283` | `0.010445576994500407` | below |
| `polarity_v2_subset` | `0.2` | `0.6910569105691057` | `0.15` | `0.20333333333333334` | `0.9212` | `0.6906517038692105` | `0.012149433455224587` | below |
| `polarity_v2_subset` | `0.35` | `0.7922705314009661` | `0.18` | `0.08333333333333333` | `0.9501333333333333` | `0.7671722299685426` | `0.012709381524486371` | below |
| `polarity_v2_subset` | `0.5` | `0.7961165048543689` | `0.18` | `0.08` | `0.9512666666666667` | `0.8032640276685201` | `0.009510900714809395` | below |
| `polarity_v2_subset` | `0.7` | `0.7623762376237624` | `0.23` | `0.08333333333333333` | `0.9408333333333334` | `0.7746085063454922` | `0.010168125706777137` | below |
| `base_repaired` | `0.2` | `0.6028368794326241` | `0.15` | `0.3233333333333333` | `0.836` | `0.5875975818753203` | `0.0072644937704852905` | below |
| `base_repaired` | `0.35` | `0.6666666666666666` | `0.21` | `0.19333333333333333` | `0.8736333333333333` | `0.6562132568691309` | `0.003066286466003447` | below |
| `base_repaired` | `0.5` | `0.6372549019607843` | `0.35` | `0.13` | `0.8865666666666666` | `0.6773443365329748` | `0.006036176826319677` | below |
| `base_repaired` | `0.7` | `0.5789473684210527` | `0.45` | `0.11666666666666667` | `0.8737666666666667` | `0.6384145772045755` | `0.006644429628721253` | below |
| `f2_l2` | `0.2` | `0.6810810810810811` | `0.37` | `0.07333333333333333` | `0.8735333333333333` | `0.6640142270858445` | `0.0133475640441823` | below |
| `f2_l2` | `0.35` | `0.5620915032679739` | `0.57` | `0.03333333333333333` | `0.8832` | `0.7139972820811493` | `0.001541832087715984` | below |
| `f2_l2` | `0.5` | `0.5384615384615384` | `0.58` | `0.04666666666666667` | `0.8731666666666666` | `0.6778721652744261` | `0.009679889703171966` | below |
| `f2_l2` | `0.7` | `0.5365853658536586` | `0.56` | `0.06666666666666667` | `0.8523000000000001` | `0.6404338346286214` | `0.010804196687579743` | below |
| `tail_p3` | `0.2` | `0.5603112840466926` | `0.28` | `0.2833333333333333` | `0.7983666666666667` | `0.5800023055519671` | `0.00327148488371447` | below |
| `tail_p3` | `0.35` | `0.5643564356435643` | `0.43` | `0.15` | `0.8401333333333333` | `0.5835507485166415` | `0.007484448629323772` | below |
| `tail_p3` | `0.5` | `0.5979381443298969` | `0.42` | `0.12` | `0.845` | `0.6346334329979884` | `0.010221396237278258` | below |
| `tail_p3` | `0.7` | `0.59375` | `0.43` | `0.11666666666666667` | `0.8314333333333335` | `0.6021102449698875` | `0.007652415549268567` | below |
| `tail_p5` | `0.2` | `0.5702127659574469` | `0.33` | `0.22666666666666666` | `0.8213666666666667` | `0.5755832348049564` | `0.014458656051359646` | below |
| `tail_p5` | `0.35` | `0.59375` | `0.43` | `0.11666666666666667` | `0.8563666666666666` | `0.5937389865676719` | `0.014945143880921934` | below |
| `tail_p5` | `0.5` | `0.5978260869565217` | `0.45` | `0.09666666666666666` | `0.8574333333333333` | `0.6643311296145895` | `0.007136959741856059` | below |
| `tail_p5` | `0.7` | `0.5168539325842697` | `0.54` | `0.10666666666666667` | `0.8412333333333333` | `0.6388757978290608` | `0.006001064616545495` | below |
| `tail_p10` | `0.2` | `0.6037735849056604` | `0.36` | `0.16` | `0.8518333333333334` | `0.6000448362632061` | `0.00604679400646644` | below |
| `tail_p10` | `0.35` | `0.632183908045977` | `0.45` | `0.06333333333333334` | `0.8746666666666667` | `0.6567448153364049` | `0.010801597711728131` | below |
| `tail_p10` | `0.5` | `0.6101694915254238` | `0.46` | `0.07666666666666666` | `0.8689` | `0.6546797531470012` | `0.009262472282028516` | below |
| `tail_p10` | `0.7` | `0.5146198830409356` | `0.56` | `0.09` | `0.8486666666666667` | `0.6534135789062651` | `0.004992946196905659` | below |
| `tail_p25` | `0.2` | `0.6666666666666666` | `0.35` | `0.1` | `0.8749666666666667` | `0.6447690195338687` | `0.014194397121667783` | below |
| `tail_p25` | `0.35` | `0.6265060240963856` | `0.48` | `0.04666666666666667` | `0.8863666666666667` | `0.7126992647916909` | `0.0111894730861467` | below |
| `tail_p25` | `0.5` | `0.6153846153846154` | `0.48` | `0.056666666666666664` | `0.8762` | `0.6788115322346716` | `0.016584130937698123` | below |
| `tail_p25` | `0.7` | `0.5308641975308642` | `0.57` | `0.06333333333333334` | `0.8541666666666666` | `0.6649742148858907` | `0.004694298483032759` | below |
### receta / full_only / 1B_full
Nested family `dir1024_clip_polboost`, wins `23`, recipe `dir1024_clip_polboost|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-`, CAL_ONLY p10 F1 `0.6222222222222222`.
- anchors `full_doc`: sep_ge_1 `75`, sep_ge_1_and_sign_flip `39`, polarity_dials `168`, tie_count `0`.
- anchors `clause_opt2c`: sep_ge_1 `3`, sep_ge_1_and_sign_flip `2`, polarity_dials `90`, tie_count `0`.
| family | w_f | CAL_ONLY p10 F1 | FRR | FAR | ROC-AUC | 5x5 F1 mean | 5x5 F1 std | versus TASK-013 CAL p10 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `dir1024_sig_sep` | `null` | `0.6067415730337079` | `0.46` | `0.08` | `0.9153666666666667` | `0.7495726495726496` | `0.0035110420352895137` | below |
| `dir1024_sig_sep2` | `null` | `0.6214689265536724` | `0.45` | `0.07333333333333333` | `0.9169333333333334` | `0.7542918454935623` | `0.0023992145681328452` | below |
| `dir1024_clip_polboost` | `null` | `0.6222222222222222` | `0.44` | `0.08` | `0.9164666666666667` | `0.7615519399249061` | `0.007052429666207086` | below |
| `polarity_v2_subset` | `null` | `0.7064676616915423` | `0.29` | `0.1` | `0.9151` | `0.7451848890398116` | `0.0037045862350799223` | below |
| `base_repaired` | `null` | `0.5360824742268041` | `0.48` | `0.14` | `0.8391` | `0.6266847601408024` | `0.0050744827252147545` | below |
| `f2_l2` | `null` | `0.5` | `0.58` | `0.08666666666666667` | `0.8255` | `0.6119856972955663` | `0.005338406814710966` | below |
| `tail_p3` | `null` | `0.5454545454545454` | `0.46` | `0.14666666666666667` | `0.8090333333333333` | `0.5895429036270576` | `0.009134916054161581` | below |
| `tail_p5` | `null` | `0.5268817204301075` | `0.51` | `0.12333333333333334` | `0.8167666666666668` | `0.601112978993398` | `0.004628444149112287` | below |
| `tail_p10` | `null` | `0.5222222222222223` | `0.53` | `0.11` | `0.8238666666666665` | `0.6287598857861901` | `0.002872512072625054` | below |
| `tail_p25` | `null` | `0.48554913294797686` | `0.58` | `0.10333333333333333` | `0.8273666666666668` | `0.6188589085464086` | `0.010856866309680675` | below |
### receta / clauses / 1B_full
Nested family `dir1024_sig_sep`, wins `12`, recipe `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20`, CAL_ONLY p10 F1 `0.8829787234042553`.
- anchors `full_doc`: sep_ge_1 `75`, sep_ge_1_and_sign_flip `39`, polarity_dials `168`, tie_count `0`.
- anchors `clause_opt2c`: sep_ge_1 `3`, sep_ge_1_and_sign_flip `2`, polarity_dials `90`, tie_count `0`.
| family | w_f | CAL_ONLY p10 F1 | FRR | FAR | ROC-AUC | 5x5 F1 mean | 5x5 F1 std | versus TASK-013 CAL p10 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `dir1024_sig_sep` | `0.2` | `0.8829787234042553` | `0.17` | `0.016666666666666666` | `0.9791666666666666` | `0.8912696292338291` | `0.005149452129231724` | above |
| `dir1024_sig_sep` | `0.35` | `0.8379888268156425` | `0.25` | `0.013333333333333334` | `0.9788999999999999` | `0.8422789126081044` | `0.007973382105973722` | above |
| `dir1024_sig_sep` | `0.5` | `0.7816091954022989` | `0.32` | `0.02` | `0.9698666666666667` | `0.8016513743268223` | `0.012171556447113792` | below |
| `dir1024_sig_sep` | `0.7` | `0.7231638418079096` | `0.36` | `0.043333333333333335` | `0.9501666666666667` | `0.7672803833006853` | `0.009405920711506794` | below |
| `dir1024_sig_sep2` | `0.2` | `0.8481675392670157` | `0.19` | `0.03333333333333333` | `0.9783333333333334` | `0.8720974721059471` | `0.00835374615024206` | above |
| `dir1024_sig_sep2` | `0.35` | `0.8248587570621468` | `0.27` | `0.013333333333333334` | `0.9782333333333333` | `0.8564847839159813` | `0.011362678084852517` | above |
| `dir1024_sig_sep2` | `0.5` | `0.797752808988764` | `0.29` | `0.023333333333333334` | `0.9696333333333333` | `0.7956116251010829` | `0.012869340717554823` | below |
| `dir1024_sig_sep2` | `0.7` | `0.711864406779661` | `0.37` | `0.04666666666666667` | `0.9503` | `0.765041349041349` | `0.0130457929682537` | below |
| `dir1024_clip_polboost` | `0.2` | `0.8717948717948718` | `0.15` | `0.03333333333333333` | `0.9773666666666666` | `0.888888888888889` | `1.2412670766236366e-16` | above |
| `dir1024_clip_polboost` | `0.35` | `0.8369565217391305` | `0.23` | `0.023333333333333334` | `0.9774666666666667` | `0.8394210756303538` | `0.006911725146371975` | above |
| `dir1024_clip_polboost` | `0.5` | `0.7865168539325843` | `0.3` | `0.02666666666666667` | `0.9696333333333333` | `0.7909882630785391` | `0.013043694707132267` | below |
| `dir1024_clip_polboost` | `0.7` | `0.711864406779661` | `0.37` | `0.04666666666666667` | `0.9497333333333333` | `0.7742893540195214` | `0.007881393367348439` | below |
| `polarity_v2_subset` | `0.2` | `0.6721311475409836` | `0.18` | `0.20666666666666667` | `0.9152333333333332` | `0.6925618196224809` | `0.013761133865287763` | below |
| `polarity_v2_subset` | `0.35` | `0.7522935779816514` | `0.18` | `0.12` | `0.9437666666666666` | `0.7552186714783011` | `0.010134591667535034` | below |
| `polarity_v2_subset` | `0.5` | `0.780952380952381` | `0.18` | `0.09333333333333334` | `0.948` | `0.7747168032348681` | `0.014901801193569975` | below |
| `polarity_v2_subset` | `0.7` | `0.7707317073170732` | `0.21` | `0.08666666666666667` | `0.9398333333333333` | `0.7649257759939645` | `0.001520502271357542` | below |
| `base_repaired` | `0.2` | `0.6068965517241379` | `0.12` | `0.34` | `0.8378666666666668` | `0.6059969714485252` | `0.010073698360980545` | below |
| `base_repaired` | `0.35` | `0.6724890829694323` | `0.23` | `0.17333333333333334` | `0.8731666666666666` | `0.6661244012182287` | `0.005308453363999398` | below |
| `base_repaired` | `0.5` | `0.6331658291457286` | `0.37` | `0.12` | `0.8856999999999999` | `0.6650491658151326` | `0.018184224181272125` | below |
| `base_repaired` | `0.7` | `0.582010582010582` | `0.45` | `0.11333333333333333` | `0.8710666666666667` | `0.6423778974017714` | `0.007976759832366974` | below |
| `f2_l2` | `0.2` | `0.6810810810810811` | `0.37` | `0.07333333333333333` | `0.8735333333333333` | `0.6640142270858445` | `0.0133475640441823` | below |
| `f2_l2` | `0.35` | `0.5620915032679739` | `0.57` | `0.03333333333333333` | `0.8832` | `0.7139972820811493` | `0.001541832087715984` | below |
| `f2_l2` | `0.5` | `0.5384615384615384` | `0.58` | `0.04666666666666667` | `0.8731666666666666` | `0.6778721652744261` | `0.009679889703171966` | below |
| `f2_l2` | `0.7` | `0.5365853658536586` | `0.56` | `0.06666666666666667` | `0.8523000000000001` | `0.6404338346286214` | `0.010804196687579743` | below |
| `tail_p3` | `0.2` | `0.5603112840466926` | `0.28` | `0.2833333333333333` | `0.7983666666666667` | `0.5800023055519671` | `0.00327148488371447` | below |
| `tail_p3` | `0.35` | `0.5643564356435643` | `0.43` | `0.15` | `0.8401333333333333` | `0.5835507485166415` | `0.007484448629323772` | below |
| `tail_p3` | `0.5` | `0.5979381443298969` | `0.42` | `0.12` | `0.845` | `0.6346334329979884` | `0.010221396237278258` | below |
| `tail_p3` | `0.7` | `0.59375` | `0.43` | `0.11666666666666667` | `0.8314333333333335` | `0.6021102449698875` | `0.007652415549268567` | below |
| `tail_p5` | `0.2` | `0.5702127659574469` | `0.33` | `0.22666666666666666` | `0.8213666666666667` | `0.5755832348049564` | `0.014458656051359646` | below |
| `tail_p5` | `0.35` | `0.59375` | `0.43` | `0.11666666666666667` | `0.8563666666666666` | `0.5937389865676719` | `0.014945143880921934` | below |
| `tail_p5` | `0.5` | `0.5978260869565217` | `0.45` | `0.09666666666666666` | `0.8574333333333333` | `0.6643311296145895` | `0.007136959741856059` | below |
| `tail_p5` | `0.7` | `0.5168539325842697` | `0.54` | `0.10666666666666667` | `0.8412333333333333` | `0.6388757978290608` | `0.006001064616545495` | below |
| `tail_p10` | `0.2` | `0.6037735849056604` | `0.36` | `0.16` | `0.8518333333333334` | `0.6000448362632061` | `0.00604679400646644` | below |
| `tail_p10` | `0.35` | `0.632183908045977` | `0.45` | `0.06333333333333334` | `0.8746666666666667` | `0.6567448153364049` | `0.010801597711728131` | below |
| `tail_p10` | `0.5` | `0.6101694915254238` | `0.46` | `0.07666666666666666` | `0.8689` | `0.6546797531470012` | `0.009262472282028516` | below |
| `tail_p10` | `0.7` | `0.5146198830409356` | `0.56` | `0.09` | `0.8486666666666667` | `0.6534135789062651` | `0.004992946196905659` | below |
| `tail_p25` | `0.2` | `0.6666666666666666` | `0.35` | `0.1` | `0.8749666666666667` | `0.6447690195338687` | `0.014194397121667783` | below |
| `tail_p25` | `0.35` | `0.6265060240963856` | `0.48` | `0.04666666666666667` | `0.8863666666666667` | `0.7126992647916909` | `0.0111894730861467` | below |
| `tail_p25` | `0.5` | `0.6153846153846154` | `0.48` | `0.056666666666666664` | `0.8762` | `0.6788115322346716` | `0.016584130937698123` | below |
| `tail_p25` | `0.7` | `0.5308641975308642` | `0.57` | `0.06333333333333334` | `0.8541666666666666` | `0.6649742148858907` | `0.004694298483032759` | below |
### receta / full_only / 1B_full_v3
Nested family `polarity_v2_subset`, wins `20`, recipe `polarity_v2_subset|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-`, CAL_ONLY p10 F1 `0.7164179104477612`.
- anchors `full_doc`: sep_ge_1 `79`, sep_ge_1_and_sign_flip `42`, polarity_dials `168`, tie_count `0`.
- anchors `clause_opt2c`: sep_ge_1 `2`, sep_ge_1_and_sign_flip `1`, polarity_dials `86`, tie_count `0`.
| family | w_f | CAL_ONLY p10 F1 | FRR | FAR | ROC-AUC | 5x5 F1 mean | 5x5 F1 std | versus TASK-013 CAL p10 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `dir1024_sig_sep` | `null` | `0.5977011494252874` | `0.48` | `0.07333333333333333` | `0.9147666666666667` | `0.7328585274466926` | `0.004901380015899786` | below |
| `dir1024_sig_sep2` | `null` | `0.6206896551724138` | `0.46` | `0.06666666666666667` | `0.9165` | `0.7502435975829422` | `0.005339757289966313` | below |
| `dir1024_clip_polboost` | `null` | `0.6127167630057804` | `0.47` | `0.06666666666666667` | `0.9175666666666666` | `0.755990356848579` | `0.009690594870458287` | below |
| `polarity_v2_subset` | `null` | `0.7164179104477612` | `0.28` | `0.09666666666666666` | `0.9227666666666666` | `0.7482918293841845` | `0.010255171890646748` | below |
| `base_repaired` | `null` | `0.538860103626943` | `0.48` | `0.13666666666666666` | `0.8424666666666667` | `0.6271553380888548` | `0.00869658326788419` | below |
| `f2_l2` | `null` | `0.5` | `0.58` | `0.08666666666666667` | `0.8255` | `0.6119856972955663` | `0.005338406814710966` | below |
| `tail_p3` | `null` | `0.5454545454545454` | `0.46` | `0.14666666666666667` | `0.8090333333333333` | `0.5895429036270576` | `0.009134916054161581` | below |
| `tail_p5` | `null` | `0.5268817204301075` | `0.51` | `0.12333333333333334` | `0.8167666666666668` | `0.601112978993398` | `0.004628444149112287` | below |
| `tail_p10` | `null` | `0.5222222222222223` | `0.53` | `0.11` | `0.8238666666666665` | `0.6287598857861901` | `0.002872512072625054` | below |
| `tail_p25` | `null` | `0.48554913294797686` | `0.58` | `0.10333333333333333` | `0.8273666666666668` | `0.6188589085464086` | `0.010856866309680675` | below |
### receta / clauses / 1B_full_v3
Nested family `dir1024_sig_sep`, wins `9`, recipe `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20`, CAL_ONLY p10 F1 `0.8770053475935828`.
- anchors `full_doc`: sep_ge_1 `79`, sep_ge_1_and_sign_flip `42`, polarity_dials `168`, tie_count `0`.
- anchors `clause_opt2c`: sep_ge_1 `2`, sep_ge_1_and_sign_flip `1`, polarity_dials `86`, tie_count `0`.
| family | w_f | CAL_ONLY p10 F1 | FRR | FAR | ROC-AUC | 5x5 F1 mean | 5x5 F1 std | versus TASK-013 CAL p10 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `dir1024_sig_sep` | `0.2` | `0.8770053475935828` | `0.18` | `0.016666666666666666` | `0.9802333333333333` | `0.8746050178972586` | `0.0033258414466764102` | above |
| `dir1024_sig_sep` | `0.35` | `0.8379888268156425` | `0.25` | `0.013333333333333334` | `0.9797` | `0.8528704126694077` | `0.02194712898250757` | above |
| `dir1024_sig_sep` | `0.5` | `0.7816091954022989` | `0.32` | `0.02` | `0.9696333333333333` | `0.7924480870032704` | `0.007266315294420035` | below |
| `dir1024_sig_sep` | `0.7` | `0.6419753086419753` | `0.48` | `0.03333333333333333` | `0.9502` | `0.7961693167450965` | `0.0033456977849287252` | below |
| `dir1024_sig_sep2` | `0.2` | `0.8631578947368421` | `0.18` | `0.02666666666666667` | `0.9794666666666667` | `0.8791071951416246` | `0.002827673763805903` | above |
| `dir1024_sig_sep2` | `0.35` | `0.8248587570621468` | `0.27` | `0.013333333333333334` | `0.9791` | `0.8721439859525901` | `0.002324719145576212` | above |
| `dir1024_sig_sep2` | `0.5` | `0.7674418604651163` | `0.34` | `0.02` | `0.9702000000000001` | `0.7975897711029155` | `0.007626267434313157` | below |
| `dir1024_sig_sep2` | `0.7` | `0.7167630057803468` | `0.38` | `0.03666666666666667` | `0.9511333333333334` | `0.7798026526630645` | `0.018210111265616072` | below |
| `dir1024_clip_polboost` | `0.2` | `0.8704663212435233` | `0.16` | `0.03` | `0.9778666666666667` | `0.8496321599814968` | `0.00977545044050942` | above |
| `dir1024_clip_polboost` | `0.35` | `0.8333333333333334` | `0.25` | `0.016666666666666666` | `0.9784666666666666` | `0.8589107760688941` | `0.005881724047001731` | above |
| `dir1024_clip_polboost` | `0.5` | `0.7771428571428571` | `0.32` | `0.023333333333333334` | `0.9689333333333333` | `0.7927303621367129` | `0.011412469074646638` | below |
| `dir1024_clip_polboost` | `0.7` | `0.6941176470588235` | `0.41` | `0.03666666666666667` | `0.9498333333333334` | `0.7851655681095334` | `0.0076065525968897684` | below |
| `polarity_v2_subset` | `0.2` | `0.6919831223628692` | `0.18` | `0.18333333333333332` | `0.9139333333333334` | `0.7101594643869824` | `0.014834715995253022` | below |
| `polarity_v2_subset` | `0.35` | `0.7729468599033816` | `0.2` | `0.09` | `0.9470333333333334` | `0.7737555059074145` | `0.009926346228307976` | below |
| `polarity_v2_subset` | `0.5` | `0.7960199004975125` | `0.2` | `0.07` | `0.9515666666666667` | `0.7942198444608576` | `0.014750856139194881` | below |
| `polarity_v2_subset` | `0.7` | `0.7623762376237624` | `0.23` | `0.08333333333333333` | `0.9440333333333333` | `0.7930769230769231` | `0.006319875663521186` | below |
| `base_repaired` | `0.2` | `0.6214285714285714` | `0.13` | `0.31` | `0.8501666666666667` | `0.6177274309592293` | `0.010275250752345118` | below |
| `base_repaired` | `0.35` | `0.6607929515418502` | `0.25` | `0.17333333333333334` | `0.8857333333333333` | `0.6625419582545206` | `0.011440938061101996` | below |
| `base_repaired` | `0.5` | `0.6859903381642513` | `0.29` | `0.12` | `0.8957666666666666` | `0.6834130752673222` | `0.008778313712864734` | below |
| `base_repaired` | `0.7` | `0.59375` | `0.43` | `0.11666666666666667` | `0.8802666666666666` | `0.6765228263282739` | `0.00735915084119285` | below |
| `f2_l2` | `0.2` | `0.6810810810810811` | `0.37` | `0.07333333333333333` | `0.8735333333333333` | `0.6640142270858445` | `0.0133475640441823` | below |
| `f2_l2` | `0.35` | `0.5620915032679739` | `0.57` | `0.03333333333333333` | `0.8832` | `0.7139972820811493` | `0.001541832087715984` | below |
| `f2_l2` | `0.5` | `0.5384615384615384` | `0.58` | `0.04666666666666667` | `0.8731666666666666` | `0.6778721652744261` | `0.009679889703171966` | below |
| `f2_l2` | `0.7` | `0.5365853658536586` | `0.56` | `0.06666666666666667` | `0.8523000000000001` | `0.6404338346286214` | `0.010804196687579743` | below |
| `tail_p3` | `0.2` | `0.5603112840466926` | `0.28` | `0.2833333333333333` | `0.7983666666666667` | `0.5800023055519671` | `0.00327148488371447` | below |
| `tail_p3` | `0.35` | `0.5643564356435643` | `0.43` | `0.15` | `0.8401333333333333` | `0.5835507485166415` | `0.007484448629323772` | below |
| `tail_p3` | `0.5` | `0.5979381443298969` | `0.42` | `0.12` | `0.845` | `0.6346334329979884` | `0.010221396237278258` | below |
| `tail_p3` | `0.7` | `0.59375` | `0.43` | `0.11666666666666667` | `0.8314333333333335` | `0.6021102449698875` | `0.007652415549268567` | below |
| `tail_p5` | `0.2` | `0.5702127659574469` | `0.33` | `0.22666666666666666` | `0.8213666666666667` | `0.5755832348049564` | `0.014458656051359646` | below |
| `tail_p5` | `0.35` | `0.59375` | `0.43` | `0.11666666666666667` | `0.8563666666666666` | `0.5937389865676719` | `0.014945143880921934` | below |
| `tail_p5` | `0.5` | `0.5978260869565217` | `0.45` | `0.09666666666666666` | `0.8574333333333333` | `0.6643311296145895` | `0.007136959741856059` | below |
| `tail_p5` | `0.7` | `0.5168539325842697` | `0.54` | `0.10666666666666667` | `0.8412333333333333` | `0.6388757978290608` | `0.006001064616545495` | below |
| `tail_p10` | `0.2` | `0.6037735849056604` | `0.36` | `0.16` | `0.8518333333333334` | `0.6000448362632061` | `0.00604679400646644` | below |
| `tail_p10` | `0.35` | `0.632183908045977` | `0.45` | `0.06333333333333334` | `0.8746666666666667` | `0.6567448153364049` | `0.010801597711728131` | below |
| `tail_p10` | `0.5` | `0.6101694915254238` | `0.46` | `0.07666666666666666` | `0.8689` | `0.6546797531470012` | `0.009262472282028516` | below |
| `tail_p10` | `0.7` | `0.5146198830409356` | `0.56` | `0.09` | `0.8486666666666667` | `0.6534135789062651` | `0.004992946196905659` | below |
| `tail_p25` | `0.2` | `0.6666666666666666` | `0.35` | `0.1` | `0.8749666666666667` | `0.6447690195338687` | `0.014194397121667783` | below |
| `tail_p25` | `0.35` | `0.6265060240963856` | `0.48` | `0.04666666666666667` | `0.8863666666666667` | `0.7126992647916909` | `0.0111894730861467` | below |
| `tail_p25` | `0.5` | `0.6153846153846154` | `0.48` | `0.056666666666666664` | `0.8762` | `0.6788115322346716` | `0.016584130937698123` | below |
| `tail_p25` | `0.7` | `0.5308641975308642` | `0.57` | `0.06333333333333334` | `0.8541666666666666` | `0.6649742148858907` | `0.004694298483032759` | below |

## 4. Guardrail and S_struct ablations

Guard-only keeps the headline family, w_f, and struct reduction, with alpha above zero, beta at zero, and gamma null. Struct-only keeps that same pairing with identity coupling, a null guard, alpha at zero, and either beta above zero or a gamma value. `[HOLDOUT_MAX_SCAN]` is the maximum stored CAL_ONLY p10 F1 in `grid_cal_only`. Choosing it uses holdout F1, so it is not the nested headline and it is not `[ORACLE_UPPER_BOUND]`.
### python / full_only / 1B_base_tech
Grid rows 1170. Rows whose CAL_ONLY p10 F1 is below the frozen TASK-013 value: 59. Both counts are computed from the stored grid.
- Headline `dir1024_sig_sep|identity|a=0.00|g=-|gamma|b=0.00|y=0.10|r=full_doc|w=-` F1 `0.728110599078341`.
- Paired alpha=0 beta=0 `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` F1 `0.6929824561403509` is above the headline when the headline is compared with this row.
- Paired guard-only `dir1024_sig_sep|multiplicative|a=0.10|g=f2_l2|beta|b=0.00|y=-|r=full_doc|w=-` F1 `0.6964285714285714`.
- Paired struct-only `dir1024_sig_sep|identity|a=0.00|g=-|gamma|b=0.00|y=0.10|r=full_doc|w=-` F1 `0.728110599078341`.
- `[HOLDOUT_MAX_SCAN]` `dir1024_sig_sep|identity|a=0.00|g=-|gamma|b=0.00|y=0.10|r=full_doc|w=-` F1 `0.728110599078341`.
S_struct latency (microseconds per score() call on holdout strings): combined p50 `19.125` us, p99 `194.42477999999988` us. full_doc n `400` p50 `42.521` p99 `884.7728299999999`. clause_opt2c n `1968` p50 `17.4795` p99 `37.734469999999966`.
Per-feature firing on the focus subtypes, plus in-domain rows whose full_doc `n_below_1` is not zero:
- `code_snippet` `IN_DOMAIN_VALID` n `6` full_doc mean `0.935817090297094` n_below_1 `6` features `char_shannon_entropy` `3`, `letter_ratio` `5`, `punct_ratio` `2`; min_full_clause mean `0.10852127782385196` n_below_1 `6` features `char_shannon_entropy` `6`, `digit_ratio` `4`, `letter_ratio` `6`, `punct_ratio` `6`, `rare_nonletter_char_rate` `1`.
- `dilution_80_20` `HYBRID_BOUNDARY` n `10` full_doc mean `1.0` n_below_1 `0` features `none`; min_full_clause mean `0.9280794716528421` n_below_1 `5` features `char_shannon_entropy` `1`, `digit_ratio` `2`, `foreign_connector_ratio` `1`, `rare_nonletter_char_rate` `2`, `target_connector_ratio` `1`.
- `extreme_short_punct` `ADVERSARIAL_FUZZING` n `10` full_doc mean `0.02447790438092962` n_below_1 `10` features `char_shannon_entropy` `10`, `digit_ratio` `1`, `letter_ratio` `10`, `max_repeated_punct_run` `2`, `punct_ratio` `10`, `rare_nonletter_char_rate` `2`; min_full_clause mean `0.02447790438092962` n_below_1 `10` features `char_shannon_entropy` `10`, `digit_ratio` `1`, `letter_ratio` `10`, `max_repeated_punct_run` `2`, `punct_ratio` `10`, `rare_nonletter_char_rate` `4`.
- `homoglyph_zwsp_fullwidth` `ADVERSARIAL_FUZZING` n `12` full_doc mean `0.021689799610091643` n_below_1 `12` features `char_shannon_entropy` `1`, `foreign_connector_ratio` `4`, `max_repeated_punct_run` `4`, `non_latin_or_control_unicode_ratio` `12`, `punct_ratio` `4`, `rare_nonletter_char_rate` `6`, `symbol_ratio` `12`; min_full_clause mean `0.021689799610091643` n_below_1 `12` features `char_shannon_entropy` `1`, `foreign_connector_ratio` `4`, `max_repeated_punct_run` `4`, `non_latin_or_control_unicode_ratio` `12`, `punct_ratio` `4`, `rare_nonletter_char_rate` `6`, `symbol_ratio` `12`.
- `long_architecture_guide` `IN_DOMAIN_VALID` n `10` full_doc mean `0.9884339293608242` n_below_1 `1` features `rare_nonletter_char_rate` `1`; min_full_clause mean `0.933245058270568` n_below_1 `6` features `char_shannon_entropy` `2`, `digit_ratio` `2`, `rare_nonletter_char_rate` `3`, `symbol_ratio` `1`.
- `long_debugging_walkthrough` `IN_DOMAIN_VALID` n `10` full_doc mean `0.9755933094990719` n_below_1 `4` features `char_shannon_entropy` `3`, `rare_nonletter_char_rate` `1`; min_full_clause mean `0.5965870562114504` n_below_1 `9` features `char_shannon_entropy` `6`, `digit_ratio` `4`, `foreign_connector_ratio` `3`, `letter_ratio` `3`, `punct_ratio` `3`, `rare_nonletter_char_rate` `2`.
- `near_ood_neighbor` `HYBRID_BOUNDARY` n `12` full_doc mean `0.8412424808778044` n_below_1 `5` features `char_shannon_entropy` `1`, `rare_nonletter_char_rate` `4`; min_full_clause mean `0.8117779686522985` n_below_1 `7` features `char_shannon_entropy` `2`, `digit_ratio` `1`, `rare_nonletter_char_rate` `5`.
- `packaging_env` `IN_DOMAIN_VALID` n `6` full_doc mean `0.9994488296631068` n_below_1 `1` features `punct_ratio` `1`; min_full_clause mean `0.9791240842042014` n_below_1 `2` features `punct_ratio` `1`, `rare_nonletter_char_rate` `1`.
- `pytest_testing` `IN_DOMAIN_VALID` n `8` full_doc mean `0.9997378614300055` n_below_1 `1` features `punct_ratio` `1`; min_full_clause mean `0.9692507432416474` n_below_1 `3` features `punct_ratio` `1`, `rare_nonletter_char_rate` `2`.
- `short_idiom_query` `IN_DOMAIN_VALID` n `20` full_doc mean `0.9119852571312421` n_below_1 `16` features `char_shannon_entropy` `5`, `digit_ratio` `1`, `letter_ratio` `5`, `max_repeated_punct_run` `14`, `punct_ratio` `14`; min_full_clause mean `0.9119852571312421` n_below_1 `16` features `char_shannon_entropy` `6`, `digit_ratio` `1`, `letter_ratio` `5`, `max_repeated_punct_run` `14`, `punct_ratio` `14`.
- `traceback_debugging` `IN_DOMAIN_VALID` n `8` full_doc mean `0.9949947951096993` n_below_1 `3` features `char_shannon_entropy` `1`, `punct_ratio` `2`; min_full_clause mean `0.96809982555115` n_below_1 `5` features `char_shannon_entropy` `2`, `punct_ratio` `2`, `rare_nonletter_char_rate` `1`, `target_connector_ratio` `1`.
- `typing_protocol` `IN_DOMAIN_VALID` n `8` full_doc mean `0.9996221914320963` n_below_1 `1` features `punct_ratio` `1`; min_full_clause mean `0.9996221914320963` n_below_1 `1` features `punct_ratio` `1`.
- `panaderia_fermentacion` is absent from `struct_firing` on this cell.
- `diagnostico_pasteleria_panaderia` is absent from `struct_firing` on this cell.
- `smuggle_recipe_footnote` is absent from `struct_firing` on this cell.
### python / clauses / 1B_base_tech
Grid rows 9360. Rows whose CAL_ONLY p10 F1 is below the frozen TASK-013 value: 1092. Both counts are computed from the stored grid.
- Headline `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.20|y=-|r=full_doc|w=0.50` F1 `0.8159203980099502`.
- Paired alpha=0 beta=0 `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` F1 `0.7420814479638009` is above the headline when the headline is compared with this row.
- Paired guard-only `dir1024_sig_sep|multiplicative|a=0.15|g=tail_p5|beta|b=0.00|y=-|r=full_doc|w=0.50` F1 `0.7601809954751131`.
- Paired struct-only `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.20|y=-|r=full_doc|w=0.50` F1 `0.8159203980099502`.
- `[HOLDOUT_MAX_SCAN]` `dir1024_clip_polboost|multiplicative|a=0.20|g=tail_p25|beta|b=0.20|y=-|r=full_doc|w=0.50` F1 `0.8217821782178217`.
S_struct latency (microseconds per score() call on holdout strings): combined p50 `19.125` us, p99 `194.42477999999988` us. full_doc n `400` p50 `42.521` p99 `884.7728299999999`. clause_opt2c n `1968` p50 `17.4795` p99 `37.734469999999966`.
Per-feature firing on the focus subtypes, plus in-domain rows whose full_doc `n_below_1` is not zero:
- `code_snippet` `IN_DOMAIN_VALID` n `6` full_doc mean `0.935817090297094` n_below_1 `6` features `char_shannon_entropy` `3`, `letter_ratio` `5`, `punct_ratio` `2`; min_full_clause mean `0.10852127782385196` n_below_1 `6` features `char_shannon_entropy` `6`, `digit_ratio` `4`, `letter_ratio` `6`, `punct_ratio` `6`, `rare_nonletter_char_rate` `1`.
- `dilution_80_20` `HYBRID_BOUNDARY` n `10` full_doc mean `1.0` n_below_1 `0` features `none`; min_full_clause mean `0.9280794716528421` n_below_1 `5` features `char_shannon_entropy` `1`, `digit_ratio` `2`, `foreign_connector_ratio` `1`, `rare_nonletter_char_rate` `2`, `target_connector_ratio` `1`.
- `extreme_short_punct` `ADVERSARIAL_FUZZING` n `10` full_doc mean `0.02447790438092962` n_below_1 `10` features `char_shannon_entropy` `10`, `digit_ratio` `1`, `letter_ratio` `10`, `max_repeated_punct_run` `2`, `punct_ratio` `10`, `rare_nonletter_char_rate` `2`; min_full_clause mean `0.02447790438092962` n_below_1 `10` features `char_shannon_entropy` `10`, `digit_ratio` `1`, `letter_ratio` `10`, `max_repeated_punct_run` `2`, `punct_ratio` `10`, `rare_nonletter_char_rate` `4`.
- `homoglyph_zwsp_fullwidth` `ADVERSARIAL_FUZZING` n `12` full_doc mean `0.021689799610091643` n_below_1 `12` features `char_shannon_entropy` `1`, `foreign_connector_ratio` `4`, `max_repeated_punct_run` `4`, `non_latin_or_control_unicode_ratio` `12`, `punct_ratio` `4`, `rare_nonletter_char_rate` `6`, `symbol_ratio` `12`; min_full_clause mean `0.021689799610091643` n_below_1 `12` features `char_shannon_entropy` `1`, `foreign_connector_ratio` `4`, `max_repeated_punct_run` `4`, `non_latin_or_control_unicode_ratio` `12`, `punct_ratio` `4`, `rare_nonletter_char_rate` `6`, `symbol_ratio` `12`.
- `long_architecture_guide` `IN_DOMAIN_VALID` n `10` full_doc mean `0.9884339293608242` n_below_1 `1` features `rare_nonletter_char_rate` `1`; min_full_clause mean `0.933245058270568` n_below_1 `6` features `char_shannon_entropy` `2`, `digit_ratio` `2`, `rare_nonletter_char_rate` `3`, `symbol_ratio` `1`.
- `long_debugging_walkthrough` `IN_DOMAIN_VALID` n `10` full_doc mean `0.9755933094990719` n_below_1 `4` features `char_shannon_entropy` `3`, `rare_nonletter_char_rate` `1`; min_full_clause mean `0.5965870562114504` n_below_1 `9` features `char_shannon_entropy` `6`, `digit_ratio` `4`, `foreign_connector_ratio` `3`, `letter_ratio` `3`, `punct_ratio` `3`, `rare_nonletter_char_rate` `2`.
- `near_ood_neighbor` `HYBRID_BOUNDARY` n `12` full_doc mean `0.8412424808778044` n_below_1 `5` features `char_shannon_entropy` `1`, `rare_nonletter_char_rate` `4`; min_full_clause mean `0.8117779686522985` n_below_1 `7` features `char_shannon_entropy` `2`, `digit_ratio` `1`, `rare_nonletter_char_rate` `5`.
- `packaging_env` `IN_DOMAIN_VALID` n `6` full_doc mean `0.9994488296631068` n_below_1 `1` features `punct_ratio` `1`; min_full_clause mean `0.9791240842042014` n_below_1 `2` features `punct_ratio` `1`, `rare_nonletter_char_rate` `1`.
- `pytest_testing` `IN_DOMAIN_VALID` n `8` full_doc mean `0.9997378614300055` n_below_1 `1` features `punct_ratio` `1`; min_full_clause mean `0.9692507432416474` n_below_1 `3` features `punct_ratio` `1`, `rare_nonletter_char_rate` `2`.
- `short_idiom_query` `IN_DOMAIN_VALID` n `20` full_doc mean `0.9119852571312421` n_below_1 `16` features `char_shannon_entropy` `5`, `digit_ratio` `1`, `letter_ratio` `5`, `max_repeated_punct_run` `14`, `punct_ratio` `14`; min_full_clause mean `0.9119852571312421` n_below_1 `16` features `char_shannon_entropy` `6`, `digit_ratio` `1`, `letter_ratio` `5`, `max_repeated_punct_run` `14`, `punct_ratio` `14`.
- `traceback_debugging` `IN_DOMAIN_VALID` n `8` full_doc mean `0.9949947951096993` n_below_1 `3` features `char_shannon_entropy` `1`, `punct_ratio` `2`; min_full_clause mean `0.96809982555115` n_below_1 `5` features `char_shannon_entropy` `2`, `punct_ratio` `2`, `rare_nonletter_char_rate` `1`, `target_connector_ratio` `1`.
- `typing_protocol` `IN_DOMAIN_VALID` n `8` full_doc mean `0.9996221914320963` n_below_1 `1` features `punct_ratio` `1`; min_full_clause mean `0.9996221914320963` n_below_1 `1` features `punct_ratio` `1`.
- `panaderia_fermentacion` is absent from `struct_firing` on this cell.
- `diagnostico_pasteleria_panaderia` is absent from `struct_firing` on this cell.
- `smuggle_recipe_footnote` is absent from `struct_firing` on this cell.
### python / full_only / 1B_base_tech_noise
Grid rows 1170. Rows whose CAL_ONLY p10 F1 is below the frozen TASK-013 value: 57. Both counts are computed from the stored grid.
- Headline `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.05|y=-|r=full_doc|w=-` F1 `0.6991150442477876`.
- Paired alpha=0 beta=0 `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` F1 `0.6810344827586207` is above the headline when the headline is compared with this row.
- Paired guard-only `dir1024_sig_sep|additive|a=0.05|g=tail_p5|beta|b=0.00|y=-|r=full_doc|w=-` F1 `0.6869565217391305`.
- Paired struct-only `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.10|y=-|r=full_doc|w=-` F1 `0.7022222222222222`.
- `[HOLDOUT_MAX_SCAN]` `dir1024_sig_sep|additive|a=0.05|g=tail_p10|beta|b=0.15|y=-|r=full_doc|w=-` F1 `0.7053571428571429`.
S_struct latency (microseconds per score() call on holdout strings): combined p50 `19.125` us, p99 `194.42477999999988` us. full_doc n `400` p50 `42.521` p99 `884.7728299999999`. clause_opt2c n `1968` p50 `17.4795` p99 `37.734469999999966`.
Per-feature firing on the focus subtypes, plus in-domain rows whose full_doc `n_below_1` is not zero:
- `code_snippet` `IN_DOMAIN_VALID` n `6` full_doc mean `0.935817090297094` n_below_1 `6` features `char_shannon_entropy` `3`, `letter_ratio` `5`, `punct_ratio` `2`; min_full_clause mean `0.10852127782385196` n_below_1 `6` features `char_shannon_entropy` `6`, `digit_ratio` `4`, `letter_ratio` `6`, `punct_ratio` `6`, `rare_nonletter_char_rate` `1`.
- `dilution_80_20` `HYBRID_BOUNDARY` n `10` full_doc mean `1.0` n_below_1 `0` features `none`; min_full_clause mean `0.9280794716528421` n_below_1 `5` features `char_shannon_entropy` `1`, `digit_ratio` `2`, `foreign_connector_ratio` `1`, `rare_nonletter_char_rate` `2`, `target_connector_ratio` `1`.
- `extreme_short_punct` `ADVERSARIAL_FUZZING` n `10` full_doc mean `0.02447790438092962` n_below_1 `10` features `char_shannon_entropy` `10`, `digit_ratio` `1`, `letter_ratio` `10`, `max_repeated_punct_run` `2`, `punct_ratio` `10`, `rare_nonletter_char_rate` `2`; min_full_clause mean `0.02447790438092962` n_below_1 `10` features `char_shannon_entropy` `10`, `digit_ratio` `1`, `letter_ratio` `10`, `max_repeated_punct_run` `2`, `punct_ratio` `10`, `rare_nonletter_char_rate` `4`.
- `homoglyph_zwsp_fullwidth` `ADVERSARIAL_FUZZING` n `12` full_doc mean `0.021689799610091643` n_below_1 `12` features `char_shannon_entropy` `1`, `foreign_connector_ratio` `4`, `max_repeated_punct_run` `4`, `non_latin_or_control_unicode_ratio` `12`, `punct_ratio` `4`, `rare_nonletter_char_rate` `6`, `symbol_ratio` `12`; min_full_clause mean `0.021689799610091643` n_below_1 `12` features `char_shannon_entropy` `1`, `foreign_connector_ratio` `4`, `max_repeated_punct_run` `4`, `non_latin_or_control_unicode_ratio` `12`, `punct_ratio` `4`, `rare_nonletter_char_rate` `6`, `symbol_ratio` `12`.
- `long_architecture_guide` `IN_DOMAIN_VALID` n `10` full_doc mean `0.9884339293608242` n_below_1 `1` features `rare_nonletter_char_rate` `1`; min_full_clause mean `0.933245058270568` n_below_1 `6` features `char_shannon_entropy` `2`, `digit_ratio` `2`, `rare_nonletter_char_rate` `3`, `symbol_ratio` `1`.
- `long_debugging_walkthrough` `IN_DOMAIN_VALID` n `10` full_doc mean `0.9755933094990719` n_below_1 `4` features `char_shannon_entropy` `3`, `rare_nonletter_char_rate` `1`; min_full_clause mean `0.5965870562114504` n_below_1 `9` features `char_shannon_entropy` `6`, `digit_ratio` `4`, `foreign_connector_ratio` `3`, `letter_ratio` `3`, `punct_ratio` `3`, `rare_nonletter_char_rate` `2`.
- `near_ood_neighbor` `HYBRID_BOUNDARY` n `12` full_doc mean `0.8412424808778044` n_below_1 `5` features `char_shannon_entropy` `1`, `rare_nonletter_char_rate` `4`; min_full_clause mean `0.8117779686522985` n_below_1 `7` features `char_shannon_entropy` `2`, `digit_ratio` `1`, `rare_nonletter_char_rate` `5`.
- `packaging_env` `IN_DOMAIN_VALID` n `6` full_doc mean `0.9994488296631068` n_below_1 `1` features `punct_ratio` `1`; min_full_clause mean `0.9791240842042014` n_below_1 `2` features `punct_ratio` `1`, `rare_nonletter_char_rate` `1`.
- `pytest_testing` `IN_DOMAIN_VALID` n `8` full_doc mean `0.9997378614300055` n_below_1 `1` features `punct_ratio` `1`; min_full_clause mean `0.9692507432416474` n_below_1 `3` features `punct_ratio` `1`, `rare_nonletter_char_rate` `2`.
- `short_idiom_query` `IN_DOMAIN_VALID` n `20` full_doc mean `0.9119852571312421` n_below_1 `16` features `char_shannon_entropy` `5`, `digit_ratio` `1`, `letter_ratio` `5`, `max_repeated_punct_run` `14`, `punct_ratio` `14`; min_full_clause mean `0.9119852571312421` n_below_1 `16` features `char_shannon_entropy` `6`, `digit_ratio` `1`, `letter_ratio` `5`, `max_repeated_punct_run` `14`, `punct_ratio` `14`.
- `traceback_debugging` `IN_DOMAIN_VALID` n `8` full_doc mean `0.9949947951096993` n_below_1 `3` features `char_shannon_entropy` `1`, `punct_ratio` `2`; min_full_clause mean `0.96809982555115` n_below_1 `5` features `char_shannon_entropy` `2`, `punct_ratio` `2`, `rare_nonletter_char_rate` `1`, `target_connector_ratio` `1`.
- `typing_protocol` `IN_DOMAIN_VALID` n `8` full_doc mean `0.9996221914320963` n_below_1 `1` features `punct_ratio` `1`; min_full_clause mean `0.9996221914320963` n_below_1 `1` features `punct_ratio` `1`.
- `panaderia_fermentacion` is absent from `struct_firing` on this cell.
- `diagnostico_pasteleria_panaderia` is absent from `struct_firing` on this cell.
- `smuggle_recipe_footnote` is absent from `struct_firing` on this cell.
### python / clauses / 1B_base_tech_noise
Grid rows 9360. Rows whose CAL_ONLY p10 F1 is below the frozen TASK-013 value: 1050. Both counts are computed from the stored grid.
- Headline `dir1024_clip_polboost|multiplicative|a=0.05|g=tail_p5|beta|b=0.30|y=-|r=full_doc|w=0.35` F1 `0.8118811881188119`.
- Paired alpha=0 beta=0 `dir1024_clip_polboost|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` F1 `0.7413793103448276` is above the headline when the headline is compared with this row.
- Paired guard-only `dir1024_clip_polboost|multiplicative|a=0.10|g=f2_l2|beta|b=0.00|y=-|r=full_doc|w=0.35` F1 `0.7555555555555555`.
- Paired struct-only `dir1024_clip_polboost|identity|a=0.00|g=-|beta|b=0.30|y=-|r=full_doc|w=0.35` F1 `0.8155339805825242`.
- `[HOLDOUT_MAX_SCAN]` `dir1024_clip_polboost|additive|a=0.05|g=tail_p5|gamma|b=0.00|y=0.25|r=full_doc|w=0.35` F1 `0.8177339901477833`.
S_struct latency (microseconds per score() call on holdout strings): combined p50 `19.125` us, p99 `194.42477999999988` us. full_doc n `400` p50 `42.521` p99 `884.7728299999999`. clause_opt2c n `1968` p50 `17.4795` p99 `37.734469999999966`.
Per-feature firing on the focus subtypes, plus in-domain rows whose full_doc `n_below_1` is not zero:
- `code_snippet` `IN_DOMAIN_VALID` n `6` full_doc mean `0.935817090297094` n_below_1 `6` features `char_shannon_entropy` `3`, `letter_ratio` `5`, `punct_ratio` `2`; min_full_clause mean `0.10852127782385196` n_below_1 `6` features `char_shannon_entropy` `6`, `digit_ratio` `4`, `letter_ratio` `6`, `punct_ratio` `6`, `rare_nonletter_char_rate` `1`.
- `dilution_80_20` `HYBRID_BOUNDARY` n `10` full_doc mean `1.0` n_below_1 `0` features `none`; min_full_clause mean `0.9280794716528421` n_below_1 `5` features `char_shannon_entropy` `1`, `digit_ratio` `2`, `foreign_connector_ratio` `1`, `rare_nonletter_char_rate` `2`, `target_connector_ratio` `1`.
- `extreme_short_punct` `ADVERSARIAL_FUZZING` n `10` full_doc mean `0.02447790438092962` n_below_1 `10` features `char_shannon_entropy` `10`, `digit_ratio` `1`, `letter_ratio` `10`, `max_repeated_punct_run` `2`, `punct_ratio` `10`, `rare_nonletter_char_rate` `2`; min_full_clause mean `0.02447790438092962` n_below_1 `10` features `char_shannon_entropy` `10`, `digit_ratio` `1`, `letter_ratio` `10`, `max_repeated_punct_run` `2`, `punct_ratio` `10`, `rare_nonletter_char_rate` `4`.
- `homoglyph_zwsp_fullwidth` `ADVERSARIAL_FUZZING` n `12` full_doc mean `0.021689799610091643` n_below_1 `12` features `char_shannon_entropy` `1`, `foreign_connector_ratio` `4`, `max_repeated_punct_run` `4`, `non_latin_or_control_unicode_ratio` `12`, `punct_ratio` `4`, `rare_nonletter_char_rate` `6`, `symbol_ratio` `12`; min_full_clause mean `0.021689799610091643` n_below_1 `12` features `char_shannon_entropy` `1`, `foreign_connector_ratio` `4`, `max_repeated_punct_run` `4`, `non_latin_or_control_unicode_ratio` `12`, `punct_ratio` `4`, `rare_nonletter_char_rate` `6`, `symbol_ratio` `12`.
- `long_architecture_guide` `IN_DOMAIN_VALID` n `10` full_doc mean `0.9884339293608242` n_below_1 `1` features `rare_nonletter_char_rate` `1`; min_full_clause mean `0.933245058270568` n_below_1 `6` features `char_shannon_entropy` `2`, `digit_ratio` `2`, `rare_nonletter_char_rate` `3`, `symbol_ratio` `1`.
- `long_debugging_walkthrough` `IN_DOMAIN_VALID` n `10` full_doc mean `0.9755933094990719` n_below_1 `4` features `char_shannon_entropy` `3`, `rare_nonletter_char_rate` `1`; min_full_clause mean `0.5965870562114504` n_below_1 `9` features `char_shannon_entropy` `6`, `digit_ratio` `4`, `foreign_connector_ratio` `3`, `letter_ratio` `3`, `punct_ratio` `3`, `rare_nonletter_char_rate` `2`.
- `near_ood_neighbor` `HYBRID_BOUNDARY` n `12` full_doc mean `0.8412424808778044` n_below_1 `5` features `char_shannon_entropy` `1`, `rare_nonletter_char_rate` `4`; min_full_clause mean `0.8117779686522985` n_below_1 `7` features `char_shannon_entropy` `2`, `digit_ratio` `1`, `rare_nonletter_char_rate` `5`.
- `packaging_env` `IN_DOMAIN_VALID` n `6` full_doc mean `0.9994488296631068` n_below_1 `1` features `punct_ratio` `1`; min_full_clause mean `0.9791240842042014` n_below_1 `2` features `punct_ratio` `1`, `rare_nonletter_char_rate` `1`.
- `pytest_testing` `IN_DOMAIN_VALID` n `8` full_doc mean `0.9997378614300055` n_below_1 `1` features `punct_ratio` `1`; min_full_clause mean `0.9692507432416474` n_below_1 `3` features `punct_ratio` `1`, `rare_nonletter_char_rate` `2`.
- `short_idiom_query` `IN_DOMAIN_VALID` n `20` full_doc mean `0.9119852571312421` n_below_1 `16` features `char_shannon_entropy` `5`, `digit_ratio` `1`, `letter_ratio` `5`, `max_repeated_punct_run` `14`, `punct_ratio` `14`; min_full_clause mean `0.9119852571312421` n_below_1 `16` features `char_shannon_entropy` `6`, `digit_ratio` `1`, `letter_ratio` `5`, `max_repeated_punct_run` `14`, `punct_ratio` `14`.
- `traceback_debugging` `IN_DOMAIN_VALID` n `8` full_doc mean `0.9949947951096993` n_below_1 `3` features `char_shannon_entropy` `1`, `punct_ratio` `2`; min_full_clause mean `0.96809982555115` n_below_1 `5` features `char_shannon_entropy` `2`, `punct_ratio` `2`, `rare_nonletter_char_rate` `1`, `target_connector_ratio` `1`.
- `typing_protocol` `IN_DOMAIN_VALID` n `8` full_doc mean `0.9996221914320963` n_below_1 `1` features `punct_ratio` `1`; min_full_clause mean `0.9996221914320963` n_below_1 `1` features `punct_ratio` `1`.
- `panaderia_fermentacion` is absent from `struct_firing` on this cell.
- `diagnostico_pasteleria_panaderia` is absent from `struct_firing` on this cell.
- `smuggle_recipe_footnote` is absent from `struct_firing` on this cell.
### python / full_only / 1B_full
Grid rows 1170. Rows whose CAL_ONLY p10 F1 is below the frozen TASK-013 value: 55. Both counts are computed from the stored grid.
- Headline `dir1024_sig_sep|additive|a=0.05|g=f2_l2|beta|b=0.20|y=-|r=full_doc|w=-` F1 `0.6956521739130435`.
- Paired alpha=0 beta=0 `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` F1 `0.675` is above the headline when the headline is compared with this row.
- Paired guard-only `dir1024_sig_sep|multiplicative|a=0.05|g=tail_p5|beta|b=0.00|y=-|r=full_doc|w=-` F1 `0.6835443037974683`.
- Paired struct-only `dir1024_sig_sep|identity|a=0.00|g=-|gamma|b=0.00|y=0.10|r=full_doc|w=-` F1 `0.7105263157894737`.
- `[HOLDOUT_MAX_SCAN]` `dir1024_sig_sep|additive|a=0.05|g=tail_p5|gamma|b=0.00|y=0.10|r=full_doc|w=-` F1 `0.7142857142857143`.
S_struct latency (microseconds per score() call on holdout strings): combined p50 `19.125` us, p99 `194.42477999999988` us. full_doc n `400` p50 `42.521` p99 `884.7728299999999`. clause_opt2c n `1968` p50 `17.4795` p99 `37.734469999999966`.
Per-feature firing on the focus subtypes, plus in-domain rows whose full_doc `n_below_1` is not zero:
- `code_snippet` `IN_DOMAIN_VALID` n `6` full_doc mean `0.935817090297094` n_below_1 `6` features `char_shannon_entropy` `3`, `letter_ratio` `5`, `punct_ratio` `2`; min_full_clause mean `0.10852127782385196` n_below_1 `6` features `char_shannon_entropy` `6`, `digit_ratio` `4`, `letter_ratio` `6`, `punct_ratio` `6`, `rare_nonletter_char_rate` `1`.
- `dilution_80_20` `HYBRID_BOUNDARY` n `10` full_doc mean `1.0` n_below_1 `0` features `none`; min_full_clause mean `0.9280794716528421` n_below_1 `5` features `char_shannon_entropy` `1`, `digit_ratio` `2`, `foreign_connector_ratio` `1`, `rare_nonletter_char_rate` `2`, `target_connector_ratio` `1`.
- `extreme_short_punct` `ADVERSARIAL_FUZZING` n `10` full_doc mean `0.02447790438092962` n_below_1 `10` features `char_shannon_entropy` `10`, `digit_ratio` `1`, `letter_ratio` `10`, `max_repeated_punct_run` `2`, `punct_ratio` `10`, `rare_nonletter_char_rate` `2`; min_full_clause mean `0.02447790438092962` n_below_1 `10` features `char_shannon_entropy` `10`, `digit_ratio` `1`, `letter_ratio` `10`, `max_repeated_punct_run` `2`, `punct_ratio` `10`, `rare_nonletter_char_rate` `4`.
- `homoglyph_zwsp_fullwidth` `ADVERSARIAL_FUZZING` n `12` full_doc mean `0.021689799610091643` n_below_1 `12` features `char_shannon_entropy` `1`, `foreign_connector_ratio` `4`, `max_repeated_punct_run` `4`, `non_latin_or_control_unicode_ratio` `12`, `punct_ratio` `4`, `rare_nonletter_char_rate` `6`, `symbol_ratio` `12`; min_full_clause mean `0.021689799610091643` n_below_1 `12` features `char_shannon_entropy` `1`, `foreign_connector_ratio` `4`, `max_repeated_punct_run` `4`, `non_latin_or_control_unicode_ratio` `12`, `punct_ratio` `4`, `rare_nonletter_char_rate` `6`, `symbol_ratio` `12`.
- `long_architecture_guide` `IN_DOMAIN_VALID` n `10` full_doc mean `0.9884339293608242` n_below_1 `1` features `rare_nonletter_char_rate` `1`; min_full_clause mean `0.933245058270568` n_below_1 `6` features `char_shannon_entropy` `2`, `digit_ratio` `2`, `rare_nonletter_char_rate` `3`, `symbol_ratio` `1`.
- `long_debugging_walkthrough` `IN_DOMAIN_VALID` n `10` full_doc mean `0.9755933094990719` n_below_1 `4` features `char_shannon_entropy` `3`, `rare_nonletter_char_rate` `1`; min_full_clause mean `0.5965870562114504` n_below_1 `9` features `char_shannon_entropy` `6`, `digit_ratio` `4`, `foreign_connector_ratio` `3`, `letter_ratio` `3`, `punct_ratio` `3`, `rare_nonletter_char_rate` `2`.
- `near_ood_neighbor` `HYBRID_BOUNDARY` n `12` full_doc mean `0.8412424808778044` n_below_1 `5` features `char_shannon_entropy` `1`, `rare_nonletter_char_rate` `4`; min_full_clause mean `0.8117779686522985` n_below_1 `7` features `char_shannon_entropy` `2`, `digit_ratio` `1`, `rare_nonletter_char_rate` `5`.
- `packaging_env` `IN_DOMAIN_VALID` n `6` full_doc mean `0.9994488296631068` n_below_1 `1` features `punct_ratio` `1`; min_full_clause mean `0.9791240842042014` n_below_1 `2` features `punct_ratio` `1`, `rare_nonletter_char_rate` `1`.
- `pytest_testing` `IN_DOMAIN_VALID` n `8` full_doc mean `0.9997378614300055` n_below_1 `1` features `punct_ratio` `1`; min_full_clause mean `0.9692507432416474` n_below_1 `3` features `punct_ratio` `1`, `rare_nonletter_char_rate` `2`.
- `short_idiom_query` `IN_DOMAIN_VALID` n `20` full_doc mean `0.9119852571312421` n_below_1 `16` features `char_shannon_entropy` `5`, `digit_ratio` `1`, `letter_ratio` `5`, `max_repeated_punct_run` `14`, `punct_ratio` `14`; min_full_clause mean `0.9119852571312421` n_below_1 `16` features `char_shannon_entropy` `6`, `digit_ratio` `1`, `letter_ratio` `5`, `max_repeated_punct_run` `14`, `punct_ratio` `14`.
- `traceback_debugging` `IN_DOMAIN_VALID` n `8` full_doc mean `0.9949947951096993` n_below_1 `3` features `char_shannon_entropy` `1`, `punct_ratio` `2`; min_full_clause mean `0.96809982555115` n_below_1 `5` features `char_shannon_entropy` `2`, `punct_ratio` `2`, `rare_nonletter_char_rate` `1`, `target_connector_ratio` `1`.
- `typing_protocol` `IN_DOMAIN_VALID` n `8` full_doc mean `0.9996221914320963` n_below_1 `1` features `punct_ratio` `1`; min_full_clause mean `0.9996221914320963` n_below_1 `1` features `punct_ratio` `1`.
- `panaderia_fermentacion` is absent from `struct_firing` on this cell.
- `diagnostico_pasteleria_panaderia` is absent from `struct_firing` on this cell.
- `smuggle_recipe_footnote` is absent from `struct_firing` on this cell.
### python / clauses / 1B_full
Grid rows 9360. Rows whose CAL_ONLY p10 F1 is below the frozen TASK-013 value: 1545. Both counts are computed from the stored grid.
- Headline `dir1024_sig_sep|multiplicative|a=0.20|g=tail_p5|gamma|b=0.00|y=0.10|r=full_doc|w=0.35` F1 `0.8133971291866029`.
- Paired alpha=0 beta=0 `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` F1 `0.7510548523206751` is above the headline when the headline is compared with this row.
- Paired guard-only `dir1024_sig_sep|multiplicative|a=0.20|g=tail_p5|beta|b=0.00|y=-|r=full_doc|w=0.35` F1 `0.7652173913043478`.
- Paired struct-only `dir1024_sig_sep|identity|a=0.00|g=-|gamma|b=0.00|y=0.10|r=full_doc|w=0.35` F1 `0.8075117370892019`.
- `[HOLDOUT_MAX_SCAN]` `dir1024_sig_sep|multiplicative|a=0.20|g=tail_p5|gamma|b=0.00|y=0.10|r=full_doc|w=0.35` F1 `0.8133971291866029`.
S_struct latency (microseconds per score() call on holdout strings): combined p50 `19.125` us, p99 `194.42477999999988` us. full_doc n `400` p50 `42.521` p99 `884.7728299999999`. clause_opt2c n `1968` p50 `17.4795` p99 `37.734469999999966`.
Per-feature firing on the focus subtypes, plus in-domain rows whose full_doc `n_below_1` is not zero:
- `code_snippet` `IN_DOMAIN_VALID` n `6` full_doc mean `0.935817090297094` n_below_1 `6` features `char_shannon_entropy` `3`, `letter_ratio` `5`, `punct_ratio` `2`; min_full_clause mean `0.10852127782385196` n_below_1 `6` features `char_shannon_entropy` `6`, `digit_ratio` `4`, `letter_ratio` `6`, `punct_ratio` `6`, `rare_nonletter_char_rate` `1`.
- `dilution_80_20` `HYBRID_BOUNDARY` n `10` full_doc mean `1.0` n_below_1 `0` features `none`; min_full_clause mean `0.9280794716528421` n_below_1 `5` features `char_shannon_entropy` `1`, `digit_ratio` `2`, `foreign_connector_ratio` `1`, `rare_nonletter_char_rate` `2`, `target_connector_ratio` `1`.
- `extreme_short_punct` `ADVERSARIAL_FUZZING` n `10` full_doc mean `0.02447790438092962` n_below_1 `10` features `char_shannon_entropy` `10`, `digit_ratio` `1`, `letter_ratio` `10`, `max_repeated_punct_run` `2`, `punct_ratio` `10`, `rare_nonletter_char_rate` `2`; min_full_clause mean `0.02447790438092962` n_below_1 `10` features `char_shannon_entropy` `10`, `digit_ratio` `1`, `letter_ratio` `10`, `max_repeated_punct_run` `2`, `punct_ratio` `10`, `rare_nonletter_char_rate` `4`.
- `homoglyph_zwsp_fullwidth` `ADVERSARIAL_FUZZING` n `12` full_doc mean `0.021689799610091643` n_below_1 `12` features `char_shannon_entropy` `1`, `foreign_connector_ratio` `4`, `max_repeated_punct_run` `4`, `non_latin_or_control_unicode_ratio` `12`, `punct_ratio` `4`, `rare_nonletter_char_rate` `6`, `symbol_ratio` `12`; min_full_clause mean `0.021689799610091643` n_below_1 `12` features `char_shannon_entropy` `1`, `foreign_connector_ratio` `4`, `max_repeated_punct_run` `4`, `non_latin_or_control_unicode_ratio` `12`, `punct_ratio` `4`, `rare_nonletter_char_rate` `6`, `symbol_ratio` `12`.
- `long_architecture_guide` `IN_DOMAIN_VALID` n `10` full_doc mean `0.9884339293608242` n_below_1 `1` features `rare_nonletter_char_rate` `1`; min_full_clause mean `0.933245058270568` n_below_1 `6` features `char_shannon_entropy` `2`, `digit_ratio` `2`, `rare_nonletter_char_rate` `3`, `symbol_ratio` `1`.
- `long_debugging_walkthrough` `IN_DOMAIN_VALID` n `10` full_doc mean `0.9755933094990719` n_below_1 `4` features `char_shannon_entropy` `3`, `rare_nonletter_char_rate` `1`; min_full_clause mean `0.5965870562114504` n_below_1 `9` features `char_shannon_entropy` `6`, `digit_ratio` `4`, `foreign_connector_ratio` `3`, `letter_ratio` `3`, `punct_ratio` `3`, `rare_nonletter_char_rate` `2`.
- `near_ood_neighbor` `HYBRID_BOUNDARY` n `12` full_doc mean `0.8412424808778044` n_below_1 `5` features `char_shannon_entropy` `1`, `rare_nonletter_char_rate` `4`; min_full_clause mean `0.8117779686522985` n_below_1 `7` features `char_shannon_entropy` `2`, `digit_ratio` `1`, `rare_nonletter_char_rate` `5`.
- `packaging_env` `IN_DOMAIN_VALID` n `6` full_doc mean `0.9994488296631068` n_below_1 `1` features `punct_ratio` `1`; min_full_clause mean `0.9791240842042014` n_below_1 `2` features `punct_ratio` `1`, `rare_nonletter_char_rate` `1`.
- `pytest_testing` `IN_DOMAIN_VALID` n `8` full_doc mean `0.9997378614300055` n_below_1 `1` features `punct_ratio` `1`; min_full_clause mean `0.9692507432416474` n_below_1 `3` features `punct_ratio` `1`, `rare_nonletter_char_rate` `2`.
- `short_idiom_query` `IN_DOMAIN_VALID` n `20` full_doc mean `0.9119852571312421` n_below_1 `16` features `char_shannon_entropy` `5`, `digit_ratio` `1`, `letter_ratio` `5`, `max_repeated_punct_run` `14`, `punct_ratio` `14`; min_full_clause mean `0.9119852571312421` n_below_1 `16` features `char_shannon_entropy` `6`, `digit_ratio` `1`, `letter_ratio` `5`, `max_repeated_punct_run` `14`, `punct_ratio` `14`.
- `traceback_debugging` `IN_DOMAIN_VALID` n `8` full_doc mean `0.9949947951096993` n_below_1 `3` features `char_shannon_entropy` `1`, `punct_ratio` `2`; min_full_clause mean `0.96809982555115` n_below_1 `5` features `char_shannon_entropy` `2`, `punct_ratio` `2`, `rare_nonletter_char_rate` `1`, `target_connector_ratio` `1`.
- `typing_protocol` `IN_DOMAIN_VALID` n `8` full_doc mean `0.9996221914320963` n_below_1 `1` features `punct_ratio` `1`; min_full_clause mean `0.9996221914320963` n_below_1 `1` features `punct_ratio` `1`.
- `panaderia_fermentacion` is absent from `struct_firing` on this cell.
- `diagnostico_pasteleria_panaderia` is absent from `struct_firing` on this cell.
- `smuggle_recipe_footnote` is absent from `struct_firing` on this cell.
### python / full_only / 1B_full_v3
Grid rows 1170. Rows whose CAL_ONLY p10 F1 is below the frozen TASK-013 value: 91. Both counts are computed from the stored grid.
- Headline `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.10|y=-|r=full_doc|w=-` F1 `0.6583333333333333`.
- Paired alpha=0 beta=0 `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` F1 `0.6530612244897959` is above the headline when the headline is compared with this row.
- Paired guard-only `dir1024_sig_sep|multiplicative|a=0.10|g=tail_p10|beta|b=0.00|y=-|r=full_doc|w=-` F1 `0.6694915254237288`.
- Paired struct-only `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.05|y=-|r=full_doc|w=-` F1 `0.6666666666666666`.
- `[HOLDOUT_MAX_SCAN]` `dir1024_sig_sep|additive|a=0.15|g=tail_p10|gamma|b=0.00|y=0.10|r=full_doc|w=-` F1 `0.6869565217391305`.
S_struct latency (microseconds per score() call on holdout strings): combined p50 `19.125` us, p99 `194.42477999999988` us. full_doc n `400` p50 `42.521` p99 `884.7728299999999`. clause_opt2c n `1968` p50 `17.4795` p99 `37.734469999999966`.
Per-feature firing on the focus subtypes, plus in-domain rows whose full_doc `n_below_1` is not zero:
- `code_snippet` `IN_DOMAIN_VALID` n `6` full_doc mean `0.935817090297094` n_below_1 `6` features `char_shannon_entropy` `3`, `letter_ratio` `5`, `punct_ratio` `2`; min_full_clause mean `0.10852127782385196` n_below_1 `6` features `char_shannon_entropy` `6`, `digit_ratio` `4`, `letter_ratio` `6`, `punct_ratio` `6`, `rare_nonletter_char_rate` `1`.
- `dilution_80_20` `HYBRID_BOUNDARY` n `10` full_doc mean `1.0` n_below_1 `0` features `none`; min_full_clause mean `0.9280794716528421` n_below_1 `5` features `char_shannon_entropy` `1`, `digit_ratio` `2`, `foreign_connector_ratio` `1`, `rare_nonletter_char_rate` `2`, `target_connector_ratio` `1`.
- `extreme_short_punct` `ADVERSARIAL_FUZZING` n `10` full_doc mean `0.02447790438092962` n_below_1 `10` features `char_shannon_entropy` `10`, `digit_ratio` `1`, `letter_ratio` `10`, `max_repeated_punct_run` `2`, `punct_ratio` `10`, `rare_nonletter_char_rate` `2`; min_full_clause mean `0.02447790438092962` n_below_1 `10` features `char_shannon_entropy` `10`, `digit_ratio` `1`, `letter_ratio` `10`, `max_repeated_punct_run` `2`, `punct_ratio` `10`, `rare_nonletter_char_rate` `4`.
- `homoglyph_zwsp_fullwidth` `ADVERSARIAL_FUZZING` n `12` full_doc mean `0.021689799610091643` n_below_1 `12` features `char_shannon_entropy` `1`, `foreign_connector_ratio` `4`, `max_repeated_punct_run` `4`, `non_latin_or_control_unicode_ratio` `12`, `punct_ratio` `4`, `rare_nonletter_char_rate` `6`, `symbol_ratio` `12`; min_full_clause mean `0.021689799610091643` n_below_1 `12` features `char_shannon_entropy` `1`, `foreign_connector_ratio` `4`, `max_repeated_punct_run` `4`, `non_latin_or_control_unicode_ratio` `12`, `punct_ratio` `4`, `rare_nonletter_char_rate` `6`, `symbol_ratio` `12`.
- `long_architecture_guide` `IN_DOMAIN_VALID` n `10` full_doc mean `0.9884339293608242` n_below_1 `1` features `rare_nonletter_char_rate` `1`; min_full_clause mean `0.933245058270568` n_below_1 `6` features `char_shannon_entropy` `2`, `digit_ratio` `2`, `rare_nonletter_char_rate` `3`, `symbol_ratio` `1`.
- `long_debugging_walkthrough` `IN_DOMAIN_VALID` n `10` full_doc mean `0.9755933094990719` n_below_1 `4` features `char_shannon_entropy` `3`, `rare_nonletter_char_rate` `1`; min_full_clause mean `0.5965870562114504` n_below_1 `9` features `char_shannon_entropy` `6`, `digit_ratio` `4`, `foreign_connector_ratio` `3`, `letter_ratio` `3`, `punct_ratio` `3`, `rare_nonletter_char_rate` `2`.
- `near_ood_neighbor` `HYBRID_BOUNDARY` n `12` full_doc mean `0.8412424808778044` n_below_1 `5` features `char_shannon_entropy` `1`, `rare_nonletter_char_rate` `4`; min_full_clause mean `0.8117779686522985` n_below_1 `7` features `char_shannon_entropy` `2`, `digit_ratio` `1`, `rare_nonletter_char_rate` `5`.
- `packaging_env` `IN_DOMAIN_VALID` n `6` full_doc mean `0.9994488296631068` n_below_1 `1` features `punct_ratio` `1`; min_full_clause mean `0.9791240842042014` n_below_1 `2` features `punct_ratio` `1`, `rare_nonletter_char_rate` `1`.
- `pytest_testing` `IN_DOMAIN_VALID` n `8` full_doc mean `0.9997378614300055` n_below_1 `1` features `punct_ratio` `1`; min_full_clause mean `0.9692507432416474` n_below_1 `3` features `punct_ratio` `1`, `rare_nonletter_char_rate` `2`.
- `short_idiom_query` `IN_DOMAIN_VALID` n `20` full_doc mean `0.9119852571312421` n_below_1 `16` features `char_shannon_entropy` `5`, `digit_ratio` `1`, `letter_ratio` `5`, `max_repeated_punct_run` `14`, `punct_ratio` `14`; min_full_clause mean `0.9119852571312421` n_below_1 `16` features `char_shannon_entropy` `6`, `digit_ratio` `1`, `letter_ratio` `5`, `max_repeated_punct_run` `14`, `punct_ratio` `14`.
- `traceback_debugging` `IN_DOMAIN_VALID` n `8` full_doc mean `0.9949947951096993` n_below_1 `3` features `char_shannon_entropy` `1`, `punct_ratio` `2`; min_full_clause mean `0.96809982555115` n_below_1 `5` features `char_shannon_entropy` `2`, `punct_ratio` `2`, `rare_nonletter_char_rate` `1`, `target_connector_ratio` `1`.
- `typing_protocol` `IN_DOMAIN_VALID` n `8` full_doc mean `0.9996221914320963` n_below_1 `1` features `punct_ratio` `1`; min_full_clause mean `0.9996221914320963` n_below_1 `1` features `punct_ratio` `1`.
- `panaderia_fermentacion` is absent from `struct_firing` on this cell.
- `diagnostico_pasteleria_panaderia` is absent from `struct_firing` on this cell.
- `smuggle_recipe_footnote` is absent from `struct_firing` on this cell.
### python / clauses / 1B_full_v3
Grid rows 9360. Rows whose CAL_ONLY p10 F1 is below the frozen TASK-013 value: 1709. Both counts are computed from the stored grid.
- Headline `dir1024_sig_sep2|multiplicative|a=0.10|g=f2_l2|gamma|b=0.00|y=0.10|r=full_doc|w=0.35` F1 `0.7941176470588235`.
- Paired alpha=0 beta=0 `dir1024_sig_sep2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` F1 `0.7699115044247787` is above the headline when the headline is compared with this row.
- Paired guard-only `dir1024_sig_sep2|additive|a=0.15|g=tail_p5|beta|b=0.00|y=-|r=full_doc|w=0.35` F1 `0.776255707762557`.
- Paired struct-only `dir1024_sig_sep2|identity|a=0.00|g=-|beta|b=0.10|y=-|r=full_doc|w=0.35` F1 `0.8095238095238095`.
- `[HOLDOUT_MAX_SCAN]` `dir1024_sig_sep2|multiplicative|a=0.15|g=tail_p5|gamma|b=0.00|y=0.10|r=full_doc|w=0.35` F1 `0.8269230769230769`.
S_struct latency (microseconds per score() call on holdout strings): combined p50 `19.125` us, p99 `194.42477999999988` us. full_doc n `400` p50 `42.521` p99 `884.7728299999999`. clause_opt2c n `1968` p50 `17.4795` p99 `37.734469999999966`.
Per-feature firing on the focus subtypes, plus in-domain rows whose full_doc `n_below_1` is not zero:
- `code_snippet` `IN_DOMAIN_VALID` n `6` full_doc mean `0.935817090297094` n_below_1 `6` features `char_shannon_entropy` `3`, `letter_ratio` `5`, `punct_ratio` `2`; min_full_clause mean `0.10852127782385196` n_below_1 `6` features `char_shannon_entropy` `6`, `digit_ratio` `4`, `letter_ratio` `6`, `punct_ratio` `6`, `rare_nonletter_char_rate` `1`.
- `dilution_80_20` `HYBRID_BOUNDARY` n `10` full_doc mean `1.0` n_below_1 `0` features `none`; min_full_clause mean `0.9280794716528421` n_below_1 `5` features `char_shannon_entropy` `1`, `digit_ratio` `2`, `foreign_connector_ratio` `1`, `rare_nonletter_char_rate` `2`, `target_connector_ratio` `1`.
- `extreme_short_punct` `ADVERSARIAL_FUZZING` n `10` full_doc mean `0.02447790438092962` n_below_1 `10` features `char_shannon_entropy` `10`, `digit_ratio` `1`, `letter_ratio` `10`, `max_repeated_punct_run` `2`, `punct_ratio` `10`, `rare_nonletter_char_rate` `2`; min_full_clause mean `0.02447790438092962` n_below_1 `10` features `char_shannon_entropy` `10`, `digit_ratio` `1`, `letter_ratio` `10`, `max_repeated_punct_run` `2`, `punct_ratio` `10`, `rare_nonletter_char_rate` `4`.
- `homoglyph_zwsp_fullwidth` `ADVERSARIAL_FUZZING` n `12` full_doc mean `0.021689799610091643` n_below_1 `12` features `char_shannon_entropy` `1`, `foreign_connector_ratio` `4`, `max_repeated_punct_run` `4`, `non_latin_or_control_unicode_ratio` `12`, `punct_ratio` `4`, `rare_nonletter_char_rate` `6`, `symbol_ratio` `12`; min_full_clause mean `0.021689799610091643` n_below_1 `12` features `char_shannon_entropy` `1`, `foreign_connector_ratio` `4`, `max_repeated_punct_run` `4`, `non_latin_or_control_unicode_ratio` `12`, `punct_ratio` `4`, `rare_nonletter_char_rate` `6`, `symbol_ratio` `12`.
- `long_architecture_guide` `IN_DOMAIN_VALID` n `10` full_doc mean `0.9884339293608242` n_below_1 `1` features `rare_nonletter_char_rate` `1`; min_full_clause mean `0.933245058270568` n_below_1 `6` features `char_shannon_entropy` `2`, `digit_ratio` `2`, `rare_nonletter_char_rate` `3`, `symbol_ratio` `1`.
- `long_debugging_walkthrough` `IN_DOMAIN_VALID` n `10` full_doc mean `0.9755933094990719` n_below_1 `4` features `char_shannon_entropy` `3`, `rare_nonletter_char_rate` `1`; min_full_clause mean `0.5965870562114504` n_below_1 `9` features `char_shannon_entropy` `6`, `digit_ratio` `4`, `foreign_connector_ratio` `3`, `letter_ratio` `3`, `punct_ratio` `3`, `rare_nonletter_char_rate` `2`.
- `near_ood_neighbor` `HYBRID_BOUNDARY` n `12` full_doc mean `0.8412424808778044` n_below_1 `5` features `char_shannon_entropy` `1`, `rare_nonletter_char_rate` `4`; min_full_clause mean `0.8117779686522985` n_below_1 `7` features `char_shannon_entropy` `2`, `digit_ratio` `1`, `rare_nonletter_char_rate` `5`.
- `packaging_env` `IN_DOMAIN_VALID` n `6` full_doc mean `0.9994488296631068` n_below_1 `1` features `punct_ratio` `1`; min_full_clause mean `0.9791240842042014` n_below_1 `2` features `punct_ratio` `1`, `rare_nonletter_char_rate` `1`.
- `pytest_testing` `IN_DOMAIN_VALID` n `8` full_doc mean `0.9997378614300055` n_below_1 `1` features `punct_ratio` `1`; min_full_clause mean `0.9692507432416474` n_below_1 `3` features `punct_ratio` `1`, `rare_nonletter_char_rate` `2`.
- `short_idiom_query` `IN_DOMAIN_VALID` n `20` full_doc mean `0.9119852571312421` n_below_1 `16` features `char_shannon_entropy` `5`, `digit_ratio` `1`, `letter_ratio` `5`, `max_repeated_punct_run` `14`, `punct_ratio` `14`; min_full_clause mean `0.9119852571312421` n_below_1 `16` features `char_shannon_entropy` `6`, `digit_ratio` `1`, `letter_ratio` `5`, `max_repeated_punct_run` `14`, `punct_ratio` `14`.
- `traceback_debugging` `IN_DOMAIN_VALID` n `8` full_doc mean `0.9949947951096993` n_below_1 `3` features `char_shannon_entropy` `1`, `punct_ratio` `2`; min_full_clause mean `0.96809982555115` n_below_1 `5` features `char_shannon_entropy` `2`, `punct_ratio` `2`, `rare_nonletter_char_rate` `1`, `target_connector_ratio` `1`.
- `typing_protocol` `IN_DOMAIN_VALID` n `8` full_doc mean `0.9996221914320963` n_below_1 `1` features `punct_ratio` `1`; min_full_clause mean `0.9996221914320963` n_below_1 `1` features `punct_ratio` `1`.
- `panaderia_fermentacion` is absent from `struct_firing` on this cell.
- `diagnostico_pasteleria_panaderia` is absent from `struct_firing` on this cell.
- `smuggle_recipe_footnote` is absent from `struct_firing` on this cell.
### receta / full_only / 1B_base_tech
Grid rows 1170. Rows whose CAL_ONLY p10 F1 is below the frozen TASK-013 value: 1169. Both counts are computed from the stored grid.
- Headline `polarity_v2_subset|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` F1 `0.7403846153846154`.
- Paired alpha=0 beta=0 `polarity_v2_subset|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` F1 `0.7403846153846154` is tied with the headline when the headline is compared with this row.
- Paired guard-only row is absent.
- Paired struct-only `polarity_v2_subset|identity|a=0.00|g=-|beta|b=0.05|y=-|r=full_doc|w=-` F1 `0.7035175879396985`.
- `[HOLDOUT_MAX_SCAN]` `polarity_v2_subset|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` F1 `0.7403846153846154`.
S_struct latency (microseconds per score() call on holdout strings): combined p50 `20.625` us, p99 `200.49970000000062` us. full_doc n `400` p50 `47.2085` p99 `946.2988399999999`. clause_opt2c n `1946` p50 `19.375` p99 `54.93749999999994`.
Per-feature firing on the focus subtypes, plus in-domain rows whose full_doc `n_below_1` is not zero:
- `cocina_regional` `IN_DOMAIN_VALID` n `8` full_doc mean `0.5833892136217328` n_below_1 `6` features `foreign_connector_ratio` `1`, `punct_ratio` `2`, `rare_nonletter_char_rate` `4`, `target_connector_ratio` `1`; min_full_clause mean `0.4804626378701009` n_below_1 `6` features `char_shannon_entropy` `2`, `foreign_connector_ratio` `1`, `punct_ratio` `2`, `rare_nonletter_char_rate` `4`, `symbol_ratio` `1`, `target_connector_ratio` `2`.
- `consulta_corta` `IN_DOMAIN_VALID` n `20` full_doc mean `0.028940498658351486` n_below_1 `20` features `char_shannon_entropy` `8`, `letter_ratio` `7`, `max_repeated_punct_run` `15`, `punct_ratio` `16`, `rare_nonletter_char_rate` `5`, `symbol_ratio` `7`, `target_connector_ratio` `6`; min_full_clause mean `0.024162241650889142` n_below_1 `20` features `char_shannon_entropy` `9`, `letter_ratio` `7`, `max_repeated_punct_run` `15`, `punct_ratio` `16`, `rare_nonletter_char_rate` `5`, `symbol_ratio` `7`, `target_connector_ratio` `6`.
- `diagnostico_pasteleria_panaderia` `IN_DOMAIN_VALID` n `8` full_doc mean `1.0` n_below_1 `0` features `none`; min_full_clause mean `0.9367547842571509` n_below_1 `6` features `char_shannon_entropy` `3`, `foreign_connector_ratio` `1`, `letter_ratio` `3`, `symbol_ratio` `1`, `target_connector_ratio` `3`.
- `dilution_80_20` `HYBRID_BOUNDARY` n `10` full_doc mean `0.7783372923780758` n_below_1 `8` features `char_shannon_entropy` `2`, `punct_ratio` `1`, `rare_nonletter_char_rate` `6`, `symbol_ratio` `4`, `target_connector_ratio` `1`; min_full_clause mean `0.30187841129659954` n_below_1 `10` features `char_shannon_entropy` `5`, `foreign_connector_ratio` `2`, `letter_ratio` `2`, `punct_ratio` `1`, `rare_nonletter_char_rate` `7`, `symbol_ratio` `5`, `target_connector_ratio` `2`.
- `extreme_short_punct` `ADVERSARIAL_FUZZING` n `10` full_doc mean `5.614891346849248e-06` n_below_1 `10` features `char_shannon_entropy` `10`, `digit_ratio` `1`, `letter_ratio` `10`, `max_repeated_punct_run` `6`, `punct_ratio` `10`, `rare_nonletter_bigram_rate` `9`, `rare_nonletter_char_rate` `7`, `symbol_ratio` `3`; min_full_clause mean `5.59328641587905e-06` n_below_1 `10` features `char_shannon_entropy` `10`, `digit_ratio` `1`, `letter_ratio` `10`, `max_repeated_punct_run` `6`, `punct_ratio` `10`, `rare_nonletter_bigram_rate` `9`, `rare_nonletter_char_rate` `9`, `symbol_ratio` `3`.
- `homoglyph_zwsp_fullwidth` `ADVERSARIAL_FUZZING` n `12` full_doc mean `0.023747952634073626` n_below_1 `12` features `char_shannon_entropy` `1`, `foreign_connector_ratio` `3`, `letter_ratio` `5`, `max_repeated_punct_run` `4`, `non_latin_or_control_unicode_ratio` `12`, `punct_ratio` `5`, `rare_nonletter_bigram_rate` `1`, `rare_nonletter_char_rate` `6`, `symbol_ratio` `12`, `target_connector_ratio` `9`; min_full_clause mean `0.023747952634073626` n_below_1 `12` features `char_shannon_entropy` `1`, `foreign_connector_ratio` `3`, `letter_ratio` `5`, `max_repeated_punct_run` `4`, `non_latin_or_control_unicode_ratio` `12`, `punct_ratio` `5`, `rare_nonletter_bigram_rate` `1`, `rare_nonletter_char_rate` `6`, `symbol_ratio` `12`, `target_connector_ratio` `9`.
- `near_ood_neighbor` `HYBRID_BOUNDARY` n `12` full_doc mean `0.8730096561047865` n_below_1 `7` features `letter_ratio` `2`, `punct_ratio` `2`, `rare_nonletter_char_rate` `2`, `symbol_ratio` `2`; min_full_clause mean `0.8097494496691354` n_below_1 `9` features `char_shannon_entropy` `5`, `foreign_connector_ratio` `1`, `letter_ratio` `3`, `punct_ratio` `2`, `rare_nonletter_char_rate` `2`, `symbol_ratio` `2`.
- `panaderia_fermentacion` `IN_DOMAIN_VALID` n `10` full_doc mean `0.5553236913122764` n_below_1 `9` features `foreign_connector_ratio` `1`, `punct_ratio` `5`, `rare_nonletter_char_rate` `5`; min_full_clause mean `0.5039149200505284` n_below_1 `10` features `char_shannon_entropy` `3`, `foreign_connector_ratio` `1`, `letter_ratio` `3`, `punct_ratio` `6`, `rare_nonletter_char_rate` `5`, `symbol_ratio` `1`.
- `receta_completa` `IN_DOMAIN_VALID` n `10` full_doc mean `0.9951559522284821` n_below_1 `1` features `symbol_ratio` `1`; min_full_clause mean `0.9332966539612337` n_below_1 `5` features `char_shannon_entropy` `4`, `foreign_connector_ratio` `2`, `letter_ratio` `1`, `symbol_ratio` `2`, `target_connector_ratio` `1`.
- `salsas_emulsiones` `IN_DOMAIN_VALID` n `8` full_doc mean `0.5612106971026649` n_below_1 `7` features `letter_ratio` `1`, `punct_ratio` `2`, `rare_nonletter_char_rate` `4`, `symbol_ratio` `1`, `target_connector_ratio` `1`; min_full_clause mean `0.4984571763777811` n_below_1 `7` features `char_shannon_entropy` `3`, `letter_ratio` `2`, `punct_ratio` `2`, `rare_nonletter_char_rate` `4`, `symbol_ratio` `1`, `target_connector_ratio` `1`.
- `smuggle_recipe_footnote` `HYBRID_BOUNDARY` n `10` full_doc mean `0.10655450030333107` n_below_1 `9` features `char_shannon_entropy` `5`, `digit_ratio` `1`, `punct_ratio` `1`, `rare_nonletter_bigram_rate` `9`, `rare_nonletter_char_rate` `9`, `symbol_ratio` `2`, `target_connector_ratio` `1`; min_full_clause mean `0.10391163800745092` n_below_1 `9` features `char_shannon_entropy` `8`, `digit_ratio` `1`, `letter_ratio` `3`, `punct_ratio` `9`, `rare_nonletter_bigram_rate` `9`, `rare_nonletter_char_rate` `9`, `symbol_ratio` `3`, `target_connector_ratio` `1`.
- `sustitucion_ingredientes` `IN_DOMAIN_VALID` n `8` full_doc mean `0.19816987506111944` n_below_1 `8` features `punct_ratio` `1`, `rare_nonletter_char_rate` `8`, `symbol_ratio` `1`; min_full_clause mean `0.014264233908999256` n_below_1 `8` features `char_shannon_entropy` `1`, `punct_ratio` `1`, `rare_nonletter_char_rate` `8`, `symbol_ratio` `1`.
- `tecnica_culinaria` `IN_DOMAIN_VALID` n `10` full_doc mean `0.551495245911283` n_below_1 `8` features `punct_ratio` `5`, `rare_nonletter_char_rate` `5`, `symbol_ratio` `2`; min_full_clause mean `0.4996121921276638` n_below_1 `9` features `char_shannon_entropy` `4`, `punct_ratio` `5`, `rare_nonletter_char_rate` `5`, `symbol_ratio` `3`, `target_connector_ratio` `1`.
- `temperatura_tiempos` `IN_DOMAIN_VALID` n `6` full_doc mean `0.4299355219530636` n_below_1 `4` features `punct_ratio` `1`, `rare_nonletter_char_rate` `4`, `symbol_ratio` `1`; min_full_clause mean `0.339299718405166` n_below_1 `5` features `char_shannon_entropy` `4`, `punct_ratio` `1`, `rare_nonletter_char_rate` `4`, `symbol_ratio` `1`.
- `long_debugging_walkthrough` is absent from `struct_firing` on this cell.
### receta / clauses / 1B_base_tech
Grid rows 9360. Rows whose CAL_ONLY p10 F1 is below the frozen TASK-013 value: 8569. Both counts are computed from the stored grid.
- Headline `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` F1 `0.8783068783068783`.
- Paired alpha=0 beta=0 `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` F1 `0.8783068783068783` is tied with the headline when the headline is compared with this row.
- Paired guard-only `dir1024_sig_sep|additive|a=0.05|g=f2_l2|beta|b=0.00|y=-|r=full_doc|w=0.20` F1 `0.8770053475935828`.
- Paired struct-only `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.05|y=-|r=full_doc|w=0.20` F1 `0.8342857142857143`.
- `[HOLDOUT_MAX_SCAN]` `dir1024_clip_polboost|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` F1 `0.8877551020408163`.
S_struct latency (microseconds per score() call on holdout strings): combined p50 `20.625` us, p99 `200.49970000000062` us. full_doc n `400` p50 `47.2085` p99 `946.2988399999999`. clause_opt2c n `1946` p50 `19.375` p99 `54.93749999999994`.
Per-feature firing on the focus subtypes, plus in-domain rows whose full_doc `n_below_1` is not zero:
- `cocina_regional` `IN_DOMAIN_VALID` n `8` full_doc mean `0.5833892136217328` n_below_1 `6` features `foreign_connector_ratio` `1`, `punct_ratio` `2`, `rare_nonletter_char_rate` `4`, `target_connector_ratio` `1`; min_full_clause mean `0.4804626378701009` n_below_1 `6` features `char_shannon_entropy` `2`, `foreign_connector_ratio` `1`, `punct_ratio` `2`, `rare_nonletter_char_rate` `4`, `symbol_ratio` `1`, `target_connector_ratio` `2`.
- `consulta_corta` `IN_DOMAIN_VALID` n `20` full_doc mean `0.028940498658351486` n_below_1 `20` features `char_shannon_entropy` `8`, `letter_ratio` `7`, `max_repeated_punct_run` `15`, `punct_ratio` `16`, `rare_nonletter_char_rate` `5`, `symbol_ratio` `7`, `target_connector_ratio` `6`; min_full_clause mean `0.024162241650889142` n_below_1 `20` features `char_shannon_entropy` `9`, `letter_ratio` `7`, `max_repeated_punct_run` `15`, `punct_ratio` `16`, `rare_nonletter_char_rate` `5`, `symbol_ratio` `7`, `target_connector_ratio` `6`.
- `diagnostico_pasteleria_panaderia` `IN_DOMAIN_VALID` n `8` full_doc mean `1.0` n_below_1 `0` features `none`; min_full_clause mean `0.9367547842571509` n_below_1 `6` features `char_shannon_entropy` `3`, `foreign_connector_ratio` `1`, `letter_ratio` `3`, `symbol_ratio` `1`, `target_connector_ratio` `3`.
- `dilution_80_20` `HYBRID_BOUNDARY` n `10` full_doc mean `0.7783372923780758` n_below_1 `8` features `char_shannon_entropy` `2`, `punct_ratio` `1`, `rare_nonletter_char_rate` `6`, `symbol_ratio` `4`, `target_connector_ratio` `1`; min_full_clause mean `0.30187841129659954` n_below_1 `10` features `char_shannon_entropy` `5`, `foreign_connector_ratio` `2`, `letter_ratio` `2`, `punct_ratio` `1`, `rare_nonletter_char_rate` `7`, `symbol_ratio` `5`, `target_connector_ratio` `2`.
- `extreme_short_punct` `ADVERSARIAL_FUZZING` n `10` full_doc mean `5.614891346849248e-06` n_below_1 `10` features `char_shannon_entropy` `10`, `digit_ratio` `1`, `letter_ratio` `10`, `max_repeated_punct_run` `6`, `punct_ratio` `10`, `rare_nonletter_bigram_rate` `9`, `rare_nonletter_char_rate` `7`, `symbol_ratio` `3`; min_full_clause mean `5.59328641587905e-06` n_below_1 `10` features `char_shannon_entropy` `10`, `digit_ratio` `1`, `letter_ratio` `10`, `max_repeated_punct_run` `6`, `punct_ratio` `10`, `rare_nonletter_bigram_rate` `9`, `rare_nonletter_char_rate` `9`, `symbol_ratio` `3`.
- `homoglyph_zwsp_fullwidth` `ADVERSARIAL_FUZZING` n `12` full_doc mean `0.023747952634073626` n_below_1 `12` features `char_shannon_entropy` `1`, `foreign_connector_ratio` `3`, `letter_ratio` `5`, `max_repeated_punct_run` `4`, `non_latin_or_control_unicode_ratio` `12`, `punct_ratio` `5`, `rare_nonletter_bigram_rate` `1`, `rare_nonletter_char_rate` `6`, `symbol_ratio` `12`, `target_connector_ratio` `9`; min_full_clause mean `0.023747952634073626` n_below_1 `12` features `char_shannon_entropy` `1`, `foreign_connector_ratio` `3`, `letter_ratio` `5`, `max_repeated_punct_run` `4`, `non_latin_or_control_unicode_ratio` `12`, `punct_ratio` `5`, `rare_nonletter_bigram_rate` `1`, `rare_nonletter_char_rate` `6`, `symbol_ratio` `12`, `target_connector_ratio` `9`.
- `near_ood_neighbor` `HYBRID_BOUNDARY` n `12` full_doc mean `0.8730096561047865` n_below_1 `7` features `letter_ratio` `2`, `punct_ratio` `2`, `rare_nonletter_char_rate` `2`, `symbol_ratio` `2`; min_full_clause mean `0.8097494496691354` n_below_1 `9` features `char_shannon_entropy` `5`, `foreign_connector_ratio` `1`, `letter_ratio` `3`, `punct_ratio` `2`, `rare_nonletter_char_rate` `2`, `symbol_ratio` `2`.
- `panaderia_fermentacion` `IN_DOMAIN_VALID` n `10` full_doc mean `0.5553236913122764` n_below_1 `9` features `foreign_connector_ratio` `1`, `punct_ratio` `5`, `rare_nonletter_char_rate` `5`; min_full_clause mean `0.5039149200505284` n_below_1 `10` features `char_shannon_entropy` `3`, `foreign_connector_ratio` `1`, `letter_ratio` `3`, `punct_ratio` `6`, `rare_nonletter_char_rate` `5`, `symbol_ratio` `1`.
- `receta_completa` `IN_DOMAIN_VALID` n `10` full_doc mean `0.9951559522284821` n_below_1 `1` features `symbol_ratio` `1`; min_full_clause mean `0.9332966539612337` n_below_1 `5` features `char_shannon_entropy` `4`, `foreign_connector_ratio` `2`, `letter_ratio` `1`, `symbol_ratio` `2`, `target_connector_ratio` `1`.
- `salsas_emulsiones` `IN_DOMAIN_VALID` n `8` full_doc mean `0.5612106971026649` n_below_1 `7` features `letter_ratio` `1`, `punct_ratio` `2`, `rare_nonletter_char_rate` `4`, `symbol_ratio` `1`, `target_connector_ratio` `1`; min_full_clause mean `0.4984571763777811` n_below_1 `7` features `char_shannon_entropy` `3`, `letter_ratio` `2`, `punct_ratio` `2`, `rare_nonletter_char_rate` `4`, `symbol_ratio` `1`, `target_connector_ratio` `1`.
- `smuggle_recipe_footnote` `HYBRID_BOUNDARY` n `10` full_doc mean `0.10655450030333107` n_below_1 `9` features `char_shannon_entropy` `5`, `digit_ratio` `1`, `punct_ratio` `1`, `rare_nonletter_bigram_rate` `9`, `rare_nonletter_char_rate` `9`, `symbol_ratio` `2`, `target_connector_ratio` `1`; min_full_clause mean `0.10391163800745092` n_below_1 `9` features `char_shannon_entropy` `8`, `digit_ratio` `1`, `letter_ratio` `3`, `punct_ratio` `9`, `rare_nonletter_bigram_rate` `9`, `rare_nonletter_char_rate` `9`, `symbol_ratio` `3`, `target_connector_ratio` `1`.
- `sustitucion_ingredientes` `IN_DOMAIN_VALID` n `8` full_doc mean `0.19816987506111944` n_below_1 `8` features `punct_ratio` `1`, `rare_nonletter_char_rate` `8`, `symbol_ratio` `1`; min_full_clause mean `0.014264233908999256` n_below_1 `8` features `char_shannon_entropy` `1`, `punct_ratio` `1`, `rare_nonletter_char_rate` `8`, `symbol_ratio` `1`.
- `tecnica_culinaria` `IN_DOMAIN_VALID` n `10` full_doc mean `0.551495245911283` n_below_1 `8` features `punct_ratio` `5`, `rare_nonletter_char_rate` `5`, `symbol_ratio` `2`; min_full_clause mean `0.4996121921276638` n_below_1 `9` features `char_shannon_entropy` `4`, `punct_ratio` `5`, `rare_nonletter_char_rate` `5`, `symbol_ratio` `3`, `target_connector_ratio` `1`.
- `temperatura_tiempos` `IN_DOMAIN_VALID` n `6` full_doc mean `0.4299355219530636` n_below_1 `4` features `punct_ratio` `1`, `rare_nonletter_char_rate` `4`, `symbol_ratio` `1`; min_full_clause mean `0.339299718405166` n_below_1 `5` features `char_shannon_entropy` `4`, `punct_ratio` `1`, `rare_nonletter_char_rate` `4`, `symbol_ratio` `1`.
- `long_debugging_walkthrough` is absent from `struct_firing` on this cell.
### receta / full_only / 1B_base_tech_noise
Grid rows 1170. Rows whose CAL_ONLY p10 F1 is below the frozen TASK-013 value: 1170. Both counts are computed from the stored grid.
- Headline `dir1024_clip_polboost|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` F1 `0.6136363636363636`.
- Paired alpha=0 beta=0 `dir1024_clip_polboost|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` F1 `0.6136363636363636` is tied with the headline when the headline is compared with this row.
- Paired guard-only `dir1024_clip_polboost|additive|a=0.05|g=f2_l2|beta|b=0.00|y=-|r=full_doc|w=-` F1 `0.6011560693641619`.
- Paired struct-only `dir1024_clip_polboost|identity|a=0.00|g=-|beta|b=0.05|y=-|r=full_doc|w=-` F1 `0.5125`.
- `[HOLDOUT_MAX_SCAN]` `polarity_v2_subset|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` F1 `0.7281553398058253`.
S_struct latency (microseconds per score() call on holdout strings): combined p50 `20.625` us, p99 `200.49970000000062` us. full_doc n `400` p50 `47.2085` p99 `946.2988399999999`. clause_opt2c n `1946` p50 `19.375` p99 `54.93749999999994`.
Per-feature firing on the focus subtypes, plus in-domain rows whose full_doc `n_below_1` is not zero:
- `cocina_regional` `IN_DOMAIN_VALID` n `8` full_doc mean `0.5833892136217328` n_below_1 `6` features `foreign_connector_ratio` `1`, `punct_ratio` `2`, `rare_nonletter_char_rate` `4`, `target_connector_ratio` `1`; min_full_clause mean `0.4804626378701009` n_below_1 `6` features `char_shannon_entropy` `2`, `foreign_connector_ratio` `1`, `punct_ratio` `2`, `rare_nonletter_char_rate` `4`, `symbol_ratio` `1`, `target_connector_ratio` `2`.
- `consulta_corta` `IN_DOMAIN_VALID` n `20` full_doc mean `0.028940498658351486` n_below_1 `20` features `char_shannon_entropy` `8`, `letter_ratio` `7`, `max_repeated_punct_run` `15`, `punct_ratio` `16`, `rare_nonletter_char_rate` `5`, `symbol_ratio` `7`, `target_connector_ratio` `6`; min_full_clause mean `0.024162241650889142` n_below_1 `20` features `char_shannon_entropy` `9`, `letter_ratio` `7`, `max_repeated_punct_run` `15`, `punct_ratio` `16`, `rare_nonletter_char_rate` `5`, `symbol_ratio` `7`, `target_connector_ratio` `6`.
- `diagnostico_pasteleria_panaderia` `IN_DOMAIN_VALID` n `8` full_doc mean `1.0` n_below_1 `0` features `none`; min_full_clause mean `0.9367547842571509` n_below_1 `6` features `char_shannon_entropy` `3`, `foreign_connector_ratio` `1`, `letter_ratio` `3`, `symbol_ratio` `1`, `target_connector_ratio` `3`.
- `dilution_80_20` `HYBRID_BOUNDARY` n `10` full_doc mean `0.7783372923780758` n_below_1 `8` features `char_shannon_entropy` `2`, `punct_ratio` `1`, `rare_nonletter_char_rate` `6`, `symbol_ratio` `4`, `target_connector_ratio` `1`; min_full_clause mean `0.30187841129659954` n_below_1 `10` features `char_shannon_entropy` `5`, `foreign_connector_ratio` `2`, `letter_ratio` `2`, `punct_ratio` `1`, `rare_nonletter_char_rate` `7`, `symbol_ratio` `5`, `target_connector_ratio` `2`.
- `extreme_short_punct` `ADVERSARIAL_FUZZING` n `10` full_doc mean `5.614891346849248e-06` n_below_1 `10` features `char_shannon_entropy` `10`, `digit_ratio` `1`, `letter_ratio` `10`, `max_repeated_punct_run` `6`, `punct_ratio` `10`, `rare_nonletter_bigram_rate` `9`, `rare_nonletter_char_rate` `7`, `symbol_ratio` `3`; min_full_clause mean `5.59328641587905e-06` n_below_1 `10` features `char_shannon_entropy` `10`, `digit_ratio` `1`, `letter_ratio` `10`, `max_repeated_punct_run` `6`, `punct_ratio` `10`, `rare_nonletter_bigram_rate` `9`, `rare_nonletter_char_rate` `9`, `symbol_ratio` `3`.
- `homoglyph_zwsp_fullwidth` `ADVERSARIAL_FUZZING` n `12` full_doc mean `0.023747952634073626` n_below_1 `12` features `char_shannon_entropy` `1`, `foreign_connector_ratio` `3`, `letter_ratio` `5`, `max_repeated_punct_run` `4`, `non_latin_or_control_unicode_ratio` `12`, `punct_ratio` `5`, `rare_nonletter_bigram_rate` `1`, `rare_nonletter_char_rate` `6`, `symbol_ratio` `12`, `target_connector_ratio` `9`; min_full_clause mean `0.023747952634073626` n_below_1 `12` features `char_shannon_entropy` `1`, `foreign_connector_ratio` `3`, `letter_ratio` `5`, `max_repeated_punct_run` `4`, `non_latin_or_control_unicode_ratio` `12`, `punct_ratio` `5`, `rare_nonletter_bigram_rate` `1`, `rare_nonletter_char_rate` `6`, `symbol_ratio` `12`, `target_connector_ratio` `9`.
- `near_ood_neighbor` `HYBRID_BOUNDARY` n `12` full_doc mean `0.8730096561047865` n_below_1 `7` features `letter_ratio` `2`, `punct_ratio` `2`, `rare_nonletter_char_rate` `2`, `symbol_ratio` `2`; min_full_clause mean `0.8097494496691354` n_below_1 `9` features `char_shannon_entropy` `5`, `foreign_connector_ratio` `1`, `letter_ratio` `3`, `punct_ratio` `2`, `rare_nonletter_char_rate` `2`, `symbol_ratio` `2`.
- `panaderia_fermentacion` `IN_DOMAIN_VALID` n `10` full_doc mean `0.5553236913122764` n_below_1 `9` features `foreign_connector_ratio` `1`, `punct_ratio` `5`, `rare_nonletter_char_rate` `5`; min_full_clause mean `0.5039149200505284` n_below_1 `10` features `char_shannon_entropy` `3`, `foreign_connector_ratio` `1`, `letter_ratio` `3`, `punct_ratio` `6`, `rare_nonletter_char_rate` `5`, `symbol_ratio` `1`.
- `receta_completa` `IN_DOMAIN_VALID` n `10` full_doc mean `0.9951559522284821` n_below_1 `1` features `symbol_ratio` `1`; min_full_clause mean `0.9332966539612337` n_below_1 `5` features `char_shannon_entropy` `4`, `foreign_connector_ratio` `2`, `letter_ratio` `1`, `symbol_ratio` `2`, `target_connector_ratio` `1`.
- `salsas_emulsiones` `IN_DOMAIN_VALID` n `8` full_doc mean `0.5612106971026649` n_below_1 `7` features `letter_ratio` `1`, `punct_ratio` `2`, `rare_nonletter_char_rate` `4`, `symbol_ratio` `1`, `target_connector_ratio` `1`; min_full_clause mean `0.4984571763777811` n_below_1 `7` features `char_shannon_entropy` `3`, `letter_ratio` `2`, `punct_ratio` `2`, `rare_nonletter_char_rate` `4`, `symbol_ratio` `1`, `target_connector_ratio` `1`.
- `smuggle_recipe_footnote` `HYBRID_BOUNDARY` n `10` full_doc mean `0.10655450030333107` n_below_1 `9` features `char_shannon_entropy` `5`, `digit_ratio` `1`, `punct_ratio` `1`, `rare_nonletter_bigram_rate` `9`, `rare_nonletter_char_rate` `9`, `symbol_ratio` `2`, `target_connector_ratio` `1`; min_full_clause mean `0.10391163800745092` n_below_1 `9` features `char_shannon_entropy` `8`, `digit_ratio` `1`, `letter_ratio` `3`, `punct_ratio` `9`, `rare_nonletter_bigram_rate` `9`, `rare_nonletter_char_rate` `9`, `symbol_ratio` `3`, `target_connector_ratio` `1`.
- `sustitucion_ingredientes` `IN_DOMAIN_VALID` n `8` full_doc mean `0.19816987506111944` n_below_1 `8` features `punct_ratio` `1`, `rare_nonletter_char_rate` `8`, `symbol_ratio` `1`; min_full_clause mean `0.014264233908999256` n_below_1 `8` features `char_shannon_entropy` `1`, `punct_ratio` `1`, `rare_nonletter_char_rate` `8`, `symbol_ratio` `1`.
- `tecnica_culinaria` `IN_DOMAIN_VALID` n `10` full_doc mean `0.551495245911283` n_below_1 `8` features `punct_ratio` `5`, `rare_nonletter_char_rate` `5`, `symbol_ratio` `2`; min_full_clause mean `0.4996121921276638` n_below_1 `9` features `char_shannon_entropy` `4`, `punct_ratio` `5`, `rare_nonletter_char_rate` `5`, `symbol_ratio` `3`, `target_connector_ratio` `1`.
- `temperatura_tiempos` `IN_DOMAIN_VALID` n `6` full_doc mean `0.4299355219530636` n_below_1 `4` features `punct_ratio` `1`, `rare_nonletter_char_rate` `4`, `symbol_ratio` `1`; min_full_clause mean `0.339299718405166` n_below_1 `5` features `char_shannon_entropy` `4`, `punct_ratio` `1`, `rare_nonletter_char_rate` `4`, `symbol_ratio` `1`.
- `long_debugging_walkthrough` is absent from `struct_firing` on this cell.
### receta / clauses / 1B_base_tech_noise
Grid rows 9360. Rows whose CAL_ONLY p10 F1 is below the frozen TASK-013 value: 8736. Both counts are computed from the stored grid.
- Headline `dir1024_sig_sep|additive|a=0.10|g=tail_p10|beta|b=0.00|y=-|r=full_doc|w=0.20` F1 `0.8648648648648649`.
- Paired alpha=0 beta=0 `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` F1 `0.8770053475935828` is below the headline when the headline is compared with this row.
- Paired guard-only `dir1024_sig_sep|additive|a=0.05|g=tail_p5|beta|b=0.00|y=-|r=full_doc|w=0.20` F1 `0.8648648648648649`.
- Paired struct-only `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.05|y=-|r=full_doc|w=0.20` F1 `0.8275862068965517`.
- `[HOLDOUT_MAX_SCAN]` `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` F1 `0.8770053475935828`.
S_struct latency (microseconds per score() call on holdout strings): combined p50 `20.625` us, p99 `200.49970000000062` us. full_doc n `400` p50 `47.2085` p99 `946.2988399999999`. clause_opt2c n `1946` p50 `19.375` p99 `54.93749999999994`.
Per-feature firing on the focus subtypes, plus in-domain rows whose full_doc `n_below_1` is not zero:
- `cocina_regional` `IN_DOMAIN_VALID` n `8` full_doc mean `0.5833892136217328` n_below_1 `6` features `foreign_connector_ratio` `1`, `punct_ratio` `2`, `rare_nonletter_char_rate` `4`, `target_connector_ratio` `1`; min_full_clause mean `0.4804626378701009` n_below_1 `6` features `char_shannon_entropy` `2`, `foreign_connector_ratio` `1`, `punct_ratio` `2`, `rare_nonletter_char_rate` `4`, `symbol_ratio` `1`, `target_connector_ratio` `2`.
- `consulta_corta` `IN_DOMAIN_VALID` n `20` full_doc mean `0.028940498658351486` n_below_1 `20` features `char_shannon_entropy` `8`, `letter_ratio` `7`, `max_repeated_punct_run` `15`, `punct_ratio` `16`, `rare_nonletter_char_rate` `5`, `symbol_ratio` `7`, `target_connector_ratio` `6`; min_full_clause mean `0.024162241650889142` n_below_1 `20` features `char_shannon_entropy` `9`, `letter_ratio` `7`, `max_repeated_punct_run` `15`, `punct_ratio` `16`, `rare_nonletter_char_rate` `5`, `symbol_ratio` `7`, `target_connector_ratio` `6`.
- `diagnostico_pasteleria_panaderia` `IN_DOMAIN_VALID` n `8` full_doc mean `1.0` n_below_1 `0` features `none`; min_full_clause mean `0.9367547842571509` n_below_1 `6` features `char_shannon_entropy` `3`, `foreign_connector_ratio` `1`, `letter_ratio` `3`, `symbol_ratio` `1`, `target_connector_ratio` `3`.
- `dilution_80_20` `HYBRID_BOUNDARY` n `10` full_doc mean `0.7783372923780758` n_below_1 `8` features `char_shannon_entropy` `2`, `punct_ratio` `1`, `rare_nonletter_char_rate` `6`, `symbol_ratio` `4`, `target_connector_ratio` `1`; min_full_clause mean `0.30187841129659954` n_below_1 `10` features `char_shannon_entropy` `5`, `foreign_connector_ratio` `2`, `letter_ratio` `2`, `punct_ratio` `1`, `rare_nonletter_char_rate` `7`, `symbol_ratio` `5`, `target_connector_ratio` `2`.
- `extreme_short_punct` `ADVERSARIAL_FUZZING` n `10` full_doc mean `5.614891346849248e-06` n_below_1 `10` features `char_shannon_entropy` `10`, `digit_ratio` `1`, `letter_ratio` `10`, `max_repeated_punct_run` `6`, `punct_ratio` `10`, `rare_nonletter_bigram_rate` `9`, `rare_nonletter_char_rate` `7`, `symbol_ratio` `3`; min_full_clause mean `5.59328641587905e-06` n_below_1 `10` features `char_shannon_entropy` `10`, `digit_ratio` `1`, `letter_ratio` `10`, `max_repeated_punct_run` `6`, `punct_ratio` `10`, `rare_nonletter_bigram_rate` `9`, `rare_nonletter_char_rate` `9`, `symbol_ratio` `3`.
- `homoglyph_zwsp_fullwidth` `ADVERSARIAL_FUZZING` n `12` full_doc mean `0.023747952634073626` n_below_1 `12` features `char_shannon_entropy` `1`, `foreign_connector_ratio` `3`, `letter_ratio` `5`, `max_repeated_punct_run` `4`, `non_latin_or_control_unicode_ratio` `12`, `punct_ratio` `5`, `rare_nonletter_bigram_rate` `1`, `rare_nonletter_char_rate` `6`, `symbol_ratio` `12`, `target_connector_ratio` `9`; min_full_clause mean `0.023747952634073626` n_below_1 `12` features `char_shannon_entropy` `1`, `foreign_connector_ratio` `3`, `letter_ratio` `5`, `max_repeated_punct_run` `4`, `non_latin_or_control_unicode_ratio` `12`, `punct_ratio` `5`, `rare_nonletter_bigram_rate` `1`, `rare_nonletter_char_rate` `6`, `symbol_ratio` `12`, `target_connector_ratio` `9`.
- `near_ood_neighbor` `HYBRID_BOUNDARY` n `12` full_doc mean `0.8730096561047865` n_below_1 `7` features `letter_ratio` `2`, `punct_ratio` `2`, `rare_nonletter_char_rate` `2`, `symbol_ratio` `2`; min_full_clause mean `0.8097494496691354` n_below_1 `9` features `char_shannon_entropy` `5`, `foreign_connector_ratio` `1`, `letter_ratio` `3`, `punct_ratio` `2`, `rare_nonletter_char_rate` `2`, `symbol_ratio` `2`.
- `panaderia_fermentacion` `IN_DOMAIN_VALID` n `10` full_doc mean `0.5553236913122764` n_below_1 `9` features `foreign_connector_ratio` `1`, `punct_ratio` `5`, `rare_nonletter_char_rate` `5`; min_full_clause mean `0.5039149200505284` n_below_1 `10` features `char_shannon_entropy` `3`, `foreign_connector_ratio` `1`, `letter_ratio` `3`, `punct_ratio` `6`, `rare_nonletter_char_rate` `5`, `symbol_ratio` `1`.
- `receta_completa` `IN_DOMAIN_VALID` n `10` full_doc mean `0.9951559522284821` n_below_1 `1` features `symbol_ratio` `1`; min_full_clause mean `0.9332966539612337` n_below_1 `5` features `char_shannon_entropy` `4`, `foreign_connector_ratio` `2`, `letter_ratio` `1`, `symbol_ratio` `2`, `target_connector_ratio` `1`.
- `salsas_emulsiones` `IN_DOMAIN_VALID` n `8` full_doc mean `0.5612106971026649` n_below_1 `7` features `letter_ratio` `1`, `punct_ratio` `2`, `rare_nonletter_char_rate` `4`, `symbol_ratio` `1`, `target_connector_ratio` `1`; min_full_clause mean `0.4984571763777811` n_below_1 `7` features `char_shannon_entropy` `3`, `letter_ratio` `2`, `punct_ratio` `2`, `rare_nonletter_char_rate` `4`, `symbol_ratio` `1`, `target_connector_ratio` `1`.
- `smuggle_recipe_footnote` `HYBRID_BOUNDARY` n `10` full_doc mean `0.10655450030333107` n_below_1 `9` features `char_shannon_entropy` `5`, `digit_ratio` `1`, `punct_ratio` `1`, `rare_nonletter_bigram_rate` `9`, `rare_nonletter_char_rate` `9`, `symbol_ratio` `2`, `target_connector_ratio` `1`; min_full_clause mean `0.10391163800745092` n_below_1 `9` features `char_shannon_entropy` `8`, `digit_ratio` `1`, `letter_ratio` `3`, `punct_ratio` `9`, `rare_nonletter_bigram_rate` `9`, `rare_nonletter_char_rate` `9`, `symbol_ratio` `3`, `target_connector_ratio` `1`.
- `sustitucion_ingredientes` `IN_DOMAIN_VALID` n `8` full_doc mean `0.19816987506111944` n_below_1 `8` features `punct_ratio` `1`, `rare_nonletter_char_rate` `8`, `symbol_ratio` `1`; min_full_clause mean `0.014264233908999256` n_below_1 `8` features `char_shannon_entropy` `1`, `punct_ratio` `1`, `rare_nonletter_char_rate` `8`, `symbol_ratio` `1`.
- `tecnica_culinaria` `IN_DOMAIN_VALID` n `10` full_doc mean `0.551495245911283` n_below_1 `8` features `punct_ratio` `5`, `rare_nonletter_char_rate` `5`, `symbol_ratio` `2`; min_full_clause mean `0.4996121921276638` n_below_1 `9` features `char_shannon_entropy` `4`, `punct_ratio` `5`, `rare_nonletter_char_rate` `5`, `symbol_ratio` `3`, `target_connector_ratio` `1`.
- `temperatura_tiempos` `IN_DOMAIN_VALID` n `6` full_doc mean `0.4299355219530636` n_below_1 `4` features `punct_ratio` `1`, `rare_nonletter_char_rate` `4`, `symbol_ratio` `1`; min_full_clause mean `0.339299718405166` n_below_1 `5` features `char_shannon_entropy` `4`, `punct_ratio` `1`, `rare_nonletter_char_rate` `4`, `symbol_ratio` `1`.
- `long_debugging_walkthrough` is absent from `struct_firing` on this cell.
### receta / full_only / 1B_full
Grid rows 1170. Rows whose CAL_ONLY p10 F1 is below the frozen TASK-013 value: 1170. Both counts are computed from the stored grid.
- Headline `dir1024_clip_polboost|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` F1 `0.6222222222222222`.
- Paired alpha=0 beta=0 `dir1024_clip_polboost|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` F1 `0.6222222222222222` is tied with the headline when the headline is compared with this row.
- Paired guard-only `dir1024_clip_polboost|additive|a=0.05|g=tail_p5|beta|b=0.00|y=-|r=full_doc|w=-` F1 `0.6145251396648045`.
- Paired struct-only `dir1024_clip_polboost|identity|a=0.00|g=-|beta|b=0.05|y=-|r=full_doc|w=-` F1 `0.5508982035928144`.
- `[HOLDOUT_MAX_SCAN]` `polarity_v2_subset|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` F1 `0.7064676616915423`.
S_struct latency (microseconds per score() call on holdout strings): combined p50 `20.625` us, p99 `200.49970000000062` us. full_doc n `400` p50 `47.2085` p99 `946.2988399999999`. clause_opt2c n `1946` p50 `19.375` p99 `54.93749999999994`.
Per-feature firing on the focus subtypes, plus in-domain rows whose full_doc `n_below_1` is not zero:
- `cocina_regional` `IN_DOMAIN_VALID` n `8` full_doc mean `0.5833892136217328` n_below_1 `6` features `foreign_connector_ratio` `1`, `punct_ratio` `2`, `rare_nonletter_char_rate` `4`, `target_connector_ratio` `1`; min_full_clause mean `0.4804626378701009` n_below_1 `6` features `char_shannon_entropy` `2`, `foreign_connector_ratio` `1`, `punct_ratio` `2`, `rare_nonletter_char_rate` `4`, `symbol_ratio` `1`, `target_connector_ratio` `2`.
- `consulta_corta` `IN_DOMAIN_VALID` n `20` full_doc mean `0.028940498658351486` n_below_1 `20` features `char_shannon_entropy` `8`, `letter_ratio` `7`, `max_repeated_punct_run` `15`, `punct_ratio` `16`, `rare_nonletter_char_rate` `5`, `symbol_ratio` `7`, `target_connector_ratio` `6`; min_full_clause mean `0.024162241650889142` n_below_1 `20` features `char_shannon_entropy` `9`, `letter_ratio` `7`, `max_repeated_punct_run` `15`, `punct_ratio` `16`, `rare_nonletter_char_rate` `5`, `symbol_ratio` `7`, `target_connector_ratio` `6`.
- `diagnostico_pasteleria_panaderia` `IN_DOMAIN_VALID` n `8` full_doc mean `1.0` n_below_1 `0` features `none`; min_full_clause mean `0.9367547842571509` n_below_1 `6` features `char_shannon_entropy` `3`, `foreign_connector_ratio` `1`, `letter_ratio` `3`, `symbol_ratio` `1`, `target_connector_ratio` `3`.
- `dilution_80_20` `HYBRID_BOUNDARY` n `10` full_doc mean `0.7783372923780758` n_below_1 `8` features `char_shannon_entropy` `2`, `punct_ratio` `1`, `rare_nonletter_char_rate` `6`, `symbol_ratio` `4`, `target_connector_ratio` `1`; min_full_clause mean `0.30187841129659954` n_below_1 `10` features `char_shannon_entropy` `5`, `foreign_connector_ratio` `2`, `letter_ratio` `2`, `punct_ratio` `1`, `rare_nonletter_char_rate` `7`, `symbol_ratio` `5`, `target_connector_ratio` `2`.
- `extreme_short_punct` `ADVERSARIAL_FUZZING` n `10` full_doc mean `5.614891346849248e-06` n_below_1 `10` features `char_shannon_entropy` `10`, `digit_ratio` `1`, `letter_ratio` `10`, `max_repeated_punct_run` `6`, `punct_ratio` `10`, `rare_nonletter_bigram_rate` `9`, `rare_nonletter_char_rate` `7`, `symbol_ratio` `3`; min_full_clause mean `5.59328641587905e-06` n_below_1 `10` features `char_shannon_entropy` `10`, `digit_ratio` `1`, `letter_ratio` `10`, `max_repeated_punct_run` `6`, `punct_ratio` `10`, `rare_nonletter_bigram_rate` `9`, `rare_nonletter_char_rate` `9`, `symbol_ratio` `3`.
- `homoglyph_zwsp_fullwidth` `ADVERSARIAL_FUZZING` n `12` full_doc mean `0.023747952634073626` n_below_1 `12` features `char_shannon_entropy` `1`, `foreign_connector_ratio` `3`, `letter_ratio` `5`, `max_repeated_punct_run` `4`, `non_latin_or_control_unicode_ratio` `12`, `punct_ratio` `5`, `rare_nonletter_bigram_rate` `1`, `rare_nonletter_char_rate` `6`, `symbol_ratio` `12`, `target_connector_ratio` `9`; min_full_clause mean `0.023747952634073626` n_below_1 `12` features `char_shannon_entropy` `1`, `foreign_connector_ratio` `3`, `letter_ratio` `5`, `max_repeated_punct_run` `4`, `non_latin_or_control_unicode_ratio` `12`, `punct_ratio` `5`, `rare_nonletter_bigram_rate` `1`, `rare_nonletter_char_rate` `6`, `symbol_ratio` `12`, `target_connector_ratio` `9`.
- `near_ood_neighbor` `HYBRID_BOUNDARY` n `12` full_doc mean `0.8730096561047865` n_below_1 `7` features `letter_ratio` `2`, `punct_ratio` `2`, `rare_nonletter_char_rate` `2`, `symbol_ratio` `2`; min_full_clause mean `0.8097494496691354` n_below_1 `9` features `char_shannon_entropy` `5`, `foreign_connector_ratio` `1`, `letter_ratio` `3`, `punct_ratio` `2`, `rare_nonletter_char_rate` `2`, `symbol_ratio` `2`.
- `panaderia_fermentacion` `IN_DOMAIN_VALID` n `10` full_doc mean `0.5553236913122764` n_below_1 `9` features `foreign_connector_ratio` `1`, `punct_ratio` `5`, `rare_nonletter_char_rate` `5`; min_full_clause mean `0.5039149200505284` n_below_1 `10` features `char_shannon_entropy` `3`, `foreign_connector_ratio` `1`, `letter_ratio` `3`, `punct_ratio` `6`, `rare_nonletter_char_rate` `5`, `symbol_ratio` `1`.
- `receta_completa` `IN_DOMAIN_VALID` n `10` full_doc mean `0.9951559522284821` n_below_1 `1` features `symbol_ratio` `1`; min_full_clause mean `0.9332966539612337` n_below_1 `5` features `char_shannon_entropy` `4`, `foreign_connector_ratio` `2`, `letter_ratio` `1`, `symbol_ratio` `2`, `target_connector_ratio` `1`.
- `salsas_emulsiones` `IN_DOMAIN_VALID` n `8` full_doc mean `0.5612106971026649` n_below_1 `7` features `letter_ratio` `1`, `punct_ratio` `2`, `rare_nonletter_char_rate` `4`, `symbol_ratio` `1`, `target_connector_ratio` `1`; min_full_clause mean `0.4984571763777811` n_below_1 `7` features `char_shannon_entropy` `3`, `letter_ratio` `2`, `punct_ratio` `2`, `rare_nonletter_char_rate` `4`, `symbol_ratio` `1`, `target_connector_ratio` `1`.
- `smuggle_recipe_footnote` `HYBRID_BOUNDARY` n `10` full_doc mean `0.10655450030333107` n_below_1 `9` features `char_shannon_entropy` `5`, `digit_ratio` `1`, `punct_ratio` `1`, `rare_nonletter_bigram_rate` `9`, `rare_nonletter_char_rate` `9`, `symbol_ratio` `2`, `target_connector_ratio` `1`; min_full_clause mean `0.10391163800745092` n_below_1 `9` features `char_shannon_entropy` `8`, `digit_ratio` `1`, `letter_ratio` `3`, `punct_ratio` `9`, `rare_nonletter_bigram_rate` `9`, `rare_nonletter_char_rate` `9`, `symbol_ratio` `3`, `target_connector_ratio` `1`.
- `sustitucion_ingredientes` `IN_DOMAIN_VALID` n `8` full_doc mean `0.19816987506111944` n_below_1 `8` features `punct_ratio` `1`, `rare_nonletter_char_rate` `8`, `symbol_ratio` `1`; min_full_clause mean `0.014264233908999256` n_below_1 `8` features `char_shannon_entropy` `1`, `punct_ratio` `1`, `rare_nonletter_char_rate` `8`, `symbol_ratio` `1`.
- `tecnica_culinaria` `IN_DOMAIN_VALID` n `10` full_doc mean `0.551495245911283` n_below_1 `8` features `punct_ratio` `5`, `rare_nonletter_char_rate` `5`, `symbol_ratio` `2`; min_full_clause mean `0.4996121921276638` n_below_1 `9` features `char_shannon_entropy` `4`, `punct_ratio` `5`, `rare_nonletter_char_rate` `5`, `symbol_ratio` `3`, `target_connector_ratio` `1`.
- `temperatura_tiempos` `IN_DOMAIN_VALID` n `6` full_doc mean `0.4299355219530636` n_below_1 `4` features `punct_ratio` `1`, `rare_nonletter_char_rate` `4`, `symbol_ratio` `1`; min_full_clause mean `0.339299718405166` n_below_1 `5` features `char_shannon_entropy` `4`, `punct_ratio` `1`, `rare_nonletter_char_rate` `4`, `symbol_ratio` `1`.
- `long_debugging_walkthrough` is absent from `struct_firing` on this cell.
### receta / clauses / 1B_full
Grid rows 9360. Rows whose CAL_ONLY p10 F1 is below the frozen TASK-013 value: 8747. Both counts are computed from the stored grid.
- Headline `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` F1 `0.8829787234042553`.
- Paired alpha=0 beta=0 `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` F1 `0.8829787234042553` is tied with the headline when the headline is compared with this row.
- Paired guard-only `dir1024_sig_sep|additive|a=0.05|g=f2_l2|beta|b=0.00|y=-|r=full_doc|w=0.20` F1 `0.8770053475935828`.
- Paired struct-only `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.05|y=-|r=full_doc|w=0.20` F1 `0.8342857142857143`.
- `[HOLDOUT_MAX_SCAN]` `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` F1 `0.8829787234042553`.
S_struct latency (microseconds per score() call on holdout strings): combined p50 `20.625` us, p99 `200.49970000000062` us. full_doc n `400` p50 `47.2085` p99 `946.2988399999999`. clause_opt2c n `1946` p50 `19.375` p99 `54.93749999999994`.
Per-feature firing on the focus subtypes, plus in-domain rows whose full_doc `n_below_1` is not zero:
- `cocina_regional` `IN_DOMAIN_VALID` n `8` full_doc mean `0.5833892136217328` n_below_1 `6` features `foreign_connector_ratio` `1`, `punct_ratio` `2`, `rare_nonletter_char_rate` `4`, `target_connector_ratio` `1`; min_full_clause mean `0.4804626378701009` n_below_1 `6` features `char_shannon_entropy` `2`, `foreign_connector_ratio` `1`, `punct_ratio` `2`, `rare_nonletter_char_rate` `4`, `symbol_ratio` `1`, `target_connector_ratio` `2`.
- `consulta_corta` `IN_DOMAIN_VALID` n `20` full_doc mean `0.028940498658351486` n_below_1 `20` features `char_shannon_entropy` `8`, `letter_ratio` `7`, `max_repeated_punct_run` `15`, `punct_ratio` `16`, `rare_nonletter_char_rate` `5`, `symbol_ratio` `7`, `target_connector_ratio` `6`; min_full_clause mean `0.024162241650889142` n_below_1 `20` features `char_shannon_entropy` `9`, `letter_ratio` `7`, `max_repeated_punct_run` `15`, `punct_ratio` `16`, `rare_nonletter_char_rate` `5`, `symbol_ratio` `7`, `target_connector_ratio` `6`.
- `diagnostico_pasteleria_panaderia` `IN_DOMAIN_VALID` n `8` full_doc mean `1.0` n_below_1 `0` features `none`; min_full_clause mean `0.9367547842571509` n_below_1 `6` features `char_shannon_entropy` `3`, `foreign_connector_ratio` `1`, `letter_ratio` `3`, `symbol_ratio` `1`, `target_connector_ratio` `3`.
- `dilution_80_20` `HYBRID_BOUNDARY` n `10` full_doc mean `0.7783372923780758` n_below_1 `8` features `char_shannon_entropy` `2`, `punct_ratio` `1`, `rare_nonletter_char_rate` `6`, `symbol_ratio` `4`, `target_connector_ratio` `1`; min_full_clause mean `0.30187841129659954` n_below_1 `10` features `char_shannon_entropy` `5`, `foreign_connector_ratio` `2`, `letter_ratio` `2`, `punct_ratio` `1`, `rare_nonletter_char_rate` `7`, `symbol_ratio` `5`, `target_connector_ratio` `2`.
- `extreme_short_punct` `ADVERSARIAL_FUZZING` n `10` full_doc mean `5.614891346849248e-06` n_below_1 `10` features `char_shannon_entropy` `10`, `digit_ratio` `1`, `letter_ratio` `10`, `max_repeated_punct_run` `6`, `punct_ratio` `10`, `rare_nonletter_bigram_rate` `9`, `rare_nonletter_char_rate` `7`, `symbol_ratio` `3`; min_full_clause mean `5.59328641587905e-06` n_below_1 `10` features `char_shannon_entropy` `10`, `digit_ratio` `1`, `letter_ratio` `10`, `max_repeated_punct_run` `6`, `punct_ratio` `10`, `rare_nonletter_bigram_rate` `9`, `rare_nonletter_char_rate` `9`, `symbol_ratio` `3`.
- `homoglyph_zwsp_fullwidth` `ADVERSARIAL_FUZZING` n `12` full_doc mean `0.023747952634073626` n_below_1 `12` features `char_shannon_entropy` `1`, `foreign_connector_ratio` `3`, `letter_ratio` `5`, `max_repeated_punct_run` `4`, `non_latin_or_control_unicode_ratio` `12`, `punct_ratio` `5`, `rare_nonletter_bigram_rate` `1`, `rare_nonletter_char_rate` `6`, `symbol_ratio` `12`, `target_connector_ratio` `9`; min_full_clause mean `0.023747952634073626` n_below_1 `12` features `char_shannon_entropy` `1`, `foreign_connector_ratio` `3`, `letter_ratio` `5`, `max_repeated_punct_run` `4`, `non_latin_or_control_unicode_ratio` `12`, `punct_ratio` `5`, `rare_nonletter_bigram_rate` `1`, `rare_nonletter_char_rate` `6`, `symbol_ratio` `12`, `target_connector_ratio` `9`.
- `near_ood_neighbor` `HYBRID_BOUNDARY` n `12` full_doc mean `0.8730096561047865` n_below_1 `7` features `letter_ratio` `2`, `punct_ratio` `2`, `rare_nonletter_char_rate` `2`, `symbol_ratio` `2`; min_full_clause mean `0.8097494496691354` n_below_1 `9` features `char_shannon_entropy` `5`, `foreign_connector_ratio` `1`, `letter_ratio` `3`, `punct_ratio` `2`, `rare_nonletter_char_rate` `2`, `symbol_ratio` `2`.
- `panaderia_fermentacion` `IN_DOMAIN_VALID` n `10` full_doc mean `0.5553236913122764` n_below_1 `9` features `foreign_connector_ratio` `1`, `punct_ratio` `5`, `rare_nonletter_char_rate` `5`; min_full_clause mean `0.5039149200505284` n_below_1 `10` features `char_shannon_entropy` `3`, `foreign_connector_ratio` `1`, `letter_ratio` `3`, `punct_ratio` `6`, `rare_nonletter_char_rate` `5`, `symbol_ratio` `1`.
- `receta_completa` `IN_DOMAIN_VALID` n `10` full_doc mean `0.9951559522284821` n_below_1 `1` features `symbol_ratio` `1`; min_full_clause mean `0.9332966539612337` n_below_1 `5` features `char_shannon_entropy` `4`, `foreign_connector_ratio` `2`, `letter_ratio` `1`, `symbol_ratio` `2`, `target_connector_ratio` `1`.
- `salsas_emulsiones` `IN_DOMAIN_VALID` n `8` full_doc mean `0.5612106971026649` n_below_1 `7` features `letter_ratio` `1`, `punct_ratio` `2`, `rare_nonletter_char_rate` `4`, `symbol_ratio` `1`, `target_connector_ratio` `1`; min_full_clause mean `0.4984571763777811` n_below_1 `7` features `char_shannon_entropy` `3`, `letter_ratio` `2`, `punct_ratio` `2`, `rare_nonletter_char_rate` `4`, `symbol_ratio` `1`, `target_connector_ratio` `1`.
- `smuggle_recipe_footnote` `HYBRID_BOUNDARY` n `10` full_doc mean `0.10655450030333107` n_below_1 `9` features `char_shannon_entropy` `5`, `digit_ratio` `1`, `punct_ratio` `1`, `rare_nonletter_bigram_rate` `9`, `rare_nonletter_char_rate` `9`, `symbol_ratio` `2`, `target_connector_ratio` `1`; min_full_clause mean `0.10391163800745092` n_below_1 `9` features `char_shannon_entropy` `8`, `digit_ratio` `1`, `letter_ratio` `3`, `punct_ratio` `9`, `rare_nonletter_bigram_rate` `9`, `rare_nonletter_char_rate` `9`, `symbol_ratio` `3`, `target_connector_ratio` `1`.
- `sustitucion_ingredientes` `IN_DOMAIN_VALID` n `8` full_doc mean `0.19816987506111944` n_below_1 `8` features `punct_ratio` `1`, `rare_nonletter_char_rate` `8`, `symbol_ratio` `1`; min_full_clause mean `0.014264233908999256` n_below_1 `8` features `char_shannon_entropy` `1`, `punct_ratio` `1`, `rare_nonletter_char_rate` `8`, `symbol_ratio` `1`.
- `tecnica_culinaria` `IN_DOMAIN_VALID` n `10` full_doc mean `0.551495245911283` n_below_1 `8` features `punct_ratio` `5`, `rare_nonletter_char_rate` `5`, `symbol_ratio` `2`; min_full_clause mean `0.4996121921276638` n_below_1 `9` features `char_shannon_entropy` `4`, `punct_ratio` `5`, `rare_nonletter_char_rate` `5`, `symbol_ratio` `3`, `target_connector_ratio` `1`.
- `temperatura_tiempos` `IN_DOMAIN_VALID` n `6` full_doc mean `0.4299355219530636` n_below_1 `4` features `punct_ratio` `1`, `rare_nonletter_char_rate` `4`, `symbol_ratio` `1`; min_full_clause mean `0.339299718405166` n_below_1 `5` features `char_shannon_entropy` `4`, `punct_ratio` `1`, `rare_nonletter_char_rate` `4`, `symbol_ratio` `1`.
- `long_debugging_walkthrough` is absent from `struct_firing` on this cell.
### receta / full_only / 1B_full_v3
Grid rows 1170. Rows whose CAL_ONLY p10 F1 is below the frozen TASK-013 value: 1170. Both counts are computed from the stored grid.
- Headline `polarity_v2_subset|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` F1 `0.7164179104477612`.
- Paired alpha=0 beta=0 `polarity_v2_subset|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` F1 `0.7164179104477612` is tied with the headline when the headline is compared with this row.
- Paired guard-only row is absent.
- Paired struct-only `polarity_v2_subset|identity|a=0.00|g=-|beta|b=0.05|y=-|r=full_doc|w=-` F1 `0.694300518134715`.
- `[HOLDOUT_MAX_SCAN]` `polarity_v2_subset|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` F1 `0.7164179104477612`.
S_struct latency (microseconds per score() call on holdout strings): combined p50 `20.625` us, p99 `200.49970000000062` us. full_doc n `400` p50 `47.2085` p99 `946.2988399999999`. clause_opt2c n `1946` p50 `19.375` p99 `54.93749999999994`.
Per-feature firing on the focus subtypes, plus in-domain rows whose full_doc `n_below_1` is not zero:
- `cocina_regional` `IN_DOMAIN_VALID` n `8` full_doc mean `0.5833892136217328` n_below_1 `6` features `foreign_connector_ratio` `1`, `punct_ratio` `2`, `rare_nonletter_char_rate` `4`, `target_connector_ratio` `1`; min_full_clause mean `0.4804626378701009` n_below_1 `6` features `char_shannon_entropy` `2`, `foreign_connector_ratio` `1`, `punct_ratio` `2`, `rare_nonletter_char_rate` `4`, `symbol_ratio` `1`, `target_connector_ratio` `2`.
- `consulta_corta` `IN_DOMAIN_VALID` n `20` full_doc mean `0.028940498658351486` n_below_1 `20` features `char_shannon_entropy` `8`, `letter_ratio` `7`, `max_repeated_punct_run` `15`, `punct_ratio` `16`, `rare_nonletter_char_rate` `5`, `symbol_ratio` `7`, `target_connector_ratio` `6`; min_full_clause mean `0.024162241650889142` n_below_1 `20` features `char_shannon_entropy` `9`, `letter_ratio` `7`, `max_repeated_punct_run` `15`, `punct_ratio` `16`, `rare_nonletter_char_rate` `5`, `symbol_ratio` `7`, `target_connector_ratio` `6`.
- `diagnostico_pasteleria_panaderia` `IN_DOMAIN_VALID` n `8` full_doc mean `1.0` n_below_1 `0` features `none`; min_full_clause mean `0.9367547842571509` n_below_1 `6` features `char_shannon_entropy` `3`, `foreign_connector_ratio` `1`, `letter_ratio` `3`, `symbol_ratio` `1`, `target_connector_ratio` `3`.
- `dilution_80_20` `HYBRID_BOUNDARY` n `10` full_doc mean `0.7783372923780758` n_below_1 `8` features `char_shannon_entropy` `2`, `punct_ratio` `1`, `rare_nonletter_char_rate` `6`, `symbol_ratio` `4`, `target_connector_ratio` `1`; min_full_clause mean `0.30187841129659954` n_below_1 `10` features `char_shannon_entropy` `5`, `foreign_connector_ratio` `2`, `letter_ratio` `2`, `punct_ratio` `1`, `rare_nonletter_char_rate` `7`, `symbol_ratio` `5`, `target_connector_ratio` `2`.
- `extreme_short_punct` `ADVERSARIAL_FUZZING` n `10` full_doc mean `5.614891346849248e-06` n_below_1 `10` features `char_shannon_entropy` `10`, `digit_ratio` `1`, `letter_ratio` `10`, `max_repeated_punct_run` `6`, `punct_ratio` `10`, `rare_nonletter_bigram_rate` `9`, `rare_nonletter_char_rate` `7`, `symbol_ratio` `3`; min_full_clause mean `5.59328641587905e-06` n_below_1 `10` features `char_shannon_entropy` `10`, `digit_ratio` `1`, `letter_ratio` `10`, `max_repeated_punct_run` `6`, `punct_ratio` `10`, `rare_nonletter_bigram_rate` `9`, `rare_nonletter_char_rate` `9`, `symbol_ratio` `3`.
- `homoglyph_zwsp_fullwidth` `ADVERSARIAL_FUZZING` n `12` full_doc mean `0.023747952634073626` n_below_1 `12` features `char_shannon_entropy` `1`, `foreign_connector_ratio` `3`, `letter_ratio` `5`, `max_repeated_punct_run` `4`, `non_latin_or_control_unicode_ratio` `12`, `punct_ratio` `5`, `rare_nonletter_bigram_rate` `1`, `rare_nonletter_char_rate` `6`, `symbol_ratio` `12`, `target_connector_ratio` `9`; min_full_clause mean `0.023747952634073626` n_below_1 `12` features `char_shannon_entropy` `1`, `foreign_connector_ratio` `3`, `letter_ratio` `5`, `max_repeated_punct_run` `4`, `non_latin_or_control_unicode_ratio` `12`, `punct_ratio` `5`, `rare_nonletter_bigram_rate` `1`, `rare_nonletter_char_rate` `6`, `symbol_ratio` `12`, `target_connector_ratio` `9`.
- `near_ood_neighbor` `HYBRID_BOUNDARY` n `12` full_doc mean `0.8730096561047865` n_below_1 `7` features `letter_ratio` `2`, `punct_ratio` `2`, `rare_nonletter_char_rate` `2`, `symbol_ratio` `2`; min_full_clause mean `0.8097494496691354` n_below_1 `9` features `char_shannon_entropy` `5`, `foreign_connector_ratio` `1`, `letter_ratio` `3`, `punct_ratio` `2`, `rare_nonletter_char_rate` `2`, `symbol_ratio` `2`.
- `panaderia_fermentacion` `IN_DOMAIN_VALID` n `10` full_doc mean `0.5553236913122764` n_below_1 `9` features `foreign_connector_ratio` `1`, `punct_ratio` `5`, `rare_nonletter_char_rate` `5`; min_full_clause mean `0.5039149200505284` n_below_1 `10` features `char_shannon_entropy` `3`, `foreign_connector_ratio` `1`, `letter_ratio` `3`, `punct_ratio` `6`, `rare_nonletter_char_rate` `5`, `symbol_ratio` `1`.
- `receta_completa` `IN_DOMAIN_VALID` n `10` full_doc mean `0.9951559522284821` n_below_1 `1` features `symbol_ratio` `1`; min_full_clause mean `0.9332966539612337` n_below_1 `5` features `char_shannon_entropy` `4`, `foreign_connector_ratio` `2`, `letter_ratio` `1`, `symbol_ratio` `2`, `target_connector_ratio` `1`.
- `salsas_emulsiones` `IN_DOMAIN_VALID` n `8` full_doc mean `0.5612106971026649` n_below_1 `7` features `letter_ratio` `1`, `punct_ratio` `2`, `rare_nonletter_char_rate` `4`, `symbol_ratio` `1`, `target_connector_ratio` `1`; min_full_clause mean `0.4984571763777811` n_below_1 `7` features `char_shannon_entropy` `3`, `letter_ratio` `2`, `punct_ratio` `2`, `rare_nonletter_char_rate` `4`, `symbol_ratio` `1`, `target_connector_ratio` `1`.
- `smuggle_recipe_footnote` `HYBRID_BOUNDARY` n `10` full_doc mean `0.10655450030333107` n_below_1 `9` features `char_shannon_entropy` `5`, `digit_ratio` `1`, `punct_ratio` `1`, `rare_nonletter_bigram_rate` `9`, `rare_nonletter_char_rate` `9`, `symbol_ratio` `2`, `target_connector_ratio` `1`; min_full_clause mean `0.10391163800745092` n_below_1 `9` features `char_shannon_entropy` `8`, `digit_ratio` `1`, `letter_ratio` `3`, `punct_ratio` `9`, `rare_nonletter_bigram_rate` `9`, `rare_nonletter_char_rate` `9`, `symbol_ratio` `3`, `target_connector_ratio` `1`.
- `sustitucion_ingredientes` `IN_DOMAIN_VALID` n `8` full_doc mean `0.19816987506111944` n_below_1 `8` features `punct_ratio` `1`, `rare_nonletter_char_rate` `8`, `symbol_ratio` `1`; min_full_clause mean `0.014264233908999256` n_below_1 `8` features `char_shannon_entropy` `1`, `punct_ratio` `1`, `rare_nonletter_char_rate` `8`, `symbol_ratio` `1`.
- `tecnica_culinaria` `IN_DOMAIN_VALID` n `10` full_doc mean `0.551495245911283` n_below_1 `8` features `punct_ratio` `5`, `rare_nonletter_char_rate` `5`, `symbol_ratio` `2`; min_full_clause mean `0.4996121921276638` n_below_1 `9` features `char_shannon_entropy` `4`, `punct_ratio` `5`, `rare_nonletter_char_rate` `5`, `symbol_ratio` `3`, `target_connector_ratio` `1`.
- `temperatura_tiempos` `IN_DOMAIN_VALID` n `6` full_doc mean `0.4299355219530636` n_below_1 `4` features `punct_ratio` `1`, `rare_nonletter_char_rate` `4`, `symbol_ratio` `1`; min_full_clause mean `0.339299718405166` n_below_1 `5` features `char_shannon_entropy` `4`, `punct_ratio` `1`, `rare_nonletter_char_rate` `4`, `symbol_ratio` `1`.
- `long_debugging_walkthrough` is absent from `struct_firing` on this cell.
### receta / clauses / 1B_full_v3
Grid rows 9360. Rows whose CAL_ONLY p10 F1 is below the frozen TASK-013 value: 8806. Both counts are computed from the stored grid.
- Headline `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` F1 `0.8770053475935828`.
- Paired alpha=0 beta=0 `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` F1 `0.8770053475935828` is tied with the headline when the headline is compared with this row.
- Paired guard-only `dir1024_sig_sep|additive|a=0.05|g=tail_p5|beta|b=0.00|y=-|r=full_doc|w=0.20` F1 `0.8770053475935828`.
- Paired struct-only `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.05|y=-|r=full_doc|w=0.20` F1 `0.8208092485549133`.
- `[HOLDOUT_MAX_SCAN]` `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` F1 `0.8770053475935828`.
S_struct latency (microseconds per score() call on holdout strings): combined p50 `20.625` us, p99 `200.49970000000062` us. full_doc n `400` p50 `47.2085` p99 `946.2988399999999`. clause_opt2c n `1946` p50 `19.375` p99 `54.93749999999994`.
Per-feature firing on the focus subtypes, plus in-domain rows whose full_doc `n_below_1` is not zero:
- `cocina_regional` `IN_DOMAIN_VALID` n `8` full_doc mean `0.5833892136217328` n_below_1 `6` features `foreign_connector_ratio` `1`, `punct_ratio` `2`, `rare_nonletter_char_rate` `4`, `target_connector_ratio` `1`; min_full_clause mean `0.4804626378701009` n_below_1 `6` features `char_shannon_entropy` `2`, `foreign_connector_ratio` `1`, `punct_ratio` `2`, `rare_nonletter_char_rate` `4`, `symbol_ratio` `1`, `target_connector_ratio` `2`.
- `consulta_corta` `IN_DOMAIN_VALID` n `20` full_doc mean `0.028940498658351486` n_below_1 `20` features `char_shannon_entropy` `8`, `letter_ratio` `7`, `max_repeated_punct_run` `15`, `punct_ratio` `16`, `rare_nonletter_char_rate` `5`, `symbol_ratio` `7`, `target_connector_ratio` `6`; min_full_clause mean `0.024162241650889142` n_below_1 `20` features `char_shannon_entropy` `9`, `letter_ratio` `7`, `max_repeated_punct_run` `15`, `punct_ratio` `16`, `rare_nonletter_char_rate` `5`, `symbol_ratio` `7`, `target_connector_ratio` `6`.
- `diagnostico_pasteleria_panaderia` `IN_DOMAIN_VALID` n `8` full_doc mean `1.0` n_below_1 `0` features `none`; min_full_clause mean `0.9367547842571509` n_below_1 `6` features `char_shannon_entropy` `3`, `foreign_connector_ratio` `1`, `letter_ratio` `3`, `symbol_ratio` `1`, `target_connector_ratio` `3`.
- `dilution_80_20` `HYBRID_BOUNDARY` n `10` full_doc mean `0.7783372923780758` n_below_1 `8` features `char_shannon_entropy` `2`, `punct_ratio` `1`, `rare_nonletter_char_rate` `6`, `symbol_ratio` `4`, `target_connector_ratio` `1`; min_full_clause mean `0.30187841129659954` n_below_1 `10` features `char_shannon_entropy` `5`, `foreign_connector_ratio` `2`, `letter_ratio` `2`, `punct_ratio` `1`, `rare_nonletter_char_rate` `7`, `symbol_ratio` `5`, `target_connector_ratio` `2`.
- `extreme_short_punct` `ADVERSARIAL_FUZZING` n `10` full_doc mean `5.614891346849248e-06` n_below_1 `10` features `char_shannon_entropy` `10`, `digit_ratio` `1`, `letter_ratio` `10`, `max_repeated_punct_run` `6`, `punct_ratio` `10`, `rare_nonletter_bigram_rate` `9`, `rare_nonletter_char_rate` `7`, `symbol_ratio` `3`; min_full_clause mean `5.59328641587905e-06` n_below_1 `10` features `char_shannon_entropy` `10`, `digit_ratio` `1`, `letter_ratio` `10`, `max_repeated_punct_run` `6`, `punct_ratio` `10`, `rare_nonletter_bigram_rate` `9`, `rare_nonletter_char_rate` `9`, `symbol_ratio` `3`.
- `homoglyph_zwsp_fullwidth` `ADVERSARIAL_FUZZING` n `12` full_doc mean `0.023747952634073626` n_below_1 `12` features `char_shannon_entropy` `1`, `foreign_connector_ratio` `3`, `letter_ratio` `5`, `max_repeated_punct_run` `4`, `non_latin_or_control_unicode_ratio` `12`, `punct_ratio` `5`, `rare_nonletter_bigram_rate` `1`, `rare_nonletter_char_rate` `6`, `symbol_ratio` `12`, `target_connector_ratio` `9`; min_full_clause mean `0.023747952634073626` n_below_1 `12` features `char_shannon_entropy` `1`, `foreign_connector_ratio` `3`, `letter_ratio` `5`, `max_repeated_punct_run` `4`, `non_latin_or_control_unicode_ratio` `12`, `punct_ratio` `5`, `rare_nonletter_bigram_rate` `1`, `rare_nonletter_char_rate` `6`, `symbol_ratio` `12`, `target_connector_ratio` `9`.
- `near_ood_neighbor` `HYBRID_BOUNDARY` n `12` full_doc mean `0.8730096561047865` n_below_1 `7` features `letter_ratio` `2`, `punct_ratio` `2`, `rare_nonletter_char_rate` `2`, `symbol_ratio` `2`; min_full_clause mean `0.8097494496691354` n_below_1 `9` features `char_shannon_entropy` `5`, `foreign_connector_ratio` `1`, `letter_ratio` `3`, `punct_ratio` `2`, `rare_nonletter_char_rate` `2`, `symbol_ratio` `2`.
- `panaderia_fermentacion` `IN_DOMAIN_VALID` n `10` full_doc mean `0.5553236913122764` n_below_1 `9` features `foreign_connector_ratio` `1`, `punct_ratio` `5`, `rare_nonletter_char_rate` `5`; min_full_clause mean `0.5039149200505284` n_below_1 `10` features `char_shannon_entropy` `3`, `foreign_connector_ratio` `1`, `letter_ratio` `3`, `punct_ratio` `6`, `rare_nonletter_char_rate` `5`, `symbol_ratio` `1`.
- `receta_completa` `IN_DOMAIN_VALID` n `10` full_doc mean `0.9951559522284821` n_below_1 `1` features `symbol_ratio` `1`; min_full_clause mean `0.9332966539612337` n_below_1 `5` features `char_shannon_entropy` `4`, `foreign_connector_ratio` `2`, `letter_ratio` `1`, `symbol_ratio` `2`, `target_connector_ratio` `1`.
- `salsas_emulsiones` `IN_DOMAIN_VALID` n `8` full_doc mean `0.5612106971026649` n_below_1 `7` features `letter_ratio` `1`, `punct_ratio` `2`, `rare_nonletter_char_rate` `4`, `symbol_ratio` `1`, `target_connector_ratio` `1`; min_full_clause mean `0.4984571763777811` n_below_1 `7` features `char_shannon_entropy` `3`, `letter_ratio` `2`, `punct_ratio` `2`, `rare_nonletter_char_rate` `4`, `symbol_ratio` `1`, `target_connector_ratio` `1`.
- `smuggle_recipe_footnote` `HYBRID_BOUNDARY` n `10` full_doc mean `0.10655450030333107` n_below_1 `9` features `char_shannon_entropy` `5`, `digit_ratio` `1`, `punct_ratio` `1`, `rare_nonletter_bigram_rate` `9`, `rare_nonletter_char_rate` `9`, `symbol_ratio` `2`, `target_connector_ratio` `1`; min_full_clause mean `0.10391163800745092` n_below_1 `9` features `char_shannon_entropy` `8`, `digit_ratio` `1`, `letter_ratio` `3`, `punct_ratio` `9`, `rare_nonletter_bigram_rate` `9`, `rare_nonletter_char_rate` `9`, `symbol_ratio` `3`, `target_connector_ratio` `1`.
- `sustitucion_ingredientes` `IN_DOMAIN_VALID` n `8` full_doc mean `0.19816987506111944` n_below_1 `8` features `punct_ratio` `1`, `rare_nonletter_char_rate` `8`, `symbol_ratio` `1`; min_full_clause mean `0.014264233908999256` n_below_1 `8` features `char_shannon_entropy` `1`, `punct_ratio` `1`, `rare_nonletter_char_rate` `8`, `symbol_ratio` `1`.
- `tecnica_culinaria` `IN_DOMAIN_VALID` n `10` full_doc mean `0.551495245911283` n_below_1 `8` features `punct_ratio` `5`, `rare_nonletter_char_rate` `5`, `symbol_ratio` `2`; min_full_clause mean `0.4996121921276638` n_below_1 `9` features `char_shannon_entropy` `4`, `punct_ratio` `5`, `rare_nonletter_char_rate` `5`, `symbol_ratio` `3`, `target_connector_ratio` `1`.
- `temperatura_tiempos` `IN_DOMAIN_VALID` n `6` full_doc mean `0.4299355219530636` n_below_1 `4` features `punct_ratio` `1`, `rare_nonletter_char_rate` `4`, `symbol_ratio` `1`; min_full_clause mean `0.339299718405166` n_below_1 `5` features `char_shannon_entropy` `4`, `punct_ratio` `1`, `rare_nonletter_char_rate` `4`, `symbol_ratio` `1`.
- `long_debugging_walkthrough` is absent from `struct_firing` on this cell.

## 5. w_f on smuggle_recipe_footnote and dilution_80_20

Each row is a stored `w_f_effect` entry at alpha 0 and beta 0. `smuggle_recipe_footnote` and `dilution_80_20` rates are the stored error rates. A null rate means the subtype has n 0 in that block. The roadmap's earlier 80% and 74% figures are not rewritten here; the rates below are the v3 literals.
### python / full_only / 1B_base_tech
| family | w_f | in-domain n | in-domain FRR | smuggle n | smuggle FAR | dilution n | dilution FAR |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `dir1024_sig_sep` | `null` | `100` | `0.21` | `0` | `null` | `10` | `0.5` |
| `dir1024_sig_sep2` | `null` | `100` | `0.21` | `0` | `null` | `10` | `0.6` |
| `dir1024_clip_polboost` | `null` | `100` | `0.2` | `0` | `null` | `10` | `0.5` |
| `polarity_v2_subset` | `null` | `100` | `0.19` | `0` | `null` | `10` | `0.7` |
| `base_repaired` | `null` | `100` | `0.24` | `0` | `null` | `10` | `0.8` |
| `f2_l2` | `null` | `100` | `0.5` | `0` | `null` | `10` | `0.9` |
| `tail_p3` | `null` | `100` | `0.28` | `0` | `null` | `10` | `0.8` |
| `tail_p5` | `null` | `100` | `0.29` | `0` | `null` | `10` | `0.9` |
| `tail_p10` | `null` | `100` | `0.28` | `0` | `null` | `10` | `0.9` |
| `tail_p25` | `null` | `100` | `0.4` | `0` | `null` | `10` | `0.9` |
### python / clauses / 1B_base_tech
| family | w_f | in-domain n | in-domain FRR | smuggle n | smuggle FAR | dilution n | dilution FAR |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `dir1024_sig_sep` | `0.2` | `100` | `0.1` | `0` | `null` | `10` | `0.0` |
| `dir1024_sig_sep` | `0.35` | `100` | `0.13` | `0` | `null` | `10` | `0.0` |
| `dir1024_sig_sep` | `0.5` | `100` | `0.18` | `0` | `null` | `10` | `0.0` |
| `dir1024_sig_sep` | `0.7` | `100` | `0.16` | `0` | `null` | `10` | `0.0` |
| `dir1024_sig_sep2` | `0.2` | `100` | `0.09` | `0` | `null` | `10` | `0.0` |
| `dir1024_sig_sep2` | `0.35` | `100` | `0.16` | `0` | `null` | `10` | `0.0` |
| `dir1024_sig_sep2` | `0.5` | `100` | `0.18` | `0` | `null` | `10` | `0.0` |
| `dir1024_sig_sep2` | `0.7` | `100` | `0.16` | `0` | `null` | `10` | `0.0` |
| `dir1024_clip_polboost` | `0.2` | `100` | `0.09` | `0` | `null` | `10` | `0.0` |
| `dir1024_clip_polboost` | `0.35` | `100` | `0.12` | `0` | `null` | `10` | `0.0` |
| `dir1024_clip_polboost` | `0.5` | `100` | `0.16` | `0` | `null` | `10` | `0.0` |
| `dir1024_clip_polboost` | `0.7` | `100` | `0.13` | `0` | `null` | `10` | `0.0` |
| `polarity_v2_subset` | `0.2` | `100` | `0.08` | `0` | `null` | `10` | `0.6` |
| `polarity_v2_subset` | `0.35` | `100` | `0.07` | `0` | `null` | `10` | `0.5` |
| `polarity_v2_subset` | `0.5` | `100` | `0.07` | `0` | `null` | `10` | `0.5` |
| `polarity_v2_subset` | `0.7` | `100` | `0.12` | `0` | `null` | `10` | `0.7` |
| `base_repaired` | `0.2` | `100` | `0.07` | `0` | `null` | `10` | `0.1` |
| `base_repaired` | `0.35` | `100` | `0.11` | `0` | `null` | `10` | `0.2` |
| `base_repaired` | `0.5` | `100` | `0.14` | `0` | `null` | `10` | `0.3` |
| `base_repaired` | `0.7` | `100` | `0.22` | `0` | `null` | `10` | `0.5` |
| `f2_l2` | `0.2` | `100` | `0.29` | `0` | `null` | `10` | `0.0` |
| `f2_l2` | `0.35` | `100` | `0.37` | `0` | `null` | `10` | `0.0` |
| `f2_l2` | `0.5` | `100` | `0.38` | `0` | `null` | `10` | `0.0` |
| `f2_l2` | `0.7` | `100` | `0.47` | `0` | `null` | `10` | `0.5` |
| `tail_p3` | `0.2` | `100` | `0.14` | `0` | `null` | `10` | `0.2` |
| `tail_p3` | `0.35` | `100` | `0.19` | `0` | `null` | `10` | `0.2` |
| `tail_p3` | `0.5` | `100` | `0.25` | `0` | `null` | `10` | `0.3` |
| `tail_p3` | `0.7` | `100` | `0.28` | `0` | `null` | `10` | `0.6` |
| `tail_p5` | `0.2` | `100` | `0.16` | `0` | `null` | `10` | `0.0` |
| `tail_p5` | `0.35` | `100` | `0.23` | `0` | `null` | `10` | `0.0` |
| `tail_p5` | `0.5` | `100` | `0.25` | `0` | `null` | `10` | `0.0` |
| `tail_p5` | `0.7` | `100` | `0.32` | `0` | `null` | `10` | `0.5` |
| `tail_p10` | `0.2` | `100` | `0.19` | `0` | `null` | `10` | `0.0` |
| `tail_p10` | `0.35` | `100` | `0.3` | `0` | `null` | `10` | `0.0` |
| `tail_p10` | `0.5` | `100` | `0.36` | `0` | `null` | `10` | `0.0` |
| `tail_p10` | `0.7` | `100` | `0.34` | `0` | `null` | `10` | `0.6` |
| `tail_p25` | `0.2` | `100` | `0.26` | `0` | `null` | `10` | `0.1` |
| `tail_p25` | `0.35` | `100` | `0.33` | `0` | `null` | `10` | `0.1` |
| `tail_p25` | `0.5` | `100` | `0.35` | `0` | `null` | `10` | `0.1` |
| `tail_p25` | `0.7` | `100` | `0.39` | `0` | `null` | `10` | `0.4` |
### python / full_only / 1B_base_tech_noise
| family | w_f | in-domain n | in-domain FRR | smuggle n | smuggle FAR | dilution n | dilution FAR |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `dir1024_sig_sep` | `null` | `100` | `0.21` | `0` | `null` | `10` | `0.7` |
| `dir1024_sig_sep2` | `null` | `100` | `0.21` | `0` | `null` | `10` | `0.9` |
| `dir1024_clip_polboost` | `null` | `100` | `0.21` | `0` | `null` | `10` | `0.8` |
| `polarity_v2_subset` | `null` | `100` | `0.17` | `0` | `null` | `10` | `0.8` |
| `base_repaired` | `null` | `100` | `0.26` | `0` | `null` | `10` | `0.8` |
| `f2_l2` | `null` | `100` | `0.5` | `0` | `null` | `10` | `0.9` |
| `tail_p3` | `null` | `100` | `0.28` | `0` | `null` | `10` | `0.8` |
| `tail_p5` | `null` | `100` | `0.29` | `0` | `null` | `10` | `0.9` |
| `tail_p10` | `null` | `100` | `0.28` | `0` | `null` | `10` | `0.9` |
| `tail_p25` | `null` | `100` | `0.4` | `0` | `null` | `10` | `0.9` |
### python / clauses / 1B_base_tech_noise
| family | w_f | in-domain n | in-domain FRR | smuggle n | smuggle FAR | dilution n | dilution FAR |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `dir1024_sig_sep` | `0.2` | `100` | `0.12` | `0` | `null` | `10` | `0.0` |
| `dir1024_sig_sep` | `0.35` | `100` | `0.15` | `0` | `null` | `10` | `0.0` |
| `dir1024_sig_sep` | `0.5` | `100` | `0.18` | `0` | `null` | `10` | `0.0` |
| `dir1024_sig_sep` | `0.7` | `100` | `0.2` | `0` | `null` | `10` | `0.1` |
| `dir1024_sig_sep2` | `0.2` | `100` | `0.11` | `0` | `null` | `10` | `0.0` |
| `dir1024_sig_sep2` | `0.35` | `100` | `0.16` | `0` | `null` | `10` | `0.0` |
| `dir1024_sig_sep2` | `0.5` | `100` | `0.19` | `0` | `null` | `10` | `0.0` |
| `dir1024_sig_sep2` | `0.7` | `100` | `0.19` | `0` | `null` | `10` | `0.1` |
| `dir1024_clip_polboost` | `0.2` | `100` | `0.11` | `0` | `null` | `10` | `0.0` |
| `dir1024_clip_polboost` | `0.35` | `100` | `0.14` | `0` | `null` | `10` | `0.0` |
| `dir1024_clip_polboost` | `0.5` | `100` | `0.17` | `0` | `null` | `10` | `0.0` |
| `dir1024_clip_polboost` | `0.7` | `100` | `0.19` | `0` | `null` | `10` | `0.1` |
| `polarity_v2_subset` | `0.2` | `100` | `0.07` | `0` | `null` | `10` | `0.5` |
| `polarity_v2_subset` | `0.35` | `100` | `0.06` | `0` | `null` | `10` | `0.5` |
| `polarity_v2_subset` | `0.5` | `100` | `0.13` | `0` | `null` | `10` | `0.6` |
| `polarity_v2_subset` | `0.7` | `100` | `0.14` | `0` | `null` | `10` | `0.6` |
| `base_repaired` | `0.2` | `100` | `0.07` | `0` | `null` | `10` | `0.1` |
| `base_repaired` | `0.35` | `100` | `0.1` | `0` | `null` | `10` | `0.2` |
| `base_repaired` | `0.5` | `100` | `0.15` | `0` | `null` | `10` | `0.3` |
| `base_repaired` | `0.7` | `100` | `0.25` | `0` | `null` | `10` | `0.5` |
| `f2_l2` | `0.2` | `100` | `0.29` | `0` | `null` | `10` | `0.0` |
| `f2_l2` | `0.35` | `100` | `0.37` | `0` | `null` | `10` | `0.0` |
| `f2_l2` | `0.5` | `100` | `0.38` | `0` | `null` | `10` | `0.0` |
| `f2_l2` | `0.7` | `100` | `0.47` | `0` | `null` | `10` | `0.5` |
| `tail_p3` | `0.2` | `100` | `0.14` | `0` | `null` | `10` | `0.2` |
| `tail_p3` | `0.35` | `100` | `0.19` | `0` | `null` | `10` | `0.2` |
| `tail_p3` | `0.5` | `100` | `0.25` | `0` | `null` | `10` | `0.3` |
| `tail_p3` | `0.7` | `100` | `0.28` | `0` | `null` | `10` | `0.6` |
| `tail_p5` | `0.2` | `100` | `0.16` | `0` | `null` | `10` | `0.0` |
| `tail_p5` | `0.35` | `100` | `0.23` | `0` | `null` | `10` | `0.0` |
| `tail_p5` | `0.5` | `100` | `0.25` | `0` | `null` | `10` | `0.0` |
| `tail_p5` | `0.7` | `100` | `0.32` | `0` | `null` | `10` | `0.5` |
| `tail_p10` | `0.2` | `100` | `0.19` | `0` | `null` | `10` | `0.0` |
| `tail_p10` | `0.35` | `100` | `0.3` | `0` | `null` | `10` | `0.0` |
| `tail_p10` | `0.5` | `100` | `0.36` | `0` | `null` | `10` | `0.0` |
| `tail_p10` | `0.7` | `100` | `0.34` | `0` | `null` | `10` | `0.6` |
| `tail_p25` | `0.2` | `100` | `0.26` | `0` | `null` | `10` | `0.1` |
| `tail_p25` | `0.35` | `100` | `0.33` | `0` | `null` | `10` | `0.1` |
| `tail_p25` | `0.5` | `100` | `0.35` | `0` | `null` | `10` | `0.1` |
| `tail_p25` | `0.7` | `100` | `0.39` | `0` | `null` | `10` | `0.4` |
### python / full_only / 1B_full
| family | w_f | in-domain n | in-domain FRR | smuggle n | smuggle FAR | dilution n | dilution FAR |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `dir1024_sig_sep` | `null` | `100` | `0.19` | `0` | `null` | `10` | `0.8` |
| `dir1024_sig_sep2` | `null` | `100` | `0.2` | `0` | `null` | `10` | `0.8` |
| `dir1024_clip_polboost` | `null` | `100` | `0.19` | `0` | `null` | `10` | `0.8` |
| `polarity_v2_subset` | `null` | `100` | `0.1` | `0` | `null` | `10` | `0.9` |
| `base_repaired` | `null` | `100` | `0.22` | `0` | `null` | `10` | `0.8` |
| `f2_l2` | `null` | `100` | `0.5` | `0` | `null` | `10` | `0.9` |
| `tail_p3` | `null` | `100` | `0.28` | `0` | `null` | `10` | `0.8` |
| `tail_p5` | `null` | `100` | `0.29` | `0` | `null` | `10` | `0.9` |
| `tail_p10` | `null` | `100` | `0.28` | `0` | `null` | `10` | `0.9` |
| `tail_p25` | `null` | `100` | `0.4` | `0` | `null` | `10` | `0.9` |
### python / clauses / 1B_full
| family | w_f | in-domain n | in-domain FRR | smuggle n | smuggle FAR | dilution n | dilution FAR |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `dir1024_sig_sep` | `0.2` | `100` | `0.1` | `0` | `null` | `10` | `0.0` |
| `dir1024_sig_sep` | `0.35` | `100` | `0.11` | `0` | `null` | `10` | `0.0` |
| `dir1024_sig_sep` | `0.5` | `100` | `0.12` | `0` | `null` | `10` | `0.0` |
| `dir1024_sig_sep` | `0.7` | `100` | `0.19` | `0` | `null` | `10` | `0.1` |
| `dir1024_sig_sep2` | `0.2` | `100` | `0.11` | `0` | `null` | `10` | `0.0` |
| `dir1024_sig_sep2` | `0.35` | `100` | `0.12` | `0` | `null` | `10` | `0.0` |
| `dir1024_sig_sep2` | `0.5` | `100` | `0.12` | `0` | `null` | `10` | `0.0` |
| `dir1024_sig_sep2` | `0.7` | `100` | `0.18` | `0` | `null` | `10` | `0.2` |
| `dir1024_clip_polboost` | `0.2` | `100` | `0.09` | `0` | `null` | `10` | `0.0` |
| `dir1024_clip_polboost` | `0.35` | `100` | `0.1` | `0` | `null` | `10` | `0.0` |
| `dir1024_clip_polboost` | `0.5` | `100` | `0.13` | `0` | `null` | `10` | `0.0` |
| `dir1024_clip_polboost` | `0.7` | `100` | `0.16` | `0` | `null` | `10` | `0.1` |
| `polarity_v2_subset` | `0.2` | `100` | `0.08` | `0` | `null` | `10` | `0.6` |
| `polarity_v2_subset` | `0.35` | `100` | `0.07` | `0` | `null` | `10` | `0.5` |
| `polarity_v2_subset` | `0.5` | `100` | `0.07` | `0` | `null` | `10` | `0.5` |
| `polarity_v2_subset` | `0.7` | `100` | `0.07` | `0` | `null` | `10` | `0.6` |
| `base_repaired` | `0.2` | `100` | `0.08` | `0` | `null` | `10` | `0.1` |
| `base_repaired` | `0.35` | `100` | `0.12` | `0` | `null` | `10` | `0.2` |
| `base_repaired` | `0.5` | `100` | `0.14` | `0` | `null` | `10` | `0.2` |
| `base_repaired` | `0.7` | `100` | `0.22` | `0` | `null` | `10` | `0.5` |
| `f2_l2` | `0.2` | `100` | `0.29` | `0` | `null` | `10` | `0.0` |
| `f2_l2` | `0.35` | `100` | `0.37` | `0` | `null` | `10` | `0.0` |
| `f2_l2` | `0.5` | `100` | `0.38` | `0` | `null` | `10` | `0.0` |
| `f2_l2` | `0.7` | `100` | `0.47` | `0` | `null` | `10` | `0.5` |
| `tail_p3` | `0.2` | `100` | `0.14` | `0` | `null` | `10` | `0.2` |
| `tail_p3` | `0.35` | `100` | `0.19` | `0` | `null` | `10` | `0.2` |
| `tail_p3` | `0.5` | `100` | `0.25` | `0` | `null` | `10` | `0.3` |
| `tail_p3` | `0.7` | `100` | `0.28` | `0` | `null` | `10` | `0.6` |
| `tail_p5` | `0.2` | `100` | `0.16` | `0` | `null` | `10` | `0.0` |
| `tail_p5` | `0.35` | `100` | `0.23` | `0` | `null` | `10` | `0.0` |
| `tail_p5` | `0.5` | `100` | `0.25` | `0` | `null` | `10` | `0.0` |
| `tail_p5` | `0.7` | `100` | `0.32` | `0` | `null` | `10` | `0.5` |
| `tail_p10` | `0.2` | `100` | `0.19` | `0` | `null` | `10` | `0.0` |
| `tail_p10` | `0.35` | `100` | `0.3` | `0` | `null` | `10` | `0.0` |
| `tail_p10` | `0.5` | `100` | `0.36` | `0` | `null` | `10` | `0.0` |
| `tail_p10` | `0.7` | `100` | `0.34` | `0` | `null` | `10` | `0.6` |
| `tail_p25` | `0.2` | `100` | `0.26` | `0` | `null` | `10` | `0.1` |
| `tail_p25` | `0.35` | `100` | `0.33` | `0` | `null` | `10` | `0.1` |
| `tail_p25` | `0.5` | `100` | `0.35` | `0` | `null` | `10` | `0.1` |
| `tail_p25` | `0.7` | `100` | `0.39` | `0` | `null` | `10` | `0.4` |
### python / full_only / 1B_full_v3
| family | w_f | in-domain n | in-domain FRR | smuggle n | smuggle FAR | dilution n | dilution FAR |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `dir1024_sig_sep` | `null` | `100` | `0.2` | `0` | `null` | `10` | `0.8` |
| `dir1024_sig_sep2` | `null` | `100` | `0.2` | `0` | `null` | `10` | `0.9` |
| `dir1024_clip_polboost` | `null` | `100` | `0.2` | `0` | `null` | `10` | `0.8` |
| `polarity_v2_subset` | `null` | `100` | `0.19` | `0` | `null` | `10` | `0.9` |
| `base_repaired` | `null` | `100` | `0.25` | `0` | `null` | `10` | `0.8` |
| `f2_l2` | `null` | `100` | `0.5` | `0` | `null` | `10` | `0.9` |
| `tail_p3` | `null` | `100` | `0.28` | `0` | `null` | `10` | `0.8` |
| `tail_p5` | `null` | `100` | `0.29` | `0` | `null` | `10` | `0.9` |
| `tail_p10` | `null` | `100` | `0.28` | `0` | `null` | `10` | `0.9` |
| `tail_p25` | `null` | `100` | `0.4` | `0` | `null` | `10` | `0.9` |
### python / clauses / 1B_full_v3
| family | w_f | in-domain n | in-domain FRR | smuggle n | smuggle FAR | dilution n | dilution FAR |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `dir1024_sig_sep` | `0.2` | `100` | `0.13` | `0` | `null` | `10` | `0.0` |
| `dir1024_sig_sep` | `0.35` | `100` | `0.14` | `0` | `null` | `10` | `0.0` |
| `dir1024_sig_sep` | `0.5` | `100` | `0.15` | `0` | `null` | `10` | `0.0` |
| `dir1024_sig_sep` | `0.7` | `100` | `0.18` | `0` | `null` | `10` | `0.2` |
| `dir1024_sig_sep2` | `0.2` | `100` | `0.13` | `0` | `null` | `10` | `0.0` |
| `dir1024_sig_sep2` | `0.35` | `100` | `0.13` | `0` | `null` | `10` | `0.0` |
| `dir1024_sig_sep2` | `0.5` | `100` | `0.18` | `0` | `null` | `10` | `0.0` |
| `dir1024_sig_sep2` | `0.7` | `100` | `0.19` | `0` | `null` | `10` | `0.3` |
| `dir1024_clip_polboost` | `0.2` | `100` | `0.13` | `0` | `null` | `10` | `0.0` |
| `dir1024_clip_polboost` | `0.35` | `100` | `0.12` | `0` | `null` | `10` | `0.0` |
| `dir1024_clip_polboost` | `0.5` | `100` | `0.15` | `0` | `null` | `10` | `0.0` |
| `dir1024_clip_polboost` | `0.7` | `100` | `0.17` | `0` | `null` | `10` | `0.3` |
| `polarity_v2_subset` | `0.2` | `100` | `0.08` | `0` | `null` | `10` | `0.5` |
| `polarity_v2_subset` | `0.35` | `100` | `0.09` | `0` | `null` | `10` | `0.4` |
| `polarity_v2_subset` | `0.5` | `100` | `0.1` | `0` | `null` | `10` | `0.4` |
| `polarity_v2_subset` | `0.7` | `100` | `0.13` | `0` | `null` | `10` | `0.5` |
| `base_repaired` | `0.2` | `100` | `0.08` | `0` | `null` | `10` | `0.1` |
| `base_repaired` | `0.35` | `100` | `0.1` | `0` | `null` | `10` | `0.2` |
| `base_repaired` | `0.5` | `100` | `0.15` | `0` | `null` | `10` | `0.3` |
| `base_repaired` | `0.7` | `100` | `0.23` | `0` | `null` | `10` | `0.5` |
| `f2_l2` | `0.2` | `100` | `0.29` | `0` | `null` | `10` | `0.0` |
| `f2_l2` | `0.35` | `100` | `0.37` | `0` | `null` | `10` | `0.0` |
| `f2_l2` | `0.5` | `100` | `0.38` | `0` | `null` | `10` | `0.0` |
| `f2_l2` | `0.7` | `100` | `0.47` | `0` | `null` | `10` | `0.5` |
| `tail_p3` | `0.2` | `100` | `0.14` | `0` | `null` | `10` | `0.2` |
| `tail_p3` | `0.35` | `100` | `0.19` | `0` | `null` | `10` | `0.2` |
| `tail_p3` | `0.5` | `100` | `0.25` | `0` | `null` | `10` | `0.3` |
| `tail_p3` | `0.7` | `100` | `0.28` | `0` | `null` | `10` | `0.6` |
| `tail_p5` | `0.2` | `100` | `0.16` | `0` | `null` | `10` | `0.0` |
| `tail_p5` | `0.35` | `100` | `0.23` | `0` | `null` | `10` | `0.0` |
| `tail_p5` | `0.5` | `100` | `0.25` | `0` | `null` | `10` | `0.0` |
| `tail_p5` | `0.7` | `100` | `0.32` | `0` | `null` | `10` | `0.5` |
| `tail_p10` | `0.2` | `100` | `0.19` | `0` | `null` | `10` | `0.0` |
| `tail_p10` | `0.35` | `100` | `0.3` | `0` | `null` | `10` | `0.0` |
| `tail_p10` | `0.5` | `100` | `0.36` | `0` | `null` | `10` | `0.0` |
| `tail_p10` | `0.7` | `100` | `0.34` | `0` | `null` | `10` | `0.6` |
| `tail_p25` | `0.2` | `100` | `0.26` | `0` | `null` | `10` | `0.1` |
| `tail_p25` | `0.35` | `100` | `0.33` | `0` | `null` | `10` | `0.1` |
| `tail_p25` | `0.5` | `100` | `0.35` | `0` | `null` | `10` | `0.1` |
| `tail_p25` | `0.7` | `100` | `0.39` | `0` | `null` | `10` | `0.4` |
### receta / full_only / 1B_base_tech
| family | w_f | in-domain n | in-domain FRR | smuggle n | smuggle FAR | dilution n | dilution FAR |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `dir1024_sig_sep` | `null` | `100` | `0.43` | `10` | `0.9` | `10` | `0.7` |
| `dir1024_sig_sep2` | `null` | `100` | `0.39` | `10` | `0.8` | `10` | `0.8` |
| `dir1024_clip_polboost` | `null` | `100` | `0.42` | `10` | `0.9` | `10` | `0.8` |
| `polarity_v2_subset` | `null` | `100` | `0.23` | `10` | `0.8` | `10` | `0.7` |
| `base_repaired` | `null` | `100` | `0.48` | `10` | `1.0` | `10` | `0.9` |
| `f2_l2` | `null` | `100` | `0.58` | `10` | `0.8` | `10` | `0.9` |
| `tail_p3` | `null` | `100` | `0.46` | `10` | `1.0` | `10` | `0.9` |
| `tail_p5` | `null` | `100` | `0.51` | `10` | `0.9` | `10` | `0.8` |
| `tail_p10` | `null` | `100` | `0.53` | `10` | `1.0` | `10` | `0.8` |
| `tail_p25` | `null` | `100` | `0.58` | `10` | `1.0` | `10` | `0.8` |
### receta / clauses / 1B_base_tech
| family | w_f | in-domain n | in-domain FRR | smuggle n | smuggle FAR | dilution n | dilution FAR |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `dir1024_sig_sep` | `0.2` | `100` | `0.17` | `10` | `0.2` | `10` | `0.0` |
| `dir1024_sig_sep` | `0.35` | `100` | `0.22` | `10` | `0.2` | `10` | `0.0` |
| `dir1024_sig_sep` | `0.5` | `100` | `0.28` | `10` | `0.3` | `10` | `0.0` |
| `dir1024_sig_sep` | `0.7` | `100` | `0.34` | `10` | `0.5` | `10` | `0.5` |
| `dir1024_sig_sep2` | `0.2` | `100` | `0.18` | `10` | `0.3` | `10` | `0.0` |
| `dir1024_sig_sep2` | `0.35` | `100` | `0.22` | `10` | `0.3` | `10` | `0.0` |
| `dir1024_sig_sep2` | `0.5` | `100` | `0.3` | `10` | `0.3` | `10` | `0.0` |
| `dir1024_sig_sep2` | `0.7` | `100` | `0.31` | `10` | `0.5` | `10` | `0.5` |
| `dir1024_clip_polboost` | `0.2` | `100` | `0.13` | `10` | `0.2` | `10` | `0.0` |
| `dir1024_clip_polboost` | `0.35` | `100` | `0.22` | `10` | `0.3` | `10` | `0.0` |
| `dir1024_clip_polboost` | `0.5` | `100` | `0.29` | `10` | `0.3` | `10` | `0.2` |
| `dir1024_clip_polboost` | `0.7` | `100` | `0.31` | `10` | `0.5` | `10` | `0.5` |
| `polarity_v2_subset` | `0.2` | `100` | `0.15` | `10` | `0.6` | `10` | `0.3` |
| `polarity_v2_subset` | `0.35` | `100` | `0.17` | `10` | `0.7` | `10` | `0.3` |
| `polarity_v2_subset` | `0.5` | `100` | `0.15` | `10` | `0.7` | `10` | `0.7` |
| `polarity_v2_subset` | `0.7` | `100` | `0.22` | `10` | `0.7` | `10` | `0.7` |
| `base_repaired` | `0.2` | `100` | `0.15` | `10` | `0.5` | `10` | `0.6` |
| `base_repaired` | `0.35` | `100` | `0.24` | `10` | `0.6` | `10` | `0.6` |
| `base_repaired` | `0.5` | `100` | `0.3` | `10` | `0.8` | `10` | `0.6` |
| `base_repaired` | `0.7` | `100` | `0.41` | `10` | `0.9` | `10` | `0.8` |
| `f2_l2` | `0.2` | `100` | `0.37` | `10` | `0.4` | `10` | `0.1` |
| `f2_l2` | `0.35` | `100` | `0.57` | `10` | `0.3` | `10` | `0.1` |
| `f2_l2` | `0.5` | `100` | `0.58` | `10` | `0.6` | `10` | `0.3` |
| `f2_l2` | `0.7` | `100` | `0.56` | `10` | `0.8` | `10` | `0.6` |
| `tail_p3` | `0.2` | `100` | `0.28` | `10` | `0.7` | `10` | `0.6` |
| `tail_p3` | `0.35` | `100` | `0.43` | `10` | `0.7` | `10` | `0.5` |
| `tail_p3` | `0.5` | `100` | `0.42` | `10` | `0.8` | `10` | `0.8` |
| `tail_p3` | `0.7` | `100` | `0.43` | `10` | `0.9` | `10` | `0.8` |
| `tail_p5` | `0.2` | `100` | `0.33` | `10` | `0.6` | `10` | `0.5` |
| `tail_p5` | `0.35` | `100` | `0.43` | `10` | `0.6` | `10` | `0.5` |
| `tail_p5` | `0.5` | `100` | `0.45` | `10` | `0.7` | `10` | `0.7` |
| `tail_p5` | `0.7` | `100` | `0.54` | `10` | `0.9` | `10` | `0.8` |
| `tail_p10` | `0.2` | `100` | `0.36` | `10` | `0.6` | `10` | `0.4` |
| `tail_p10` | `0.35` | `100` | `0.45` | `10` | `0.6` | `10` | `0.4` |
| `tail_p10` | `0.5` | `100` | `0.46` | `10` | `0.7` | `10` | `0.6` |
| `tail_p10` | `0.7` | `100` | `0.56` | `10` | `0.8` | `10` | `0.8` |
| `tail_p25` | `0.2` | `100` | `0.35` | `10` | `0.6` | `10` | `0.2` |
| `tail_p25` | `0.35` | `100` | `0.48` | `10` | `0.5` | `10` | `0.2` |
| `tail_p25` | `0.5` | `100` | `0.48` | `10` | `0.7` | `10` | `0.5` |
| `tail_p25` | `0.7` | `100` | `0.57` | `10` | `0.8` | `10` | `0.6` |
### receta / full_only / 1B_base_tech_noise
| family | w_f | in-domain n | in-domain FRR | smuggle n | smuggle FAR | dilution n | dilution FAR |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `dir1024_sig_sep` | `null` | `100` | `0.48` | `10` | `0.8` | `10` | `0.7` |
| `dir1024_sig_sep2` | `null` | `100` | `0.45` | `10` | `0.8` | `10` | `0.7` |
| `dir1024_clip_polboost` | `null` | `100` | `0.46` | `10` | `0.8` | `10` | `0.7` |
| `polarity_v2_subset` | `null` | `100` | `0.25` | `10` | `0.8` | `10` | `0.8` |
| `base_repaired` | `null` | `100` | `0.48` | `10` | `1.0` | `10` | `0.9` |
| `f2_l2` | `null` | `100` | `0.58` | `10` | `0.8` | `10` | `0.9` |
| `tail_p3` | `null` | `100` | `0.46` | `10` | `1.0` | `10` | `0.9` |
| `tail_p5` | `null` | `100` | `0.51` | `10` | `0.9` | `10` | `0.8` |
| `tail_p10` | `null` | `100` | `0.53` | `10` | `1.0` | `10` | `0.8` |
| `tail_p25` | `null` | `100` | `0.58` | `10` | `1.0` | `10` | `0.8` |
### receta / clauses / 1B_base_tech_noise
| family | w_f | in-domain n | in-domain FRR | smuggle n | smuggle FAR | dilution n | dilution FAR |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `dir1024_sig_sep` | `0.2` | `100` | `0.18` | `10` | `0.2` | `10` | `0.0` |
| `dir1024_sig_sep` | `0.35` | `100` | `0.24` | `10` | `0.2` | `10` | `0.0` |
| `dir1024_sig_sep` | `0.5` | `100` | `0.32` | `10` | `0.2` | `10` | `0.0` |
| `dir1024_sig_sep` | `0.7` | `100` | `0.37` | `10` | `0.4` | `10` | `0.5` |
| `dir1024_sig_sep2` | `0.2` | `100` | `0.18` | `10` | `0.2` | `10` | `0.1` |
| `dir1024_sig_sep2` | `0.35` | `100` | `0.26` | `10` | `0.2` | `10` | `0.0` |
| `dir1024_sig_sep2` | `0.5` | `100` | `0.34` | `10` | `0.2` | `10` | `0.0` |
| `dir1024_sig_sep2` | `0.7` | `100` | `0.36` | `10` | `0.4` | `10` | `0.5` |
| `dir1024_clip_polboost` | `0.2` | `100` | `0.19` | `10` | `0.2` | `10` | `0.1` |
| `dir1024_clip_polboost` | `0.35` | `100` | `0.24` | `10` | `0.2` | `10` | `0.0` |
| `dir1024_clip_polboost` | `0.5` | `100` | `0.33` | `10` | `0.2` | `10` | `0.2` |
| `dir1024_clip_polboost` | `0.7` | `100` | `0.39` | `10` | `0.4` | `10` | `0.5` |
| `polarity_v2_subset` | `0.2` | `100` | `0.15` | `10` | `0.6` | `10` | `0.2` |
| `polarity_v2_subset` | `0.35` | `100` | `0.18` | `10` | `0.6` | `10` | `0.2` |
| `polarity_v2_subset` | `0.5` | `100` | `0.18` | `10` | `0.7` | `10` | `0.5` |
| `polarity_v2_subset` | `0.7` | `100` | `0.23` | `10` | `0.7` | `10` | `0.7` |
| `base_repaired` | `0.2` | `100` | `0.15` | `10` | `0.6` | `10` | `0.5` |
| `base_repaired` | `0.35` | `100` | `0.21` | `10` | `0.6` | `10` | `0.6` |
| `base_repaired` | `0.5` | `100` | `0.35` | `10` | `0.7` | `10` | `0.7` |
| `base_repaired` | `0.7` | `100` | `0.45` | `10` | `0.9` | `10` | `0.8` |
| `f2_l2` | `0.2` | `100` | `0.37` | `10` | `0.4` | `10` | `0.1` |
| `f2_l2` | `0.35` | `100` | `0.57` | `10` | `0.3` | `10` | `0.1` |
| `f2_l2` | `0.5` | `100` | `0.58` | `10` | `0.6` | `10` | `0.3` |
| `f2_l2` | `0.7` | `100` | `0.56` | `10` | `0.8` | `10` | `0.6` |
| `tail_p3` | `0.2` | `100` | `0.28` | `10` | `0.7` | `10` | `0.6` |
| `tail_p3` | `0.35` | `100` | `0.43` | `10` | `0.7` | `10` | `0.5` |
| `tail_p3` | `0.5` | `100` | `0.42` | `10` | `0.8` | `10` | `0.8` |
| `tail_p3` | `0.7` | `100` | `0.43` | `10` | `0.9` | `10` | `0.8` |
| `tail_p5` | `0.2` | `100` | `0.33` | `10` | `0.6` | `10` | `0.5` |
| `tail_p5` | `0.35` | `100` | `0.43` | `10` | `0.6` | `10` | `0.5` |
| `tail_p5` | `0.5` | `100` | `0.45` | `10` | `0.7` | `10` | `0.7` |
| `tail_p5` | `0.7` | `100` | `0.54` | `10` | `0.9` | `10` | `0.8` |
| `tail_p10` | `0.2` | `100` | `0.36` | `10` | `0.6` | `10` | `0.4` |
| `tail_p10` | `0.35` | `100` | `0.45` | `10` | `0.6` | `10` | `0.4` |
| `tail_p10` | `0.5` | `100` | `0.46` | `10` | `0.7` | `10` | `0.6` |
| `tail_p10` | `0.7` | `100` | `0.56` | `10` | `0.8` | `10` | `0.8` |
| `tail_p25` | `0.2` | `100` | `0.35` | `10` | `0.6` | `10` | `0.2` |
| `tail_p25` | `0.35` | `100` | `0.48` | `10` | `0.5` | `10` | `0.2` |
| `tail_p25` | `0.5` | `100` | `0.48` | `10` | `0.7` | `10` | `0.5` |
| `tail_p25` | `0.7` | `100` | `0.57` | `10` | `0.8` | `10` | `0.6` |
### receta / full_only / 1B_full
| family | w_f | in-domain n | in-domain FRR | smuggle n | smuggle FAR | dilution n | dilution FAR |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `dir1024_sig_sep` | `null` | `100` | `0.46` | `10` | `0.9` | `10` | `0.8` |
| `dir1024_sig_sep2` | `null` | `100` | `0.45` | `10` | `0.9` | `10` | `0.7` |
| `dir1024_clip_polboost` | `null` | `100` | `0.44` | `10` | `0.9` | `10` | `0.7` |
| `polarity_v2_subset` | `null` | `100` | `0.29` | `10` | `0.8` | `10` | `0.7` |
| `base_repaired` | `null` | `100` | `0.48` | `10` | `1.0` | `10` | `0.9` |
| `f2_l2` | `null` | `100` | `0.58` | `10` | `0.8` | `10` | `0.9` |
| `tail_p3` | `null` | `100` | `0.46` | `10` | `1.0` | `10` | `0.9` |
| `tail_p5` | `null` | `100` | `0.51` | `10` | `0.9` | `10` | `0.8` |
| `tail_p10` | `null` | `100` | `0.53` | `10` | `1.0` | `10` | `0.8` |
| `tail_p25` | `null` | `100` | `0.58` | `10` | `1.0` | `10` | `0.8` |
### receta / clauses / 1B_full
| family | w_f | in-domain n | in-domain FRR | smuggle n | smuggle FAR | dilution n | dilution FAR |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `dir1024_sig_sep` | `0.2` | `100` | `0.17` | `10` | `0.2` | `10` | `0.0` |
| `dir1024_sig_sep` | `0.35` | `100` | `0.25` | `10` | `0.2` | `10` | `0.0` |
| `dir1024_sig_sep` | `0.5` | `100` | `0.32` | `10` | `0.2` | `10` | `0.0` |
| `dir1024_sig_sep` | `0.7` | `100` | `0.36` | `10` | `0.5` | `10` | `0.5` |
| `dir1024_sig_sep2` | `0.2` | `100` | `0.19` | `10` | `0.2` | `10` | `0.1` |
| `dir1024_sig_sep2` | `0.35` | `100` | `0.27` | `10` | `0.2` | `10` | `0.1` |
| `dir1024_sig_sep2` | `0.5` | `100` | `0.29` | `10` | `0.2` | `10` | `0.1` |
| `dir1024_sig_sep2` | `0.7` | `100` | `0.37` | `10` | `0.5` | `10` | `0.5` |
| `dir1024_clip_polboost` | `0.2` | `100` | `0.15` | `10` | `0.2` | `10` | `0.1` |
| `dir1024_clip_polboost` | `0.35` | `100` | `0.23` | `10` | `0.2` | `10` | `0.1` |
| `dir1024_clip_polboost` | `0.5` | `100` | `0.3` | `10` | `0.2` | `10` | `0.2` |
| `dir1024_clip_polboost` | `0.7` | `100` | `0.37` | `10` | `0.5` | `10` | `0.5` |
| `polarity_v2_subset` | `0.2` | `100` | `0.18` | `10` | `0.6` | `10` | `0.3` |
| `polarity_v2_subset` | `0.35` | `100` | `0.18` | `10` | `0.7` | `10` | `0.3` |
| `polarity_v2_subset` | `0.5` | `100` | `0.18` | `10` | `0.8` | `10` | `0.6` |
| `polarity_v2_subset` | `0.7` | `100` | `0.21` | `10` | `0.7` | `10` | `0.6` |
| `base_repaired` | `0.2` | `100` | `0.12` | `10` | `0.5` | `10` | `0.5` |
| `base_repaired` | `0.35` | `100` | `0.23` | `10` | `0.5` | `10` | `0.4` |
| `base_repaired` | `0.5` | `100` | `0.37` | `10` | `0.7` | `10` | `0.6` |
| `base_repaired` | `0.7` | `100` | `0.45` | `10` | `0.9` | `10` | `0.8` |
| `f2_l2` | `0.2` | `100` | `0.37` | `10` | `0.4` | `10` | `0.1` |
| `f2_l2` | `0.35` | `100` | `0.57` | `10` | `0.3` | `10` | `0.1` |
| `f2_l2` | `0.5` | `100` | `0.58` | `10` | `0.6` | `10` | `0.3` |
| `f2_l2` | `0.7` | `100` | `0.56` | `10` | `0.8` | `10` | `0.6` |
| `tail_p3` | `0.2` | `100` | `0.28` | `10` | `0.7` | `10` | `0.6` |
| `tail_p3` | `0.35` | `100` | `0.43` | `10` | `0.7` | `10` | `0.5` |
| `tail_p3` | `0.5` | `100` | `0.42` | `10` | `0.8` | `10` | `0.8` |
| `tail_p3` | `0.7` | `100` | `0.43` | `10` | `0.9` | `10` | `0.8` |
| `tail_p5` | `0.2` | `100` | `0.33` | `10` | `0.6` | `10` | `0.5` |
| `tail_p5` | `0.35` | `100` | `0.43` | `10` | `0.6` | `10` | `0.5` |
| `tail_p5` | `0.5` | `100` | `0.45` | `10` | `0.7` | `10` | `0.7` |
| `tail_p5` | `0.7` | `100` | `0.54` | `10` | `0.9` | `10` | `0.8` |
| `tail_p10` | `0.2` | `100` | `0.36` | `10` | `0.6` | `10` | `0.4` |
| `tail_p10` | `0.35` | `100` | `0.45` | `10` | `0.6` | `10` | `0.4` |
| `tail_p10` | `0.5` | `100` | `0.46` | `10` | `0.7` | `10` | `0.6` |
| `tail_p10` | `0.7` | `100` | `0.56` | `10` | `0.8` | `10` | `0.8` |
| `tail_p25` | `0.2` | `100` | `0.35` | `10` | `0.6` | `10` | `0.2` |
| `tail_p25` | `0.35` | `100` | `0.48` | `10` | `0.5` | `10` | `0.2` |
| `tail_p25` | `0.5` | `100` | `0.48` | `10` | `0.7` | `10` | `0.5` |
| `tail_p25` | `0.7` | `100` | `0.57` | `10` | `0.8` | `10` | `0.6` |
### receta / full_only / 1B_full_v3
| family | w_f | in-domain n | in-domain FRR | smuggle n | smuggle FAR | dilution n | dilution FAR |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `dir1024_sig_sep` | `null` | `100` | `0.48` | `10` | `0.9` | `10` | `0.8` |
| `dir1024_sig_sep2` | `null` | `100` | `0.46` | `10` | `0.8` | `10` | `0.7` |
| `dir1024_clip_polboost` | `null` | `100` | `0.47` | `10` | `0.8` | `10` | `0.7` |
| `polarity_v2_subset` | `null` | `100` | `0.28` | `10` | `0.9` | `10` | `0.8` |
| `base_repaired` | `null` | `100` | `0.48` | `10` | `1.0` | `10` | `0.9` |
| `f2_l2` | `null` | `100` | `0.58` | `10` | `0.8` | `10` | `0.9` |
| `tail_p3` | `null` | `100` | `0.46` | `10` | `1.0` | `10` | `0.9` |
| `tail_p5` | `null` | `100` | `0.51` | `10` | `0.9` | `10` | `0.8` |
| `tail_p10` | `null` | `100` | `0.53` | `10` | `1.0` | `10` | `0.8` |
| `tail_p25` | `null` | `100` | `0.58` | `10` | `1.0` | `10` | `0.8` |
### receta / clauses / 1B_full_v3
| family | w_f | in-domain n | in-domain FRR | smuggle n | smuggle FAR | dilution n | dilution FAR |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `dir1024_sig_sep` | `0.2` | `100` | `0.18` | `10` | `0.2` | `10` | `0.0` |
| `dir1024_sig_sep` | `0.35` | `100` | `0.25` | `10` | `0.2` | `10` | `0.0` |
| `dir1024_sig_sep` | `0.5` | `100` | `0.32` | `10` | `0.2` | `10` | `0.0` |
| `dir1024_sig_sep` | `0.7` | `100` | `0.48` | `10` | `0.3` | `10` | `0.4` |
| `dir1024_sig_sep2` | `0.2` | `100` | `0.18` | `10` | `0.2` | `10` | `0.1` |
| `dir1024_sig_sep2` | `0.35` | `100` | `0.27` | `10` | `0.2` | `10` | `0.1` |
| `dir1024_sig_sep2` | `0.5` | `100` | `0.34` | `10` | `0.2` | `10` | `0.1` |
| `dir1024_sig_sep2` | `0.7` | `100` | `0.38` | `10` | `0.3` | `10` | `0.5` |
| `dir1024_clip_polboost` | `0.2` | `100` | `0.16` | `10` | `0.2` | `10` | `0.1` |
| `dir1024_clip_polboost` | `0.35` | `100` | `0.25` | `10` | `0.2` | `10` | `0.0` |
| `dir1024_clip_polboost` | `0.5` | `100` | `0.32` | `10` | `0.2` | `10` | `0.1` |
| `dir1024_clip_polboost` | `0.7` | `100` | `0.41` | `10` | `0.3` | `10` | `0.5` |
| `polarity_v2_subset` | `0.2` | `100` | `0.18` | `10` | `0.6` | `10` | `0.3` |
| `polarity_v2_subset` | `0.35` | `100` | `0.2` | `10` | `0.7` | `10` | `0.3` |
| `polarity_v2_subset` | `0.5` | `100` | `0.2` | `10` | `0.6` | `10` | `0.4` |
| `polarity_v2_subset` | `0.7` | `100` | `0.23` | `10` | `0.7` | `10` | `0.7` |
| `base_repaired` | `0.2` | `100` | `0.13` | `10` | `0.4` | `10` | `0.4` |
| `base_repaired` | `0.35` | `100` | `0.25` | `10` | `0.6` | `10` | `0.4` |
| `base_repaired` | `0.5` | `100` | `0.29` | `10` | `0.7` | `10` | `0.6` |
| `base_repaired` | `0.7` | `100` | `0.43` | `10` | `0.9` | `10` | `0.9` |
| `f2_l2` | `0.2` | `100` | `0.37` | `10` | `0.4` | `10` | `0.1` |
| `f2_l2` | `0.35` | `100` | `0.57` | `10` | `0.3` | `10` | `0.1` |
| `f2_l2` | `0.5` | `100` | `0.58` | `10` | `0.6` | `10` | `0.3` |
| `f2_l2` | `0.7` | `100` | `0.56` | `10` | `0.8` | `10` | `0.6` |
| `tail_p3` | `0.2` | `100` | `0.28` | `10` | `0.7` | `10` | `0.6` |
| `tail_p3` | `0.35` | `100` | `0.43` | `10` | `0.7` | `10` | `0.5` |
| `tail_p3` | `0.5` | `100` | `0.42` | `10` | `0.8` | `10` | `0.8` |
| `tail_p3` | `0.7` | `100` | `0.43` | `10` | `0.9` | `10` | `0.8` |
| `tail_p5` | `0.2` | `100` | `0.33` | `10` | `0.6` | `10` | `0.5` |
| `tail_p5` | `0.35` | `100` | `0.43` | `10` | `0.6` | `10` | `0.5` |
| `tail_p5` | `0.5` | `100` | `0.45` | `10` | `0.7` | `10` | `0.7` |
| `tail_p5` | `0.7` | `100` | `0.54` | `10` | `0.9` | `10` | `0.8` |
| `tail_p10` | `0.2` | `100` | `0.36` | `10` | `0.6` | `10` | `0.4` |
| `tail_p10` | `0.35` | `100` | `0.45` | `10` | `0.6` | `10` | `0.4` |
| `tail_p10` | `0.5` | `100` | `0.46` | `10` | `0.7` | `10` | `0.6` |
| `tail_p10` | `0.7` | `100` | `0.56` | `10` | `0.8` | `10` | `0.8` |
| `tail_p25` | `0.2` | `100` | `0.35` | `10` | `0.6` | `10` | `0.2` |
| `tail_p25` | `0.35` | `100` | `0.48` | `10` | `0.5` | `10` | `0.2` |
| `tail_p25` | `0.5` | `100` | `0.48` | `10` | `0.7` | `10` | `0.5` |
| `tail_p25` | `0.7` | `100` | `0.57` | `10` | `0.8` | `10` | `0.6` |

## 6. Master tables

Document-level CAL_ONLY uses the calibration percentile only. The stored `holdout_labels_in_threshold` value is reported per cell. 5x5 figures are `secondary_repeated_oof_5x5`. Bootstrap intervals are `bootstrap.nested_selected`.
### python / full_only / 1B_base_tech
n_prompts `400`, n_calibration_bundles `600`, rule `document_level_CAL_ONLY`, holdout_labels_in_threshold `false`, selection `modal fold wins across 5 seeds x 5 nested folds; tie break is mean train F1 then lowest column`.
CAL_ONLY on the nested recipe:
| tag | F1 | FRR | FAR | precision | recall | threshold | ROC-AUC | tp | fn | tn | fp |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `p05` | `0.6910569105691057` | `0.15` | `0.20333333333333334` | `0.5821917808219178` | `0.85` | `0.5176736136795019` | `0.9179666666666666` | `85` | `15` | `239` | `61` |
| `p10` | `0.728110599078341` | `0.21` | `0.12666666666666668` | `0.6752136752136753` | `0.79` | `0.528430989982629` | `0.9179666666666666` | `79` | `21` | `262` | `38` |
| `p15` | `0.7307692307692307` | `0.24` | `0.10666666666666667` | `0.7037037037037037` | `0.76` | `0.5330101419143072` | `0.9179666666666666` | `76` | `24` | `268` | `32` |
nested 5x5:
| metric | mean | std |
| --- | --- | --- |
| `f1` | `0.7125885632538125` | `0.004458970520057445` |
| `frr` | `0.276` | `0.008944271909999166` |
| `far` | `0.10266666666666666` | `0.0036514837167011083` |
| `roc_auc` | `0.9153133333333333` | `0.0017279724792047158` |
| seed | F1 | FRR | FAR | ROC-AUC |
| --- | --- | --- | --- | --- |
| `0` | `0.7128712871287128` | `0.28` | `0.1` | `0.9139666666666667` |
| `1` | `0.7184466019417476` | `0.26` | `0.10666666666666667` | `0.9173666666666667` |
| `2` | `0.7058823529411765` | `0.28` | `0.10666666666666667` | `0.9163999999999999` |
| `3` | `0.7128712871287128` | `0.28` | `0.1` | `0.9156666666666666` |
| `4` | `0.7128712871287128` | `0.28` | `0.1` | `0.9131666666666666` |
modal recipe fixed 5x5:
| metric | mean | std |
| --- | --- | --- |
| `f1` | `0.7201737610948256` | `0.006118894789967026` |
| `frr` | `0.264` | `0.0054772255750516665` |
| `far` | `0.10266666666666666` | `0.004346134936801769` |
| `roc_auc` | `0.9179666666666666` | `0.0` |
| seed | F1 | FRR | FAR | ROC-AUC |
| --- | --- | --- | --- | --- |
| `0` | `0.7192118226600985` | `0.27` | `0.1` | `0.9179666666666666` |
| `1` | `0.7219512195121951` | `0.26` | `0.10333333333333333` | `0.9179666666666666` |
| `2` | `0.7121951219512195` | `0.27` | `0.10666666666666667` | `0.9179666666666666` |
| `3` | `0.7184466019417476` | `0.26` | `0.10666666666666667` | `0.9179666666666666` |
| `4` | `0.729064039408867` | `0.26` | `0.09666666666666666` | `0.9179666666666666` |
Bootstrap n `1000`, seed `0`, probability `0.1`, threshold_policy `resampled_calibration_percentile`, refits_thresholds `true`.
| metric | ci95 low | ci95 high |
| --- | --- | --- |
| `f1` | `0.6693863319386332` | `0.7762667907966484` |
| `frr` | `0.14` | `0.28` |
| `far` | `0.09666666666666666` | `0.17333333333333334` |
| `roc_auc` | `0.8957533333333334` | `0.9380683333333334` |
Paired bootstrap delta of the nested score against the frozen F1 literals:
| frozen key | point | ci95 low | ci95 high |
| --- | --- | --- | --- |
| `task012_f1` | `0.16112539225055508` | `0.10878633193863319` | `0.21566679079664844` |
| `task013_cal_p10_f1` | `0.08792257534914659` | `0.03558351503722467` | `0.14246397389523993` |
| `task013_repeated_f1` | `0.09396222478816815` | `0.04162316447624625` | `0.1485036233342615` |
### python / clauses / 1B_base_tech
n_prompts `400`, n_calibration_bundles `600`, rule `document_level_CAL_ONLY`, holdout_labels_in_threshold `false`, selection `modal fold wins across 5 seeds x 5 nested folds; tie break is mean train F1 then lowest column`.
CAL_ONLY on the nested recipe:
| tag | F1 | FRR | FAR | precision | recall | threshold | ROC-AUC | tp | fn | tn | fp |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `p05` | `0.7927927927927928` | `0.12` | `0.11333333333333333` | `0.7213114754098361` | `0.88` | `0.5016660345073295` | `0.9500333333333334` | `88` | `12` | `266` | `34` |
| `p10` | `0.8159203980099502` | `0.18` | `0.06333333333333334` | `0.8118811881188119` | `0.82` | `0.5088870486814978` | `0.9500333333333334` | `82` | `18` | `281` | `19` |
| `p15` | `0.7875647668393783` | `0.24` | `0.056666666666666664` | `0.8172043010752689` | `0.76` | `0.5125821465131917` | `0.9500333333333334` | `76` | `24` | `283` | `17` |
nested 5x5:
| metric | mean | std |
| --- | --- | --- |
| `f1` | `0.7804607956366759` | `0.006974253924474721` |
| `frr` | `0.168` | `0.013038404810405298` |
| `far` | `0.1` | `0.003333333333333334` |
| `roc_auc` | `0.9289466666666666` | `0.013258573745987089` |
| seed | F1 | FRR | FAR | ROC-AUC |
| --- | --- | --- | --- | --- |
| `0` | `0.7714285714285715` | `0.19` | `0.09666666666666666` | `0.9292` |
| `1` | `0.7850467289719626` | `0.16` | `0.1` | `0.9456666666666667` |
| `2` | `0.7887323943661971` | `0.16` | `0.09666666666666666` | `0.9147333333333333` |
| `3` | `0.7757009345794392` | `0.17` | `0.10333333333333333` | `0.9171333333333334` |
| `4` | `0.7813953488372093` | `0.16` | `0.10333333333333333` | `0.9380000000000001` |
modal recipe fixed 5x5:
| metric | mean | std |
| --- | --- | --- |
| `f1` | `0.8126406926406927` | `0.012390333381817055` |
| `frr` | `0.186` | `0.008944271909999153` |
| `far` | `0.06333333333333332` | `0.014907119849998597` |
| `roc_auc` | `0.9500333333333334` | `0.0` |
| seed | F1 | FRR | FAR | ROC-AUC |
| --- | --- | --- | --- | --- |
| `0` | `0.7904761904761904` | `0.17` | `0.09` | `0.9500333333333334` |
| `1` | `0.8181818181818182` | `0.19` | `0.056666666666666664` | `0.9500333333333334` |
| `2` | `0.8181818181818182` | `0.19` | `0.056666666666666664` | `0.9500333333333334` |
| `3` | `0.8181818181818182` | `0.19` | `0.056666666666666664` | `0.9500333333333334` |
| `4` | `0.8181818181818182` | `0.19` | `0.056666666666666664` | `0.9500333333333334` |
Bootstrap n `1000`, seed `0`, probability `0.1`, threshold_policy `resampled_calibration_percentile`, refits_thresholds `true`.
| metric | ci95 low | ci95 high |
| --- | --- | --- |
| `f1` | `0.7475728155339806` | `0.8531077211690363` |
| `frr` | `0.11` | `0.29` |
| `far` | `0.04` | `0.1` |
| `roc_auc` | `0.930965` | `0.9668341666666667` |
Paired bootstrap delta of the nested score against the frozen F1 literals:
| frozen key | point | ci95 low | ci95 high |
| --- | --- | --- | --- |
| `task012_f1` | `0.13198936329362385` | `0.07527281553398057` | `0.18080772116903635` |
| `task013_cal_p10_f1` | `0.13280921888929173` | `0.07609267112964846` | `0.18162757676470423` |
| `task013_repeated_f1` | `0.11202415334683577` | `0.0553076055871925` | `0.16084251122224827` |
### python / full_only / 1B_base_tech_noise
n_prompts `400`, n_calibration_bundles `600`, rule `document_level_CAL_ONLY`, holdout_labels_in_threshold `false`, selection `modal fold wins across 5 seeds x 5 nested folds; tie break is mean train F1 then lowest column`.
CAL_ONLY on the nested recipe:
| tag | F1 | FRR | FAR | precision | recall | threshold | ROC-AUC | tp | fn | tn | fp |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `p05` | `0.6538461538461539` | `0.15` | `0.25` | `0.53125` | `0.85` | `0.5090838982602569` | `0.9050666666666667` | `85` | `15` | `225` | `75` |
| `p10` | `0.6991150442477876` | `0.21` | `0.15666666666666668` | `0.626984126984127` | `0.79` | `0.5214030284199227` | `0.9050666666666667` | `79` | `21` | `253` | `47` |
| `p15` | `0.7169811320754716` | `0.24` | `0.12` | `0.6785714285714286` | `0.76` | `0.5285838207574433` | `0.9050666666666667` | `76` | `24` | `264` | `36` |
nested 5x5:
| metric | mean | std |
| --- | --- | --- |
| `f1` | `0.6981847084656871` | `0.010828163080099068` |
| `frr` | `0.29000000000000004` | `0.012247448713915879` |
| `far` | `0.10800000000000001` | `0.009006170724070861` |
| `roc_auc` | `0.9030466666666666` | `0.0035914713790683016` |
| seed | F1 | FRR | FAR | ROC-AUC |
| --- | --- | --- | --- | --- |
| `0` | `0.7024390243902439` | `0.28` | `0.11` | `0.9049` |
| `1` | `0.7135678391959799` | `0.29` | `0.09333333333333334` | `0.9037` |
| `2` | `0.6893203883495146` | `0.29` | `0.11666666666666667` | `0.9041666666666666` |
| `3` | `0.6865671641791045` | `0.31` | `0.10666666666666667` | `0.8967666666666666` |
| `4` | `0.6990291262135923` | `0.28` | `0.11333333333333333` | `0.9057` |
modal recipe fixed 5x5:
| metric | mean | std |
| --- | --- | --- |
| `f1` | `0.7121344261406677` | `0.011236606847894412` |
| `frr` | `0.278` | `0.004472135954999583` |
| `far` | `0.10200000000000001` | `0.009006170724070861` |
| `roc_auc` | `0.9050666666666667` | `0.0` |
| seed | F1 | FRR | FAR | ROC-AUC |
| --- | --- | --- | --- | --- |
| `0` | `0.7024390243902439` | `0.28` | `0.11` | `0.9050666666666667` |
| `1` | `0.7263681592039801` | `0.27` | `0.09333333333333334` | `0.9050666666666667` |
| `2` | `0.7164179104477612` | `0.28` | `0.09666666666666666` | `0.9050666666666667` |
| `3` | `0.7164179104477612` | `0.28` | `0.09666666666666666` | `0.9050666666666667` |
| `4` | `0.6990291262135923` | `0.28` | `0.11333333333333333` | `0.9050666666666667` |
Bootstrap n `1000`, seed `0`, probability `0.1`, threshold_policy `resampled_calibration_percentile`, refits_thresholds `true`.
| metric | ci95 low | ci95 high |
| --- | --- | --- |
| `f1` | `0.6416506410256411` | `0.7488869863013699` |
| `frr` | `0.14` | `0.28` |
| `far` | `0.12` | `0.20666666666666667` |
| `roc_auc` | `0.8822991666666666` | `0.9259016666666666` |
Paired bootstrap delta of the nested score against the frozen F1 literals:
| frozen key | point | ci95 low | ci95 high |
| --- | --- | --- | --- |
| `task012_f1` | `0.13412091171037333` | `0.0810506410256411` | `0.1882869863013698` |
| `task013_cal_p10_f1` | `0.06091809480896483` | `0.007847824124232584` | `0.1150841693999613` |
| `task013_repeated_f1` | `0.0669577442479864` | `0.013887473563254161` | `0.12112381883898288` |
### python / clauses / 1B_base_tech_noise
n_prompts `400`, n_calibration_bundles `600`, rule `document_level_CAL_ONLY`, holdout_labels_in_threshold `false`, selection `modal fold wins across 5 seeds x 5 nested folds; tie break is mean train F1 then lowest column`.
CAL_ONLY on the nested recipe:
| tag | F1 | FRR | FAR | precision | recall | threshold | ROC-AUC | tp | fn | tn | fp |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `p05` | `0.7811158798283262` | `0.09` | `0.14` | `0.6842105263157895` | `0.91` | `0.47313529402946847` | `0.9477` | `91` | `9` | `258` | `42` |
| `p10` | `0.8118811881188119` | `0.18` | `0.06666666666666667` | `0.803921568627451` | `0.82` | `0.48630477798685595` | `0.9477` | `82` | `18` | `280` | `20` |
| `p15` | `0.7875647668393783` | `0.24` | `0.056666666666666664` | `0.8172043010752689` | `0.76` | `0.49426539786560836` | `0.9477` | `76` | `24` | `283` | `17` |
nested 5x5:
| metric | mean | std |
| --- | --- | --- |
| `f1` | `0.7648457678409377` | `0.014797125814703481` |
| `frr` | `0.2` | `0.023452078799117145` |
| `far` | `0.09733333333333334` | `0.011879019787470307` |
| `roc_auc` | `0.94178` | `0.003504647707766889` |
| seed | F1 | FRR | FAR | ROC-AUC |
| --- | --- | --- | --- | --- |
| `0` | `0.7536231884057971` | `0.22` | `0.09666666666666666` | `0.9377333333333334` |
| `1` | `0.780952380952381` | `0.18` | `0.09333333333333334` | `0.9442333333333334` |
| `2` | `0.772093023255814` | `0.17` | `0.10666666666666667` | `0.9392333333333334` |
| `3` | `0.7452830188679245` | `0.21` | `0.11` | `0.9462666666666668` |
| `4` | `0.7722772277227723` | `0.22` | `0.08` | `0.9414333333333333` |
modal recipe fixed 5x5:
| metric | mean | std |
| --- | --- | --- |
| `f1` | `0.8092415896124336` | `0.008809086486086448` |
| `frr` | `0.164` | `0.015165750888103104` |
| `far` | `0.07666666666666666` | `0.0` |
| `roc_auc` | `0.9477` | `0.0` |
| seed | F1 | FRR | FAR | ROC-AUC |
| --- | --- | --- | --- | --- |
| `0` | `0.8115942028985508` | `0.16` | `0.07666666666666666` | `0.9477` |
| `1` | `0.8173076923076923` | `0.15` | `0.07666666666666666` | `0.9477` |
| `2` | `0.8115942028985508` | `0.16` | `0.07666666666666666` | `0.9477` |
| `3` | `0.8115942028985508` | `0.16` | `0.07666666666666666` | `0.9477` |
| `4` | `0.7941176470588235` | `0.19` | `0.07666666666666666` | `0.9477` |
Bootstrap n `1000`, seed `0`, probability `0.1`, threshold_policy `resampled_calibration_percentile`, refits_thresholds `true`.
| metric | ci95 low | ci95 high |
| --- | --- | --- |
| `f1` | `0.7575482807348092` | `0.8558035714285713` |
| `frr` | `0.1` | `0.26` |
| `far` | `0.04666666666666667` | `0.09666666666666666` |
| `roc_auc` | `0.928865` | `0.9644008333333334` |
Paired bootstrap delta of the nested score against the frozen F1 literals:
| frozen key | point | ci95 low | ci95 high |
| --- | --- | --- | --- |
| `task012_f1` | `0.1359486314023063` | `0.08524828073480922` | `0.18350357142857135` |
| `task013_cal_p10_f1` | `0.1367684869979742` | `0.08606813633047711` | `0.18432342702423923` |
| `task013_repeated_f1` | `0.11598342145551822` | `0.06528307078802115` | `0.16353836148178327` |
### python / full_only / 1B_full
n_prompts `400`, n_calibration_bundles `600`, rule `document_level_CAL_ONLY`, holdout_labels_in_threshold `false`, selection `modal fold wins across 5 seeds x 5 nested folds; tie break is mean train F1 then lowest column`.
CAL_ONLY on the nested recipe:
| tag | F1 | FRR | FAR | precision | recall | threshold | ROC-AUC | tp | fn | tn | fp |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `p05` | `0.6640625` | `0.15` | `0.23666666666666666` | `0.5448717948717948` | `0.85` | `0.4997452665472717` | `0.909` | `85` | `15` | `229` | `71` |
| `p10` | `0.6956521739130435` | `0.2` | `0.16666666666666666` | `0.6153846153846154` | `0.8` | `0.5091549860954211` | `0.909` | `80` | `20` | `250` | `50` |
| `p15` | `0.7136150234741784` | `0.24` | `0.12333333333333334` | `0.672566371681416` | `0.76` | `0.5169164027712564` | `0.909` | `76` | `24` | `263` | `37` |
nested 5x5:
| metric | mean | std |
| --- | --- | --- |
| `f1` | `0.7210721319540588` | `0.01229710364155884` |
| `frr` | `0.256` | `0.008944271909999166` |
| `far` | `0.10666666666666666` | `0.01178511301977579` |
| `roc_auc` | `0.9062866666666665` | `0.0015688991186320609` |
| seed | F1 | FRR | FAR | ROC-AUC |
| --- | --- | --- | --- | --- |
| `0` | `0.7109004739336493` | `0.25` | `0.12` | `0.9042333333333332` |
| `1` | `0.7246376811594203` | `0.25` | `0.10666666666666667` | `0.9068666666666666` |
| `2` | `0.7389162561576355` | `0.25` | `0.09333333333333334` | `0.9080333333333332` |
| `3` | `0.7227722772277227` | `0.27` | `0.09666666666666666` | `0.9072` |
| `4` | `0.7081339712918661` | `0.26` | `0.11666666666666667` | `0.9051` |
modal recipe fixed 5x5:
| metric | mean | std |
| --- | --- | --- |
| `f1` | `0.7376676583914549` | `0.0027919494817341185` |
| `frr` | `0.252` | `0.004472135954999584` |
| `far` | `0.09333333333333334` | `0.0` |
| `roc_auc` | `0.909` | `0.0` |
| seed | F1 | FRR | FAR | ROC-AUC |
| --- | --- | --- | --- | --- |
| `0` | `0.7389162561576355` | `0.25` | `0.09333333333333334` | `0.909` |
| `1` | `0.7389162561576355` | `0.25` | `0.09333333333333334` | `0.909` |
| `2` | `0.7389162561576355` | `0.25` | `0.09333333333333334` | `0.909` |
| `3` | `0.7389162561576355` | `0.25` | `0.09333333333333334` | `0.909` |
| `4` | `0.7326732673267327` | `0.26` | `0.09333333333333334` | `0.909` |
Bootstrap n `1000`, seed `0`, probability `0.1`, threshold_policy `resampled_calibration_percentile`, refits_thresholds `true`.
| metric | ci95 low | ci95 high |
| --- | --- | --- |
| `f1` | `0.6443370984251262` | `0.7477477477477478` |
| `frr` | `0.14` | `0.28` |
| `far` | `0.12` | `0.21` |
| `roc_auc` | `0.8872633333333333` | `0.9294683333333333` |
Paired bootstrap delta of the nested score against the frozen F1 literals:
| frozen key | point | ci95 low | ci95 high |
| --- | --- | --- | --- |
| `task012_f1` | `0.13530502050766358` | `0.08373709842512618` | `0.18714774774774778` |
| `task013_cal_p10_f1` | `0.06210220360625508` | `0.010534281523717673` | `0.11394493084633928` |
| `task013_repeated_f1` | `0.06814185304527666` | `0.01657393096273925` | `0.11998458028536085` |
### python / clauses / 1B_full
n_prompts `400`, n_calibration_bundles `600`, rule `document_level_CAL_ONLY`, holdout_labels_in_threshold `false`, selection `modal fold wins across 5 seeds x 5 nested folds; tie break is mean train F1 then lowest column`.
CAL_ONLY on the nested recipe:
| tag | F1 | FRR | FAR | precision | recall | threshold | ROC-AUC | tp | fn | tn | fp |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `p05` | `0.768595041322314` | `0.07` | `0.16333333333333333` | `0.6549295774647887` | `0.93` | `0.4507378572442141` | `0.9428666666666666` | `93` | `7` | `251` | `49` |
| `p10` | `0.8133971291866029` | `0.15` | `0.08` | `0.7798165137614679` | `0.85` | `0.460990544250629` | `0.9428666666666666` | `85` | `15` | `276` | `24` |
| `p15` | `0.7653061224489796` | `0.25` | `0.07` | `0.78125` | `0.75` | `0.4662717593078252` | `0.9428666666666666` | `75` | `25` | `279` | `21` |
nested 5x5:
| metric | mean | std |
| --- | --- | --- |
| `f1` | `0.7619373229937537` | `0.007362726152493284` |
| `frr` | `0.184` | `0.005477225575051666` |
| `far` | `0.10866666666666666` | `0.005577733510227166` |
| `roc_auc` | `0.9211200000000002` | `0.008577153114848518` |
| seed | F1 | FRR | FAR | ROC-AUC |
| --- | --- | --- | --- | --- |
| `0` | `0.7627906976744186` | `0.18` | `0.11` | `0.9131` |
| `1` | `0.7735849056603774` | `0.18` | `0.1` | `0.9289` |
| `2` | `0.7534883720930232` | `0.19` | `0.11333333333333333` | `0.9123666666666667` |
| `3` | `0.7592592592592593` | `0.18` | `0.11333333333333333` | `0.9307333333333334` |
| `4` | `0.7605633802816901` | `0.19` | `0.10666666666666667` | `0.9205000000000001` |
modal recipe fixed 5x5:
| metric | mean | std |
| --- | --- | --- |
| `f1` | `0.8064420234575123` | `0.002843663848948536` |
| `frr` | `0.15` | `0.007071067811865472` |
| `far` | `0.086` | `0.0014907119849998634` |
| `roc_auc` | `0.9428666666666666` | `0.0` |
| seed | F1 | FRR | FAR | ROC-AUC |
| --- | --- | --- | --- | --- |
| `0` | `0.8056872037914692` | `0.15` | `0.08666666666666667` | `0.9428666666666666` |
| `1` | `0.8056872037914692` | `0.15` | `0.08666666666666667` | `0.9428666666666666` |
| `2` | `0.8038277511961722` | `0.16` | `0.08333333333333333` | `0.9428666666666666` |
| `3` | `0.8056872037914692` | `0.15` | `0.08666666666666667` | `0.9428666666666666` |
| `4` | `0.8113207547169812` | `0.14` | `0.08666666666666667` | `0.9428666666666666` |
Bootstrap n `1000`, seed `0`, probability `0.1`, threshold_policy `resampled_calibration_percentile`, refits_thresholds `true`.
| metric | ci95 low | ci95 high |
| --- | --- | --- |
| `f1` | `0.7464079125901593` | `0.8516790714159135` |
| `frr` | `0.09` | `0.25024999999999975` |
| `far` | `0.056666666666666664` | `0.11666666666666667` |
| `roc_auc` | `0.9235316666666666` | `0.9601033333333334` |
Paired bootstrap delta of the nested score against the frozen F1 literals:
| frozen key | point | ci95 low | ci95 high |
| --- | --- | --- | --- |
| `task012_f1` | `0.1283784944307621` | `0.07410791259015925` | `0.1793790714159135` |
| `task013_cal_p10_f1` | `0.12919835002643` | `0.07492776818582714` | `0.18019892701158138` |
| `task013_repeated_f1` | `0.10841328448397403` | `0.05414270264337118` | `0.15941386146912542` |
### python / full_only / 1B_full_v3
n_prompts `400`, n_calibration_bundles `600`, rule `document_level_CAL_ONLY`, holdout_labels_in_threshold `false`, selection `modal fold wins across 5 seeds x 5 nested folds; tie break is mean train F1 then lowest column`.
CAL_ONLY on the nested recipe:
| tag | F1 | FRR | FAR | precision | recall | threshold | ROC-AUC | tp | fn | tn | fp |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `p05` | `0.6439393939393939` | `0.15` | `0.2633333333333333` | `0.5182926829268293` | `0.85` | `0.5030516411429602` | `0.9038333333333333` | `85` | `15` | `221` | `79` |
| `p10` | `0.6583333333333333` | `0.21` | `0.20333333333333334` | `0.5642857142857143` | `0.79` | `0.5130931009481453` | `0.9038333333333333` | `79` | `21` | `239` | `61` |
| `p15` | `0.7123287671232876` | `0.22` | `0.13666666666666666` | `0.6554621848739496` | `0.78` | `0.5213623014871123` | `0.9038333333333333` | `78` | `22` | `259` | `41` |
nested 5x5:
| metric | mean | std |
| --- | --- | --- |
| `f1` | `0.6883696601962811` | `0.009839488996404246` |
| `frr` | `0.26` | `0.014142135623730963` |
| `far` | `0.13666666666666666` | `0.006666666666666668` |
| `roc_auc` | `0.89908` | `0.0038659913203328423` |
| seed | F1 | FRR | FAR | ROC-AUC |
| --- | --- | --- | --- | --- |
| `0` | `0.6981132075471698` | `0.26` | `0.12666666666666668` | `0.9029666666666667` |
| `1` | `0.6940639269406392` | `0.24` | `0.14333333333333334` | `0.8992666666666667` |
| `2` | `0.6728971962616822` | `0.28` | `0.14` | `0.8934333333333333` |
| `3` | `0.6851851851851852` | `0.26` | `0.14` | `0.8974666666666666` |
| `4` | `0.6915887850467289` | `0.26` | `0.13333333333333333` | `0.9022666666666666` |
modal recipe fixed 5x5:
| metric | mean | std |
| --- | --- | --- |
| `f1` | `0.7053481706750656` | `0.003772436344616783` |
| `frr` | `0.246` | `0.0054772255750516665` |
| `far` | `0.128` | `0.005055250296034368` |
| `roc_auc` | `0.9038333333333333` | `0.0` |
| seed | F1 | FRR | FAR | ROC-AUC |
| --- | --- | --- | --- | --- |
| `0` | `0.7109004739336493` | `0.25` | `0.12` | `0.9038333333333333` |
| `1` | `0.7037037037037037` | `0.24` | `0.13333333333333333` | `0.9038333333333333` |
| `2` | `0.7069767441860465` | `0.24` | `0.13` | `0.9038333333333333` |
| `3` | `0.704225352112676` | `0.25` | `0.12666666666666668` | `0.9038333333333333` |
| `4` | `0.7009345794392523` | `0.25` | `0.13` | `0.9038333333333333` |
Bootstrap n `1000`, seed `0`, probability `0.1`, threshold_policy `resampled_calibration_percentile`, refits_thresholds `true`.
| metric | ci95 low | ci95 high |
| --- | --- | --- |
| `f1` | `0.614689294768976` | `0.7272936740678676` |
| `frr` | `0.14` | `0.28` |
| `far` | `0.13666666666666666` | `0.24` |
| `roc_auc` | `0.8828633333333333` | `0.9233025` |
Paired bootstrap delta of the nested score against the frozen F1 literals:
| frozen key | point | ci95 low | ci95 high |
| --- | --- | --- | --- |
| `task012_f1` | `0.10686252678896835` | `0.054089294768976004` | `0.16669367406786764` |
| `task013_cal_p10_f1` | `0.03365970988755985` | `-0.019113522132432503` | `0.09349085716645912` |
| `task013_repeated_f1` | `0.03969935932658143` | `-0.013073872693410924` | `0.0995305066054807` |
### python / clauses / 1B_full_v3
n_prompts `400`, n_calibration_bundles `600`, rule `document_level_CAL_ONLY`, holdout_labels_in_threshold `false`, selection `modal fold wins across 5 seeds x 5 nested folds; tie break is mean train F1 then lowest column`.
CAL_ONLY on the nested recipe:
| tag | F1 | FRR | FAR | precision | recall | threshold | ROC-AUC | tp | fn | tn | fp |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `p05` | `0.757201646090535` | `0.08` | `0.17` | `0.6433566433566433` | `0.92` | `0.46202110440230465` | `0.9444666666666667` | `92` | `8` | `249` | `51` |
| `p10` | `0.7941176470588235` | `0.19` | `0.07666666666666666` | `0.7788461538461539` | `0.81` | `0.47393899320687977` | `0.9444666666666667` | `81` | `19` | `277` | `23` |
| `p15` | `0.7604166666666666` | `0.27` | `0.06333333333333334` | `0.7934782608695652` | `0.73` | `0.47995660385592204` | `0.9444666666666667` | `73` | `27` | `281` | `19` |
nested 5x5:
| metric | mean | std |
| --- | --- | --- |
| `f1` | `0.7920621458570938` | `0.011215522604976116` |
| `frr` | `0.15400000000000003` | `0.019493588689617935` |
| `far` | `0.09666666666666666` | `0.0023570226039551587` |
| `roc_auc` | `0.9361733333333333` | `0.003259720506082986` |
| seed | F1 | FRR | FAR | ROC-AUC |
| --- | --- | --- | --- | --- |
| `0` | `0.7887323943661971` | `0.16` | `0.09666666666666666` | `0.9391666666666667` |
| `1` | `0.8110599078341014` | `0.12` | `0.09666666666666666` | `0.9374666666666667` |
| `2` | `0.7830188679245284` | `0.17` | `0.09666666666666666` | `0.9317` |
| `3` | `0.7850467289719626` | `0.16` | `0.1` | `0.9338333333333333` |
| `4` | `0.7924528301886793` | `0.16` | `0.09333333333333334` | `0.9387` |
modal recipe fixed 5x5:
| metric | mean | std |
| --- | --- | --- |
| `f1` | `0.8279069767441861` | `1.2412670766236366e-16` |
| `frr` | `0.11000000000000001` | `1.5515838457795457e-17` |
| `far` | `0.08666666666666667` | `0.0` |
| `roc_auc` | `0.9444666666666667` | `0.0` |
| seed | F1 | FRR | FAR | ROC-AUC |
| --- | --- | --- | --- | --- |
| `0` | `0.827906976744186` | `0.11` | `0.08666666666666667` | `0.9444666666666667` |
| `1` | `0.827906976744186` | `0.11` | `0.08666666666666667` | `0.9444666666666667` |
| `2` | `0.827906976744186` | `0.11` | `0.08666666666666667` | `0.9444666666666667` |
| `3` | `0.827906976744186` | `0.11` | `0.08666666666666667` | `0.9444666666666667` |
| `4` | `0.827906976744186` | `0.11` | `0.08666666666666667` | `0.9444666666666667` |
Bootstrap n `1000`, seed `0`, probability `0.1`, threshold_policy `resampled_calibration_percentile`, refits_thresholds `true`.
| metric | ci95 low | ci95 high |
| --- | --- | --- |
| `f1` | `0.7437185929648241` | `0.845771144278607` |
| `frr` | `0.07975000000000002` | `0.27` |
| `far` | `0.05333333333333334` | `0.12666666666666668` |
| `roc_auc` | `0.925365` | `0.9613341666666667` |
Paired bootstrap delta of the nested score against the frozen F1 literals:
| frozen key | point | ci95 low | ci95 high |
| --- | --- | --- | --- |
| `task012_f1` | `0.12409423791211772` | `0.07141859296482411` | `0.173471144278607` |
| `task013_cal_p10_f1` | `0.1249140935077856` | `0.072238448560492` | `0.17429099987427488` |
| `task013_repeated_f1` | `0.10412902796532963` | `0.051453383018036036` | `0.15350593433181892` |
### receta / full_only / 1B_base_tech
n_prompts `400`, n_calibration_bundles `600`, rule `document_level_CAL_ONLY`, holdout_labels_in_threshold `false`, selection `modal fold wins across 5 seeds x 5 nested folds; tie break is mean train F1 then lowest column`.
CAL_ONLY on the nested recipe:
| tag | F1 | FRR | FAR | precision | recall | threshold | ROC-AUC | tp | fn | tn | fp |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `p05` | `0.7543859649122807` | `0.14` | `0.14` | `0.671875` | `0.86` | `0.2895460291277572` | `0.9178` | `86` | `14` | `258` | `42` |
| `p10` | `0.7403846153846154` | `0.23` | `0.10333333333333333` | `0.7129629629629629` | `0.77` | `0.31774289909518183` | `0.9178` | `77` | `23` | `269` | `31` |
| `p15` | `0.708994708994709` | `0.33` | `0.07333333333333333` | `0.7528089887640449` | `0.67` | `0.33332902102395184` | `0.9178` | `67` | `33` | `278` | `22` |
nested 5x5:
| metric | mean | std |
| --- | --- | --- |
| `f1` | `0.742755666816479` | `0.009854602771124779` |
| `frr` | `0.15400000000000003` | `0.013416407864998734` |
| `far` | `0.14400000000000002` | `0.005477225575051651` |
| `roc_auc` | `0.7767999999999999` | `0.037635259767640476` |
| seed | F1 | FRR | FAR | ROC-AUC |
| --- | --- | --- | --- | --- |
| `0` | `0.7510917030567685` | `0.14` | `0.14333333333333334` | `0.8370333333333333` |
| `1` | `0.7400881057268722` | `0.16` | `0.14333333333333334` | `0.7545999999999999` |
| `2` | `0.7377777777777778` | `0.17` | `0.14` | `0.7491666666666666` |
| `3` | `0.7304347826086957` | `0.16` | `0.15333333333333332` | `0.7525333333333333` |
| `4` | `0.7543859649122807` | `0.14` | `0.14` | `0.7906666666666666` |
modal recipe fixed 5x5:
| metric | mean | std |
| --- | --- | --- |
| `f1` | `0.7513565819177839` | `0.01317622075551062` |
| `frr` | `0.178` | `0.01788854381999832` |
| `far` | `0.122` | `0.006497862896539309` |
| `roc_auc` | `0.9178` | `0.0` |
| seed | F1 | FRR | FAR | ROC-AUC |
| --- | --- | --- | --- | --- |
| `0` | `0.7671232876712328` | `0.16` | `0.11666666666666667` | `0.9178` |
| `1` | `0.7636363636363637` | `0.16` | `0.12` | `0.9178` |
| `2` | `0.7407407407407407` | `0.2` | `0.12` | `0.9178` |
| `3` | `0.7387387387387387` | `0.18` | `0.13333333333333333` | `0.9178` |
| `4` | `0.7465437788018433` | `0.19` | `0.12` | `0.9178` |
Bootstrap n `1000`, seed `0`, probability `0.1`, threshold_policy `resampled_calibration_percentile`, refits_thresholds `true`.
| metric | ci95 low | ci95 high |
| --- | --- | --- |
| `f1` | `0.6733668341708543` | `0.7946772832267235` |
| `frr` | `0.13` | `0.35` |
| `far` | `0.07` | `0.13333333333333333` |
| `roc_auc` | `0.8961316666666665` | `0.9368341666666667` |
Paired bootstrap delta of the nested score against the frozen F1 literals:
| frozen key | point | ci95 low | ci95 high |
| --- | --- | --- | --- |
| `task012_f1` | `0.04060283330316495` | `-0.02413316582914571` | `0.09717728322672343` |
| `task013_cal_p10_f1` | `-0.0022817820814504597` | `-0.06701778121376112` | `0.05429266784210803` |
| `task013_repeated_f1` | `-0.013253748614618914` | `-0.07798974774692957` | `0.04332070130893958` |
### receta / clauses / 1B_base_tech
n_prompts `400`, n_calibration_bundles `600`, rule `document_level_CAL_ONLY`, holdout_labels_in_threshold `false`, selection `modal fold wins across 5 seeds x 5 nested folds; tie break is mean train F1 then lowest column`.
CAL_ONLY on the nested recipe:
| tag | F1 | FRR | FAR | precision | recall | threshold | ROC-AUC | tp | fn | tn | fp |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `p05` | `0.9038461538461539` | `0.06` | `0.04666666666666667` | `0.8703703703703703` | `0.94` | `0.4891306991938037` | `0.9792000000000001` | `94` | `6` | `286` | `14` |
| `p10` | `0.8783068783068783` | `0.17` | `0.02` | `0.9325842696629213` | `0.83` | `0.49552256757212493` | `0.9792000000000001` | `83` | `17` | `294` | `6` |
| `p15` | `0.850828729281768` | `0.23` | `0.013333333333333334` | `0.9506172839506173` | `0.77` | `0.5001272755093548` | `0.9792000000000001` | `77` | `23` | `296` | `4` |
nested 5x5:
| metric | mean | std |
| --- | --- | --- |
| `f1` | `0.8632849426609299` | `0.01703571400939901` |
| `frr` | `0.128` | `0.023874672772626646` |
| `far` | `0.04933333333333333` | `0.00494413232473044` |
| `roc_auc` | `0.9620200000000001` | `0.009245317132953816` |
| seed | F1 | FRR | FAR | ROC-AUC |
| --- | --- | --- | --- | --- |
| `0` | `0.8613861386138614` | `0.13` | `0.05` | `0.9734333333333334` |
| `1` | `0.835820895522388` | `0.16` | `0.056666666666666664` | `0.9576333333333333` |
| `2` | `0.864321608040201` | `0.14` | `0.043333333333333335` | `0.9511666666666666` |
| `3` | `0.8780487804878049` | `0.1` | `0.05` | `0.9581333333333334` |
| `4` | `0.8768472906403941` | `0.11` | `0.04666666666666667` | `0.9697333333333333` |
modal recipe fixed 5x5:
| metric | mean | std |
| --- | --- | --- |
| `f1` | `0.8876191641515078` | `0.01354106871240532` |
| `frr` | `0.08399999999999999` | `0.013416407864998736` |
| `far` | `0.049333333333333326` | `0.005962847939999437` |
| `roc_auc` | `0.9792000000000002` | `1.2412670766236366e-16` |
| seed | F1 | FRR | FAR | ROC-AUC |
| --- | --- | --- | --- | --- |
| `0` | `0.8985507246376812` | `0.07` | `0.04666666666666667` | `0.9792000000000001` |
| `1` | `0.8653846153846154` | `0.1` | `0.06` | `0.9792000000000001` |
| `2` | `0.8878048780487805` | `0.09` | `0.04666666666666667` | `0.9792000000000001` |
| `3` | `0.8878048780487805` | `0.09` | `0.04666666666666667` | `0.9792000000000001` |
| `4` | `0.8985507246376812` | `0.07` | `0.04666666666666667` | `0.9792000000000001` |
Bootstrap n `1000`, seed `0`, probability `0.1`, threshold_policy `resampled_calibration_percentile`, refits_thresholds `true`.
| metric | ci95 low | ci95 high |
| --- | --- | --- |
| `f1` | `0.8217504442751967` | `0.9214659685863874` |
| `frr` | `0.1` | `0.25` |
| `far` | `0.006666666666666667` | `0.05` |
| `roc_auc` | `0.9635258333333333` | `0.9918016666666667` |
Paired bootstrap delta of the nested score against the frozen F1 literals:
| frozen key | point | ci95 low | ci95 high |
| --- | --- | --- | --- |
| `task012_f1` | `0.148983660692039` | `0.0960504442751967` | `0.1957659685863874` |
| `task013_cal_p10_f1` | `0.0765615949643395` | `0.023628378547497202` | `0.1233439028586879` |
| `task013_repeated_f1` | `0.09011272041795206` | `0.03717950400110979` | `0.1368950283123005` |
### receta / full_only / 1B_base_tech_noise
n_prompts `400`, n_calibration_bundles `600`, rule `document_level_CAL_ONLY`, holdout_labels_in_threshold `false`, selection `modal fold wins across 5 seeds x 5 nested folds; tie break is mean train F1 then lowest column`.
CAL_ONLY on the nested recipe:
| tag | F1 | FRR | FAR | precision | recall | threshold | ROC-AUC | tp | fn | tn | fp |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `p05` | `0.7135678391959799` | `0.29` | `0.09333333333333334` | `0.7171717171717171` | `0.71` | `0.5601768731039588` | `0.9180333333333333` | `71` | `29` | `272` | `28` |
| `p10` | `0.6136363636363636` | `0.46` | `0.07333333333333333` | `0.7105263157894737` | `0.54` | `0.5825339760212047` | `0.9180333333333333` | `54` | `46` | `278` | `22` |
| `p15` | `0.5714285714285714` | `0.52` | `0.06666666666666667` | `0.7058823529411765` | `0.48` | `0.5900491626818362` | `0.9180333333333333` | `48` | `52` | `280` | `20` |
nested 5x5:
| metric | mean | std |
| --- | --- | --- |
| `f1` | `0.7449303201506592` | `0.010997248911401034` |
| `frr` | `0.138` | `0.024899799195977464` |
| `far` | `0.15066666666666667` | `0.00641179468722378` |
| `roc_auc` | `0.8207466666666668` | `0.022296320075045742` |
| seed | F1 | FRR | FAR | ROC-AUC |
| --- | --- | --- | --- | --- |
| `0` | `0.7586206896551724` | `0.12` | `0.14666666666666667` | `0.8481333333333334` |
| `1` | `0.75` | `0.13` | `0.15` | `0.8061333333333334` |
| `2` | `0.7288888888888889` | `0.18` | `0.14333333333333334` | `0.81` |
| `3` | `0.7457627118644068` | `0.12` | `0.16` | `0.7984333333333334` |
| `4` | `0.7413793103448276` | `0.14` | `0.15333333333333332` | `0.8410333333333333` |
modal recipe fixed 5x5:
| metric | mean | std |
| --- | --- | --- |
| `f1` | `0.7631017818257231` | `0.003814173208194929` |
| `frr` | `0.098` | `0.008366600265340758` |
| `far` | `0.154` | `0.0014907119849998695` |
| `roc_auc` | `0.9180333333333334` | `1.2412670766236366e-16` |
| seed | F1 | FRR | FAR | ROC-AUC |
| --- | --- | --- | --- | --- |
| `0` | `0.7679324894514767` | `0.09` | `0.15333333333333332` | `0.9180333333333333` |
| `1` | `0.7627118644067796` | `0.1` | `0.15333333333333332` | `0.9180333333333333` |
| `2` | `0.7574468085106383` | `0.11` | `0.15333333333333332` | `0.9180333333333333` |
| `3` | `0.7647058823529411` | `0.09` | `0.15666666666666668` | `0.9180333333333333` |
| `4` | `0.7627118644067796` | `0.1` | `0.15333333333333332` | `0.9180333333333333` |
Bootstrap n `1000`, seed `0`, probability `0.1`, threshold_policy `resampled_calibration_percentile`, refits_thresholds `true`.
| metric | ci95 low | ci95 high |
| --- | --- | --- |
| `f1` | `0.5433230029946374` | `0.6779661016949152` |
| `frr` | `0.36975` | `0.55` |
| `far` | `0.056666666666666664` | `0.09333333333333334` |
| `roc_auc` | `0.9033991666666666` | `0.9324366666666667` |
Paired bootstrap delta of the nested score against the frozen F1 literals:
| frozen key | point | ci95 low | ci95 high |
| --- | --- | --- | --- |
| `task012_f1` | `-0.08465733306915076` | `-0.15417699700536255` | `-0.019533898305084785` |
| `task013_cal_p10_f1` | `-0.12754194845376615` | `-0.19706161238997796` | `-0.062418513689700195` |
| `task013_repeated_f1` | `-0.13851391498693463` | `-0.20803357892314642` | `-0.07339048022286865` |
### receta / clauses / 1B_base_tech_noise
n_prompts `400`, n_calibration_bundles `600`, rule `document_level_CAL_ONLY`, holdout_labels_in_threshold `false`, selection `modal fold wins across 5 seeds x 5 nested folds; tie break is mean train F1 then lowest column`.
CAL_ONLY on the nested recipe:
| tag | F1 | FRR | FAR | precision | recall | threshold | ROC-AUC | tp | fn | tn | fp |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `p05` | `0.896551724137931` | `0.09` | `0.04` | `0.883495145631068` | `0.91` | `0.4732926472590812` | `0.9802333333333333` | `91` | `9` | `288` | `12` |
| `p10` | `0.8648648648648649` | `0.2` | `0.016666666666666666` | `0.9411764705882353` | `0.8` | `0.4798925788678054` | `0.9802333333333333` | `80` | `20` | `295` | `5` |
| `p15` | `0.8045977011494253` | `0.3` | `0.013333333333333334` | `0.9459459459459459` | `0.7` | `0.4838509872756913` | `0.9802333333333333` | `70` | `30` | `296` | `4` |
nested 5x5:
| metric | mean | std |
| --- | --- | --- |
| `f1` | `0.8708893003272469` | `0.0106366386154175` |
| `frr` | `0.11599999999999999` | `0.020736441353327726` |
| `far` | `0.04866666666666667` | `0.006055300708194982` |
| `roc_auc` | `0.9765666666666666` | `0.0035392246482967202` |
| seed | F1 | FRR | FAR | ROC-AUC |
| --- | --- | --- | --- | --- |
| `0` | `0.88` | `0.12` | `0.04` | `0.9797333333333333` |
| `1` | `0.86` | `0.14` | `0.04666666666666667` | `0.9762666666666666` |
| `2` | `0.8613861386138614` | `0.13` | `0.05` | `0.9783` |
| `3` | `0.8695652173913043` | `0.1` | `0.056666666666666664` | `0.9706333333333333` |
| `4` | `0.883495145631068` | `0.09` | `0.05` | `0.9779` |
modal recipe fixed 5x5:
| metric | mean | std |
| --- | --- | --- |
| `f1` | `0.8869332720627024` | `0.0044757445204071265` |
| `frr` | `0.098` | `0.008366600265340758` |
| `far` | `0.044000000000000004` | `0.004346134936801767` |
| `roc_auc` | `0.9802333333333333` | `0.0` |
| seed | F1 | FRR | FAR | ROC-AUC |
| --- | --- | --- | --- | --- |
| `0` | `0.8878048780487805` | `0.09` | `0.04666666666666667` | `0.9802333333333333` |
| `1` | `0.8811881188118812` | `0.11` | `0.043333333333333335` | `0.9802333333333333` |
| `2` | `0.8910891089108911` | `0.1` | `0.04` | `0.9802333333333333` |
| `3` | `0.8910891089108911` | `0.1` | `0.04` | `0.9802333333333333` |
| `4` | `0.883495145631068` | `0.09` | `0.05` | `0.9802333333333333` |
Bootstrap n `1000`, seed `0`, probability `0.1`, threshold_policy `resampled_calibration_percentile`, refits_thresholds `true`.
| metric | ci95 low | ci95 high |
| --- | --- | --- |
| `f1` | `0.7861271676300579` | `0.91005291005291` |
| `frr` | `0.13` | `0.32` |
| `far` | `0.0033333333333333335` | `0.03333333333333333` |
| `roc_auc` | `0.9662333333333334` | `0.9919041666666667` |
Paired bootstrap delta of the nested score against the frozen F1 literals:
| frozen key | point | ci95 low | ci95 high |
| --- | --- | --- | --- |
| `task012_f1` | `0.12849791102707256` | `0.06042716763005784` | `0.18435291005291` |
| `task013_cal_p10_f1` | `0.05607584529937307` | `-0.011994898097641649` | `0.1119308443252105` |
| `task013_repeated_f1` | `0.06962697075298566` | `0.0015562273559709405` | `0.1254819697788231` |
### receta / full_only / 1B_full
n_prompts `400`, n_calibration_bundles `600`, rule `document_level_CAL_ONLY`, holdout_labels_in_threshold `false`, selection `modal fold wins across 5 seeds x 5 nested folds; tie break is mean train F1 then lowest column`.
CAL_ONLY on the nested recipe:
| tag | F1 | FRR | FAR | precision | recall | threshold | ROC-AUC | tp | fn | tn | fp |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `p05` | `0.6934673366834171` | `0.31` | `0.1` | `0.696969696969697` | `0.69` | `0.5561329211731433` | `0.9164666666666667` | `69` | `31` | `270` | `30` |
| `p10` | `0.6222222222222222` | `0.44` | `0.08` | `0.7` | `0.56` | `0.5737362602691222` | `0.9164666666666667` | `56` | `44` | `276` | `24` |
| `p15` | `0.5798816568047337` | `0.51` | `0.06666666666666667` | `0.7101449275362319` | `0.49` | `0.5851854491588836` | `0.9164666666666667` | `49` | `51` | `280` | `20` |
nested 5x5:
| metric | mean | std |
| --- | --- | --- |
| `f1` | `0.7588019823313941` | `0.009249697573858396` |
| `frr` | `0.1` | `0.017320508075688777` |
| `far` | `0.15733333333333333` | `0.0014907119849998569` |
| `roc_auc` | `0.9149333333333333` | `0.002951365032583336` |
| seed | F1 | FRR | FAR | ROC-AUC |
| --- | --- | --- | --- | --- |
| `0` | `0.7647058823529411` | `0.09` | `0.15666666666666668` | `0.9164666666666667` |
| `1` | `0.7563025210084033` | `0.1` | `0.16` | `0.9097` |
| `2` | `0.7647058823529411` | `0.09` | `0.15666666666666668` | `0.9164666666666667` |
| `3` | `0.7435897435897436` | `0.13` | `0.15666666666666668` | `0.9155666666666666` |
| `4` | `0.7647058823529411` | `0.09` | `0.15666666666666668` | `0.9164666666666667` |
modal recipe fixed 5x5:
| metric | mean | std |
| --- | --- | --- |
| `f1` | `0.7615519399249061` | `0.007052429666207086` |
| `frr` | `0.096` | `0.013416407864998738` |
| `far` | `0.15666666666666668` | `0.0` |
| `roc_auc` | `0.9164666666666668` | `1.2412670766236366e-16` |
| seed | F1 | FRR | FAR | ROC-AUC |
| --- | --- | --- | --- | --- |
| `0` | `0.7647058823529411` | `0.09` | `0.15666666666666668` | `0.9164666666666667` |
| `1` | `0.7647058823529411` | `0.09` | `0.15666666666666668` | `0.9164666666666667` |
| `2` | `0.7647058823529411` | `0.09` | `0.15666666666666668` | `0.9164666666666667` |
| `3` | `0.7489361702127659` | `0.12` | `0.15666666666666668` | `0.9164666666666667` |
| `4` | `0.7647058823529411` | `0.09` | `0.15666666666666668` | `0.9164666666666667` |
Bootstrap n `1000`, seed `0`, probability `0.1`, threshold_policy `resampled_calibration_percentile`, refits_thresholds `true`.
| metric | ci95 low | ci95 high |
| --- | --- | --- |
| `f1` | `0.5517241379310345` | `0.6923184357541899` |
| `frr` | `0.35` | `0.52` |
| `far` | `0.06` | `0.1` |
| `roc_auc` | `0.8999991666666666` | `0.9321708333333335` |
Paired bootstrap delta of the nested score against the frozen F1 literals:
| frozen key | point | ci95 low | ci95 high |
| --- | --- | --- | --- |
| `task012_f1` | `-0.07600505016730838` | `-0.14577586206896553` | `-0.00518156424581009` |
| `task013_cal_p10_f1` | `-0.1188896655519238` | `-0.18866047745358094` | `-0.0480661796304255` |
| `task013_repeated_f1` | `-0.12986163208509224` | `-0.1996324439867494` | `-0.05903814616359395` |
### receta / clauses / 1B_full
n_prompts `400`, n_calibration_bundles `600`, rule `document_level_CAL_ONLY`, holdout_labels_in_threshold `false`, selection `modal fold wins across 5 seeds x 5 nested folds; tie break is mean train F1 then lowest column`.
CAL_ONLY on the nested recipe:
| tag | F1 | FRR | FAR | precision | recall | threshold | ROC-AUC | tp | fn | tn | fp |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `p05` | `0.8666666666666667` | `0.09` | `0.06333333333333334` | `0.8272727272727273` | `0.91` | `0.48451289878436754` | `0.9791666666666666` | `91` | `9` | `281` | `19` |
| `p10` | `0.8829787234042553` | `0.17` | `0.016666666666666666` | `0.9431818181818182` | `0.83` | `0.491950229317033` | `0.9791666666666666` | `83` | `17` | `295` | `5` |
| `p15` | `0.8314606741573034` | `0.26` | `0.013333333333333334` | `0.9487179487179487` | `0.74` | `0.4969153683638866` | `0.9791666666666666` | `74` | `26` | `296` | `4` |
nested 5x5:
| metric | mean | std |
| --- | --- | --- |
| `f1` | `0.8779304506282788` | `0.009681912428697568` |
| `frr` | `0.138` | `0.008366600265340753` |
| `far` | `0.034` | `0.00983192080250175` |
| `roc_auc` | `0.9705933333333334` | `0.003479335824231139` |
| seed | F1 | FRR | FAR | ROC-AUC |
| --- | --- | --- | --- | --- |
| `0` | `0.8865979381443299` | `0.14` | `0.02666666666666667` | `0.972` |
| `1` | `0.8808290155440415` | `0.15` | `0.02666666666666667` | `0.9700666666666666` |
| `2` | `0.8613861386138614` | `0.13` | `0.05` | `0.9725333333333334` |
| `3` | `0.8787878787878788` | `0.13` | `0.03666666666666667` | `0.9735666666666667` |
| `4` | `0.882051282051282` | `0.14` | `0.03` | `0.9647999999999999` |
modal recipe fixed 5x5:
| metric | mean | std |
| --- | --- | --- |
| `f1` | `0.8912696292338291` | `0.005149452129231724` |
| `frr` | `0.148` | `0.01095445115010332` |
| `far` | `0.02` | `0.007453559924999299` |
| `roc_auc` | `0.9791666666666666` | `0.0` |
| seed | F1 | FRR | FAR | ROC-AUC |
| --- | --- | --- | --- | --- |
| `0` | `0.8888888888888888` | `0.16` | `0.016666666666666666` | `0.9791666666666666` |
| `1` | `0.8947368421052632` | `0.15` | `0.016666666666666666` | `0.9791666666666666` |
| `2` | `0.8947368421052632` | `0.15` | `0.016666666666666666` | `0.9791666666666666` |
| `3` | `0.883248730964467` | `0.13` | `0.03333333333333333` | `0.9791666666666666` |
| `4` | `0.8947368421052632` | `0.15` | `0.016666666666666666` | `0.9791666666666666` |
Bootstrap n `1000`, seed `0`, probability `0.1`, threshold_policy `resampled_calibration_percentile`, refits_thresholds `true`.
| metric | ci95 low | ci95 high |
| --- | --- | --- |
| `f1` | `0.8275669427855904` | `0.9278350515463918` |
| `frr` | `0.09` | `0.24024999999999977` |
| `far` | `0.006583333333333339` | `0.04666666666666667` |
| `roc_auc` | `0.9648316666666665` | `0.9904016666666667` |
Paired bootstrap delta of the nested score against the frozen F1 literals:
| frozen key | point | ci95 low | ci95 high |
| --- | --- | --- | --- |
| `task012_f1` | `0.15472123101468407` | `0.10186694278559043` | `0.20213505154639178` |
| `task013_cal_p10_f1` | `0.08229916528698453` | `0.029444877057890933` | `0.12971298581869228` |
| `task013_repeated_f1` | `0.09585029074059713` | `0.04299600251150352` | `0.14326411127230487` |
### receta / full_only / 1B_full_v3
n_prompts `400`, n_calibration_bundles `600`, rule `document_level_CAL_ONLY`, holdout_labels_in_threshold `false`, selection `modal fold wins across 5 seeds x 5 nested folds; tie break is mean train F1 then lowest column`.
CAL_ONLY on the nested recipe:
| tag | F1 | FRR | FAR | precision | recall | threshold | ROC-AUC | tp | fn | tn | fp |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `p05` | `0.7636363636363637` | `0.16` | `0.12` | `0.7` | `0.84` | `0.2887323176872545` | `0.9227666666666666` | `84` | `16` | `264` | `36` |
| `p10` | `0.7164179104477612` | `0.28` | `0.09666666666666666` | `0.7128712871287128` | `0.72` | `0.3173995899884165` | `0.9227666666666666` | `72` | `28` | `271` | `29` |
| `p15` | `0.6808510638297872` | `0.36` | `0.08` | `0.7272727272727273` | `0.64` | `0.33189685166992355` | `0.9227666666666666` | `64` | `36` | `276` | `24` |
nested 5x5:
| metric | mean | std |
| --- | --- | --- |
| `f1` | `0.7453808183346586` | `0.00666037412425954` |
| `frr` | `0.16` | `0.01224744871391589` |
| `far` | `0.13799999999999998` | `0.009006170724070865` |
| `roc_auc` | `0.8321933333333332` | `0.05488547369042396` |
| seed | F1 | FRR | FAR | ROC-AUC |
| --- | --- | --- | --- | --- |
| `0` | `0.7545454545454545` | `0.17` | `0.12333333333333334` | `0.9227666666666666` |
| `1` | `0.7466666666666667` | `0.16` | `0.13666666666666666` | `0.7732333333333333` |
| `2` | `0.7377777777777778` | `0.17` | `0.14` | `0.8266` |
| `3` | `0.7478260869565218` | `0.14` | `0.14666666666666667` | `0.8193333333333332` |
| `4` | `0.7400881057268722` | `0.16` | `0.14333333333333334` | `0.8190333333333334` |
modal recipe fixed 5x5:
| metric | mean | std |
| --- | --- | --- |
| `f1` | `0.7482918293841845` | `0.010255171890646748` |
| `frr` | `0.162` | `0.008366600265340762` |
| `far` | `0.13399999999999998` | `0.00924962461700774` |
| `roc_auc` | `0.9227666666666666` | `0.0` |
| seed | F1 | FRR | FAR | ROC-AUC |
| --- | --- | --- | --- | --- |
| `0` | `0.7545454545454545` | `0.17` | `0.12333333333333334` | `0.9227666666666666` |
| `1` | `0.7567567567567568` | `0.16` | `0.12666666666666668` | `0.9227666666666666` |
| `2` | `0.7345132743362832` | `0.17` | `0.14333333333333334` | `0.9227666666666666` |
| `3` | `0.7555555555555555` | `0.15` | `0.13333333333333333` | `0.9227666666666666` |
| `4` | `0.7400881057268722` | `0.16` | `0.14333333333333334` | `0.9227666666666666` |
Bootstrap n `1000`, seed `0`, probability `0.1`, threshold_policy `resampled_calibration_percentile`, refits_thresholds `true`.
| metric | ci95 low | ci95 high |
| --- | --- | --- |
| `f1` | `0.6494777891725589` | `0.7751196172248804` |
| `frr` | `0.19` | `0.39` |
| `far` | `0.07333333333333333` | `0.11666666666666667` |
| `roc_auc` | `0.9038983333333334` | `0.940035` |
Paired bootstrap delta of the nested score against the frozen F1 literals:
| frozen key | point | ci95 low | ci95 high |
| --- | --- | --- | --- |
| `task012_f1` | `0.014415575937684102` | `-0.048022210827441014` | `0.07761961722488042` |
| `task013_cal_p10_f1` | `-0.028469039446931306` | `-0.09090682621205642` | `0.03473500184026501` |
| `task013_repeated_f1` | `-0.03944100598009976` | `-0.10187879274522488` | `0.02376303530709656` |
### receta / clauses / 1B_full_v3
n_prompts `400`, n_calibration_bundles `600`, rule `document_level_CAL_ONLY`, holdout_labels_in_threshold `false`, selection `modal fold wins across 5 seeds x 5 nested folds; tie break is mean train F1 then lowest column`.
CAL_ONLY on the nested recipe:
| tag | F1 | FRR | FAR | precision | recall | threshold | ROC-AUC | tp | fn | tn | fp |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `p05` | `0.8761904761904762` | `0.08` | `0.06` | `0.8363636363636363` | `0.92` | `0.48310678076031716` | `0.9802333333333333` | `92` | `8` | `282` | `18` |
| `p10` | `0.8770053475935828` | `0.18` | `0.016666666666666666` | `0.9425287356321839` | `0.82` | `0.4911316484365966` | `0.9802333333333333` | `82` | `18` | `295` | `5` |
| `p15` | `0.8045977011494253` | `0.3` | `0.013333333333333334` | `0.9459459459459459` | `0.7` | `0.4959425366295612` | `0.9802333333333333` | `70` | `30` | `296` | `4` |
nested 5x5:
| metric | mean | std |
| --- | --- | --- |
| `f1` | `0.8602960108810551` | `0.004088619685136745` |
| `frr` | `0.138` | `0.008366600265340753` |
| `far` | `0.04733333333333334` | `0.004944132324730443` |
| `roc_auc` | `0.9540000000000001` | `0.016312026919491768` |
| seed | F1 | FRR | FAR | ROC-AUC |
| --- | --- | --- | --- | --- |
| `0` | `0.86` | `0.14` | `0.04666666666666667` | `0.9482` |
| `1` | `0.8571428571428571` | `0.13` | `0.05333333333333334` | `0.9617000000000001` |
| `2` | `0.8656716417910447` | `0.13` | `0.04666666666666667` | `0.9785000000000001` |
| `3` | `0.8629441624365483` | `0.15` | `0.04` | `0.9374333333333333` |
| `4` | `0.8557213930348259` | `0.14` | `0.05` | `0.9441666666666667` |
modal recipe fixed 5x5:
| metric | mean | std |
| --- | --- | --- |
| `f1` | `0.8746050178972586` | `0.0033258414466764102` |
| `frr` | `0.14200000000000002` | `0.00836660026534075` |
| `far` | `0.034666666666666665` | `0.001825741858350554` |
| `roc_auc` | `0.9802333333333333` | `0.0` |
| seed | F1 | FRR | FAR | ROC-AUC |
| --- | --- | --- | --- | --- |
| `0` | `0.8717948717948718` | `0.15` | `0.03333333333333333` | `0.9802333333333333` |
| `1` | `0.8730964467005076` | `0.14` | `0.03666666666666667` | `0.9802333333333333` |
| `2` | `0.8787878787878788` | `0.13` | `0.03666666666666667` | `0.9802333333333333` |
| `3` | `0.8775510204081632` | `0.14` | `0.03333333333333333` | `0.9802333333333333` |
| `4` | `0.8717948717948718` | `0.15` | `0.03333333333333333` | `0.9802333333333333` |
Bootstrap n `1000`, seed `0`, probability `0.1`, threshold_policy `resampled_calibration_percentile`, refits_thresholds `true`.
| metric | ci95 low | ci95 high |
| --- | --- | --- |
| `f1` | `0.8111111111111111` | `0.9200158730158731` |
| `frr` | `0.09` | `0.28` |
| `far` | `0.0033333333333333335` | `0.043333333333333335` |
| `roc_auc` | `0.9670325000000001` | `0.9910691666666667` |
Paired bootstrap delta of the nested score against the frozen F1 literals:
| frozen key | point | ci95 low | ci95 high |
| --- | --- | --- | --- |
| `task012_f1` | `0.14373472106765192` | `0.0854111111111111` | `0.19431587301587303` |
| `task013_cal_p10_f1` | `0.07131265533995242` | `0.012989045383411613` | `0.12189380728817353` |
| `task013_repeated_f1` | `0.08486378079356502` | `0.026540170837024202` | `0.13544493274178612` |
### 6.4 [ORACLE_UPPER_BOUND]
Every row in this subsection carries the stored tag `[ORACLE_UPPER_BOUND]`. These F1 values are not CAL_ONLY operating points and they are not the 5x5 means above.
#### python / full_only / 1B_base_tech
| tag | source | F1 | FRR | FAR | threshold |
| --- | --- | --- | --- | --- | --- |
| `[ORACLE_UPPER_BOUND]` | `seed0_mixed_scores_fit_on_all_holdout_labels` | `0.7281553398058253` | `0.25` | `0.10333333333333333` | `0.5357482988057042` |
| `[ORACLE_UPPER_BOUND]` | `modal_recipe_repeated_oof` | `0.7414634146341463` | `0.24` | `0.09666666666666666` | `0.5357482988057042` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.7222222222222222` | `0.22` | `0.12666666666666668` | `0.5344585632320921` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.714975845410628` | `0.26` | `0.11` | `0.5476783618473273` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_clip_polboost|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.7129629629629629` | `0.23` | `0.13` | `0.5569384658570354` |
| `[ORACLE_UPPER_BOUND]` | `polarity_v2_subset|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.6137931034482759` | `0.11` | `0.33666666666666667` | `0.2523200388428075` |
| `[ORACLE_UPPER_BOUND]` | `base_repaired|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.5647840531561462` | `0.15` | `0.38666666666666666` | `0.4414259647919292` |
| `[ORACLE_UPPER_BOUND]` | `f2_l2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.5555555555555556` | `0.15` | `0.4033333333333333` | `0.34979198724764127` |
| `[ORACLE_UPPER_BOUND]` | `tail_p3|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.5443037974683544` | `0.14` | `0.43333333333333335` | `0.34904214845088466` |
| `[ORACLE_UPPER_BOUND]` | `tail_p5|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.5576923076923077` | `0.13` | `0.4166666666666667` | `0.3491605190093569` |
| `[ORACLE_UPPER_BOUND]` | `tail_p10|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.554140127388535` | `0.13` | `0.42333333333333334` | `0.3507585206141468` |
| `[ORACLE_UPPER_BOUND]` | `tail_p25|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.56` | `0.09` | `0.44666666666666666` | `0.34548388894612353` |
#### python / clauses / 1B_base_tech
| tag | source | F1 | FRR | FAR | threshold |
| --- | --- | --- | --- | --- | --- |
| `[ORACLE_UPPER_BOUND]` | `seed0_mixed_scores_fit_on_all_holdout_labels` | `0.7981651376146789` | `0.13` | `0.10333333333333333` | `0.4894157376513294` |
| `[ORACLE_UPPER_BOUND]` | `modal_recipe_repeated_oof` | `0.8241206030150754` | `0.18` | `0.056666666666666664` | `0.5093616674908599` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.7107438016528925` | `0.14` | `0.18666666666666668` | `0.4916555309033399` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.7410714285714286` | `0.17` | `0.13666666666666666` | `0.5043028333634587` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.7596153846153846` | `0.21` | `0.09666666666666666` | `0.5158470184533978` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.7671232876712328` | `0.16` | `0.11666666666666667` | `0.5209865333228181` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.7044534412955465` | `0.13` | `0.2` | `0.4871345795942519` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.7339449541284404` | `0.2` | `0.12666666666666668` | `0.5079685302949616` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.7606837606837606` | `0.11` | `0.15` | `0.5091781680930244` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.7767857142857143` | `0.13` | `0.12333333333333334` | `0.5239574505670889` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_clip_polboost|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.6987951807228916` | `0.13` | `0.20666666666666667` | `0.4829934276193868` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_clip_polboost|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.7300380228136882` | `0.04` | `0.22333333333333333` | `0.4876822809863761` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_clip_polboost|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.7557603686635944` | `0.18` | `0.11666666666666667` | `0.5220528141795294` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_clip_polboost|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.775330396475771` | `0.12` | `0.13` | `0.5335704613156655` |
| `[ORACLE_UPPER_BOUND]` | `polarity_v2_subset|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.6517857142857143` | `0.27` | `0.17` | `0.2369810466742439` |
| `[ORACLE_UPPER_BOUND]` | `polarity_v2_subset|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.6757990867579908` | `0.26` | `0.15` | `0.2463244229483489` |
| `[ORACLE_UPPER_BOUND]` | `polarity_v2_subset|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.7083333333333334` | `0.15` | `0.18333333333333332` | `0.24803367814288352` |
| `[ORACLE_UPPER_BOUND]` | `polarity_v2_subset|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.72` | `0.19` | `0.14666666666666667` | `0.27595500651438903` |
| `[ORACLE_UPPER_BOUND]` | `base_repaired|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.5644171779141104` | `0.08` | `0.44666666666666666` | `0.5676436690598992` |
| `[ORACLE_UPPER_BOUND]` | `base_repaired|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.5968992248062015` | `0.23` | `0.27` | `0.5929814647918827` |
| `[ORACLE_UPPER_BOUND]` | `base_repaired|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.6260162601626016` | `0.23` | `0.23` | `0.5777541779566839` |
| `[ORACLE_UPPER_BOUND]` | `base_repaired|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.6036363636363636` | `0.17` | `0.30666666666666664` | `0.5165076961043711` |
| `[ORACLE_UPPER_BOUND]` | `f2_l2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.6556016597510373` | `0.21` | `0.20666666666666667` | `0.34987879975091507` |
| `[ORACLE_UPPER_BOUND]` | `f2_l2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.6825396825396826` | `0.14` | `0.22` | `0.3516596501900516` |
| `[ORACLE_UPPER_BOUND]` | `f2_l2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.6551724137931034` | `0.24` | `0.18666666666666668` | `0.35712292544519053` |
| `[ORACLE_UPPER_BOUND]` | `f2_l2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.5859375` | `0.25` | `0.27` | `0.3577739380370541` |
| `[ORACLE_UPPER_BOUND]` | `tail_p3|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.5629139072847682` | `0.15` | `0.39` | `0.34050872373695945` |
| `[ORACLE_UPPER_BOUND]` | `tail_p3|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.5748987854251012` | `0.29` | `0.25333333333333335` | `0.3555790223561034` |
| `[ORACLE_UPPER_BOUND]` | `tail_p3|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.5746268656716418` | `0.23` | `0.30333333333333334` | `0.3543173806215518` |
| `[ORACLE_UPPER_BOUND]` | `tail_p3|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.5704225352112676` | `0.19` | `0.3433333333333333` | `0.355993816633399` |
| `[ORACLE_UPPER_BOUND]` | `tail_p5|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.5886792452830188` | `0.22` | `0.29` | `0.3478485921719418` |
| `[ORACLE_UPPER_BOUND]` | `tail_p5|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.5963636363636363` | `0.18` | `0.31` | `0.34955312794561316` |
| `[ORACLE_UPPER_BOUND]` | `tail_p5|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.5984251968503937` | `0.24` | `0.26` | `0.3570554389300352` |
| `[ORACLE_UPPER_BOUND]` | `tail_p5|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.5757575757575758` | `0.24` | `0.29333333333333333` | `0.36187659684259027` |
| `[ORACLE_UPPER_BOUND]` | `tail_p10|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.5985401459854015` | `0.18` | `0.30666666666666664` | `0.3442592925674462` |
| `[ORACLE_UPPER_BOUND]` | `tail_p10|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.607773851590106` | `0.14` | `0.3233333333333333` | `0.34766582797939316` |
| `[ORACLE_UPPER_BOUND]` | `tail_p10|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.6122448979591837` | `0.1` | `0.3466666666666667` | `0.34979667039881746` |
| `[ORACLE_UPPER_BOUND]` | `tail_p10|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.5906040268456376` | `0.12` | `0.36666666666666664` | `0.3501947911386747` |
| `[ORACLE_UPPER_BOUND]` | `tail_p25|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.6213592233009708` | `0.36` | `0.14` | `0.3562686469574779` |
| `[ORACLE_UPPER_BOUND]` | `tail_p25|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.6343283582089553` | `0.15` | `0.27666666666666667` | `0.3469388191141947` |
| `[ORACLE_UPPER_BOUND]` | `tail_p25|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.6433566433566433` | `0.08` | `0.31333333333333335` | `0.34801605390820434` |
| `[ORACLE_UPPER_BOUND]` | `tail_p25|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.6072607260726073` | `0.08` | `0.37` | `0.3485832135152539` |
#### python / full_only / 1B_base_tech_noise
| tag | source | F1 | FRR | FAR | threshold |
| --- | --- | --- | --- | --- | --- |
| `[ORACLE_UPPER_BOUND]` | `seed0_mixed_scores_fit_on_all_holdout_labels` | `0.7263681592039801` | `0.27` | `0.09333333333333334` | `0.5350620204749679` |
| `[ORACLE_UPPER_BOUND]` | `modal_recipe_repeated_oof` | `0.73` | `0.27` | `0.09` | `0.5356967333235556` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.7219512195121951` | `0.26` | `0.10333333333333333` | `0.5350620204749679` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.7053140096618358` | `0.27` | `0.11333333333333333` | `0.5436045500727298` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_clip_polboost|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.7081339712918661` | `0.26` | `0.11666666666666667` | `0.5556726964123455` |
| `[ORACLE_UPPER_BOUND]` | `polarity_v2_subset|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.664` | `0.17` | `0.22333333333333333` | `0.27682672687536114` |
| `[ORACLE_UPPER_BOUND]` | `base_repaired|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.5654761904761905` | `0.05` | `0.47` | `0.40195460407905753` |
| `[ORACLE_UPPER_BOUND]` | `f2_l2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.5555555555555556` | `0.15` | `0.4033333333333333` | `0.34979198724764127` |
| `[ORACLE_UPPER_BOUND]` | `tail_p3|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.5443037974683544` | `0.14` | `0.43333333333333335` | `0.34904214845088466` |
| `[ORACLE_UPPER_BOUND]` | `tail_p5|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.5576923076923077` | `0.13` | `0.4166666666666667` | `0.3491605190093569` |
| `[ORACLE_UPPER_BOUND]` | `tail_p10|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.554140127388535` | `0.13` | `0.42333333333333334` | `0.3507585206141468` |
| `[ORACLE_UPPER_BOUND]` | `tail_p25|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.56` | `0.09` | `0.44666666666666666` | `0.34548388894612353` |
#### python / clauses / 1B_base_tech_noise
| tag | source | F1 | FRR | FAR | threshold |
| --- | --- | --- | --- | --- | --- |
| `[ORACLE_UPPER_BOUND]` | `seed0_mixed_scores_fit_on_all_holdout_labels` | `0.8133971291866029` | `0.15` | `0.08` | `0.4823982782990759` |
| `[ORACLE_UPPER_BOUND]` | `modal_recipe_repeated_oof` | `0.8229665071770335` | `0.14` | `0.07666666666666666` | `0.48351359794890325` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.7250996015936255` | `0.09` | `0.2` | `0.4832627940718279` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.7592592592592593` | `0.18` | `0.11333333333333333` | `0.5012630227113684` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.776255707762557` | `0.15` | `0.11333333333333333` | `0.5073216436994494` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.7684729064039408` | `0.22` | `0.08333333333333333` | `0.5231183280133576` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.7272727272727273` | `0.12` | `0.18` | `0.4827382210796613` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.7583333333333333` | `0.09` | `0.16333333333333333` | `0.49095897141483175` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.775330396475771` | `0.12` | `0.13` | `0.5056104527253777` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.7707317073170732` | `0.21` | `0.08666666666666667` | `0.5258939971693147` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_clip_polboost|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.726530612244898` | `0.11` | `0.18666666666666668` | `0.47486853745027635` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_clip_polboost|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.7627906976744186` | `0.18` | `0.11` | `0.5027167107010516` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_clip_polboost|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.7751196172248804` | `0.19` | `0.09333333333333334` | `0.5169631060225224` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_clip_polboost|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.7766990291262136` | `0.2` | `0.08666666666666667` | `0.5364192310960847` |
| `[ORACLE_UPPER_BOUND]` | `polarity_v2_subset|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.6693877551020408` | `0.18` | `0.21` | `0.20812127045608061` |
| `[ORACLE_UPPER_BOUND]` | `polarity_v2_subset|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.726457399103139` | `0.19` | `0.14` | `0.2331569670965768` |
| `[ORACLE_UPPER_BOUND]` | `polarity_v2_subset|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.7477477477477478` | `0.17` | `0.13` | `0.25446719575236676` |
| `[ORACLE_UPPER_BOUND]` | `polarity_v2_subset|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.73` | `0.27` | `0.09` | `0.2955933204038149` |
| `[ORACLE_UPPER_BOUND]` | `base_repaired|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.5661538461538461` | `0.08` | `0.44333333333333336` | `0.5692840013234715` |
| `[ORACLE_UPPER_BOUND]` | `base_repaired|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.5977011494252874` | `0.22` | `0.27666666666666667` | `0.5895268503920542` |
| `[ORACLE_UPPER_BOUND]` | `base_repaired|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.6287878787878788` | `0.17` | `0.27` | `0.5624728537173669` |
| `[ORACLE_UPPER_BOUND]` | `base_repaired|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.6007326007326007` | `0.18` | `0.30333333333333334` | `0.520908516772156` |
| `[ORACLE_UPPER_BOUND]` | `f2_l2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.6556016597510373` | `0.21` | `0.20666666666666667` | `0.34987879975091507` |
| `[ORACLE_UPPER_BOUND]` | `f2_l2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.6825396825396826` | `0.14` | `0.22` | `0.3516596501900516` |
| `[ORACLE_UPPER_BOUND]` | `f2_l2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.6551724137931034` | `0.24` | `0.18666666666666668` | `0.35712292544519053` |
| `[ORACLE_UPPER_BOUND]` | `f2_l2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.5859375` | `0.25` | `0.27` | `0.3577739380370541` |
| `[ORACLE_UPPER_BOUND]` | `tail_p3|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.5629139072847682` | `0.15` | `0.39` | `0.34050872373695945` |
| `[ORACLE_UPPER_BOUND]` | `tail_p3|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.5748987854251012` | `0.29` | `0.25333333333333335` | `0.3555790223561034` |
| `[ORACLE_UPPER_BOUND]` | `tail_p3|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.5746268656716418` | `0.23` | `0.30333333333333334` | `0.3543173806215518` |
| `[ORACLE_UPPER_BOUND]` | `tail_p3|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.5704225352112676` | `0.19` | `0.3433333333333333` | `0.355993816633399` |
| `[ORACLE_UPPER_BOUND]` | `tail_p5|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.5886792452830188` | `0.22` | `0.29` | `0.3478485921719418` |
| `[ORACLE_UPPER_BOUND]` | `tail_p5|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.5963636363636363` | `0.18` | `0.31` | `0.34955312794561316` |
| `[ORACLE_UPPER_BOUND]` | `tail_p5|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.5984251968503937` | `0.24` | `0.26` | `0.3570554389300352` |
| `[ORACLE_UPPER_BOUND]` | `tail_p5|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.5757575757575758` | `0.24` | `0.29333333333333333` | `0.36187659684259027` |
| `[ORACLE_UPPER_BOUND]` | `tail_p10|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.5985401459854015` | `0.18` | `0.30666666666666664` | `0.3442592925674462` |
| `[ORACLE_UPPER_BOUND]` | `tail_p10|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.607773851590106` | `0.14` | `0.3233333333333333` | `0.34766582797939316` |
| `[ORACLE_UPPER_BOUND]` | `tail_p10|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.6122448979591837` | `0.1` | `0.3466666666666667` | `0.34979667039881746` |
| `[ORACLE_UPPER_BOUND]` | `tail_p10|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.5906040268456376` | `0.12` | `0.36666666666666664` | `0.3501947911386747` |
| `[ORACLE_UPPER_BOUND]` | `tail_p25|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.6213592233009708` | `0.36` | `0.14` | `0.3562686469574779` |
| `[ORACLE_UPPER_BOUND]` | `tail_p25|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.6343283582089553` | `0.15` | `0.27666666666666667` | `0.3469388191141947` |
| `[ORACLE_UPPER_BOUND]` | `tail_p25|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.6433566433566433` | `0.08` | `0.31333333333333335` | `0.34801605390820434` |
| `[ORACLE_UPPER_BOUND]` | `tail_p25|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.6072607260726073` | `0.08` | `0.37` | `0.3485832135152539` |
#### python / full_only / 1B_full
| tag | source | F1 | FRR | FAR | threshold |
| --- | --- | --- | --- | --- | --- |
| `[ORACLE_UPPER_BOUND]` | `seed0_mixed_scores_fit_on_all_holdout_labels` | `0.7109004739336493` | `0.25` | `0.12` | `0.5251586013940569` |
| `[ORACLE_UPPER_BOUND]` | `modal_recipe_repeated_oof` | `0.7450980392156863` | `0.24` | `0.09333333333333334` | `0.5213838923594908` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.7264150943396226` | `0.23` | `0.11666666666666667` | `0.5302892168550384` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.7289719626168224` | `0.22` | `0.12` | `0.5345332150693148` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_clip_polboost|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.7123287671232876` | `0.22` | `0.13666666666666666` | `0.5469042594908831` |
| `[ORACLE_UPPER_BOUND]` | `polarity_v2_subset|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.6523605150214592` | `0.24` | `0.19` | `0.29680916932824825` |
| `[ORACLE_UPPER_BOUND]` | `base_repaired|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.5732484076433121` | `0.1` | `0.41333333333333333` | `0.42379305581965276` |
| `[ORACLE_UPPER_BOUND]` | `f2_l2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.5555555555555556` | `0.15` | `0.4033333333333333` | `0.34979198724764127` |
| `[ORACLE_UPPER_BOUND]` | `tail_p3|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.5443037974683544` | `0.14` | `0.43333333333333335` | `0.34904214845088466` |
| `[ORACLE_UPPER_BOUND]` | `tail_p5|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.5576923076923077` | `0.13` | `0.4166666666666667` | `0.3491605190093569` |
| `[ORACLE_UPPER_BOUND]` | `tail_p10|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.554140127388535` | `0.13` | `0.42333333333333334` | `0.3507585206141468` |
| `[ORACLE_UPPER_BOUND]` | `tail_p25|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.56` | `0.09` | `0.44666666666666666` | `0.34548388894612353` |
#### python / clauses / 1B_full
| tag | source | F1 | FRR | FAR | threshold |
| --- | --- | --- | --- | --- | --- |
| `[ORACLE_UPPER_BOUND]` | `seed0_mixed_scores_fit_on_all_holdout_labels` | `0.7172995780590717` | `0.15` | `0.17333333333333334` | `0.4686274390197004` |
| `[ORACLE_UPPER_BOUND]` | `modal_recipe_repeated_oof` | `0.819047619047619` | `0.14` | `0.08` | `0.46080516855669196` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.7359307359307359` | `0.15` | `0.15333333333333332` | `0.48618916152273445` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.7644444444444445` | `0.14` | `0.13` | `0.4941170647101286` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.7822222222222223` | `0.12` | `0.12333333333333334` | `0.5019222349581797` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.7647058823529411` | `0.22` | `0.08666666666666667` | `0.518384485930422` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.7381974248927039` | `0.14` | `0.15666666666666668` | `0.48229949127661537` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.7631578947368421` | `0.13` | `0.13666666666666666` | `0.49075576053012526` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.7787610619469026` | `0.12` | `0.12666666666666668` | `0.5020370144804656` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.7586206896551724` | `0.23` | `0.08666666666666667` | `0.5232565930294945` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_clip_polboost|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.7296137339055794` | `0.15` | `0.16` | `0.4767438533282467` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_clip_polboost|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.7606837606837606` | `0.11` | `0.15` | `0.48715453409553744` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_clip_polboost|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.7713004484304933` | `0.14` | `0.12333333333333334` | `0.5057379359663864` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_clip_polboost|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.7586206896551724` | `0.23` | `0.08666666666666667` | `0.5316167269283971` |
| `[ORACLE_UPPER_BOUND]` | `polarity_v2_subset|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.6527196652719666` | `0.22` | `0.20333333333333334` | `0.20526462735434775` |
| `[ORACLE_UPPER_BOUND]` | `polarity_v2_subset|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.6942148760330579` | `0.16` | `0.19333333333333333` | `0.21563031822938306` |
| `[ORACLE_UPPER_BOUND]` | `polarity_v2_subset|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.7154471544715447` | `0.12` | `0.19333333333333333` | `0.2312727175901073` |
| `[ORACLE_UPPER_BOUND]` | `polarity_v2_subset|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.7` | `0.23` | `0.14333333333333334` | `0.2688458049918101` |
| `[ORACLE_UPPER_BOUND]` | `base_repaired|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.5661538461538461` | `0.08` | `0.44333333333333336` | `0.5672622251570931` |
| `[ORACLE_UPPER_BOUND]` | `base_repaired|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.6029411764705882` | `0.18` | `0.3` | `0.5813048429434632` |
| `[ORACLE_UPPER_BOUND]` | `base_repaired|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.6299212598425197` | `0.2` | `0.24666666666666667` | `0.5691420932386784` |
| `[ORACLE_UPPER_BOUND]` | `base_repaired|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.6122448979591837` | `0.25` | `0.23333333333333334` | `0.5438270518110039` |
| `[ORACLE_UPPER_BOUND]` | `f2_l2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.6556016597510373` | `0.21` | `0.20666666666666667` | `0.34987879975091507` |
| `[ORACLE_UPPER_BOUND]` | `f2_l2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.6825396825396826` | `0.14` | `0.22` | `0.3516596501900516` |
| `[ORACLE_UPPER_BOUND]` | `f2_l2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.6551724137931034` | `0.24` | `0.18666666666666668` | `0.35712292544519053` |
| `[ORACLE_UPPER_BOUND]` | `f2_l2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.5859375` | `0.25` | `0.27` | `0.3577739380370541` |
| `[ORACLE_UPPER_BOUND]` | `tail_p3|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.5629139072847682` | `0.15` | `0.39` | `0.34050872373695945` |
| `[ORACLE_UPPER_BOUND]` | `tail_p3|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.5748987854251012` | `0.29` | `0.25333333333333335` | `0.3555790223561034` |
| `[ORACLE_UPPER_BOUND]` | `tail_p3|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.5746268656716418` | `0.23` | `0.30333333333333334` | `0.3543173806215518` |
| `[ORACLE_UPPER_BOUND]` | `tail_p3|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.5704225352112676` | `0.19` | `0.3433333333333333` | `0.355993816633399` |
| `[ORACLE_UPPER_BOUND]` | `tail_p5|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.5886792452830188` | `0.22` | `0.29` | `0.3478485921719418` |
| `[ORACLE_UPPER_BOUND]` | `tail_p5|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.5963636363636363` | `0.18` | `0.31` | `0.34955312794561316` |
| `[ORACLE_UPPER_BOUND]` | `tail_p5|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.5984251968503937` | `0.24` | `0.26` | `0.3570554389300352` |
| `[ORACLE_UPPER_BOUND]` | `tail_p5|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.5757575757575758` | `0.24` | `0.29333333333333333` | `0.36187659684259027` |
| `[ORACLE_UPPER_BOUND]` | `tail_p10|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.5985401459854015` | `0.18` | `0.30666666666666664` | `0.3442592925674462` |
| `[ORACLE_UPPER_BOUND]` | `tail_p10|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.607773851590106` | `0.14` | `0.3233333333333333` | `0.34766582797939316` |
| `[ORACLE_UPPER_BOUND]` | `tail_p10|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.6122448979591837` | `0.1` | `0.3466666666666667` | `0.34979667039881746` |
| `[ORACLE_UPPER_BOUND]` | `tail_p10|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.5906040268456376` | `0.12` | `0.36666666666666664` | `0.3501947911386747` |
| `[ORACLE_UPPER_BOUND]` | `tail_p25|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.6213592233009708` | `0.36` | `0.14` | `0.3562686469574779` |
| `[ORACLE_UPPER_BOUND]` | `tail_p25|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.6343283582089553` | `0.15` | `0.27666666666666667` | `0.3469388191141947` |
| `[ORACLE_UPPER_BOUND]` | `tail_p25|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.6433566433566433` | `0.08` | `0.31333333333333335` | `0.34801605390820434` |
| `[ORACLE_UPPER_BOUND]` | `tail_p25|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.6072607260726073` | `0.08` | `0.37` | `0.3485832135152539` |
#### python / full_only / 1B_full_v3
| tag | source | F1 | FRR | FAR | threshold |
| --- | --- | --- | --- | --- | --- |
| `[ORACLE_UPPER_BOUND]` | `seed0_mixed_scores_fit_on_all_holdout_labels` | `0.7219512195121951` | `0.26` | `0.10333333333333333` | `0.5295689473964872` |
| `[ORACLE_UPPER_BOUND]` | `modal_recipe_repeated_oof` | `0.7203791469194313` | `0.24` | `0.11666666666666667` | `0.5265841512192679` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.7096774193548387` | `0.23` | `0.13333333333333333` | `0.5265841512192679` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.7093596059113301` | `0.28` | `0.10333333333333333` | `0.5376733659303713` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_clip_polboost|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.7053571428571429` | `0.21` | `0.15` | `0.5349582055746153` |
| `[ORACLE_UPPER_BOUND]` | `polarity_v2_subset|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.6592592592592592` | `0.11` | `0.27` | `0.24886366201656474` |
| `[ORACLE_UPPER_BOUND]` | `base_repaired|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.5714285714285714` | `0.14` | `0.38333333333333336` | `0.4372788417868792` |
| `[ORACLE_UPPER_BOUND]` | `f2_l2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.5555555555555556` | `0.15` | `0.4033333333333333` | `0.34979198724764127` |
| `[ORACLE_UPPER_BOUND]` | `tail_p3|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.5443037974683544` | `0.14` | `0.43333333333333335` | `0.34904214845088466` |
| `[ORACLE_UPPER_BOUND]` | `tail_p5|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.5576923076923077` | `0.13` | `0.4166666666666667` | `0.3491605190093569` |
| `[ORACLE_UPPER_BOUND]` | `tail_p10|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.554140127388535` | `0.13` | `0.42333333333333334` | `0.3507585206141468` |
| `[ORACLE_UPPER_BOUND]` | `tail_p25|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.56` | `0.09` | `0.44666666666666666` | `0.34548388894612353` |
#### python / clauses / 1B_full_v3
| tag | source | F1 | FRR | FAR | threshold |
| --- | --- | --- | --- | --- | --- |
| `[ORACLE_UPPER_BOUND]` | `seed0_mixed_scores_fit_on_all_holdout_labels` | `0.7962085308056872` | `0.16` | `0.09` | `0.47299986570348534` |
| `[ORACLE_UPPER_BOUND]` | `modal_recipe_repeated_oof` | `0.8333333333333334` | `0.1` | `0.08666666666666667` | `0.47076087200940464` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.7579908675799086` | `0.17` | `0.12` | `0.4868961903149415` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.7706422018348624` | `0.16` | `0.11333333333333333` | `0.49293523893177243` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.7727272727272727` | `0.15` | `0.11666666666666667` | `0.5015185525617858` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.7559808612440191` | `0.21` | `0.1` | `0.5146159476045348` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.7465437788018433` | `0.19` | `0.12` | `0.4849930159024663` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.7733333333333333` | `0.13` | `0.12666666666666668` | `0.48776557561361106` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.7713004484304933` | `0.14` | `0.12333333333333334` | `0.49981306557206095` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.7551020408163265` | `0.26` | `0.07333333333333333` | `0.5264971268394787` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_clip_polboost|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.7443946188340808` | `0.17` | `0.13333333333333333` | `0.4760926814707027` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_clip_polboost|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.7719298245614035` | `0.12` | `0.13333333333333333` | `0.483601627009156` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_clip_polboost|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.7807017543859649` | `0.11` | `0.13` | `0.4990049488692795` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_clip_polboost|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.7605633802816901` | `0.19` | `0.10666666666666667` | `0.5215869322127238` |
| `[ORACLE_UPPER_BOUND]` | `polarity_v2_subset|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.6787330316742082` | `0.25` | `0.15333333333333332` | `0.20273643854764478` |
| `[ORACLE_UPPER_BOUND]` | `polarity_v2_subset|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.7219512195121951` | `0.26` | `0.10333333333333333` | `0.23420542152049467` |
| `[ORACLE_UPPER_BOUND]` | `polarity_v2_subset|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.7570093457943925` | `0.19` | `0.11` | `0.23939728470396082` |
| `[ORACLE_UPPER_BOUND]` | `polarity_v2_subset|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.7208121827411168` | `0.29` | `0.08666666666666667` | `0.28218359088037315` |
| `[ORACLE_UPPER_BOUND]` | `base_repaired|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.5609756097560976` | `0.08` | `0.4533333333333333` | `0.566904960178859` |
| `[ORACLE_UPPER_BOUND]` | `base_repaired|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.6007604562737643` | `0.21` | `0.28` | `0.5856940841229172` |
| `[ORACLE_UPPER_BOUND]` | `base_repaired|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.6220472440944882` | `0.21` | `0.25` | `0.5665092332469155` |
| `[ORACLE_UPPER_BOUND]` | `base_repaired|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.6025641025641025` | `0.06` | `0.3933333333333333` | `0.48854752248611916` |
| `[ORACLE_UPPER_BOUND]` | `f2_l2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.6556016597510373` | `0.21` | `0.20666666666666667` | `0.34987879975091507` |
| `[ORACLE_UPPER_BOUND]` | `f2_l2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.6825396825396826` | `0.14` | `0.22` | `0.3516596501900516` |
| `[ORACLE_UPPER_BOUND]` | `f2_l2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.6551724137931034` | `0.24` | `0.18666666666666668` | `0.35712292544519053` |
| `[ORACLE_UPPER_BOUND]` | `f2_l2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.5859375` | `0.25` | `0.27` | `0.3577739380370541` |
| `[ORACLE_UPPER_BOUND]` | `tail_p3|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.5629139072847682` | `0.15` | `0.39` | `0.34050872373695945` |
| `[ORACLE_UPPER_BOUND]` | `tail_p3|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.5748987854251012` | `0.29` | `0.25333333333333335` | `0.3555790223561034` |
| `[ORACLE_UPPER_BOUND]` | `tail_p3|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.5746268656716418` | `0.23` | `0.30333333333333334` | `0.3543173806215518` |
| `[ORACLE_UPPER_BOUND]` | `tail_p3|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.5704225352112676` | `0.19` | `0.3433333333333333` | `0.355993816633399` |
| `[ORACLE_UPPER_BOUND]` | `tail_p5|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.5886792452830188` | `0.22` | `0.29` | `0.3478485921719418` |
| `[ORACLE_UPPER_BOUND]` | `tail_p5|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.5963636363636363` | `0.18` | `0.31` | `0.34955312794561316` |
| `[ORACLE_UPPER_BOUND]` | `tail_p5|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.5984251968503937` | `0.24` | `0.26` | `0.3570554389300352` |
| `[ORACLE_UPPER_BOUND]` | `tail_p5|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.5757575757575758` | `0.24` | `0.29333333333333333` | `0.36187659684259027` |
| `[ORACLE_UPPER_BOUND]` | `tail_p10|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.5985401459854015` | `0.18` | `0.30666666666666664` | `0.3442592925674462` |
| `[ORACLE_UPPER_BOUND]` | `tail_p10|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.607773851590106` | `0.14` | `0.3233333333333333` | `0.34766582797939316` |
| `[ORACLE_UPPER_BOUND]` | `tail_p10|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.6122448979591837` | `0.1` | `0.3466666666666667` | `0.34979667039881746` |
| `[ORACLE_UPPER_BOUND]` | `tail_p10|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.5906040268456376` | `0.12` | `0.36666666666666664` | `0.3501947911386747` |
| `[ORACLE_UPPER_BOUND]` | `tail_p25|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.6213592233009708` | `0.36` | `0.14` | `0.3562686469574779` |
| `[ORACLE_UPPER_BOUND]` | `tail_p25|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.6343283582089553` | `0.15` | `0.27666666666666667` | `0.3469388191141947` |
| `[ORACLE_UPPER_BOUND]` | `tail_p25|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.6433566433566433` | `0.08` | `0.31333333333333335` | `0.34801605390820434` |
| `[ORACLE_UPPER_BOUND]` | `tail_p25|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.6072607260726073` | `0.08` | `0.37` | `0.3485832135152539` |
#### receta / full_only / 1B_base_tech
| tag | source | F1 | FRR | FAR | threshold |
| --- | --- | --- | --- | --- | --- |
| `[ORACLE_UPPER_BOUND]` | `seed0_mixed_scores_fit_on_all_holdout_labels` | `0.7014218009478673` | `0.26` | `0.12333333333333334` | `0.521286731252359` |
| `[ORACLE_UPPER_BOUND]` | `modal_recipe_repeated_oof` | `0.7706422018348624` | `0.16` | `0.11333333333333333` | `0.30798228588655296` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.7692307692307693` | `0.1` | `0.14666666666666667` | `0.5147138461513727` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.7711864406779662` | `0.09` | `0.15` | `0.5191598606111604` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_clip_polboost|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.7711864406779662` | `0.09` | `0.15` | `0.5285954046613094` |
| `[ORACLE_UPPER_BOUND]` | `polarity_v2_subset|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.7706422018348624` | `0.16` | `0.11333333333333333` | `0.30798228588655296` |
| `[ORACLE_UPPER_BOUND]` | `base_repaired|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.648854961832061` | `0.15` | `0.25666666666666665` | `0.36613665707604354` |
| `[ORACLE_UPPER_BOUND]` | `f2_l2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.6319702602230484` | `0.15` | `0.28` | `0.32458617741807333` |
| `[ORACLE_UPPER_BOUND]` | `tail_p3|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.6141732283464567` | `0.22` | `0.25333333333333335` | `0.3363862626887389` |
| `[ORACLE_UPPER_BOUND]` | `tail_p5|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.6220472440944882` | `0.21` | `0.25` | `0.3317284689970968` |
| `[ORACLE_UPPER_BOUND]` | `tail_p10|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.6403162055335968` | `0.19` | `0.24` | `0.33172679849942743` |
| `[ORACLE_UPPER_BOUND]` | `tail_p25|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.6390977443609023` | `0.15` | `0.27` | `0.3246892217661505` |
#### receta / clauses / 1B_base_tech
| tag | source | F1 | FRR | FAR | threshold |
| --- | --- | --- | --- | --- | --- |
| `[ORACLE_UPPER_BOUND]` | `seed0_mixed_scores_fit_on_all_holdout_labels` | `0.8715596330275229` | `0.05` | `0.07666666666666666` | `0.4810775075378366` |
| `[ORACLE_UPPER_BOUND]` | `modal_recipe_repeated_oof` | `0.9038461538461539` | `0.06` | `0.04666666666666667` | `0.48924321441314134` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.9038461538461539` | `0.06` | `0.04666666666666667` | `0.48924321441314134` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.896551724137931` | `0.09` | `0.04` | `0.4996847350046622` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.8341232227488151` | `0.12` | `0.07666666666666666` | `0.5050812878690021` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.8018018018018018` | `0.11` | `0.11` | `0.5100009785379394` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.9038461538461539` | `0.06` | `0.04666666666666667` | `0.48737857316434513` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.8952380952380953` | `0.06` | `0.05333333333333334` | `0.49673914822920373` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.8450704225352113` | `0.1` | `0.07666666666666666` | `0.505848439339001` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.8138528138528138` | `0.06` | `0.12333333333333334` | `0.5070645276970254` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_clip_polboost|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.8942307692307693` | `0.07` | `0.05` | `0.4843707282382663` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_clip_polboost|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.8780487804878049` | `0.1` | `0.05` | `0.5025020118793598` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_clip_polboost|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.839622641509434` | `0.11` | `0.07666666666666666` | `0.5107846985161388` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_clip_polboost|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.8054298642533937` | `0.11` | `0.10666666666666667` | `0.5201663035624488` |
| `[ORACLE_UPPER_BOUND]` | `polarity_v2_subset|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.7450980392156863` | `0.24` | `0.09333333333333334` | `0.21568385332767756` |
| `[ORACLE_UPPER_BOUND]` | `polarity_v2_subset|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.8121827411167513` | `0.2` | `0.056666666666666664` | `0.23712532972979775` |
| `[ORACLE_UPPER_BOUND]` | `polarity_v2_subset|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.8108108108108109` | `0.1` | `0.10666666666666667` | `0.23664378261516364` |
| `[ORACLE_UPPER_BOUND]` | `polarity_v2_subset|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.8018018018018018` | `0.11` | `0.11` | `0.2634901365350622` |
| `[ORACLE_UPPER_BOUND]` | `base_repaired|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.6175438596491228` | `0.12` | `0.3233333333333333` | `0.46099254769637676` |
| `[ORACLE_UPPER_BOUND]` | `base_repaired|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.6639004149377593` | `0.2` | `0.20333333333333334` | `0.4779380421429984` |
| `[ORACLE_UPPER_BOUND]` | `base_repaired|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.6889952153110048` | `0.28` | `0.12333333333333334` | `0.4878756146696912` |
| `[ORACLE_UPPER_BOUND]` | `base_repaired|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.6755555555555556` | `0.24` | `0.16333333333333333` | `0.45517005964250234` |
| `[ORACLE_UPPER_BOUND]` | `f2_l2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.6951871657754011` | `0.35` | `0.07333333333333333` | `0.34436050539188146` |
| `[ORACLE_UPPER_BOUND]` | `f2_l2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.7326732673267327` | `0.26` | `0.09333333333333334` | `0.3452034485873323` |
| `[ORACLE_UPPER_BOUND]` | `f2_l2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.6976744186046512` | `0.25` | `0.13333333333333333` | `0.3451382465527102` |
| `[ORACLE_UPPER_BOUND]` | `f2_l2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.6615384615384615` | `0.14` | `0.24666666666666667` | `0.33001046707757503` |
| `[ORACLE_UPPER_BOUND]` | `tail_p3|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.587360594795539` | `0.21` | `0.3` | `0.3300886492869601` |
| `[ORACLE_UPPER_BOUND]` | `tail_p3|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.6212121212121212` | `0.18` | `0.2733333333333333` | `0.332096399139887` |
| `[ORACLE_UPPER_BOUND]` | `tail_p3|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.6509803921568628` | `0.17` | `0.24` | `0.3346428645627744` |
| `[ORACLE_UPPER_BOUND]` | `tail_p3|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.6353790613718412` | `0.12` | `0.2966666666666667` | `0.3255302470608496` |
| `[ORACLE_UPPER_BOUND]` | `tail_p5|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.5992217898832685` | `0.23` | `0.26666666666666666` | `0.3315225526913693` |
| `[ORACLE_UPPER_BOUND]` | `tail_p5|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.6360424028268551` | `0.1` | `0.31` | `0.32617935498924955` |
| `[ORACLE_UPPER_BOUND]` | `tail_p5|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.6751054852320675` | `0.2` | `0.19` | `0.3384010629895189` |
| `[ORACLE_UPPER_BOUND]` | `tail_p5|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.658008658008658` | `0.24` | `0.18333333333333332` | `0.3427350362640315` |
| `[ORACLE_UPPER_BOUND]` | `tail_p10|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.6297872340425532` | `0.26` | `0.20333333333333334` | `0.33548133048237533` |
| `[ORACLE_UPPER_BOUND]` | `tail_p10|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.68` | `0.32` | `0.10666666666666667` | `0.3439151000410851` |
| `[ORACLE_UPPER_BOUND]` | `tail_p10|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.6812227074235808` | `0.22` | `0.17` | `0.34003492765342713` |
| `[ORACLE_UPPER_BOUND]` | `tail_p10|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.6639344262295082` | `0.19` | `0.21` | `0.33616920582802745` |
| `[ORACLE_UPPER_BOUND]` | `tail_p25|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.672645739910314` | `0.25` | `0.16` | `0.33732205208530053` |
| `[ORACLE_UPPER_BOUND]` | `tail_p25|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.7238095238095238` | `0.24` | `0.11333333333333333` | `0.34173471757869883` |
| `[ORACLE_UPPER_BOUND]` | `tail_p25|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.6991150442477876` | `0.21` | `0.15666666666666668` | `0.34060382411684087` |
| `[ORACLE_UPPER_BOUND]` | `tail_p25|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.675` | `0.19` | `0.19666666666666666` | `0.33687532687531896` |
#### receta / full_only / 1B_base_tech_noise
| tag | source | F1 | FRR | FAR | threshold |
| --- | --- | --- | --- | --- | --- |
| `[ORACLE_UPPER_BOUND]` | `seed0_mixed_scores_fit_on_all_holdout_labels` | `0.7069767441860465` | `0.24` | `0.13` | `0.5166247879404232` |
| `[ORACLE_UPPER_BOUND]` | `modal_recipe_repeated_oof` | `0.7711864406779662` | `0.09` | `0.15` | `0.5183418551599825` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.7647058823529411` | `0.09` | `0.15666666666666668` | `0.5080326722137896` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.7679324894514767` | `0.09` | `0.15333333333333332` | `0.5130222111855745` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_clip_polboost|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.7711864406779662` | `0.09` | `0.15` | `0.5183418551599825` |
| `[ORACLE_UPPER_BOUND]` | `polarity_v2_subset|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.7649769585253456` | `0.17` | `0.11333333333333333` | `0.3063605845738084` |
| `[ORACLE_UPPER_BOUND]` | `base_repaired|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.6541353383458647` | `0.13` | `0.2633333333333333` | `0.3611029699905208` |
| `[ORACLE_UPPER_BOUND]` | `f2_l2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.6319702602230484` | `0.15` | `0.28` | `0.32458617741807333` |
| `[ORACLE_UPPER_BOUND]` | `tail_p3|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.6141732283464567` | `0.22` | `0.25333333333333335` | `0.3363862626887389` |
| `[ORACLE_UPPER_BOUND]` | `tail_p5|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.6220472440944882` | `0.21` | `0.25` | `0.3317284689970968` |
| `[ORACLE_UPPER_BOUND]` | `tail_p10|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.6403162055335968` | `0.19` | `0.24` | `0.33172679849942743` |
| `[ORACLE_UPPER_BOUND]` | `tail_p25|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.6390977443609023` | `0.15` | `0.27` | `0.3246892217661505` |
#### receta / clauses / 1B_base_tech_noise
| tag | source | F1 | FRR | FAR | threshold |
| --- | --- | --- | --- | --- | --- |
| `[ORACLE_UPPER_BOUND]` | `seed0_mixed_scores_fit_on_all_holdout_labels` | `0.8955223880597015` | `0.1` | `0.03666666666666667` | `0.4778676720700513` |
| `[ORACLE_UPPER_BOUND]` | `modal_recipe_repeated_oof` | `0.9054726368159204` | `0.09` | `0.03333333333333333` | `0.4753366542900339` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.9019607843137255` | `0.08` | `0.04` | `0.488530739225166` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.8878048780487805` | `0.09` | `0.04666666666666667` | `0.49618432323524186` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.8356807511737089` | `0.11` | `0.08` | `0.5010622324177298` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.8103448275862069` | `0.06` | `0.12666666666666668` | `0.49951312677165594` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.9038461538461539` | `0.06` | `0.04666666666666667` | `0.48613437385680014` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.8837209302325582` | `0.05` | `0.06666666666666667` | `0.4911758433559453` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.8407079646017699` | `0.05` | `0.10333333333333333` | `0.4951480661299046` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.8173913043478261` | `0.06` | `0.12` | `0.5029392721872841` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_clip_polboost|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.900990099009901` | `0.09` | `0.03666666666666667` | `0.48441146232794824` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_clip_polboost|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.883495145631068` | `0.09` | `0.05` | `0.4946743957321289` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_clip_polboost|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.8387096774193549` | `0.09` | `0.08666666666666667` | `0.5030638780286258` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_clip_polboost|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.8070175438596491` | `0.08` | `0.12` | `0.5064500615613043` |
| `[ORACLE_UPPER_BOUND]` | `polarity_v2_subset|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.7307692307692307` | `0.24` | `0.10666666666666667` | `0.21112064171655234` |
| `[ORACLE_UPPER_BOUND]` | `polarity_v2_subset|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.8` | `0.14` | `0.09666666666666666` | `0.22214984784196737` |
| `[ORACLE_UPPER_BOUND]` | `polarity_v2_subset|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.8235294117647058` | `0.09` | `0.1` | `0.23817853028439218` |
| `[ORACLE_UPPER_BOUND]` | `polarity_v2_subset|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.7981651376146789` | `0.13` | `0.10333333333333333` | `0.27133322038047264` |
| `[ORACLE_UPPER_BOUND]` | `base_repaired|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.6186440677966102` | `0.27` | `0.21` | `0.49917795278951915` |
| `[ORACLE_UPPER_BOUND]` | `base_repaired|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.6720647773279352` | `0.17` | `0.21333333333333335` | `0.47442329744807676` |
| `[ORACLE_UPPER_BOUND]` | `base_repaired|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.6916666666666667` | `0.17` | `0.19` | `0.4648599821625533` |
| `[ORACLE_UPPER_BOUND]` | `base_repaired|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.6695652173913044` | `0.23` | `0.17666666666666667` | `0.44847935751040424` |
| `[ORACLE_UPPER_BOUND]` | `f2_l2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.6951871657754011` | `0.35` | `0.07333333333333333` | `0.34436050539188146` |
| `[ORACLE_UPPER_BOUND]` | `f2_l2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.7326732673267327` | `0.26` | `0.09333333333333334` | `0.3452034485873323` |
| `[ORACLE_UPPER_BOUND]` | `f2_l2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.6976744186046512` | `0.25` | `0.13333333333333333` | `0.3451382465527102` |
| `[ORACLE_UPPER_BOUND]` | `f2_l2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.6615384615384615` | `0.14` | `0.24666666666666667` | `0.33001046707757503` |
| `[ORACLE_UPPER_BOUND]` | `tail_p3|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.587360594795539` | `0.21` | `0.3` | `0.3300886492869601` |
| `[ORACLE_UPPER_BOUND]` | `tail_p3|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.6212121212121212` | `0.18` | `0.2733333333333333` | `0.332096399139887` |
| `[ORACLE_UPPER_BOUND]` | `tail_p3|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.6509803921568628` | `0.17` | `0.24` | `0.3346428645627744` |
| `[ORACLE_UPPER_BOUND]` | `tail_p3|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.6353790613718412` | `0.12` | `0.2966666666666667` | `0.3255302470608496` |
| `[ORACLE_UPPER_BOUND]` | `tail_p5|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.5992217898832685` | `0.23` | `0.26666666666666666` | `0.3315225526913693` |
| `[ORACLE_UPPER_BOUND]` | `tail_p5|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.6360424028268551` | `0.1` | `0.31` | `0.32617935498924955` |
| `[ORACLE_UPPER_BOUND]` | `tail_p5|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.6751054852320675` | `0.2` | `0.19` | `0.3384010629895189` |
| `[ORACLE_UPPER_BOUND]` | `tail_p5|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.658008658008658` | `0.24` | `0.18333333333333332` | `0.3427350362640315` |
| `[ORACLE_UPPER_BOUND]` | `tail_p10|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.6297872340425532` | `0.26` | `0.20333333333333334` | `0.33548133048237533` |
| `[ORACLE_UPPER_BOUND]` | `tail_p10|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.68` | `0.32` | `0.10666666666666667` | `0.3439151000410851` |
| `[ORACLE_UPPER_BOUND]` | `tail_p10|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.6812227074235808` | `0.22` | `0.17` | `0.34003492765342713` |
| `[ORACLE_UPPER_BOUND]` | `tail_p10|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.6639344262295082` | `0.19` | `0.21` | `0.33616920582802745` |
| `[ORACLE_UPPER_BOUND]` | `tail_p25|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.672645739910314` | `0.25` | `0.16` | `0.33732205208530053` |
| `[ORACLE_UPPER_BOUND]` | `tail_p25|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.7238095238095238` | `0.24` | `0.11333333333333333` | `0.34173471757869883` |
| `[ORACLE_UPPER_BOUND]` | `tail_p25|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.6991150442477876` | `0.21` | `0.15666666666666668` | `0.34060382411684087` |
| `[ORACLE_UPPER_BOUND]` | `tail_p25|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.675` | `0.19` | `0.19666666666666666` | `0.33687532687531896` |
#### receta / full_only / 1B_full
| tag | source | F1 | FRR | FAR | threshold |
| --- | --- | --- | --- | --- | --- |
| `[ORACLE_UPPER_BOUND]` | `seed0_mixed_scores_fit_on_all_holdout_labels` | `0.7698744769874477` | `0.08` | `0.15666666666666668` | `0.5086507218671111` |
| `[ORACLE_UPPER_BOUND]` | `modal_recipe_repeated_oof` | `0.7698744769874477` | `0.08` | `0.15666666666666668` | `0.5086507218671111` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.7586206896551724` | `0.12` | `0.14666666666666667` | `0.509943829974776` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.7606837606837606` | `0.11` | `0.15` | `0.5123062569409177` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_clip_polboost|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.7698744769874477` | `0.08` | `0.15666666666666668` | `0.5086507218671111` |
| `[ORACLE_UPPER_BOUND]` | `polarity_v2_subset|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.7532467532467533` | `0.13` | `0.14666666666666667` | `0.2790957856800876` |
| `[ORACLE_UPPER_BOUND]` | `base_repaired|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.6496350364963503` | `0.11` | `0.2833333333333333` | `0.3522222261026485` |
| `[ORACLE_UPPER_BOUND]` | `f2_l2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.6319702602230484` | `0.15` | `0.28` | `0.32458617741807333` |
| `[ORACLE_UPPER_BOUND]` | `tail_p3|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.6141732283464567` | `0.22` | `0.25333333333333335` | `0.3363862626887389` |
| `[ORACLE_UPPER_BOUND]` | `tail_p5|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.6220472440944882` | `0.21` | `0.25` | `0.3317284689970968` |
| `[ORACLE_UPPER_BOUND]` | `tail_p10|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.6403162055335968` | `0.19` | `0.24` | `0.33172679849942743` |
| `[ORACLE_UPPER_BOUND]` | `tail_p25|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.6390977443609023` | `0.15` | `0.27` | `0.3246892217661505` |
#### receta / clauses / 1B_full
| tag | source | F1 | FRR | FAR | threshold |
| --- | --- | --- | --- | --- | --- |
| `[ORACLE_UPPER_BOUND]` | `seed0_mixed_scores_fit_on_all_holdout_labels` | `0.8666666666666667` | `0.09` | `0.06333333333333334` | `0.4795977288068465` |
| `[ORACLE_UPPER_BOUND]` | `modal_recipe_repeated_oof` | `0.900523560209424` | `0.14` | `0.016666666666666666` | `0.4917252746734227` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.900523560209424` | `0.14` | `0.016666666666666666` | `0.4917252746734227` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.8730964467005076` | `0.14` | `0.03666666666666667` | `0.4970234558642494` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.8285714285714286` | `0.13` | `0.07666666666666666` | `0.49988256867594016` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.7913043478260869` | `0.09` | `0.13` | `0.4972933583927398` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.8932038834951457` | `0.08` | `0.04666666666666667` | `0.48155786903325787` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.8792270531400966` | `0.09` | `0.05333333333333334` | `0.49248259936617145` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.8333333333333334` | `0.05` | `0.11` | `0.48826111901601865` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.7981220657276995` | `0.15` | `0.09333333333333334` | `0.5122375533328796` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_clip_polboost|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.8944723618090452` | `0.11` | `0.03333333333333333` | `0.4829290338209932` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_clip_polboost|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.8673469387755102` | `0.15` | `0.03666666666666667` | `0.49777369646118375` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_clip_polboost|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.8269230769230769` | `0.14` | `0.07333333333333333` | `0.5040412068068838` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_clip_polboost|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.7963800904977375` | `0.12` | `0.11` | `0.5088830176995224` |
| `[ORACLE_UPPER_BOUND]` | `polarity_v2_subset|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.7204301075268817` | `0.33` | `0.06333333333333334` | `0.22058498804898227` |
| `[ORACLE_UPPER_BOUND]` | `polarity_v2_subset|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.7777777777777778` | `0.23` | `0.07` | `0.22891978894828274` |
| `[ORACLE_UPPER_BOUND]` | `polarity_v2_subset|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.7981220657276995` | `0.15` | `0.09333333333333334` | `0.2364368051397014` |
| `[ORACLE_UPPER_BOUND]` | `polarity_v2_subset|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.7887323943661971` | `0.16` | `0.09666666666666666` | `0.26735076266143876` |
| `[ORACLE_UPPER_BOUND]` | `base_repaired|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.624` | `0.22` | `0.24` | `0.4854268440852733` |
| `[ORACLE_UPPER_BOUND]` | `base_repaired|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.6818181818181818` | `0.25` | `0.15` | `0.4915186653588214` |
| `[ORACLE_UPPER_BOUND]` | `base_repaired|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.6916666666666667` | `0.17` | `0.19` | `0.4618470410743425` |
| `[ORACLE_UPPER_BOUND]` | `base_repaired|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.6694214876033058` | `0.19` | `0.20333333333333334` | `0.43243924128264144` |
| `[ORACLE_UPPER_BOUND]` | `f2_l2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.6951871657754011` | `0.35` | `0.07333333333333333` | `0.34436050539188146` |
| `[ORACLE_UPPER_BOUND]` | `f2_l2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.7326732673267327` | `0.26` | `0.09333333333333334` | `0.3452034485873323` |
| `[ORACLE_UPPER_BOUND]` | `f2_l2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.6976744186046512` | `0.25` | `0.13333333333333333` | `0.3451382465527102` |
| `[ORACLE_UPPER_BOUND]` | `f2_l2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.6615384615384615` | `0.14` | `0.24666666666666667` | `0.33001046707757503` |
| `[ORACLE_UPPER_BOUND]` | `tail_p3|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.587360594795539` | `0.21` | `0.3` | `0.3300886492869601` |
| `[ORACLE_UPPER_BOUND]` | `tail_p3|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.6212121212121212` | `0.18` | `0.2733333333333333` | `0.332096399139887` |
| `[ORACLE_UPPER_BOUND]` | `tail_p3|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.6509803921568628` | `0.17` | `0.24` | `0.3346428645627744` |
| `[ORACLE_UPPER_BOUND]` | `tail_p3|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.6353790613718412` | `0.12` | `0.2966666666666667` | `0.3255302470608496` |
| `[ORACLE_UPPER_BOUND]` | `tail_p5|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.5992217898832685` | `0.23` | `0.26666666666666666` | `0.3315225526913693` |
| `[ORACLE_UPPER_BOUND]` | `tail_p5|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.6360424028268551` | `0.1` | `0.31` | `0.32617935498924955` |
| `[ORACLE_UPPER_BOUND]` | `tail_p5|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.6751054852320675` | `0.2` | `0.19` | `0.3384010629895189` |
| `[ORACLE_UPPER_BOUND]` | `tail_p5|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.658008658008658` | `0.24` | `0.18333333333333332` | `0.3427350362640315` |
| `[ORACLE_UPPER_BOUND]` | `tail_p10|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.6297872340425532` | `0.26` | `0.20333333333333334` | `0.33548133048237533` |
| `[ORACLE_UPPER_BOUND]` | `tail_p10|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.68` | `0.32` | `0.10666666666666667` | `0.3439151000410851` |
| `[ORACLE_UPPER_BOUND]` | `tail_p10|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.6812227074235808` | `0.22` | `0.17` | `0.34003492765342713` |
| `[ORACLE_UPPER_BOUND]` | `tail_p10|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.6639344262295082` | `0.19` | `0.21` | `0.33616920582802745` |
| `[ORACLE_UPPER_BOUND]` | `tail_p25|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.672645739910314` | `0.25` | `0.16` | `0.33732205208530053` |
| `[ORACLE_UPPER_BOUND]` | `tail_p25|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.7238095238095238` | `0.24` | `0.11333333333333333` | `0.34173471757869883` |
| `[ORACLE_UPPER_BOUND]` | `tail_p25|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.6991150442477876` | `0.21` | `0.15666666666666668` | `0.34060382411684087` |
| `[ORACLE_UPPER_BOUND]` | `tail_p25|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.675` | `0.19` | `0.19666666666666666` | `0.33687532687531896` |
#### receta / full_only / 1B_full_v3
| tag | source | F1 | FRR | FAR | threshold |
| --- | --- | --- | --- | --- | --- |
| `[ORACLE_UPPER_BOUND]` | `seed0_mixed_scores_fit_on_all_holdout_labels` | `0.772093023255814` | `0.17` | `0.10666666666666667` | `0.29870725022482764` |
| `[ORACLE_UPPER_BOUND]` | `modal_recipe_repeated_oof` | `0.772093023255814` | `0.17` | `0.10666666666666667` | `0.29870725022482764` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.7532467532467533` | `0.13` | `0.14666666666666667` | `0.5051643067552105` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.7606837606837606` | `0.11` | `0.15` | `0.5085293835514015` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_clip_polboost|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.7666666666666667` | `0.08` | `0.16` | `0.5037821248994184` |
| `[ORACLE_UPPER_BOUND]` | `polarity_v2_subset|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.772093023255814` | `0.17` | `0.10666666666666667` | `0.29870725022482764` |
| `[ORACLE_UPPER_BOUND]` | `base_repaired|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.6544117647058824` | `0.11` | `0.27666666666666667` | `0.3551553609751639` |
| `[ORACLE_UPPER_BOUND]` | `f2_l2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.6319702602230484` | `0.15` | `0.28` | `0.32458617741807333` |
| `[ORACLE_UPPER_BOUND]` | `tail_p3|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.6141732283464567` | `0.22` | `0.25333333333333335` | `0.3363862626887389` |
| `[ORACLE_UPPER_BOUND]` | `tail_p5|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.6220472440944882` | `0.21` | `0.25` | `0.3317284689970968` |
| `[ORACLE_UPPER_BOUND]` | `tail_p10|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.6403162055335968` | `0.19` | `0.24` | `0.33172679849942743` |
| `[ORACLE_UPPER_BOUND]` | `tail_p25|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=-` | `0.6390977443609023` | `0.15` | `0.27` | `0.3246892217661505` |
#### receta / clauses / 1B_full_v3
| tag | source | F1 | FRR | FAR | threshold |
| --- | --- | --- | --- | --- | --- |
| `[ORACLE_UPPER_BOUND]` | `seed0_mixed_scores_fit_on_all_holdout_labels` | `0.8527918781725888` | `0.16` | `0.043333333333333335` | `0.48167463715286013` |
| `[ORACLE_UPPER_BOUND]` | `modal_recipe_repeated_oof` | `0.896551724137931` | `0.09` | `0.04` | `0.4848833566463882` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.896551724137931` | `0.09` | `0.04` | `0.4848833566463882` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.8787878787878788` | `0.13` | `0.03666666666666667` | `0.49440234257298765` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.8253968253968254` | `0.22` | `0.03666666666666667` | `0.51048787218177` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.8034934497816594` | `0.08` | `0.12333333333333334` | `0.4960400694976773` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.8975609756097561` | `0.08` | `0.043333333333333335` | `0.48012738093749874` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.8811881188118812` | `0.11` | `0.043333333333333335` | `0.4933603657133931` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.8341708542713567` | `0.17` | `0.05333333333333334` | `0.5048047009648222` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_sig_sep2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.7982832618025751` | `0.07` | `0.13333333333333333` | `0.49399625138087483` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_clip_polboost|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.882051282051282` | `0.14` | `0.03` | `0.4822497168402322` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_clip_polboost|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.8775510204081632` | `0.14` | `0.03333333333333333` | `0.4960617097322472` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_clip_polboost|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.8294930875576036` | `0.1` | `0.09` | `0.4959884518756319` |
| `[ORACLE_UPPER_BOUND]` | `dir1024_clip_polboost|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.801762114537445` | `0.09` | `0.12` | `0.5013436642498195` |
| `[ORACLE_UPPER_BOUND]` | `polarity_v2_subset|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.729064039408867` | `0.26` | `0.09666666666666666` | `0.19578400017670491` |
| `[ORACLE_UPPER_BOUND]` | `polarity_v2_subset|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.7963800904977375` | `0.12` | `0.11` | `0.20459543691585982` |
| `[ORACLE_UPPER_BOUND]` | `polarity_v2_subset|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.8127853881278538` | `0.11` | `0.1` | `0.22378310665517187` |
| `[ORACLE_UPPER_BOUND]` | `polarity_v2_subset|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.8056872037914692` | `0.15` | `0.08666666666666667` | `0.26871621114563016` |
| `[ORACLE_UPPER_BOUND]` | `base_repaired|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.6403162055335968` | `0.19` | `0.24` | `0.4783960926319102` |
| `[ORACLE_UPPER_BOUND]` | `base_repaired|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.6833333333333333` | `0.18` | `0.19333333333333333` | `0.46956820513728836` |
| `[ORACLE_UPPER_BOUND]` | `base_repaired|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.7035573122529645` | `0.11` | `0.21333333333333335` | `0.44809770253236536` |
| `[ORACLE_UPPER_BOUND]` | `base_repaired|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.6923076923076923` | `0.1` | `0.23333333333333334` | `0.4147871174220405` |
| `[ORACLE_UPPER_BOUND]` | `f2_l2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.6951871657754011` | `0.35` | `0.07333333333333333` | `0.34436050539188146` |
| `[ORACLE_UPPER_BOUND]` | `f2_l2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.7326732673267327` | `0.26` | `0.09333333333333334` | `0.3452034485873323` |
| `[ORACLE_UPPER_BOUND]` | `f2_l2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.6976744186046512` | `0.25` | `0.13333333333333333` | `0.3451382465527102` |
| `[ORACLE_UPPER_BOUND]` | `f2_l2|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.6615384615384615` | `0.14` | `0.24666666666666667` | `0.33001046707757503` |
| `[ORACLE_UPPER_BOUND]` | `tail_p3|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.587360594795539` | `0.21` | `0.3` | `0.3300886492869601` |
| `[ORACLE_UPPER_BOUND]` | `tail_p3|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.6212121212121212` | `0.18` | `0.2733333333333333` | `0.332096399139887` |
| `[ORACLE_UPPER_BOUND]` | `tail_p3|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.6509803921568628` | `0.17` | `0.24` | `0.3346428645627744` |
| `[ORACLE_UPPER_BOUND]` | `tail_p3|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.6353790613718412` | `0.12` | `0.2966666666666667` | `0.3255302470608496` |
| `[ORACLE_UPPER_BOUND]` | `tail_p5|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.5992217898832685` | `0.23` | `0.26666666666666666` | `0.3315225526913693` |
| `[ORACLE_UPPER_BOUND]` | `tail_p5|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.6360424028268551` | `0.1` | `0.31` | `0.32617935498924955` |
| `[ORACLE_UPPER_BOUND]` | `tail_p5|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.6751054852320675` | `0.2` | `0.19` | `0.3384010629895189` |
| `[ORACLE_UPPER_BOUND]` | `tail_p5|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.658008658008658` | `0.24` | `0.18333333333333332` | `0.3427350362640315` |
| `[ORACLE_UPPER_BOUND]` | `tail_p10|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.6297872340425532` | `0.26` | `0.20333333333333334` | `0.33548133048237533` |
| `[ORACLE_UPPER_BOUND]` | `tail_p10|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.68` | `0.32` | `0.10666666666666667` | `0.3439151000410851` |
| `[ORACLE_UPPER_BOUND]` | `tail_p10|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.6812227074235808` | `0.22` | `0.17` | `0.34003492765342713` |
| `[ORACLE_UPPER_BOUND]` | `tail_p10|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.6639344262295082` | `0.19` | `0.21` | `0.33616920582802745` |
| `[ORACLE_UPPER_BOUND]` | `tail_p25|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.20` | `0.672645739910314` | `0.25` | `0.16` | `0.33732205208530053` |
| `[ORACLE_UPPER_BOUND]` | `tail_p25|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.35` | `0.7238095238095238` | `0.24` | `0.11333333333333333` | `0.34173471757869883` |
| `[ORACLE_UPPER_BOUND]` | `tail_p25|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.50` | `0.6991150442477876` | `0.21` | `0.15666666666666668` | `0.34060382411684087` |
| `[ORACLE_UPPER_BOUND]` | `tail_p25|identity|a=0.00|g=-|beta|b=0.00|y=-|r=full_doc|w=0.70` | `0.675` | `0.19` | `0.19666666666666666` | `0.33687532687531896` |

## 7. Subtype deltas

Focus subtypes first. A name that the benchmark file does not contain on that cell is `absent`. The full stored subtype list follows.
| domain | granularity | preset | subtype | category | n | kind | error_rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `python` | `full_only` | `1B_base_tech` | `extreme_short_punct` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.0` |
| `python` | `full_only` | `1B_base_tech` | `homoglyph_zwsp_fullwidth` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `python` | `full_only` | `1B_base_tech` | `near_ood_neighbor` | `HYBRID_BOUNDARY` | `12` | `far` | `0.3333333333333333` |
| `python` | `full_only` | `1B_base_tech` | `panaderia_fermentacion` | `absent` | `absent` | `absent` | `absent` |
| `python` | `full_only` | `1B_base_tech` | `diagnostico_pasteleria_panaderia` | `absent` | `absent` | `absent` | `absent` |
| `python` | `full_only` | `1B_base_tech` | `long_debugging_walkthrough` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.0` |
| `python` | `full_only` | `1B_base_tech` | `smuggle_recipe_footnote` | `absent` | `absent` | `absent` | `absent` |
| `python` | `full_only` | `1B_base_tech` | `dilution_80_20` | `HYBRID_BOUNDARY` | `10` | `far` | `0.5` |
| `python` | `clauses` | `1B_base_tech` | `extreme_short_punct` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.0` |
| `python` | `clauses` | `1B_base_tech` | `homoglyph_zwsp_fullwidth` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `python` | `clauses` | `1B_base_tech` | `near_ood_neighbor` | `HYBRID_BOUNDARY` | `12` | `far` | `0.5` |
| `python` | `clauses` | `1B_base_tech` | `panaderia_fermentacion` | `absent` | `absent` | `absent` | `absent` |
| `python` | `clauses` | `1B_base_tech` | `diagnostico_pasteleria_panaderia` | `absent` | `absent` | `absent` | `absent` |
| `python` | `clauses` | `1B_base_tech` | `long_debugging_walkthrough` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.1` |
| `python` | `clauses` | `1B_base_tech` | `smuggle_recipe_footnote` | `absent` | `absent` | `absent` | `absent` |
| `python` | `clauses` | `1B_base_tech` | `dilution_80_20` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `python` | `full_only` | `1B_base_tech_noise` | `extreme_short_punct` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.0` |
| `python` | `full_only` | `1B_base_tech_noise` | `homoglyph_zwsp_fullwidth` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.08333333333333333` |
| `python` | `full_only` | `1B_base_tech_noise` | `near_ood_neighbor` | `HYBRID_BOUNDARY` | `12` | `far` | `0.3333333333333333` |
| `python` | `full_only` | `1B_base_tech_noise` | `panaderia_fermentacion` | `absent` | `absent` | `absent` | `absent` |
| `python` | `full_only` | `1B_base_tech_noise` | `diagnostico_pasteleria_panaderia` | `absent` | `absent` | `absent` | `absent` |
| `python` | `full_only` | `1B_base_tech_noise` | `long_debugging_walkthrough` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.0` |
| `python` | `full_only` | `1B_base_tech_noise` | `smuggle_recipe_footnote` | `absent` | `absent` | `absent` | `absent` |
| `python` | `full_only` | `1B_base_tech_noise` | `dilution_80_20` | `HYBRID_BOUNDARY` | `10` | `far` | `0.7` |
| `python` | `clauses` | `1B_base_tech_noise` | `extreme_short_punct` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.0` |
| `python` | `clauses` | `1B_base_tech_noise` | `homoglyph_zwsp_fullwidth` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `python` | `clauses` | `1B_base_tech_noise` | `near_ood_neighbor` | `HYBRID_BOUNDARY` | `12` | `far` | `0.5833333333333334` |
| `python` | `clauses` | `1B_base_tech_noise` | `panaderia_fermentacion` | `absent` | `absent` | `absent` | `absent` |
| `python` | `clauses` | `1B_base_tech_noise` | `diagnostico_pasteleria_panaderia` | `absent` | `absent` | `absent` | `absent` |
| `python` | `clauses` | `1B_base_tech_noise` | `long_debugging_walkthrough` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.2` |
| `python` | `clauses` | `1B_base_tech_noise` | `smuggle_recipe_footnote` | `absent` | `absent` | `absent` | `absent` |
| `python` | `clauses` | `1B_base_tech_noise` | `dilution_80_20` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `python` | `full_only` | `1B_full` | `extreme_short_punct` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.0` |
| `python` | `full_only` | `1B_full` | `homoglyph_zwsp_fullwidth` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `python` | `full_only` | `1B_full` | `near_ood_neighbor` | `HYBRID_BOUNDARY` | `12` | `far` | `0.4166666666666667` |
| `python` | `full_only` | `1B_full` | `panaderia_fermentacion` | `absent` | `absent` | `absent` | `absent` |
| `python` | `full_only` | `1B_full` | `diagnostico_pasteleria_panaderia` | `absent` | `absent` | `absent` | `absent` |
| `python` | `full_only` | `1B_full` | `long_debugging_walkthrough` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.0` |
| `python` | `full_only` | `1B_full` | `smuggle_recipe_footnote` | `absent` | `absent` | `absent` | `absent` |
| `python` | `full_only` | `1B_full` | `dilution_80_20` | `HYBRID_BOUNDARY` | `10` | `far` | `0.8` |
| `python` | `clauses` | `1B_full` | `extreme_short_punct` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.0` |
| `python` | `clauses` | `1B_full` | `homoglyph_zwsp_fullwidth` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `python` | `clauses` | `1B_full` | `near_ood_neighbor` | `HYBRID_BOUNDARY` | `12` | `far` | `0.5833333333333334` |
| `python` | `clauses` | `1B_full` | `panaderia_fermentacion` | `absent` | `absent` | `absent` | `absent` |
| `python` | `clauses` | `1B_full` | `diagnostico_pasteleria_panaderia` | `absent` | `absent` | `absent` | `absent` |
| `python` | `clauses` | `1B_full` | `long_debugging_walkthrough` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.4` |
| `python` | `clauses` | `1B_full` | `smuggle_recipe_footnote` | `absent` | `absent` | `absent` | `absent` |
| `python` | `clauses` | `1B_full` | `dilution_80_20` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `python` | `full_only` | `1B_full_v3` | `extreme_short_punct` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.0` |
| `python` | `full_only` | `1B_full_v3` | `homoglyph_zwsp_fullwidth` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `python` | `full_only` | `1B_full_v3` | `near_ood_neighbor` | `HYBRID_BOUNDARY` | `12` | `far` | `0.4166666666666667` |
| `python` | `full_only` | `1B_full_v3` | `panaderia_fermentacion` | `absent` | `absent` | `absent` | `absent` |
| `python` | `full_only` | `1B_full_v3` | `diagnostico_pasteleria_panaderia` | `absent` | `absent` | `absent` | `absent` |
| `python` | `full_only` | `1B_full_v3` | `long_debugging_walkthrough` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.0` |
| `python` | `full_only` | `1B_full_v3` | `smuggle_recipe_footnote` | `absent` | `absent` | `absent` | `absent` |
| `python` | `full_only` | `1B_full_v3` | `dilution_80_20` | `HYBRID_BOUNDARY` | `10` | `far` | `0.9` |
| `python` | `clauses` | `1B_full_v3` | `extreme_short_punct` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.0` |
| `python` | `clauses` | `1B_full_v3` | `homoglyph_zwsp_fullwidth` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `python` | `clauses` | `1B_full_v3` | `near_ood_neighbor` | `HYBRID_BOUNDARY` | `12` | `far` | `0.5833333333333334` |
| `python` | `clauses` | `1B_full_v3` | `panaderia_fermentacion` | `absent` | `absent` | `absent` | `absent` |
| `python` | `clauses` | `1B_full_v3` | `diagnostico_pasteleria_panaderia` | `absent` | `absent` | `absent` | `absent` |
| `python` | `clauses` | `1B_full_v3` | `long_debugging_walkthrough` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.4` |
| `python` | `clauses` | `1B_full_v3` | `smuggle_recipe_footnote` | `absent` | `absent` | `absent` | `absent` |
| `python` | `clauses` | `1B_full_v3` | `dilution_80_20` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `receta` | `full_only` | `1B_base_tech` | `extreme_short_punct` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.0` |
| `receta` | `full_only` | `1B_base_tech` | `homoglyph_zwsp_fullwidth` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.08333333333333333` |
| `receta` | `full_only` | `1B_base_tech` | `near_ood_neighbor` | `HYBRID_BOUNDARY` | `12` | `far` | `0.0` |
| `receta` | `full_only` | `1B_base_tech` | `panaderia_fermentacion` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.6` |
| `receta` | `full_only` | `1B_base_tech` | `diagnostico_pasteleria_panaderia` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.125` |
| `receta` | `full_only` | `1B_base_tech` | `long_debugging_walkthrough` | `absent` | `absent` | `absent` | `absent` |
| `receta` | `full_only` | `1B_base_tech` | `smuggle_recipe_footnote` | `HYBRID_BOUNDARY` | `10` | `far` | `0.8` |
| `receta` | `full_only` | `1B_base_tech` | `dilution_80_20` | `HYBRID_BOUNDARY` | `10` | `far` | `0.7` |
| `receta` | `clauses` | `1B_base_tech` | `extreme_short_punct` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.1` |
| `receta` | `clauses` | `1B_base_tech` | `homoglyph_zwsp_fullwidth` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `receta` | `clauses` | `1B_base_tech` | `near_ood_neighbor` | `HYBRID_BOUNDARY` | `12` | `far` | `0.0` |
| `receta` | `clauses` | `1B_base_tech` | `panaderia_fermentacion` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.3` |
| `receta` | `clauses` | `1B_base_tech` | `diagnostico_pasteleria_panaderia` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.5` |
| `receta` | `clauses` | `1B_base_tech` | `long_debugging_walkthrough` | `absent` | `absent` | `absent` | `absent` |
| `receta` | `clauses` | `1B_base_tech` | `smuggle_recipe_footnote` | `HYBRID_BOUNDARY` | `10` | `far` | `0.2` |
| `receta` | `clauses` | `1B_base_tech` | `dilution_80_20` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `receta` | `full_only` | `1B_base_tech_noise` | `extreme_short_punct` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.0` |
| `receta` | `full_only` | `1B_base_tech_noise` | `homoglyph_zwsp_fullwidth` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `receta` | `full_only` | `1B_base_tech_noise` | `near_ood_neighbor` | `HYBRID_BOUNDARY` | `12` | `far` | `0.0` |
| `receta` | `full_only` | `1B_base_tech_noise` | `panaderia_fermentacion` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.8` |
| `receta` | `full_only` | `1B_base_tech_noise` | `diagnostico_pasteleria_panaderia` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.25` |
| `receta` | `full_only` | `1B_base_tech_noise` | `long_debugging_walkthrough` | `absent` | `absent` | `absent` | `absent` |
| `receta` | `full_only` | `1B_base_tech_noise` | `smuggle_recipe_footnote` | `HYBRID_BOUNDARY` | `10` | `far` | `0.8` |
| `receta` | `full_only` | `1B_base_tech_noise` | `dilution_80_20` | `HYBRID_BOUNDARY` | `10` | `far` | `0.7` |
| `receta` | `clauses` | `1B_base_tech_noise` | `extreme_short_punct` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.0` |
| `receta` | `clauses` | `1B_base_tech_noise` | `homoglyph_zwsp_fullwidth` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `receta` | `clauses` | `1B_base_tech_noise` | `near_ood_neighbor` | `HYBRID_BOUNDARY` | `12` | `far` | `0.0` |
| `receta` | `clauses` | `1B_base_tech_noise` | `panaderia_fermentacion` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.2` |
| `receta` | `clauses` | `1B_base_tech_noise` | `diagnostico_pasteleria_panaderia` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.5` |
| `receta` | `clauses` | `1B_base_tech_noise` | `long_debugging_walkthrough` | `absent` | `absent` | `absent` | `absent` |
| `receta` | `clauses` | `1B_base_tech_noise` | `smuggle_recipe_footnote` | `HYBRID_BOUNDARY` | `10` | `far` | `0.2` |
| `receta` | `clauses` | `1B_base_tech_noise` | `dilution_80_20` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `receta` | `full_only` | `1B_full` | `extreme_short_punct` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.0` |
| `receta` | `full_only` | `1B_full` | `homoglyph_zwsp_fullwidth` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `receta` | `full_only` | `1B_full` | `near_ood_neighbor` | `HYBRID_BOUNDARY` | `12` | `far` | `0.0` |
| `receta` | `full_only` | `1B_full` | `panaderia_fermentacion` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.8` |
| `receta` | `full_only` | `1B_full` | `diagnostico_pasteleria_panaderia` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.25` |
| `receta` | `full_only` | `1B_full` | `long_debugging_walkthrough` | `absent` | `absent` | `absent` | `absent` |
| `receta` | `full_only` | `1B_full` | `smuggle_recipe_footnote` | `HYBRID_BOUNDARY` | `10` | `far` | `0.9` |
| `receta` | `full_only` | `1B_full` | `dilution_80_20` | `HYBRID_BOUNDARY` | `10` | `far` | `0.7` |
| `receta` | `clauses` | `1B_full` | `extreme_short_punct` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.0` |
| `receta` | `clauses` | `1B_full` | `homoglyph_zwsp_fullwidth` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `receta` | `clauses` | `1B_full` | `near_ood_neighbor` | `HYBRID_BOUNDARY` | `12` | `far` | `0.0` |
| `receta` | `clauses` | `1B_full` | `panaderia_fermentacion` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.3` |
| `receta` | `clauses` | `1B_full` | `diagnostico_pasteleria_panaderia` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.5` |
| `receta` | `clauses` | `1B_full` | `long_debugging_walkthrough` | `absent` | `absent` | `absent` | `absent` |
| `receta` | `clauses` | `1B_full` | `smuggle_recipe_footnote` | `HYBRID_BOUNDARY` | `10` | `far` | `0.2` |
| `receta` | `clauses` | `1B_full` | `dilution_80_20` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `receta` | `full_only` | `1B_full_v3` | `extreme_short_punct` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.0` |
| `receta` | `full_only` | `1B_full_v3` | `homoglyph_zwsp_fullwidth` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `receta` | `full_only` | `1B_full_v3` | `near_ood_neighbor` | `HYBRID_BOUNDARY` | `12` | `far` | `0.0` |
| `receta` | `full_only` | `1B_full_v3` | `panaderia_fermentacion` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.6` |
| `receta` | `full_only` | `1B_full_v3` | `diagnostico_pasteleria_panaderia` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.375` |
| `receta` | `full_only` | `1B_full_v3` | `long_debugging_walkthrough` | `absent` | `absent` | `absent` | `absent` |
| `receta` | `full_only` | `1B_full_v3` | `smuggle_recipe_footnote` | `HYBRID_BOUNDARY` | `10` | `far` | `0.9` |
| `receta` | `full_only` | `1B_full_v3` | `dilution_80_20` | `HYBRID_BOUNDARY` | `10` | `far` | `0.8` |
| `receta` | `clauses` | `1B_full_v3` | `extreme_short_punct` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.0` |
| `receta` | `clauses` | `1B_full_v3` | `homoglyph_zwsp_fullwidth` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `receta` | `clauses` | `1B_full_v3` | `near_ood_neighbor` | `HYBRID_BOUNDARY` | `12` | `far` | `0.0` |
| `receta` | `clauses` | `1B_full_v3` | `panaderia_fermentacion` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.3` |
| `receta` | `clauses` | `1B_full_v3` | `diagnostico_pasteleria_panaderia` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.5` |
| `receta` | `clauses` | `1B_full_v3` | `long_debugging_walkthrough` | `absent` | `absent` | `absent` | `absent` |
| `receta` | `clauses` | `1B_full_v3` | `smuggle_recipe_footnote` | `HYBRID_BOUNDARY` | `10` | `far` | `0.2` |
| `receta` | `clauses` | `1B_full_v3` | `dilution_80_20` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
Full subtype breakdown:
| domain | granularity | preset | subtype | category | n | kind | error_rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `python` | `full_only` | `1B_base_tech` | `asyncio_concurrency` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.125` |
| `python` | `full_only` | `1B_base_tech` | `code_snippet` | `IN_DOMAIN_VALID` | `6` | `frr` | `0.3333333333333333` |
| `python` | `full_only` | `1B_base_tech` | `data_structures_oop` | `IN_DOMAIN_VALID` | `6` | `frr` | `0.5` |
| `python` | `full_only` | `1B_base_tech` | `delimiter_escape` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.08333333333333333` |
| `python` | `full_only` | `1B_base_tech` | `dilution_20_80` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `python` | `full_only` | `1B_base_tech` | `dilution_50_50` | `HYBRID_BOUNDARY` | `10` | `far` | `0.1` |
| `python` | `full_only` | `1B_base_tech` | `dilution_80_20` | `HYBRID_BOUNDARY` | `10` | `far` | `0.5` |
| `python` | `full_only` | `1B_base_tech` | `extreme_high_entropy_gibberish` | `ADVERSARIAL_FUZZING` | `7` | `far` | `0.0` |
| `python` | `full_only` | `1B_base_tech` | `extreme_short_punct` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.0` |
| `python` | `full_only` | `1B_base_tech` | `homoglyph_zwsp_fullwidth` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `python` | `full_only` | `1B_base_tech` | `keyword_stuffing_hidden_instruction` | `ADVERSARIAL_FUZZING` | `6` | `far` | `0.3333333333333333` |
| `python` | `full_only` | `1B_base_tech` | `long_architecture_guide` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.0` |
| `python` | `full_only` | `1B_base_tech` | `long_context_flooding` | `ADVERSARIAL_FUZZING` | `6` | `far` | `0.16666666666666666` |
| `python` | `full_only` | `1B_base_tech` | `long_debugging_walkthrough` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.0` |
| `python` | `full_only` | `1B_base_tech` | `near_ood_neighbor` | `HYBRID_BOUNDARY` | `12` | `far` | `0.3333333333333333` |
| `python` | `full_only` | `1B_base_tech` | `obfuscation_base64` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `python` | `full_only` | `1B_base_tech` | `obfuscation_hex_rot13_leet` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.0` |
| `python` | `full_only` | `1B_base_tech` | `ood_architecture_music_hardware` | `OUT_OF_DOMAIN_BENIGN` | `8` | `far` | `0.0` |
| `python` | `full_only` | `1B_base_tech` | `ood_astronomy_geology` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `python` | `full_only` | `1B_base_tech` | `ood_finance_law` | `OUT_OF_DOMAIN_BENIGN` | `12` | `far` | `0.0` |
| `python` | `full_only` | `1B_base_tech` | `ood_history_literature_philosophy` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `python` | `full_only` | `1B_base_tech` | `ood_medicine_biology` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `python` | `full_only` | `1B_base_tech` | `ood_suite2_clinc` | `OUT_OF_DOMAIN_BENIGN` | `40` | `far` | `0.0` |
| `python` | `full_only` | `1B_base_tech` | `ood_travel_weather_sports` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `python` | `full_only` | `1B_base_tech` | `packaging_env` | `IN_DOMAIN_VALID` | `6` | `frr` | `0.16666666666666666` |
| `python` | `full_only` | `1B_base_tech` | `pivot_middle` | `HYBRID_BOUNDARY` | `10` | `far` | `0.8` |
| `python` | `full_only` | `1B_base_tech` | `pivot_prefix` | `HYBRID_BOUNDARY` | `10` | `far` | `0.3` |
| `python` | `full_only` | `1B_base_tech` | `pivot_suffix` | `HYBRID_BOUNDARY` | `10` | `far` | `0.1` |
| `python` | `full_only` | `1B_base_tech` | `polarity_flip_indirect` | `HYBRID_BOUNDARY` | `8` | `far` | `0.25` |
| `python` | `full_only` | `1B_base_tech` | `prompt_injection_jailbreak` | `ADVERSARIAL_FUZZING` | `25` | `far` | `0.28` |
| `python` | `full_only` | `1B_base_tech` | `pytest_testing` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.0` |
| `python` | `full_only` | `1B_base_tech` | `short_idiom_query` | `IN_DOMAIN_VALID` | `20` | `frr` | `0.5` |
| `python` | `full_only` | `1B_base_tech` | `smuggle_comment_docstring` | `HYBRID_BOUNDARY` | `10` | `far` | `0.2` |
| `python` | `full_only` | `1B_base_tech` | `smuggle_json_yaml` | `HYBRID_BOUNDARY` | `10` | `far` | `0.1` |
| `python` | `full_only` | `1B_base_tech` | `stdlib_idiom` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.2` |
| `python` | `full_only` | `1B_base_tech` | `traceback_debugging` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.125` |
| `python` | `full_only` | `1B_base_tech` | `typing_protocol` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.125` |
| `python` | `clauses` | `1B_base_tech` | `asyncio_concurrency` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.25` |
| `python` | `clauses` | `1B_base_tech` | `code_snippet` | `IN_DOMAIN_VALID` | `6` | `frr` | `0.5` |
| `python` | `clauses` | `1B_base_tech` | `data_structures_oop` | `IN_DOMAIN_VALID` | `6` | `frr` | `0.16666666666666666` |
| `python` | `clauses` | `1B_base_tech` | `delimiter_escape` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.08333333333333333` |
| `python` | `clauses` | `1B_base_tech` | `dilution_20_80` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `python` | `clauses` | `1B_base_tech` | `dilution_50_50` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `python` | `clauses` | `1B_base_tech` | `dilution_80_20` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `python` | `clauses` | `1B_base_tech` | `extreme_high_entropy_gibberish` | `ADVERSARIAL_FUZZING` | `7` | `far` | `0.0` |
| `python` | `clauses` | `1B_base_tech` | `extreme_short_punct` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.0` |
| `python` | `clauses` | `1B_base_tech` | `homoglyph_zwsp_fullwidth` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `python` | `clauses` | `1B_base_tech` | `keyword_stuffing_hidden_instruction` | `ADVERSARIAL_FUZZING` | `6` | `far` | `0.16666666666666666` |
| `python` | `clauses` | `1B_base_tech` | `long_architecture_guide` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.3` |
| `python` | `clauses` | `1B_base_tech` | `long_context_flooding` | `ADVERSARIAL_FUZZING` | `6` | `far` | `0.0` |
| `python` | `clauses` | `1B_base_tech` | `long_debugging_walkthrough` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.1` |
| `python` | `clauses` | `1B_base_tech` | `near_ood_neighbor` | `HYBRID_BOUNDARY` | `12` | `far` | `0.5` |
| `python` | `clauses` | `1B_base_tech` | `obfuscation_base64` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `python` | `clauses` | `1B_base_tech` | `obfuscation_hex_rot13_leet` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.0` |
| `python` | `clauses` | `1B_base_tech` | `ood_architecture_music_hardware` | `OUT_OF_DOMAIN_BENIGN` | `8` | `far` | `0.0` |
| `python` | `clauses` | `1B_base_tech` | `ood_astronomy_geology` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `python` | `clauses` | `1B_base_tech` | `ood_finance_law` | `OUT_OF_DOMAIN_BENIGN` | `12` | `far` | `0.0` |
| `python` | `clauses` | `1B_base_tech` | `ood_history_literature_philosophy` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `python` | `clauses` | `1B_base_tech` | `ood_medicine_biology` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `python` | `clauses` | `1B_base_tech` | `ood_suite2_clinc` | `OUT_OF_DOMAIN_BENIGN` | `40` | `far` | `0.0` |
| `python` | `clauses` | `1B_base_tech` | `ood_travel_weather_sports` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `python` | `clauses` | `1B_base_tech` | `packaging_env` | `IN_DOMAIN_VALID` | `6` | `frr` | `0.0` |
| `python` | `clauses` | `1B_base_tech` | `pivot_middle` | `HYBRID_BOUNDARY` | `10` | `far` | `0.2` |
| `python` | `clauses` | `1B_base_tech` | `pivot_prefix` | `HYBRID_BOUNDARY` | `10` | `far` | `0.1` |
| `python` | `clauses` | `1B_base_tech` | `pivot_suffix` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `python` | `clauses` | `1B_base_tech` | `polarity_flip_indirect` | `HYBRID_BOUNDARY` | `8` | `far` | `0.125` |
| `python` | `clauses` | `1B_base_tech` | `prompt_injection_jailbreak` | `ADVERSARIAL_FUZZING` | `25` | `far` | `0.28` |
| `python` | `clauses` | `1B_base_tech` | `pytest_testing` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.0` |
| `python` | `clauses` | `1B_base_tech` | `short_idiom_query` | `IN_DOMAIN_VALID` | `20` | `frr` | `0.25` |
| `python` | `clauses` | `1B_base_tech` | `smuggle_comment_docstring` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `python` | `clauses` | `1B_base_tech` | `smuggle_json_yaml` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `python` | `clauses` | `1B_base_tech` | `stdlib_idiom` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.1` |
| `python` | `clauses` | `1B_base_tech` | `traceback_debugging` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.125` |
| `python` | `clauses` | `1B_base_tech` | `typing_protocol` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.125` |
| `python` | `full_only` | `1B_base_tech_noise` | `asyncio_concurrency` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.125` |
| `python` | `full_only` | `1B_base_tech_noise` | `code_snippet` | `IN_DOMAIN_VALID` | `6` | `frr` | `0.3333333333333333` |
| `python` | `full_only` | `1B_base_tech_noise` | `data_structures_oop` | `IN_DOMAIN_VALID` | `6` | `frr` | `0.3333333333333333` |
| `python` | `full_only` | `1B_base_tech_noise` | `delimiter_escape` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.16666666666666666` |
| `python` | `full_only` | `1B_base_tech_noise` | `dilution_20_80` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `python` | `full_only` | `1B_base_tech_noise` | `dilution_50_50` | `HYBRID_BOUNDARY` | `10` | `far` | `0.3` |
| `python` | `full_only` | `1B_base_tech_noise` | `dilution_80_20` | `HYBRID_BOUNDARY` | `10` | `far` | `0.7` |
| `python` | `full_only` | `1B_base_tech_noise` | `extreme_high_entropy_gibberish` | `ADVERSARIAL_FUZZING` | `7` | `far` | `0.0` |
| `python` | `full_only` | `1B_base_tech_noise` | `extreme_short_punct` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.0` |
| `python` | `full_only` | `1B_base_tech_noise` | `homoglyph_zwsp_fullwidth` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.08333333333333333` |
| `python` | `full_only` | `1B_base_tech_noise` | `keyword_stuffing_hidden_instruction` | `ADVERSARIAL_FUZZING` | `6` | `far` | `0.3333333333333333` |
| `python` | `full_only` | `1B_base_tech_noise` | `long_architecture_guide` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.0` |
| `python` | `full_only` | `1B_base_tech_noise` | `long_context_flooding` | `ADVERSARIAL_FUZZING` | `6` | `far` | `0.3333333333333333` |
| `python` | `full_only` | `1B_base_tech_noise` | `long_debugging_walkthrough` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.0` |
| `python` | `full_only` | `1B_base_tech_noise` | `near_ood_neighbor` | `HYBRID_BOUNDARY` | `12` | `far` | `0.3333333333333333` |
| `python` | `full_only` | `1B_base_tech_noise` | `obfuscation_base64` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `python` | `full_only` | `1B_base_tech_noise` | `obfuscation_hex_rot13_leet` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.0` |
| `python` | `full_only` | `1B_base_tech_noise` | `ood_architecture_music_hardware` | `OUT_OF_DOMAIN_BENIGN` | `8` | `far` | `0.0` |
| `python` | `full_only` | `1B_base_tech_noise` | `ood_astronomy_geology` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `python` | `full_only` | `1B_base_tech_noise` | `ood_finance_law` | `OUT_OF_DOMAIN_BENIGN` | `12` | `far` | `0.0` |
| `python` | `full_only` | `1B_base_tech_noise` | `ood_history_literature_philosophy` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `python` | `full_only` | `1B_base_tech_noise` | `ood_medicine_biology` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `python` | `full_only` | `1B_base_tech_noise` | `ood_suite2_clinc` | `OUT_OF_DOMAIN_BENIGN` | `40` | `far` | `0.0` |
| `python` | `full_only` | `1B_base_tech_noise` | `ood_travel_weather_sports` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `python` | `full_only` | `1B_base_tech_noise` | `packaging_env` | `IN_DOMAIN_VALID` | `6` | `frr` | `0.0` |
| `python` | `full_only` | `1B_base_tech_noise` | `pivot_middle` | `HYBRID_BOUNDARY` | `10` | `far` | `0.9` |
| `python` | `full_only` | `1B_base_tech_noise` | `pivot_prefix` | `HYBRID_BOUNDARY` | `10` | `far` | `0.4` |
| `python` | `full_only` | `1B_base_tech_noise` | `pivot_suffix` | `HYBRID_BOUNDARY` | `10` | `far` | `0.3` |
| `python` | `full_only` | `1B_base_tech_noise` | `polarity_flip_indirect` | `HYBRID_BOUNDARY` | `8` | `far` | `0.125` |
| `python` | `full_only` | `1B_base_tech_noise` | `prompt_injection_jailbreak` | `ADVERSARIAL_FUZZING` | `25` | `far` | `0.24` |
| `python` | `full_only` | `1B_base_tech_noise` | `pytest_testing` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.0` |
| `python` | `full_only` | `1B_base_tech_noise` | `short_idiom_query` | `IN_DOMAIN_VALID` | `20` | `frr` | `0.6` |
| `python` | `full_only` | `1B_base_tech_noise` | `smuggle_comment_docstring` | `HYBRID_BOUNDARY` | `10` | `far` | `0.2` |
| `python` | `full_only` | `1B_base_tech_noise` | `smuggle_json_yaml` | `HYBRID_BOUNDARY` | `10` | `far` | `0.1` |
| `python` | `full_only` | `1B_base_tech_noise` | `stdlib_idiom` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.2` |
| `python` | `full_only` | `1B_base_tech_noise` | `traceback_debugging` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.125` |
| `python` | `full_only` | `1B_base_tech_noise` | `typing_protocol` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.125` |
| `python` | `clauses` | `1B_base_tech_noise` | `asyncio_concurrency` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.125` |
| `python` | `clauses` | `1B_base_tech_noise` | `code_snippet` | `IN_DOMAIN_VALID` | `6` | `frr` | `0.5` |
| `python` | `clauses` | `1B_base_tech_noise` | `data_structures_oop` | `IN_DOMAIN_VALID` | `6` | `frr` | `0.16666666666666666` |
| `python` | `clauses` | `1B_base_tech_noise` | `delimiter_escape` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `python` | `clauses` | `1B_base_tech_noise` | `dilution_20_80` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `python` | `clauses` | `1B_base_tech_noise` | `dilution_50_50` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `python` | `clauses` | `1B_base_tech_noise` | `dilution_80_20` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `python` | `clauses` | `1B_base_tech_noise` | `extreme_high_entropy_gibberish` | `ADVERSARIAL_FUZZING` | `7` | `far` | `0.0` |
| `python` | `clauses` | `1B_base_tech_noise` | `extreme_short_punct` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.0` |
| `python` | `clauses` | `1B_base_tech_noise` | `homoglyph_zwsp_fullwidth` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `python` | `clauses` | `1B_base_tech_noise` | `keyword_stuffing_hidden_instruction` | `ADVERSARIAL_FUZZING` | `6` | `far` | `0.16666666666666666` |
| `python` | `clauses` | `1B_base_tech_noise` | `long_architecture_guide` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.4` |
| `python` | `clauses` | `1B_base_tech_noise` | `long_context_flooding` | `ADVERSARIAL_FUZZING` | `6` | `far` | `0.0` |
| `python` | `clauses` | `1B_base_tech_noise` | `long_debugging_walkthrough` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.2` |
| `python` | `clauses` | `1B_base_tech_noise` | `near_ood_neighbor` | `HYBRID_BOUNDARY` | `12` | `far` | `0.5833333333333334` |
| `python` | `clauses` | `1B_base_tech_noise` | `obfuscation_base64` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `python` | `clauses` | `1B_base_tech_noise` | `obfuscation_hex_rot13_leet` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.1` |
| `python` | `clauses` | `1B_base_tech_noise` | `ood_architecture_music_hardware` | `OUT_OF_DOMAIN_BENIGN` | `8` | `far` | `0.125` |
| `python` | `clauses` | `1B_base_tech_noise` | `ood_astronomy_geology` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `python` | `clauses` | `1B_base_tech_noise` | `ood_finance_law` | `OUT_OF_DOMAIN_BENIGN` | `12` | `far` | `0.0` |
| `python` | `clauses` | `1B_base_tech_noise` | `ood_history_literature_philosophy` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `python` | `clauses` | `1B_base_tech_noise` | `ood_medicine_biology` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `python` | `clauses` | `1B_base_tech_noise` | `ood_suite2_clinc` | `OUT_OF_DOMAIN_BENIGN` | `40` | `far` | `0.0` |
| `python` | `clauses` | `1B_base_tech_noise` | `ood_travel_weather_sports` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `python` | `clauses` | `1B_base_tech_noise` | `packaging_env` | `IN_DOMAIN_VALID` | `6` | `frr` | `0.0` |
| `python` | `clauses` | `1B_base_tech_noise` | `pivot_middle` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `python` | `clauses` | `1B_base_tech_noise` | `pivot_prefix` | `HYBRID_BOUNDARY` | `10` | `far` | `0.1` |
| `python` | `clauses` | `1B_base_tech_noise` | `pivot_suffix` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `python` | `clauses` | `1B_base_tech_noise` | `polarity_flip_indirect` | `HYBRID_BOUNDARY` | `8` | `far` | `0.125` |
| `python` | `clauses` | `1B_base_tech_noise` | `prompt_injection_jailbreak` | `ADVERSARIAL_FUZZING` | `25` | `far` | `0.28` |
| `python` | `clauses` | `1B_base_tech_noise` | `pytest_testing` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.0` |
| `python` | `clauses` | `1B_base_tech_noise` | `short_idiom_query` | `IN_DOMAIN_VALID` | `20` | `frr` | `0.2` |
| `python` | `clauses` | `1B_base_tech_noise` | `smuggle_comment_docstring` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `python` | `clauses` | `1B_base_tech_noise` | `smuggle_json_yaml` | `HYBRID_BOUNDARY` | `10` | `far` | `0.1` |
| `python` | `clauses` | `1B_base_tech_noise` | `stdlib_idiom` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.1` |
| `python` | `clauses` | `1B_base_tech_noise` | `traceback_debugging` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.125` |
| `python` | `clauses` | `1B_base_tech_noise` | `typing_protocol` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.125` |
| `python` | `full_only` | `1B_full` | `asyncio_concurrency` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.125` |
| `python` | `full_only` | `1B_full` | `code_snippet` | `IN_DOMAIN_VALID` | `6` | `frr` | `0.3333333333333333` |
| `python` | `full_only` | `1B_full` | `data_structures_oop` | `IN_DOMAIN_VALID` | `6` | `frr` | `0.3333333333333333` |
| `python` | `full_only` | `1B_full` | `delimiter_escape` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.08333333333333333` |
| `python` | `full_only` | `1B_full` | `dilution_20_80` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `python` | `full_only` | `1B_full` | `dilution_50_50` | `HYBRID_BOUNDARY` | `10` | `far` | `0.2` |
| `python` | `full_only` | `1B_full` | `dilution_80_20` | `HYBRID_BOUNDARY` | `10` | `far` | `0.8` |
| `python` | `full_only` | `1B_full` | `extreme_high_entropy_gibberish` | `ADVERSARIAL_FUZZING` | `7` | `far` | `0.0` |
| `python` | `full_only` | `1B_full` | `extreme_short_punct` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.0` |
| `python` | `full_only` | `1B_full` | `homoglyph_zwsp_fullwidth` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `python` | `full_only` | `1B_full` | `keyword_stuffing_hidden_instruction` | `ADVERSARIAL_FUZZING` | `6` | `far` | `0.3333333333333333` |
| `python` | `full_only` | `1B_full` | `long_architecture_guide` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.0` |
| `python` | `full_only` | `1B_full` | `long_context_flooding` | `ADVERSARIAL_FUZZING` | `6` | `far` | `0.3333333333333333` |
| `python` | `full_only` | `1B_full` | `long_debugging_walkthrough` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.0` |
| `python` | `full_only` | `1B_full` | `near_ood_neighbor` | `HYBRID_BOUNDARY` | `12` | `far` | `0.4166666666666667` |
| `python` | `full_only` | `1B_full` | `obfuscation_base64` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `python` | `full_only` | `1B_full` | `obfuscation_hex_rot13_leet` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.0` |
| `python` | `full_only` | `1B_full` | `ood_architecture_music_hardware` | `OUT_OF_DOMAIN_BENIGN` | `8` | `far` | `0.0` |
| `python` | `full_only` | `1B_full` | `ood_astronomy_geology` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `python` | `full_only` | `1B_full` | `ood_finance_law` | `OUT_OF_DOMAIN_BENIGN` | `12` | `far` | `0.0` |
| `python` | `full_only` | `1B_full` | `ood_history_literature_philosophy` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `python` | `full_only` | `1B_full` | `ood_medicine_biology` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `python` | `full_only` | `1B_full` | `ood_suite2_clinc` | `OUT_OF_DOMAIN_BENIGN` | `40` | `far` | `0.0` |
| `python` | `full_only` | `1B_full` | `ood_travel_weather_sports` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `python` | `full_only` | `1B_full` | `packaging_env` | `IN_DOMAIN_VALID` | `6` | `frr` | `0.0` |
| `python` | `full_only` | `1B_full` | `pivot_middle` | `HYBRID_BOUNDARY` | `10` | `far` | `0.9` |
| `python` | `full_only` | `1B_full` | `pivot_prefix` | `HYBRID_BOUNDARY` | `10` | `far` | `0.4` |
| `python` | `full_only` | `1B_full` | `pivot_suffix` | `HYBRID_BOUNDARY` | `10` | `far` | `0.4` |
| `python` | `full_only` | `1B_full` | `polarity_flip_indirect` | `HYBRID_BOUNDARY` | `8` | `far` | `0.375` |
| `python` | `full_only` | `1B_full` | `prompt_injection_jailbreak` | `ADVERSARIAL_FUZZING` | `25` | `far` | `0.28` |
| `python` | `full_only` | `1B_full` | `pytest_testing` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.0` |
| `python` | `full_only` | `1B_full` | `short_idiom_query` | `IN_DOMAIN_VALID` | `20` | `frr` | `0.55` |
| `python` | `full_only` | `1B_full` | `smuggle_comment_docstring` | `HYBRID_BOUNDARY` | `10` | `far` | `0.2` |
| `python` | `full_only` | `1B_full` | `smuggle_json_yaml` | `HYBRID_BOUNDARY` | `10` | `far` | `0.1` |
| `python` | `full_only` | `1B_full` | `stdlib_idiom` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.2` |
| `python` | `full_only` | `1B_full` | `traceback_debugging` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.125` |
| `python` | `full_only` | `1B_full` | `typing_protocol` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.125` |
| `python` | `clauses` | `1B_full` | `asyncio_concurrency` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.0` |
| `python` | `clauses` | `1B_full` | `code_snippet` | `IN_DOMAIN_VALID` | `6` | `frr` | `0.5` |
| `python` | `clauses` | `1B_full` | `data_structures_oop` | `IN_DOMAIN_VALID` | `6` | `frr` | `0.0` |
| `python` | `clauses` | `1B_full` | `delimiter_escape` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.16666666666666666` |
| `python` | `clauses` | `1B_full` | `dilution_20_80` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `python` | `clauses` | `1B_full` | `dilution_50_50` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `python` | `clauses` | `1B_full` | `dilution_80_20` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `python` | `clauses` | `1B_full` | `extreme_high_entropy_gibberish` | `ADVERSARIAL_FUZZING` | `7` | `far` | `0.0` |
| `python` | `clauses` | `1B_full` | `extreme_short_punct` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.0` |
| `python` | `clauses` | `1B_full` | `homoglyph_zwsp_fullwidth` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `python` | `clauses` | `1B_full` | `keyword_stuffing_hidden_instruction` | `ADVERSARIAL_FUZZING` | `6` | `far` | `0.16666666666666666` |
| `python` | `clauses` | `1B_full` | `long_architecture_guide` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.3` |
| `python` | `clauses` | `1B_full` | `long_context_flooding` | `ADVERSARIAL_FUZZING` | `6` | `far` | `0.0` |
| `python` | `clauses` | `1B_full` | `long_debugging_walkthrough` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.4` |
| `python` | `clauses` | `1B_full` | `near_ood_neighbor` | `HYBRID_BOUNDARY` | `12` | `far` | `0.5833333333333334` |
| `python` | `clauses` | `1B_full` | `obfuscation_base64` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `python` | `clauses` | `1B_full` | `obfuscation_hex_rot13_leet` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.1` |
| `python` | `clauses` | `1B_full` | `ood_architecture_music_hardware` | `OUT_OF_DOMAIN_BENIGN` | `8` | `far` | `0.125` |
| `python` | `clauses` | `1B_full` | `ood_astronomy_geology` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `python` | `clauses` | `1B_full` | `ood_finance_law` | `OUT_OF_DOMAIN_BENIGN` | `12` | `far` | `0.0` |
| `python` | `clauses` | `1B_full` | `ood_history_literature_philosophy` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `python` | `clauses` | `1B_full` | `ood_medicine_biology` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `python` | `clauses` | `1B_full` | `ood_suite2_clinc` | `OUT_OF_DOMAIN_BENIGN` | `40` | `far` | `0.0` |
| `python` | `clauses` | `1B_full` | `ood_travel_weather_sports` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `python` | `clauses` | `1B_full` | `packaging_env` | `IN_DOMAIN_VALID` | `6` | `frr` | `0.0` |
| `python` | `clauses` | `1B_full` | `pivot_middle` | `HYBRID_BOUNDARY` | `10` | `far` | `0.1` |
| `python` | `clauses` | `1B_full` | `pivot_prefix` | `HYBRID_BOUNDARY` | `10` | `far` | `0.1` |
| `python` | `clauses` | `1B_full` | `pivot_suffix` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `python` | `clauses` | `1B_full` | `polarity_flip_indirect` | `HYBRID_BOUNDARY` | `8` | `far` | `0.25` |
| `python` | `clauses` | `1B_full` | `prompt_injection_jailbreak` | `ADVERSARIAL_FUZZING` | `25` | `far` | `0.28` |
| `python` | `clauses` | `1B_full` | `pytest_testing` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.0` |
| `python` | `clauses` | `1B_full` | `short_idiom_query` | `IN_DOMAIN_VALID` | `20` | `frr` | `0.15` |
| `python` | `clauses` | `1B_full` | `smuggle_comment_docstring` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `python` | `clauses` | `1B_full` | `smuggle_json_yaml` | `HYBRID_BOUNDARY` | `10` | `far` | `0.1` |
| `python` | `clauses` | `1B_full` | `stdlib_idiom` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.0` |
| `python` | `clauses` | `1B_full` | `traceback_debugging` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.125` |
| `python` | `clauses` | `1B_full` | `typing_protocol` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.125` |
| `python` | `full_only` | `1B_full_v3` | `asyncio_concurrency` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.125` |
| `python` | `full_only` | `1B_full_v3` | `code_snippet` | `IN_DOMAIN_VALID` | `6` | `frr` | `0.3333333333333333` |
| `python` | `full_only` | `1B_full_v3` | `data_structures_oop` | `IN_DOMAIN_VALID` | `6` | `frr` | `0.3333333333333333` |
| `python` | `full_only` | `1B_full_v3` | `delimiter_escape` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.16666666666666666` |
| `python` | `full_only` | `1B_full_v3` | `dilution_20_80` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `python` | `full_only` | `1B_full_v3` | `dilution_50_50` | `HYBRID_BOUNDARY` | `10` | `far` | `0.4` |
| `python` | `full_only` | `1B_full_v3` | `dilution_80_20` | `HYBRID_BOUNDARY` | `10` | `far` | `0.9` |
| `python` | `full_only` | `1B_full_v3` | `extreme_high_entropy_gibberish` | `ADVERSARIAL_FUZZING` | `7` | `far` | `0.0` |
| `python` | `full_only` | `1B_full_v3` | `extreme_short_punct` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.0` |
| `python` | `full_only` | `1B_full_v3` | `homoglyph_zwsp_fullwidth` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `python` | `full_only` | `1B_full_v3` | `keyword_stuffing_hidden_instruction` | `ADVERSARIAL_FUZZING` | `6` | `far` | `0.5` |
| `python` | `full_only` | `1B_full_v3` | `long_architecture_guide` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.0` |
| `python` | `full_only` | `1B_full_v3` | `long_context_flooding` | `ADVERSARIAL_FUZZING` | `6` | `far` | `1.0` |
| `python` | `full_only` | `1B_full_v3` | `long_debugging_walkthrough` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.0` |
| `python` | `full_only` | `1B_full_v3` | `near_ood_neighbor` | `HYBRID_BOUNDARY` | `12` | `far` | `0.4166666666666667` |
| `python` | `full_only` | `1B_full_v3` | `obfuscation_base64` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `python` | `full_only` | `1B_full_v3` | `obfuscation_hex_rot13_leet` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.0` |
| `python` | `full_only` | `1B_full_v3` | `ood_architecture_music_hardware` | `OUT_OF_DOMAIN_BENIGN` | `8` | `far` | `0.0` |
| `python` | `full_only` | `1B_full_v3` | `ood_astronomy_geology` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `python` | `full_only` | `1B_full_v3` | `ood_finance_law` | `OUT_OF_DOMAIN_BENIGN` | `12` | `far` | `0.0` |
| `python` | `full_only` | `1B_full_v3` | `ood_history_literature_philosophy` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `python` | `full_only` | `1B_full_v3` | `ood_medicine_biology` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `python` | `full_only` | `1B_full_v3` | `ood_suite2_clinc` | `OUT_OF_DOMAIN_BENIGN` | `40` | `far` | `0.0` |
| `python` | `full_only` | `1B_full_v3` | `ood_travel_weather_sports` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `python` | `full_only` | `1B_full_v3` | `packaging_env` | `IN_DOMAIN_VALID` | `6` | `frr` | `0.0` |
| `python` | `full_only` | `1B_full_v3` | `pivot_middle` | `HYBRID_BOUNDARY` | `10` | `far` | `1.0` |
| `python` | `full_only` | `1B_full_v3` | `pivot_prefix` | `HYBRID_BOUNDARY` | `10` | `far` | `0.5` |
| `python` | `full_only` | `1B_full_v3` | `pivot_suffix` | `HYBRID_BOUNDARY` | `10` | `far` | `0.4` |
| `python` | `full_only` | `1B_full_v3` | `polarity_flip_indirect` | `HYBRID_BOUNDARY` | `8` | `far` | `0.375` |
| `python` | `full_only` | `1B_full_v3` | `prompt_injection_jailbreak` | `ADVERSARIAL_FUZZING` | `25` | `far` | `0.28` |
| `python` | `full_only` | `1B_full_v3` | `pytest_testing` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.0` |
| `python` | `full_only` | `1B_full_v3` | `short_idiom_query` | `IN_DOMAIN_VALID` | `20` | `frr` | `0.6` |
| `python` | `full_only` | `1B_full_v3` | `smuggle_comment_docstring` | `HYBRID_BOUNDARY` | `10` | `far` | `0.2` |
| `python` | `full_only` | `1B_full_v3` | `smuggle_json_yaml` | `HYBRID_BOUNDARY` | `10` | `far` | `0.1` |
| `python` | `full_only` | `1B_full_v3` | `stdlib_idiom` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.2` |
| `python` | `full_only` | `1B_full_v3` | `traceback_debugging` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.125` |
| `python` | `full_only` | `1B_full_v3` | `typing_protocol` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.125` |
| `python` | `clauses` | `1B_full_v3` | `asyncio_concurrency` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.125` |
| `python` | `clauses` | `1B_full_v3` | `code_snippet` | `IN_DOMAIN_VALID` | `6` | `frr` | `0.6666666666666666` |
| `python` | `clauses` | `1B_full_v3` | `data_structures_oop` | `IN_DOMAIN_VALID` | `6` | `frr` | `0.0` |
| `python` | `clauses` | `1B_full_v3` | `delimiter_escape` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.16666666666666666` |
| `python` | `clauses` | `1B_full_v3` | `dilution_20_80` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `python` | `clauses` | `1B_full_v3` | `dilution_50_50` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `python` | `clauses` | `1B_full_v3` | `dilution_80_20` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `python` | `clauses` | `1B_full_v3` | `extreme_high_entropy_gibberish` | `ADVERSARIAL_FUZZING` | `7` | `far` | `0.0` |
| `python` | `clauses` | `1B_full_v3` | `extreme_short_punct` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.0` |
| `python` | `clauses` | `1B_full_v3` | `homoglyph_zwsp_fullwidth` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `python` | `clauses` | `1B_full_v3` | `keyword_stuffing_hidden_instruction` | `ADVERSARIAL_FUZZING` | `6` | `far` | `0.16666666666666666` |
| `python` | `clauses` | `1B_full_v3` | `long_architecture_guide` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.4` |
| `python` | `clauses` | `1B_full_v3` | `long_context_flooding` | `ADVERSARIAL_FUZZING` | `6` | `far` | `0.0` |
| `python` | `clauses` | `1B_full_v3` | `long_debugging_walkthrough` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.4` |
| `python` | `clauses` | `1B_full_v3` | `near_ood_neighbor` | `HYBRID_BOUNDARY` | `12` | `far` | `0.5833333333333334` |
| `python` | `clauses` | `1B_full_v3` | `obfuscation_base64` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `python` | `clauses` | `1B_full_v3` | `obfuscation_hex_rot13_leet` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.0` |
| `python` | `clauses` | `1B_full_v3` | `ood_architecture_music_hardware` | `OUT_OF_DOMAIN_BENIGN` | `8` | `far` | `0.125` |
| `python` | `clauses` | `1B_full_v3` | `ood_astronomy_geology` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `python` | `clauses` | `1B_full_v3` | `ood_finance_law` | `OUT_OF_DOMAIN_BENIGN` | `12` | `far` | `0.0` |
| `python` | `clauses` | `1B_full_v3` | `ood_history_literature_philosophy` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `python` | `clauses` | `1B_full_v3` | `ood_medicine_biology` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `python` | `clauses` | `1B_full_v3` | `ood_suite2_clinc` | `OUT_OF_DOMAIN_BENIGN` | `40` | `far` | `0.0` |
| `python` | `clauses` | `1B_full_v3` | `ood_travel_weather_sports` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `python` | `clauses` | `1B_full_v3` | `packaging_env` | `IN_DOMAIN_VALID` | `6` | `frr` | `0.0` |
| `python` | `clauses` | `1B_full_v3` | `pivot_middle` | `HYBRID_BOUNDARY` | `10` | `far` | `0.1` |
| `python` | `clauses` | `1B_full_v3` | `pivot_prefix` | `HYBRID_BOUNDARY` | `10` | `far` | `0.2` |
| `python` | `clauses` | `1B_full_v3` | `pivot_suffix` | `HYBRID_BOUNDARY` | `10` | `far` | `0.1` |
| `python` | `clauses` | `1B_full_v3` | `polarity_flip_indirect` | `HYBRID_BOUNDARY` | `8` | `far` | `0.125` |
| `python` | `clauses` | `1B_full_v3` | `prompt_injection_jailbreak` | `ADVERSARIAL_FUZZING` | `25` | `far` | `0.28` |
| `python` | `clauses` | `1B_full_v3` | `pytest_testing` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.0` |
| `python` | `clauses` | `1B_full_v3` | `short_idiom_query` | `IN_DOMAIN_VALID` | `20` | `frr` | `0.15` |
| `python` | `clauses` | `1B_full_v3` | `smuggle_comment_docstring` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `python` | `clauses` | `1B_full_v3` | `smuggle_json_yaml` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `python` | `clauses` | `1B_full_v3` | `stdlib_idiom` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.1` |
| `python` | `clauses` | `1B_full_v3` | `traceback_debugging` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.125` |
| `python` | `clauses` | `1B_full_v3` | `typing_protocol` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.125` |
| `receta` | `full_only` | `1B_base_tech` | `cocina_regional` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.0` |
| `receta` | `full_only` | `1B_base_tech` | `consulta_corta` | `IN_DOMAIN_VALID` | `20` | `frr` | `0.35` |
| `receta` | `full_only` | `1B_base_tech` | `delimiter_escape` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `receta` | `full_only` | `1B_base_tech` | `diagnostico_pasteleria_panaderia` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.125` |
| `receta` | `full_only` | `1B_base_tech` | `dilution_20_80` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `receta` | `full_only` | `1B_base_tech` | `dilution_50_50` | `HYBRID_BOUNDARY` | `10` | `far` | `0.2` |
| `receta` | `full_only` | `1B_base_tech` | `dilution_80_20` | `HYBRID_BOUNDARY` | `10` | `far` | `0.7` |
| `receta` | `full_only` | `1B_base_tech` | `extreme_high_entropy_gibberish` | `ADVERSARIAL_FUZZING` | `7` | `far` | `0.0` |
| `receta` | `full_only` | `1B_base_tech` | `extreme_short_punct` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.0` |
| `receta` | `full_only` | `1B_base_tech` | `guia_culinaria_larga` | `IN_DOMAIN_VALID` | `12` | `frr` | `0.0` |
| `receta` | `full_only` | `1B_base_tech` | `homoglyph_zwsp_fullwidth` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.08333333333333333` |
| `receta` | `full_only` | `1B_base_tech` | `keyword_stuffing_hidden_instruction` | `ADVERSARIAL_FUZZING` | `6` | `far` | `0.0` |
| `receta` | `full_only` | `1B_base_tech` | `long_context_flooding` | `ADVERSARIAL_FUZZING` | `6` | `far` | `0.0` |
| `receta` | `full_only` | `1B_base_tech` | `near_ood_neighbor` | `HYBRID_BOUNDARY` | `12` | `far` | `0.0` |
| `receta` | `full_only` | `1B_base_tech` | `obfuscation_base64` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `receta` | `full_only` | `1B_base_tech` | `obfuscation_hex_rot13_leet` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.0` |
| `receta` | `full_only` | `1B_base_tech` | `ood_finanzas_derecho` | `OUT_OF_DOMAIN_BENIGN` | `12` | `far` | `0.0` |
| `receta` | `full_only` | `1B_base_tech` | `ood_hardware_arquitectura_musica` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `receta` | `full_only` | `1B_base_tech` | `ood_historia_literatura` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `receta` | `full_only` | `1B_base_tech` | `ood_medicina_ciencia` | `OUT_OF_DOMAIN_BENIGN` | `11` | `far` | `0.0` |
| `receta` | `full_only` | `1B_base_tech` | `ood_suite2_clean_astronomia` | `OUT_OF_DOMAIN_BENIGN` | `7` | `far` | `0.0` |
| `receta` | `full_only` | `1B_base_tech` | `ood_suite2_clean_legal` | `OUT_OF_DOMAIN_BENIGN` | `9` | `far` | `0.0` |
| `receta` | `full_only` | `1B_base_tech` | `ood_suite2_clean_medicina` | `OUT_OF_DOMAIN_BENIGN` | `9` | `far` | `0.0` |
| `receta` | `full_only` | `1B_base_tech` | `ood_suite2_es_oos` | `OUT_OF_DOMAIN_BENIGN` | `20` | `far` | `0.0` |
| `receta` | `full_only` | `1B_base_tech` | `ood_viajes_clima_deportes` | `OUT_OF_DOMAIN_BENIGN` | `12` | `far` | `0.0` |
| `receta` | `full_only` | `1B_base_tech` | `panaderia_fermentacion` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.6` |
| `receta` | `full_only` | `1B_base_tech` | `pivot_middle` | `HYBRID_BOUNDARY` | `10` | `far` | `0.7` |
| `receta` | `full_only` | `1B_base_tech` | `pivot_prefix` | `HYBRID_BOUNDARY` | `10` | `far` | `0.1` |
| `receta` | `full_only` | `1B_base_tech` | `pivot_suffix` | `HYBRID_BOUNDARY` | `10` | `far` | `0.4` |
| `receta` | `full_only` | `1B_base_tech` | `polarity_flip_indirect` | `HYBRID_BOUNDARY` | `8` | `far` | `0.125` |
| `receta` | `full_only` | `1B_base_tech` | `prompt_injection_jailbreak` | `ADVERSARIAL_FUZZING` | `25` | `far` | `0.0` |
| `receta` | `full_only` | `1B_base_tech` | `receta_completa` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.0` |
| `receta` | `full_only` | `1B_base_tech` | `salsas_emulsiones` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.125` |
| `receta` | `full_only` | `1B_base_tech` | `smuggle_json_yaml` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `receta` | `full_only` | `1B_base_tech` | `smuggle_recipe_footnote` | `HYBRID_BOUNDARY` | `10` | `far` | `0.8` |
| `receta` | `full_only` | `1B_base_tech` | `sustitucion_ingredientes` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.25` |
| `receta` | `full_only` | `1B_base_tech` | `tecnica_culinaria` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.3` |
| `receta` | `full_only` | `1B_base_tech` | `temperatura_tiempos` | `IN_DOMAIN_VALID` | `6` | `frr` | `0.5` |
| `receta` | `clauses` | `1B_base_tech` | `cocina_regional` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.25` |
| `receta` | `clauses` | `1B_base_tech` | `consulta_corta` | `IN_DOMAIN_VALID` | `20` | `frr` | `0.1` |
| `receta` | `clauses` | `1B_base_tech` | `delimiter_escape` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `receta` | `clauses` | `1B_base_tech` | `diagnostico_pasteleria_panaderia` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.5` |
| `receta` | `clauses` | `1B_base_tech` | `dilution_20_80` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `receta` | `clauses` | `1B_base_tech` | `dilution_50_50` | `HYBRID_BOUNDARY` | `10` | `far` | `0.1` |
| `receta` | `clauses` | `1B_base_tech` | `dilution_80_20` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `receta` | `clauses` | `1B_base_tech` | `extreme_high_entropy_gibberish` | `ADVERSARIAL_FUZZING` | `7` | `far` | `0.0` |
| `receta` | `clauses` | `1B_base_tech` | `extreme_short_punct` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.1` |
| `receta` | `clauses` | `1B_base_tech` | `guia_culinaria_larga` | `IN_DOMAIN_VALID` | `12` | `frr` | `0.16666666666666666` |
| `receta` | `clauses` | `1B_base_tech` | `homoglyph_zwsp_fullwidth` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `receta` | `clauses` | `1B_base_tech` | `keyword_stuffing_hidden_instruction` | `ADVERSARIAL_FUZZING` | `6` | `far` | `0.0` |
| `receta` | `clauses` | `1B_base_tech` | `long_context_flooding` | `ADVERSARIAL_FUZZING` | `6` | `far` | `0.0` |
| `receta` | `clauses` | `1B_base_tech` | `near_ood_neighbor` | `HYBRID_BOUNDARY` | `12` | `far` | `0.0` |
| `receta` | `clauses` | `1B_base_tech` | `obfuscation_base64` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `receta` | `clauses` | `1B_base_tech` | `obfuscation_hex_rot13_leet` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.0` |
| `receta` | `clauses` | `1B_base_tech` | `ood_finanzas_derecho` | `OUT_OF_DOMAIN_BENIGN` | `12` | `far` | `0.0` |
| `receta` | `clauses` | `1B_base_tech` | `ood_hardware_arquitectura_musica` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `receta` | `clauses` | `1B_base_tech` | `ood_historia_literatura` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `receta` | `clauses` | `1B_base_tech` | `ood_medicina_ciencia` | `OUT_OF_DOMAIN_BENIGN` | `11` | `far` | `0.0` |
| `receta` | `clauses` | `1B_base_tech` | `ood_suite2_clean_astronomia` | `OUT_OF_DOMAIN_BENIGN` | `7` | `far` | `0.0` |
| `receta` | `clauses` | `1B_base_tech` | `ood_suite2_clean_legal` | `OUT_OF_DOMAIN_BENIGN` | `9` | `far` | `0.0` |
| `receta` | `clauses` | `1B_base_tech` | `ood_suite2_clean_medicina` | `OUT_OF_DOMAIN_BENIGN` | `9` | `far` | `0.0` |
| `receta` | `clauses` | `1B_base_tech` | `ood_suite2_es_oos` | `OUT_OF_DOMAIN_BENIGN` | `20` | `far` | `0.05` |
| `receta` | `clauses` | `1B_base_tech` | `ood_viajes_clima_deportes` | `OUT_OF_DOMAIN_BENIGN` | `12` | `far` | `0.0` |
| `receta` | `clauses` | `1B_base_tech` | `panaderia_fermentacion` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.3` |
| `receta` | `clauses` | `1B_base_tech` | `pivot_middle` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `receta` | `clauses` | `1B_base_tech` | `pivot_prefix` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `receta` | `clauses` | `1B_base_tech` | `pivot_suffix` | `HYBRID_BOUNDARY` | `10` | `far` | `0.1` |
| `receta` | `clauses` | `1B_base_tech` | `polarity_flip_indirect` | `HYBRID_BOUNDARY` | `8` | `far` | `0.0` |
| `receta` | `clauses` | `1B_base_tech` | `prompt_injection_jailbreak` | `ADVERSARIAL_FUZZING` | `25` | `far` | `0.0` |
| `receta` | `clauses` | `1B_base_tech` | `receta_completa` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.0` |
| `receta` | `clauses` | `1B_base_tech` | `salsas_emulsiones` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.125` |
| `receta` | `clauses` | `1B_base_tech` | `smuggle_json_yaml` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `receta` | `clauses` | `1B_base_tech` | `smuggle_recipe_footnote` | `HYBRID_BOUNDARY` | `10` | `far` | `0.2` |
| `receta` | `clauses` | `1B_base_tech` | `sustitucion_ingredientes` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.125` |
| `receta` | `clauses` | `1B_base_tech` | `tecnica_culinaria` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.1` |
| `receta` | `clauses` | `1B_base_tech` | `temperatura_tiempos` | `IN_DOMAIN_VALID` | `6` | `frr` | `0.16666666666666666` |
| `receta` | `full_only` | `1B_base_tech_noise` | `cocina_regional` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.625` |
| `receta` | `full_only` | `1B_base_tech_noise` | `consulta_corta` | `IN_DOMAIN_VALID` | `20` | `frr` | `0.65` |
| `receta` | `full_only` | `1B_base_tech_noise` | `delimiter_escape` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `receta` | `full_only` | `1B_base_tech_noise` | `diagnostico_pasteleria_panaderia` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.25` |
| `receta` | `full_only` | `1B_base_tech_noise` | `dilution_20_80` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `receta` | `full_only` | `1B_base_tech_noise` | `dilution_50_50` | `HYBRID_BOUNDARY` | `10` | `far` | `0.1` |
| `receta` | `full_only` | `1B_base_tech_noise` | `dilution_80_20` | `HYBRID_BOUNDARY` | `10` | `far` | `0.7` |
| `receta` | `full_only` | `1B_base_tech_noise` | `extreme_high_entropy_gibberish` | `ADVERSARIAL_FUZZING` | `7` | `far` | `0.0` |
| `receta` | `full_only` | `1B_base_tech_noise` | `extreme_short_punct` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.0` |
| `receta` | `full_only` | `1B_base_tech_noise` | `guia_culinaria_larga` | `IN_DOMAIN_VALID` | `12` | `frr` | `0.0` |
| `receta` | `full_only` | `1B_base_tech_noise` | `homoglyph_zwsp_fullwidth` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `receta` | `full_only` | `1B_base_tech_noise` | `keyword_stuffing_hidden_instruction` | `ADVERSARIAL_FUZZING` | `6` | `far` | `0.0` |
| `receta` | `full_only` | `1B_base_tech_noise` | `long_context_flooding` | `ADVERSARIAL_FUZZING` | `6` | `far` | `0.0` |
| `receta` | `full_only` | `1B_base_tech_noise` | `near_ood_neighbor` | `HYBRID_BOUNDARY` | `12` | `far` | `0.0` |
| `receta` | `full_only` | `1B_base_tech_noise` | `obfuscation_base64` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `receta` | `full_only` | `1B_base_tech_noise` | `obfuscation_hex_rot13_leet` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.0` |
| `receta` | `full_only` | `1B_base_tech_noise` | `ood_finanzas_derecho` | `OUT_OF_DOMAIN_BENIGN` | `12` | `far` | `0.0` |
| `receta` | `full_only` | `1B_base_tech_noise` | `ood_hardware_arquitectura_musica` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `receta` | `full_only` | `1B_base_tech_noise` | `ood_historia_literatura` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `receta` | `full_only` | `1B_base_tech_noise` | `ood_medicina_ciencia` | `OUT_OF_DOMAIN_BENIGN` | `11` | `far` | `0.0` |
| `receta` | `full_only` | `1B_base_tech_noise` | `ood_suite2_clean_astronomia` | `OUT_OF_DOMAIN_BENIGN` | `7` | `far` | `0.0` |
| `receta` | `full_only` | `1B_base_tech_noise` | `ood_suite2_clean_legal` | `OUT_OF_DOMAIN_BENIGN` | `9` | `far` | `0.0` |
| `receta` | `full_only` | `1B_base_tech_noise` | `ood_suite2_clean_medicina` | `OUT_OF_DOMAIN_BENIGN` | `9` | `far` | `0.0` |
| `receta` | `full_only` | `1B_base_tech_noise` | `ood_suite2_es_oos` | `OUT_OF_DOMAIN_BENIGN` | `20` | `far` | `0.0` |
| `receta` | `full_only` | `1B_base_tech_noise` | `ood_viajes_clima_deportes` | `OUT_OF_DOMAIN_BENIGN` | `12` | `far` | `0.0` |
| `receta` | `full_only` | `1B_base_tech_noise` | `panaderia_fermentacion` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.8` |
| `receta` | `full_only` | `1B_base_tech_noise` | `pivot_middle` | `HYBRID_BOUNDARY` | `10` | `far` | `0.6` |
| `receta` | `full_only` | `1B_base_tech_noise` | `pivot_prefix` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `receta` | `full_only` | `1B_base_tech_noise` | `pivot_suffix` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `receta` | `full_only` | `1B_base_tech_noise` | `polarity_flip_indirect` | `HYBRID_BOUNDARY` | `8` | `far` | `0.0` |
| `receta` | `full_only` | `1B_base_tech_noise` | `prompt_injection_jailbreak` | `ADVERSARIAL_FUZZING` | `25` | `far` | `0.0` |
| `receta` | `full_only` | `1B_base_tech_noise` | `receta_completa` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.0` |
| `receta` | `full_only` | `1B_base_tech_noise` | `salsas_emulsiones` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.5` |
| `receta` | `full_only` | `1B_base_tech_noise` | `smuggle_json_yaml` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `receta` | `full_only` | `1B_base_tech_noise` | `smuggle_recipe_footnote` | `HYBRID_BOUNDARY` | `10` | `far` | `0.8` |
| `receta` | `full_only` | `1B_base_tech_noise` | `sustitucion_ingredientes` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.375` |
| `receta` | `full_only` | `1B_base_tech_noise` | `tecnica_culinaria` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.6` |
| `receta` | `full_only` | `1B_base_tech_noise` | `temperatura_tiempos` | `IN_DOMAIN_VALID` | `6` | `frr` | `0.8333333333333334` |
| `receta` | `clauses` | `1B_base_tech_noise` | `cocina_regional` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.375` |
| `receta` | `clauses` | `1B_base_tech_noise` | `consulta_corta` | `IN_DOMAIN_VALID` | `20` | `frr` | `0.1` |
| `receta` | `clauses` | `1B_base_tech_noise` | `delimiter_escape` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `receta` | `clauses` | `1B_base_tech_noise` | `diagnostico_pasteleria_panaderia` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.5` |
| `receta` | `clauses` | `1B_base_tech_noise` | `dilution_20_80` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `receta` | `clauses` | `1B_base_tech_noise` | `dilution_50_50` | `HYBRID_BOUNDARY` | `10` | `far` | `0.1` |
| `receta` | `clauses` | `1B_base_tech_noise` | `dilution_80_20` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `receta` | `clauses` | `1B_base_tech_noise` | `extreme_high_entropy_gibberish` | `ADVERSARIAL_FUZZING` | `7` | `far` | `0.0` |
| `receta` | `clauses` | `1B_base_tech_noise` | `extreme_short_punct` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.0` |
| `receta` | `clauses` | `1B_base_tech_noise` | `guia_culinaria_larga` | `IN_DOMAIN_VALID` | `12` | `frr` | `0.3333333333333333` |
| `receta` | `clauses` | `1B_base_tech_noise` | `homoglyph_zwsp_fullwidth` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `receta` | `clauses` | `1B_base_tech_noise` | `keyword_stuffing_hidden_instruction` | `ADVERSARIAL_FUZZING` | `6` | `far` | `0.0` |
| `receta` | `clauses` | `1B_base_tech_noise` | `long_context_flooding` | `ADVERSARIAL_FUZZING` | `6` | `far` | `0.0` |
| `receta` | `clauses` | `1B_base_tech_noise` | `near_ood_neighbor` | `HYBRID_BOUNDARY` | `12` | `far` | `0.0` |
| `receta` | `clauses` | `1B_base_tech_noise` | `obfuscation_base64` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `receta` | `clauses` | `1B_base_tech_noise` | `obfuscation_hex_rot13_leet` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.0` |
| `receta` | `clauses` | `1B_base_tech_noise` | `ood_finanzas_derecho` | `OUT_OF_DOMAIN_BENIGN` | `12` | `far` | `0.0` |
| `receta` | `clauses` | `1B_base_tech_noise` | `ood_hardware_arquitectura_musica` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `receta` | `clauses` | `1B_base_tech_noise` | `ood_historia_literatura` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `receta` | `clauses` | `1B_base_tech_noise` | `ood_medicina_ciencia` | `OUT_OF_DOMAIN_BENIGN` | `11` | `far` | `0.0` |
| `receta` | `clauses` | `1B_base_tech_noise` | `ood_suite2_clean_astronomia` | `OUT_OF_DOMAIN_BENIGN` | `7` | `far` | `0.0` |
| `receta` | `clauses` | `1B_base_tech_noise` | `ood_suite2_clean_legal` | `OUT_OF_DOMAIN_BENIGN` | `9` | `far` | `0.0` |
| `receta` | `clauses` | `1B_base_tech_noise` | `ood_suite2_clean_medicina` | `OUT_OF_DOMAIN_BENIGN` | `9` | `far` | `0.0` |
| `receta` | `clauses` | `1B_base_tech_noise` | `ood_suite2_es_oos` | `OUT_OF_DOMAIN_BENIGN` | `20` | `far` | `0.05` |
| `receta` | `clauses` | `1B_base_tech_noise` | `ood_viajes_clima_deportes` | `OUT_OF_DOMAIN_BENIGN` | `12` | `far` | `0.0` |
| `receta` | `clauses` | `1B_base_tech_noise` | `panaderia_fermentacion` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.2` |
| `receta` | `clauses` | `1B_base_tech_noise` | `pivot_middle` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `receta` | `clauses` | `1B_base_tech_noise` | `pivot_prefix` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `receta` | `clauses` | `1B_base_tech_noise` | `pivot_suffix` | `HYBRID_BOUNDARY` | `10` | `far` | `0.1` |
| `receta` | `clauses` | `1B_base_tech_noise` | `polarity_flip_indirect` | `HYBRID_BOUNDARY` | `8` | `far` | `0.0` |
| `receta` | `clauses` | `1B_base_tech_noise` | `prompt_injection_jailbreak` | `ADVERSARIAL_FUZZING` | `25` | `far` | `0.0` |
| `receta` | `clauses` | `1B_base_tech_noise` | `receta_completa` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.0` |
| `receta` | `clauses` | `1B_base_tech_noise` | `salsas_emulsiones` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.125` |
| `receta` | `clauses` | `1B_base_tech_noise` | `smuggle_json_yaml` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `receta` | `clauses` | `1B_base_tech_noise` | `smuggle_recipe_footnote` | `HYBRID_BOUNDARY` | `10` | `far` | `0.2` |
| `receta` | `clauses` | `1B_base_tech_noise` | `sustitucion_ingredientes` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.25` |
| `receta` | `clauses` | `1B_base_tech_noise` | `tecnica_culinaria` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.1` |
| `receta` | `clauses` | `1B_base_tech_noise` | `temperatura_tiempos` | `IN_DOMAIN_VALID` | `6` | `frr` | `0.16666666666666666` |
| `receta` | `full_only` | `1B_full` | `cocina_regional` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.625` |
| `receta` | `full_only` | `1B_full` | `consulta_corta` | `IN_DOMAIN_VALID` | `20` | `frr` | `0.6` |
| `receta` | `full_only` | `1B_full` | `delimiter_escape` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `receta` | `full_only` | `1B_full` | `diagnostico_pasteleria_panaderia` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.25` |
| `receta` | `full_only` | `1B_full` | `dilution_20_80` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `receta` | `full_only` | `1B_full` | `dilution_50_50` | `HYBRID_BOUNDARY` | `10` | `far` | `0.1` |
| `receta` | `full_only` | `1B_full` | `dilution_80_20` | `HYBRID_BOUNDARY` | `10` | `far` | `0.7` |
| `receta` | `full_only` | `1B_full` | `extreme_high_entropy_gibberish` | `ADVERSARIAL_FUZZING` | `7` | `far` | `0.0` |
| `receta` | `full_only` | `1B_full` | `extreme_short_punct` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.0` |
| `receta` | `full_only` | `1B_full` | `guia_culinaria_larga` | `IN_DOMAIN_VALID` | `12` | `frr` | `0.0` |
| `receta` | `full_only` | `1B_full` | `homoglyph_zwsp_fullwidth` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `receta` | `full_only` | `1B_full` | `keyword_stuffing_hidden_instruction` | `ADVERSARIAL_FUZZING` | `6` | `far` | `0.0` |
| `receta` | `full_only` | `1B_full` | `long_context_flooding` | `ADVERSARIAL_FUZZING` | `6` | `far` | `0.0` |
| `receta` | `full_only` | `1B_full` | `near_ood_neighbor` | `HYBRID_BOUNDARY` | `12` | `far` | `0.0` |
| `receta` | `full_only` | `1B_full` | `obfuscation_base64` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `receta` | `full_only` | `1B_full` | `obfuscation_hex_rot13_leet` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.0` |
| `receta` | `full_only` | `1B_full` | `ood_finanzas_derecho` | `OUT_OF_DOMAIN_BENIGN` | `12` | `far` | `0.0` |
| `receta` | `full_only` | `1B_full` | `ood_hardware_arquitectura_musica` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `receta` | `full_only` | `1B_full` | `ood_historia_literatura` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `receta` | `full_only` | `1B_full` | `ood_medicina_ciencia` | `OUT_OF_DOMAIN_BENIGN` | `11` | `far` | `0.0` |
| `receta` | `full_only` | `1B_full` | `ood_suite2_clean_astronomia` | `OUT_OF_DOMAIN_BENIGN` | `7` | `far` | `0.0` |
| `receta` | `full_only` | `1B_full` | `ood_suite2_clean_legal` | `OUT_OF_DOMAIN_BENIGN` | `9` | `far` | `0.0` |
| `receta` | `full_only` | `1B_full` | `ood_suite2_clean_medicina` | `OUT_OF_DOMAIN_BENIGN` | `9` | `far` | `0.0` |
| `receta` | `full_only` | `1B_full` | `ood_suite2_es_oos` | `OUT_OF_DOMAIN_BENIGN` | `20` | `far` | `0.0` |
| `receta` | `full_only` | `1B_full` | `ood_viajes_clima_deportes` | `OUT_OF_DOMAIN_BENIGN` | `12` | `far` | `0.0` |
| `receta` | `full_only` | `1B_full` | `panaderia_fermentacion` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.8` |
| `receta` | `full_only` | `1B_full` | `pivot_middle` | `HYBRID_BOUNDARY` | `10` | `far` | `0.5` |
| `receta` | `full_only` | `1B_full` | `pivot_prefix` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `receta` | `full_only` | `1B_full` | `pivot_suffix` | `HYBRID_BOUNDARY` | `10` | `far` | `0.2` |
| `receta` | `full_only` | `1B_full` | `polarity_flip_indirect` | `HYBRID_BOUNDARY` | `8` | `far` | `0.0` |
| `receta` | `full_only` | `1B_full` | `prompt_injection_jailbreak` | `ADVERSARIAL_FUZZING` | `25` | `far` | `0.0` |
| `receta` | `full_only` | `1B_full` | `receta_completa` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.0` |
| `receta` | `full_only` | `1B_full` | `salsas_emulsiones` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.375` |
| `receta` | `full_only` | `1B_full` | `smuggle_json_yaml` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `receta` | `full_only` | `1B_full` | `smuggle_recipe_footnote` | `HYBRID_BOUNDARY` | `10` | `far` | `0.9` |
| `receta` | `full_only` | `1B_full` | `sustitucion_ingredientes` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.375` |
| `receta` | `full_only` | `1B_full` | `tecnica_culinaria` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.6` |
| `receta` | `full_only` | `1B_full` | `temperatura_tiempos` | `IN_DOMAIN_VALID` | `6` | `frr` | `0.8333333333333334` |
| `receta` | `clauses` | `1B_full` | `cocina_regional` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.25` |
| `receta` | `clauses` | `1B_full` | `consulta_corta` | `IN_DOMAIN_VALID` | `20` | `frr` | `0.15` |
| `receta` | `clauses` | `1B_full` | `delimiter_escape` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `receta` | `clauses` | `1B_full` | `diagnostico_pasteleria_panaderia` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.5` |
| `receta` | `clauses` | `1B_full` | `dilution_20_80` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `receta` | `clauses` | `1B_full` | `dilution_50_50` | `HYBRID_BOUNDARY` | `10` | `far` | `0.1` |
| `receta` | `clauses` | `1B_full` | `dilution_80_20` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `receta` | `clauses` | `1B_full` | `extreme_high_entropy_gibberish` | `ADVERSARIAL_FUZZING` | `7` | `far` | `0.0` |
| `receta` | `clauses` | `1B_full` | `extreme_short_punct` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.0` |
| `receta` | `clauses` | `1B_full` | `guia_culinaria_larga` | `IN_DOMAIN_VALID` | `12` | `frr` | `0.16666666666666666` |
| `receta` | `clauses` | `1B_full` | `homoglyph_zwsp_fullwidth` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `receta` | `clauses` | `1B_full` | `keyword_stuffing_hidden_instruction` | `ADVERSARIAL_FUZZING` | `6` | `far` | `0.0` |
| `receta` | `clauses` | `1B_full` | `long_context_flooding` | `ADVERSARIAL_FUZZING` | `6` | `far` | `0.0` |
| `receta` | `clauses` | `1B_full` | `near_ood_neighbor` | `HYBRID_BOUNDARY` | `12` | `far` | `0.0` |
| `receta` | `clauses` | `1B_full` | `obfuscation_base64` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `receta` | `clauses` | `1B_full` | `obfuscation_hex_rot13_leet` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.0` |
| `receta` | `clauses` | `1B_full` | `ood_finanzas_derecho` | `OUT_OF_DOMAIN_BENIGN` | `12` | `far` | `0.0` |
| `receta` | `clauses` | `1B_full` | `ood_hardware_arquitectura_musica` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `receta` | `clauses` | `1B_full` | `ood_historia_literatura` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `receta` | `clauses` | `1B_full` | `ood_medicina_ciencia` | `OUT_OF_DOMAIN_BENIGN` | `11` | `far` | `0.0` |
| `receta` | `clauses` | `1B_full` | `ood_suite2_clean_astronomia` | `OUT_OF_DOMAIN_BENIGN` | `7` | `far` | `0.0` |
| `receta` | `clauses` | `1B_full` | `ood_suite2_clean_legal` | `OUT_OF_DOMAIN_BENIGN` | `9` | `far` | `0.0` |
| `receta` | `clauses` | `1B_full` | `ood_suite2_clean_medicina` | `OUT_OF_DOMAIN_BENIGN` | `9` | `far` | `0.0` |
| `receta` | `clauses` | `1B_full` | `ood_suite2_es_oos` | `OUT_OF_DOMAIN_BENIGN` | `20` | `far` | `0.05` |
| `receta` | `clauses` | `1B_full` | `ood_viajes_clima_deportes` | `OUT_OF_DOMAIN_BENIGN` | `12` | `far` | `0.0` |
| `receta` | `clauses` | `1B_full` | `panaderia_fermentacion` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.3` |
| `receta` | `clauses` | `1B_full` | `pivot_middle` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `receta` | `clauses` | `1B_full` | `pivot_prefix` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `receta` | `clauses` | `1B_full` | `pivot_suffix` | `HYBRID_BOUNDARY` | `10` | `far` | `0.1` |
| `receta` | `clauses` | `1B_full` | `polarity_flip_indirect` | `HYBRID_BOUNDARY` | `8` | `far` | `0.0` |
| `receta` | `clauses` | `1B_full` | `prompt_injection_jailbreak` | `ADVERSARIAL_FUZZING` | `25` | `far` | `0.0` |
| `receta` | `clauses` | `1B_full` | `receta_completa` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.0` |
| `receta` | `clauses` | `1B_full` | `salsas_emulsiones` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.125` |
| `receta` | `clauses` | `1B_full` | `smuggle_json_yaml` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `receta` | `clauses` | `1B_full` | `smuggle_recipe_footnote` | `HYBRID_BOUNDARY` | `10` | `far` | `0.2` |
| `receta` | `clauses` | `1B_full` | `sustitucion_ingredientes` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.125` |
| `receta` | `clauses` | `1B_full` | `tecnica_culinaria` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.0` |
| `receta` | `clauses` | `1B_full` | `temperatura_tiempos` | `IN_DOMAIN_VALID` | `6` | `frr` | `0.16666666666666666` |
| `receta` | `full_only` | `1B_full_v3` | `cocina_regional` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.125` |
| `receta` | `full_only` | `1B_full_v3` | `consulta_corta` | `IN_DOMAIN_VALID` | `20` | `frr` | `0.4` |
| `receta` | `full_only` | `1B_full_v3` | `delimiter_escape` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `receta` | `full_only` | `1B_full_v3` | `diagnostico_pasteleria_panaderia` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.375` |
| `receta` | `full_only` | `1B_full_v3` | `dilution_20_80` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `receta` | `full_only` | `1B_full_v3` | `dilution_50_50` | `HYBRID_BOUNDARY` | `10` | `far` | `0.2` |
| `receta` | `full_only` | `1B_full_v3` | `dilution_80_20` | `HYBRID_BOUNDARY` | `10` | `far` | `0.8` |
| `receta` | `full_only` | `1B_full_v3` | `extreme_high_entropy_gibberish` | `ADVERSARIAL_FUZZING` | `7` | `far` | `0.0` |
| `receta` | `full_only` | `1B_full_v3` | `extreme_short_punct` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.0` |
| `receta` | `full_only` | `1B_full_v3` | `guia_culinaria_larga` | `IN_DOMAIN_VALID` | `12` | `frr` | `0.0` |
| `receta` | `full_only` | `1B_full_v3` | `homoglyph_zwsp_fullwidth` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `receta` | `full_only` | `1B_full_v3` | `keyword_stuffing_hidden_instruction` | `ADVERSARIAL_FUZZING` | `6` | `far` | `0.0` |
| `receta` | `full_only` | `1B_full_v3` | `long_context_flooding` | `ADVERSARIAL_FUZZING` | `6` | `far` | `0.0` |
| `receta` | `full_only` | `1B_full_v3` | `near_ood_neighbor` | `HYBRID_BOUNDARY` | `12` | `far` | `0.0` |
| `receta` | `full_only` | `1B_full_v3` | `obfuscation_base64` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `receta` | `full_only` | `1B_full_v3` | `obfuscation_hex_rot13_leet` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.0` |
| `receta` | `full_only` | `1B_full_v3` | `ood_finanzas_derecho` | `OUT_OF_DOMAIN_BENIGN` | `12` | `far` | `0.0` |
| `receta` | `full_only` | `1B_full_v3` | `ood_hardware_arquitectura_musica` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `receta` | `full_only` | `1B_full_v3` | `ood_historia_literatura` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `receta` | `full_only` | `1B_full_v3` | `ood_medicina_ciencia` | `OUT_OF_DOMAIN_BENIGN` | `11` | `far` | `0.0` |
| `receta` | `full_only` | `1B_full_v3` | `ood_suite2_clean_astronomia` | `OUT_OF_DOMAIN_BENIGN` | `7` | `far` | `0.0` |
| `receta` | `full_only` | `1B_full_v3` | `ood_suite2_clean_legal` | `OUT_OF_DOMAIN_BENIGN` | `9` | `far` | `0.0` |
| `receta` | `full_only` | `1B_full_v3` | `ood_suite2_clean_medicina` | `OUT_OF_DOMAIN_BENIGN` | `9` | `far` | `0.0` |
| `receta` | `full_only` | `1B_full_v3` | `ood_suite2_es_oos` | `OUT_OF_DOMAIN_BENIGN` | `20` | `far` | `0.0` |
| `receta` | `full_only` | `1B_full_v3` | `ood_viajes_clima_deportes` | `OUT_OF_DOMAIN_BENIGN` | `12` | `far` | `0.0` |
| `receta` | `full_only` | `1B_full_v3` | `panaderia_fermentacion` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.6` |
| `receta` | `full_only` | `1B_full_v3` | `pivot_middle` | `HYBRID_BOUNDARY` | `10` | `far` | `0.6` |
| `receta` | `full_only` | `1B_full_v3` | `pivot_prefix` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `receta` | `full_only` | `1B_full_v3` | `pivot_suffix` | `HYBRID_BOUNDARY` | `10` | `far` | `0.3` |
| `receta` | `full_only` | `1B_full_v3` | `polarity_flip_indirect` | `HYBRID_BOUNDARY` | `8` | `far` | `0.125` |
| `receta` | `full_only` | `1B_full_v3` | `prompt_injection_jailbreak` | `ADVERSARIAL_FUZZING` | `25` | `far` | `0.0` |
| `receta` | `full_only` | `1B_full_v3` | `receta_completa` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.0` |
| `receta` | `full_only` | `1B_full_v3` | `salsas_emulsiones` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.125` |
| `receta` | `full_only` | `1B_full_v3` | `smuggle_json_yaml` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `receta` | `full_only` | `1B_full_v3` | `smuggle_recipe_footnote` | `HYBRID_BOUNDARY` | `10` | `far` | `0.9` |
| `receta` | `full_only` | `1B_full_v3` | `sustitucion_ingredientes` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.25` |
| `receta` | `full_only` | `1B_full_v3` | `tecnica_culinaria` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.3` |
| `receta` | `full_only` | `1B_full_v3` | `temperatura_tiempos` | `IN_DOMAIN_VALID` | `6` | `frr` | `0.6666666666666666` |
| `receta` | `clauses` | `1B_full_v3` | `cocina_regional` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.375` |
| `receta` | `clauses` | `1B_full_v3` | `consulta_corta` | `IN_DOMAIN_VALID` | `20` | `frr` | `0.1` |
| `receta` | `clauses` | `1B_full_v3` | `delimiter_escape` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `receta` | `clauses` | `1B_full_v3` | `diagnostico_pasteleria_panaderia` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.5` |
| `receta` | `clauses` | `1B_full_v3` | `dilution_20_80` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `receta` | `clauses` | `1B_full_v3` | `dilution_50_50` | `HYBRID_BOUNDARY` | `10` | `far` | `0.1` |
| `receta` | `clauses` | `1B_full_v3` | `dilution_80_20` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `receta` | `clauses` | `1B_full_v3` | `extreme_high_entropy_gibberish` | `ADVERSARIAL_FUZZING` | `7` | `far` | `0.0` |
| `receta` | `clauses` | `1B_full_v3` | `extreme_short_punct` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.0` |
| `receta` | `clauses` | `1B_full_v3` | `guia_culinaria_larga` | `IN_DOMAIN_VALID` | `12` | `frr` | `0.16666666666666666` |
| `receta` | `clauses` | `1B_full_v3` | `homoglyph_zwsp_fullwidth` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `receta` | `clauses` | `1B_full_v3` | `keyword_stuffing_hidden_instruction` | `ADVERSARIAL_FUZZING` | `6` | `far` | `0.0` |
| `receta` | `clauses` | `1B_full_v3` | `long_context_flooding` | `ADVERSARIAL_FUZZING` | `6` | `far` | `0.0` |
| `receta` | `clauses` | `1B_full_v3` | `near_ood_neighbor` | `HYBRID_BOUNDARY` | `12` | `far` | `0.0` |
| `receta` | `clauses` | `1B_full_v3` | `obfuscation_base64` | `ADVERSARIAL_FUZZING` | `12` | `far` | `0.0` |
| `receta` | `clauses` | `1B_full_v3` | `obfuscation_hex_rot13_leet` | `ADVERSARIAL_FUZZING` | `10` | `far` | `0.0` |
| `receta` | `clauses` | `1B_full_v3` | `ood_finanzas_derecho` | `OUT_OF_DOMAIN_BENIGN` | `12` | `far` | `0.0` |
| `receta` | `clauses` | `1B_full_v3` | `ood_hardware_arquitectura_musica` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `receta` | `clauses` | `1B_full_v3` | `ood_historia_literatura` | `OUT_OF_DOMAIN_BENIGN` | `10` | `far` | `0.0` |
| `receta` | `clauses` | `1B_full_v3` | `ood_medicina_ciencia` | `OUT_OF_DOMAIN_BENIGN` | `11` | `far` | `0.0` |
| `receta` | `clauses` | `1B_full_v3` | `ood_suite2_clean_astronomia` | `OUT_OF_DOMAIN_BENIGN` | `7` | `far` | `0.0` |
| `receta` | `clauses` | `1B_full_v3` | `ood_suite2_clean_legal` | `OUT_OF_DOMAIN_BENIGN` | `9` | `far` | `0.0` |
| `receta` | `clauses` | `1B_full_v3` | `ood_suite2_clean_medicina` | `OUT_OF_DOMAIN_BENIGN` | `9` | `far` | `0.0` |
| `receta` | `clauses` | `1B_full_v3` | `ood_suite2_es_oos` | `OUT_OF_DOMAIN_BENIGN` | `20` | `far` | `0.05` |
| `receta` | `clauses` | `1B_full_v3` | `ood_viajes_clima_deportes` | `OUT_OF_DOMAIN_BENIGN` | `12` | `far` | `0.0` |
| `receta` | `clauses` | `1B_full_v3` | `panaderia_fermentacion` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.3` |
| `receta` | `clauses` | `1B_full_v3` | `pivot_middle` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `receta` | `clauses` | `1B_full_v3` | `pivot_prefix` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `receta` | `clauses` | `1B_full_v3` | `pivot_suffix` | `HYBRID_BOUNDARY` | `10` | `far` | `0.1` |
| `receta` | `clauses` | `1B_full_v3` | `polarity_flip_indirect` | `HYBRID_BOUNDARY` | `8` | `far` | `0.0` |
| `receta` | `clauses` | `1B_full_v3` | `prompt_injection_jailbreak` | `ADVERSARIAL_FUZZING` | `25` | `far` | `0.0` |
| `receta` | `clauses` | `1B_full_v3` | `receta_completa` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.1` |
| `receta` | `clauses` | `1B_full_v3` | `salsas_emulsiones` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.125` |
| `receta` | `clauses` | `1B_full_v3` | `smuggle_json_yaml` | `HYBRID_BOUNDARY` | `10` | `far` | `0.0` |
| `receta` | `clauses` | `1B_full_v3` | `smuggle_recipe_footnote` | `HYBRID_BOUNDARY` | `10` | `far` | `0.2` |
| `receta` | `clauses` | `1B_full_v3` | `sustitucion_ingredientes` | `IN_DOMAIN_VALID` | `8` | `frr` | `0.125` |
| `receta` | `clauses` | `1B_full_v3` | `tecnica_culinaria` | `IN_DOMAIN_VALID` | `10` | `frr` | `0.0` |
| `receta` | `clauses` | `1B_full_v3` | `temperatura_tiempos` | `IN_DOMAIN_VALID` | `6` | `frr` | `0.16666666666666666` |

## 8. sqlite3 subprocess json canary

Marker counts are the stored `canary_sqlite_subprocess_json` object on the nested p10 decision. Token hit counts can exceed `n_marker` when one text contains more than one of the three tokens.
| domain | granularity | preset | n_marker | n in-domain | sqlite3 | subprocess | json | in-domain n | in-domain error | all n | all error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `python` | `full_only` | `1B_base_tech` | `17` | `11` | `5` | `5` | `15` | `11` | `0.0` | `17` | `0.88` |
| `python` | `clauses` | `1B_base_tech` | `17` | `11` | `5` | `5` | `15` | `11` | `0.09090909090909091` | `17` | `0.8695652173913043` |
| `python` | `full_only` | `1B_base_tech_noise` | `17` | `11` | `5` | `5` | `15` | `11` | `0.09090909090909091` | `17` | `0.8333333333333334` |
| `python` | `clauses` | `1B_base_tech_noise` | `17` | `11` | `5` | `5` | `15` | `11` | `0.09090909090909091` | `17` | `0.9090909090909091` |
| `python` | `full_only` | `1B_full` | `17` | `11` | `5` | `5` | `15` | `11` | `0.09090909090909091` | `17` | `0.8333333333333334` |
| `python` | `clauses` | `1B_full` | `17` | `11` | `5` | `5` | `15` | `11` | `0.09090909090909091` | `17` | `0.9090909090909091` |
| `python` | `full_only` | `1B_full_v3` | `17` | `11` | `5` | `5` | `15` | `11` | `0.09090909090909091` | `17` | `0.8333333333333334` |
| `python` | `clauses` | `1B_full_v3` | `17` | `11` | `5` | `5` | `15` | `11` | `0.18181818181818182` | `17` | `0.8571428571428571` |
| `receta` | `full_only` | `1B_base_tech` | `0` | `0` | `0` | `0` | `0` | `0` | `null` | `0` | `null` |
| `receta` | `clauses` | `1B_base_tech` | `0` | `0` | `0` | `0` | `0` | `0` | `null` | `0` | `null` |
| `receta` | `full_only` | `1B_base_tech_noise` | `0` | `0` | `0` | `0` | `0` | `0` | `null` | `0` | `null` |
| `receta` | `clauses` | `1B_base_tech_noise` | `0` | `0` | `0` | `0` | `0` | `0` | `null` | `0` | `null` |
| `receta` | `full_only` | `1B_full` | `0` | `0` | `0` | `0` | `0` | `0` | `null` | `0` | `null` |
| `receta` | `clauses` | `1B_full` | `0` | `0` | `0` | `0` | `0` | `0` | `null` | `0` | `null` |
| `receta` | `full_only` | `1B_full_v3` | `0` | `0` | `0` | `0` | `0` | `0` | `null` | `0` | `null` |
| `receta` | `clauses` | `1B_full_v3` | `0` | `0` | `0` | `0` | `0` | `0` | `null` | `0` | `null` |

## 9. Closed and open

Closed measurements:
- `bootstrap.refits_thresholds` is `true` on the manifest and on every cell.
- Primary statistic `document_level_CAL_ONLY`. Nested selection text is stored per cell in section 6.
- `[ORACLE_UPPER_BOUND]` stays in section 6.4. `[HOLDOUT_MAX_SCAN]` stays in section 4. Neither is the executive F1.
- twelve headlines are above the frozen TASK-013 CAL_ONLY p10, one are equal, and three are below.
Open, and not restated as a gain:
- `receta`/`full_only`/`1B_base_tech_noise` family `dir1024_clip_polboost` F1 `0.6136363636363636` is below `0.7403846153846154`.
- `receta`/`full_only`/`1B_full` family `dir1024_clip_polboost` F1 `0.6222222222222222` is below `0.7403846153846154`.
- `receta`/`full_only`/`1B_full_v3` family `polarity_v2_subset` F1 `0.7164179104477612` is below `0.7403846153846154`.
- `receta`/`full_only`/`1B_base_tech` family `polarity_v2_subset` F1 `0.7403846153846154` is tied with `0.7403846153846154`.
- receta/full_only selected `polarity_v2_subset` on `1B_base_tech`, `1B_full_v3`.
- `base_repaired` alpha=0 rows that sit below the frozen TASK-013 CAL_ONLY p10 are listed in section 3. Repairing F3 anchor retention did not, by itself, pass that frozen F_polarity headline on those rows.
- Adding `structural_symbol_noise` lowers the nested F1 on the pairs in section 2 where the later preset is below the earlier one. That drop is a loss on the headline F1.
- near-OOD, hybrid, smuggle, and dilution rates that remain away from zero are the stored rates in sections 0, 5, and 7. A clause-cell improvement does not cancel a full_only cell that kept the higher rate.
- In-domain rows with `n_below_1` above zero in section 4 show `S_struct` firing on valid text. The latency figures do not say that firing is harmless.
This report does not promote the scorer into the production path. The approval gate is still open.

