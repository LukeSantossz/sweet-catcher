from fastapi import FastAPI

from app.api.health import router as health_router
from app.profile.router import router as profile_router


def create_app() -> FastAPI:
    app = FastAPI(title="Personal AI Job Hunter")
    app.include_router(health_router)
    app.include_router(profile_router)
    return app


app = create_app()
