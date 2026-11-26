"""FastAPI application entry point."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.ai import router as ai_router
from app.api.routes.auth import router as auth_router
from app.api.routes.compute import router as compute_router
from app.api.routes.health import router as health_router
from app.api.routes.notebooks import router as notebooks_router
from app.api.routes.reasoning import router as reasoning_router
from app.api.routes.verification import router as verification_router
from app.api.routes.visualization import router as visualization_router
from app.core.config import settings
from app.core.exceptions import MathLabError

app = FastAPI(
    title="MathLab API",
    version="0.1.0",
    description="AI-Assisted Computational and Mathematical Learning Workbench API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(MathLabError)
async def mathlab_error_handler(_: Request, exc: MathLabError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request payload validation failed.",
                "details": {"errors": exc.errors()},
            }
        },
    )


@app.api_route("/", methods=["GET", "HEAD"])
def root() -> dict[str, str]:
    """Root status endpoint for browser checks and uptime probes."""
    return {"status": "ok", "message": "MathLab is working!"}


app.include_router(health_router, prefix="/api/v1")
app.include_router(compute_router, prefix="/api/v1")
app.include_router(reasoning_router, prefix="/api/v1")
app.include_router(verification_router, prefix="/api/v1")
app.include_router(notebooks_router, prefix="/api/v1")
app.include_router(visualization_router, prefix="/api/v1")
app.include_router(ai_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
