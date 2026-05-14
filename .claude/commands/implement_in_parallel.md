---
model: opus
description: Use when you have a plan file and need to implement it using parallel build-agents for efficiency
argument-hint: [path-to-plan]
---

# Implement in Parallel

Follow the `Workflow` to implement the `PATH_TO_PLAN` by delegating individual file creation to specialized build-agents in parallel, then `Report` the completed work.

## Variables

PATH_TO_PLAN: $ARGUMENTS

## Codebase Structure

The build-agent sub-agent is located at `.claude/agents/build-agent.md` and is specialized for writing individual files based on detailed specifications.

## Instructions

- **Never guess or assume context**: Each build-agent needs comprehensive instructions as if they are new engineers
- **Provide verbose specifications**: Include all relevant files, patterns, conventions, and examples
- **Launch agents in parallel**: Use a single message with multiple Task tool calls to maximize efficiency
- **One file per agent**: Each build-agent should focus on implementing ONE specific file
- **Include full context**: Specifications must include:
  - Exact file path
  - Complete functional requirements
  - Related files and their relationships
  - Code style and patterns to follow
  - Dependencies and imports needed
  - Example code or similar files to reference

## Project-Specific Context for Build Agents

Each build-agent specification MUST include these project conventions:

- **AppV3 architecture**: Business logic in `AppV3\[Domain]\`, infrastructure in `App\`
- **Thin models** (NO query scopes), **fat repositories** (ALL query logic), **service-to-service** communication
- **CacheManager** for caching (`usePersonalCache()/useSystemCache()/useCasinoCache()`), NOT Cache/Redis facades
- **TransactionRunner** for atomic operations
- **ValidationService + ValidatorConfig** for input validation
- **CoreJsonResource** for API responses, DTOs for 3+ parameters
- **Config defaults** ONLY in config files, NOT in `config()` second argument
- **Exceptions**: `LogicV3Exception` for user errors, `InternalLogicException` for internal
- **Routes** in `routes/api-v3.php`, middleware: `players`/`admins`, throttling via `throttler()`
- **Casino DB**: migrations in `database/migrations_casino/` with `DatabaseConnectionsEnum::MYSQL_CASINO`

### Validation Commands
```bash
docker compose exec app-backend ./vendor/bin/phpunit
docker compose exec app-backend php artisan migrate
```

## The Iron Law

```
NO COMPLETION CLAIM WITHOUT VERIFIED EVIDENCE
```

Claiming completion without running validation? Start over.

**No exceptions:**
- Don't claim "should work" - prove it works
- Don't trust individual agent reports alone - run project-wide checks
- Don't skip final verification "this once"
- Evidence or it didn't happen

## Verification Gate (MANDATORY)

BEFORE claiming implementation is complete:

1. **IDENTIFY**: What validation commands prove completion?
2. **RUN**: Execute EVERY validation command (fresh, complete)
3. **READ**: Full output - check exit codes, count failures
4. **VERIFY**: Does ALL output confirm success?
   - If NO: Fix issues, re-run, repeat
   - If YES: Include evidence in report
5. **ONLY THEN**: Claim completion

Skip any step = incomplete implementation. Return to Step 1.

**Evidence required for completion claim:**
- Validation command output (actual output, not "it passed")
- Test results with pass/fail counts
- Git diff summary
- All build-agent reports reviewed

## Red Flags - STOP Implementation

If any of these thoughts occur to you, STOP and reconsider:

- Launching agents without reading the plan thoroughly
- Skipping context gathering "to save time"
- "I'll verify after all agents finish"
- Trusting agent reports without project-wide checks
- "Just a small file, no need for full spec"
- Claiming completion before final verification
- Skipping failed agent re-runs

**If any of these apply: STOP. Follow the workflow properly.**

## Common Rationalizations

| Excuse | Reality |
|--------|---------|
| "Agent reports look good" | Individual success ≠ integrated success. Run full checks. |
| "All files were created" | Created ≠ working. Verify integration. |
| "Tests were passing earlier" | Previous runs prove nothing. Run again. |
| "Small change, skip the spec" | Agents need full context. Always provide specs. |
| "I'll fix integration issues later" | Later creates more work. Fix now. |

## Announcement (MANDATORY)

Before starting work, announce:

"I'm using /implement_in_parallel to implement the plan at [path]. I will provide complete specifications to each build-agent and verify all work before claiming completion."

This creates commitment. Skipping this step = likely to skip other steps.

## Workflow

### Step 1: Read and Analyze the Plan

- If no `PATH_TO_PLAN` is provided, STOP immediately and ask the user to provide it.

  **No exceptions:**
  - Don't infer the plan from conversation
  - Don't create an ad-hoc plan
  - Don't proceed without an explicit path
  - STOP means STOP

- Read the plan at `PATH_TO_PLAN`
- Analyze the plan thoroughly to understand:
  - All files that need to be created or modified
  - Dependencies between files
  - The overall architecture and flow
  - Code style and conventions mentioned

### Step 2: Gather Context for Specifications

- Read relevant existing files in the codebase to understand:
  - Coding patterns and conventions
  - Import styles and module organization
  - Error handling approaches
  - Documentation standards
  - Similar implementations that can serve as examples
- Use Grep/Glob to find related files that provide context
- Identify which files can be built in parallel vs which have dependencies

### Step 3: Create Detailed File Specifications

For each file that needs to be created/modified, create a comprehensive specification that includes:

```markdown
# File: [absolute/path/to/file.ext]

