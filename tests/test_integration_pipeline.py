import base64
from io import BytesIO
from urllib.parse import urlparse

import pytest
from PIL import Image

from config import settings
from generator import Background, ImageFormat, Quality
from main import (
    DescribeAssetInput,
    GenerateImageInput,
    ValidateAssetInput,
    describe_asset_tool,
    generate_image,
    validate_asset_tool,
)


class MockImageGenerationResponse:
    def __init__(self, image_bytes: bytes):
        encoded = base64.b64encode(image_bytes).decode("utf-8")
        self.data = [{"b64_json": encoded}]


class AsyncMockResponse:
    def __init__(self, content: str):
        self._content = content

    def __getitem__(self, item):
        if item == "choices":
            return [{"message": {"content": self._content}}]
        raise KeyError(item)


@pytest.mark.asyncio
async def test_generate_describe_validate_pipeline(monkeypatch, tmp_path):
    # Route storage to temporary directory for the pipeline test
    monkeypatch.setattr(settings, "image_dir", str(tmp_path))

    # Prepare a simple image payload to simulate LiteLLM image generation
    image_buffer = BytesIO()
    Image.new("RGB", (32, 32), color="green").save(image_buffer, format="PNG")
    image_bytes = image_buffer.getvalue()

    async def mock_image_generation(**kwargs):
        return MockImageGenerationResponse(image_bytes)

    async def mock_describer_completion(**kwargs):
        return AsyncMockResponse("A compact green square icon with flat shading.")

    validator_calls = []

    async def mock_validator_completion(**kwargs):
        validator_calls.append(kwargs)
        return AsyncMockResponse('{"verdict": "pass", "confidence": 0.9, "reason": "Matches."}')

    monkeypatch.setattr("generator.aimage_generation", mock_image_generation)
    monkeypatch.setattr("describer.acompletion", mock_describer_completion)
    monkeypatch.setattr("validator.acompletion", mock_validator_completion)

    # Generate an image and request validation
    gen_output = await generate_image(
        GenerateImageInput(
            prompt="A minimal green square icon",
            quality=Quality.AUTO,
            background=Background.AUTO,
            dimensions=(128, 128),
            image_format=ImageFormat.PNG,
            validate_output=True,
            validation_focus="Color and shape fidelity",
        )
    )

    assert gen_output.validation is not None
    assert gen_output.validation.verdict == "pass"
    assert gen_output.data["uri"].startswith("file://")
    assert gen_output.metadata["attempts"] == 1
    assert len(gen_output.retry_history) == 1

    # Derive the saved image path from the returned URI
    image_path = urlparse(gen_output.data["uri"]).path

    # Describe the image and request validation of the summary
    describe_output = await describe_asset_tool(
        DescribeAssetInput(
            uri=image_path,
            purpose="UI element catalog",
            auto_validate=True,
            validation_focus="Ensure mention of color",
            structure_detail=True,
        )
    )

    assert "green square" in describe_output.data["summary"].lower()
    assert describe_output.validation is not None
    assert describe_output.validation.verdict == "pass"
    assert describe_output.metadata.get("attempts") == 1

    # Standalone validation tool should also succeed
    validation_tool_output = await validate_asset_tool(
        ValidateAssetInput(
            uri=image_path,
            expected_description="A compact green square icon with flat shading.",
            structure_detail=True,
        )
    )

    assert validation_tool_output.validation.verdict == "pass"
    assert validation_tool_output.data["expected_description"].startswith("A compact")
    assert validation_tool_output.retry_history[0].validation.verdict == "pass"
    assert len(validator_calls) == 3  # generate, describe, standalone
