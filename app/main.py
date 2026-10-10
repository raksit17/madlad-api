from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.core.config import get_settings


settings = get_settings()


def create_translator():
    # Import only the selected provider; Qwen mode never loads MADLAD weights.
    if settings.translation_provider == "qwen":
        from app.experimental.qwen.translator import QwenTranslator

        return QwenTranslator(settings=settings)

    from app.services.madlad import MadladTranslator

    return MadladTranslator(settings=settings)


@asynccontextmanager
async def lifespan(app: FastAPI):
    translator = create_translator()
    translator.load()
    app.state.translator = translator

    try:
        yield
    finally:
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
        "provider": settings.translation_provider,
        "model": (
            settings.qwen_model
            if settings.translation_provider == "qwen"
            else settings.model_name
        ),
        "docs": "/docs",
        "translate": "/v1/translate",
        "batch": "/v1/translate/batch",
    }
