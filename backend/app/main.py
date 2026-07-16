from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import auth, health
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.db.session import dispose_engine
from app.queue.redis_client import close_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await dispose_engine()
    await close_redis()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="Distributed workflow orchestration engine",
        version="0.1.0",
        lifespan=lifespan,
    )

    from fastapi.middleware.cors import CORSMiddleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000", "http://localhost:3001", "http://localhost:3002", "http://localhost:3003", "http://localhost:3004",
            "http://127.0.0.1:3000", "http://127.0.0.1:3001", "http://127.0.0.1:3002", "http://127.0.0.1:3003", "http://127.0.0.1:3004"
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    app.include_router(health.router)
    app.include_router(auth.router)

    from app.api import workflows

    app.include_router(workflows.router)

    from app.api import executions

    app.include_router(executions.router)

    from app.api import dlq

    app.include_router(dlq.router)

    from app.api import workers

    app.include_router(workers.router)

    from app.api import metrics

    app.include_router(metrics.router)

    from app.api import websocket

    app.include_router(websocket.router)

    return app


app = create_app()
