#!/usr/bin/env python3
"""
Simple test script to validate MCP server startup and basic functionality.
"""
import sys
import asyncio
import subprocess
import time
from pathlib import Path

async def test_server_import():
    """Test that the server can be imported and initialized."""
    try:
        import main
        print("✓ Successfully imported main module")

        # Check that mcp object exists
        if hasattr(main, 'mcp'):
            print(f"✓ MCP server object exists: {type(main.mcp)}")

            # Try to access the tools using FastMCP's API
            try:
                # FastMCP may have different ways to access tools
                if hasattr(main.mcp, 'list_tools'):
                    tools = await main.mcp.list_tools()
                    if tools:
                        print(f"✓ Server has {len(tools)} tools registered")
                        for tool in tools[:5]:
                            tool_name = tool.name if hasattr(tool, 'name') else str(tool)
                            print(f"  - {tool_name}")
                        if len(tools) > 5:
                            print(f"  ... and {len(tools) - 5} more")
                elif hasattr(main.mcp, 'tools'):
                    tools = main.mcp.tools
                    if tools:
                        print(f"✓ Server has {len(tools)} tools registered")
                        for tool_name in list(tools.keys())[:5]:
                            print(f"  - {tool_name}")
                        if len(tools) > 5:
                            print(f"  ... and {len(tools) - 5} more")
                else:
                    print("⚠ Could not determine tool count (may register at runtime)")
            except Exception as e:
                print(f"⚠ Could not check tools: {e}")

            return True
        else:
            print("✗ MCP server object not found")
            return False

    except ImportError as e:
        print(f"✗ Failed to import main module: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

async def test_console_script_entry_point():
    """Test that the console script entry point (mmodal-stdio) works correctly."""
    try:
        print("Testing mmodal-stdio console script...")

        # Start the server process using the actual console script
        proc = subprocess.Popen(
            [".venv/bin/mmodal-stdio"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=Path(__file__).parent,
            text=True
        )

        # Wait for server to be ready by reading initial output or checking if it's still alive
        max_wait = 2.0  # seconds
        start_time = time.time()
        server_started = False

        while time.time() - start_time < max_wait:
            if proc.poll() is not None:
                # Process died
                _, stderr = proc.communicate()
                print(f"✗ mmodal-stdio script crashed: {stderr}")
                return False

            # If still running after a reasonable time, consider it started
            if time.time() - start_time > 0.3:
                server_started = True
                break

            time.sleep(0.1)

        if server_started and proc.poll() is None:
            print("✓ mmodal-stdio console script started successfully")
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
            return True
        else:
            print("✗ mmodal-stdio script failed to start")
            return False

    except FileNotFoundError:
        print("✗ mmodal-stdio script not found in .venv/bin/")
        return False
    except Exception as e:
        print(f"✗ Failed to test mmodal-stdio script: {e}")
        return False


async def test_mcp_cli_stdio():
    """Test that the MCP server can be started via CLI with stdio transport."""
    try:
        print("Testing MCP CLI with stdio transport...")

        # Start the server process
        proc = subprocess.Popen(
            [str(Path(sys.executable).parent / "mcp"), "run", "main.py:mcp", "--transport", "stdio"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=Path(__file__).parent,
            text=True
        )

        # Wait for server to be ready by checking if it stays alive
        max_wait = 2.0  # seconds
        start_time = time.time()
        server_started = False

        while time.time() - start_time < max_wait:
            if proc.poll() is not None:
                # Process died
                _, stderr = proc.communicate()
                print(f"✗ MCP server crashed: {stderr}")
                return False

            # If still running after a reasonable time, consider it started
            if time.time() - start_time > 0.3:
                server_started = True
                break

            time.sleep(0.1)

        if server_started and proc.poll() is None:
            print("✓ MCP server started successfully with stdio transport")
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
            return True
        else:
            print("✗ MCP server failed to start")
            return False

    except Exception as e:
        print(f"✗ Failed to start MCP server: {e}")
        return False

async def test_package_structure():
    """Test that all required modules can be imported."""
    modules = ['cache', 'cleanup', 'config', 'describer', 'generator',
               'main', 'storage', 'utils', 'validator']

    try:
        for module in modules:
            __import__(module)
        print(f"✓ All {len(modules)} modules can be imported")
        return True
    except ImportError as e:
        print(f"✗ Failed to import module: {e}")
        return False

async def main_test():
    """Run all tests."""
    print("=" * 60)
    print("MCP Server Validation Tests")
    print("=" * 60)

    results = []

    # Test 1: Package structure
    print("\n[Test 1] Package Structure")
    results.append(await test_package_structure())

    # Test 2: Import and initialization
    print("\n[Test 2] Server Import and Initialization")
    results.append(await test_server_import())

    # Test 3: Console script entry point
    print("\n[Test 3] Console Script Entry Point (mmodal-stdio)")
    results.append(await test_console_script_entry_point())

    # Test 4: CLI stdio transport
    print("\n[Test 4] MCP CLI with stdio transport")
    results.append(await test_mcp_cli_stdio())

    # Summary
    print("\n" + "=" * 60)
    print(f"Tests passed: {sum(results)}/{len(results)}")
    print("=" * 60)

    return all(results)

if __name__ == "__main__":
    success = asyncio.run(main_test())
    sys.exit(0 if success else 1)
