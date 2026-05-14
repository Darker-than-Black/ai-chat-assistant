# MCP and ACP overview (NOT used in this project)

## Status: out of scope

This file exists for reference only — to recognize MCP/ACP terminology when reading external material, and to remember why we deliberately *don't* use them here.

**This project does not use MCP or ACP.** All agents are in-process, all tools are LangChain `@tool` functions called directly. Don't introduce these protocols without an architectural reason.

## What they are

**MCP (Model Context Protocol)** — Anthropic's standard for exposing tools/resources/prompts to LLMs over a JSON-RPC protocol. Splits "the model" from "the tools" so any MCP-capable host can use any MCP server.

```
[LLM Host] ── MCP Client ──► MCP Server ──► [Tools, Resources]
```

Practical impact: instead of writing `@tool` Python functions in your codebase, you run a separate MCP server (locally or remote) and any client can discover + call its tools.

**ACP (Agent Communication Protocol)** — IBM/BeeAI's protocol for agent-to-agent communication. Same idea, one level up: instead of a host calling a tool, an agent calls another agent over HTTP with a standardized message envelope.

```
[Agent A] ── ACP Client ──► ACP Server ──► [Agent B]
```

## Why we don't use them

- **Single-process simplicity.** Our system is one Python service. MCP/ACP make sense for distributed setups, multi-team boundaries, or when third parties need to plug their tools into your agent. None of that applies to a course project.
- **Coordination overhead.** Each protocol = network hop + serialization + auth. We'd add complexity without reducing complexity elsewhere.
- **Library-first principle (`CLAUDE.md`).** LangChain `@tool` and LangGraph in-process delegation already cover everything we need.

## When they WOULD make sense (future)

- We want to expose `web_search` / `knowledge_search` to a third-party agent (Anthropic's Claude desktop app, for example).
- We want to scale individual workers independently and they're written in different languages or stacks.
- We need a marketplace of pluggable tools that aren't owned by us.

## Minimal "what it looks like" — FastMCP server

```python
from fastmcp import FastMCP

server = FastMCP(name="ProcurementSearch")

@server.tool()
def search_laws(query: str) -> str:
    """Search procurement laws."""
    return "..."

if __name__ == "__main__":
    server.run()   # exposes JSON-RPC endpoint
```

A consumer would connect via `fastmcp.Client(...)` and call `search_laws` remotely.

## Source

`lesson-9.md` — full lecture on both protocols. Read it only if you have a concrete reason to introduce them.
