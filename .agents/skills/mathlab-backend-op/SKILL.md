---
name: mathlab-backend-op
description: >-
  Use this skill when adding, modifying, or debugging a mathematical operation,
  domain module, or computation endpoint in the MathLab Python backend.
---

# Adding or Updating a MathLab Backend Operation

Follow these steps to keep `backend/app/modules/math_engine` safe, deterministic, and consistent.

## Steps

1. **Enforce Controlled Execution**
   - Never use `eval()`, `exec()`, or unrestricted `sympy.sympify()` on user input.
   - Parse all expressions and equations through [safe_parser.py](../../../backend/app/modules/math_engine/parser/safe_parser.py) (`parse_math_expression`, `parse_math_input`, `parse_symbol`) and matrices through `parse_matrix` in [linear_algebra/operations.py](../../../backend/app/modules/math_engine/linear_algebra/operations.py).
   - Raise typed errors from [exceptions.py](../../../backend/app/core/exceptions.py) (`InvalidExpressionError`, `DomainError`, `ComputationLimitError`, `UnsupportedOperationError`).

2. **Implement Domain Logic**
   - Place the operation inside its domain module under `backend/app/modules/math_engine/`:
     - `algebra/`
     - `calculus/`
     - `linear_algebra/`
     - `numerical/`
   - Return a dict with `result` (formatted via `format_sympy_expr` using `^` for powers), `latex` (`sp.latex(...)`), and `details` (including `"method"`).

3. **Whitelist in Operation Registry**
   - Add an `OperationSpec` entry (with optional aliases) to `OPERATION_REGISTRY` in [registry.py](../../../backend/app/modules/math_engine/registry/registry.py).
   - Ensure execution stays wrapped by `run_with_timeout(...)`.

4. **Validate with Tests**
   - Add unit and edge-case tests in [test_math_engine.py](../../../backend/app/tests/test_math_engine.py) and API tests in [test_compute_api.py](../../../backend/app/tests/test_compute_api.py).
   - Run the backend test suite from `backend/`:
     ```powershell
     .\.venv\Scripts\python.exe -m pytest app/tests -v
     ```
   - Confirm all tests pass without skipped assertions.
