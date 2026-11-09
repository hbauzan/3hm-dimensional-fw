# TASK SPECIFICATION: WEBGUI COMPREHENSIVE E2E TESTING, MOCK STABILIZATION & OVERRIDE DIAGNOSTICS

## 1. Project Context & Current State (Ground Truth)

* **Repository**: `3hm-dimensional-fw` (Three-Headed Semantic Firewall).
* **Target Subsystems**:
  * **Frontend SPA**: React 19 + TypeScript 5.8 + Vite 8.3 + Tailwind CSS v4 in [`frontend/`](file:///Users/hbauzan/treepwood/3hm-dimentional-fw/frontend) (SF-Proxy Playground running on `http://127.0.0.1:5173`).
  * **Backend Gateway**: Rust `sf-proxy` running on `http://127.0.0.1:8088` (`/v1/chat/completions` and `/api/v1/chat`).
  * **Storage Engine**: LanceDB at `data/sf-lancedb` (`domain_hypercubes` table with 55 canonical pairwise locks + 11 domain locks).
* **Canonical Toolchain**:
  * Frontend: `pnpm` exclusively (`pnpm test`, `pnpm test:e2e`, `pnpm run lint`, `pnpm run build`). Zero mixing of npm/yarn/bun.
  * Backend: `cargo` exclusively (`cargo test`, `cargo clippy`, `cargo build`).
  * Local Factory CLI: `/Users/hbauzan/treepwood/fabrica_de_software/agent.sh` with `uv`.
* **Current Quality Baseline**:
  * Frontend: 36 unit/integration tests passing in Vitest (`pnpm test`), 0 linter errors (`pnpm oxlint`), 0 TypeScript errors (`pnpm run build`).
  * Backend: 100% test pass across `cargo test --workspace`.
* **Empirical Failure Identified (The L2 Perilla Issue)**:
  * When adjusting the **L2 Clause Threshold** slider in `frontend/src/ui/Playground.tsx` under `mock` mode:
    1. Moving the slider triggers `tune()`, setting `overridesArmed: true` and sending `overrides: { l1_threshold, l2_threshold, quorum_k, epsilon }`.
    2. Because `session.overrides.epsilon` defaults to `0.0`, `sf-proxy/src/chat_api.rs:apply_chat_overrides()` collapses dilated coordinate bounds (`lo - epsilon`, `hi + epsilon`), stripping calibration margins.
    3. Concurrently, `handle_api_v1_chat()` executes `evaluate_pairwise_containment()` against all 10 pairwise differential locks for `python` (e.g., `python_receta`). In mock mode, the mock embedder returns `centroid(python)`, which does not fall inside the differential envelope of `python_receta`.
    4. The gateway returns `HTTP 403 Forbidden` with a `PairwiseBreachEnvelope`: `{"error":{"kind":"ddi_ingress_breach","code":"SEMANTIC_CONTAINMENT_BREACH", ...}}`.
    5. The frontend's `parseChatBreach()` expects `{ decision: "BREACH", failing_tier: ... }` and fails to parse `PairwiseBreachEnvelope`.
    6. `postChat()` falls through to `{ kind: 'error', status: 403, message: ... }`, displaying an unhandled raw error banner `[HTTP 403] {"error": ...}` instead of the structured `BreachCard`.

---

## 2. Objective & Scope

### 2.1 Objective
Implement an automated end-to-end (E2E) testing suite with Playwright in [`frontend/`](file:///Users/hbauzan/treepwood/3hm-dimentional-fw/frontend) combined with interactive browser validation, systematically auditing and stabilizing **every single function and control** of the WebGUI (Playground). Fix the mock-mode override/pairwise collapse bug, normalize pairwise breach envelopes so `BreachCard` renders cleanly on all 403s, and ensure zero regressions across both TypeScript and Rust test suites.

### 2.2 Scope
1. **Mock Gateway & Pairwise Telemetry Stabilization**:
   - In `crates/sf-proxy/src/chat_api.rs` and `cascade.rs`: when `mock` upstream / `MockBatchEmbedder` is active, bypass or calibrate pairwise differential checks so valid mock prompts pass without false breaches.
   - In `frontend/src/domain/breach.ts`: update `parseChatBreach()` to recognize both standard `ChatBreachDto` and `PairwiseBreachEnvelope` (`L3_PAIRWISE_QUORUM`), mapping them into a unified breach structure.
   - In `frontend/src/domain/session.ts` and `Playground.tsx`: prevent default `epsilon: 0.0` from stripping lock dilation when only tuning L1 or L2 sliders.
2. **Headless E2E Test Suite (Playwright)**:
   - Configure `@playwright/test` in `frontend/` under canonical `pnpm`.
   - Add `"test:e2e": "playwright test"` to `frontend/package.json`.
   - Comprehensive test specs covering all 6 functional areas of the WebGUI.
3. **Comprehensive Functional WebGUI Audit**:
   - **Area 1 — Chat & Streaming**: Textarea input, Enter to send, Shift+Enter for newline, send button busy state, SSE token streaming, auto-scroll stickiness.
   - **Area 2 — Preset Chips**: All 4 preset buttons (`Python generator` -> Pass, `Risotto L1` -> L1 Breach, `Piggyback L2` -> L2 Breach, `Spectral L3` -> L3 Breach).
   - **Area 3 — Live Tuning Drawer**: Gateway base, Domain selector (11 canonical + custom), "Apply overrides" checkbox, all 4 sliders (L1, L2, Quorum K, Epsilon) verifying graceful `PassCard` or `BreachCard` rendering without raw HTTP 403 crashes.
   - **Area 4 — Telemetry Cards**: Rendering of `PassCard` (green with 3 heads) vs `BreachCard` (high-contrast red with failing tier, cosine bar, breached clause, affirmative votes).
   - **Area 5 — Upstream & Environment Sync**: Provider selector (`mock`, `gemini`, `openai`, `deepseek`, `groq`, `ollama`), "Usar keys de .env" toggle, "🔄 Cargar de .env" button and status feedback, mock notice visibility.
   - **Area 6 — Viewport & Layout Ergonomics**: `100dvh` containment, sidebar fixed width (`w-60`), independent scrollable regions.
4. **Autonomous Fix Threshold**:
   - High autonomy: Bugs in UI state, React hooks, DTO parsing, Playwright selectors, and mock forwarder wiring in `sf-proxy` must be solved directly via TDD.
   - Consult user only if changes require altering RFC-003 IEEE 754 math kernels or rewriting LanceDB physical schemas.

---

## 3. Ground Truth: Files, Contracts & Invariants

### 3.1 Primary Files
* [`frontend/package.json`](file:///Users/hbauzan/treepwood/3hm-dimentional-fw/frontend/package.json): Add `@playwright/test` devDependency and `test:e2e` script.
* [`frontend/playwright.config.ts`](file:///Users/hbauzan/treepwood/3hm-dimentional-fw/frontend/playwright.config.ts): New Playwright configuration targeting `http://127.0.0.1:5173`.
* [`frontend/e2e/playground.spec.ts`](file:///Users/hbauzan/treepwood/3hm-dimentional-fw/frontend/e2e/playground.spec.ts): New comprehensive E2E test specs.
* [`frontend/src/domain/breach.ts`](file:///Users/hbauzan/treepwood/3hm-dimentional-fw/frontend/src/domain/breach.ts): Normalize `PairwiseBreachEnvelope` into `ChatBreachDto`.
* [`frontend/src/domain/types.ts`](file:///Users/hbauzan/treepwood/3hm-dimentional-fw/frontend/src/domain/types.ts): Extend `FailingTier` with `L3_PAIRWISE_QUORUM`.
* [`frontend/src/ui/Playground.tsx`](file:///Users/hbauzan/treepwood/3hm-dimentional-fw/frontend/src/ui/Playground.tsx): Preserve epsilon and fix override defaults.
* [`crates/sf-proxy/src/chat_api.rs`](file:///Users/hbauzan/treepwood/3hm-dimentional-fw/crates/sf-proxy/src/chat_api.rs): Safeguard mock embedder and pairwise containment under mock mode.
* [`crates/sf-proxy/src/cascade.rs`](file:///Users/hbauzan/treepwood/3hm-dimentional-fw/crates/sf-proxy/src/cascade.rs): Align pairwise breach telemetry with frontend DTOs.

### 3.2 Testing Contract (Do NOT Break Existing Selectors)
| Component / Control | Accessible Selector / Matcher | Invariant Requirement |
| :--- | :--- | :--- |
| Prompt Textarea | `getByRole('textbox', { name: 'Prompt' })` | Exact accessible name inmutable |
| Send Button | `getByRole('button', { name: /Send|Sending/ })` | Text flips to "Sending" while busy |
| Messages List | `getByRole('list', { name: 'Messages' })` | Semantic `<ol>` container |
| Gateway Base Input | `getByRole('textbox', { name: 'Gateway base' })` | Auto-complete off, monospace |
| Domain Dropdown | `getByRole('combobox', { name: 'Domain id' })` | Populated with 11 canonical domains |
| Apply Overrides | `getByRole('checkbox', { name: 'Apply overrides' })` | Controls `overridesArmed` |
| Slider L1 | `getByRole('slider', { name: 'L1 cosine threshold' })` | Min 0, Max 1, Step 0.01 |
| Slider L2 | `getByRole('slider', { name: 'L2 clause threshold' })` | Min 0, Max 1, Step 0.01 |
| Slider Quorum | `getByRole('slider', { name: 'Quorum K' })` | Min 1, Max 1015, Step 1 |
| Slider Epsilon | `getByRole('slider', { name: 'Epsilon' })` | Min 0, Max 0.5, Step 0.005 |
| Use Env Checkbox | `getByRole('checkbox', { name: 'Usar keys de .env' })` | Toggles env sync |
| Load Env Button | `getByRole('button', { name: 'Cargar de .env' })` | Calls `/api/v1/env/catalog` |
| Provider Dropdown | `getByLabelText('Provider')` / `#upstream-provider` | Options: mock, gemini, openai, deepseek, groq, ollama |
| Pass Card | `getByText(/SEMANTIC CONTAINMENT PASS/i)` | Green diagnostic card on 200 |
| Breach Card | `getByText(/SEMANTIC CONTAINMENT BREACH/i)` | Red diagnostic card on 403 |

---

## 4. Architectural Layout & Tracer Bullet Slices

```
                               ┌──────────────────────────────────────────────┐
                               │     PLAYWRIGHT E2E & BROWSER SUBAGENT        │
                               └──────────────────────┬───────────────────────┘
                                                      │ HTTP / DOM actions
                                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ SF-PROXY PLAYGROUND (React 19 SPA :5173)                                                                    │
│  ┌─────────────────────────────────────────────────────────┐  ┌──────────────────────────────────────────┐  │
│  │ Chat Section                                            │  │ Live Tuning Drawer (w-60)                │  │
│  │  - Messages <ol> (Sticky scroll, PassCard & BreachCard) │  │  - Gateway base & Domain Selector (11)   │  │
│  │  - Preset Chips (Pass, L1, L2, L3)                      │  │  - Apply Overrides Checkbox              │  │
│  │  - Prompt Form (<textarea> + Send button)               │  │  - Sliders: L1, L2, Quorum K, Epsilon    │  │
│  └────────────────────────────┬────────────────────────────┘  │  - Upstream Provider & .env Sync Button  │  │
│                               │                               └──────────────────────────────────────────┘  │
└───────────────────────────────┼─────────────────────────────────────────────────────────────────────────────┘
                                │ POST /api/v1/chat
                                ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ SF-PROXY GATEWAY (:8088)                                                                                    │
│  - evaluate_chat_cascade(): L1 -> L2 -> L3 (MockBatchEmbedder calibration)                                  │
│  - evaluate_pairwise_containment(): Safe handling under mock mode                                            │
│  - Breach JSON normalization: ChatBreachDto + PairwiseBreachEnvelope unified                                │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Tracer Bullet 1: Backend Mock & Pairwise Telemetry Normalization
1. **Mock Bypass in Pairwise Containment**:
   In `crates/sf-proxy/src/chat_api.rs`, ensure that when `state.embedder` is `MockBatchEmbedder` and prompt is not an explicit breach, `evaluate_pairwise_containment()` does not fail closed against differential locks that require real `bge-m3` embeddings.
2. **Breach Schema Unification in Frontend**:
   In `frontend/src/domain/breach.ts`, extend `parseChatBreach()`:
   If `payload.error` exists with `kind === "ddi_ingress_breach"`, transform it into a valid `ChatBreachDto` with `failing_tier: "L3_PAIRWISE_QUORUM"` so `BreachCard` renders the pair lock name and clause index instead of failing into an unformatted error.
3. **Epsilon Preservation in Overrides**:
   In `frontend/src/ui/Playground.tsx`, if the user has not adjusted epsilon, do not send `epsilon: 0.0` which strips dilated bounds; send `undefined` or the stored calibration epsilon.

### Tracer Bullet 2: Playwright Headless Setup under Canonical `pnpm`
1. Install `@playwright/test` in `frontend/` using `pnpm add -D @playwright/test`.
2. Install browser binaries using `pnpm exec playwright install chromium`.
3. Create `frontend/playwright.config.ts`:
   - `testDir: './e2e'`
   - `baseURL: 'http://127.0.0.1:5173'`
   - Headless execution with timeout and video/screenshot on failure.
4. Add script in `frontend/package.json`: `"test:e2e": "playwright test"`.

### Tracer Bullet 3: Comprehensive E2E Test Suite Implementation
Implement `frontend/e2e/playground.spec.ts` covering:
1. **Preset Verification**: Click each of the 4 prompt presets, click Send, verify:
   - `Python generator`: Receives 200, renders `PassCard`, displays assistant stream.
   - `Risotto L1`: Receives 403, renders `BreachCard` with `L1_CENTROID_COSINE`.
   - `Piggyback L2`: Receives 403, renders `BreachCard` with `L2_CLAUSE_GATE` (or Pairwise Quorum).
   - `Spectral L3`: Receives 403, renders `BreachCard` with `L3_SPECTRAL_QUORUM`.
2. **Live Tuning Sliders & Overrides**:
   - Check `Apply overrides`.
   - Move `L2 clause threshold` from `0.50` to `0.80`. Send Python prompt -> Assert it triggers expected L2 breach and renders structured `BreachCard` without raw 403 error text.
   - Move `L2 clause threshold` to `0.10`. Send Python prompt -> Assert it passes and renders `PassCard`.
3. **Domain Selector**:
   - Change domain to `receta`, `legal`, `medicina`. Send prompt and verify request payload carries correct `domain_id`.
4. **Upstream & .env Sync**:
   - Toggle "Usar keys de .env", click "🔄 Cargar de .env", assert status message reflects catalog response.
   - Switch provider from `mock` to `openai` -> assert Base URL, Model, and API Key inputs appear.
   - Switch back to `mock` -> assert mock warning notice renders.
5. **Ergonomics & Keyboard Shortcuts**:
   - Focus textarea, press Enter -> form submits. Press Shift+Enter -> inserts newline without submitting.

### Tracer Bullet 4: Browser Subagent Interactive Verification & Notification
1. Launch `browser_subagent` to perform an interactive run against `http://localhost:5173`:
   - Interact with the L2 perilla live, send prompt, capture recording.
   - Validate visual polish and no layout shift.
2. Execute `/Users/hbauzan/treepwood/fabrica_de_software/agent.sh notify` to trigger native macOS notification.
3. Present Approval Gate before git delivery.

---

## 5. Development Protocol, Quality Gate & Definition of Done

### 5.1 Protocol Invariants
* **Git Branch**: Create `feat/webgui-e2e-audit` from `main`.
* **Sole Author**: `hbauzan` (`Héctor Andrés Bauzán Saavedra` <`hbauzan@gmail.com`>). No AI or bot co-author trailers.
* **Toolchain Rigor**: Exclusively `pnpm` in `frontend/`, `cargo` in root workspace.

### 5.2 Canonical Verification Commands
```bash
# 1. Frontend Unit & Integration Tests
cd /Users/hbauzan/treepwood/3hm-dimentional-fw/frontend && pnpm test

# 2. Frontend Linters and TypeScript Build
cd /Users/hbauzan/treepwood/3hm-dimentional-fw/frontend && pnpm oxlint && pnpm run build

# 3. Headless Playwright E2E Tests (Services must be running: sf-proxy on 8088, vite on 5173)
cd /Users/hbauzan/treepwood/3hm-dimentional-fw/frontend && pnpm test:e2e

# 4. Rust Workspace Tests
cargo test --workspace

# 5. Local Factory Contract Validation
/Users/hbauzan/treepwood/fabrica_de_software/agent.sh validate --task-file TASKS.md
```

### 5.3 Definition of Done (Falsifiable Checklist)
- [ ] Adjusting the L2 Clause Threshold slider in mock mode no longer causes an unhandled HTTP 403 error banner.
- [ ] Any HTTP 403 response (including pairwise containment breaches) parses cleanly into a structured visual `BreachCard`.
- [ ] Playwright is installed via canonical `pnpm` with `pnpm test:e2e` passing 100% across all 6 WebGUI functional areas.
- [ ] Existing 36 Vitest tests continue to pass 100% with 0 TypeScript and 0 linter errors.
- [ ] All Rust tests across `sf-proxy`, `sf-kernels`, `sf-storage`, `sf-ui` pass 100%.
- [ ] Native macOS notification dispatched upon completion via `agent.sh notify`.
- [ ] Approval Gate presented to user before commit/merge.
