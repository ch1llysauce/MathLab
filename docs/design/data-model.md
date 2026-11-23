# Data Model & Persistence Design

## 1. Storage Responsibilities

- **Supabase PostgreSQL**: Primary source of truth for all application and notebook state (`infrastructure/supabase/migrations/` and `seed.sql`).
- **Cloudflare R2**: Object storage only for exported notebooks, generated reports, visualization assets, and large files.
- Do **not** maintain duplicate authoritative databases outside Supabase PostgreSQL.

---

## 2. Core Entities (Target Schema)

| Entity | Purpose | Key Attributes (Target) |
|---|---|---|
| `users` | Application user profile linked to Supabase Auth | `id`, `email`, `display_name`, `created_at` |
| `notebooks` | Top-level mathematical workspace | `id`, `user_id`, `title`, `mode` (`computational` \| `learning`), `created_at`, `updated_at` |
| `notebook_cells` | Ordered cells inside a notebook | `id`, `notebook_id`, `position`, `cell_type` (`math` \| `markdown` \| `ai`), `operation`, `expression`, `status` (`idle` \| `valid` \| `stale` \| `error`), `depends_on` |
| `computation_results` | Latest structured result per cell execution | `id`, `cell_id`, `result_text`, `result_latex`, `reasoning_json`, `verification_status`, `verification_details`, `visualization_json`, `executed_at` |
| `variables_and_assumptions` | Notebook-scoped symbol bindings & constraints | `id`, `notebook_id`, `cell_id`, `symbol_name`, `value_expr`, `assumptions_json` |
| `notebook_history` | Snapshots or audit trail of executions/edits | `id`, `notebook_id`, `snapshot_json`, `created_at` |
| `saved_examples` | Curated or user-saved worked examples | `id`, `title`, `domain`, `description`, `cells_json`, `is_public` |

---

## 3. Notebook Execution & Invalidation Rules

1. **No raw Python storage**: Cells store structured mathematical expressions and operation requests, never arbitrary Python scripts.
2. **Sequential context**: Executing cell $N$ reads variable bindings and assumptions produced by valid cells $1 \dots N-1$.
3. **Upstream invalidation**: Editing cell $K$ marks cell $K$ and all downstream cells that depend on variables/results from cell $K$ as `stale` so stale outputs are never presented as verified.

---

## 4. Verification Status Taxonomy

Every verification record distinguishes between proof and computational support:

- `verified` — Symbolic equivalence or exact substitution confirms the result under stated assumptions.
- `numerical_support` — Numerical residuals/sampling agree within tolerance, without symbolic proof.
- `partial` — Some checks passed, or result holds only on a restricted subdomain.
- `inconclusive` — Unable to confirm or refute (e.g., timeout, undecidable symbolic simplification).
