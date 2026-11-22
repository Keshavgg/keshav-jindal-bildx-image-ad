import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Tuple
from app.config import settings
from app.models.schemas import (
    GenerationRequest,
    GenerationStatus,
    GenerationMetadata,
    GenerationStatusResponse,
    CreativeCopy,
)
from app.prompts.copy_grounding import PROMPT_VERSION
from app.providers import get_provider
from app.providers.base import (
    BaseAIProvider,
    TemporaryProviderError,
    PermanentProviderError,
    ProviderTimeoutError,
)
from app.services.image_downloader import (
    download_and_validate_image,
    ImageDownloadError,
    ImageSecurityError,
    ImageSizeError,
    InvalidImageError,
)
from app.services.composer import AdCompositor

logger = logging.getLogger(__name__)


class CapacityExceededError(Exception):
    """Raised when the server's concurrent task capacity is saturated."""
    pass


class GenerationQueueManager:
    """
    Manages generation lifecycle, bounded concurrency, idempotency deduplication,
    capacity bounds, failure isolation, and exponential backoff retries.
    """

    def __init__(self, provider: Optional[BaseAIProvider] = None):
        self._provider = provider or get_provider(settings.AI_PROVIDER)
        self._semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_PROVIDER_CALLS)
        self._tasks: Dict[str, GenerationStatusResponse] = {}
        self._task_requests: Dict[str, GenerationRequest] = {}
        self._idempotency_map: Dict[str, str] = {}
        self._task_futures: Dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()
        self._compositor = AdCompositor()

    def set_provider(self, provider: BaseAIProvider):
        """Allows swapping provider (e.g. for testing specific failure modes)."""
        self._provider = provider

    def get_provider(self) -> BaseAIProvider:
        return self._provider

    async def reset_state(self):
        """Cleans up all tasks and cancels in-flight jobs. Used for test isolation."""
        async with self._lock:
            for task in self._task_futures.values():
                if not task.done():
                    task.cancel()
            self._tasks.clear()
            self._task_requests.clear()
            self._idempotency_map.clear()
            self._task_futures.clear()

    def get_active_count(self) -> int:
        return sum(
            1 for t in self._tasks.values()
            if t.status in (GenerationStatus.PENDING, GenerationStatus.PROCESSING, GenerationStatus.RETRYING)
        )

    async def submit_generation(
        self,
        request: GenerationRequest,
        idempotency_key: Optional[str] = None
    ) -> Tuple[GenerationStatusResponse, bool]:
        """
        Submits a generation request.
        Returns (GenerationStatusResponse, is_duplicate).
        Raises CapacityExceededError if queue is full.
        """
        async with self._lock:
            # 1. Idempotency Check
            if idempotency_key:
                clean_key = idempotency_key.strip()
                if clean_key in self._idempotency_map:
                    existing_id = self._idempotency_map[clean_key]
                    if existing_id in self._tasks:
                        logger.info(f"Duplicate idempotency key '{clean_key}' matched task {existing_id}")
                        return self._tasks[existing_id], True

            # 2. Capacity Check
            active_count = self.get_active_count()
            if active_count >= settings.MAX_QUEUE_CAPACITY:
                logger.warning(
                    f"Rejected request: active tasks ({active_count}) >= capacity ({settings.MAX_QUEUE_CAPACITY})"
                )
                raise CapacityExceededError(
                    f"Server capacity reached ({settings.MAX_QUEUE_CAPACITY} active jobs). Please retry shortly."
                )

            # 3. Create Task Record
            task_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)

            metadata = GenerationMetadata(
                model=self._provider.provider_name,
                prompt_version=PROMPT_VERSION,
                source_url=str(request.image_url),
                created_at=now,
                retry_count=0,
            )

            response = GenerationStatusResponse(
                task_id=task_id,
                status=GenerationStatus.PENDING,
                idempotency_key=idempotency_key,
                created_at=now,
                updated_at=now,
                retry_count=0,
                metadata=metadata,
            )

            self._tasks[task_id] = response
            self._task_requests[task_id] = request
            if idempotency_key:
                self._idempotency_map[idempotency_key.strip()] = task_id

            # 4. Spawn Background Worker Task (Isolated Execution)
            worker_task = asyncio.create_task(self._process_task(task_id))
            self._task_futures[task_id] = worker_task

            return response, False

    def get_task_status(self, task_id: str) -> Optional[GenerationStatusResponse]:
        return self._tasks.get(task_id)

    async def _update_task_status(
        self,
        task_id: str,
        status: GenerationStatus,
        error_message: Optional[str] = None,
        creative_copy: Optional[CreativeCopy] = None,
        ad_image_url: Optional[str] = None,
        duration_ms: Optional[float] = None,
    ):
        if task_id in self._tasks:
            task = self._tasks[task_id]
            task.status = status
            task.updated_at = datetime.now(timezone.utc)
            if error_message is not None:
                task.error_message = error_message
            if creative_copy is not None:
                task.creative_copy = creative_copy
            if ad_image_url is not None:
                task.ad_image_url = ad_image_url
            if task.metadata:
                task.metadata.retry_count = task.retry_count
                if status in (GenerationStatus.COMPLETED, GenerationStatus.FAILED):
                    task.metadata.completed_at = datetime.now(timezone.utc)
                    task.metadata.duration_ms = duration_ms

    async def _process_task(self, task_id: str):
        """
        Background worker pipeline:
        1. Validate & download source image (Permanent fail-fast on error)
        2. Bounded provider concurrency via Semaphore
        3. Retry loop for transient failures with exponential backoff
        4. Compose final high-res ad and persist
        """
        start_time = time.perf_counter()
        request = self._task_requests[task_id]

        try:
            # Transition to PROCESSING
            await self._update_task_status(task_id, GenerationStatus.PROCESSING)

            # --- STEP 1: Safe Image Download & Validation ---
            try:
                product_image = await download_and_validate_image(str(request.image_url))
            except (ImageSecurityError, ImageSizeError, InvalidImageError, ImageDownloadError) as exc:
                # Permanent validation errors - DO NOT retry
                logger.error(f"Task {task_id} image download failed: {exc}")
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                await self._update_task_status(
                    task_id,
                    status=GenerationStatus.FAILED,
                    error_message=str(exc),
                    duration_ms=duration_ms
                )
                return

            # --- STEP 2: AI Provider with Bounded Concurrency & Retries ---
            copy_result: Optional[CreativeCopy] = None
            bg_image = None
            max_retries = settings.MAX_RETRIES
            attempt = 0

            while attempt <= max_retries:
                try:
                    async with self._semaphore:
                        # Enforce provider timeout
                        copy_result = await asyncio.wait_for(
                            self._provider.generate_ad_copy(request),
                            timeout=settings.PROVIDER_TIMEOUT_SECONDS
                        )
                        bg_image = await asyncio.wait_for(
                            self._provider.generate_background(
                                visual_direction=copy_result.visual_direction,
                                tone=request.tone,
                                width=1080,
                                height=1080
                            ),
                            timeout=settings.PROVIDER_TIMEOUT_SECONDS
                        )
                        # Succeeded!
                        break

                except (TemporaryProviderError, ProviderTimeoutError, asyncio.TimeoutError) as exc:
                    attempt += 1
                    if task_id in self._tasks:
                        self._tasks[task_id].retry_count = attempt

                    if attempt <= max_retries:
                        delay = settings.RETRY_INITIAL_DELAY_SECONDS * (settings.RETRY_BACKOFF_FACTOR ** (attempt - 1))
                        logger.warning(
                            f"Task {task_id} transient error ({exc}). Retrying attempt {attempt}/{max_retries} in {delay:.2f}s"
                        )
                        await self._update_task_status(
                            task_id,
                            status=GenerationStatus.RETRYING,
                            error_message=f"Temporary issue encountered. Retrying in {delay:.1f}s: {exc}"
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"Task {task_id} exhausted all {max_retries} retries: {exc}")
                        duration_ms = (time.perf_counter() - start_time) * 1000.0
                        await self._update_task_status(
                            task_id,
                            status=GenerationStatus.FAILED,
                            error_message=f"Generation failed after {max_retries} retries: {exc}",
                            duration_ms=duration_ms
                        )
                        return

                except PermanentProviderError as exc:
                    # Permanent error: fail-fast without retrying
                    logger.error(f"Task {task_id} permanent provider error: {exc}")
                    duration_ms = (time.perf_counter() - start_time) * 1000.0
                    await self._update_task_status(
                        task_id,
                        status=GenerationStatus.FAILED,
                        error_message=f"Provider error: {exc}",
                        duration_ms=duration_ms
                    )
                    return

                except Exception as exc:
                    logger.exception(f"Task {task_id} unexpected error: {exc}")
                    duration_ms = (time.perf_counter() - start_time) * 1000.0
                    await self._update_task_status(
                        task_id,
                        status=GenerationStatus.FAILED,
                        error_message="An unexpected internal error occurred during generation.",
                        duration_ms=duration_ms
                    )
                    return

            if not copy_result or not bg_image:
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                await self._update_task_status(
                    task_id,
                    status=GenerationStatus.FAILED,
                    error_message="Creative generation produced empty output.",
                    duration_ms=duration_ms
                )
                return

            # --- STEP 3: Deterministic Ad Composition ---
            output_filename = f"{task_id}.png"
            output_filepath = str(Path(settings.OUTPUT_DIR) / output_filename)

            self._compositor.compose_ad(
                background=bg_image,
                product_image=product_image,
                product_name=request.product_name,
                creative_copy=copy_result,
                tone=request.tone,
                output_path=output_filepath
            )

            # --- STEP 4: Mark COMPLETED ---
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            await self._update_task_status(
                task_id,
                status=GenerationStatus.COMPLETED,
                error_message=None,
                creative_copy=copy_result,
                ad_image_url=f"/api/download/{task_id}",
                duration_ms=duration_ms
            )
            logger.info(f"Task {task_id} successfully completed in {duration_ms:.1f}ms")

        except asyncio.CancelledError:
            logger.info(f"Task {task_id} cancelled.")
        except Exception as exc:
            logger.exception(f"Unhandled pipeline crash on task {task_id}: {exc}")
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            await self._update_task_status(
                task_id,
                status=GenerationStatus.FAILED,
                error_message="An internal server error occurred while processing the ad.",
                duration_ms=duration_ms
            )


# Global singleton instance
queue_manager = GenerationQueueManager()
