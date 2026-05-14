---
description: Analyze repository structure and update all commands to work with this specific codebase
---

# Adapt Commands to Repository

> Analyze the current repository structure and update all commands in `.claude/commands/` to work with this specific codebase. Use interactive prompts when uncertain.

## Instructions

### Phase 1: Discovery

1. Run `git ls-files` to understand the project structure
2. Read `README.md` and any documentation files (CONTRIBUTING.md, docs/*)
3. Read config files: `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, etc.

### Phase 2: Identify & Confirm (Interactive)

For each of the following, attempt to auto-detect. If uncertain or multiple options exist, use AskUserQuestion to confirm with the user:

1. **Project Type**: Single app, monorepo, library, or other?
2. **Backend/Server Path**: Look for `server/`, `backend/`, `api/`, `src/`, `app/server/`
3. **Frontend/Client Path**: Look for `client/`, `frontend/`, `web/`, `app/client/`
4. **Scripts Path**: Look for `scripts/`, `bin/`, or package.json scripts
5. **Package Manager**: npm, yarn, pnpm, bun, uv, pip, poetry, cargo, go, etc.
6. **Test Command**: pytest, jest, vitest, cargo test, go test, etc.
7. **Start Command**: How to run the application (scripts, npm start, etc.)

### Phase 3: Update Commands (In Place)

#### Update plan.md, plan_w_scouters.md, quick-plan.md

Using the Edit tool, update these sections in each file:

- `## Relevant Files` - Replace paths with discovered paths for this repo (if present)
- `## Validation Commands` - Update test command (e.g., `cd <path> && <test_command>`)
- Package manager references (change `uv add` if using different package manager)

#### Update implement.md

Using the Edit tool, rewrite to:

- Use correct package manager commands for this repo
- Update test/build commands based on discovered config
- Update file paths to match repo structure

#### Update fix.md

Using the Edit tool, update to:

- Reference correct file paths for the repo
- Update any package manager or test commands

#### Update review.md

Using the Edit tool, update to:

- Reference correct file paths and patterns for the repo
- Update validation commands if present

### Phase 4: Preserve These Commands

Do NOT modify these commands (they are repository-agnostic):

- `prime.md`, `prime_cc.md`, `prime_specific_docs.md`
- `all_tools.md`, `ping.md`
- `question.md`, `question-w-mermaid-diagrams.md`
- `meta_prompt.md`
- `load_ai_docs.md`, `load_bundle.md`
- `find_and_summarize.md`
- `parallel_subagents.md`
- All orchestration commands (`orch_*.md`)
- `adapt.md` (this file)

## Report

After completing adaptation, report:

- Repository type and tech stack detected
- Commands updated and key changes made
- Any items that need manual review
