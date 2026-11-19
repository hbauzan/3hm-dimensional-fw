# TASK SPECIFICATION: FRONTEND CANONICAL DOMAIN SELECTOR IN PLAYGROUND (OPTION A)

## 1. Project Context & Current State (Ground Truth)

* **Repository**: `3hm-dimensional-fw` (Three-Headed Semantic Firewall).
* **Module Affected**: `frontend/` (React 19 + TypeScript + Vite + Tailwind CSS v4).
* **Storage & Backend Baseline**:
  * LanceDB (`data/sf-lancedb`) contains the **11 canonical domains**:
    `["python", "receta", "legal", "medicina", "astronomia", "finanzas", "filosofia", "musica", "geologia", "botanica", "arquitectura"]`
    plus their 55 pairwise differential containment locks.
  * Backend gateway `crates/sf-proxy` processes `POST /api/v1/chat` requiring a `domain_id` string (defaults to `"python"`).
* **Current UI Limitation**:
  * In `frontend/src/ui/Playground.tsx` (lines 265–276), `Domain id` is rendered as an unassisted free-text `<input type="text">`.
  * Operators must manually type or remember domain identifiers without visual feedback or discovery of available firewall domains.
* **Canonical Toolchain**:
  * Frontend: `pnpm` exclusively (`pnpm test`, `pnpm run lint`, `pnpm run build`). Zero mixing of npm/yarn.

---

## 2. Objective, Scope & Design Decision

### 2.1 Primary Objectives
1. **Replace Free-Text Input with Canonical Dropdown**:
   Replace the raw `<input>` under `Domain id` in `frontend/src/ui/Playground.tsx` with a styled `<select>` containing all 11 canonical domains.
2. **Domain Constant Source of Truth**:
   Declare `CANONICAL_DOMAINS` in `frontend/src/domain/presets.ts` as the single source of truth in the frontend, mirroring `CANONICAL_DOMAINS` from `crates/sf-storage/src/calibration.rs`.
3. **Graceful Custom Domain Preservation**:
   If `session.domainId` holds a non-canonical or custom domain (e.g. from localStorage), ensure it renders as an additional `<option>` so existing stored sessions never lose state or render blank.
4. **Zero Regression Guarantee**:
   All 36 existing tests in `frontend/` must continue to pass, and a new test must verify domain switching and payload propagation.

### 2.2 Out of Scope
* Modifying Rust backend code or adding new API routes (Option A is strictly frontend-scoped).
* Altering the 55 pairwise differential lock naming convention (`left_right`).

---

## 3. Ground Truth: Files, Contracts & Invariants

### 3.1 Primary Files
* `frontend/src/domain/presets.ts`: Export `CANONICAL_DOMAINS` array and `CanonicalDomain` type.
* `frontend/src/ui/Playground.tsx`: Replace text `<input>` with `<select>` using `fieldClass` styling.
* `frontend/src/ui/Playground.test.tsx`: Add test asserting domain selection propagates into request payload.
* `TASKS.md`: Local multi-agent software factory contract.

### 3.2 Testing & Quality Contracts
* **Vitest Suite**: 100% pass (`pnpm test` in `frontend/`).
* **Linter & Typecheck**: 0 warnings and 0 errors (`pnpm run lint` and `pnpm run build` in `frontend/`).
* **Accessible Role**: The selector must have an accessible name matching `'Domain id'`.

---

## 4. Architectural Layout & Algorithmic Specification

### 4.1 Canonical Domains Declaration (`frontend/src/domain/presets.ts`)

```typescript
export const CANONICAL_DOMAINS = [
  'python',
  'receta',
  'legal',
  'medicina',
  'astronomia',
  'finanzas',
  'filosofia',
  'musica',
  'geologia',
  'botanica',
  'arquitectura',
] as const

export type CanonicalDomain = (typeof CANONICAL_DOMAINS)[number]

export function isCanonicalDomain(value: string): value is CanonicalDomain {
  return (CANONICAL_DOMAINS as readonly string[]).includes(value)
}
```

### 4.2 UI Component Refactor (`frontend/src/ui/Playground.tsx`)

In the live tuning sidebar panel:

```tsx
<label className="flex flex-col gap-1 text-[10px] uppercase tracking-wide text-studio-muted">
  Domain id
  <select
    aria-label="Domain id"
    className={fieldClass}
    value={session.domainId}
    onChange={(event) =>
      commit((current) => ({ ...current, domainId: event.target.value }))
    }
  >
    {CANONICAL_DOMAINS.map((domain) => (
      <option key={domain} value={domain}>
        {domain}
      </option>
    ))}
    {!CANONICAL_DOMAINS.includes(session.domainId as CanonicalDomain) && session.domainId && (
      <option value={session.domainId}>
        {session.domainId} (custom)
      </option>
    )}
  </select>
</label>
```

---

## 5. Development Protocol, Quality Gate & Definition of Done

### 5.1 Protocol Invariants
* **Git Branch**: `feat/frontend-canonical-domain-selector` created from `main`.
* **Authorship**: Exclusively `hbauzan` (`Héctor Andrés Bauzán Saavedra` <`hbauzan@gmail.com`>). No bot or co-author trailers.
* **Approval Gate**: Full self-verification before requesting human push/merge.

### 5.2 Verification Commands
```bash
# 1. Frontend Unit & Integration Tests
cd frontend && pnpm test

# 2. Frontend Linter
cd frontend && pnpm run lint

# 3. Frontend Production Build & TypeScript Typecheck
cd frontend && pnpm run build
```

### 5.3 Definition of Done
- [x] `CANONICAL_DOMAINS` exported from `frontend/src/domain/presets.ts` with all 11 domains.
- [x] `Domain id` in `frontend/src/ui/Playground.tsx` rendered as a styled `<select>` matching studio theme.
- [x] Non-canonical domain preserved if loaded from stored session.
- [x] New unit test in `Playground.test.tsx` verifying selecting another domain (e.g., `'legal'`) sends `"domain_id": "legal"` in the chat request body.
- [x] 100% tests passing in Vitest (37+ tests) with zero errors in `pnpm run lint` and `pnpm run build`.
