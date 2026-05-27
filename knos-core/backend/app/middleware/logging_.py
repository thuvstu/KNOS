# backend/app/middleware/logging_.py
import uuid
import time
import structlog
from fastapi import Request

logger = structlog.get_logger()


async def logging_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    start = time.monotonic()

    log = logger.bind(
        request_id=request_id,
        method=request.method,
        path=request.url.path,
    )
    log.info("request_started")

    try:
        response = await call_next(request)
        duration_ms = int((time.monotonic() - start) * 1000)
        log.info("request_finished", status=response.status_code, duration_ms=duration_ms)
        response.headers["X-Request-Id"] = request_id
        return response
    except Exception as e:
        log.error("request_failed", error=str(e), exc_info=True)
        raise
