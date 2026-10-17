from fastapi import APIRouter
from pydantic import BaseModel
from app.config import get_settings

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    status: str
    environment: str
    gemini_configured: bool
    serpapi_configured: bool


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Verify application health and configuration readiness without leaking secrets."""
    settings = get_settings()
    return HealthResponse(
        status="ok",
        environment=settings.app_env,
        gemini_configured=settings.has_gemini_credentials,
        serpapi_configured=settings.has_serpapi_credentials,
    )
