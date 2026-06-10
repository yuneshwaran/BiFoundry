import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.powerbi import router as powerbi_router
from api.project import router as project_router
from config import API_TITLE, API_VERSION, WORK_ROOT
from database import init_db


def get_cors_origins():
    origins = os.getenv("CORS_ORIGINS", "")
    if not origins:
        return ["*"]
    return [origin.strip() for origin in origins.split(",") if origin.strip()]


app = FastAPI(title=API_TITLE, version=API_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()
    os.makedirs(WORK_ROOT, exist_ok=True)


@app.get("/health")
def health():
    return {"status": "ok", "service": API_TITLE, "version": API_VERSION}


app.include_router(powerbi_router, prefix="/api")
app.include_router(project_router, prefix="/api")
