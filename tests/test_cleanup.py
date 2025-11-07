import asyncio
import os
from datetime import datetime, timedelta, UTC
from pathlib import Path

import pytest

from cleanup import cleanup_old_files
from config import settings


@pytest.mark.asyncio
async def test_cleanup_removes_old_files(monkeypatch, tmp_path):
    image_dir = tmp_path / "images"
    image_dir.mkdir()

    monkeypatch.setattr(settings, "image_dir", str(image_dir), raising=False)
    monkeypatch.setattr(settings, "file_retention_days", 1, raising=False)
    monkeypatch.setattr(settings, "cleanup_run_interval_seconds", 0, raising=False)
    monkeypatch.setattr(settings, "cleanup_check_interval_seconds", 0, raising=False)

    old_file = image_dir / "old.png"
    old_file.write_text("old")
    old_timestamp = (datetime.now(UTC) - timedelta(days=2)).timestamp()
    os.utime(old_file, (old_timestamp, old_timestamp))

    fresh_file = image_dir / "fresh.png"
    fresh_file.write_text("fresh")

    removed = []

    async def fake_to_thread(func, *args, **kwargs):
        result = func(*args, **kwargs)
        removed.append(Path(args[0]))
        return result

    async def fake_sleep(seconds):
        raise asyncio.CancelledError

    monkeypatch.setattr("cleanup.asyncio.to_thread", fake_to_thread)
    monkeypatch.setattr("cleanup.asyncio.sleep", fake_sleep)

    with pytest.raises(asyncio.CancelledError):
        await cleanup_old_files()

    assert not old_file.exists()
    assert fresh_file.exists()
    assert removed == [old_file]
