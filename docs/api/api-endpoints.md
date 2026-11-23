# MathLab API Endpoints & Contracts

Base prefix: `/api/v1`

> **Implementation Status:** `GET /api/v1/health`, `GET /api/v1/compute/operations`, `POST /api/v1/compute` (M1), `POST /api/v1/reasoning/analyze` (M2), `POST /api/v1/verification/check` (M3), and the `/api/v1/notebooks` endpoints (M4) are implemented in [backend/app/main.py](../../backend/app/main.py). All remaining endpoints below are target design contracts defined in [DEVELOPMENT.md](../../DEVELOPMENT.md#L427-L450).

## 1. Conventions

- **Validation**: All request and response bodies use Pydantic v2 schemas (`backend/app/schemas/`).
- **Authentication**: Protected endpoints accept a Supabase Auth Bearer JWT (`Authorization: Bearer <token>`).
- **Content Type**: `application/json`.
- **Standard Error Format** (target):
  ```json
  {
    "error": {
      "code": "INVALID_EXPRESSION",
      "message": "Unsupported operation or malformed mathematical expression.",
      "details": {}
    }
  }
  ```

---

## 2. Endpoint Inventory

| Method | Endpoint | Purpose | Status |
|---|---|---|---|
| `GET` | `/api/v1/health` | Service health check | Implemented |
| `GET` | `/api/v1/compute/operations` | List approved operations | Implemented (M1) |
| `POST` | `/api/v1/compute` | Execute mathematical operations | Implemented (M1) |
| `POST` | `/api/v1/reasoning/analyze` | Classify problem & select method | Implemented (M2) |
| `POST` | `/api/v1/verification/check` | Verify a computed result | Implemented (M3) |
| `POST` | `/api/v1/visualization/plot` | Generate 2D/3D plot datasets | Planned (M5) |
| `GET` | `/api/v1/notebooks` | List user notebooks | Implemented (M4) |
| `POST` | `/api/v1/notebooks` | Create a notebook | Implemented (M4) |
| `GET` | `/api/v1/notebooks/{id}` | Retrieve notebook and cells | Implemented (M4) |
| `PUT` | `/api/v1/notebooks/{id}` | Update notebook / cells | Implemented (M4) |
| `POST` | `/api/v1/notebooks/{id}/execute` | Execute notebook cells sequentially | Implemented (M4) |
| `POST` | `/api/v1/ai/explain` | Generate grounded AI explanation | Planned (M6) |

---

## 3. Target Endpoint Contracts

### `GET /api/v1/health`
Returns service status and active `APP_ENV`.
```json
{
  "status": "ok",
  "environment": "development"
}
```

### `POST /api/v1/compute`
Executes a whitelisted mathematical operation via `math_engine`.
- **Request**:
  ```json
  {
    "operation": "differentiate",
    "expression": "x^3 + 2*x",
    "variable": "x",
    "assumptions": { "x": "real" },
    "options": {}
  }
  ```
- **Response**:
  ```json
  {
    "operation": "differentiate",
    "input": "x^3 + 2*x",
    "result": "3*x^2 + 2",
    "latex": "3x^{2} + 2",
    "metadata": {
      "method": "symbolic_differentiation",
      "warnings": []
    }
  }
  ```

### `POST /api/v1/reasoning/analyze`
Identifies the problem type, applicable methods, assumptions, and selection rationale.

### `POST /api/v1/verification/check`
Runs symbolic equivalence, numerical residuals, substitution, or cross-method checks and returns a qualified status (`verified`, `numerical_support`, `partial`, or `inconclusive`).

### `POST /api/v1/visualization/plot`
Evaluates 2D/3D functions over requested domains and returns Plotly-compatible trace data plus detected key points (roots, intercepts, critical points).

### `/api/v1/notebooks` & `/api/v1/notebooks/{id}`
CRUD operations for notebooks and their structured cells, plus `POST /api/v1/notebooks/{id}/execute` for sequential execution with dependency invalidation.

### `POST /api/v1/ai/explain`
Accepts a problem/computation context and returns a natural-language walkthrough grounded in outputs from `math_engine`, `reasoning_engine`, and `verification_engine`.
