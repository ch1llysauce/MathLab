"""Service layer for generating mathematical visualization datasets."""

from __future__ import annotations

from app.modules.visualization_engine.sampler import generate_visualization_data
from app.schemas.visualization import PlotRequest, PlotResponse


def create_plot(request: PlotRequest) -> PlotResponse:
    """Generate validated 2D/3D Plotly datasets and key mathematical points."""
    raw = generate_visualization_data(
        expression=request.expression,
        expressions=request.expressions,
        plot_type=request.plot_type,
        variables=request.variables,
        x_range=request.x_range,
        y_range=request.y_range,
        num_points=request.num_points,
        grid_size=request.grid_size,
        parameters=request.parameters,
        assumptions=request.assumptions,
        include_derivative=request.include_derivative,
        include_integral=request.include_integral,
        tangent_at=request.tangent_at,
        tangent_y=request.tangent_y,
        detect_features=request.detect_features,
        matrix=request.matrix,
        matrix_b=request.matrix_b,
        vector=request.vector,
        matrix_view=request.matrix_view,
    )
    return PlotResponse(**raw)
