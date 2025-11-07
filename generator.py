from enum import Enum
import logging
import base64
from typing import Any, Dict

from litellm import aimage_generation
from config import settings

class Quality(str, Enum):
    AUTO = "auto"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class Background(str, Enum):
    AUTO = "auto"
    TRANSPARENT = "transparent"
    OPAQUE = "opaque"

class ImageFormat(str, Enum):
    PNG = "PNG"
    JPEG = "JPEG"
    WEBP = "WEBP"

def build_generation_prompt(
    prompt: str,
    style: str,
    acceptance_criteria: str,
    quality: Quality,
    background: Background,
) -> str:
    """Builds the full prompt for the image generation model."""
    full_prompt = f"{prompt}"
    if style:
        full_prompt += f", in the style of {style}"
    if acceptance_criteria:
        full_prompt += f", meeting the following criteria: {acceptance_criteria}"

    if quality == Quality.HIGH:
        full_prompt += ", 4k, HDR, high quality"
    elif quality == Quality.MEDIUM or quality == Quality.AUTO:
        full_prompt += ", standard quality"
    elif quality == Quality.LOW:
        full_prompt += ", low quality"

    if background == Background.TRANSPARENT:
        full_prompt += ", on a transparent background"
    elif background == Background.OPAQUE:
        full_prompt += ", on a solid color background"

    return full_prompt

async def generate_image(
    prompt: str,
    style: str,
    acceptance_criteria: str,
    quality: Quality = Quality.AUTO,
    background: Background = Background.AUTO,
    dimensions: tuple[int, int] = (1024, 1024),
) -> bytes | None:
    """
    Generates an image using LiteLLM's image generation interface.

    Returns:
        The image data as bytes, or None if an error occurred.
    """
    try:
        width, height = dimensions
        min_dim = settings.image_min_dimension
        max_dim = settings.image_max_dimension
        if not (min_dim <= width <= max_dim and min_dim <= height <= max_dim):
            raise ValueError(
                f"dimensions must be between {min_dim} and {max_dim} pixels; received {dimensions}"
            )

        full_prompt = build_generation_prompt(
            prompt, style, acceptance_criteria, quality, background
        )

        if settings.image_generation_prompt_prefix:
            full_prompt = f"{settings.image_generation_prompt_prefix.strip()}\n\n{full_prompt}".strip()

        size = f"{dimensions[0]}x{dimensions[1]}"

        llm_settings = settings.get_llm_settings("image")

        request_kwargs: Dict[str, Any] = {
            "model": llm_settings.model,
            "prompt": full_prompt,
            "size": size,
        }

        if llm_settings.api_key:
            request_kwargs["api_key"] = llm_settings.api_key
        if llm_settings.api_base:
            request_kwargs["api_base"] = llm_settings.api_base
        if llm_settings.extra_params:
            request_kwargs.update(llm_settings.extra_params)

        response = await aimage_generation(**request_kwargs)
        data = getattr(response, "data", None) or response.get("data")  # type: ignore[attr-defined]
        if not data:
            logging.error("LiteLLM image generation returned no data.")
            return None

        first_image = data[0]
        if isinstance(first_image, dict):
            encoded_image = first_image.get("b64_json")
        else:
            encoded_image = getattr(first_image, "b64_json", None)

        if not encoded_image:
            logging.error("LiteLLM image generation response missing 'b64_json'.")
            return None

        try:
            image_bytes = base64.b64decode(encoded_image)
        except Exception as decode_error:
            logging.error(f"Failed to decode base64 image data: {decode_error}")
            return None

        if not image_bytes:
            logging.error("No images were generated.")
            return None

        return image_bytes
    except ValueError:
        raise
    except Exception as e:
        logging.error(f"An error occurred during image generation: {e}")
        return None
