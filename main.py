import asyncio
import base64
import logging
import tempfile
from pathlib import Path
from typing import Any, Literal, Tuple

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field
from starlette.staticfiles import StaticFiles

from cache import cache
from cleanup import cleanup_old_files
from config import settings
from describer import describe_asset, resolve_asset_path
from generator import (
    Background,
    ImageFormat,
    Quality,
    build_generation_prompt,
    generate_image as gen_image,
)
from storage import get_image_path, get_image_url, save_image
from validator import ValidationResultData, validate_asset
from utils import (
    build_assistant_hint,
    build_final_guidance,
    extract_suggestions,
    normalize_verdict,
)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

mcp = FastMCP("mmodal")
if hasattr(mcp, "mount"):
    mcp.mount("/images", StaticFiles(directory=settings.image_dir), name="images")
else:
    logging.warning("FastMCP static mounting not available; skipping /images mount.")


def _as_validation_output(data: ValidationResultData) -> "ValidationOutput":
    return ValidationOutput(
        verdict=normalize_verdict(data.verdict),
        confidence=data.confidence,
        reasoning=data.reasoning,
    )


async def _start_cleanup_task():
    logging.info("Starting background cleanup task...")
    asyncio.create_task(cleanup_old_files())


if hasattr(mcp, "on_startup"):
    @mcp.on_startup
    async def startup():
        await _start_cleanup_task()
else:
    try:
        app = getattr(mcp, "app")
        app.add_event_handler("startup", _start_cleanup_task)
    except AttributeError:
        logging.warning("Startup event hook unavailable; cleanup task will not auto-run.")


class ValidationOutput(BaseModel):
    verdict: Literal["pass", "fail", "unknown"] = Field(
        ..., description="Validation verdict comparing the asset against expectations."
    )
    confidence: float | None = Field(
        None, description="Optional confidence score returned by the validator (0-1)."
    )
    reasoning: str = Field(
        ..., description="Validator-provided reasoning explaining the verdict."
    )


class RetryRecord(BaseModel):
    attempt: int = Field(..., description="1-based attempt number.")
    prompt: str | None = Field(
        None, description="Prompt or purpose used for this attempt (when applicable)."
    )
    summary: str | None = Field(
        None, description="Generated summary (for description retries)."
    )
    validation: ValidationOutput | None = Field(
        None, description="Validation result for this attempt, if available."
    )
    notes: str | None = Field(
        None, description="Additional notes such as validation feedback."
    )


class ToolResponse(BaseModel):
    data: dict[str, Any] = Field(default_factory=dict, description="Primary payload.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Structured metadata.")
    validation: ValidationOutput | None = Field(
        None, description="Final validation verdict, if available."
    )
    assistant_hint: str = Field("", description="Short hint suitable for surfacing to end users.")
    retry_suggestions: list[str] = Field(
        default_factory=list,
        description="Actionable suggestions derived from the validator to guide retries.",
    )
    retry_history: list[RetryRecord] = Field(
        default_factory=list,
        description="List of attempts (including validation results) performed automatically.",
    )
    final_guidance: str = Field(
        "", description="Summary guidance after completing retries."
    )


class GenerateImageInput(BaseModel):
    """Create a custom image using the configured LiteLLM provider."""

    prompt: str = Field(..., description="Detailed instructions describing the desired image.")
    quality: Quality = Field(Quality.AUTO, description="Rendering quality for the generated asset.")
    background: Background = Field(Background.AUTO, description="Background treatment for the image.")
    dimensions: Tuple[int, int] = Field((1024, 1024), description="Width and height in pixels.")
    image_format: ImageFormat = Field(ImageFormat.PNG, description="Output file format.")
    style: str = Field(
        "",
        description="Optional creative style hints (e.g., 'watercolor', 'isometric render').",
    )
    acceptance_criteria: str = Field(
        "",
        description="Explicit requirements that must appear in the generated image.",
    )
    validation_focus: str = Field(
        "",
        description="Optional instructions for the validator when auto-validating the result.",
    )
    validate_output: bool = Field(
        False,
        description="When true, automatically run validation against the generated asset.",
    )
    max_validation_retries: int = Field(
        0,
        ge=0,
        description="Number of additional attempts to run if validation fails.",
    )


