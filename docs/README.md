# MathLab Documentation

This directory contains the architecture, API, and design documentation for **MathLab**, supporting the overview in [README.md](../README.md) and the guide in [DEVELOPMENT.md](../DEVELOPMENT.md).

## Contents

### Architecture (`docs/architecture/`)
- [System Architecture](architecture/system-architecture.md) — Monorepo layout, modular monolith boundaries, execution pipeline, data ownership, and security model.
- [Implementation Roadmap](architecture/implementation-roadmap.md) — Step-by-step build procedure from **M1** to **M8**, including target modules and verification tests.

### API (`docs/api/`)
- [API Endpoints & Contracts](api/api-endpoints.md) — Versioned REST endpoints (`/api/v1/...`), request/response schemas, authentication, and error conventions.

### Design (`docs/design/`)
- [Data Model & Persistence](design/data-model.md) — Core PostgreSQL entities, notebook cell dependency/invalidation model, verification states, and R2 storage scope.
- [Workbench UI/UX Design](design/ui-ux-workbench.md) — Computational Mode vs. Learning Mode, 5-step explainable output layout, and frontend/mobile component mapping.
