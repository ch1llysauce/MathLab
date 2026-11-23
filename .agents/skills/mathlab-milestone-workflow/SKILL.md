---
name: mathlab-milestone-workflow
description: >-
  Use this skill when planning or implementing the next MathLab development
  milestone (M1 through M8) or checking architectural alignment with the project docs.
---

# MathLab Milestone Implementation Workflow

Keep development aligned with [DEVELOPMENT.md](../../../DEVELOPMENT.md) and the docs in [docs/README.md](../../../docs/README.md).

## Steps

1. **Confirm Milestone Scope & Contracts**
   - Check the current milestone tasks in [implementation-roadmap.md](../../../docs/architecture/implementation-roadmap.md) (M1 Math Engine -> M2 Reasoning -> M3 Verification -> M4 Notebook -> M5 Visualization -> M6 AI/Learning -> M7 Web Release -> M8 Mobile Companion).
   - Check endpoint schemas in [api-endpoints.md](../../../docs/api/api-endpoints.md) and entities in [data-model.md](../../../docs/design/data-model.md).
   - Maintain **Web before Mobile** (`apps/web` is primary; `apps/mobile` is companion in M8).

2. **Enforce Core Architectural Boundaries**
   - Backend remains a **modular monolith** under `backend/app/modules/`.
   - AI features (`ai_engine`) must never invent mathematical results independently; ground explanations in `math_engine`, `reasoning_engine`, and `verification_engine` outputs.
   - Notebook cells store structured expressions/operations, never arbitrary Python code.

3. **Update Docs & Verify Everything**
   - Update endpoint implementation status in [api-endpoints.md](../../../docs/api/api-endpoints.md) when new routes ship.
   - Verify backend (`backend/`): `.\.venv\Scripts\python.exe -m pytest app/tests -v`
   - Verify web (`apps/web/`): `npm run build`
