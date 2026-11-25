-- Initial database seed file for MathLab (Supabase PostgreSQL).

INSERT INTO saved_examples (id, title, domain, description, cells_json, is_public)
VALUES
    (
        '00000000-0000-0000-0000-000000000101',
        'Polynomial Derivative via Power Rule',
        'calculus',
        'Differentiate a polynomial and inspect finite-difference verification.',
        '[{"cell_type": "math", "operation": "differentiate", "expression": "x^3 + 2*x", "variable": "x"}]'::jsonb,
        TRUE
    ),
    (
        '00000000-0000-0000-0000-000000000102',
        'Solving and Verifying a Quadratic Equation',
        'algebra',
        'Find roots of a quadratic equation and verify by direct symbolic substitution.',
        '[{"cell_type": "math", "operation": "solve", "expression": "x^2 - 5*x + 6 = 0", "variable": "x"}]'::jsonb,
        TRUE
    ),
    (
        '00000000-0000-0000-0000-000000000103',
        'Definite Integral & Quadrature Cross-Check',
        'calculus',
        'Evaluate a definite integral symbolically and cross-check with adaptive quadrature.',
        '[{"cell_type": "math", "operation": "integrate", "expression": "x^2", "variable": "x", "options": {"lower": 0, "upper": 3}}]'::jsonb,
        TRUE
    )
ON CONFLICT (id) DO NOTHING;
