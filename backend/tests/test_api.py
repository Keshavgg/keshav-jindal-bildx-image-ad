import asyncio
import io
import pytest
from PIL import Image
from unittest.mock import patch, MagicMock
from app.config import settings
from app.models.schemas import CreativeCopy, GenerationStatus
from app.providers.fake_provider import FakeAIProvider
from app.services.image_downloader import ImageSecurityError, ImageSizeError, InvalidImageError
from tests.conftest import generate_test_image_bytes

VALID_PAYLOAD = {
    "image_url": "https://bildx.ai/samples/assets/roam-front.webp",
    "product_name": "ROAM Lock 750",
    "product_description": "A 750 ml insulated steel tumbler with a locking sip lid.",
    "target_audience": "Commuters, gym users and day hikers",
    "key_benefits": ["Up to 12 hours cold", "Carry loop", "Locking lid"],
    "tone": "Adventurous and practical"
}


# ==============================================================================
# 1. Valid generation request flow
# ==============================================================================
@pytest.mark.asyncio
async def test_valid_generation_request(async_client):
    """Scenario 1: Valid request accepted and completes successfully."""
    test_img = Image.open(io.BytesIO(generate_test_image_bytes()))

    with patch("app.services.queue_manager.download_and_validate_image", return_value=test_img):
        res = await async_client.post("/api/generate", json=VALID_PAYLOAD)
        assert res.status_code == 202
        data = res.json()
        task_id = data["task_id"]
        assert data["status"] in (GenerationStatus.PENDING, GenerationStatus.PROCESSING)

        # Poll for completion
        for _ in range(50):
            await asyncio.sleep(0.05)
            status_res = await async_client.get(f"/api/status/{task_id}")
            sdata = status_res.json()
            if sdata["status"] == GenerationStatus.COMPLETED:
                break

        assert sdata["status"] == GenerationStatus.COMPLETED
        assert sdata["creative_copy"] is not None
        assert len(sdata["creative_copy"]["headline"].split()) <= 8
        assert len(sdata["creative_copy"]["supporting_text"].split()) <= 20
        assert len(sdata["creative_copy"]["cta"].split()) <= 4
        assert sdata["ad_image_url"] == f"/api/download/{task_id}"


# ==============================================================================
# 2. Invalid or unreachable image URL
# ==============================================================================
@pytest.mark.asyncio
async def test_invalid_or_unreachable_image_url(async_client):
    """Scenario 2: Unreachable image URL fails fast without retrying."""
    with patch(
        "app.services.queue_manager.download_and_validate_image",
        side_effect=InvalidImageError("Failed to resolve host 'non-existent-host.invalid'")
    ):
        res = await async_client.post("/api/generate", json=VALID_PAYLOAD)
        assert res.status_code == 202
        task_id = res.json()["task_id"]

        for _ in range(30):
            await asyncio.sleep(0.05)
            status_res = await async_client.get(f"/api/status/{task_id}")
            sdata = status_res.json()
            if sdata["status"] == GenerationStatus.FAILED:
                break

        assert sdata["status"] == GenerationStatus.FAILED
        assert "Failed to resolve host" in sdata["error_message"]
        # Permanent validation error must not trigger provider retries
        assert sdata["retry_count"] == 0


# ==============================================================================
# 3. SSRF Protection (Private & Link-Local IPs blocked)
# ==============================================================================
@pytest.mark.asyncio
async def test_ssrf_internal_ip_blocked(async_client):
    """Scenario 3: SSRF attempt to 127.0.0.1 or cloud metadata is blocked immediately."""
    payload = dict(VALID_PAYLOAD)
    payload["image_url"] = "http://127.0.0.1:8000/secret.png"

    res = await async_client.post("/api/generate", json=payload)
    assert res.status_code == 202
    task_id = res.json()["task_id"]

    for _ in range(30):
        await asyncio.sleep(0.05)
        status_res = await async_client.get(f"/api/status/{task_id}")
        sdata = status_res.json()
        if sdata["status"] == GenerationStatus.FAILED:
            break

    assert sdata["status"] == GenerationStatus.FAILED
    assert "prohibited" in sdata["error_message"].lower() or "restricted" in sdata["error_message"].lower()


