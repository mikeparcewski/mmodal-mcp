from dataclasses import dataclass
from typing import Any, Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


@dataclass
class LiteLLMSettings:
    """Resolved LiteLLM configuration for a specific domain (image/docs/text)."""

    model: str
    api_key: str | None
    api_base: str | None
    extra_params: dict[str, Any]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Global defaults --------------------------------------------------------
    litellm_default_model: str = Field(
        default="gemini/gemini-1.5-flash",
        description="Fallback LiteLLM model identifier used when a domain-specific model is not set.",
    )
    litellm_default_api_key: str | None = Field(
        default=None,
        description="Fallback API key passed to LiteLLM when domain-specific keys are not set.",
    )
    litellm_default_api_base: str | None = Field(
        default=None,
        description="Optional default custom API base URL for LiteLLM providers.",
    )
    litellm_default_extra_params: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional parameters forwarded to LiteLLM calls when no domain-specific parameters are provided.",
    )

    # Image generation overrides ---------------------------------------------
    litellm_image_model: str | None = Field(
        default=None,
        description="LiteLLM model used for image generation. Falls back to litellm_default_model.",
    )
    litellm_image_api_key: str | None = Field(
        default=None,
        description="API key applied to image generation calls. Falls back to litellm_default_api_key.",
    )
    litellm_image_api_base: str | None = Field(
        default=None,
        description="Custom API base for image generation calls.",
    )
    litellm_image_extra_params: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional kwargs forwarded to LiteLLM image generation calls.",
    )

    # Document/asset description overrides -----------------------------------
    litellm_docs_model: str | None = Field(
        default=None,
        description="LiteLLM model used when describing documents or visual assets.",
    )
    litellm_docs_api_key: str | None = Field(
        default=None,
        description="API key used for document/asset description calls.",
    )
    litellm_docs_api_base: str | None = Field(
        default=None,
        description="Custom API base for document/asset description calls.",
    )
    litellm_docs_extra_params: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional kwargs forwarded to document/asset description calls.",
    )

    # General text / validation overrides ------------------------------------
    litellm_text_model: str | None = Field(
        default=None,
        description="LiteLLM model used for general text tasks (e.g., validation).",
    )
    litellm_text_api_key: str | None = Field(
        default=None,
        description="API key used for general text tasks.",
    )
    litellm_text_api_base: str | None = Field(
        default=None,
        description="Custom API base for general text tasks.",
    )
    litellm_text_extra_params: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional kwargs forwarded to general text tasks.",
    )

    # Prompt customization ----------------------------------------------------
    image_generation_prompt_prefix: str = Field(
        default="Create an image that follows the user's instructions with attention to visual detail.",
        description="Prefix added to generated prompts before calling the image model.",
    )
    asset_description_system_prompt: str = Field(
        default="You are an attentive analyst who describes visual and document assets for coding assistants.",
        description="System prompt supplied when asking the LLM to describe assets.",
    )
    asset_description_prompt_template: str = Field(
        default=(
            "Provide a concise yet thorough description of the supplied asset so a coding assistant "
            "can reference it. Highlight key structures, notable content, and anything relevant to "
            "developers building product experiences."
        ),
        description="User prompt template prepended to asset description requests.",
    )
    asset_structure_guidance_visual: str = Field(
        default="Include notes about composition, style, color balance, and any focal points.",
        description="Additional guidance applied when structure detail is requested for visual assets.",
    )
    asset_structure_guidance_document: str = Field(
        default="Outline the document layout, hierarchy, and any repeated sections or tables.",
        description="Additional guidance when structure detail is requested for documents, decks, or spreadsheets.",
    )
    asset_validation_system_prompt: str = Field(
        default=(
            "You are a meticulous reviewer who validates whether an asset matches a provided description."
            " Always respond with JSON containing 'verdict', 'confidence', and 'reason'."
        ),
        description="System prompt for validation requests.",
    )
    asset_validation_prompt_template: str = Field(
        default=(
            "Determine if the asset aligns with the expected description."
            ' Respond with JSON: {"verdict": "pass|fail", "confidence": number or null, "reason": string}. '
            "If verdict is 'fail', make the reason a short, actionable checklist describing exactly what must change"
            " (e.g., '- add the missing red logo above the header')."
        ),
        description="User prompt template for asset validation requests.",
    )

    # Storage / caching -------------------------------------------------------
    image_dir: str = "images"
    cache_ttl_seconds: int = 3600
    cache_max_items: int = 256
    file_retention_days: int = 7
    cleanup_check_interval_seconds: int = Field(
        default=60,
        description="Delay (seconds) before rechecking when the image directory is missing.",
    )
    cleanup_run_interval_seconds: int = Field(
        default=3600,
        description="Delay (seconds) between cleanup sweeps when the directory exists.",
    )
    image_min_dimension: int = Field(
        default=64,
        description="Minimum allowed width/height (pixels) for generated images.",
    )
    image_max_dimension: int = Field(
        default=4096,
        description="Maximum allowed width/height (pixels) for generated images.",
    )

    def get_llm_settings(self, domain: Literal["image", "docs", "text"]) -> LiteLLMSettings:
        """Return LiteLLM configuration for the requested domain with fallbacks to defaults."""

        model = getattr(self, f"litellm_{domain}_model") or self.litellm_default_model
        api_key = getattr(self, f"litellm_{domain}_api_key") or self.litellm_default_api_key
        api_base = getattr(self, f"litellm_{domain}_api_base") or self.litellm_default_api_base
        extra_params = {
            **self.litellm_default_extra_params,
            **getattr(self, f"litellm_{domain}_extra_params"),
        }
        return LiteLLMSettings(
            model=model,
            api_key=api_key,
            api_base=api_base,
            extra_params=extra_params,
        )


settings = Settings()
