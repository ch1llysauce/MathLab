"""Pydantic schemas for M5 Computational Visualization Studio endpoints."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class PlotRequest(BaseModel):
    """Request payload for generating 2D or 3D plotting datasets."""

    expression: str | None = Field(default=None, description="Primary mathematical expression.")
    expressions: list[str] = Field(
        default_factory=list,
        description="Optional list of expressions for multi-function comparison.",
    )
    plot_type: Literal["2d", "3d", "matrix"] = Field(default="2d")
    variables: list[str] = Field(
        default_factory=lambda: ["x"],
        description="Plot variables: ['x'] for 2D or ['x', 'y'] for 3D.",
    )
    x_range: list[float] | None = Field(default=None, description="[x_min, x_max]")
    y_range: list[float] | None = Field(default=None, description="[y_min, y_max] for 3D plots")
    num_points: int = Field(default=250, ge=10, le=1000)
    grid_size: int = Field(default=35, ge=10, le=80)
    parameters: dict[str, float] = Field(
        default_factory=dict,
        description="Interactive parameter bindings, e.g. {'a': 1.0, 'b': -2.0}.",
    )
    matrix: list[list[Any]] | None = Field(default=None, description="Primary matrix for matrix visualization.")
    matrix_b: list[list[Any]] | None = Field(default=None, description="Optional comparison/result matrix.")
    vector: list[Any] | None = Field(default=None, description="Optional target vector b for Ax = b plotting.")
    matrix_view: Literal["auto", "transform", "system", "heatmap", "surface"] = Field(default="auto")
    assumptions: dict[str, str] | None = Field(default=None)
    include_derivative: bool = Field(default=False)
    include_integral: bool = Field(default=False)
    tangent_at: float | None = Field(default=None)
    tangent_y: float | None = Field(default=None)
    detect_features: bool = Field(default=True)


class KeyPointSchema(BaseModel):
    """Important mathematical point detected on a 2D curve."""

    kind: str
    x: float
    y: float
    label: str
    derivative_expr: str | None = None


class PlotLayoutSchema(BaseModel):
    """Plot axis and title metadata."""

    title: str
    xaxis_title: str
    yaxis_title: str
    zaxis_title: str | None = None


class PlotResponse(BaseModel):
    """Structured Plotly-compatible visualization response."""

    plot_type: Literal["2d", "3d"]
    traces: list[dict[str, Any]]
    key_points: list[KeyPointSchema] = Field(default_factory=list)
    layout: PlotLayoutSchema
    metadata: dict[str, Any] = Field(default_factory=dict)