# ==============================================================================
# 4. Non-image URL or Oversized response (>10MB)
# ==============================================================================
@pytest.mark.asyncio
async def test_oversized_image_rejected(async_client):
    """Scenario 4a: Image exceeding 10MB size limit is rejected."""
    with patch(
        "app.services.queue_manager.download_and_validate_image",
        side_effect=ImageSizeError("Image download exceeded maximum size limit of 10485760 bytes (10MB)")
    ):
        res = await async_client.post("/api/generate", json=VALID_PAYLOAD)
        task_id = res.json()["task_id"]

        for _ in range(30):
            await asyncio.sleep(0.05)
            status_res = await async_client.get(f"/api/status/{task_id}")
            sdata = status_res.json()
            if sdata["status"] == GenerationStatus.FAILED:
                break

        assert sdata["status"] == GenerationStatus.FAILED
        assert "10MB" in sdata["error_message"]


@pytest.mark.asyncio
async def test_non_image_url_rejected(async_client):
    """Scenario 4b: HTML/JSON non-image content is rejected."""
    with patch(
        "app.services.queue_manager.download_and_validate_image",
        side_effect=InvalidImageError("Remote URL returned non-image Content-Type 'text/html'")
    ):
        res = await async_client.post("/api/generate", json=VALID_PAYLOAD)
        task_id = res.json()["task_id"]

        for _ in range(30):
            await asyncio.sleep(0.05)
            status_res = await async_client.get(f"/api/status/{task_id}")
            sdata = status_res.json()
            if sdata["status"] == GenerationStatus.FAILED:
                break

        assert sdata["status"] == GenerationStatus.FAILED
        assert "non-image" in sdata["error_message"].lower()


# ==============================================================================
# 5. Successful completion and download
# ==============================================================================
@pytest.mark.asyncio
async def test_successful_download(async_client):
    """Scenario 5: Completed ad can be downloaded via GET /api/download/{task_id}."""
    test_img = Image.open(io.BytesIO(generate_test_image_bytes()))

    with patch("app.services.queue_manager.download_and_validate_image", return_value=test_img):
        res = await async_client.post("/api/generate", json=VALID_PAYLOAD)
        task_id = res.json()["task_id"]

        for _ in range(50):
            await asyncio.sleep(0.05)
            status_res = await async_client.get(f"/api/status/{task_id}")
            if status_res.json()["status"] == GenerationStatus.COMPLETED:
                break

        # Download image
        down_res = await async_client.get(f"/api/download/{task_id}")
        assert down_res.status_code == 200
        assert down_res.headers["content-type"] == "image/png"
        assert down_res.content.startswith(b"\x89PNG\r\n\x1a\n")  # Valid PNG magic number


# ==============================================================================
# 6. Provider timeout handling
# ==============================================================================
@pytest.mark.asyncio
async def test_provider_timeout_handling(async_client):
    """Scenario 6: Provider call timeout is handled cleanly and marked failed."""
    from app.services.queue_manager import queue_manager
    fake = FakeAIProvider(simulated_delay_seconds=0.01, failure_mode="timeout")
    queue_manager.set_provider(fake)

    test_img = Image.open(io.BytesIO(generate_test_image_bytes()))

    with patch("app.services.queue_manager.download_and_validate_image", return_value=test_img), \
         patch.object(settings, "PROVIDER_TIMEOUT_SECONDS", 0.05), \
         patch.object(settings, "MAX_RETRIES", 1), \
         patch.object(settings, "RETRY_INITIAL_DELAY_SECONDS", 0.01):

        res = await async_client.post("/api/generate", json=VALID_PAYLOAD)
        task_id = res.json()["task_id"]

        for _ in range(40):
            await asyncio.sleep(0.05)
            status_res = await async_client.get(f"/api/status/{task_id}")
            sdata = status_res.json()
            if sdata["status"] == GenerationStatus.FAILED:
                break

        assert sdata["status"] == GenerationStatus.FAILED
        assert "retries" in sdata["error_message"].lower() or "timeout" in sdata["error_message"].lower()


