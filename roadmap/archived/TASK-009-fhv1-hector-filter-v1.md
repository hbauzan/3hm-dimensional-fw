---
task_id: "TASK-009"
status: "DONE"
assigned_architect: "maximum-architect-agent"
protocol: "transparent-dev-protocol"
title: "Implementación de Filtro Héctor v1 (fhv1) AABB IEEE-754 Lossless"
created_at: "2026-11-21T13:40:00-03:00"
---

# TASK-009: Implementación de Filtro Héctor v1 (fhv1) AABB IEEE-754 Lossless

## 1. Objective
Implementar el filtro determinista `fhv1` (**Exhaustive Coordinate-Wise Axis-Aligned Bounding Box** en precisión nativa IEEE 754 `f64`, zero-rounding end-to-end) según [`roadmap/fhv1-hector-filter-v1.roadmap.md`](roadmap/fhv1-hector-filter-v1.roadmap.md) sobre el branch dedicado `feat/fhv1-hector-filter-v1`, preservando `3HM` (`v0.2.1`) sin regresiones.

## 2. Invariants & Constraints
- **Canonical Toolchain**: `cargo` (Rust `1.94.1`), `pnpm` (`frontend/`, `11.8.0`), `uv` (`tools/`). Cero mezcla de gestores.
- **Single Branch & Atomic Commits**: todo el desarrollo vive en `feat/fhv1-hector-filter-v1` (desde `main`), con commits atómicos verificados por cada Slice (`1..8`). Prohibido `push` o `merge` a `main` antes del Approval Gate humano.
- **Zero-Rounding RFC-003 Extended**: `Float64` en LanceDB (`Arrow =58.4.1`), JSON `f64` nativo, `rust_xlsxwriter` crudo y `String(val)` en vistas `fhv1`. Conservar `.toFixed(4)` en `format.ts` únicamente para tarjetas `3HM` (`BreachCard.test.tsx`).
- **Kernel Purity & Deps**: `sf-kernels` permanece 0-dep (`observed_bits: u64`, sin `serde`). Nuevos crates: `rust_xlsxwriter`, `parquet = "=58.4.1"`, `zip`. Charting SPA: `echarts` (`echarts/core` + `CanvasRenderer`).
- **eval_granularity (1B)**: `full_only` (`[normalized_full_text]`), `clauses` (`[normalized_full_text]` + `ClauseSegmenter` Option 2C), `full_mirror` (expansor multi-granularidad 10 estrategias). Sin early-exit; registra siempre `full_text_passed` y `all_chunks_passed`.
- **Chat Compatibility & `3hm_plus_fhv1`**: `buildChatRequest` omite `filter_mode` en `"3hm_default"`. Rechazos `fhv1` emiten `fhv1_ingress_breach` (`FHV1_AABB_ENVELOPE`). En `3hm_plus_fhv1` se evalúa y persiste siempre la traza `fhv1` en `fhv1_audit_traces` incluso si `3HM` bloquea primero.
- **Non-Interactive Runtime & LanceDB Guard**: prohibido ejecutar `./setup.sh`. Usar comandos no-interactivos con polling de `/health` y limpieza de PIDs. **PROHIBIDO borrar o sobreescribir `domain_hypercubes` en `data/sf-lancedb`** (`seed_canonical_locks` o borrado de `data/sf-lancedb` rompe los 9 E2E de `3HM`).
- **Live `:8080` Scope & `--augment-llm`**: calibración y benchmark en vivo contra `:8080` corren **solo en modo determinista** (sin `--augment-llm`). Validar `--augment-llm` mediante tests offline de contrato/mock HTTP (`--provider` obligatorio, `.env`, caché SHA-256 JSONL).
- **Axum 0.8 & Protected Selectors**: rutas dinámicas con `{id}` (nunca `:id`); preservar los 11 selectores protegidos de `Playground.test.tsx` / `playground.spec.ts` y `w-60` / `h-[100dvh]`.
- **3HM & Version Fence**: prohibido modificar `domain_hypercubes`, scoring `3HM`, `Suite 1` / `Suite 2` o bumpear `0.2.1` (cambios bajo `## [Unreleased]` en `CHANGELOG.md`).
- **Exclusive Authorship & Hygiene**: `hbauzan <hbauzan@gmail.com>`. Cero `Co-authored-by:` y cero menciones a asistentes, bots o modelos. Prohibido `git add -A` o stagear `repomix-output.xml`.

