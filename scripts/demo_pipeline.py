import asyncio
import base64
import sys
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import describer
import generator
import validator
from config import settings
from main import (
    DescribeAssetInput,
    GenerateImageInput,
    ValidateAssetInput,
    describe_asset_tool,
    generate_image,
    validate_asset_tool,
)


class MockImageResponse:
    def __init__(self, image_bytes: bytes):
        encoded = base64.b64encode(image_bytes).decode("utf-8")
        self.data = [{"b64_json": encoded}]


class MockLLMResponse:
    def __init__(self, content: str):
        self._content = content

    def __getitem__(self, item):
        if item == "choices":
            return [{"message": {"content": self._content}}]
        raise KeyError(item)


async def run_demo() -> None:
    """Demonstrate generate → describe → validate using mocked LiteLLM calls."""
    original_image_dir = settings.image_dir
    original_image_generation = generator.image_generation
    original_describer_completion = describer.acompletion
    original_validator_completion = validator.acompletion

    with TemporaryDirectory() as tmpdir:
        settings.image_dir = tmpdir

        # Prepare an in-memory sample image to simulate a LiteLLM response.
        image_buffer = BytesIO()
        Image.new("RGB", (64, 64), color="#40C057").save(image_buffer, format="PNG")
        image_bytes = image_buffer.getvalue()

        def mock_image_generation(**kwargs):
            print("mock_image_generation called with:", kwargs["prompt"])
            return MockImageResponse(image_bytes)

        async def mock_describer_completion(**kwargs):
            print("mock_describer_completion invoked")
            return MockLLMResponse(
                "A bright green square icon with flat shading and rounded appearance."
            )

        async def mock_validator_completion(**kwargs):
            print("mock_validator_completion invoked with focus:", kwargs.get("evaluation_focus"))
            return MockLLMResponse(
                '{"verdict": "pass", "confidence": 0.92, "reason": "Image matches expectations."}'
            )

        generator.image_generation = mock_image_generation
        describer.acompletion = mock_describer_completion
        validator.acompletion = mock_validator_completion

        try:
            print("=== Generating image ===")
            gen_output = await generate_image(
                GenerateImageInput(
                    prompt="A simple green square icon for success state",
                    quality=generator.Quality.AUTO,
                    background=generator.Background.AUTO,
                    dimensions=(64, 64),
                    image_format=generator.ImageFormat.PNG,
                    validate_output=True,
                    validation_focus="Ensure color and simplicity are respected",
                )
            )
            print("Generated image URI:", gen_output.uri)
            if gen_output.validation:
                print("Validation verdict:", gen_output.validation.verdict)
                print("Validation reasoning:", gen_output.validation.reasoning)

            image_path = Path(gen_output.uri.replace("file://", "")).resolve()

            print("\n=== Describing asset ===")
            describe_output = await describe_asset_tool(
                DescribeAssetInput(
                    uri=str(image_path),
                    purpose="Product UI success indicators",
                    audience="Frontend developers",
                    structure_detail=True,
                    auto_validate=True,
                    validation_focus="Confirm mention of color and shape",
                )
            )
            print("Description:", describe_output.summary)
            if describe_output.validation:
                print("Description validation:", describe_output.validation.verdict)
                print("Reasoning:", describe_output.validation.reasoning)

            print("\n=== Standalone validation ===")
            validate_output = await validate_asset_tool(
                ValidateAssetInput(
                    uri=str(image_path),
                    expected_description="A bright green square icon with flat shading.",
                    structure_detail=True,
                    evaluation_focus="Color accuracy and flat style",
                )
            )
            print("Standalone validation verdict:", validate_output.validation.verdict)
            print("Standalone validation reasoning:", validate_output.validation.reasoning)

        finally:
            # Restore patched values and clean up.
            settings.image_dir = original_image_dir
            generator.image_generation = original_image_generation
            describer.acompletion = original_describer_completion
            validator.acompletion = original_validator_completion


if __name__ == "__main__":
    asyncio.run(run_demo())