@mcp.tool()
async def generate_image(input: GenerateImageInput) -> ToolResponse:
    """Generate an image, persist it, and optionally validate it against the request."""

    logging.info("Generating image via mmodal-mcp")

    max_retries = input.max_validation_retries if input.validate_output else 0
    max_retries = max(0, max_retries)
    retry_history: list[RetryRecord] = []
    base_prompt = input.prompt
    current_prompt = base_prompt
    final_validation: ValidationOutput | None = None
    final_image_bytes: bytes | None = None
    final_prompt_used = base_prompt
    attempts_run = 0


    for attempt_index in range(max_retries + 1):
        attempts_run = attempt_index + 1
        final_prompt_used = current_prompt

        image_bytes = await gen_image(
            prompt=current_prompt,
            style=input.style,
            acceptance_criteria=input.acceptance_criteria,
            quality=input.quality,
            background=input.background,
            dimensions=input.dimensions,
        )

        if not image_bytes:
            logging.error("Failed to generate image bytes.")
            raise RuntimeError("Failed to generate or save the image.")

        if not input.validate_output:
            final_image_bytes = image_bytes
            break

        with tempfile.NamedTemporaryFile(
            suffix=f".{input.image_format.value.lower()}", delete=False
        ) as tmp_file:
            tmp_file.write(image_bytes)
            temp_path = Path(tmp_file.name)

        expected = build_generation_prompt(
            prompt=current_prompt,
            style=input.style,
            acceptance_criteria=input.acceptance_criteria,
            quality=input.quality,
            background=input.background,
        )
        if settings.image_generation_prompt_prefix:
            expected = f"{settings.image_generation_prompt_prefix.strip()}\n\n{expected}".strip()

        try:
            validation_data = await validate_asset(
                uri=str(temp_path),
                expected_description=expected,
                evaluation_focus=input.validation_focus,
                structure_detail=True,
            )
        finally:
            temp_path.unlink(missing_ok=True)

        validation_output = _as_validation_output(validation_data)
        retry_history.append(
            RetryRecord(
                attempt=attempts_run,
                prompt=current_prompt,
                validation=validation_output,
                notes=validation_output.reasoning,
            )
        )

        if validation_output.verdict == "pass":
            final_validation = validation_output
            final_image_bytes = image_bytes
            break

        final_validation = validation_output

        if attempt_index < max_retries:
            feedback = validation_output.reasoning.strip()
            if feedback:
                current_prompt = (
                    f"{base_prompt}\n\nRetry guidance (attempt {attempts_run + 1}):\n{feedback}"
                )
            else:
                current_prompt = base_prompt
            continue

        # Exhausted retries, use the last attempt result
        final_image_bytes = image_bytes
        break

    if final_image_bytes is None:
        logging.error("Failed to generate or save the image.")
        raise RuntimeError("Failed to generate or save the image.")

    image_id = await save_image(
        image_data=final_image_bytes,
        prompt=final_prompt_used,
        quality=input.quality,
        background=input.background,
        dimensions=input.dimensions,
        image_format=input.image_format,
    )
    if not image_id:
        logging.error("Failed to store generated image.")
        raise RuntimeError("Failed to store generated image.")

    cache.set_base64(image_id, final_image_bytes)
    transport = "stdio"
    mcp_context = getattr(mcp, "context", None)
    if mcp_context is not None and getattr(mcp_context, "transport", None):
        transport = mcp_context.transport
    uri = get_image_url(image_id, transport, input.image_format)
    image_path = get_image_path(image_id, input.image_format)

    base64_data = base64.b64encode(final_image_bytes).decode("utf-8")

    retry_suggestions = (
        extract_suggestions(final_validation.reasoning)
        if final_validation and final_validation.verdict == "fail"
        else []
    )

    assistant_hint = build_assistant_hint(
        final_validation,
        "Image generated successfully." if input.validate_output else "Image generated; validation skipped.",
    )

    final_guidance = build_final_guidance(
        final_validation,
        "Image generation complete." if input.validate_output else "Image generation complete (no validation).",
    )

    if not input.validate_output and not retry_history:
        retry_history = [
            RetryRecord(
                attempt=1,
                prompt=base_prompt,
                validation=None,
            )
        ]

    metadata = {
        "id": image_id,
        "path": str(image_path),
        "format": input.image_format.value,
        "dimensions": list(input.dimensions),
        "attempts": attempts_run,
    }

    return ToolResponse(
        data={"uri": uri, "base64_data": base64_data},
        metadata=metadata,
        validation=final_validation,
        assistant_hint=assistant_hint,
        retry_suggestions=retry_suggestions,
        retry_history=retry_history,
        final_guidance=final_guidance,
    )


class DescribeAssetInput(BaseModel):
    """Analyze an existing asset and summarize it for coding assistants."""

    uri: str = Field(
        ..., description="Path to the asset to describe. Relative paths resolve from IMAGE_DIR."
    )
    purpose: str = Field(
        "",
        description="Optional context describing why the assistant needs this asset described.",
    )
    audience: str = Field(
        "",
        description="Intended audience for the description (e.g., 'frontend engineer', 'QA analyst').",
    )
    structure_detail: bool = Field(
        False,
        description="Request structure analysis (composition for images, layout for documents).",
    )
    validation_focus: str = Field(
        "",
        description="Optional guidance for validation when auto-validating the summary.",
    )
    auto_validate: bool = Field(
        False,
        description="When true, run validation to ensure the summary matches the asset.",
    )
    max_validation_retries: int = Field(
        0,
        ge=0,
        description="Number of additional description attempts if validation fails.",
    )


