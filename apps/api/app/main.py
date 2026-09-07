from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.database import Base, engine
from app.domains.audit.router import router as audit_router
from app.domains.auth.router import router as auth_router
from app.domains.boq.router import router as boq_router
from app.domains.exports.router import router as exports_router
from app.domains.parsing.router import router as parsing_router
from app.domains.quotes.router import router as quotes_router
from app.domains.suppliers.router import router as suppliers_router
from app.seed import seed_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.environment != "testing":
        # Initialize database tables on startup (especially for SQLite dev mode)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        # Automatically seed if database is empty
        try:
            await seed_database()
        except Exception as e:
            print(f"Seed info: {e}")
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="BoQ pricing and supplier quote marketplace for South African contractors.",
    lifespan=lifespan,
)

# Robust CORS configuration for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if isinstance(exc.detail, dict):
        err_code = exc.detail.get("code", f"HTTP_{exc.status_code}")
        err_msg = exc.detail.get("message", "An error occurred")
        err_details = exc.detail.get("details", {})
    else:
        err_code = f"HTTP_{exc.status_code}"
        err_msg = str(exc.detail)
        err_details = {}

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": err_code,
                "message": err_msg,
                "details": err_details,
            },
            "detail": exc.detail,
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    if settings.debug:
        print(f"Unhandled Exception: {exc}")
        traceback.print_exc()

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected internal server error occurred.",
                "details": str(exc) if settings.debug else {},
            }
        },
    )


# Root and Health check
@app.get("/", tags=["General"])
async def root():
    return {
        "status": "online",
        "app": settings.app_name,
        "version": settings.app_version,
        "docs_url": "/docs",
        "health_url": "/api/v1/health",
    }


@app.get("/health", tags=["Health"])
@app.get("/api/v1/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name, "version": settings.app_version}


# Register domain routers under API v1 prefix
app.include_router(auth_router, prefix=settings.api_v1_prefix)
app.include_router(boq_router, prefix=settings.api_v1_prefix)
app.include_router(parsing_router, prefix=settings.api_v1_prefix)
app.include_router(suppliers_router, prefix=settings.api_v1_prefix)
app.include_router(quotes_router, prefix=settings.api_v1_prefix)
app.include_router(audit_router, prefix=settings.api_v1_prefix)
app.include_router(exports_router, prefix=settings.api_v1_prefix)
