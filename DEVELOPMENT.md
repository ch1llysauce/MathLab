# MathLab – Development Guide

This document describes the development environment, repository architecture, setup procedures, conventions, and implementation roadmap for MathLab.

## 1. Development Principles

MathLab follows these architectural principles:

1. **Computation-first architecture** – Mathematical operations are handled by a dedicated Python computation layer.
2. **Modular monolith** – Keep the backend organized into independent modules without introducing unnecessary microservices.
3. **Separation of concerns** – Computation, reasoning, verification, visualization data preparation, and AI orchestration have distinct responsibilities.
4. **Shared mathematical context** – Computational and Learning Modes use the same notebook and computation infrastructure.
5. **Controlled execution** – Never execute arbitrary user-provided Python code.
6. **Incremental development** – Implement and validate the core mathematical capabilities before expanding the platform.

## 2. Repository Architecture

MathLab uses a monorepo structure.

```text
mathlab/
│
├── apps/
│   ├── web/
│   │   ├── public/
│   │   ├── src/
│   │   │   ├── app/
│   │   │   ├── components/
│   │   │   │   ├── common/
│   │   │   │   ├── notebook/
│   │   │   │   ├── computation/
│   │   │   │   ├── visualization/
│   │   │   │   └── learning/
│   │   │   ├── features/
│   │   │   │   ├── authentication/
│   │   │   │   ├── notebooks/
│   │   │   │   ├── computation/
│   │   │   │   ├── learning/
│   │   │   │   └── settings/
│   │   │   ├── hooks/
│   │   ├── services/
│   │   ├── stores/
│   │   ├── types/
│   │   └── utils/
│   │
│   └── mobile/
│       ├── app/
│       ├── src/
│       │   ├── components/
│       │   ├── features/
│       │   ├── hooks/
│       │   ├── services/
│       │   ├── stores/
│       │   └── types/
│       └── assets/
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   └── dependencies/
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   └── exceptions.py
│   │   ├── modules/
│   │   │   ├── math_engine/
│   │   │   │   ├── algebra/
│   │   │   │   ├── calculus/
│   │   │   │   ├── linear_algebra/
│   │   │   │   ├── numerical/
│   │   │   │   ├── parser/
│   │   │   │   └── registry/
│   │   │   │
│   │   │   ├── reasoning_engine/
│   │   │   │   ├── classifier/
│   │   │   │   ├── rules/
│   │   │   │   ├── method_selector/
│   │   │   │   └── assumptions/
│   │   │   │
│   │   │   ├── verification_engine/
│   │   │   │   ├── symbolic/
│   │   │   │   ├── numerical/
│   │   │   │   ├── equivalence/
│   │   │   │   └── analysis/
│   │   │   │
│   │   │   ├── notebook_engine/
│   │   │   ├── visualization_engine/
│   │   │   └── ai_engine/
│   │   │
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── repositories/
│   │   ├── services/
│   │   └── tests/
│   │
│   ├── pyproject.toml
│   └── uv.lock
│
├── packages/
│   ├── shared-types/
│   ├── api-client/
│   └── math-input/
│
├── infrastructure/
│   ├── cloudflare/
│   │   ├── workers/
│   │   └── wrangler.toml
│   └── supabase/
│       ├── migrations/
│       └── seed.sql
│
├── docs/
│   ├── architecture/
│   ├── api/
│   └── design/
│
├── .env.example
├── .gitignore
├── package.json
├── pnpm-workspace.yaml
├── pnpm-lock.yaml
├── README.md
└── DEVELOPMENT.md
```

### Architecture Notes

- `apps/web` is the primary MathLab interface.
- `apps/mobile` is a companion application for notebook access, quick computations, and synchronized work.
- `backend/app/modules/math_engine` handles mathematical computation.
- `reasoning_engine` identifies problems and selects appropriate methods.
- `verification_engine` evaluates the reliability of computed results.
- `notebook_engine` manages cell execution and computational context.
- `visualization_engine` prepares mathematical data for visualization.
- `ai_engine` handles LLM integration and contextual explanations.
- `packages` contains reusable TypeScript code shared between applications.
- `infrastructure` contains deployment and database configuration.

The backend remains a modular monolith initially. Separate computation workers or services can be introduced later if workload and security requirements justify them.

## 3. Technology Stack

### Frontend

- React
- TypeScript
- Vite
- Tailwind CSS
- Plotly
- KaTeX
- CodeMirror 6

### Mobile

- React Native
- Expo
- TypeScript

### Backend

- Python
- FastAPI
- Pydantic
- SymPy
- NumPy
- SciPy
- pytest

### Infrastructure

- Cloudflare Pages – Web application hosting.
- Cloudflare Workers – Lightweight edge routing, validation, and API-related functionality.
- Cloudflare R2 – Object storage for exported files and generated assets.
- Supabase PostgreSQL – Primary relational database.
- Supabase Auth – Authentication and identity management.
- Conventional Python hosting – FastAPI and mathematical execution.

### AI

