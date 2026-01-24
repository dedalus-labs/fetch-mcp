# Copyright (c) 2026 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

"""Fetch API tools.

Provides web content fetching capabilities.
Converts HTML to markdown for easier consumption by LLMs.
"""

from typing import Any
from urllib.parse import urlparse, urlunparse

import httpx
import markdownify
import readabilipy.simple_json
from protego import Protego
from pydantic.dataclasses import dataclass

from dedalus_mcp import tool
from dedalus_mcp.types import ToolAnnotations


DEFAULT_USER_AGENT_AUTONOMOUS = "ModelContextProtocol/1.0 (Autonomous; +https://github.com/modelcontextprotocol/servers)"
DEFAULT_USER_AGENT_MANUAL = "ModelContextProtocol/1.0 (User-Specified; +https://github.com/modelcontextprotocol/servers)"


@dataclass(frozen=True)
class FetchResult:
    """Fetch API result."""

    success: bool
    content: str | None = None
    content_type: str | None = None
    error: str | None = None


def _extract_content_from_html(html: str) -> str:
    """Extract and convert HTML content to Markdown format.

    Args:
        html: Raw HTML content to process

    Returns:
        Simplified markdown version of the content

    """
    ret = readabilipy.simple_json.simple_json_from_html_string(html, use_readability=True)
    if not ret["content"]:
        return "<error>Page failed to be simplified from HTML</error>"
    content = markdownify.markdownify(
        ret["content"],
        heading_style=markdownify.ATX,
    )
    return content


def _get_robots_txt_url(url: str) -> str:
    """Get the robots.txt URL for a given website URL.

    Args:
        url: Website URL to get robots.txt for

    Returns:
        URL of the robots.txt file

    """
    parsed = urlparse(url)
    robots_url = urlunparse((parsed.scheme, parsed.netloc, "/robots.txt", "", "", ""))
    return robots_url


async def _check_robots_txt(url: str, user_agent: str, proxy_url: str | None = None) -> tuple[bool, str | None]:
    """Check if the URL can be fetched according to robots.txt.

    Args:
        url: URL to check
        user_agent: User agent string
        proxy_url: Optional proxy URL

    Returns:
        Tuple of (allowed, error_message)

    """
    robot_txt_url = _get_robots_txt_url(url)

    async with httpx.AsyncClient(proxies=proxy_url) as client:
        try:
            response = await client.get(
                robot_txt_url,
                follow_redirects=True,
                headers={"User-Agent": user_agent},
            )
        except httpx.HTTPError:
            return False, f"Failed to fetch robots.txt {robot_txt_url} due to a connection issue"

        if response.status_code in (401, 403):
            return (
                False,
                f"When fetching robots.txt ({robot_txt_url}), received status {response.status_code} "
                "so assuming that autonomous fetching is not allowed",
            )
        elif 400 <= response.status_code < 500:
            return True, None

        robot_txt = response.text

    processed_robot_txt = "\n".join(line for line in robot_txt.splitlines() if not line.strip().startswith("#"))
    robot_parser = Protego.parse(processed_robot_txt)

    if not robot_parser.can_fetch(str(url), user_agent):
        return (
            False,
            f"The site's robots.txt ({robot_txt_url}) specifies that autonomous fetching of this page is not allowed",
        )

    return True, None


async def _fetch_url(
    url: str,
    user_agent: str,
    force_raw: bool = False,
    proxy_url: str | None = None,
) -> FetchResult:
    """Fetch the URL and return the content.

    Args:
        url: URL to fetch
        user_agent: User agent string
        force_raw: Get raw content without markdown conversion
        proxy_url: Optional proxy URL

    Returns:
        FetchResult with content or error

    """
    async with httpx.AsyncClient(proxies=proxy_url) as client:
        try:
            response = await client.get(
                url,
                follow_redirects=True,
                headers={"User-Agent": user_agent},
                timeout=30,
            )
        except httpx.HTTPError as e:
            return FetchResult(success=False, error=f"Failed to fetch {url}: {e!r}")

        if response.status_code >= 400:
            return FetchResult(success=False, error=f"Failed to fetch {url} - status code {response.status_code}")

        page_raw = response.text
        content_type = response.headers.get("content-type", "")

    is_page_html = "<html" in page_raw[:100] or "text/html" in content_type or not content_type

    if is_page_html and not force_raw:
        content = _extract_content_from_html(page_raw)
        return FetchResult(success=True, content=content, content_type="text/markdown")

    return FetchResult(success=True, content=page_raw, content_type=content_type)


