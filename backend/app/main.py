import asyncio
import sys

from fastapi import FastAPI

from app.api.health import router as health_router
from app.profile.router import router as profile_router
from app.search.router import router as search_router

# psycopg's async driver cannot use Windows' default ProactorEventLoop; select the
# selector loop policy on Windows so the app's DB connections work when the API runs
# on a Windows host (the Linux container is unaffected). Mirrors tests/conftest.py.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())  # pyright: ignore[reportDeprecated]


def create_app() -> FastAPI:
    app = FastAPI(title="Personal AI Job Hunter")
    app.include_router(health_router)
    app.include_router(profile_router)
    app.include_router(search_router)
    return app


app = create_app()
