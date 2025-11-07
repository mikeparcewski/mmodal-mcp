import base64
from unittest.mock import AsyncMock, MagicMock

import pytest

from generator import generate_image


@pytest.fixture
def mock_litellm_image_generation(mocker):
    """Mocks LiteLLM image generation response."""
    encoded = base64.b64encode(b"test-image-data").decode("utf-8")
    mock_response = MagicMock()
    mock_response.data = [{"b64_json": encoded}]

    async_mock = AsyncMock(return_value=mock_response)
    mocker.patch("generator.aimage_generation", new=async_mock)
    return async_mock


@pytest.mark.asyncio
async def test_generate_image_success(mock_litellm_image_generation):
    """Tests successful image generation."""
    prompt = "a cat"
    image_data = await generate_image(prompt, "", "")

    assert image_data == b"test-image-data"
    mock_litellm_image_generation.assert_called_once()

    call_args = mock_litellm_image_generation.call_args
    assert "a cat, standard quality" in call_args.kwargs["prompt"]
    assert call_args.kwargs["size"] == "1024x1024"
    assert "response_format" not in call_args.kwargs


@pytest.mark.asyncio
async def test_generate_image_with_style_and_criteria(mock_litellm_image_generation):
    """Tests image generation with style and acceptance criteria."""
    prompt = "a robot"
    style = "steampunk"
    criteria = "holding a gear"

    await generate_image(prompt, style, criteria)

    call_args = mock_litellm_image_generation.call_args
    assert "in the style of steampunk" in call_args.kwargs["prompt"]
    assert "meeting the following criteria: holding a gear" in call_args.kwargs["prompt"]


@pytest.mark.asyncio
async def test_generate_image_api_failure(mocker):
    """Tests the case where LiteLLM raises an exception."""
    mocker.patch("generator.aimage_generation", side_effect=Exception("API Error"))

    image_data = await generate_image("a fish", "", "")
    assert image_data is None


@pytest.mark.asyncio
async def test_generate_image_invalid_dimensions():
    """Rejects dimensions outside configured limits."""
    with pytest.raises(ValueError):
        await generate_image("prompt", "", "", dimensions=(10, 10))
