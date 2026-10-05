from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.api.auth import TOKEN_HEADER
from src.api.auth import router as auth_router
from src.api.investigations import router as investigations_router
from src.api.mvp_runtime import configure_mvp, get_mvp_runner, get_mvp_store
from src.api.research_routes import router as research_router
from src.api.reviews import router as reviews_router
from src.api.routes import router
from src.api.vmec_routes import router as vmec_router
from src.config import get_settings
from src.services.errors import MvpError, validation_details
from src.vmec import DomainError


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    print(f"Starting {settings.app_name} in {settings.app_env} mode")
    configure_mvp()
    yield
    print("Shutting down...")


app = FastAPI(
    title="MedReview VMEC-03",
    description="Nghiên cứu đối chiếu thuốc trên dữ liệu mô phỏng",
    version="0.1.0",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(investigations_router, prefix="/api/v1")
app.include_router(reviews_router, prefix="/api/v1")
app.include_router(router, prefix="/api/v1")
app.include_router(vmec_router, prefix="/api/v1")
app.include_router(research_router)


def custom_openapi() -> dict:
    """OpenAPI kèm security scheme cho các route MVP (sinh client không bị 401 oan)."""
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    schemes = schema.setdefault("components", {}).setdefault("securitySchemes", {})
    schemes["MvpApiToken"] = {
        "type": "apiKey",
        "in": "header",
        "name": TOKEN_HEADER,
        "description": f"Token theo vai trò (investigator/reviewer) gửi qua header {TOKEN_HEADER}.",
    }
    for operations in schema.get("paths", {}).values():
        for operation in operations.values():
            if not isinstance(operation, dict):
                continue
            tags = operation.get("tags") or []
            if any(str(tag).startswith("mvp") for tag in tags):
                operation.setdefault("security", [{"MvpApiToken": []}])
    app.openapi_schema = schema
    return schema


app.openapi = custom_openapi


@app.exception_handler(MvpError)
async def mvp_error(request: Request, exc: MvpError):
    return JSONResponse(status_code=exc.status, content=exc.envelope(str(uuid4())))


def _error_envelope(
    code: str, message: str, *, details: dict | None = None, retryable: bool = False
) -> dict:
    """Envelope lỗi dùng chung: ``{"error": {...}}`` + khoá phẳng tương thích client VMEC cũ.

    MVP (Người 4) đọc ``error.code``/``error.request_id``; các route VMEC cũ đọc trực tiếp
    ``code``/``message`` nên giữ thêm khoá phẳng để không phá vỡ hợp đồng cũ.
    """
    request_id = str(uuid4())
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
            "request_id": request_id,
            "retryable": retryable,
        },
        "code": code,
        "message": message,
        "request_id": request_id,
        "retryable": retryable,
    }


@app.exception_handler(DomainError)
async def domain_error(request: Request, exc: DomainError):
    return JSONResponse(
        status_code=exc.status,
        content=_error_envelope(str(exc.code), exc.message, retryable=exc.retryable),
    )


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content=_error_envelope(
            "invalid_request",
            "Dữ liệu gửi lên không đúng schema.",
            details={"errors": validation_details(exc)},
        ),
    )


@app.exception_handler(StarletteHTTPException)
async def http_error(request: Request, exc: StarletteHTTPException):
    code = "not_found" if exc.status_code == 404 else "http_error"
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_envelope(code, str(exc.detail), retryable=exc.status_code >= 500),
    )


@app.get("/health")
async def health():
    """Liveness: tiến trình còn sống."""
    return {"status": "ok", "env": settings.app_env}


@app.get("/ready")
async def ready():
    """Readiness: store MVP đọc được và runner sẵn sàng nhận việc.

    Endpoint này không cần token (dùng cho health-check) nên chỉ trả thông tin tối thiểu,
    không lộ ID cuộc điều tra đang chạy hay chi tiết lỗi nội bộ.
    """
    try:
        store = get_mvp_store()
        store.list_investigations(limit=1)
        runner = get_mvp_runner()
    except Exception:  # noqa: BLE001 - báo lỗi readiness thay vì 500
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "reason": "store hoặc runner chưa sẵn sàng"},
        )
    return {
        "status": "ready",
        "env": settings.app_env,
        "runner_busy": runner.is_busy,
        "runner_active": runner.current is not None,
    }
