import asyncio

from fastapi import FastAPI
from contextlib import asynccontextmanager

from core.app.api.routes import router
from core.app.worker import run_worker


@asynccontextmanager
async def lifespan(app: FastAPI):
    # воркер у фоні при старті сервісу
    task = asyncio.create_task(run_worker())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="Core Service",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(router)