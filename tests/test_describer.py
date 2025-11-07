import asyncio
from pathlib import Path

import pytest
from PIL import Image
from docx import Document

from config import settings
from describer import describe_asset


class AsyncMockResponse:
    def __init__(self, content: str):
        self._content = content

    def __getitem__(self, item):
        if item == "choices":
            return [{"message": {"content": self._content}}]
        raise KeyError(item)


@pytest.mark.asyncio
async def test_describe_image(monkeypatch, tmp_path):
    image_path = tmp_path / "sample.png"
    image = Image.new("RGB", (64, 64), color="blue")
    image.save(image_path)

    captured_kwargs = {}

    async def mock_acompletion(**kwargs):
        nonlocal captured_kwargs
        captured_kwargs = kwargs
        return AsyncMockResponse("A blue square icon.")

    monkeypatch.setattr("describer.acompletion", mock_acompletion)

    result = await describe_asset(
        str(image_path),
        purpose="UI icon exploration",
        structure_detail=True,
    )

    assert "summary" in result.__dict__
    assert result.summary == "A blue square icon."
    assert result.metadata["type"] == "image"
    assert result.metadata["width"] == 64
    assert captured_kwargs["messages"][1]["content"][1]["image_url"]["url"].startswith("data:image/png;base64,")
    assert settings.asset_structure_guidance_visual.split(" ")[0] in captured_kwargs["messages"][1]["content"][0]["text"]
    assert captured_kwargs["model"] == settings.get_llm_settings("docs").model


@pytest.mark.asyncio
async def test_describe_docx(monkeypatch, tmp_path):
    doc_path = tmp_path / "spec.docx"
    document = Document()
    document.add_paragraph("Login flow overview")
    document.save(doc_path)

    async def mock_acompletion(**kwargs):
        user_message = kwargs["messages"][1]["content"]
        assert "Login flow overview" in user_message
        assert settings.asset_structure_guidance_document.split(" ")[0] in user_message
        assert kwargs["model"] == settings.get_llm_settings("docs").model
        return AsyncMockResponse("Summary for docx")

    monkeypatch.setattr("describer.acompletion", mock_acompletion)

    result = await describe_asset(
        str(doc_path),
        audience="frontend engineer",
        structure_detail=True,
    )

    assert result.summary == "Summary for docx"
    assert result.metadata["type"] == "docx"


@pytest.mark.asyncio
async def test_describe_unsupported_extension(tmp_path):
    unsupported = tmp_path / "archive.zip"
    unsupported.write_bytes(b"PK")

    with pytest.raises(ValueError):
        await describe_asset(str(unsupported))
