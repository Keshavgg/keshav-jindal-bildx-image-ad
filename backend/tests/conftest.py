import io
import pytest
from PIL import Image
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.services.queue_manager import queue_manager
from app.providers.fake_provider import FakeAIProvider


def generate_test_image_bytes() -> bytes:
    """Creates valid test PNG image in memory."""
    img = Image.new("RGBA", (400, 400), (220, 100, 80, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture(autouse=True)
async def reset_queue_state():
    """Resets queue manager and sets FakeAIProvider before every test."""
    await queue_manager.reset_state()
    fake = FakeAIProvider(simulated_delay_seconds=0.01)
    queue_manager.set_provider(fake)
    yield
    await queue_manager.reset_state()


@pytest.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
