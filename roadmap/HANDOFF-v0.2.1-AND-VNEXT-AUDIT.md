# Handoff & Baseline Audit Dossier — `v0.2.1` → `vNext`

> **Propósito de este documento**: Transferir con cero pérdida de contexto toda la evidencia empírica, estado de ingeniería, invariantes resueltos, límites conocidos y calibración de trabajo al próximo arquitecto revisor antes de diseñar el motor **vNext**.
>
> **Regla #1 para quien reciba este documento**: **NO confíes ciegamente en este handoff.** Antes de proponer arquitectura nueva, auditá de cero el repositorio en vivo, contrastá cada número contra archivos/logs/CI reales y emití tu propio mapa epistémico (`Sabemos | Deducimos | Sigue abierto`).

---

## 1. Calibración Obligatoria: Rol, Perfil Cognitivo y Protocolo

Quien retome este repositorio debe operar exactamente bajo estas directivas:

1. **Rol**: Principal Software Architect / DevSecOps especializado en sistemas de alta densidad lógica, baja latencia (Rust / SIMD), almacenamiento columnar (LanceDB) y gateways/servicios de inferencia (Python / `uv` + TypeScript / React / `pnpm`).
2. **Perfil del propietario (`hbauzan`)**:
   * **Neurodivergencia**: **TEA + TDAH + Altas Capacidades Intelectuales (AACC, CI 130+)**.
   * **Trayectoria**: **Senior IT / Infraestructura (+30 años)**; prioridad absoluta en invariantes de sistema, fronteras de seguridad, red/RPC, latencia p50/p99, huella de caché/memoria, CI/CD y blast radius. No plantear derivaciones matemáticas extensas ni micro-detalles sintácticos salvo pedido expreso: traducir todo a arquitectura operativa e infraestructura con ejemplos concretos.
3. **Estilo estricto**:
   * **No-Fluff**: prohibidos saludos, preámbulos complacientes y cierres vacíos. Ir directo al mapa, tabla o código.
   * **Alta densidad esquemática**: tablas comparativas, bullets atómicos, enlaces `file://` con línea exacta a toda evidencia verificada.
   * **Literalidad cero ambigüedades (TEA)**: si un requerimiento o contrato admite dos interpretaciones, **FRENAR Y PREGUNTAR**, nunca asumir por omisión.
   * **Bilingüismo técnico natural**: español + terminología nativa en inglés (`CONTEXT.md`).
4. **Rigor epistémico bajo auditoría (`.agents/skills/transparent-dev-protocol/epistemic.md`)**:
   * Etiquetar afirmaciones atómicas con `[HECHO]`, `[VERIFICADO]`, `[INFERENCIA]`, `[SIN VERIFICAR]`, `[HIPÓTESIS]`, `[ASUNCIÓN]`, `[DECISIÓN]` o `[RIESGO]` según evidencia directa de esa sesión.
   * **Nunca** reportar un check como pasado si no se ejecutó tras el último cambio, ni extrapolar métricas.
5. **Protocolos, Toolchains y Reglas Innegociables**:
   * Leer `.agents/skills/transparent-dev-protocol/SKILL.md` (y módulos bajo demanda) y `.agents/skills/fabrica-de-software/SKILL.md` (`TASKS.md` + `/Users/hbauzan/treepwood/fabrica_de_software/agent.sh`).
   * **Toolchain canónico único**: `cargo` (Rust `1.94.1`), `pnpm` (`frontend/`, `11.8.0`), `uv` (`tools/`). Prohibido mezclar gestores (`pip`, `npm`, etc.).
   * **Autoría Git exclusiva**: `hbauzan` (`Héctor Andrés Bauzán Saavedra <hbauzan@gmail.com>`). Prohibido añadir `Co-authored-by:`.
   * **Prohibición lexical absoluta**: **NUNCA** mencionar nombres de asistentes, IDEs, modelos, bots o herramientas externas en código, comentarios, docstrings, tests, changelogs, roadmaps o mensajes de commit.

---

## 2. Qué Se Hizo (`v0.2.0` → `v0.2.1` / `TASK-007`)

A partir de una auditoría inicial del repo (que detectó 3 bugs críticos de integridad/seguridad y 7 desalineaciones entre documentación, benchmarks y runtime), se ejecutaron secuencialmente **10 Tracer Bullet Slices** con TDD, revisión independiente y CI verde:

