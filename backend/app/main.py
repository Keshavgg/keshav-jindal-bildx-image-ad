import logging
import os
import re
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from app.config import settings
from app.models.schemas import (
    GenerationRequest,
    GenerationStatusResponse,
    HealthResponse,
    GenerationStatus,
)
from app.services.queue_manager import queue_manager, CapacityExceededError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("bildx-api")

app = FastAPI(
    title=settings.APP_NAME,
    description="Full-stack AI Image-Ad Generator with grounded creative copy and deterministic composition",
    version="1.0.0",
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Prevents leakage of sensitive configuration, credentials, or internal stack traces in production.
    """
    logger.exception(f"Unhandled server exception on {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. Please contact support or retry."}
    )


@app.post(
    "/api/generate",
    response_model=GenerationStatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start new image ad generation",
    responses={
        202: {"description": "Task accepted and scheduled"},
        429: {"description": "Queue capacity exceeded"},
        422: {"description": "Invalid product context or image URL format"},
    }
)
async def start_generation(
    request: GenerationRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")
):
    try:
        response, is_duplicate = await queue_manager.submit_generation(
            request=request,
            idempotency_key=idempotency_key
        )
        return response
    except CapacityExceededError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc)
        )


@app.get(
    "/api/status/{task_id}",
    response_model=GenerationStatusResponse,
    summary="Get generation task status and creative copy",
    responses={
        200: {"description": "Current status returned"},
        404: {"description": "Task ID not found"},
    }
)
async def get_task_status(task_id: str):
    task = queue_manager.get_task_status(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Generation task '{task_id}' not found."
        )
    return task


@app.get(
    "/api/download/{task_id}",
    summary="Download completed ad image as PNG",
    responses={
        200: {"description": "Binary PNG image file"},
        400: {"description": "Task is not yet completed"},
        404: {"description": "Task or file not found"},
    }
)
async def download_ad_image(task_id: str):
    task = queue_manager.get_task_status(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Generation task '{task_id}' not found."
        )

    if task.status != GenerationStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ad image is not ready for download. Current status is '{task.status}'."
        )

    filepath = Path(settings.OUTPUT_DIR) / f"{task_id}.png"
    if not filepath.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generated image file could not be located on disk."
        )

    # Sanitize product name for Content-Disposition filename
    product_name = "ad"
    if task_id in queue_manager._task_requests:
        raw_name = queue_manager._task_requests[task_id].product_name
        product_name = re.sub(r"[^a-zA-Z0-9_\-]+", "_", raw_name).strip("_")

    return FileResponse(
        path=str(filepath),
        media_type="image/png",
        filename=f"{product_name}-ad.png",
    )


@app.get(
    "/api/health",
    response_model=HealthResponse,
    summary="Health and concurrency capacity check"
)
async def health_check():
    provider = queue_manager.get_provider()
    return HealthResponse(
        status="healthy",
        provider=provider.provider_name,
        active_tasks=queue_manager.get_active_count(),
        queue_capacity=settings.MAX_QUEUE_CAPACITY,
        max_concurrent_calls=settings.MAX_CONCURRENT_PROVIDER_CALLS,
    )


@app.post(
    "/api/reset-state",
    summary="Reset queue state (for testing/demo)",
    include_in_schema=False
)
async def reset_state():
    await queue_manager.reset_state()
    return {"status": "reset_complete"}
