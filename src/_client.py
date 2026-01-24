# Copyright (c) 2026 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

"""Demo client for Fetch MCP server.

Demonstrates using the fetch tools via DedalusRunner and raw client.

Environment variables:
    DEDALUS_API_KEY: Your Dedalus API key (dsk_*)
    DEDALUS_API_URL: Product API base URL
    DEDALUS_AS_URL: Authorization server URL
"""

import asyncio
import os

from dotenv import load_dotenv

load_dotenv()

from dedalus_labs import AsyncDedalus, DedalusRunner


class MissingEnvError(ValueError):
    """Required environment variable not set."""


def get_env(key: str) -> str:
    """Get required env var or raise."""
    val = os.getenv(key)
    if not val:
        raise MissingEnvError(key)
    return val


API_URL = get_env("DEDALUS_API_URL")
AS_URL = get_env("DEDALUS_AS_URL")
DEDALUS_API_KEY = os.getenv("DEDALUS_API_KEY")

# Debug: print env vars
print("=== Environment ===")
print(f"  DEDALUS_API_URL: {API_URL}")
print(f"  DEDALUS_AS_URL: {AS_URL}")
print(f"  DEDALUS_API_KEY: {DEDALUS_API_KEY[:20]}..." if DEDALUS_API_KEY else "  DEDALUS_API_KEY: None")


async def run_fetch_url() -> None:
    """Demo fetching a URL and extracting content as markdown."""
    client = AsyncDedalus(api_key=DEDALUS_API_KEY, base_url=API_URL, as_base_url=AS_URL)
    runner = DedalusRunner(client)

    result = await runner.run(
        input="Fetch the contents of https://example.com and summarize what you find.",
        model="openai/gpt-5",
        mcp_servers=["issac/fetch-mcp"],
    )

    print("=== Fetch URL Demo ===")
    print(result.output)

    if result.mcp_results:
        print("\n=== MCP Tool Results ===")
        for r in result.mcp_results:
            print(f"  {r.tool_name} ({r.duration_ms}ms): {str(r.result)[:200]}...")




async def main() -> None:
    """Run demo modes."""
    print("=" * 60)
    print("Fetch URL Demo (DedalusRunner)")
    print("=" * 60)
    await run_fetch_url()

    print("\n" + "=" * 60)
    print("Check Robots.txt Demo (DedalusRunner)")
    print("=" * 60)
    await run_check_robots()


if __name__ == "__main__":
    asyncio.run(main())