## Purpose
[What this file does and why it exists]

## Requirements
- [Detailed requirement 1]
- [Detailed requirement 2]
- [etc.]

## Related Files
- **[file-path]**: [how it relates and what to reference]
- [etc.]

## Code Style & Patterns
- [Pattern 1 to follow]
- [Pattern 2 to follow]
- [etc.]

## Dependencies
- [Import/dependency 1]
- [Import/dependency 2]
- [etc.]

## Example Code
[Provide similar code from the codebase or pseudocode example]

## Integration Points
[How this file connects with other parts of the system]

## Verification
[How to verify this file works: tests to run, type checks, etc.]
```

### Step 4: Identify Parallel vs Sequential Work

- Group files into batches based on dependencies:
  - **Batch 1**: Files with no dependencies (can be built in parallel)
  - **Batch 2**: Files that depend on Batch 1
  - **Batch 3**: Files that depend on Batch 2
  - [etc.]

### Step 5: Launch Build Agents in Parallel

For each batch (starting with Batch 1):

- Launch multiple build-agent instances in parallel using a **single message** with multiple Task tool calls
- Each Task tool call should:
  - Use `subagent_type: "build-agent"`
  - Provide the complete specification created in Step 3
  - Include all necessary context for that specific file
- Wait for all agents in the current batch to complete before moving to the next batch

Example of launching agents in parallel:
```
In a single message, make multiple Task tool calls:
- Task(subagent_type="build-agent", prompt="[Full spec for file1]")
- Task(subagent_type="build-agent", prompt="[Full spec for file2]")
- Task(subagent_type="build-agent", prompt="[Full spec for file3]")
```

### Step 6: Monitor and Collect Results

- Review the reports from each build-agent
- Identify any issues or concerns raised
- Note any deviations from specifications
- Check verification results (tests, type checks, etc.)

### Step 7: Handle Issues

- If any agents report problems:
  - Review the issue
  - Make necessary adjustments
  - Re-launch the specific agent with updated specifications if needed

### Step 8: Final Verification

- Run any project-wide checks (e.g., full test suite, build process)
- Verify all files integrate correctly
- Check that all requirements from the plan are met

## Report

Your final report should include:

### Summary
- Brief overview of what was implemented
- Number of files created/modified
- Any significant architectural decisions made

### File-by-File Breakdown
For each file:
- **Path**: [file path]
- **Status**: ✅ Created | ⚠️ Created with issues | ❌ Failed
- **Summary**: [Brief summary from build-agent report]
- **Issues**: [Any issues or concerns]

### Verification Results
```bash
git diff --stat
```

### Overall Status
- **Total Files**: [number]
- **Successful**: [number]
- **Issues**: [number]
- **Failed**: [number]

### Recommendations
- [Any follow-up work needed]
- [Suggestions for testing]
- [Other recommendations]
