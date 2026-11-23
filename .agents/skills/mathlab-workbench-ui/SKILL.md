---
name: mathlab-workbench-ui
description: >-
  Use this skill when building or updating MathLab web UI components, notebook
  interfaces, visualizations, or learning-mode views in apps/web/.
---

# Building MathLab Workbench UI

Follow [ui-ux-workbench.md](../../../docs/design/ui-ux-workbench.md) so the interface stays a crisp computational workbench rather than generic AI-generated SaaS UI.

## Steps

1. **Apply Workbench Visual Standards**
   - Keep math legible and primary: crisp KaTeX typesetting, clean CodeMirror 6 inputs, and uncluttered Plotly viewports.
   - Avoid generic "AI slop": no neon/purple-blue gradients, glowing borders, heavy glassmorphism clutter, sparkle icons, or floating chatbot widgets detached from cells.
   - Reserve strong accent colors strictly for functional status (`verified`, `numerical_support`, `partial`, `stale`, `error`, `inconclusive`).
   - Use progressive disclosure: default cell view shows `Input -> Output -> Verification Badge`, with reasoning, assumptions, and derivations expandable on demand.

2. **Respect Frontend Architecture**
   - Keep mathematical computation on the Python backend; never replicate symbolic/numerical math logic in React components.
   - Place shared API calls in `apps/web/src/services/`, strict TypeScript types in `apps/web/src/types/`, and components under `apps/web/src/components/{common,notebook,computation,visualization,learning}/`.
   - Maintain TypeScript strict mode (`"strict": true` in [tsconfig.json](../../../apps/web/tsconfig.json)).

3. **Verify Build & Types**
   - Run the typecheck and production bundle from `apps/web/`:
     ```powershell
     npm run build
     ```
   - Confirm `tsc -b && vite build` exits with code 0.
