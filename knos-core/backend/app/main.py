# backend/app/main.py
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_settings
from .database import check_db_connection
from .services.embedding import get_embedding_service
from .middleware.logging_ import logging_middleware
from .routers import entries, search, graph, import_, srs, taxonomy, ai

logger = structlog.get_logger()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ─── Startup ───
    logger.info("knos_starting", version="1.0.0")

    ok = await check_db_connection()
    if not ok:
        logger.error("db_unavailable_at_startup")

    emb = get_embedding_service()
    await emb.start()
    logger.info("embedding_service_ready")

    yield

    # ─── Shutdown ───
    await emb.stop()
    logger.info("knos_stopped")


app = FastAPI(
    title="KnOS Core API",
    version="1.0.0",
    description="個人知識OS バックエンド — Phase 0〜5 + EX",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ─── CORS ───
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Logging ───
app.middleware("http")(logging_middleware)

# ─── Routers ───
app.include_router(entries.router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.include_router(graph.router, prefix="/api")
app.include_router(import_.router, prefix="/api")
app.include_router(srs.router, prefix="/api")
app.include_router(taxonomy.router, prefix="/api")
app.include_router(ai.router, prefix="/api")


# ─── Health ───
@app.get("/api/health")
async def health():
    db_ok = await check_db_connection()
    return {
        "status": "ok" if db_ok else "degraded",
        "db": "connected" if db_ok else "disconnected",
        "version": "1.0.0",
    }


# ─── Global exception handler ───
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("unhandled_exception", path=request.url.path, error=str(exc), exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})
