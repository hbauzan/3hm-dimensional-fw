---
task_id: "TASK-010"
status: "IN_PROGRESS"
assigned_architect: "maximum-architect-agent"
protocol: "transparent-dev-protocol"
title: "Hardening, refactor y cobertura completa de tests para Filtro Héctor v1 (fhv1)"
created_at: "2026-11-21T18:53:00-03:00"
---

# TASK-010: Hardening, refactor y cobertura completa de tests para Filtro Héctor v1 (`fhv1`)

## 1. Objective
Cerrar los detalles técnicos detectados en la auditoría post-`TASK-009` y completar la cobertura de tests unitarios, de integración REST/batch-reuse, componentes Vitest y Playwright E2E en vivo según [`roadmap/fhv1-hardening-and-test-coverage.roadmap.md`](roadmap/fhv1-hardening-and-test-coverage.roadmap.md) sobre el branch `feat/fhv1-hector-filter-v1`.

## 2. Invariants & Constraints
- **Canonical Toolchain**: `cargo` (`1.94.1`), `pnpm` (`frontend/`, `11.8.0`), `uv run --script` (`tools/`). Cero mezcla de gestores.
- **Single Branch & Atomic Commits**: todo el trabajo continúa sobre `feat/fhv1-hector-filter-v1` (desde `e448906`), con commits atómicos verificados por cada Slice (`1..4`). Prohibido `push` o `merge` a `main` antes del Approval Gate humano.
- **Code Quality & Precision**: deduplicar `stats_from_profile` / lógica repetida en `chat_api.rs`, medir `eval_latency_ns` real en el path `reuse`, estampar `x-sf-trace-id` + `x-sf-fhv1-decision: PASS` en `/api/v1/chat` (`fhv1` / `3hm_plus_fhv1`), usar `trace_id` único atómico (`AtomicU64`) y agrupar `trace_id = {run_id}-{input_id}` en benchmarks. Cero `.toFixed()` en `fhv1`; `sf-kernels` sigue 0-dep.
- **3HM & LanceDB Fence**: **PROHIBIDO borrar o pisar `data/sf-lancedb/domain_hypercubes.lance`**, cambiar `0.2.1`, alterar `formatGate` `.toFixed(4)` o romper los 11 selectores protegidos y `3hm_default` payload.
- **Non-Interactive Services**: prohibido `./setup.sh`. Usar el runbook en background de §1.3 con polling y limpieza de PIDs.
- **Exclusive Authorship & Hygiene**: `hbauzan <hbauzan@gmail.com>`. Cero `Co-authored-by:` y cero menciones a asistentes, bots o modelos. Prohibido `git add -A` o stagear `repomix-output.xml`.

## 3. Tracer Bullet Slices
- [x] **Slice 1** (`feat/fhv1-hector-filter-v1`): deduplicar `sf_storage::stats_from_profile` y bloque `3hm_plus_fhv1` en `chat_api.rs`, medir `eval_latency_ns` en path `reuse`, emitir `x-sf-trace-id` + `x-sf-fhv1-decision: PASS` en chat `fhv1`/`3hm_plus_fhv1`, usar `AtomicU64` en `new_trace_id`, unificar `trace_id` por prompt en benchmarks, y sumar tests faltantes en `fhv1_precision_test.rs` y `fhv1_roundtrip_test.rs`.
- [x] **Slice 2** (`feat/fhv1-hector-filter-v1`): completar unit tests en `fhv1_corpus.rs` y `fhv1_eval.rs`, y expandir `fhv1_api_e2e_test.rs` cubriendo `fhv1_store: None` (`503`/empty `200`), métricas/cuantiles y `400`/`404`, `/evaluate` 3 granularidades + headers, `/benchmarks/run` + `409` overlap, `.xlsx` simple, `/api/v1/chat` PASS/breach/contador de reuso único de `/embed` en `3hm_plus_fhv1`, filtros de trazas y unicidad en ráfaga.
- [ ] **Slice 3** (`feat/fhv1-hector-filter-v1`): agregar tabla `Granularity comparison` y atribución `oob_catch_counts` en `Fhv1BenchmarkExplorer.tsx` / `fhv1Charts.ts`, alinear validación `0 <= P25 < P75 < P90 <= 1` en `Fhv1VarianceStudio.tsx`, crear `StudioShell.test.tsx` y completar tests en `fhv1.test.ts`, `BreachCard.test.tsx`, `Playground.test.tsx`, `Fhv1VarianceStudio.test.tsx` y `Fhv1BenchmarkExplorer.test.tsx`.
- [ ] **Slice 4** (`feat/fhv1-hector-filter-v1`): ampliar `frontend/e2e/fhv1.spec.ts` (+3 tests E2E en vivo: chat `fhv1` + `3hm_plus_fhv1` dual-trace, Variance Studio métrica/cuantil + descarga `.csv`/`.xlsx`, Explorer tabla comparativa + paginación + drill-down), actualizar `[Unreleased]` en `CHANGELOG.md`, correr el Full Milestone Verification Gate (11 checks incluyendo `14` Playwright E2E, `agent.sh validate` y `agent.sh notify`) y frenar en el Approval Gate.