| Slice | Área | Commit / Merge en `main` | Problema resuelto / Invariante cerrado | Ubicación clave |
| :---: | :--- | :--- | :--- | :--- |
| **01** | Storage LanceDB | `b642d19` / `8e62cc8` | Persistía siempre `top_k_len = 103` (duplicando votos en `Mode A` cuando `keep_n < 103`) y hardcodeaba `doc_count = 1`, `sha256 = 0`. Ahora persiste `top_k_len` real (`UInt16`, acotado `<= MAX_TOPK`), `CorpusManifest::UNPROVIDED` o SHA-256 real. | [`schema.rs`](file:///Users/hbauzan/treepwood/3hm-dimentional-fw/crates/sf-storage/src/schema.rs), [`registry.rs`](file:///Users/hbauzan/treepwood/3hm-dimentional-fw/crates/sf-storage/src/registry.rs), [`calibration.rs`](file:///Users/hbauzan/treepwood/3hm-dimentional-fw/crates/sf-storage/src/calibration.rs) |
| **02** | Frontera HTTP Proxy | `dd3990b` / `421064b` | `POST /api/v1/chat` aceptaba `NaN`, `Inf`, `epsilon < 0` y thresholds fuera de `[-1.0, 1.0]`. En `polarity == 1`, `epsilon < 0` invertía `lo > hi` (`0` votos) generando un `ALLOW ALL` silencioso. Ahora corta con HTTP `400` (`invalid_chat_override`) antes de dilatar. | [`chat_api.rs`](file:///Users/hbauzan/treepwood/3hm-dimentional-fw/crates/sf-proxy/src/chat_api.rs), [`gateway_s1_e2e.rs`](file:///Users/hbauzan/treepwood/3hm-dimentional-fw/crates/sf-proxy/tests/gateway_s1_e2e.rs) |
| **03** | Diagnostic Studio (`sf-ui`) | `7f0a2a4` / `f0cd2ce` | `handle_inspect` evaluaba cada sub-cláusula con `query_vec` del prompt completo; `sf-ui/src/chat.rs` corría pairwise sobre vectores mock e ignoraba overrides inválidos sin HTTP `400`. Corregido con embeddings por cláusula, guardia mock (`BREACH` token) y paridad HTTP `400`. | [`handlers.rs`](file:///Users/hbauzan/treepwood/3hm-dimentional-fw/crates/sf-ui/src/handlers.rs), [`chat.rs`](file:///Users/hbauzan/treepwood/3hm-dimentional-fw/crates/sf-ui/src/chat.rs) |
| **04** | Seeding & Mock | `d0bdcd2` / `f0cd2ce` | `setup.sh` y `seed_canonical_locks` hidrataban solo 55 pares (faltaba `"python"` y los otros 10 base). Ahora siembra **66 locks** (11 base + 55 pares) y `MockBatchEmbedder` resuelve centroides por `domain_id`. | [`seed_canonical_locks.rs`](file:///Users/hbauzan/treepwood/3hm-dimentional-fw/crates/sf-bench/src/bin/seed_canonical_locks.rs), [`sf_proxy.rs`](file:///Users/hbauzan/treepwood/3hm-dimentional-fw/crates/sf-proxy/src/bin/sf_proxy.rs), [`setup.sh`](file:///Users/hbauzan/treepwood/3hm-dimentional-fw/setup.sh) |
| **05** | RPC Batch vs Early-Exit | `7c11e9d` / `f0cd2ce` | Se decidió **mantener 1 solo batch RPC** `[prompt, clauses...]` hacia GPU/MPS (ahorra un segundo round-trip de 24–600+ ms para tráfico sano) y corregir docs: el short-circuit ahorra checks CPU/SIMD (`clauses_skipped`), no el batch neuronal previo. | [`handler.rs`](file:///Users/hbauzan/treepwood/3hm-dimentional-fw/crates/sf-proxy/src/handler.rs), [`cascade.rs`](file:///Users/hbauzan/treepwood/3hm-dimentional-fw/crates/sf-proxy/src/cascade.rs), [`CHANGELOG.md`](file:///Users/hbauzan/treepwood/3hm-dimentional-fw/CHANGELOG.md) |
| **06** | Suite 2 E2E + Nota vNext | `0a23a0a`, `085e0c2` / `f0cd2ce` | Se rehizo Suite 2 pasando prompts reales por `InputNormalizer` + `ClauseSegmenter` + `BAAI/bge-m3` (`torch.float32`) sobre 66 locks calibrados con semillas unificadas a `canonical_corpus.rs` y matrices estratificadas `EN` / `ES` / `pooled`, agregando desglose exacto de FPR (`Mode A` vs `evaluate_pairwise_containment` `Mode C`) y sembrando la nota futura sin alterar el scorer actual. | [`oos_benchmark.rs`](file:///Users/hbauzan/treepwood/3hm-dimentional-fw/crates/sf-bench/src/oos_benchmark.rs), [`suite2_catalog.rs`](file:///Users/hbauzan/treepwood/3hm-dimentional-fw/crates/sf-bench/src/suite2_catalog.rs), [`generate_real_public_benchmarks.py`](file:///Users/hbauzan/treepwood/3hm-dimentional-fw/tools/generate_real_public_benchmarks.py), [`future-holistic-resonance-gate.md`](file:///Users/hbauzan/treepwood/3hm-dimentional-fw/roadmap/future-holistic-resonance-gate.md) |
| **07** | Alcance Ingress-Only | `c8ea162` / `f0cd2ce` | Se declaró oficialmente `v0.2.x` como **Ingress-Only Semantic Firewall**; Egress Semantic Amplification (SSE out-guard) queda diferido a `v1.1+`. | [`architecture_spec.md`](file:///Users/hbauzan/treepwood/3hm-dimentional-fw/architecture_spec.md), [`README.md`](file:///Users/hbauzan/treepwood/3hm-dimentional-fw/README.md) |
| **08** | Gobernanza y Archivo | `0dde425`, `a2f19f3` / `f0cd2ce` | `GET /health` y catálogo unificados vía `env!("CARGO_PKG_VERSION")`; eliminada cabecera prematura `1.0.0` de `CHANGELOG.md`; corregida ruta `/api/v1/upstream/env` y archivados prompts cerrados. | [`handlers.rs`](file:///Users/hbauzan/treepwood/3hm-dimentional-fw/crates/sf-ui/src/handlers.rs), [`roadmap/archived/`](file:///Users/hbauzan/treepwood/3hm-dimentional-fw/roadmap/archived) |
| **09** | Verdad Empírica & `README` | `a452bfa` / `f0cd2ce` | `load_benchmark.rs` persiste reportes JSON versionados; `README.md` ahora separa Gate CPU (`--release`), Gateway Mock, Embedder MPS HTTP real, huella real (`12,693 B` / `12,736 B`), fórmula coseno normalizada, `ceil(0.10 * 1024) = 103`, Suite 1 como smoke sintético, y autopsia completa de Suite 2. | [`load_benchmark.rs`](file:///Users/hbauzan/treepwood/3hm-dimentional-fw/crates/sf-bench/src/bin/load_benchmark.rs), [`reports/load_benchmark_mock.json`](file:///Users/hbauzan/treepwood/3hm-dimentional-fw/reports/load_benchmark_mock.json), [`reports/load_benchmark_mps_http.json`](file:///Users/hbauzan/treepwood/3hm-dimentional-fw/reports/load_benchmark_mps_http.json), [`.gitignore`](file:///Users/hbauzan/treepwood/3hm-dimentional-fw/.gitignore) |
| **10** | CI Multi-Arquitectura | `75fff5d` / `f0cd2ce` | Workflow CI con `rust-x86_64` (`ubuntu-latest`), `rust-arm64` (`macos-latest`) y `frontend` (`pnpm`), validado en verde en GitHub Actions. | [`.github/workflows/ci.yml`](file:///Users/hbauzan/treepwood/3hm-dimentional-fw/.github/workflows/ci.yml) |
| **Release** | Tag & Handoff `v0.2.1` | `v0.2.1` | Promoción limpia de versiones `0.2.0` → `0.2.1`, archivo de `v0.2-hardening-and-empirical-truth.prompt.md`, y este dossier de handoff. | [`Cargo.toml`](file:///Users/hbauzan/treepwood/3hm-dimentional-fw/Cargo.toml), [`manifest.json`](file:///Users/hbauzan/treepwood/3hm-dimentional-fw/manifest.json), [`frontend/package.json`](file:///Users/hbauzan/treepwood/3hm-dimentional-fw/frontend/package.json) |

---

## 3. Resultados Empíricos Verificados (Baseline Real `v0.2.1`)

### 3.1 CI, Tests, Latencia y Huella de Memoria
* **GitHub Actions CI**:
  * Run [`44634446127`](https://github.com/hbauzan/3hm-dimensional-fw/actions/runs/44634446127) (`feat/v0.2-slices-03-10` @ `908bba3`): **`success`** (`rust-x86_64` 14m11s, `rust-arm64` 16m55s, `frontend` 15s).
  * Run [`44637292040`](https://github.com/hbauzan/3hm-dimensional-fw/actions/runs/44637292040) (`main` @ `f0cd2ce`): **`success`**.
* **Tests locales reportados en cierre `TASK-007` (`908bba3`)**: `cargo fmt --all -- --check` (0), `cargo clippy --workspace --all-targets -- -D warnings` (0), `cargo test --workspace` (**111 passed, 0 failed, 0 ignored**), `pnpm --dir frontend lint && build && test` (**10 archivos, 44 tests**). *(Re-ejecutado nuevamente tras bump `0.2.1`).*
* **CPU Gate (`sf-kernels`, `--release`, Apple M4, 1,000 iteraciones Suite 2)** — [`reports/load_benchmark_mock.json`](file:///Users/hbauzan/treepwood/3hm-dimentional-fw/reports/load_benchmark_mock.json):
  * `p50`: **`0.542 µs`** | `p99`: **`0.583 µs`**. (En perfil `dev`: `25.503 µs` p50 / `31.503 µs` p99).
* **Gateway HTTP in-process mock (`200 RPS`, `5s`, `1,000 reqs`)** — [`reports/load_benchmark_mock.json`](file:///Users/hbauzan/treepwood/3hm-dimentional-fw/reports/load_benchmark_mock.json):
  * `p50`: **`0.141951 ms`** | `p95`: **`0.166271 ms`** | `p99`: **`0.187391 ms`** | `RSS`: **`41.828125 MB`**.
* **Embedder GPU real (`BAAI/bge-m3`, Metal `mps`, `float32`, 16 calls `"a short clause"` vía HTTP `:8080`)** — [`reports/load_benchmark_mps_http.json`](file:///Users/hbauzan/treepwood/3hm-dimentional-fw/reports/load_benchmark_mps_http.json):
  * `p50`: **`23.775 ms`** | `p95 / p99`: **`629.247 ms`**. *(Logs previos en `sf_tei_mps.log` con batches `n=32`: startup `9996.7 ms`, p50 `36.44–130.98 ms`, p99 `523.57–607.52 ms`)*.
* **Huella real de locks**:
  * Fila almacenada `python`: **`12,693 bytes`** (`838,343 bytes` para 66 filas).
  * Layout `DomainHypercubeLock` en memoria: **`12,736 bytes`** (`840,576 bytes` para 66 structs antes de `String` heap → **catálogo L2/L3**, no L1 de 8 KB).

### 3.2 Autopsia de Suite 2 (`BAAI/bge-m3`, `K = 103`, `CANONICAL_COSINE = 0.50`, `epsilon = 0.0`)

| Matriz | Limpias (`n`) | FPR Primario (`Mode C`) | FPR Producción (`evaluate_pairwise_containment` Mode C) | FPR Suite (`Mode A` estricto) | Ataques (`n`) | Fugas Coseno L1 | Bloqueados (`Mode A` suite) |
| :--- | :---: | :--- | :--- | :--- | :---: | :---: | :---: |
| **EN (`python`)** | 10 | `L1=0, L2=0, L3=0` (**0/10**) | `pares=3` (**3/10 = 30.0%**) | `pares=3` (**3/10 = 30.0%**) | 82 | 48/82 (58.54%) | **64/82 (78.05%)** |
| **ES (10 dom.)** | 90 | `L1=0, L2=3, L3=0` (**3/90**) | `L2=3, pares=25` (**28/90 = 31.1%**) | `L2=3, pares=30` (**33/90 = 36.7%**) | 90 | 41/90 (45.56%) | **90/90 (100.0%)** |
| **Pooled** | 100 | **3/100 (3.00%)** | **31/100 (31.00%)** | **36/100 (36.00%)** | 172 | 89/172 (51.74%) | **154/172 (89.53%)** |

### 3.3 Diagnóstico de Causa Raíz del Motor Actual (`v0.2.1`)
1. **El firewall primario (`L1 + L2 + L3 Mode C`) tiene `3%` FPR**: `0/100` en L1, `0/100` en L3 primario, y solo `3/100` en L2 (cortes agresivos de [`segmenter.rs`](file:///Users/hbauzan/treepwood/3hm-dimentional-fw/crates/sf-proxy/src/segmenter.rs#L11-L26) en conectores como `" y "` cuando un fragmento corto pierde contexto debajo de `0.50`).
2. **La capa Pairwise actual explica `28/31` (`90%`) de los falsos positivos en producción**:
   * Al unificar semillas reales de `16` oraciones en [`calibration.rs`](file:///Users/hbauzan/treepwood/3hm-dimentional-fw/crates/sf-storage/src/calibration.rs#L462-L518) con `epsilon = 0.0`, **49 de 55 pares colapsan a `top_k_len = 0`** (incluyendo `python_receta`).
   * Los **6 pares** que conservan ejes disjuntos tienen muy pocas dimensiones activas (`quorum_k = 1`). Con `polarity = 0` exigen entrar en una micro-caja min/max de 16 muestras sin tolerancia; con `polarity = 1` (`have < 1`) prohíben cualquier solapamiento (`0` hits). Cualquier consulta legítima nueva cae rechazada con facilidad.
3. **Fuga del `21.95%` en ataques `EN` (`18/82`)**: Al colapsar casi todos los pares de `python`, el gate depende de `Mode C (K = 103 / 1015)`. Sobre $S^{1023}$, muchas coordenadas no discriminantes rondan cero para textos no relacionados y alcanzan `103` aciertos por azar, sin ponderar ni severidad de desvío ni selectividad del eje.

---

## 4. Puntos Abiertos / Deuda Conocida a Auditar Antes de `vNext`

El próximo auditor debe comprobar estos puntos explícitamente:

1. **Playwright E2E (`pnpm --dir frontend test:e2e`)**: No corre en `.github/workflows/ci.yml` (`frontend/e2e/playground.spec.ts` requiere SPA `:5173` + `sf-proxy` `:8088` corriendo). Re-verificar ejecución real contra `v0.2.1`.
2. **`recall` desglosado en modo productivo (`evaluate_pairwise_containment` Mode C)**: En `oos_benchmark.rs`, el split `Mode A` vs `Mode C` productivo se midió para `fp` (`36/100` vs `31/100`), pero el `recall` específico bajo `evaluate_pairwise_containment` (`Mode C`) no quedó tabulado por separado frente a `Mode A` (`154/172`). Medirlo al auditar.
3. **Rama AVX-512 en `sf-kernels`**: Compila bajo `#[cfg(target_arch = "x86_64")]` en CI Ubuntu (`avx2` + `fma` corre), pero ejecución efectiva de [`avx512.rs`](file:///Users/hbauzan/treepwood/3hm-dimentional-fw/crates/sf-kernels/src/simd/avx512.rs) depende de si el runner virtualizado expone `avx512f`.
4. **Hidración fallback en `sf_ui.rs` vs `setup.sh`**: Si `sf-ui` arranca sin `--lancedb-uri` ([`sf_ui.rs`](file:///Users/hbauzan/treepwood/3hm-dimentional-fw/crates/sf-ui/src/bin/sf_ui.rs#L52-L73)), todavía autohidrata **55 locks sintéticos** (`generate_canonical_locks()`) con `CorpusManifest::UNPROVIDED` (y `load_benchmark.rs` hace lo mismo en su harness mock), distinto de los **66 locks** canónicos de `setup.sh` / `seed_canonical_locks`.
5. **Egress Semantic Amplification (`v1.1+`)**: Fuera de `v0.2.1`; `upstream.rs` mantiene passthrough SSE sin inspección de salida.

---

## 5. Visión Semilla para `vNext` (Pendiente de Diseño Post-Auditoría)

Lineamiento arquitectónico dado por `hbauzan` para la próxima versión mayor (registrado también en [`future-holistic-resonance-gate.md`](file:///Users/hbauzan/treepwood/3hm-dimentional-fw/roadmap/future-holistic-resonance-gate.md)):

* **De "conteo discreto (`K = 103`)" a "Resonancia Holística Continua"**:
  * Evaluar el conjunto completo de dimensiones activas (no cortar arbitrariamente en `103` aciertos binarios).
  * Ponderar la fuerza/penalidad de cada coordenada según la holgura calibrada `(hi_d - lo_d)`:
    * Dimensiones muy estrechas/estables (p. ej. rango `[0.000001, 0.000002]`) indican alta especificidad de dominio y deben pesar fuerte cuando la consulta se aleja.
    * Dimensiones anchas/laxas (p. ej. rango `[0.02, 0.04]`) indican alta varianza natural y deben tolerar mayor excursión.
  * Obtener una métrica global de **resonancia / energía de desvío** (cuánto y en qué dimensiones críticas se aleja de los envelopes `[lo_d, hi_d]`), complementada eventualmente con mayor muestra de calibración, manejo de conectores del segmentador y revisión del rol de los pares `OvO`.

---

## 6. Prompt Listo para Iniciar la Próxima Sesión (Auditoría + Roadmap `vNext`)

Copiá y pegá esto en una sesión nueva para retomar con exactitud el mismo criterio y rigor:

```markdown
Leé `.agents/skills/transparent-dev-protocol/SKILL.md`, `.agents/skills/transparent-dev-protocol/epistemic.md`, `.agents/skills/fabrica-de-software/SKILL.md`, `CONTEXT.md`, `TASKS.md` y `roadmap/HANDOFF-v0.2.1-AND-VNEXT-AUDIT.md`.

### Reglas de Perfil y Trabajo
- Perfil del usuario: **TEA + TDAH + AACC (CI 130+)**, **Senior IT / Infraestructura (+30 años)**. Cero saludos, cero relleno, cero desarrollo matemático abstracto: traducí todo a arquitectura de sistemas, invariantes, red, caché/memoria, latencia p50/p99 y trade-offs reales. Ante cualquier ambigüedad, frená y preguntá.
- Autoría exclusiva: `hbauzan <hbauzan@gmail.com>`. **Prohibición absoluta**: jamás mencionar asistentes, IDEs, modelos o herramientas externas en código, comentarios, commits ni docs.
- Toolchain único: `cargo`, `pnpm`, `uv`.

### Paso 1 Obligatorio — Auditoría Crítica Independiente (NO propongas roadmap todavía)
No des por cierto nada del handoff sin verificarlo directamente en el repositorio actual (`v0.2.1` en `main`):
1. Verificá estado Git (`main`, tags, CI en GitHub Actions), código fuente clave (`sf-kernels`, `sf-storage`, `sf-proxy`, `sf-ui`, `sf-bench`) y reportes JSON en `reports/`.
2. Ejecutá verificación local real (`cargo fmt --all -- --check`, `cargo clippy --workspace --all-targets -- -D warnings`, `cargo test --workspace`, `pnpm --dir frontend lint && pnpm --dir frontend build && pnpm --dir frontend test`, e inspeccioná viabilidad/resultado de Playwright E2E `test:e2e` y los puntos abiertos de la Sección 4 del handoff).
3. Entregame primero el **Mapa Epistémico completo (`[HECHO]`, `[VERIFICADO]`, `[INFERENCIA]`, `[SIN VERIFICAR]`, `[RIESGO]` + matriz `Sabemos | Deducimos | Sigue abierto`)** auditando si lo declarado en `v0.2.1` y en `HANDOFF-v0.2.1-AND-VNEXT-AUDIT.md` coincide 100% con la realidad del repo.

### Paso 2 — Solo Después de Entregar la Auditoría
Con la línea base confirmada (primario 3% vs pares 31% vs fuga EN 22%, etc.), presentame opciones arquitectónicas claras (A/B/C con pros, contras, costo en latencia/memoria y riesgo) para diseñar el roadmap de **vNext** centrado en la **Resonancia Holística Continua** (ponderada por holgura `(hi_d - lo_d)` en todas las dimensiones activas) y las mejoras de calibración/segmentación que detectes.
```

