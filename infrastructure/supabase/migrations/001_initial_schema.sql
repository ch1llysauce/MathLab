-- Initial MathLab PostgreSQL schema for Supabase (M4 Computational Notebook)

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    display_name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS notebooks (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    mode TEXT NOT NULL DEFAULT 'computational' CHECK (mode IN ('computational', 'learning')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS notebook_cells (
    id UUID PRIMARY KEY,
    notebook_id UUID NOT NULL REFERENCES notebooks(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    cell_type TEXT NOT NULL DEFAULT 'math' CHECK (cell_type IN ('math', 'markdown', 'ai')),
    operation TEXT,
    expression TEXT,
    variable TEXT,
    assign_to TEXT,
    assumptions_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    options_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'idle' CHECK (status IN ('idle', 'valid', 'stale', 'error')),
    depends_on JSONB NOT NULL DEFAULT '[]'::jsonb,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS computation_results (
    id UUID PRIMARY KEY,
    cell_id UUID NOT NULL REFERENCES notebook_cells(id) ON DELETE CASCADE,
    result_text TEXT NOT NULL,
    result_latex TEXT NOT NULL,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    reasoning_json JSONB,
    verification_json JSONB,
    executed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS variables_and_assumptions (
    id UUID PRIMARY KEY,
    notebook_id UUID NOT NULL REFERENCES notebooks(id) ON DELETE CASCADE,
    cell_id UUID REFERENCES notebook_cells(id) ON DELETE CASCADE,
    symbol_name TEXT NOT NULL,
    value_expr TEXT NOT NULL,
    value_latex TEXT NOT NULL,
    assumptions_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    UNIQUE (notebook_id, symbol_name)
);

CREATE TABLE IF NOT EXISTS notebook_history (
    id UUID PRIMARY KEY,
    notebook_id UUID NOT NULL REFERENCES notebooks(id) ON DELETE CASCADE,
    snapshot_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS saved_examples (
    id UUID PRIMARY KEY,
    title TEXT NOT NULL,
    domain TEXT NOT NULL,
    description TEXT,
    cells_json JSONB NOT NULL,
    is_public BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_notebook_cells_notebook_pos ON notebook_cells(notebook_id, position);
CREATE INDEX IF NOT EXISTS idx_computation_results_cell ON computation_results(cell_id);
CREATE INDEX IF NOT EXISTS idx_notebook_history_notebook ON notebook_history(notebook_id, created_at DESC);
