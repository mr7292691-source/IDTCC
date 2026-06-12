"""IDTCC FastAPI application — Insurance Digital Twin Command Center."""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.routers import simulation, twins

# ── Configure LangSmith before anything else ─────────────────────────────────
os.environ.setdefault("LANGCHAIN_TRACING_V2",  settings.langchain_tracing_v2)
if settings.langchain_api_key:
    os.environ.setdefault("LANGCHAIN_API_KEY", settings.langchain_api_key)
os.environ.setdefault("LANGCHAIN_PROJECT",     settings.langchain_project)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pre-warm the graph on startup so first request is fast
    from app.graph.orchestrator import get_graph
    get_graph()
    yield


app = FastAPI(
    title="IDTCC — Insurance Digital Twin Command Center",
    description=(
        "50,000 living property twins. One catastrophe simulation. "
        "Seven AI agents orchestrated by LangGraph. Traced by LangSmith."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(simulation.router, prefix="/api/v1")
app.include_router(twins.router,      prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "IDTCC", "version": "1.0.0"}


@app.get("/api/v1/config")
async def get_config():
    return {
        "default_location":  settings.default_location,
        "default_twin_count": settings.default_twin_count,
        "langsmith_enabled": bool(settings.langchain_api_key),
        "langsmith_project":  settings.langchain_project,
    }
