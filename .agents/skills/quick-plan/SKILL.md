# Skill: quick-plan

Converted from: `.claude/commands/quick-plan.md`

## Metadata

```yaml
allowed-tools: Read, Write, Edit, Glob, Grep, MultiEdit
description: Creates a concise engineering implementation plan based on user requirements and saves it to specs directory
argument-hint: [user prompt]
model: opus
```


# Quick Plan

Create a detailed implementation plan based on the user's requirements provided through the `USER_PROMPT` variable. Analyze the request, think through the implementation approach, and save a comprehensive specification document to `PLAN_OUTPUT_DIRECTORY/<name-of-plan>.md` that can be used as a blueprint for actual development work.

## Variables

USER_PROMPT: $ARGUMENTS
PLAN_OUTPUT_DIRECTORY: `specs/`

## Instructions

- Carefully analyze the user's requirements provided in the USER_PROMPT variable
- Think deeply (ultrathink) about the best approach to implement the requested functionality or solve the problem
- Create a concise implementation plan that includes:
  - Clear problem statement and objectives
  - Technical approach and architecture decisions
  - Step-by-step implementation guide
  - Potential challenges and solutions
  - Testing strategy
  - Success criteria
- Generate a descriptive, kebab-case filename based on the main topic of the plan
- Save the complete implementation plan to `PLAN_OUTPUT_DIRECTORY/<descriptive-name>.md`
- Ensure the plan is detailed enough that another developer could follow it to implement the solution
- Include code examples or pseudo-code where appropriate to clarify complex concepts
- Consider edge cases, error handling, and scalability concerns
- Structure the document with clear sections and proper markdown formatting
- **Project-specific**: This is a Python LangGraph multi-agent system for Ukrainian public-procurement (ЕСЗ / Prozorro) support. Source of truth: `README.md` (in Ukrainian) + `CLAUDE.md`. Root-level modules: `agent.py` (graph wiring), `schemas.py` (Pydantic contracts: `ResearchPlan`, `SubTask`, `WorkerResponse`, `CritiqueResult`, `EscalationOutput`), `retriever.py` (hybrid retrieval over `laws` + `articles` collections), `ingest.py`, `tools.py` (Tavily UA web search, knowledge_search), `config.py` (Pydantic `Settings` from `.env`), `main.py` (REPL). Preserve invariants: three-domain scope (`technical_system` / `procurement_general` / `legal`), defense-in-depth off-topic filtering, two separate RAG collections, Critic targeted-`revise` loop, two escalation paths (Planner `needs_human=true` OR Critic exhaust → `EscalationOutput` to Slack + audit-trail). Prompts live in Langfuse at runtime; `prompts/` is a backup.

## Workflow

1. Analyze Requirements - THINK HARD and parse the USER_PROMPT to understand the core problem and desired outcome
2. Design Solution - Develop technical approach including architecture decisions and implementation strategy
3. Document Plan - Structure a comprehensive markdown document with problem statement, implementation steps, and testing approach
4. Generate Filename - Create a descriptive kebab-case filename based on the plan's main topic
5. Save & Report - Write the plan to `PLAN_OUTPUT_DIRECTORY/<filename>.md` and provide a summary of key components

## Plan Format

Follow this format when creating implementation plans:

```md
# Plan: <task name>

## Task Description
<describe the task in detail based on the prompt>

## Objective
<clearly state what will be accomplished when this plan is complete>

## Problem Statement
<clearly define the specific problem or opportunity this task addresses>

## Solution Approach
<describe the proposed solution approach and how it addresses the objective>

### Architecture Decisions
- **Affected graph nodes**: which of Supervisor / Planner / Lawyer / Common Support / Technical Support / Critic / Escalation will change — and why
- **Schemas**: new or changed Pydantic models in `schemas.py` (state shape, worker I/O)
- **RAG collection(s)**: `laws` / `articles` (with filter) / both / neither — with rationale
- **External calls**: Tavily / web fetch / Slack escalation — note rate limits and timeouts
- **Sessions / persistence**: any change to `PostgresSaver` checkpoint format or session-key shape
- **Prompt source**: which Langfuse prompt(s) are added/edited; mirror change in `prompts/`

## Relevant Files
Use these files to complete the task:

<list files relevant to the task with bullet points explaining why. Include new files to be created under an h3 'New Files' section if needed>

## Implementation Phases
IMPORTANT: Each phase should be a checkbox that will be checked off during implementation. Include Status and Comments fields for tracking progress.

- [ ] **Phase 1: Foundation** - <describe any foundational work needed>
  - Status:
  - Comments:

- [ ] **Phase 2: Core Implementation** - <describe the main implementation work>
  - Status:
  - Comments:

- [ ] **Phase 3: Integration & Polish** - <describe integration, testing, and final touches>
  - Status:
  - Comments:

## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom. Each task should be a checkbox that will be checked off during implementation. Include Status and Comments fields for tracking progress.

<list step by step tasks as checkboxes with h3 headers for grouping. Format each task as:>
- [ ] **Task description** - <detailed explanation>
  - Status:
  - Comments:

<Use h3 headers to organize tasks by category. Start with foundational changes then specific implementation. Last step should validate the work.>

### 1. <Category Name>
- [ ] **<Task Name>** - <specific action>
  - Status:
  - Comments:

### 2. <Category Name>
- [ ] **<Task Name>** - <specific action>
  - Status:
  - Comments:

<continue with additional tasks as needed>

## Testing Strategy
<describe testing approach, including unit tests and edge cases as applicable>

## Acceptance Criteria
<list specific, measurable criteria that must be met for the task to be considered complete>

## Validation Commands
Execute these commands to validate the task is complete:

<list specific commands to validate the work. Be precise about what to run>
- `python -m py_compile agent.py ingest.py retriever.py tools.py main.py config.py` — syntax check
- `python -c "from agent import agent; print(type(agent))"` — graph imports cleanly
- `pytest tests/ -q` — unit tests
- `deepeval test run tests/eval/` — LLM evaluation
- `python ingest.py` — rebuild index (only if `data/` or chunking changed)

## Notes
<optional additional context, considerations, or dependencies. If new libraries are needed, install with `pip install <pkg>` and add the pinned version to `requirements.txt`.>
```

## Report

After creating and saving the implementation plan, provide a concise report with the following format:

```
✅ Implementation Plan Created

File: PLAN_OUTPUT_DIRECTORY/<filename>.md
Topic: <brief description of what the plan covers>
Key Components:
- <main component 1>
- <main component 2>
- <main component 3>
```
