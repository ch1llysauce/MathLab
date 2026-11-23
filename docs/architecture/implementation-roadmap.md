# MathLab Implementation Roadmap (Step-by-Step)

This guide breaks the milestones in [DEVELOPMENT.md](../../DEVELOPMENT.md#L451-L508) into an incremental, step-by-step build order. Each milestone ends with concrete verification checks before moving to the next.

---

## Step 0: Environment Bootstrap

1. Copy `.env.example` to `.env` and fill in development credentials (leave `LLM_*` and `CLOUDFLARE_*` blank until needed).
2. Install JS workspace dependencies from repository root:
   ```bash
   pnpm install
   ```
3. Install Python backend dependencies from `backend/`:
   ```bash
   cd backend
   uv sync
   ```
4. Verify the FastAPI server boots:
   ```bash
   uv run uvicorn app.main:app --reload --port 8000
   ```
   Confirm `GET http://localhost:8000/api/v1/health` returns `{"status": "ok", ...}`.

---

## M1 – Mathematical Computation Engine

**Goal:** Build safe, deterministic mathematical parsing and execution before adding AI or UI complexity.

1. **Operation Registry (`backend/app/modules/math_engine/registry/`)**:
   - Define the whitelist of supported operations (simplify, expand, factor, solve, limit, diff, integrate, matrix ops, eigenvalues, numerical eval, root finding).
2. **Restricted Parser (`backend/app/modules/math_engine/parser/`)**:
   - Parse mathematical syntax safely into SymPy/structured representations without `eval`/`exec`.
   - Reject arbitrary Python syntax, imports, attribute access, and unsupported functions.
3. **Domain Implementations**:
   - `algebra/`: simplification, expansion, factorization, equation solving, complex numbers.
   - `calculus/`: limits, symbolic differentiation, definite/indefinite integration.
   - `linear_algebra/`: matrix arithmetic, determinant, rank, eigenvalues, eigenvectors.
   - `numerical/`: floating-point evaluation, numerical root finding, approximations.
4. **API & Schemas**:
   - Define request/response Pydantic models in `backend/app/schemas/` and expose `POST /api/v1/compute`.
5. **Verification (`backend/app/tests/`)**:
   - Add unit tests (e.g., `diff(x^3 + 2*x)` -> `3*x^2 + 2`, `integrate(2*x)` -> `x^2 + C`, `solve(x^2 - 5*x + 6 = 0)` -> `2, 3`, matrix eigenvalues).
   - Add security tests rejecting arbitrary Python code injection and oversized expressions.

---

## M2 – Intelligent Mathematical Reasoning

**Goal:** Classify problems deterministically and explain why a computational method is chosen.

1. **Problem Classifier (`reasoning_engine/classifier/`)**: Identify domain and problem type (e.g., polynomial equation, definite integral, square matrix eigensystem).
2. **Rule & Applicability Engine (`reasoning_engine/rules/`, `assumptions/`)**: Encode preconditions (real vs. complex domain, continuity/differentiability assumptions, matrix squareness).
3. **Method Selector (`reasoning_engine/method_selector/`)**: Rank/select symbolic vs. numerical methods and generate human-readable selection explanations.
4. **API**: Expose `POST /api/v1/reasoning/analyze` and attach reasoning metadata to `/compute`.
5. **Verification**: Test rule selection across valid and edge-case inputs (e.g., singular matrices, non-elementary integrals falling back to numerical integration).

---

## M3 – Verification and Analysis Engine

**Goal:** Independently evaluate computed outputs and qualify confidence.

1. **Symbolic Checks (`verification_engine/symbolic/`)**: Symbolic equivalence (`simplify(lhs - rhs) == 0`), differentiation of antiderivatives.
2. **Numerical Checks (`verification_engine/numerical/`)**: Residual evaluation, randomized point substitution within valid domains.
3. **Cross-Method Comparison (`verification_engine/equivalence/`)**: Compare symbolic vs. numerical outputs where applicable.
4. **Result Classification (`verification_engine/analysis/`)**: Label checks as `verified`, `numerical_support`, `partial`, or `inconclusive`.
5. **API & Tests**: Expose `POST /api/v1/verification/check` and test true positives, false solutions/extraneous roots, and domain mismatches.

---

## M4 – Computational Notebook

**Goal:** Support stateful multi-cell notebooks with dependency tracking.

1. **Persistence (`infrastructure/supabase/migrations/`, `backend/app/models/`, `repositories/`)**: Create tables for users, notebooks, cells, results, variables/assumptions, and history.
2. **Execution Context (`notebook_engine/`)**: Store variable bindings and structured cell inputs (not raw Python scripts).
3. **Dependency Graph & Invalidation**: Track variable references across cells; mark downstream dependent cells stale/invalidated whenever an upstream cell changes.
4. **API**: Implement `GET/POST /api/v1/notebooks`, `GET/PUT /api/v1/notebooks/{id}`, and `POST /api/v1/notebooks/{id}/execute`.
5. **Verification**: Integration tests confirming sequential execution, upstream-edit invalidation, and clean reload from persistence.

---

## M5 – Computational Visualization Studio

**Goal:** Generate Plotly-ready mathematical visualization datasets from backend computations.

1. **2D & 3D Samplers (`visualization_engine/`)**: Evaluate functions over bounded domains with adaptive or uniform grids.
2. **Key Feature Detection**: Compute roots, intercepts, critical points, and tangent line data using `math_engine`.
3. **Interactive Parameters**: Support parameterized expressions for slider/parameter updates.
4. **API & Frontend**: Expose `POST /api/v1/visualization/plot` and connect to Plotly components in `apps/web/src/components/visualization/`.

---

## M6 – AI and Educational Integration

**Goal:** Add natural-language interpretation and Learning Mode walkthroughs grounded in engine outputs.

1. **LLM Provider Abstraction (`ai_engine/`)**: Support external LLM API and optional local Ollama via environment config.
2. **NL-to-Operation Translation**: Map natural-language requests to whitelisted structured `math_engine` calls (validated before execution).
3. **Grounded Explanations**: Pass problem classification, method choice, assumptions, computation output, and verification status to generate step-by-step explanations.
4. **API & Mode Support**: Expose `POST /api/v1/ai/explain` and support seamless Computational Mode ↔ Learning Mode switching in notebooks.

---

## M7 – Web Application Release

**Goal:** Ship the full web workbench on Cloudflare + Python backend hosting.

1. **Authentication**: Integrate Supabase Auth across `apps/web/src/features/authentication/` and backend JWT verification in `backend/app/core/security.py`.
2. **Workbench UI**: Complete CodeMirror 6 cell editor, KaTeX rendering, notebook manager, and explainable result panels.
3. **Exports & Storage**: Integrate Cloudflare R2 for notebook exports and generated assets.
4. **Deployment**: Configure Cloudflare Pages (`apps/web`), Cloudflare Workers (`infrastructure/cloudflare/wrangler.toml`), and production Python backend hosting.

---

## M8 – Mobile Companion Application

**Goal:** Provide mobile notebook access, quick computations, and visualizations.

1. **Shared Packages**: Reuse `@mathlab/shared-types`, `@mathlab/api-client`, and `@mathlab/math-input` in `apps/mobile/`.
2. **Core Screens**: Notebook browser, quick compute view, and visualization viewer synchronized via the same `/api/v1` backend and Supabase Auth.
