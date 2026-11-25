"""Visualization API routes."""

from fastapi import APIRouter

from app.schemas.visualization import PlotRequest, PlotResponse
from app.services.visualization_service import create_plot

router = APIRouter(prefix="/visualization", tags=["visualization"])


@router.post("/plot", response_model=PlotResponse)
def plot_expression(request: PlotRequest) -> PlotResponse:
    """Generate 2D or 3D Plotly-compatible plotting data and key mathematical features."""
    return create_plot(request)
