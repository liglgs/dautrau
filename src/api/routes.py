from fastapi import APIRouter

from src.config import get_settings

router = APIRouter()

# ``POST /api/v1/chat`` của template đã bị gỡ ở MVP: mọi lượt xử lý phải đi qua
# ``/api/v1/investigations`` để không bỏ qua budget và bước review.


@router.get("/status")
async def agent_status():
    """Readiness hint; worker status is tracked per run."""
    settings = get_settings()
    return {"status": "ready" if settings.openai_api_key and not settings.openai_api_key.startswith("sk-your-") else "model_unconfigured", "agent": "VMEC-03 worker"}