## 3. Tracer Bullet Slices
- [x] **Slice 1** (`feat/fhv1-hector-filter-v1`): `sf-kernels/src/fhv1.rs` (Welford `f64`, tiers por cuantiles, AABB estricto 1024/1015, 1-ULP/16-ULP tests) + `validate_raw_f64_slice` + `embed_batch_raw_f64` (`TeiHttpEmbedder`, `TeiGrpcEmbedder`, `MockBatchEmbedder` fail-closed) + test `normalize=False` en `tools/test_bge_m3_mps_server.py`.
- [x] **Slice 2** (`feat/fhv1-hector-filter-v1`): 4 tablas `fhv1_*` en `sf-storage` (`Arrow =58.4.1`, `Float64`), `Fhv1Store` perezoso, exportador `.xlsx` (2 hojas + auto-split `.zip` `>10,000`), `.csv` y `.parquet`, más `fhv1_roundtrip_test.rs` con paridad `0-ULP` (`to_bits()`).
- [x] **Slice 3** (`feat/fhv1-hector-filter-v1`): `fhv1_pipeline.rs` (expansor determinista 10 estrategias + `expand_for_granularity`), `fhv1_corpus.rs`, `fhv1_calibrate` CLI, `tools/augment_fhv1_corpus.py` (`uv` PEP 723, `--provider` obligatorio) con tests mock + calibración determinista en vivo contra `:8080` (`python` y `receta`).
- [x] **Slice 4** (`feat/fhv1-hector-filter-v1`): `tools/generate_fhv1_benchmark.py` (100% offline default, `>=400` prompts reales/dominio, `0%` overlap con calibración) + `fhv1_eval.rs` + `fhv1_benchmark` CLI + `fhv1_e2e_test.rs` + corrida determinista en vivo contra `:8080`.
- [x] **Slice 5** (`feat/fhv1-hector-filter-v1`): `fhv1_api.rs` (Axum `{id}`, CORS `content-disposition`), extensión backward-compatible de `/api/v1/chat` (`fhv1_ingress_breach`, `3hm_plus_fhv1`), arranque perezoso de `Fhv1Store`, actualización de 7 literales `ProxyAppState` y `fhv1_api_e2e_test.rs`.
- [x] **Slice 6** (`feat/fhv1-hector-filter-v1`): `fhv1.ts`, `fhv1Client.ts`, `StudioShell` en `main.tsx`, extensión de `Playground.tsx` (switch motor, Direct Lab `/evaluate`, `Fhv1LiveAuditPanel`), `parseChatBreach`/`BreachCard.tsx`, manteniendo 44+ Vitest y 9 Playwright `playground.spec.ts` en verde.
- [x] **Slice 7** (`feat/fhv1-hector-filter-v1`): `echarts` (`echarts/core` + `CanvasRenderer`), `Fhv1VarianceStudio.tsx` (calibración UI, métricas/cuantiles, gráficos 1024D, descarga `.xlsx`/`.csv`/`.parquet`, tabla lossless 1024D) y `Fhv1VarianceStudio.test.tsx`.
- [x] **Slice 8** (`feat/fhv1-hector-filter-v1`): `Fhv1BenchmarkExplorer.tsx` (dashboard 4 cuadrantes, tabla paginada, overlay 1024D + drill-down), `frontend/e2e/fhv1.spec.ts`, doc-sync (`CONTEXT.md`, `CONTEXT-MAP.md`, `architecture_spec.md`, `CHANGELOG.md`) y validación completa del workspace + `agent.sh validate`.
