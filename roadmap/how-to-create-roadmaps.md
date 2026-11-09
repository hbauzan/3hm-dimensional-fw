# Guía de Elaboración de Roadmaps y Prompts de Arquitectura (How-to-Create-Roadmaps)

> **Tipo de Documento**: Guía de referencia operativa / Sugerencia metodológica no mandatoria.  
> **Destinatarios**: Agentes de IA (Maximum Architect Agent, copilotos técnicos, LLMs de codificación) y arquitectos humanos.  
> **Objetivo**: Estandarizar la formulación de especificaciones técnicas (`.roadmap.md` y `.prompt.md`) para maximizar la densidad latente, erradicar la ambigüedad y habilitar ejecuciones autónomas TDD sin derivas de contexto.

---

## 1. Filosofía y Principios Rectores

1. **Ground Truth Empírico sobre Suposición**:
   - Todo roadmap debe basarse en el estado activo real del repositorio (inspeccionado previamente mediante tests, manifests y código fuente), nunca en memoria estéril o asunciones tácitas.
2. **Contratos Innegociables Blindados**:
   - Si un componente ya posee tests (`*.test.tsx`, `*.rs`, etc.), el roadmap debe tabular explícitamente los selectores, roles accesibles, endpoints y contratos DTO que **no pueden romperse**.
3. **Separación de Opciones de Diseño**:
   - Ante decisiones con trade-offs (ej. ergonomía visual, densidad de información, dependencias), documentar brevemente las opciones consideradas (Opción A, B, C) y declarar cuál se implementa y por qué.
4. **Descomposición en Tracer Bullets (Vertical Slices)**:
   - Dividir la tarea en incrementos atómicos end-to-end verificables, compatibles con el esquema de tareas de `fabrica-de-software` y `transparent-dev-protocol`.

---

## 2. La Fórmula Canónica en 5 Secciones

Cada documento de especificación debe estructurarse siguiendo estas 5 secciones esenciales:

### Sección 1: Project Context & Current State (Ground Truth)
* **Entorno y Servicios**: Repositorio, crates / paquetes involucrados, puertos activos y URLs base.
* **Toolchain Canónico Único**: El gestor exclusivo fijado en el módulo (`cargo` en Rust, `pnpm` en Frontend, `uv` en Python). Prohibir herramientas secundarias o mezclas.
* **Línea Base de Calidad Verificada**: Cantidad exacta de tests pasando (`pnpm test`, `cargo test`), estado de linters (`pnpm oxlint`, `cargo clippy`) y verificación de tipos (`pnpm tsc -b`).

### Sección 2: Objective, Scope & Design Decision
* **Problema Concreto**: Qué limitación técnica o de usabilidad resuelve.
* **Alcance Técnico**: Qué introduce, qué refactoriza y qué queda expresamente fuera de alcance (Out of Scope).
* **Decisión de Diseño**: Justificación técnica de la alternativa elegida (ej. *Opción A: Densidad Studio con panel fijo `w-60`* vs. *Opción B: Collapsible drawer*).

### Sección 3: Ground Truth: Files, Contracts & Invariants
* **Archivos Primarios**: Rutas absolutas/relativas de los archivos a modificar o crear.
* **Tabla de Contratos de Testing**:
  | Control / Target | Selector en Tests | Invariante / Requerimiento |
  | :--- | :--- | :--- |
  | Input Gateway | `getByRole('textbox', { name: 'Gateway base' })` | Accessible name inmutable |
  | Botón Send | `getByRole('button', { name: 'Send' })` | Nombre accesible verbatim |
* **Tokens y Estilos del Sistema**: Constantes de diseño, variables de tema (`--color-studio-*`) o contratos CSS a reutilizar.

### Sección 4: Architectural Layout & Algorithmic Specification
* **Árbol Estructural (ASCII o Mermaid)**: Diagrama jerárquico de contenedores, flexbox/grid, scrollbars independientes y anclajes fijos.
* **Lógica Algorítmica Crítica**: Snippets de referencia funcionales para comportamientos no triviales (ej. algoritmo de stickiness de auto-scroll, tolerancia en px, reconexión SSE, etc.).
* **Medidas y Dimensiones**: Valores exactos de Tailwind / CSS (`h-[100dvh]`, `w-60`, `overscroll-contain`, tipografías `text-[10px]`).

