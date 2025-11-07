import asyncio
import os
from pathlib import Path
from datetime import datetime, timedelta, UTC
import logging

from config import settings

async def cleanup_old_files():
    """Periodically cleans up old images and metadata files."""
    while True:
        try:
            image_dir = Path(settings.image_dir)
            if not image_dir.exists():
                await asyncio.sleep(settings.cleanup_check_interval_seconds)
                continue

            retention_delta = timedelta(days=settings.file_retention_days)
            now = datetime.now(UTC)

            for file_path in image_dir.glob("*"):
                try:
                    file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime, UTC)
                    if now - file_mtime > retention_delta:
                        await asyncio.to_thread(os.remove, file_path)
                        logging.info(f"Deleted old file: {file_path}")
                except Exception as e:
                    logging.error(f"Error deleting file {file_path}: {e}")

        except Exception as e:
            logging.error(f"An error occurred in the cleanup task: {e}")

        await asyncio.sleep(settings.cleanup_run_interval_seconds)
