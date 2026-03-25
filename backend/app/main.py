from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router, ws_router
from app.config import settings
from app.services.metrics.collector import metrics_collector


@asynccontextmanager
async def lifespan(app: FastAPI):
    metrics_collector.start()
    yield
    metrics_collector.stop()


app = FastAPI(
    title="CarbonPanel",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
app.include_router(ws_router)
