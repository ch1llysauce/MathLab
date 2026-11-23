# Workbench UI/UX Design

## 1. Dual-Mode Experience

MathLab serves two interconnected modes inside the same notebook interface:

1. **Computational Mode**
   - Focuses on fast expression entry, method comparison, numerical/symbolic results, verification badges, and interactive plots.
2. **Learning Mode**
   - Surfaces concept explanations, step-by-step derivations, guided worked examples, and assumption walkthroughs grounded in the same computation outputs.

Switching modes preserves the active notebook, variables, and computation history.

---

## 2. Five-Step Explainable Output Layout

Every computation cell presents inspectable sections rather than a bare answer:

1. **Problem Recognition** — Identified mathematical domain and problem type.
2. **Method Selection** — Selected algorithm/method and why it applies.
3. **Mathematical Assumptions** — Active domain constraints (e.g., $x \in \mathbb{R}$, non-singular matrix).
4. **Result Verification** — Verification status badge (`verified`, `numerical_support`, `partial`, `inconclusive`) and check details.
5. **Computational Exploration** — Interactive parameters, plots, and alternative method comparisons.

---

## 3. Web Frontend Mapping (`apps/web/src/`)

| Area | Directory | Technology / Responsibility |
|---|---|---|
| Common UI | `components/common/` | Reusable layout, buttons, badges, error states (Tailwind CSS) |
| Notebook UI | `components/notebook/` | Cell list, CodeMirror 6 math/expression editor, KaTeX math rendering |
| Computation UI | `components/computation/` | Reasoning, assumptions, and verification inspection panels |
| Visualization UI | `components/visualization/` | Plotly 2D/3D canvases, critical-point overlays, parameter sliders |
| Learning UI | `components/learning/` | Guided walkthroughs, step-by-step derivations, AI assistant drawer |
| Feature Modules | `features/{authentication,notebooks,computation,learning,settings}/` | Domain workflows, state orchestration, and API integration |
| Shared Layers | `hooks/`, `services/`, `stores/`, `types/`, `utils/` | Custom hooks, `@mathlab/api-client` calls, state stores, TypeScript strict types |

---

## 4. Mobile Companion Scope (`apps/mobile/`)

The Expo React Native companion focuses on lightweight portability:
- Browse and inspect synced notebooks.
- Run quick single-cell computations.
- View 2D/3D visualizations and verification summaries.
- Share Supabase Auth sessions and backend API types via `packages/shared-types` and `packages/api-client`.

---

## 5. Visual & Aesthetic Design Principles (Workbench Standards)

MathLab's interface must feel like a **precision computational workbench** (comparable in discipline to scientific notebooks and modern engineering tools), never like generic AI-generated SaaS templates.

1. **Content & Math First**:
   - Prioritize mathematical legibility (crisp KaTeX typesetting, clean CodeMirror 6 cell inputs, readable Plotly axes) over decorative chrome, oversized hero headers, or marketing copy inside the app.
2. **Avoid Generic "AI Slop" Patterns**:
   - **No** neon/purple-blue gradients, glowing borders, heavy drop shadows, glassmorphism clutter, or gratuitous sparkle icons.
   - **No** disconnected generic chatbot widgets; AI explanations must be anchored directly to cells, variables, and verified engine outputs.
3. **Restrained, Semantic Color System**:
   - Use a calm, high-contrast neutral surface palette (defaulting to a crisp daylight/paper workbench or an intentional low-glare studio theme).
   - Reserve strong accent colors strictly for functional states: `verified` (success), `numerical_support` (info), `partial` / `stale` (warning), and `error` / `inconclusive` (danger/neutral).
4. **Progressive Disclosure in Cells**:
   - Keep default cells compact and scannable: **Input → Computed Output → Verification Badge**.
   - Allow Problem Recognition, Method Selection, Assumptions, and Step-by-Step Derivations to expand cleanly on demand so notebooks never degrade into walls of nested cards.
5. **Keyboard-First Notebook Ergonomics**:
   - Consistent spacing rhythm, predictable alignment, distraction-free plot viewports, and fast keyboard workflows (e.g., `Shift + Enter` to execute a cell and advance).