@mcp.tool()
async def describe_asset_tool(input: DescribeAssetInput) -> ToolResponse:
    """Describe an existing asset and optionally validate that description."""

    max_retries = input.max_validation_retries if input.auto_validate else 0
    max_retries = max(0, max_retries)
    base_purpose = input.purpose
    current_purpose = base_purpose
    retry_history: list[RetryRecord] = []

    final_summary = ""
    final_metadata: dict[str, Any] = {}
    final_validation: ValidationOutput | None = None
    attempts_run = 0

    for attempt_index in range(max_retries + 1):
        attempts_run = attempt_index + 1
        result = await describe_asset(
            uri=input.uri,
            purpose=current_purpose,
            audience=input.audience,
            structure_detail=input.structure_detail,
        )
        final_summary = result.summary
        final_metadata = result.metadata

        if not input.auto_validate:
            break

        validation_data = await validate_asset(
            uri=input.uri,
            expected_description=result.summary,
            evaluation_focus=input.validation_focus,
            structure_detail=True,
        )
        validation_output = _as_validation_output(validation_data)
        retry_history.append(
            RetryRecord(
                attempt=attempts_run,
                prompt=current_purpose or None,
                summary=result.summary,
                validation=validation_output,
                notes=validation_output.reasoning,
            )
        )

        if validation_output.verdict == "pass":
            final_validation = validation_output
            break

        final_validation = validation_output

        if attempt_index < max_retries:
            feedback = validation_output.reasoning.strip()
            if feedback:
                prefix = f"{base_purpose}\n\n" if base_purpose else ""
                current_purpose = f"{prefix}Retry guidance (attempt {attempts_run + 1}):\n{feedback}"
            else:
                current_purpose = base_purpose
            continue

        break

    if not input.auto_validate and not retry_history:
        retry_history.append(
            RetryRecord(
                attempt=1,
                prompt=current_purpose or None,
                summary=final_summary,
            )
        )

    retry_suggestions = (
        extract_suggestions(final_validation.reasoning)
        if final_validation and final_validation.verdict == "fail"
        else []
    )

    assistant_hint = build_assistant_hint(
        final_validation,
        "Asset described successfully." if input.auto_validate else "Asset described; validation skipped.",
    )

    final_guidance = build_final_guidance(
        final_validation,
        "Description complete." if input.auto_validate else "Description complete (no validation).",
    )

    metadata = {**final_metadata, "attempts": attempts_run}

    return ToolResponse(
        data={"summary": final_summary},
        metadata=metadata,
        validation=final_validation,
        assistant_hint=assistant_hint,
        retry_suggestions=retry_suggestions,
        retry_history=retry_history,
        final_guidance=final_guidance,
    )


class ValidateAssetInput(BaseModel):
    """Validate whether an asset aligns with the provided description or criteria."""

    uri: str = Field(..., description="Path or URI of the asset to validate.")
    expected_description: str = Field(
        ..., description="Description, acceptance criteria, or summary to validate."
    )
    evaluation_focus: str = Field(
        "",
        description="Optional instruction to steer validator attention (e.g., 'color accuracy').",
    )
    structure_detail: bool = Field(
        False,
        description="Include structure/composition checks during validation.",
    )


@mcp.tool()
async def validate_asset_tool(input: ValidateAssetInput) -> ToolResponse:
    """Validate whether an asset matches the provided description or requirements."""

    resolved_path = resolve_asset_path(input.uri)
    validation_data = await validate_asset(
        uri=str(resolved_path),
        expected_description=input.expected_description,
        evaluation_focus=input.evaluation_focus,
        structure_detail=input.structure_detail,
    )

    validation_output = _as_validation_output(validation_data)
    retry_suggestions = (
        extract_suggestions(validation_output.reasoning)
        if validation_output.verdict == "fail"
        else []
    )

    assistant_hint = build_assistant_hint(
        validation_output,
        "Asset matches the provided description.",
    )

    final_guidance = build_final_guidance(
        validation_output,
        "Validation passed.",
    )

    retry_history = [
        RetryRecord(
            attempt=1,
            validation=validation_output,
            notes=validation_output.reasoning,
        )
    ]

    return ToolResponse(
        data={"expected_description": input.expected_description},
        metadata={"asset_path": str(resolved_path)},
        validation=validation_output,
        assistant_hint=assistant_hint,
        retry_suggestions=retry_suggestions,
        retry_history=retry_history,
        final_guidance=final_guidance,
    )


def _run_mcp(args: list[str]):
    """Helper to run MCP with specific arguments."""
    import sys
    from mcp.__main__ import main as mcp_main
    sys.argv = args
    mcp_main()


def run_stdio():
    """Entry point for stdio transport."""
    _run_mcp(["mcp", "run", "main.py:mcp", "--transport", "stdio"])


def run_sse():
    """Entry point for SSE transport."""
    _run_mcp(["mcp", "run", "main.py:mcp", "--transport", "sse"])


def run_dev():
    """Entry point for dev mode."""
    _run_mcp(["mcp", "dev", "main.py:mcp"])


if __name__ == "__main__":
    mcp.run()
