import re
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.api.admin import router as admin_router
from src.api.auth import TOKEN_HEADER
from src.api.auth import router as auth_router
from src.api.investigations import router as investigations_router
from src.api.mvp_runtime import configure_mvp, get_mvp_runner, get_mvp_store
from src.api.research_routes import router as research_router
from src.api.reviews import router as reviews_router
from src.api.routes import router
from src.api.v2_routes import router as v2_router
from src.api.vmec_routes import router as vmec_router
from src.api.warehouse_routes import router as warehouse_router
from src.api.workflow_routes import router as workflow_router
from src.config import get_settings
from src.models.schemas import ErrorCode
from src.services.errors import MvpError, validation_details
from src.services.request_context import current_request_id, reset_request_id, set_request_id
from src.vmec import DomainError

#: ``Identifier`` của hợp đồng hospital-v2: ``^[A-Za-z0-9][A-Za-z0-9._:-]*$``, tối đa 120 ký tự.
_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
_IDENTIFIER_MAX_LENGTH = 120

#: Tập mã lỗi hợp lệ của hợp đồng, lấy thẳng từ ``ErrorCode`` — hai bên trùng khít 15 giá trị.
_CONTRACT_ERROR_CODES = frozenset(str(code) for code in ErrorCode)

#: Ánh xạ mã HTTP sang mã lỗi hợp đồng, cho các lỗi không đi qua ``MvpError``.
_CONTRACT_CODE_BY_STATUS: dict[int, str] = {
    400: str(ErrorCode.INVALID_REQUEST),
    401: str(ErrorCode.UNAUTHORIZED),
    403: str(ErrorCode.FORBIDDEN),
    404: str(ErrorCode.NOT_FOUND),
    405: str(ErrorCode.INVALID_REQUEST),
    406: str(ErrorCode.INVALID_REQUEST),
    409: str(ErrorCode.INVALID_STATE),
    413: str(ErrorCode.INVALID_REQUEST),
    415: str(ErrorCode.INVALID_REQUEST),
    422: str(ErrorCode.INVALID_REQUEST),
    429: str(ErrorCode.RUNNER_BUSY),
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    print(f"Starting {settings.app_name} in {settings.app_env} mode")
    configure_mvp()
    yield
    print("Shutting down...")


app = FastAPI(
    title="VigiLens",
    description="Điều tra nhận định an toàn thuốc trên PubMed, DailyMed và openFDA FAERS, có bằng chứng và có người duyệt.",
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

@app.middleware("http")
async def attach_request_id(request: Request, call_next):
    """Gắn một mã cho mỗi yêu cầu, dùng chung cho envelope lỗi và nhật ký kiểm toán.

    Nhận ``X-Request-Id`` do cầu nối hoặc hệ thống ngoài gửi vào để tra vết xuyên tầng; nếu không
    có thì tự sinh. Mã được trả lại trong header cùng tên.

    Mã nhận vào chỉ được giữ khi nó hợp lệ theo ``$defs/Identifier`` của hợp đồng hospital-v2 —
    ``^[A-Za-z0-9][A-Za-z0-9._:-]*$``, tối đa 120 ký tự. Mã không hợp lệ bị thay bằng mã tự sinh,
    vì ``request_id`` nằm trong envelope lỗi mà ``/api/v2`` phải khớp hợp đồng, nên để nguyên là
    khách gọi tự làm hỏng hợp đồng của chính mình. Mã sai định dạng cũng vô dụng khi tra vết.
    """
    incoming = (request.headers.get("x-request-id") or "").strip()
    usable = (
        incoming
        if len(incoming) <= _IDENTIFIER_MAX_LENGTH and _IDENTIFIER_PATTERN.match(incoming)
        else ""
    )
    request_id = usable or str(uuid4())
    token = set_request_id(request_id)
    try:
        response = await call_next(request)
    finally:
        reset_request_id(token)
    response.headers["X-Request-Id"] = request_id
    return response


app.include_router(auth_router, prefix="/api/v1")
app.include_router(investigations_router, prefix="/api/v1")
app.include_router(reviews_router, prefix="/api/v1")
app.include_router(router, prefix="/api/v1")
app.include_router(vmec_router, prefix="/api/v1")
app.include_router(warehouse_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(workflow_router, prefix="/api/v2")
app.include_router(v2_router, prefix="/api/v2")
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


def _error_envelope(
    code: str, message: str, *, details: dict | None = None, retryable: bool = False
) -> dict:
    """Envelope lỗi dùng chung: ``{"error": {...}}`` + khoá phẳng tương thích client VMEC cũ.

    MVP (Người 4) đọc ``error.code``/``error.request_id``; các route VMEC cũ đọc trực tiếp
    ``code``/``message`` nên giữ thêm khoá phẳng để không phá vỡ hợp đồng cũ.
    """
    request_id = current_request_id() or str(uuid4())
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


def _wants_contract_envelope(request: Request) -> bool:
    """``/api/v2`` nói theo hợp đồng hospital-v2; ``/api/v1`` và khách VMEC giữ envelope cũ."""
    return request.url.path.startswith("/api/v2")


def _contract_error_envelope(code: str, message: str, *, details: dict | None = None) -> dict:
    """Envelope lỗi **đúng** ``$defs/ApiError`` của hợp đồng hospital-v2, không thêm gì.

    Envelope dùng chung ở trên có hai thứ hợp đồng từ chối: khoá ``retryable`` bên trong
    ``error`` (``additionalProperties: false``) và các khoá ``code``/``message``/``request_id``/
    ``retryable`` lặp phẳng ở cấp gốc. Hệ quả trước đây là **mọi** phản hồi 4xx/5xx của
    ``/api/v2`` trượt kiểm hợp đồng, kể cả 409/422 mà hợp đồng khai báo tường minh. Hai khoá phẳng
    chỉ tồn tại cho khách VMEC cũ, nên tầng mới phát hình dạng riêng thay vì sửa envelope chung.
    """
    return {
        "error": {
            "code": code,
            "message": message[:500],
            "details": details if details else {},
            "request_id": current_request_id() or str(uuid4()),
        }
    }


def _contract_code(status: int, hint: str) -> str:
    """Chọn mã lỗi nằm trong enum của ``$defs/ApiError``.

    Đường cũ sinh ``http_error`` cho mọi mã không phải 404; chuỗi đó không có trong enum nên
    không dùng lại được ở đây. Mã hợp lệ sẵn thì giữ nguyên.
    """
    if hint in _CONTRACT_ERROR_CODES:
        return hint
    return _CONTRACT_CODE_BY_STATUS.get(status, str(ErrorCode.UNAVAILABLE))


def _error_response(
    request: Request,
    status: int,
    code: str,
    message: str,
    *,
    details: dict | None = None,
    retryable: bool = False,
    legacy: dict | None = None,
) -> JSONResponse:
    """Dựng phản hồi lỗi theo đúng hợp đồng mà đường dẫn yêu cầu phải theo.

    ``legacy`` cho phép đường cũ giữ nguyên **đúng** thân phản hồi cũ của nó. Lỗi ``MvpError`` của
    ``/api/v1`` trước đây chỉ có ``{"error": {...}}``, không có khoá phẳng; dùng chung
    ``_error_envelope`` sẽ lặng lẽ thêm bốn khoá vào một API đang chạy. Việc này chỉ nhằm tách
    envelope cho ``/api/v2``, nên đường cũ không được đổi gì.
    """
    if _wants_contract_envelope(request):
        return JSONResponse(
            status_code=status,
            content=_contract_error_envelope(_contract_code(status, code), message, details=details),
        )
    if legacy is not None:
        return JSONResponse(status_code=status, content=legacy)
    return JSONResponse(
        status_code=status, content=_error_envelope(code, message, details=details, retryable=retryable)
    )


@app.exception_handler(MvpError)
async def mvp_error(request: Request, exc: MvpError):
    return _error_response(
        request,
        exc.status,
        str(exc.code),
        exc.message,
        details=exc.details,
        retryable=exc.retryable,
        legacy=exc.envelope(current_request_id() or str(uuid4())),
    )


@app.exception_handler(DomainError)
async def domain_error(request: Request, exc: DomainError):
    return _error_response(request, exc.status, str(exc.code), exc.message, retryable=exc.retryable)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    return _error_response(
        request,
        422,
        str(ErrorCode.INVALID_REQUEST),
        "Dữ liệu gửi lên không đúng schema.",
        details={"errors": validation_details(exc)},
    )


@app.exception_handler(StarletteHTTPException)
async def http_error(request: Request, exc: StarletteHTTPException):
    code = "not_found" if exc.status_code == 404 else "http_error"
    return _error_response(request, exc.status_code, code, str(exc.detail), retryable=exc.status_code >= 500)


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
