"""IDTCC FastAPI application — Insurance Digital Twin Command Center."""
from __future__ import annotations

import logging
import os
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from app.config import settings
from app.core.logging_config import configure_logging, get_logger, log_event, request_id_var
from app.core.metrics import METRICS
from app.routers import alerts, safety, simulation, twins

# ── Configure logging + LangSmith before anything else ───────────────────────
configure_logging(level=settings.log_level, json_logs=settings.json_logs)
log = get_logger("idtcc.api")

os.environ.setdefault("LANGCHAIN_TRACING_V2",  settings.langchain_tracing_v2)
if settings.langchain_api_key:
    os.environ.setdefault("LANGCHAIN_API_KEY", settings.langchain_api_key)
os.environ.setdefault("LANGCHAIN_PROJECT",     settings.langchain_project)

# Readiness flips True once the graph is compiled and warm.
_READY = {"value": False}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pre-warm the graph on startup so the first request is fast.
    from app.graph.orchestrator import get_graph
    from app.graph.safety_orchestrator import get_safety_graph
    get_graph()
    get_safety_graph()
    _READY["value"] = True
    log_event(log, logging.INFO, "startup.complete",
              provider=settings.llm_provider, model=settings.vllm_model)
    yield


app = FastAPI(
    title="LifeShield AI — Disaster Intelligence Platform",
    description=(
        "Digital twins of citizens, property, shelters and infrastructure. "
        "16 AI agents orchestrated by LangGraph on AMD MI300X. "
        "Two lenses: insurance loss forecasting and life-safety response."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

@app.middleware("http")
async def request_context(request: Request, call_next):
    """Attach a correlation id, time the request, and record HTTP metrics."""
    rid = request.headers.get("x-request-id") or uuid.uuid4().hex
    token = request_id_var.set(rid)
    start = time.perf_counter()
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    except Exception as exc:  # noqa: BLE001
        METRICS.inc("idtcc_http_requests_total", method=request.method,
                    path=request.url.path, status="500")
        log_event(log, logging.ERROR, "http.error", method=request.method,
                  path=request.url.path, error=str(exc))
        raise
    finally:
        elapsed = time.perf_counter() - start
        METRICS.observe("idtcc_http_request_duration_seconds", elapsed,
                        method=request.method, path=request.url.path)
        try:
            METRICS.inc("idtcc_http_requests_total", method=request.method,
                        path=request.url.path, status=str(locals().get("status", "n/a")))
        finally:
            request_id_var.reset(token)


app.include_router(simulation.router, prefix="/api/v1")
app.include_router(twins.router,      prefix="/api/v1")
app.include_router(safety.router,     prefix="/api/v1")
app.include_router(alerts.router,     prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "LifeShield AI", "version": "2.0.0"}


@app.get("/health/live")
async def liveness():
    """Liveness probe — process is up."""
    return {"status": "alive"}


@app.get("/health/ready")
async def readiness():
    """Readiness probe — graph compiled and ready to serve simulations."""
    if not _READY["value"]:
        return JSONResponse(status_code=503, content={"status": "starting"})
    return {"status": "ready"}


@app.get("/metrics")
async def metrics():
    """Prometheus exposition endpoint (application-layer metrics)."""
    return PlainTextResponse(METRICS.render(), media_type="text/plain; version=0.0.4")


@app.get("/api/v1/metrics/summary")
async def metrics_summary():
    """Human-friendly metrics snapshot for the Backend dashboard view."""
    return METRICS.snapshot()


@app.get("/api/v1/config")
async def get_config():
    return {
        "default_location":  settings.default_location,
        "default_twin_count": settings.default_twin_count,
        "llm_provider":       settings.llm_provider,
        "llm_model":          settings.vllm_model,
        "langsmith_enabled": bool(settings.langchain_api_key),
        "langsmith_project":  settings.langchain_project,
    }
