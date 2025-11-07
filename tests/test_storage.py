import pytest
import json
from pathlib import Path
from PIL import Image
from io import BytesIO

from storage import save_image, get_image_url
from generator import Quality, Background, ImageFormat

@pytest.fixture
def temp_image_dir(tmp_path):
    """Creates a temporary directory for images."""
    return tmp_path

@pytest.fixture
def test_image_data():
    """Creates a valid in-memory image for testing."""
    img = Image.new('RGB', (100, 100), color = 'red')
    buf = BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()

@pytest.mark.asyncio
async def test_save_image(temp_image_dir, monkeypatch, test_image_data):
    """Tests saving an image and its metadata."""
    monkeypatch.setattr("config.settings.image_dir", str(temp_image_dir))

    prompt = "a test image"
    quality = Quality.HIGH
    background = Background.TRANSPARENT
    dimensions = (512, 512)
    image_format = ImageFormat.PNG

    image_id = await save_image(
        test_image_data, prompt, quality, background, dimensions, image_format
    )

    assert image_id is not None

    image_path = temp_image_dir / f"{image_id}.png"
    metadata_path = temp_image_dir / f"{image_id}.json"

    assert image_path.exists()
    assert metadata_path.exists()

    with open(metadata_path, "r") as f:
        metadata = json.load(f)
        assert metadata["id"] == image_id
        assert metadata["prompt"] == prompt

def test_get_image_url():
    """Tests generating transport-aware URLs."""
    image_id = "test-id"

    http_url = get_image_url(image_id, "http", ImageFormat.PNG)
    assert http_url == "/images/test-id.png"

    stdio_url = get_image_url(image_id, "stdio", ImageFormat.JPEG)
    assert stdio_url.startswith("file://")
    assert stdio_url.endswith("/images/test-id.jpeg")
