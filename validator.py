import asyncio
import json
from dataclasses import dataclass
from typing import Any, Dict, Optional

from litellm import acompletion

from config import settings
from describer import extract_asset_payload, resolve_asset_path


@dataclass
class ValidationResultData:
    verdict: str
    confidence: Optional[float]
    reasoning: str


async def validate_asset(
    uri: str,
    expected_description: str,
    evaluation_focus: str = "",
    structure_detail: bool = False,
) -> ValidationResultData:
    path = resolve_asset_path(uri)
    metadata, payload = await asyncio.to_thread(extract_asset_payload, path)

    user_sections = [
        settings.asset_validation_prompt_template.strip(),
        f"Expected Description:\n{expected_description.strip()}",
        f"Metadata: {json.dumps(metadata, indent=2)}",
    ]

    if evaluation_focus:
        user_sections.append(f"Evaluation Focus: {evaluation_focus.strip()}")

    snippet = payload.get("text_snippet")
    image_data_url = payload.get("image_data_url")

    if snippet:
        user_sections.append("Asset Content Preview:\n" + snippet)

    if structure_detail:
        asset_type = metadata.get("type", "")
        if asset_type == "image":
            user_sections.append(settings.asset_structure_guidance_visual.strip())
        else:
            user_sections.append(settings.asset_structure_guidance_document.strip())

    messages: list[Dict[str, Any]] = [
        {"role": "system", "content": settings.asset_validation_system_prompt.strip()},
    ]

    if image_data_url:
        messages.append(
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "\n\n".join(user_sections)},
                    {"type": "image_url", "image_url": {"url": image_data_url}},
                ],
            }
        )
    else:
        messages.append(
            {"role": "user", "content": "\n\n".join(user_sections)}
        )

    llm_settings = settings.get_llm_settings("text")
    request_kwargs: Dict[str, Any] = {
        "model": llm_settings.model,
        "messages": messages,
    }

    if llm_settings.api_key:
        request_kwargs["api_key"] = llm_settings.api_key
    if llm_settings.api_base:
        request_kwargs["api_base"] = llm_settings.api_base
    if llm_settings.extra_params:
        request_kwargs.update(llm_settings.extra_params)

    response = await acompletion(**request_kwargs)
    content = response["choices"][0]["message"]["content"]

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        # Attempt to extract JSON substring
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and start < end:
            parsed = json.loads(content[start : end + 1])
        else:
            parsed = {
                "verdict": "unknown",
                "confidence": None,
                "reason": content,
            }

    verdict = str(parsed.get("verdict", "unknown")).lower()
    confidence = parsed.get("confidence")
    reasoning = parsed.get("reason") or parsed.get("reasoning") or content

    return ValidationResultData(verdict=verdict, confidence=confidence, reasoning=reasoning)