# ==============================================================================
# 7. Temporary error & exponential retry
# ==============================================================================
@pytest.mark.asyncio
async def test_temporary_error_retry_success(async_client):
    """Scenario 7: Transient 503 error is retried and subsequently succeeds."""
    from app.services.queue_manager import queue_manager
    # Fails 1 time with TemporaryProviderError, succeeds on attempt 2
    fake = FakeAIProvider(simulated_delay_seconds=0.01, failure_mode="temporary", fail_times=1)
    queue_manager.set_provider(fake)

    test_img = Image.open(io.BytesIO(generate_test_image_bytes()))

    with patch("app.services.queue_manager.download_and_validate_image", return_value=test_img), \
         patch.object(settings, "RETRY_INITIAL_DELAY_SECONDS", 0.02):

        res = await async_client.post("/api/generate", json=VALID_PAYLOAD)
        task_id = res.json()["task_id"]

        saw_retrying = False
        for _ in range(50):
            await asyncio.sleep(0.04)
            status_res = await async_client.get(f"/api/status/{task_id}")
            sdata = status_res.json()
            if sdata["status"] == GenerationStatus.RETRYING:
                saw_retrying = True
            elif sdata["status"] == GenerationStatus.COMPLETED:
                break

        assert saw_retrying is True
        assert sdata["status"] == GenerationStatus.COMPLETED
        assert sdata["retry_count"] == 1


# ==============================================================================
# 8. Permanent provider error (fail-fast)
# ==============================================================================
@pytest.mark.asyncio
async def test_permanent_provider_error_fail_fast(async_client):
    """Scenario 8: Permanent provider error (e.g. invalid credentials) fails immediately."""
    from app.services.queue_manager import queue_manager
    fake = FakeAIProvider(simulated_delay_seconds=0.01, failure_mode="permanent")
    queue_manager.set_provider(fake)

    test_img = Image.open(io.BytesIO(generate_test_image_bytes()))

    with patch("app.services.queue_manager.download_and_validate_image", return_value=test_img):
        res = await async_client.post("/api/generate", json=VALID_PAYLOAD)
        task_id = res.json()["task_id"]

        for _ in range(30):
            await asyncio.sleep(0.04)
            status_res = await async_client.get(f"/api/status/{task_id}")
            sdata = status_res.json()
            if sdata["status"] == GenerationStatus.FAILED:
                break

        assert sdata["status"] == GenerationStatus.FAILED
        assert "permanent" in sdata["error_message"].lower()
        # Must fail-fast on attempt 0 without retries
        assert sdata["retry_count"] == 0


# ==============================================================================
# 9. Duplicate idempotency key protection
# ==============================================================================
@pytest.mark.asyncio
async def test_duplicate_idempotency_key(async_client):
    """Scenario 9: Identical idempotency key returns existing task ID without duplicating work."""
    test_img = Image.open(io.BytesIO(generate_test_image_bytes()))

    with patch("app.services.queue_manager.download_and_validate_image", return_value=test_img):
        headers = {"Idempotency-Key": "test-unique-key-12345"}
        res1 = await async_client.post("/api/generate", json=VALID_PAYLOAD, headers=headers)
        res2 = await async_client.post("/api/generate", json=VALID_PAYLOAD, headers=headers)

        assert res1.status_code == 202
        assert res2.status_code == 202

        task_id_1 = res1.json()["task_id"]
        task_id_2 = res2.json()["task_id"]

        assert task_id_1 == task_id_2


