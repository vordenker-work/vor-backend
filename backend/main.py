import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.database import engine
from models import models
from routers import ai, auth, marketplace, recruiters, sync, ws


@asynccontextmanager
async def lifespan(app: FastAPI):
    models.Base.metadata.create_all(bind=engine)
    if os.getenv("SEED_DEMO_JOBS", "true").lower() == "true":
        marketplace.seed_demo_jobs_if_empty()
    yield


app = FastAPI(
    title="Vor / AI-Career Bridge API",
    description="Unified backend for the PyQt6 student desktop app and recruiter web portal",
    version="0.2.0",
    lifespan=lifespan,
)

cors_origins_env = os.getenv("CORS_ORIGINS", "*").strip()
cors_origins = (
    ["*"]
    if cors_origins_env == "*"
    else [o.strip() for o in cors_origins_env.split(",") if o.strip()]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(auth.router)
app.include_router(sync.router)
app.include_router(ai.router)
app.include_router(recruiters.router)
app.include_router(marketplace.router)
app.include_router(ws.router)


@app.get("/health")
def health_check():
    return {"status": "online", "service": "ai-academic-planner-backend"}