- External LLM API for natural-language interpretation and explanations.
- Optional Ollama integration for local development and experimentation.

## 4. Local Development Setup

### Prerequisites

Install the following:

- Node.js (LTS)
- pnpm
- Python (compatible with the selected dependencies)
- uv
- Git
- Supabase account or local Supabase environment

### Clone the Repository

```bash
git clone <repository-url>
cd mathlab
```

### Install JavaScript Dependencies

```bash
pnpm install
```

### Set Up the Python Environment

```bash
cd backend
uv sync
```

Activate the virtual environment if needed:

```bash
# Windows PowerShell
.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate
```

### Configure Environment Variables

Create the necessary environment files based on `.env.example`.

### Run the Backend

From the `backend` directory:

```bash
uv run uvicorn app.main:app --reload --port 8000
```

Backend API:

```text
http://localhost:8000
```

API documentation:

```text
http://localhost:8000/docs
```

### Run the Web Application

From the repository root:

```bash
pnpm --filter web dev
```

### Run the Mobile Application

```bash
pnpm --filter mobile start
```

The actual workspace package names and scripts should match the package manifests as implementation progresses.

## 5. Environment Variables

Example configuration:

```env
# Backend
APP_ENV=development
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:5173

# Supabase
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=

# AI Integration
LLM_PROVIDER=
LLM_API_KEY=
LLM_MODEL=

# Cloudflare
CLOUDFLARE_ACCOUNT_ID=
CLOUDFLARE_R2_BUCKET=
CLOUDFLARE_API_TOKEN=
```

Frontend environment variables:

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_SUPABASE_URL=
VITE_SUPABASE_ANON_KEY=
```

Mobile environment variables should be configured separately using Expo's supported environment configuration.

**Security requirements:**
- Never commit `.env` files.
- Never expose Supabase service-role keys in frontend applications.
- Never expose Cloudflare API tokens in client-side code.
- Keep LLM API keys exclusively on trusted server-side environments.
- Validate all requests before mathematical execution.

## 6. Backend Architecture

The backend is organized into six primary functional modules.

### Math Engine

Responsible for:
- Parsing mathematical expressions.
- Symbolic computation.
- Numerical computation.
- Domain-specific mathematical operations.
- Managing approved computational operations.

Primary libraries:
- SymPy
- NumPy
- SciPy

### Reasoning Engine

Responsible for:
- Identifying mathematical problem types.
- Determining applicable computational methods.
- Evaluating method requirements.
- Managing mathematical assumptions.
- Producing method-selection explanations.

The initial implementation should use deterministic rules and mathematical conditions rather than relying exclusively on an LLM.

### Verification Engine

Responsible for:
- Symbolic equivalence checks.
- Numerical residual calculations.
- Substitution checks.
- Cross-method comparisons.
- Assumption and domain validation.

Verification results should distinguish between verified checks, numerical support, partial verification, and inconclusive results.

### Notebook Engine

Responsible for:
- Notebook persistence.
- Cell management.
- Sequential execution.
- Variable and computation context.
- Dependency tracking.
- Result invalidation after upstream edits.

Editing an earlier cell should invalidate downstream computations that depend on it.

### Visualization Engine

Responsible for:
- Preparing plotting data.
- Function evaluation over specified domains.
- Identifying important mathematical points.
- Generating 2D and 3D visualization datasets.
- Supporting interactive parameter changes.

Plotly handles frontend rendering.

### AI Engine

Responsible for:
- Natural-language interpretation.
- Contextual explanations.
- Guided mathematical walkthroughs.
- LLM request orchestration.
- Converting computational outputs into understandable explanations.

The AI engine must not independently invent mathematical results. It should reference outputs from the computation and verification engines.

## 7. Computational Execution and Security

MathLab must never treat user-submitted expressions as arbitrary Python programs.

Use a restricted mathematical parser and an approved operation registry.

Required safeguards:

- Whitelist supported mathematical operations.
- Validate expression structure and input types.
- Restrict execution time and memory.
- Limit expression complexity and output size.
- Prevent arbitrary file and network access.
- Apply rate limits.
- Isolate computational workloads where appropriate.
- Validate LLM-generated tool requests before execution.

Notebook cells should store mathematical expressions and structured operation requests, not unrestricted executable Python code.

## 8. Data and Persistence

Supabase PostgreSQL serves as the primary source of truth for application data.

Initial data entities may include:

- Users
- Notebooks
- Notebook Cells
- Computation Results
- Variables and Assumptions
- Notebook History
- Saved Examples

Cloudflare R2 is reserved for object storage, such as:
- Notebook exports.
- Generated reports.
- Visualization assets.
- Other large files.

Avoid maintaining duplicate authoritative notebook databases in both Supabase and Cloudflare D1.

## 9. API Design

Use a versioned REST API.

Initial endpoint structure:

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/v1/health` | Health check |
| POST | `/api/v1/compute` | Execute mathematical operations |
| POST | `/api/v1/reasoning/analyze` | Analyze a mathematical problem |
| POST | `/api/v1/verification/check` | Verify a result |
| POST | `/api/v1/visualization/plot` | Generate visualization data |
| GET | `/api/v1/notebooks` | Retrieve notebooks |
| POST | `/api/v1/notebooks` | Create a notebook |
| GET | `/api/v1/notebooks/{id}` | Retrieve notebook details |
| PUT | `/api/v1/notebooks/{id}` | Update notebook |
| POST | `/api/v1/notebooks/{id}/execute` | Execute notebook cells |
| POST | `/api/v1/ai/explain` | Generate contextual explanations |

