from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health
from app.api.auth import router as auth_router
from app.api.documents import router as documents_router
from app.api.exams import router as exams_router
from app.api.sessions import router as sessions_router
from app.api.users import router as users_router
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
app.include_router(auth_router, prefix="/auth")
app.include_router(users_router)
app.include_router(sessions_router)
app.include_router(documents_router)
app.include_router(exams_router)
