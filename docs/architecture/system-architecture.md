# MathLab System Architecture

## 1. Architectural Direction

MathLab is organized as a **monorepo** with a **modular monolith** Python backend:

- **Web Client (`apps/web`)**: React, TypeScript, Vite, Tailwind CSS, CodeMirror 6, KaTeX, Plotly.
- **Mobile Companion (`apps/mobile`)**: React Native, Expo, TypeScript.
- **Shared Packages (`packages/`)**: `shared-types`, `api-client`, `math-input`.
- **Edge & Hosting (`infrastructure/cloudflare`)**: Cloudflare Pages (web hosting), Cloudflare Workers (lightweight routing/validation), Cloudflare R2 (exports and large assets).
- **Backend API (`backend/app`)**: FastAPI modular monolith hosting mathematical computation, reasoning, verification, notebook execution, visualization data preparation, and AI orchestration.
- **Primary Database & Auth (`infrastructure/supabase`)**: Supabase PostgreSQL and Supabase Auth.

Cloudflare Workers are reserved for lightweight edge tasks; symbolic and numerical computation stays in the Python backend because of SymPy, NumPy, and SciPy requirements.

## 2. Request & Computation Pipeline

```text
Web (React) / Mobile (Expo)
        │
        ▼
Cloudflare Edge (Pages + lightweight Workers)
        │
        ▼
FastAPI API Layer (backend/app/api/)
        │
        ├──► 1. Reasoning Engine   ── Classify problem, check assumptions, select method
        ├──► 2. Math Engine        ── Parse safely & execute SymPy / NumPy / SciPy
        ├──► 3. Verification Engine── Symbolic equivalence, residuals, substitution, cross-checks
        ├──► 4. Visualization Engine─ Evaluate domains, find key points, format Plotly datasets
        ├──► 5. Notebook Engine    ── Sequence cells, track dependencies, invalidate stale outputs
        └──► 6. AI Engine          ── Interpret NL input & explain verified computation outputs
        │
        ├──► Supabase PostgreSQL (users, notebooks, cells, results, history)
        └──► Cloudflare R2 (exports, generated reports, visualization assets)
```

## 3. Backend Module Responsibilities

| Module | Path | Core Responsibility |
|---|---|---|
| `math_engine` | `backend/app/modules/math_engine/` | Restricted parsing (`parser/`), operation whitelist (`registry/`), symbolic & numerical domains (`algebra/`, `calculus/`, `linear_algebra/`, `numerical/`). |
| `reasoning_engine` | `backend/app/modules/reasoning_engine/` | Deterministic problem classification (`classifier/`), applicability rules (`rules/`), method selection (`method_selector/`), and assumptions (`assumptions/`). |
| `verification_engine` | `backend/app/modules/verification_engine/` | Symbolic equivalence (`symbolic/`), numerical residuals & substitution (`numerical/`), cross-method checks (`equivalence/`), and domain/reliability classification (`analysis/`). |
| `notebook_engine` | `backend/app/modules/notebook_engine/` | Notebook/cell orchestration, sequential execution, shared variable context, dependency graph, and downstream invalidation after upstream edits. |
| `visualization_engine` | `backend/app/modules/visualization_engine/` | 2D/3D domain sampling, critical points/roots/intercepts detection, and Plotly-ready dataset generation. |
| `ai_engine` | `backend/app/modules/ai_engine/` | Natural-language intent mapping, step-by-step educational explanations, and LLM orchestration grounded strictly in computation/verification outputs. |

## 4. Controlled Execution & Security Model

MathLab **never** executes user-submitted expressions or notebook cells as arbitrary Python code.

Required controls across all execution paths:
1. **Restricted mathematical parser**: Parse expressions via `math_engine/parser/` into structured AST/operation requests rather than Python `eval`/`exec`.
2. **Approved operation registry**: Allow only explicitly registered mathematical operations in `math_engine/registry/`.
3. **Input & complexity limits**: Enforce Pydantic schema validation, expression depth/length caps, output size bounds, and execution time/memory limits.
4. **Tool-call validation for AI**: Validate any LLM-proposed structured operation against the same parser, whitelist, and schema guards before execution.
5. **Credential isolation**: Keep `SUPABASE_SERVICE_ROLE_KEY`, `LLM_API_KEY`, and `CLOUDFLARE_API_TOKEN` exclusively on trusted server environments.
