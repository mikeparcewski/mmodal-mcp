import uuid
import json
import os
import aiofiles
import logging
from pathlib import Path
from datetime import datetime, UTC
from typing import Any
from PIL import Image
from io import BytesIO

from config import settings
from generator import Quality, Background, ImageFormat

async def save_image(
    image_data: bytes,
    prompt: str,
    quality: Quality,
    background: Background,
    dimensions: tuple[int, int],
    image_format: ImageFormat,
) -> str | None:
    """
    Saves the image data and metadata to the local filesystem.

    Returns:
        The unique ID of the saved image, or None if an error occurred.
    """
    try:
        image_dir = Path(settings.image_dir)
        image_dir.mkdir(exist_ok=True)

        image_id = str(uuid.uuid4())
        file_extension = image_format.value.lower()
        image_filename = f"{image_id}.{file_extension}"
        metadata_filename = f"{image_id}.json"

        image_path = image_dir / image_filename
        metadata_path = image_dir / metadata_filename

        # Convert the image to the desired format
        with Image.open(BytesIO(image_data)) as img:
            # Save the image in the desired format
            img.save(image_path, format=image_format.value)

        metadata = {
            "id": image_id,
            "prompt": prompt,
            "quality": quality.value,
            "background": background.value,
            "dimensions": dimensions,
            "format": image_format.value,
            "timestamp": datetime.now(UTC).isoformat(),
            "path": str(image_path),
        }

        async with aiofiles.open(metadata_path, "w") as f:
            await f.write(json.dumps(metadata, indent=4))

        return image_id
    except Exception as e:
        logging.error(f"Error saving image: {e}")
        return None

def get_image_url(image_id: str, transport: str, image_format: ImageFormat) -> str:
    """
    Generates a transport-aware URL for the image.
    """
    file_extension = image_format.value.lower()
    if transport in ("http", "sse"):
        return f"/images/{image_id}.{file_extension}"
    elif transport == "stdio":
        return f"file://{Path(settings.image_dir).resolve()}/{image_id}.{file_extension}"
    else:
        return ""

def get_image_path(image_id: str, image_format: ImageFormat) -> Path:
    """Returns the path to the image file."""
    file_extension = image_format.value.lower()
    return Path(settings.image_dir) / f"{image_id}.{file_extension}"

def get_metadata_path(image_id: str) -> Path:
    """Returns the path to the metadata file."""
    return Path(settings.image_dir) / f"{image_id}.json"