# ==============================================================================
# 10. Concurrent requests & bounded semaphore
# ==============================================================================
@pytest.mark.asyncio
async def test_concurrent_requests_bounded_concurrency(async_client):
    """Scenario 10: Multiple concurrent requests execute without blocking and complete with isolated IDs."""
    test_img = Image.open(io.BytesIO(generate_test_image_bytes()))

    with patch("app.services.queue_manager.download_and_validate_image", return_value=test_img):
        # Fire 6 concurrent requests
        tasks = [
            async_client.post(
                "/api/generate",
                json={**VALID_PAYLOAD, "product_name": f"Product-{i}"}
            )
            for i in range(6)
        ]
        responses = await asyncio.gather(*tasks)

        assert all(r.status_code == 202 for r in responses)
        task_ids = [r.json()["task_id"] for r in responses]
        assert len(set(task_ids)) == 6  # All IDs are unique

        # Poll all until completed
        for _ in range(60):
            await asyncio.sleep(0.05)
            statuses = await asyncio.gather(*[async_client.get(f"/api/status/{tid}") for tid in task_ids])
            if all(s.json()["status"] == GenerationStatus.COMPLETED for s in statuses):
                break

        final_statuses = [s.json()["status"] for s in statuses]
        assert all(st == GenerationStatus.COMPLETED for st in final_statuses)


# ==============================================================================
# 11. Capacity behavior (HTTP 429 when queue full)
# ==============================================================================
@pytest.mark.asyncio
async def test_capacity_exceeded_returns_429(async_client):
    """Scenario 11: When active queue exceeds MAX_QUEUE_CAPACITY, server returns HTTP 429."""
    from app.services.queue_manager import queue_manager
    # Create a slow provider to keep active tasks in-flight
    slow_fake = FakeAIProvider(simulated_delay_seconds=1.5)
    queue_manager.set_provider(slow_fake)

    test_img = Image.open(io.BytesIO(generate_test_image_bytes()))

    with patch("app.services.queue_manager.download_and_validate_image", return_value=test_img), \
         patch.object(settings, "MAX_QUEUE_CAPACITY", 2):

        # Fill capacity (2 tasks)
        r1 = await async_client.post("/api/generate", json=VALID_PAYLOAD)
        r2 = await async_client.post("/api/generate", json=VALID_PAYLOAD)
        assert r1.status_code == 202
        assert r2.status_code == 202

        # 3rd task exceeds capacity
        r3 = await async_client.post("/api/generate", json=VALID_PAYLOAD)
        assert r3.status_code == 429
        assert "capacity" in r3.json()["detail"].lower()


# ==============================================================================
# 12. Grounded creative-copy word limits validation
# ==============================================================================
def test_creative_copy_word_count_limits():
    """Scenario 12: CreativeCopy schema strictly enforces <=8, <=20, <=4 word counts."""
    # Valid instance
    copy = CreativeCopy(
        headline="Lock it. Loop it. Go.",
        supporting_text="Cold drinks for commutes, workouts and days outside.",
        cta="Explore ROAM",
        visual_direction="Premium outdoor landscape"
    )
    assert len(copy.headline.split()) <= 8
    assert len(copy.supporting_text.split()) <= 20
    assert len(copy.cta.split()) <= 4

    # Invalid headline (> 8 words)
    with pytest.raises(ValueError, match="Headline must not exceed 8 words"):
        CreativeCopy(
            headline="This is an excessively long headline that exceeds eight words limit",
            supporting_text="Valid supporting text.",
            cta="Shop Now",
            visual_direction="Studio"
        )

    # Invalid supporting text (> 20 words)
    with pytest.raises(ValueError, match="Supporting text must not exceed 20 words"):
        CreativeCopy(
            headline="Great Bottle",
            supporting_text=" ".join(["word"] * 21),
            cta="Shop Now",
            visual_direction="Studio"
        )

    # Invalid CTA (> 4 words)
    with pytest.raises(ValueError, match="CTA must not exceed 4 words"):
        CreativeCopy(
            headline="Great Bottle",
            supporting_text="Valid supporting text.",
            cta="Buy It Right Now Today",  # 5 words
            visual_direction="Studio"
        )
