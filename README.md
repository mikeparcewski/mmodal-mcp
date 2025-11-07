# mmodal-mcp

Give **any MCP client**—CLI tools, packaged vendor agents, custom automations, or IDE integrations—the visual skills they’re missing. mmodal-mcp is a FastMCP server that wraps LiteLLM so assistants can generate new imagery and produce rich descriptions of existing assets (images, decks, spreadsheets, PDFs) through guided, agent-friendly prompts.

## Why It Matters

- **Fill the gap**: Most copilots and command-line assistants can’t inspect PDFs, decks, or screenshots. This server adds that superpower through MCP tools.
- **Consistent guidance**: Validation returns actionable checklists, so autonomous agents can retry with confidence.
- **Bring your own provider**: Point LiteLLM at Gemini/Imagen, OpenAI DALL·E, or your own inference stack—no code changes required.
- **Fits any MCP client**: Use it from CLI tools, packaged vendor agents, custom automation, or GUI wrappers—if the client speaks MCP, it can use mmodal-mcp.

## Quick MCP Configs

### Custom Agents & CI Automation

```bash
uv run python scripts/fastmcp_pipeline.py
```

The script launches the server via stdio, calls each tool, and prints sanitized responses—ideal for bespoke agents, QA jobs, or integration tests.

### Claude Code CLI

```bash
claude mcp add mmodal \
  -e LITELLM_DEFAULT_MODEL=gemini/imagen-4.0-generate-001 \
  -e LITELLM_DEFAULT_API_KEY=your-gemini-key \
  -- uvx --from mmodal-mcp mmodal-mcp
```

### Claude Desktop (macOS / Windows)

```json
{
  "mmodal": {
    "command": "uvx",
    "args": ["--from", "mmodal-mcp", "mmodal-mcp"],
    "env": {
      "LITELLM_DEFAULT_MODEL": "gemini/imagen-4.0-generate-001",
      "LITELLM_DEFAULT_API_KEY": "your-gemini-key"
    }
  }
}
```

Save in `~/Library/Application Support/Claude/mcp/config.json` (macOS) or `%APPDATA%/Claude/mcp/config.json` (Windows) and restart Claude Desktop.

### Cursor / Windsurf / Other MCP-Aware IDEs

```json
{
  "mcpServers": {
    "mmodal": {
      "command": "uvx",
      "args": ["--from", "mmodal-mcp", "mmodal-mcp", "--transport", "sse"],
      "env": {
        "LITELLM_DEFAULT_MODEL": "gemini/imagen-4.0-generate-001",
        "LITELLM_DEFAULT_API_KEY": "your-gemini-key"
      }
    }
  }
}
```

Use `--transport stdio` if the client expects stdio (stdio is the default).

### OpenAI Codex CLI (`~/.codex/config.toml`)

```toml
[mcp_servers.mmodal]
command = "uvx"
args = ["--from", "mmodal-mcp", "mmodal-mcp"]
env = { LITELLM_DEFAULT_MODEL = "openai/dall-e-3", LITELLM_DEFAULT_API_KEY = "your-openai-key" }
startup_timeout_ms = 20000
```

### Gemini CLI (`~/.gemini/settings.json`)

```json
{
  "mcpServers": {
    "mmodal": {
      "command": "uvx",
      "args": ["--from", "mmodal-mcp", "mmodal-mcp"],
      "env": {
        "LITELLM_DEFAULT_MODEL": "gemini/imagen-4.0-generate-001",
        "LITELLM_DEFAULT_API_KEY": "your-gemini-key"
      }
    }
  }
}
```

## Features

- **Multiple Formats**: Support for PNG, JPEG, and WebP output formats.
- **Quality Control**: Auto, high, medium, and low quality settings.
- **Background Control**: Transparent, opaque, or auto background options.
- **FastMCP Framework**: Built with the latest MCP Python SDK.
- **LiteLLM Integration**: Provider-agnostic LLM/image access powered by LiteLLM.
- **Assistant-Friendly Tools**: Guided MCP tools for generating, describing, and validating assets.
- **Automated Validation**: Optional LLM-powered checks to confirm assets match expectations.
- **Multiple Transports**: STDIO, HTTP, and SSE transport support.
- **Structured Output**: Validated tool responses with proper schemas.
- **Resource Access**: MCP resources for image retrieval and management.
- **Local Storage**: Organized directory structure with metadata.
- **URL-based Access**: Transport-aware URL generation for images.
- **Dual Access**: Immediate base64 data + persistent resource URIs.
- **Smart Caching**: Lightweight in-memory LRU cache with TTL controls.
- **Auto Cleanup**: Configurable file retention policies.
- **Type Safety**: Full type hints with Pydantic models.
- **Error Handling**: Comprehensive error handling and logging.
- **Configuration**: Environment-based configuration management.
- **Testing**: Pytest-based test suite with async support.
- **Dev Tools**: Hot reload for development.

