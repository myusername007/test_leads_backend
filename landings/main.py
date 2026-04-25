from fastapi import FastAPI

from landings.app.api.routes import router

app = FastAPI(
    title="Landings Service",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(router)