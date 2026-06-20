"""FastAPI application entry point.

Starts the HTTP API server for the proposal engine.
In production, run via: uvicorn app.main:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.contractors import router as contractors_router
from app.api.events import events_router
from app.api.routes import router
from core.db import init_db
from core.streaming import SSEBridge
from harness.hooks import HookRegistry, install_default_hooks
from harness.observability import setup_logging
from harness.tracing import setup_tracing


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    setup_logging(json_output=True)
    setup_tracing("proposal-engine")
    _hook_registry = HookRegistry()
    install_default_hooks(_hook_registry)
    SSEBridge.install()
    await init_db()
    yield


app = FastAPI(
    title="Proposal Engine",
    version="0.1.0",
    description="AI-powered contractor proposal generation from supplier quotes",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")
app.include_router(contractors_router, prefix="/api")
app.include_router(events_router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "healthy", "version": "0.1.0"}