## Getting Started

### Prerequisites

- Python 3.10 or higher
- `uv` package manager (recommended)

### Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd mmodal-mcp
    ```

2.  **Install dependencies using uv:**
    ```bash
    uv sync
    ```

    This will automatically create a virtual environment and install all required dependencies from `pyproject.toml`.

### MCP Tools at a Glance

| Tool | Purpose | Key Inputs |
| --- | --- | --- |
| `generate_image` | Produce a new image that matches a detailed prompt. | Prompt, quality/background/dimensions, style & acceptance criteria, `validate_output`, `validation_focus`. |
| `describe_asset` | Summarize existing assets so assistants can reference them. | File path/ID, optional purpose & audience, `structure_detail`, `auto_validate`, `validation_focus`. |
| `validate_asset` | Confirm an asset matches a provided description or criteria. | File path/ID, expected description, optional `evaluation_focus`, `structure_detail`. |

All tools share common LiteLLM plumbing and use configurable prompt templates so you can tailor the experience for your assistant or brand voice.

Every response follows the same structure:

```
{
  "data": {...},
  "metadata": {...},
  "validation": {...} | null,
  "assistant_hint": "...",
  "retry_suggestions": ["..."],
  "retry_history": [ ... ],
  "final_guidance": "..."
}
```

This makes it easy for agents to inspect validation results, apply automated retries, and show users next steps.

### Configuration

1.  **Create a `.env` file:**
    Copy the `.env.example` file to `.env`:
    ```bash
    cp .env.example .env
    ```

2.  **Set your configuration:**
    The server reads its settings from environment variables (see `.env.example` for a guided template). Update the values to match your provider and runtime. A quick reference is provided below.

#### Key Environment Variables

| Variable | Purpose | Example |
| --- | --- | --- |
| `LITELLM_DEFAULT_MODEL` | Fallback LiteLLM model identifier (`provider/model`) | `gemini/gemini-1.5-flash` |
| `LITELLM_DEFAULT_API_KEY` | Default API key LiteLLM should use | `${GEMINI_API_KEY}` |
| `LITELLM_DEFAULT_API_BASE` | Override base URL (optional) | `https://custom.endpoint.googleapis.com` |
| `LITELLM_DEFAULT_EXTRA_PARAMS` | JSON-encoded kwargs applied to all calls | `{"quality": "high"}` |
| `LITELLM_IMAGE_MODEL` | Optional override for image generation | `gemini/gemini-image-001` |
| `LITELLM_DOCS_MODEL` | Optional override for asset/document descriptions | `gemini/gemini-2.0-pro` |
| `LITELLM_TEXT_MODEL` | Optional override for validation/text flows | `gemini/gemini-2.0-pro` |
| `LITELLM_*_API_KEY` / `API_BASE` / `EXTRA_PARAMS` | Per-domain overrides that fall back to defaults | *see `.env.example`* |
| `IMAGE_GENERATION_PROMPT_PREFIX` | Text prepended to every generation prompt | *see `.env.example`* |
| `ASSET_DESCRIPTION_SYSTEM_PROMPT` | System message for description calls | *see `.env.example`* |
| `ASSET_DESCRIPTION_PROMPT_TEMPLATE` | Default user prompt for description calls | *see `.env.example`* |
| `ASSET_STRUCTURE_GUIDANCE_VISUAL` | Guidance for composition/style analysis when requested | *see `.env.example`* |
| `ASSET_STRUCTURE_GUIDANCE_DOCUMENT` | Guidance for layout/structure analysis when requested | *see `.env.example`* |
| `ASSET_VALIDATION_SYSTEM_PROMPT` | System message for validation calls | *see `.env.example`* |
| `ASSET_VALIDATION_PROMPT_TEMPLATE` | Default user prompt for validation calls | *see `.env.example`* |
| `IMAGE_DIR` | Directory for generated images + metadata | `images` |
| `CACHE_TTL_SECONDS` | Seconds before cached base64 payloads expire (`0` disables expiry) | `3600` |
| `CACHE_MAX_ITEMS` | Max items in the in-memory LRU cache | `256` |
| `FILE_RETENTION_DAYS` | Cleanup window for on-disk files | `7` |
| `CLEANUP_CHECK_INTERVAL_SECONDS` | Delay before rechecking when the image directory is missing | `60` |
| `CLEANUP_RUN_INTERVAL_SECONDS` | Delay between cleanup sweeps when the directory exists | `3600` |
| `IMAGE_MIN_DIMENSION` | Minimum allowed width/height (pixels) for generated images | `64` |
| `IMAGE_MAX_DIMENSION` | Maximum allowed width/height (pixels) for generated images | `4096` |

#### Example Configurations

```
# Google Gemini (single key for everything)
LITELLM_DEFAULT_MODEL="gemini/gemini-1.5-flash"
LITELLM_DEFAULT_API_KEY="${GEMINI_API_KEY}"
LITELLM_DEFAULT_EXTRA_PARAMS='{"safetySettings": {"harmCategory": "HARM_CATEGORY_DEROGATORY"}}'

# Hybrid Gemini setup (separate image + doc credentials)
LITELLM_DEFAULT_MODEL="gemini/gemini-1.5-flash"
LITELLM_DEFAULT_API_KEY="${GEMINI_IMAGE_KEY}"
LITELLM_DOCS_MODEL="gemini/gemini-2.0-pro"
LITELLM_DOCS_API_KEY="${GEMINI_DOC_KEY}"
LITELLM_TEXT_MODEL="gemini/gemini-2.0-pro"

# OpenAI DALL-E 3 with GPT-4o for text
LITELLM_DEFAULT_MODEL="openai/dall-e-3"
LITELLM_DEFAULT_API_KEY="${OPENAI_API_KEY}"
LITELLM_DEFAULT_EXTRA_PARAMS='{"quality": "high", "style": "vivid"}'
LITELLM_TEXT_MODEL="openai/gpt-4o-mini"
ASSET_DESCRIPTION_SYSTEM_PROMPT="You are a product designer describing assets for an engineering team."

# Local inference proxy
LITELLM_DEFAULT_MODEL="local/flux-schnell"
LITELLM_DEFAULT_API_BASE="http://localhost:8080"
LITELLM_DEFAULT_EXTRA_PARAMS='{"guidance_scale": 7.5}'
LITELLM_TEXT_MODEL="local/qwen-2"
```

### Example Tool Calls

```
# generate_image
{
  "prompt": "An exploded diagram of a drone motor",
  "quality": "high",
  "background": "transparent",
  "dimensions": [1024, 1024],
  "image_format": "PNG",
  "style": "technical illustration",
  "acceptance_criteria": "Label each part, include measurements",
  "validate_output": true,
  "validation_focus": "Ensure all callouts appear",
  "max_validation_retries": 2
}

# describe_asset
{
  "uri": "docs/product-roadmap.pdf",
  "purpose": "Engineering weekly sync",
  "audience": "Full-stack team",
  "structure_detail": true,
  "auto_validate": true,
  "validation_focus": "Highlight milestones"
}

# validate_asset
{
  "uri": "images/drone-motor.png",
  "expected_description": "Exploded drone motor diagram showing bearings, stator, rotor",
  "structure_detail": true,
  "evaluation_focus": "Check that all labeled parts are visible"
}
```

### Running the Server

**Development Mode (with hot reloading):**

To run the server in development mode, use the `dev` script defined in `pyproject.toml`:

```bash
uv run dev
```

The server will be available at `http://127.0.0.1:8000`.

**MCP Transports:**

Run the server with different transport options:

```bash
uv run mmodal-mcp                    # STDIO transport (default)
uv run mmodal-mcp --transport sse    # SSE endpoint (Server-Sent Events)
mcp dev main:mcp                     # Launch with MCP Inspector
```

**Production Mode:**

For production, you can run the server directly with an ASGI server like `uvicorn`:

```bash
uvicorn main:mcp --port 8000
```

### Running Tests

To run the test suite, use `pytest`:

```bash
uv run pytest
```

For verbose output with detailed test information:

```bash
uv run pytest -v
```

This will run all the tests in the `tests/` directory and provide a report of the results.

### Development Workflow

1. **Install dependencies (including dev tools):**
   ```bash
   uv sync
   ```

2. **Run tests after making changes:**
   ```bash
   uv run pytest -v
   ```

3. **Test the MCP server locally:**
   ```bash
   # Run with stdio transport
   uv run mmodal-mcp

   # Or run the demo pipeline
   uv run python scripts/fastmcp_pipeline.py
   ```

4. **Development mode with hot reload:**
   ```bash
   uv run dev
   ```
