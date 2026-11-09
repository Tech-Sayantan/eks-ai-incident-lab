import asyncio
import os
import sys
from pathlib import Path

from mcp import Client, StdioServerParameters


async def fetch_rollout_report(*, verbose: bool = True) -> str:
    url = os.getenv("ORDERS_MCP_URL")
    target: str | StdioServerParameters
    if url:
        target = url
        if verbose:
            print("Transport: Streamable HTTP", flush=True)
    else:
        script = Path(__file__).resolve()
        target = StdioServerParameters(
            command=sys.executable,
            args=[str(script.with_name("orders_mcp_server.py"))],
            cwd=str(script.parents[2]),
        )

    async with Client(target, read_timeout_seconds=10) as client:
        if verbose:
            listing = await client.list_tools()
            print("Discovered:", [tool.name for tool in listing.tools])

        result = await client.call_tool("orders_rollout", {})
        if result.is_error:
            raise RuntimeError(f"MCP tool failed: {result.content}")

        if not result.content or result.content[0].type != "text":
            raise RuntimeError("MCP did not return a text rollout report")
        return result.content[0].text


async def main():
    report = await fetch_rollout_report()
    print("Tool returned:", report)


if __name__ == "__main__":
    asyncio.run(main())
