from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    description="API del sistema de corrección automática de exámenes manuscritos",
    version=settings.app_version,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
