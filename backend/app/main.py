"""PQC Shield API — FastAPI app with CORS, v1 router, health check, startup create_all."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as v1_router
from app.core.database import create_all

VERSION = "0.1.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure CBOM (and any other) tables exist
    import app.models.cbom  # noqa: F401
    await create_all()
    yield


app = FastAPI(
    title="PQC Shield API",
    version=VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router)


@app.get("/health")
async def health() -> dict:
    """Health check."""
    return {"status": "ok", "version": VERSION}
