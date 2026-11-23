# MathLab

### AI-Assisted Computational and Mathematical Learning Workbench

**Learn the mathematics. Perform the computations. Understand the results.**

MathLab is an intelligent mathematical computing platform that combines advanced mathematical computation, explainable reasoning, result verification, interactive visualization, and guided learning into a unified workspace.

Instead of simply producing mathematical answers, MathLab aims to help users understand how a result was obtained, why a particular method was selected, what assumptions apply, and how the result can be verified.

## Overview

MathLab is designed for students, developers, and individuals who work with or explore mathematics beyond basic arithmetic.

It provides two interconnected experiences:

- **Computational Mode** – Perform mathematical operations, solve problems, compare methods, verify results, and experiment with mathematical models.
- **Learning Mode** – Explore mathematical concepts, understand derivations, follow guided solutions, and develop mathematical intuition.

Both modes share the same computational engine and notebook environment.

## Core Features

### 1. Computational Notebook
A persistent mathematical workspace where users can:
- Enter mathematical expressions and natural-language instructions.
- Execute computations through individual cells.
- Reference variables and previous results.
- Organize computations into reusable notebooks.
- Save and synchronize notebook contents.
- Revisit previous computations.

### 2. Mathematical Computation Engine
A mathematical engine supporting symbolic and numerical computation.

Initial mathematical domains:

- **Advanced Algebra:** Simplification, expansion, factorization, equation solving, and complex numbers.
- **Calculus:** Limits, differentiation, and integration.
- **Linear Algebra:** Matrix operations, determinants, rank, eigenvalues, and eigenvectors.
- **Numerical Mathematics:** Numerical evaluation, root finding, and approximations.

### 3. Intelligent Mathematical Reasoning
An intelligent reasoning layer that helps interpret mathematical problems and determine appropriate computational methods.

Capabilities include:
- Mathematical problem classification.
- Operation and method selection.
- Rule-based evaluation of method applicability.
- Identification of assumptions and mathematical constraints.
- Explanations of why a method was selected.

### 4. Verification and Analysis Engine
A dedicated component for checking computational results through:
- Symbolic equivalence checks.
- Numerical residual evaluation.
- Substitution into original equations.
- Cross-method comparisons.
- Domain and assumption validation.

Verification results are presented with appropriate qualifications. A successful computational check does not automatically constitute a formal mathematical proof.

### 5. Computational Visualization Studio
Interactive mathematical visualization for exploring relationships and behavior.

Initial visualization capabilities:
- 2D Cartesian function plotting.
- Multiple-function comparisons.
- Derivative and integral visualization.
- Roots, intercepts, critical points, and tangent lines.
- Basic 3D surface plotting.
- Interactive rotation, zooming, and parameter adjustments.

Future visualization capabilities may include vector fields, contour plots, phase portraits, and differential equation simulations.

### 6. AI-Assisted Mathematical Learning
An integrated assistant that provides contextual mathematical support.

Capabilities include:
- Natural-language mathematical input.
- Concept explanations.
- Step-by-step derivations.
- Guided problem-solving.
- Interpretation of computational results.
- Contextual assistance within notebooks.

AI-generated explanations are grounded in the mathematical computation engine wherever applicable.

## What Makes MathLab Different?

MathLab focuses on **Explainable Computational Mathematics**.

Its goal is to make mathematical computation more inspectable by presenting:

1. **Problem Recognition** – What mathematical problem did the system identify?
2. **Method Selection** – Which method was selected, and why?
3. **Mathematical Assumptions** – What conditions or constraints apply?
4. **Result Verification** – What checks were performed?
5. **Computational Exploration** – How does the result behave under different parameters or methods?

Rather than focusing exclusively on obtaining an answer, MathLab emphasizes understanding and examining the reasoning behind mathematical results.

## MathLab vs. MathMentor AI

MathLab and MathMentor AI serve different purposes.

| MathMentor AI | MathLab |
|---|---|
| Foundational mathematics education | Advanced mathematical computing |
| Learning-oriented | Computation-oriented with integrated learning |
| Guided lessons and exercises | Computational notebooks and experiments |
| Learner progress and assessment | Method selection and result verification |
| Algebra, trigonometry, geometry fundamentals | Algebra, calculus, linear algebra, and numerical mathematics |

**MathMentor helps users master mathematical foundations. MathLab helps users compute, analyze, and explore mathematics.**

## Technology Stack

| Component | Technology |
|---|---|
| Web Application | React, TypeScript, Vite |
| Mobile Application | React Native, Expo, TypeScript |
| Styling | Tailwind CSS |
| Backend API | Python, FastAPI |
| Symbolic Mathematics | SymPy |
| Numerical Computing | NumPy, SciPy |
| Visualization | Plotly |
| Mathematical Rendering | KaTeX |
| Notebook Editor | CodeMirror 6 |
| Database | Supabase PostgreSQL |
| Authentication | Supabase Auth |
| Web Hosting | Cloudflare Pages |
| Lightweight API / Edge Layer | Cloudflare Workers |
| Object Storage | Cloudflare R2 |
| AI Integration | External LLM API / Optional Local Ollama |
| Python Validation | Pydantic, pytest |
| JavaScript Package Manager | pnpm |
| Python Package Management | uv |

Cloudflare is used selectively for web delivery, lightweight edge functionality, and object storage. Mathematical execution remains in a conventional Python backend environment to support the requirements of SymPy, NumPy, and SciPy.

## High-Level Architecture

```text
                 ┌──────────────────────┐
                 │    React Web App     │
                 │  React + TypeScript  │
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │  Cloudflare Pages   │
                 │   + Workers Layer   │
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │    FastAPI Backend  │
                 │   Application API   │
                 └──────────┬───────────┘
                            │
               ┌────────────┼────────────┐
               ▼            ▼            ▼
        ┌────────────┐ ┌───────────┐ ┌───────────┐
        │ Math Engine│ │ Reasoning │ │Verification│
        │ SymPy etc. │ │  Engine   │ │   Engine   │
        └────────────┘ └───────────┘ └───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │ Supabase PostgreSQL  │
                 │  Persistent Storage  │
                 └──────────────────────┘

                 ┌──────────────────────┐
                 │    React Native      │
                 │    Expo Mobile       │
                 └──────────┬───────────┘
                            │
                            └── Same Backend API
```

Cloudflare R2 can additionally store notebook exports, generated assets, and other files.

## Project Status

**Development Stage:** Planned / Initial Development

MathLab is intended to be developed incrementally, beginning with its mathematical computation capabilities before expanding into intelligent reasoning, verification, visualization, and AI-assisted learning.

## Development Roadmap

| Milestone | Focus |
|---|---|
| M1 | Mathematical Computation Engine |
| M2 | Intelligent Mathematical Reasoning |
| M3 | Verification and Analysis Engine |
| M4 | Computational Notebook |
| M5 | Computational Visualization Studio |
| M6 | AI and Educational Integration |
| M7 | Web Application Release |
| M8 | Mobile Companion Application |

## Project Philosophy

MathLab is built around a simple idea:

**Mathematics should not be a black box.**

Users should be able to compute results, inspect the methods behind them, verify their validity, and explore the mathematics themselves.

---

*MathLab — From mathematical answers to inspectable mathematical reasoning.*