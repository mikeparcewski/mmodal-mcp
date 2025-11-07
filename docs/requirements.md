# mmodal-mcp Requirements

## 1. Goals
- Provide an agent-friendly MCP server that can generate new visuals, describe existing assets, validate alignment, and optionally auto-retry when validation fails.
- Support heterogeneous LiteLLM providers by allowing per-domain (image, docs, text) model/API key overrides while remaining easy to configure with single defaults.
- Deliver actionable feedback so downstream agents can automatically iterate without manual intervention.

## 2. Functional Requirements
### 2.1 Tools & Capabilities
1. **Image Generation (`generate_image`)**
   - Accepts structured inputs (prompt, style, acceptance criteria, dimensions, etc.).
   - Produces: transport-aware URI, base64 payload, metadata, validation verdict (optional), assistant hint.
   - Supports optional automatic validation and exposes clear retry guidance when validation fails.

2. **Asset Description (`describe_asset`)**
   - Accepts path/URI to assets (images, PDFs, presentations, spreadsheets, text files).
   - Produces: concise summary, metadata (type, key attributes, path), validation verdict (optional), assistant hint.
   - Automatically selects the appropriate LiteLLM configuration (docs/text domain) while still handling image attachments gracefully.

3. **Asset Validation (`validate_asset`)**
   - Accepts asset reference, expected description, optional evaluation focus, structure flag.
  - Produces: verdict (`pass|fail|unknown`), confidence (0–1 or null), actionable checklist in the `reason`, assistant hint.

### 2.2 Validation Workflow
- Validation prompts must request a short actionable checklist when verdict is `fail`.
- Generation/description endpoints should still return data even if validation fails, embedding the checklist for the agent to act on.
- Support configurable auto-retry (`max_validation_retries`) controlled by the caller. Each retry should adjust prompts using validation feedback. If retries are exhausted, return a summary of attempts, remaining gaps, and next-step guidance.

### 2.3 Configuration
- Environment variables define default LiteLLM model, API key, base URL, and shared extra params.
- Optional overrides exist per domain:
  - Image: `LITELLM_IMAGE_*`
  - Document/description: `LITELLM_DOCS_*`
  - General text/validation: `LITELLM_TEXT_*`
- If overrides are absent, the defaults are used.
- Convenience mapping for common provider keys (e.g., `GEMINI_API_KEY`, `OPENAI_API_KEY`) should be supported if feasible.

### 2.4 Responses
- Every tool returns a consistent envelope:
  ```json
  {
    "data": {...},
    "metadata": {...},
    "validation": {...} | null,
    "assistant_hint": "string",
    "retry_suggestions": ["..."],
    "retry_history": [ ... ],
    "final_guidance": "string"
  }
```
- Errors should surface as structured fields rather than raw exceptions where possible (e.g., provide `error.code`, `error.message`, `provider_hint`).

### 2.5 File Handling
- Ensure generated assets are saved under `IMAGE_DIR` and returned URIs resolve correctly for any transport.
- Description/validation calls should accept absolute paths, relative paths within `IMAGE_DIR`, or relative references provided by `generate_image`.

## 3. Non-Functional Requirements
- Maintain compatibility with existing tests; add new coverage for domain-specific config resolution and validation checklists.
- Provide documentation (README, .env.example) reflecting the configuration matrix, tool behavior, and sample payloads.
- Keep latency reasonable by minimizing unnecessary validation calls; allow callers to toggle validation.
- Ensure agent-facing logs are informative (e.g., logging validation failures, retries, provider errors).

## 4. Open Questions / Future Work
- Expose auto-retry logic directly in the tools versus returning guidance for clients to act on.
- Allow configurable maximum validation retries per request.
- Consider uploading generated assets to remote storage or providing signed URLs for easier sharing.
