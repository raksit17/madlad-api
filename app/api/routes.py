from fastapi import (
    APIRouter,
    HTTPException,
    Request,
)

from starlette.concurrency import run_in_threadpool

from app.schemas.translation import (
    BatchTranslateRequest,
    BatchTranslateResponse,
    TranslateRequest,
    TranslateResponse,
)

from app.services.errors import (
    BatchTooLargeError,
    InputTooLongError,
    TranslationBackendError,
)


router = APIRouter()


@router.get("/health")
async def health():
    return {
        "status": "ok",
    }


@router.get("/ready")
async def ready(request: Request):
    translator = request.app.state.translator

    return {
        "ready": translator.is_ready(),
        "provider": translator.settings.translation_provider,
        "model": (
            translator.settings.qwen_model
            if translator.settings.translation_provider == "qwen"
            else translator.settings.model_name
        ),
        "device": (
            str(translator.input_device)
            if translator.input_device
            else None
        ),
    }


@router.post(
    "/v1/translate",
    response_model=TranslateResponse,
)
async def translate(
    payload: TranslateRequest,
    request: Request,
):
    translator = request.app.state.translator

    try:
        return await run_in_threadpool(
            translator.translate,
            payload.text,
            payload.source,
            payload.target,
            payload.max_new_tokens,
            payload.num_beams,
        )

    except InputTooLongError as exc:
        raise HTTPException(
            status_code=413,
            detail=str(exc),
        ) from exc

    except TranslationBackendError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc


@router.post(
    "/v1/translate/batch",
    response_model=BatchTranslateResponse,
)
async def translate_batch(
    payload: BatchTranslateRequest,
    request: Request,
):
    translator = request.app.state.translator

    try:
        return await run_in_threadpool(
            translator.translate_batch,
            payload.texts,
            payload.source,
            payload.target,
        )

    except InputTooLongError as exc:
        raise HTTPException(
            status_code=413,
            detail=str(exc),
        ) from exc

    except BatchTooLargeError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except TranslationBackendError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc