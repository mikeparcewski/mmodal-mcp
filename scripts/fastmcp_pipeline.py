import asyncio
import json
import os
from pathlib import Path
from urllib.parse import urlparse

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp import types

REPO_ROOT = Path(__file__).resolve().parents[1]

SERVER_COMMAND = [
    "uv",
    "run",
    "mcp",
    "run",
    "main.py:mcp",
    "--transport",
    "stdio",
]


async def call_tool(session: ClientSession, name: str, arguments: dict) -> types.CallToolResult:
    payload = {"input": arguments}
    result = await session.call_tool(name, arguments=payload)
    return result


def sanitize_payload(obj: dict | list | str | None) -> dict | list | str | None:
    if isinstance(obj, dict):
        return {
            key: (f"<base64 len={len(value)}>" if key == "base64_data" and isinstance(value, str) else sanitize_payload(value))
            for key, value in obj.items()
        }
    if isinstance(obj, list):
        return [sanitize_payload(entry) for entry in obj]
    return obj


def decode_tool_result(result: types.CallToolResult) -> list[dict]:
    decoded: list[dict] = []
    for item in result.content:
        match item:
            case types.TextContent(text=text):
                parsed = None
                try:
                    parsed = json.loads(text)
                except Exception:
                    pass
                if isinstance(parsed, (dict, list)):
                    decoded.append({"type": "json", "data": sanitize_payload(parsed)})
                else:
                    decoded.append({"type": "text", "text": text})
            case types.JsonContent(data=data):
                decoded.append({"type": "json", "data": sanitize_payload(data)})
            case _:
                decoded.append({"type": item.type, "repr": repr(item)})
    return decoded


def pretty_print(title: str, payload: dict | list | str) -> None:
    print(f"\n=== {title} ===")
    if isinstance(payload, (dict, list)):
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(payload)


async def run_pipeline() -> None:
    env = dict(os.environ)
    server_params = StdioServerParameters(
        command=SERVER_COMMAND[0],
        args=SERVER_COMMAND[1:],
        env=env,
        cwd=str(REPO_ROOT),
    )

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            init = await session.initialize()
            pretty_print("Initialized", init.model_dump())

            tools = await session.list_tools()
            pretty_print("Available tools", [tool.name for tool in tools.tools])

            gen_args = {
            "prompt": "A luminous hummingbird hovering beside neon flowers, cyberpunk skyline",
            "quality": "high",
            "background": "transparent",
                "dimensions": [512, 512],
                "image_format": "PNG",
                "style": "futuristic concept art",
                "acceptance_criteria": "Include motion-blur wings and reflective lighting",
                "validate_output": True,
                "validation_focus": "Check for wing blur and reflective neon highlights",
                "max_validation_retries": 1,
            }
            gen_result = await call_tool(session, "generate_image", gen_args)
            gen_payload = decode_tool_result(gen_result)
            pretty_print("generate_image result", gen_payload)

            uri = None
            for entry in gen_payload:
                if entry.get("type") == "json":
                    data = entry["data"]
                    uri = data.get("data", {}).get("uri")
                    break

            if not uri:
                print("Generation did not return a URI; aborting.")
                return

            asset_path = urlparse(uri).path

            describe_args = {
                "uri": asset_path,
                "structure_detail": True,
                "auto_validate": True,
                "validation_focus": "Ensure mention of neon lighting and motion",
                "max_validation_retries": 1,
            }
            describe_result = await call_tool(session, "describe_asset_tool", describe_args)
            describe_payload = decode_tool_result(describe_result)
            pretty_print("describe_asset_tool result", describe_payload)

            validate_args = {
                "uri": asset_path,
                "expected_description": "A luminous hummingbird hovering near neon flowers with wing motion blur",
                "structure_detail": True,
                "evaluation_focus": "Wing blur and neon lighting",
            }
            validate_result = await call_tool(session, "validate_asset_tool", validate_args)
            validate_payload = decode_tool_result(validate_result)
            pretty_print("validate_asset_tool result", validate_payload)


if __name__ == "__main__":
    asyncio.run(run_pipeline())