### Sección 5: Protocol, Quality Gate & Definition of Done
* **Invariantes del Protocolo de Desarrollo**:
  - Rama de trabajo: `<type>/<short-name>` desde `main`.
  - **Autoría exclusiva**: Único autor y colaborador permitido: `hbauzan` (`Héctor Andrés Bauzán Saavedra` <`hbauzan@gmail.com`>). Cero bots de IA y cero trailers `Co-authored-by`.
  - **Approval Gate**: Auto-verificación obligatoria antes de solicitar aprobación humana para commit/merge.
* **Comandos Canónicos de Verificación**: Comandos exactos a correr localmente.
* **Definition of Done (Checklist Falsable)**:
  - [ ] Contención en viewport (`100dvh` sin scroll exterior).
  - [ ] 100% de tests unitarios pasando sin modificar los archivos de test.
  - [ ] 0 advertencias y 0 errores en linter y typecheck.

---

## 3. Plantilla / Blueprint Copiable (`TASK-SPEC.template.md`)

```markdown
# TASK SPECIFICATION: [TÍTULO DE LA TAREA EN ALTA DENSIDAD]

## 1. Project Context & Current State
* **Repository**: `3hm-dimensional-fw`
* **Target Subsystem**: [ej. \`frontend/\` | \`crates/sf-proxy\`]
* **Canonical Toolchain**: [ej. \`pnpm\` exclusively | \`cargo\` exclusively]
* **Current Quality Baseline**:
  - Tests: [ej. 9 suites / 35 tests pasando en verde]
  - TypeCheck & Linters: [ej. 0 errors, 0 warnings]

---

## 2. Objective & Scope
* **Objective**: [Descripción concisa del cambio arquitectónico o feature]
* **Scope**:
  1. [Punto 1]
  2. [Punto 2]
* **Design Decision**: [Explicación de la alternativa seleccionada y descartes]

---

## 3. Ground Truth: Files & Contracts
### 3.1 Primary Files
* \`ruta/al/archivo.tsx\`

### 3.2 Testing Contract (Do NOT break these selectors)
| Control / Target | Selector / Matcher | Invariant Requirement |
| :--- | :--- | :--- |
| [Target 1] | \`getByRole('...', { name: '...' })\` | [Regla estricta] |

### 3.3 Design Tokens / Environment Constraints
* [Tokens de diseño o variables de entorno]

---

## 4. Architectural Layout & Logic Specification
\`\`\`text
Root Layout
├── Header (flex-shrink-0)
└── Main (flex-1 overflow-hidden)
      ├── Area Principal (scroll independiente)
      └── Dock / Panel (anclado)
\`\`\`

### 4.1 Key Behavioral Logic
\`\`\`typescript
// Snippet de referencia funcional o algoritmo clave
\`\`\`

---

## 5. Development Protocol & Acceptance Criteria
### 5.1 Protocol Invariants
* **Git Branch**: \`<type>/<short-name>\` desde \`main\`.
* **Authorship**: Exclusivamente \`hbauzan\` (\`Héctor Andrés Bauzán Saavedra\` <\`hbauzan@gmail.com\`>). Sin co-autores ni bots.
* **Approval Gate**: Detenerse tras auto-verificación completa antes de push o merge.

### 5.2 Verification Commands
1. \`[comando 1 de tests]\`
2. \`[comando 2 de linters / typecheck]\`

### 5.3 Definition of Done
- [ ] [Criterio 1 verificable]
- [ ] [Criterio 2 verificable]
- [ ] 100% de tests pasando sin regresiones.
- [ ] Cero errores de linter o compilación.
```

---

## 4. Sugerencias Operativas para Agentes de IA

1. **Lectura Previa Obligatoria**: Antes de redactar un roadmap, inspecciona `TASKS.md`, los archivos de test relevantes (`*.test.tsx`, `tests/*.rs`) y los manifests (`package.json`, `Cargo.toml`).
2. **Cero Placeholders**: No uses `# TODO`, `// your code here` ni elisiones en las especificaciones arquitectónicas. Los snippets deben ser sintáctica y lógicamente válidos.
3. **Persistencia en `roadmap/`**: Guarda las especificaciones activas directamente en `roadmap/<nombre-descriptivo>.prompt.md`. Al completarse la tarea y verificarse en `main`, trasládala a `roadmap/archived/`.
