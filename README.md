# Fetch MCP Server

A Fetch MCP server built with the [Dedalus MCP framework](https://dedaluslabs.ai). Provides web content fetching capabilities, converting HTML to markdown for easier consumption by LLMs.

## Features

### Available Tools

#### Fetch

| Tool | Description |
|------|-------------|
| `fetch_url` | Fetch a URL and extract its contents as markdown |
| `check_robots_txt` | Check if a URL can be fetched according to robots.txt |
| `get_robots_txt_url` | Get the robots.txt URL for a website |

#### Smoke Tests

| Tool | Description |
|------|-------------|
| `smoke_ping` | Simple ping for testing MCP connection |

### Tool Parameters

#### fetch_url

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | string | required | URL to fetch |
| `max_length` | integer | 5000 | Maximum number of characters to return |
| `start_index` | integer | 0 | Start content from this character index |
| `raw` | boolean | false | Get raw content without markdown conversion |
| `ignore_robots_txt` | boolean | false | Ignore robots.txt restrictions |
| `proxy_url` | string | null | Proxy URL to use for requests |

## Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) package manager
- Dedalus API Key

## Setup

1. **Clone the repository**

```bash
git clone https://github.com/dedalus-labs/fetch-mcp.git
cd fetch-mcp
```

2. **Install dependencies**

```bash
uv sync
```

3. **Configure environment variables**

Create a `.env` file based on .env.example:

```bash
cp .env.example .env
```

## Running the Server

```bash
cd src
python main.py
```

The server will start on port 8080.

## Client Usage

### Using DedalusRunner

```python
import asyncio
import os

from dotenv import load_dotenv
from dedalus_labs import AsyncDedalus, DedalusRunner

load_dotenv()


async def main():
    client = AsyncDedalus(
        api_key=os.getenv("DEDALUS_API_KEY"),
        base_url=os.getenv("DEDALUS_API_URL"),
        as_base_url=os.getenv("DEDALUS_AS_URL"),
    )
    runner = DedalusRunner(client)

    result = await runner.run(
        input="Fetch the contents of https://example.com and summarize it.",
        model="openai/gpt-5",
        mcp_servers=["issac/fetch-mcp"],
    )

    print(result.output)

if __name__ == "__main__":
    asyncio.run(main())
```

## Security Note

> **Caution:** This server can access local/internal IP addresses and may represent a security risk. Exercise caution when using this MCP server to ensure this does not expose any sensitive data.

## License

MIT License - see [LICENSE](LICENSE) for details.
