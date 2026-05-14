# Skill: configure_subagents_for_cursor

Converted from: `.claude/commands/configure_subagents_for_cursor.md`

## Metadata

```yaml
description: Configure sub-agents-mcp to enable Claude Code-style subagents in Cursor IDE using agents from .claude/agents/
allowed-tools: Bash, Read, Write, Edit, Glob, AskUserQuestion
```


# Configure Subagents for Cursor

> Enable Claude Code-style subagents in Cursor IDE using `sub-agents-mcp` with `cursor-agent` backend. No Claude Code or Anthropic API required - uses your existing Cursor subscription.

## How It Works

```
Your prompt → Cursor AI → sub-agents-mcp → cursor-agent CLI → Same Cursor AI
                                              (isolated context)
```

Each agent runs with fresh context, preventing pollution of your main conversation.

## Variables

CURSOR_MCP_CONFIG_PATH: ~/.cursor/mcp.json

## Workflow

### Phase 1: Check Node.js

1. Run `node --version` to check if Node.js is installed
2. If not installed, inform the user:
   - macOS: `brew install node`
   - Or use nvm: `curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash`
3. Require Node.js 18+ to proceed

### Phase 2: Install and Authenticate cursor-agent CLI

1. Check if cursor-agent is installed: `which cursor-agent`

2. If NOT installed, run:
   ```bash
   curl https://cursor.com/install -fsS | bash
   ```

3. Check authentication status and prompt user to authenticate if needed:
   ```bash
   cursor-agent login
   ```

   Note: Sessions can expire. Inform user to re-run `cursor-agent login` if they see auth errors later.

### Phase 3: Select Agents Directory

Use AskUserQuestion to ask which agents directory to use:

**Question:** Which agents directory should Cursor use?

**Options:**
1. **Project agents (Recommended)** - Use this project's `.claude/agents/` directory. Agents are specific to this project.
2. **Global agents** - Use `~/.claude/agents/` for personal agents available across all projects.

After selection, resolve to absolute path (e.g., `/Users/bohdan/Documents/coding-agents-settings/.claude/agents`).

**IMPORTANT:** The path MUST be absolute. Do not use `~` or relative paths.

### Phase 4: Configure MCP Server

1. Read existing MCP config if it exists:
   ```bash
   cat ~/.cursor/mcp.json 2>/dev/null
   ```

2. Parse existing config to preserve other MCP servers

3. Add or update the `sub-agents` server configuration:
   ```json
   {
     "mcpServers": {
       "sub-agents": {
         "command": "npx",
         "args": ["-y", "sub-agents-mcp"],
         "env": {
           "AGENTS_DIR": "<absolute-path-to-agents-directory>",
           "AGENT_TYPE": "cursor"
         }
       }
     }
   }
   ```

4. Write the merged config to `~/.cursor/mcp.json`

### Phase 5: Validate Agents

1. Use Glob to list all `.md` files in the selected agents directory
2. For each agent file, read and extract:
   - `name` from YAML frontmatter
   - `description` from YAML frontmatter
3. Build a table of available agents
4. Report any agents with missing required fields

### Phase 6: Generate Report

Output the final report in the format below.

## Report Format

```
# Cursor Subagents Configuration Complete

## Setup Summary
- Node.js: v<version>
- cursor-agent CLI: <Installed/Not Found>
- Agents Directory: <absolute-path>
- MCP Config: ~/.cursor/mcp.json

## Available Agents

| Agent | Description |
|-------|-------------|
| <name> | <description> |
| ... | ... |

## Usage in Cursor

After restarting Cursor, use these prompts:

### Analyze Code (Read-Only)
"Use the scout-report-suggest agent to find performance issues in src/api/"

### Implement a File
"Use the build-agent to create a UserService class at src/services/user.ts with CRUD operations"

### Create a Plan
"Use the planner agent to plan implementing authentication"

### Generate New Agent
"Use the meta-agent to create a test-writer agent"

## Next Steps

1. **RESTART CURSOR IDE** (required for MCP changes to take effect)
2. Test with: "Use the scout-report-suggest agent to analyze this codebase"

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Auth errors | Run `cursor-agent login` again |
| Agent not found | Verify AGENTS_DIR is absolute path in ~/.cursor/mcp.json |
| Timeout on complex tasks | Tasks >5min may timeout - break into smaller tasks |
| MCP not loading | Check ~/.cursor/mcp.json for JSON syntax errors |
| "sub-agents" tool not available | Restart Cursor after config changes |
```