# --- Fetch Tools ---


@tool(
    description="Fetch a URL from the internet and extract its contents as markdown. "
    "This tool grants internet access to retrieve up-to-date information from web pages.",
    tags=["fetch", "web", "read"],
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def fetch_url(
    url: str,
    max_length: int = 5000,
    start_index: int = 0,
    raw: bool = False,
    ignore_robots_txt: bool = False,
    proxy_url: str | None = None,
) -> FetchResult:
    """Fetch a URL and extract its contents.

    Args:
        url: URL to fetch
        max_length: Maximum number of characters to return (default 5000)
        start_index: Start content from this character index (default 0)
        raw: Get raw content without markdown conversion (default false)
        ignore_robots_txt: Ignore robots.txt restrictions (default false)
        proxy_url: Proxy URL to use for requests (optional)

    Returns:
        FetchResult with content or error

    """
    if not url:
        return FetchResult(success=False, error="URL is required")

    user_agent = DEFAULT_USER_AGENT_AUTONOMOUS

    # Check robots.txt unless ignored
    if not ignore_robots_txt:
        allowed, error = await _check_robots_txt(url, user_agent, proxy_url)
        if not allowed:
            return FetchResult(success=False, error=error)

    # Fetch the URL
    result = await _fetch_url(url, user_agent, force_raw=raw, proxy_url=proxy_url)

    if not result.success:
        return result

    content = result.content or ""
    original_length = len(content)

    # Handle pagination
    if start_index >= original_length:
        return FetchResult(success=True, content="<error>No more content available.</error>")

    truncated_content = content[start_index : start_index + max_length]
    if not truncated_content:
        return FetchResult(success=True, content="<error>No more content available.</error>")

    actual_content_length = len(truncated_content)
    remaining_content = original_length - (start_index + actual_content_length)

    # Add continuation hint if content was truncated
    if actual_content_length == max_length and remaining_content > 0:
        next_start = start_index + actual_content_length
        truncated_content += (
            f"\n\n<error>Content truncated. Call fetch_url with start_index={next_start} to get more content.</error>"
        )

    return FetchResult(
        success=True,
        content=f"Contents of {url}:\n{truncated_content}",
        content_type=result.content_type,
    )


@tool(
    description="Check if a URL can be autonomously fetched according to the site's robots.txt file",
    tags=["fetch", "robots", "read"],
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def check_robots_txt(url: str, proxy_url: str | None = None) -> FetchResult:
    """Check if a URL can be fetched according to robots.txt.

    Args:
        url: URL to check
        proxy_url: Proxy URL to use for requests (optional)

    Returns:
        FetchResult indicating if fetching is allowed

    """
    if not url:
        return FetchResult(success=False, error="URL is required")

    user_agent = DEFAULT_USER_AGENT_AUTONOMOUS
    allowed, error = await _check_robots_txt(url, user_agent, proxy_url)

    if allowed:
        return FetchResult(success=True, content=f"Fetching {url} is allowed by robots.txt")
    return FetchResult(success=False, error=error)


@tool(
    description="Extract the robots.txt URL for a given website",
    tags=["fetch", "robots", "read"],
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def get_robots_txt_url(url: str) -> FetchResult:
    """Get the robots.txt URL for a website.

    Args:
        url: Website URL

    Returns:
        FetchResult with robots.txt URL

    """
    if not url:
        return FetchResult(success=False, error="URL is required")

    robots_url = _get_robots_txt_url(url)
    return FetchResult(success=True, content=robots_url)


fetch_tools = [
    fetch_url,
    check_robots_txt,
    get_robots_txt_url,
]