These endpoints are initial design targets, not a claim that they have already been implemented.

All API requests and responses should use validated Pydantic schemas and consistent error formats.

## 10. Development Roadmap

### M1 – Mathematical Computation Engine
- Build mathematical expression parser.
- Implement algebra operations.
- Implement selected calculus operations.
- Implement linear algebra operations.
- Add numerical computation.
- Establish mathematical test cases.

### M2 – Intelligent Mathematical Reasoning
- Build problem classification.
- Implement rule-based method selection.
- Add method applicability conditions.
- Implement assumption handling.
- Generate method-selection explanations.

### M3 – Verification and Analysis Engine
- Implement symbolic equivalence checking.
- Implement numerical residual checking.
- Add substitution validation.
- Support cross-method comparisons.
- Establish verification result classifications.

### M4 – Computational Notebook
- Implement notebook and cell models.
- Support sequential execution.
- Manage variables and computation context.
- Implement dependency tracking.
- Support saving and loading notebooks.

### M5 – Computational Visualization Studio
- Implement 2D plotting.
- Implement basic 3D surface plotting.
- Add important mathematical point detection.
- Support interactive parameters.
- Integrate Plotly with computation outputs.

### M6 – AI and Educational Integration
- Integrate natural-language mathematical input.
- Add contextual mathematical explanations.
- Implement guided worked examples.
- Connect AI assistance to computation results.
- Support transitions between Computational and Learning Modes.

### M7 – Web Application Release
- Implement authentication.
- Build the main workbench interface.
- Integrate notebook synchronization.
- Configure Cloudflare deployment.
- Implement production API integration.

### M8 – Mobile Companion Application
- Build notebook browsing and access.
- Support quick computations.
- Display mathematical visualizations.
- Implement account and data synchronization.

## 11. Testing Strategy

### Mathematical Unit Tests

Examples:

| Operation | Input | Expected Result |
|---|---|---|
| Differentiate | `x^3 + 2*x` | `3*x^2 + 2` |
| Integrate | `2*x` | `x^2 + C` |
| Solve | `x^2 - 5*x + 6 = 0` | `x = 2, 3` |
| Matrix Eigenvalues | A defined test matrix | Expected eigenvalues |
| Plot | `x^2` | Valid 2D plotting data |

### Integration Tests

- Natural-language input correctly identifies an operation.
- Reasoning engine selects an applicable method.
- Computation engine returns a valid result.
- Verification engine evaluates the result.
- Visualization engine receives valid computation output.
- Notebook execution maintains the correct computational context.
- Editing an earlier cell invalidates dependent downstream results.
- Saved notebooks restore their state correctly.

### Security Tests

- Reject unsupported expressions.
- Reject arbitrary Python execution attempts.
- Enforce computation limits.
- Validate malformed API requests.
- Verify authentication and authorization.
- Prevent sensitive credentials from appearing in client responses.

## 12. Development Conventions

### General
- Prefer modular, reusable components.
- Keep mathematical logic separate from UI components.
- Use TypeScript strict mode.
- Use Python type hints.
- Validate API boundaries.
- Write tests alongside new mathematical operations.

### Git Workflow

Suggested branch naming:

```text
main
develop
feature/math-engine
feature/reasoning-engine
feature/verification-engine
feature/notebook
feature/visualization
feature/ai-integration
```

Suggested commit conventions:

```text
feat: add symbolic differentiation
feat: implement method selection rules
fix: correct numerical residual validation
refactor: separate calculus operations
test: add matrix eigenvalue tests
docs: update development guide
```

## 13. Important Architectural Decisions

| Decision | Direction |
|---|---|
| Repository | Monorepo |
| Backend Architecture | Modular Monolith |
| Mathematical Execution | Python / FastAPI |
| Symbolic Computation | SymPy |
| Numerical Computation | NumPy / SciPy |
| Primary Database | Supabase PostgreSQL |
| Web Hosting | Cloudflare Pages |
| Edge Infrastructure | Cloudflare Workers |
| Object Storage | Cloudflare R2 |
| Mobile | React Native / Expo |
| Package Manager | pnpm |
| Python Environment | uv |
| AI | External LLM API with optional Ollama |

Cloudflare Workers should handle lightweight edge functionality rather than being the default environment for heavy mathematical computations. Python dependency compatibility and execution limits must be tested before considering any migration of mathematical workloads.

---

**End of Development Guide**