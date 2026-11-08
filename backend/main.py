"""FastAPI application entrypoint."""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Ensure project root is importable when running `uvicorn backend.main:app`.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.dependencies import get_store_count
from backend.schemas import HealthResponse
from backend.routers import demand_science, fairness, forecast, market, match, recommendations, resume, search

try:
    from modules import store as job_store
except Exception:  # pragma: no cover
    job_store = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        if job_store is not None:
            job_store.init_db()
    except Exception:
        pass
    yield


app = FastAPI(
    title="TechSkillTracker API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    try:
        from modules import store as job_store

        backend = "postgres" if job_store.use_postgres() else "sqlite"
    except Exception:
        backend = "sqlite"
    postings = get_store_count()
    return HealthResponse(
        status="ok",
        backend=backend,
        postings=postings,
        store_available=postings > 0,
    )


# Routers
app.include_router(market.router)
app.include_router(forecast.router)
app.include_router(recommendations.router)
app.include_router(search.router)
app.include_router(demand_science.router)
app.include_router(fairness.router)
app.include_router(resume.router)
app.include_router(match.router)
