from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.core.config import get_settings
from app.services.madlad import MadladTranslator


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    translator = MadladTranslator(
        settings=settings,
    )

    translator.load()

    app.state.translator = translator

    yield

    translator.unload()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)


app.include_router(router)


@app.get("/")
async def root():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "model": settings.model_name,
        "docs": "/docs",
        "translate": "/v1/translate",
        "batch": "/v1/translate/batch",
    }