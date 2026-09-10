#!/usr/bin/env python3
"""Check an actual resolved MCP config through initialize and tools/list."""
from __future__ import annotations
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path


async def probe(configuration: dict) -> dict:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    item = configuration["mcpServers"]["mathmodel"]
    if not Path(item["command"]).is_absolute() or not Path(item["args"][-1]).is_absolute():
        raise ValueError("Probe requires machine-resolved absolute launch paths")
    parameters = StdioServerParameters(command=item["command"], args=item["args"], cwd=item.get("cwd"), env={**os.environ, **item.get("env", {})})
    async with asyncio.timeout(30):
        async with stdio_client(parameters) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                result = await session.initialize()
                tools = await session.list_tools()
                names = {t.name for t in tools.tools}
                required = {"open_workspace", "get_context_packet", "get_status", "run_job", "get_job", "cancel_job", "read_artifact"}
                if not required <= names:
                    raise ValueError(f"Missing MCP tools: {sorted(required - names)}")
                return {"protocol_version": result.protocolVersion, "server": result.serverInfo.name, "tools": sorted(names)}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(asyncio.run(probe(json.loads(args.config.read_text(encoding="utf-8")))), ensure_ascii=False))


if __name__ == "__main__":
    main()
