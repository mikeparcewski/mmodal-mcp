# mmodal-mcp Design Overview

## 1. Architecture Summary

```
+------------------+        +----------------------+        +------------------+
|  FastMCP Server  | -----> |  Domain LLM Adapter  | -----> |  LiteLLM Provider |
+------------------+        +----------------------+        +------------------+
        |                             |                              |
        v                             v                              v
  Tools (image/describe/validate)  Config Resolver             External APIs
```

### Components
- **Tools (`main.py`)**
  - `generate_image`: orchestrates prompt building, storage, optional validation, assistant hints.
  - `describe_asset_tool`: resolves asset, builds description prompt, optional validation.
  - `validate_asset_tool`: dedicated validation endpoint returning structured verdicts.

- **Domain LLM Adapter (`config.get_llm_settings`)**
  - Resolves the LiteLLM settings (model, API key, base, extra params) for a given domain: `image`, `docs`, `text`.
  - Falls back to default values when domain-specific overrides are not provided.

- **Generators / Describers / Validators**
  - `generator.generate_image` uses domain `"image"`.
  - `describer.describe_asset` uses domain `"docs"` (with image attachments).
  - `validator.validate_asset` uses domain `"text"` (general-purpose evaluator).

- **Storage (`storage.py`)**
  - Persists generated images + metadata, returns transport-aware URIs.
  - Used by `generate_image`; downstream calls reference paths resolved via `describer.resolve_asset_path`.

- **Validation Feedback**
- Validation results (both inline and standalone) return JSON with actionable checklist.
- Tools embed validation output, assistant hints, retry history, and final guidance in their response payloads.

## 2. Configuration Flow

1. Load base settings from `.env` via `Settings`.
2. When a tool executes, request domain settings via `settings.get_llm_settings(domain)`.
3. Merge domain-specific overrides with defaults; pass result to LiteLLM call.
4. For Gemini or other providers, the model string encodes the provider (`gemini/gemini-1.5-flash`, `openai/dall-e-3`, etc.); API key is resolved per domain.

## 3. Request / Response Contracts

### 3.1 `generate_image`
**Input (subset):**
```json
{
  "prompt": "...",
  "style": "...",
  "acceptance_criteria": "...",
  "dimensions": [1024, 1024],
  "validate_output": true,
  "validation_focus": "Ensure neon reflections...",
  "max_validation_retries": 2
}
```

**Output:**
```json
{
  "data": {
    "uri": "file:///.../image.png",
    "base64_data": "...",
    "metadata": {
      "id": "...",
      "dimensions": [1024, 1024],
      "format": "PNG",
      ...
    }
  },
  "validation": {
    "verdict": "fail",
    "confidence": 0.82,
    "reason": "- add motion blur\n- remove background neon skyline"
  },
  "assistant_hint": "Image generated but validator suggests adding motion blur and removing the skyline.",
  "retry_suggestions": [
    "Regenerate with instruction: 'Ensure transparent background; apply motion blur to wings.'"
  ],
  "retry_history": [
    {
      "attempt": 1,
      "prompt": "...",
      "validation": {"verdict": "fail", "reason": "- add motion blur"}
    }
  ],
  "final_guidance": "Best result still missing transparent background; try re-generating with explicit 'transparent background, no skyline'."
}
```

### 3.2 `describe_asset_tool`
**Input:**
```json
{
  "uri": "images/abc123.png",
  "purpose": "Design review",
  "auto_validate": true,
  "validation_focus": "Highlight wing motion"
}
```

**Output:**
```json
{
  "data": {
    "summary": "Concise description ...",
    "metadata": {...}
  },
  "validation": {
    "verdict": "pass",
    "confidence": 0.9,
    "reason": "- description covers neon lighting\n- mentions hummingbird motion"
  },
  "assistant_hint": "Summary validated successfully."
}
```

### 3.3 `validate_asset_tool`
**Input:**
```json
{
  "uri": "...",
  "expected_description": "Detailed requirements ...",
  "evaluation_focus": "Wing blur",
  "structure_detail": true
}
```

**Output:**
```json
{
  "validation": {
    "verdict": "fail",
    "confidence": 0.6,
    "reason": "- add motion blur to wings\n- replace background with transparent layer"
  },
  "assistant_hint": "Validator suggests two changes."
}
```

## 4. Validation Strategy

- **Prompt Template:** `ASSET_VALIDATION_PROMPT_TEMPLATE` enforces JSON output with actionable checklist on failure.
- **Integration Points:**
  - `generate_image` → auto validation when `validate_output` true.
  - `describe_asset_tool` → auto validation when `auto_validate` true.
  - `validate_asset_tool` → manual validation entry point.
- **Auto-Retry Flow:** When `max_validation_retries` > 0, each failed validation triggers prompt refinements based on the checklist. Responses include `retry_history` documenting each attempt and `final_guidance` summarizing remaining gaps.
- **Retry Suggestions:** Derived from validation reason or acceptance criteria to help agents adjust prompts.

## 5. Error Handling

- Wrap LiteLLM exceptions, surfacing `code`, `message`, `provider_hint`.
- If generation fails, return `RuntimeError` to tool; consider mapping to MCP error codes in CLI.
- For missing assets (path issues), provide `FileNotFoundError` with resolved path to ease debugging.

## 6. Future Enhancements

- Automatic retry logic configurable via request params (e.g., `max_validation_retries`).
- Asynchronous streaming of intermediate validation states via SSE transport.
- Optional remote storage integration (signed URLs) for collaboration.
- Enhanced logging/telemetry for agent analytics (validation failure stats, retry counts).
