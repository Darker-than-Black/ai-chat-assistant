# Create .claude/commands Structure

> Automatically create the complete `.claude/commands/` directory structure with all command files for a new repository.

## Instructions

1. Create the `.claude/commands/` directory if it doesn't exist
2. Create all command files listed below with their exact content
3. Do NOT modify the content of any files
4. Report completion with list of created files

## Run

### Step 1: Create Directory Structure

```bash
mkdir -p .claude/commands
```

### Step 2: Create All Command Files

Create each file with the exact content specified below.

---

## Plan-Related Commands

---

#### File: `.claude/commands/plan.md`

```markdown
---
description: Creates a concise engineering implementation plan based on user requirements and saves it to specs directory
argument-hint: [user prompt]
---

# Quick Plan

Create a detailed implementation plan based on the user's requirements provided through the `USER_PROMPT` variable. Analyze the request, think through the implementation approach, and save a comprehensive specification document to `PLAN_OUTPUT_DIRECTORY/<name-of-plan>.md` that can be used as a blueprint for actual development work. Follow the `Instructions` and work through the `Workflow` to create the plan.

## Variables

USER_PROMPT: $1
PLAN_OUTPUT_DIRECTORY: `specs/`

## Instructions

- IMPORTANT: If no `USER_PROMPT` is provided, stop and ask the user to provide it.
- Carefully analyze the user's requirements provided in the USER_PROMPT variable
- Determine the task type (chore|feature|refactor|fix|enhancement) and complexity (simple|medium|complex)
- Think deeply (ultrathink) about the best approach to implement the requested functionality or solve the problem
- Explore the codebase to understand existing patterns and architecture
- Follow the Plan Format below to create a comprehensive implementation plan
- Include all required sections and conditional sections based on task type and complexity
- Generate a descriptive, kebab-case filename based on the main topic of the plan
- Save the complete implementation plan to `PLAN_OUTPUT_DIRECTORY/<descriptive-name>.md`
- Ensure the plan is detailed enough that another developer could follow it to implement the solution
- Include code examples or pseudo-code where appropriate to clarify complex concepts
- Consider edge cases, error handling, and scalability concerns
- Use `AskUserQuestion` tool ONLY when there's genuine ambiguity or a critical decision point - avoid asking questions just to appear thorough. If the requirements are clear from the USER_PROMPT and codebase exploration, proceed directly with planning.

## Workflow

1. Analyze Requirements - THINK HARD and parse the USER_PROMPT to understand the core problem and desired outcome
2. Explore Codebase - Understand existing patterns, architecture, and relevant files
3. Design Solution - Develop technical approach including architecture decisions and implementation strategy
4. Document Plan - Structure a comprehensive markdown document with problem statement, implementation steps, and testing approach
5. Generate Filename - Create a descriptive kebab-case filename based on the plan's main topic
6. Save & Report - Follow the `Report` section to write the plan to `PLAN_OUTPUT_DIRECTORY/<filename>.md` and provide a summary of key components

## Plan Format

Follow this format when creating implementation plans:

` ` `md
# Plan: <task name>

## Task Description
<describe the task in detail based on the prompt>

## Objective
<clearly state what will be accomplished when this plan is complete>

<if task_type is feature or complexity is medium/complex, include these sections:>
## Problem Statement
<clearly define the specific problem or opportunity this task addresses>

## Solution Approach
<describe the proposed solution approach and how it addresses the objective>
</if>

## Relevant Files
Use these files to complete the task:

<list files relevant to the task with bullet points explaining why. Include new files to be created under an h3 'New Files' section if needed>

<if complexity is medium/complex, include this section:>
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
</if>

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

<if task_type is feature or complexity is medium/complex, include this section:>
## Testing Strategy
<describe testing approach, including unit tests and edge cases as applicable>
</if>

## Acceptance Criteria
<list specific, measurable criteria that must be met for the task to be considered complete>

## Validation Commands
Execute these commands to validate the task is complete:

<list specific commands to validate the work. Be precise about what to run>
- Example: `uv run python -m py_compile src/*.py` - Test to ensure the code compiles

## Notes
<optional additional context, considerations, or dependencies. If new libraries are needed, specify using `uv add`>
` ` `

## Report

After creating and saving the implementation plan, provide a concise report with the following format:

` ` `
✅ Implementation Plan Created

File: PLAN_OUTPUT_DIRECTORY/<filename>.md
Topic: <brief description of what the plan covers>
Key Components:
- <main component 1>
- <main component 2>
- <main component 3>
` ` `
```

---

#### File: `.claude/commands/plan_w_scouters.md`

```markdown
---
description: Creates a concise engineering implementation plan based on user requirements and saves it to specs directory
argument-hint: [user prompt]
---

# Quick Plan

Create a detailed implementation plan based on the user's requirements provided through the `USER_PROMPT` variable. Analyze the request, think through the implementation approach, and save a comprehensive specification document to `PLAN_OUTPUT_DIRECTORY/<name-of-plan>.md` that can be used as a blueprint for actual development work. Follow the `Instructions` and work through the `Workflow` to create the plan.

## Variables

USER_PROMPT: $1
PLAN_OUTPUT_DIRECTORY: `specs/`
TOTAL_BASE_SCOUT_SUBAGENTS: 3
TOTAL_FAST_SCOUT_SUBAGENTS: 5

## Instructions

- IMPORTANT: If no `USER_PROMPT` is provided, stop and ask the user to provide it.
- Carefully analyze the user's requirements provided in the USER_PROMPT variable
- Determine the task type (chore|feature|refactor|fix|enhancement) and complexity (simple|medium|complex)
- Think deeply (ultrathink) about the best approach to implement the requested functionality or solve the problem
- Explore the codebase to understand existing patterns and architecture
- Follow the Plan Format below to create a comprehensive implementation plan
- Include all required sections and conditional sections based on task type and complexity
- Generate a descriptive, kebab-case filename based on the main topic of the plan
- Save the complete implementation plan to `PLAN_OUTPUT_DIRECTORY/<descriptive-name>.md`
- Ensure the plan is detailed enough that another developer could follow it to implement the solution
- Include code examples or pseudo-code where appropriate to clarify complex concepts
- Consider edge cases, error handling, and scalability concerns
- Use `AskUserQuestion` tool ONLY when there's genuine ambiguity or a critical decision point - avoid asking questions just to appear thorough. If the requirements are clear from the USER_PROMPT and codebase exploration, proceed directly with planning.

## Workflow

1. Analyze Requirements - THINK HARD and parse the USER_PROMPT to understand the core problem and desired outcome
2. Explore Codebase - Understand existing patterns, architecture, and relevant files. Deploy a total of `TOTAL_BASE_SCOUT_SUBAGENTS + TOTAL_FAST_SCOUT_SUBAGENTS` subagents in PARALLEL to scout the codebase for files needed to complete the task.
   1. Run `TOTAL_BASE_SCOUT_SUBAGENTS` @agent-scout-report-suggest agents in parallel to scout the codebase for files needed to complete the task. Give each different direction, divide and conquer.
   2. Run `TOTAL_FAST_SCOUT_SUBAGENTS` @agent-scout-report-suggest-fast agents in parallel to scout the codebase for files needed to complete the task. Give each different direction, divide and conquer.
   3. Gather the results from the subagents and consolidate them into a single list of files needed to complete the task.
   4. Validate the files - consolidate the results from the subagents and then MANUALLY validate, double check, and look for any missing files needed to complete the task.
4. Design Solution - Develop technical approach including architecture decisions and implementation strategy
5. Document Plan - Structure a comprehensive markdown document with problem statement, implementation steps, and testing approach
6. Generate Filename - Create a descriptive kebab-case filename based on the plan's main topic
7. Save & Report - Follow the `Report` section to write the plan to `PLAN_OUTPUT_DIRECTORY/<filename>.md` and provide a summary of key components

## Plan Format

Follow this format when creating implementation plans:

` ` `md
# Plan: <task name>

## Task Description
<describe the task in detail based on the prompt>

## Objective
<clearly state what will be accomplished when this plan is complete>

<if task_type is feature or complexity is medium/complex, include these sections:>
## Problem Statement
<clearly define the specific problem or opportunity this task addresses>

## Solution Approach
<describe the proposed solution approach and how it addresses the objective>
</if>

## Relevant Files
Use these files to complete the task:

<list files relevant to the task with bullet points explaining why. Include new files to be created under an h3 'New Files' section if needed>

<if complexity is medium/complex, include this section:>
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
</if>

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

<if task_type is feature or complexity is medium/complex, include this section:>
## Testing Strategy
<describe testing approach, including unit tests and edge cases as applicable>
</if>

## Acceptance Criteria
<list specific, measurable criteria that must be met for the task to be considered complete>

## Validation Commands
Execute these commands to validate the task is complete:

<list specific commands to validate the work. Be precise about what to run>
- Example: `uv run python -m py_compile src/*.py` - Test to ensure the code compiles

## Notes
<optional additional context, considerations, or dependencies. If new libraries are needed, specify using `uv add`>
` ` `

## Report

After creating and saving the implementation plan, provide a concise report with the following format:

` ` `
✅ Implementation Plan Created

File: PLAN_OUTPUT_DIRECTORY/<filename>.md
Topic: <brief description of what the plan covers>
Key Components:
- <main component 1>
- <main component 2>
- <main component 3>
` ` `
```

---

#### File: `.claude/commands/quick-plan.md`

```markdown
---
allowed-tools: Read, Write, Edit, Glob, Grep, MultiEdit
description: Creates a concise engineering implementation plan based on user requirements and saves it to specs directory
argument-hint: [user prompt]
model: opus
---

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

## Workflow

1. Analyze Requirements - THINK HARD and parse the USER_PROMPT to understand the core problem and desired outcome
2. Design Solution - Develop technical approach including architecture decisions and implementation strategy
3. Document Plan - Structure a comprehensive markdown document with problem statement, implementation steps, and testing approach
4. Generate Filename - Create a descriptive kebab-case filename based on the plan's main topic
5. Save & Report - Write the plan to `PLAN_OUTPUT_DIRECTORY/<filename>.md` and provide a summary of key components

## Plan Format

Follow this format when creating implementation plans:

` ` `md
# Plan: <task name>

## Task Description
<describe the task in detail based on the prompt>

## Objective
<clearly state what will be accomplished when this plan is complete>

## Problem Statement
<clearly define the specific problem or opportunity this task addresses>

## Solution Approach
<describe the proposed solution approach and how it addresses the objective>

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
- Example: `uv run python -m py_compile src/*.py` - Test to ensure the code compiles

## Notes
<optional additional context, considerations, or dependencies. If new libraries are needed, specify using `uv add`>
` ` `

## Report

After creating and saving the implementation plan, provide a concise report with the following format:

` ` `
✅ Implementation Plan Created

File: PLAN_OUTPUT_DIRECTORY/<filename>.md
Topic: <brief description of what the plan covers>
Key Components:
- <main component 1>
- <main component 2>
- <main component 3>
` ` `
```

---

## Build/Implementation Commands

---

#### File: `.claude/commands/implement.md`

```markdown
---
description: Implement the codebase based on the plan
argument-hint: [path-to-plan]
---

# Implement Commands

Follow the `Workflow` to implement the `PATH_TO_PLAN` then `Report` the completed work.

## Instructions

- IMPORTANT: Implement the plan top to bottom, in order. Do not skip any steps. Do not stop in between steps. Complete every step in the plan before stopping.
  - Make your best guess judgement based on the plan, everything will be detailed there.
  - If you have not run any validation commands throughout your implementation, DO NOT STOP until you have validated the work.
  - Your implementation should end with executing the validation commands to validate the work, if there are issues, fix them before stopping.

## Variables

PATH_TO_PLAN: $ARGUMENTS

## Workflow

- If no `PATH_TO_PLAN` is provided, STOP immediately and ask the user to provide it.
- Read the plan at `PATH_TO_PLAN`. Ultrathink about the plan and IMPLEMENT it into the codebase.
  - Implement the entire plan top to bottom before stopping.

## Report

- Summarize the work you've just done in a concise bullet point list.
- Report the files and total lines changed with `git diff --stat`
```

---

#### File: `.claude/commands/implement_in_parallel.md`

```markdown
---
model: opus
description: Build the codebase in parallel by delegating file creation to build-agents
argument-hint: [path-to-plan]
---

# Build in Parallel

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

## Workflow

### Step 1: Read and Analyze the Plan

- If no `PATH_TO_PLAN` is provided, STOP immediately and ask the user to provide it
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

` ` `markdown
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
` ` `

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
` ` `
In a single message, make multiple Task tool calls:
- Task(subagent_type="build-agent", prompt="[Full spec for file1]")
- Task(subagent_type="build-agent", prompt="[Full spec for file2]")
- Task(subagent_type="build-agent", prompt="[Full spec for file3]")
` ` `

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
` ` `bash
git diff --stat
` ` `

### Overall Status
- **Total Files**: [number]
- **Successful**: [number]
- **Issues**: [number]
- **Failed**: [number]

### Recommendations
- [Any follow-up work needed]
- [Suggestions for testing]
- [Other recommendations]
```

---

#### File: `.claude/commands/fix.md`

```markdown
---
allowed-tools: Write, Read, Bash, Grep, Glob, Edit, Task
description: Fix issues identified in a code review report by implementing recommended solutions
argument-hint: [user prompt describing work], [path to plan file], [path to review report]
model: opus
---

# Fix Agent

## Purpose

You are a specialized code fix agent. Your job is to read a code review report, understand the original requirements and plan, and systematically fix all identified issues. You implement the recommended solutions from the review, starting with Blockers and High Risk items, then working down to Medium and Low Risk items. You validate each fix and ensure the codebase passes all acceptance criteria.

## Variables

USER_PROMPT: $1
PLAN_PATH: $2
REVIEW_PATH: $3
FIX_OUTPUT_DIRECTORY: `app_fix_reports/`

## Instructions

- **CRITICAL**: You ARE building and fixing code. Your job is to IMPLEMENT solutions.
- If no `USER_PROMPT` or `REVIEW_PATH` is provided, STOP immediately and ask the user to provide them.
- Read the review report at REVIEW_PATH to understand what issues need to be fixed.
- Read the plan at PLAN_PATH to understand the original implementation intent.
- Prioritize fixes by risk tier: Blockers first, then High Risk, Medium Risk, and finally Low Risk.
- For each issue, implement the recommended solution (prefer the first/primary solution).
- After fixing each issue, verify the fix works as expected.
- Run validation commands from the original plan to ensure nothing is broken.
- Create a fix report documenting what was changed and how each issue was resolved.
- If a recommended solution doesn't work, try alternative solutions or document why it couldn't be fixed.
- Be thorough but efficient—fix issues correctly the first time.

## Workflow

1. **Read the Review Report** - Parse the review at REVIEW_PATH to extract all issues organized by risk tier. Note the file paths, line numbers, and recommended solutions for each issue.

2. **Read the Plan** - Review the plan at PLAN_PATH to understand the original requirements, acceptance criteria, and validation commands.

3. **Read the Original Prompt** - Understand the USER_PROMPT to keep the original intent in mind while making fixes.

4. **Fix Blockers** - For each BLOCKER issue:
   - Read the affected file to understand the context
   - Implement the primary recommended solution
   - If the primary solution fails, try alternative solutions
   - Verify the fix resolves the issue
   - Document what was changed

5. **Fix High Risk Issues** - For each HIGH RISK issue:
   - Follow the same process as Blockers
   - These should be fixed before considering the work complete

6. **Fix Medium Risk Issues** - For each MEDIUM RISK issue:
   - Implement recommended solutions
   - These improve code quality but may be deferred if time-critical

7. **Fix Low Risk Issues** - For each LOW RISK issue:
   - Implement if time permits
   - Document any skipped items with rationale

8. **Run Validation** - Execute all validation commands from the original plan:
   - Build/compile commands
   - Test commands
   - Linting commands
   - Type checking commands

9. **Verify Review Issues Resolved** - For each issue that was fixed:
   - Confirm the fix addresses the root cause
   - Check that no new issues were introduced

10. **Generate Fix Report** - Create a comprehensive report following the Report format below. Write to `FIX_OUTPUT_DIRECTORY/fix_<timestamp>.md`.

## Report

Your fix report must follow this exact structure:

` ` `markdown
# Fix Report

**Generated**: [ISO timestamp]
**Original Work**: [Brief summary from USER_PROMPT]
**Plan Reference**: [PLAN_PATH]
**Review Reference**: [REVIEW_PATH]
**Status**: ✅ ALL FIXED | ⚠️ PARTIAL | ❌ BLOCKED

---

## Executive Summary

[2-3 sentence overview of what was fixed and the current state of the codebase]

---

## Fixes Applied

### 🚨 BLOCKERS Fixed

#### Issue #1: [Issue Title from Review]

**Original Problem**: [What was wrong]

**Solution Applied**: [Which recommended solution was used]

**Changes Made**:
- File: `[path/to/file.ext]`
- Lines: `[XX-YY]`

**Code Changed**:
` ` `[language]
// Before
[original code]

// After
[fixed code]
` ` `

**Verification**: [How it was verified to work]

---

### ⚠️ HIGH RISK Fixed

[Same structure as Blockers]

---

### ⚡ MEDIUM RISK Fixed

[Same structure, can be more concise]

---

### 💡 LOW RISK Fixed

[Same structure, can be brief]

---

## Skipped Issues

[List any issues that were NOT fixed with rationale]

| Issue | Risk Level | Reason Skipped |
| ----- | ---------- | -------------- |
| [Issue description] | MEDIUM | [Why it was skipped] |

---

## Validation Results

### Validation Commands Executed

| Command | Result | Notes |
| ------- | ------ | ----- |
| `[command]` | ✅ PASS / ❌ FAIL | [Any relevant notes] |

---

## Files Changed

[Summary of all files modified]

| File | Changes | Lines +/- |
| ---- | ------- | --------- |
| `[path/to/file.ext]` | [Brief description] | +X / -Y |

---

## Final Status

**All Blockers Fixed**: [Yes/No]
**All High Risk Fixed**: [Yes/No]
**Validation Passing**: [Yes/No]

**Overall Status**: [✅ ALL FIXED / ⚠️ PARTIAL / ❌ BLOCKED]

**Next Steps** (if any):
- [Remaining action items]
- [Follow-up tasks]

---

**Report File**: `FIX_OUTPUT_DIRECTORY/fix_[timestamp].md`
` ` `

## Important Notes

- Always start with Blockers - these must be fixed for the code to be functional
- If a fix introduces new issues, document and address them
- Use git diff to show exactly what changed
- Test each fix before moving to the next issue
- If you cannot fix an issue, clearly document why and suggest next steps
- The goal is to get the codebase to a state where it passes review
```

---

#### File: `.claude/commands/review.md`

```markdown
---
allowed-tools: Write, Read, Bash, Grep, Glob
description: Reviews completed work by analyzing git diffs and produces risk-tiered validation reports
argument-hint: [user prompt describing work], [path to plan file]
model: opus
---

# Review Agent

## Purpose

You are a specialized code review and validation agent. Analyze completed work using git diffs, identify potential issues across four risk tiers (Blockers, High Risk, Medium Risk, Low Risk), and produce comprehensive validation reports. You operate in ANALYSIS AND REPORTING mode—you do NOT build, modify, or fix code. Your output is a structured report that helps engineers understand what needs attention.

## Variables

USER_PROMPT: $1
PLAN_PATH: $2
REVIEW_OUTPUT_DIRECTORY: `app_review/`

## Instructions

- **CRITICAL**: You are NOT building anything. Your job is to ANALYZE and REPORT only.
- If no `USER_PROMPT` is provided, STOP immediately and ask the user to provide it.
- Focus on validating work against the USER_PROMPT requirements and the plan at PLAN_PATH.
- Use `git diff` extensively to understand exactly what changed in the codebase.
- Categorize every issue into one of four risk tiers: Blocker, High Risk, Medium Risk, or Low Risk.
- For each issue, provide 1-3 recommended solutions. Use just 1 solution if it's obvious, up to 3 if there are multiple valid approaches.
- Include exact file paths, line numbers, and offending code snippets for every issue.
- Write all reports to the `REVIEW_OUTPUT_DIRECTORY` with timestamps for traceability.
- End every report with a clear PASS or FAIL verdict based on whether blockers exist.
- Never make assumptions—if you can't verify something through git diff or file inspection, flag it as requiring manual review.
- Be thorough but concise—engineers need actionable insights, not verbose commentary.

## Workflow

1. **Parse the USER_PROMPT** - Extract the description of work that was completed, identify the scope of changes, note any specific requirements or acceptance criteria mentioned, determine what files or modules were likely affected.

2. **Read the Plan** - If `PLAN_PATH` is provided, read the plan file to understand what was supposed to be implemented. Compare the implementation against the plan's acceptance criteria and validation commands.

3. **Analyze Git Changes** - Run `git status` to see current state, `git diff` to see unstaged changes, `git diff --staged` to see staged changes, `git log -1 --stat` to see the most recent commit if applicable, `git diff HEAD~1` if changes were already committed. Identify all files that were added, modified, or deleted. Note the magnitude of changes (line counts, file counts).

4. **Inspect Changed Files** - Use Read to examine each modified file in full context. Use Grep to search for potential anti-patterns or red flags: hardcoded credentials or secrets, TODO/FIXME comments introduced, commented-out code blocks, missing error handling, console.log or debug statements left in production code. Use Glob to find related files that might be affected by changes. Check for consistency with existing codebase patterns.

5. **Categorize Issues by Risk Tier** - Use these criteria:

   **BLOCKER (Critical - Must Fix Before Merge)**
   - Security vulnerabilities (exposed secrets, SQL injection, XSS)
   - Breaking changes to public APIs without deprecation
   - Data loss or corruption risks
   - Critical bugs that crash the application
   - Missing required migrations or database schema mismatches
   - Hardcoded production credentials

   **HIGH RISK (Should Fix Before Merge)**
   - Performance regressions or inefficient algorithms
   - Missing error handling in critical paths
   - Race conditions or concurrency issues
   - Incomplete feature implementation (partially implemented requirements)
   - Memory leaks or resource exhaustion risks
   - Breaking changes to internal APIs without migration path
   - Missing or inadequate logging for critical operations

   **MEDIUM RISK (Fix Soon)**
   - Code duplication or violation of DRY principle
   - Inconsistent naming conventions or code style
   - Missing unit tests for new functionality
   - Technical debt introduced (complex logic without comments)
   - Suboptimal architecture or design patterns
   - Missing input validation on non-critical paths
   - Inadequate documentation for complex functions

   **LOW RISK (Nice to Have)**
   - Minor code style inconsistencies
   - Opportunities for minor refactoring
   - Missing JSDoc/docstring comments
   - Non-critical type safety improvements
   - Overly verbose or complex code that could be simplified
   - Minor performance optimizations
   - Cosmetic improvements to error messages

6. **Document Each Issue with Precision** - For every issue identified, capture: Description (clear, concise summary), Location (absolute file path, specific line numbers), Code (exact offending code snippet), Solutions (1-3 actionable recommendations ranked by preference).

7. **Generate the Report** - Structure your report following the Report section format below. Start with a quick-reference summary table, organize issues by risk tier (Blockers first, Low Risk last), within each tier order by file path for easy navigation, include a final Pass/Fail verdict, write the report to `REVIEW_OUTPUT_DIRECTORY/review_<timestamp>.md`.

8. **Deliver the Report** - Confirm the report file was written successfully, provide a summary of findings to the user, indicate the Pass/Fail verdict clearly, suggest next steps if the review failed.

## Report

Your report must follow this exact structure:

` ` `markdown
# Code Review Report

**Generated**: [ISO timestamp]
**Reviewed Work**: [Brief summary from USER_PROMPT]
**Plan Reference**: [PLAN_PATH if provided]
**Git Diff Summary**: [X files changed, Y insertions(+), Z deletions(-)]
**Verdict**: ⚠️ FAIL | ✅ PASS

---

## Executive Summary

[2-3 sentence overview of the review, highlighting critical findings and overall code quality]

---

## Quick Reference

| #   | Description               | Risk Level | Recommended Solution             |
| --- | ------------------------- | ---------- | -------------------------------- |
| 1   | [Brief issue description] | BLOCKER    | [Primary solution in 5-10 words] |
| 2   | [Brief issue description] | HIGH       | [Primary solution in 5-10 words] |
| 3   | [Brief issue description] | MEDIUM     | [Primary solution in 5-10 words] |
| ... | ...                       | ...        | ...                              |

---

## Issues by Risk Tier

### 🚨 BLOCKERS (Must Fix Before Merge)

#### Issue #1: [Issue Title]

**Description**: [Clear explanation of what's wrong and why it's a blocker]

**Location**:
- File: `[absolute/path/to/file.ext]`
- Lines: `[XX-YY]`

**Offending Code**:
` ` `[language]
[exact code snippet showing the issue]
` ` `

**Recommended Solutions**:
1. **[Primary Solution]** (Preferred)
   - [Step-by-step explanation]
   - Rationale: [Why this is the best approach]

2. **[Alternative Solution]** (If applicable)
   - [Step-by-step explanation]
   - Trade-off: [What you gain/lose with this approach]

---

### ⚠️ HIGH RISK (Should Fix Before Merge)

[Same structure as Blockers section]

---

### ⚡ MEDIUM RISK (Fix Soon)

[Same structure, potentially more concise if many issues]

---

### 💡 LOW RISK (Nice to Have)

[Same structure, can be brief for minor issues]

---

## Plan Compliance Check

[If PLAN_PATH was provided, verify against acceptance criteria]

- [ ] Acceptance Criteria 1: [Status and notes]
- [ ] Acceptance Criteria 2: [Status and notes]
- [ ] Validation Commands: [Results of running them]

---

## Verification Checklist

- [ ] All blockers addressed
- [ ] High-risk issues reviewed and resolved or accepted
- [ ] Breaking changes documented with migration guide
- [ ] Security vulnerabilities patched
- [ ] Performance regressions investigated
- [ ] Tests cover new functionality
- [ ] Documentation updated for API changes

---

## Final Verdict

**Status**: [⚠️ FAIL / ✅ PASS]

**Reasoning**: [Explain the verdict. FAIL if any blockers exist. PASS if only Medium/Low risk items remain, or if High risk items are acceptable trade-offs.]

**Next Steps**:
- [Action item 1]
- [Action item 2]
- [Action item 3]

---

**Report File**: `REVIEW_OUTPUT_DIRECTORY/review_[timestamp].md`
` ` `

Remember: Your role is to provide clear, actionable insights that help engineers ship quality code. Be thorough, precise, and constructive in your analysis.
```

---

## Prime Commands

---

#### File: `.claude/commands/prime.md`

```markdown
# Prime

Execute the `Run`, `Read` and `Report` sections to understand the codebase then summarize your understanding.

## Focus
- Primary focus: Claude Code template configuration and AI Developer Workflows

## Run
git ls-files

## Read

### Core (always read these):
- @README.md
- @CLAUDE.md
- @.env.example

### Claude Code Configuration:
- .claude/settings.json
- .claude/agents/ (all agent definitions)
- .claude/commands/ (all command prompts)
- .claude/skills/ (all skill definitions)
- .claude/output-styles/ (output format templates)

### AI Developer Workflows (ADW):
- adws/adw_modules/adw_agent_sdk.py
- adws/adw_modules/adw_database.py
- adws/adw_modules/adw_logging.py
- adws/adw_modules/adw_websockets.py
- adws/adw_workflows/ (workflow implementations)
- adws/adw_triggers/ (workflow triggers)

### Hooks:
- .claude/hooks/ (all hook scripts)

## Report
Summarize your understanding of the codebase structure and capabilities.
```

---

#### File: `.claude/commands/prime_cc.md`

```markdown
---
description: Gain a general understanding of the codebase with a focus on Claude Code improvements
---

# Prime Claude Code

Execute the `Run`, `Read` and `Report` sections to understand the codebase then summarize your understanding.

## Run

Read and execute the .claude/commands/prime.md file top to bottom.

## Read

.claude/commands/
.claude/output-styles/
.claude/hooks/
.claude/skills/
.claude/agents/
.claude/settings.json

## Report

Summarize your understanding of the codebase.
```

---

#### File: `.claude/commands/prime_specific_docs.md`

```markdown
---
name: prime_specific_docs
description: Prime specific documentation from the ai_docs directory.
---

# Purpose

Prime specific documentation from the ai_docs directory.

## Workflow

- @ai_docs/agent-sdk-cost-tracking.md
- @ai_docs/agent-sdk-skills.md
- @ai_docs/agent-sdk-slash-commands.md
- @ai_docs/claude-agent-sdk-hooks.md
- @ai_docs/claude-agent-sdk-hooks.md - the most important - pay close attention to this one
- @ai_docs/claude-code-tools-settings.md
- @ai_docs/claude-code-tools-settings.md
- @ai_docs/claude-sdk-custom-tools.md
- @ai_docs/sdk-slash-commands.md
- @ai_docs/session-management.md
- @ai_docs/uv-running-scripts.md
- @ai_docs/writing-tools-for-agents.md
- @ai_docs/claude-models-overview.md

## Report

Report your understanding of each file we've requested in a concise bullet point list.
```

---

## Orchestration Commands

---

#### File: `.claude/commands/orch_one_shot_agent.md`

```markdown
---
name: orch_one_shot_agent
description: Create and command an agent to accomplish a small task then delete the agent when the task is complete.
argument-hint: [task]
---

# Purpose

Create and command an agent to accomplish a small task then delete the agent when the task is complete.

## Variables

TASK: $1
SLEEP_INTERVAL: 10 seconds

## Instructions

- You can know a task is completed when you see a `agent_logs` from `check_agent_status` that has a `response` event_category followed by a `hook` with a `Stop` event_type.
- Run this workflow for ONLY this agent. This is not a pattern we want to use for other agents unless you're asked to do so.
- When you command each agent, instruct them to use thinking mode with the 'ultrathink' keyword in your prompt.

## Workflow

- (Create) First run `create_agent` to create the agent based on the `TASK`
- (Command) Then run `command_agent` to command the agent to accomplish the `TASK`
- (Check) The agent will then work in the background. While it works use `Bash(sleep ${SLEEP_INTERVAL})` and every `SLEEP_INTERVAL` seconds run `check_agent_status` to check on the agent's progress.
  - If you're interrupted with an additional task, make sure you return to your sleep + check loop after you've completed the additional task.
- (Delete) Once the agent has fully completed it's task AND it's followed by a `hook` with a `Stop` event_type (very important), run `interrupt_agent` and then `delete_agent` to delete the agent.
- (Report) When you finish, report the work done by the agent to the user.

## Report

Communicate to the user where you are at each step of the workflow.
```

---

#### File: `.claude/commands/orch_plan_w_scouts_build_review.md`

```markdown
---
name: orch_plan_w_scouts_build_review
description: Three-phase workflow - plan the task with a custom planner, build the solution with a specialist, then validate with a reviewer.
argument-hint: [task-description]
---

# Purpose

Execute a comprehensive three-phase development workflow: first create a custom planner agent to analyze the task and design an implementation plan, then delegate building to a specialist build agent, and finally validate the work with a review agent. This ensures thorough planning, quality implementation, and comprehensive validation.

## Variables

TASK_DESCRIPTION: $1
SLEEP_INTERVAL: 15 seconds
PLANNER_AGENT_NAME: (will be generated based on task)
BUILD_AGENT_NAME: (will be generated based on task)
REVIEW_AGENT_NAME: (will be generated based on task)

## Instructions

- You can know a task is completed when you see an `agent_logs` from `check_agent_status` that has a `response` event_category followed by a `hook` with a `Stop` event_type.
- Run this workflow for ALL THREE agents in sequence. Complete each phase entirely before starting the next.
- Phase 1: Planner creates the implementation plan (custom system prompt designed by you)
- Phase 2: Build agent implements based on the plan (uses `build-agent` template)
- Phase 3: Review agent validates the work (uses `review-agent` template)
- Do NOT delete agents after completion - leave them for inspection and debugging. We might have additional work for these agents to complete.
- Pass findings from each phase to the next agent as context.
- When you command each agent, instruct them to use thinking mode with the 'ultrathink' keyword in your prompt.

## Workflow

### Setup: Create All Agents Upfront

- **(Create Planner)** Run `create_agent` to create a planner agent WITHOUT using a subagent_template
  - Name the agent something descriptive like "planner-{task-keyword}"
  - **IMPORTANT**: Design a custom system prompt for the planner based on TASK_DESCRIPTION that instructs the agent to:
    - Analyze the task requirements thoroughly
    - Explore the codebase to understand existing patterns
    - Design a detailed implementation plan
    - Identify all files that need to be created or modified
    - Specify the technical approach and architecture decisions
    - Create a structured plan document in the `specs/` directory
    - The planner should be configured with tools: Read, Glob, Grep, Write, Bash
- **(Create Build Agent)** Run `create_agent` to create a build agent using the `build-agent` subagent_template
  - Name the agent something descriptive like "builder-{task-keyword}"
  - Use the same `task-keyword` so agents are clearly related
  - The agent should be configured for file implementation work
- **(Create Review Agent)** Run `create_agent` to create a review agent using the `review-agent` subagent_template
  - Name the agent something descriptive like "reviewer-{task-keyword}"
  - Use the same `task-keyword` so agents are clearly related
  - The agent should be configured for analysis and validation work

### Phase 1: Plan (Analysis & Design)

- **(Command Planner)** Run `command_agent` to command the planner agent to analyze and plan the TASK_DESCRIPTION
  - Instruct the agent to create a comprehensive implementation plan
  - Ensure the plan includes: objective, requirements, files to modify, step-by-step tasks, acceptance criteria
- **(Check Planner)** The planner agent will work in the background. While it works use `Bash(sleep ${SLEEP_INTERVAL})` and every `SLEEP_INTERVAL` seconds run `check_agent_status` to check on the planner's progress.
  - If you're interrupted with an additional task, make sure you return to your sleep + check loop after you've completed the additional task.
  - Continue checking until you see a `response` event_category followed by a `hook` with a `Stop` event_type
- **(Report Planner)** Once the planner has completed, retrieve and analyze their plan from the agent logs.
  - Extract key information: plan location, files to modify, implementation approach
  - Read the plan file from `specs/` directory to understand the full context
  - Communicate the planner's findings to the user

### Phase 2: Build (Implementation)

- **(Command Build Agent)** Run `command_agent` to command the build agent to implement the solution
  - Provide the build agent with:
    - The original TASK_DESCRIPTION
    - The planner's detailed plan (reference the plan file path)
    - Specific files to create/modify based on planner's analysis
    - Implementation approach from the plan
  - Instruct the build agent to implement the solution following the plan's specifications
- **(Check Build Agent)** The build agent will work in the background. While it works use `Bash(sleep ${SLEEP_INTERVAL})` and every `SLEEP_INTERVAL` seconds run `check_agent_status` to check on the build agent's progress.
  - If you're interrupted with an additional task, make sure you return to your sleep + check loop after you've completed the additional task.
  - Continue checking until you see a `response` event_category followed by a `hook` with a `Stop` event_type
- **(Report Build)** Once the build agent has completed, report the implementation results to the user.
  - Extract what was built from the agent logs
  - Note any files created or modified
  - Communicate build completion and key deliverables

### Phase 3: Review (Validation)

- **(Command Review Agent)** Run `command_agent` to command the review agent to validate the work
  - Provide the review agent with:
    - The original TASK_DESCRIPTION
    - The planner's plan for comparison
    - Instructions to analyze git diffs and validate implementation
    - Request a risk-tiered report (Blockers, High Risk, Medium Risk, Low Risk)
  - Instruct the review agent to produce a comprehensive validation report
- **(Check Review Agent)** The review agent will work in the background. While it works use `Bash(sleep ${SLEEP_INTERVAL})` and every `SLEEP_INTERVAL` seconds run `check_agent_status` to check on the review agent's progress.
  - If you're interrupted with an additional task, make sure you return to your sleep + check loop after you've completed the additional task.
  - Continue checking until you see a `response` event_category followed by a `hook` with a `Stop` event_type
- **(Report Review)** Once the review agent has completed, report the validation results to the user.
  - Extract the review findings from agent logs
  - Note the location of the review report
  - Communicate PASS/FAIL verdict and any critical issues
  - Highlight any blockers that need immediate attention

### Final Report

- **(Summary)** Provide a complete summary to the user:
  - Plan phase results: what was planned and where the plan is located
  - Build phase results: what was implemented and which files were modified
  - Review phase results: validation verdict and any issues found
  - All three agents are available for inspection (not deleted)
  - Any follow-up recommendations or next steps based on review findings

## Report

Communicate to the user where you are at each step of the workflow:

1. **Setup Starting**: "Creating planner, builder, and reviewer agents for {TASK_DESCRIPTION}..."
2. **Setup Complete**: "Agents created: Planner '{PLANNER_AGENT_NAME}', builder '{BUILD_AGENT_NAME}', and reviewer '{REVIEW_AGENT_NAME}'"
3. **Plan Phase Starting**: "Commanding planner agent to analyze and design implementation..."
4. **Plan Working**: "Planner agent is analyzing the task and designing the implementation plan... (checking every {SLEEP_INTERVAL} seconds)"
5. **Plan Complete**: "Planning complete. Implementation plan saved to: [plan-file-path]. Key approach: [summary of technical approach]"
6. **Build Phase Starting**: "Commanding build agent to implement the solution based on the plan..."
7. **Build Working**: "Build agent is implementing the solution... (checking every {SLEEP_INTERVAL} seconds)"
8. **Build Complete**: "Implementation complete. Files modified: [list of files]. Key changes: [summary of what was built]"
9. **Review Phase Starting**: "Commanding review agent to validate the implementation..."
10. **Review Working**: "Review agent is analyzing changes and validating work... (checking every {SLEEP_INTERVAL} seconds)"
11. **Review Complete**: "Review complete. Verdict: [PASS/FAIL]. Report location: [review-report-path]. Issues found: [count by risk tier]"
12. **Final Summary**: "Three-phase workflow complete. All agents are available for inspection. [Final recommendation based on review verdict]"
```

---

#### File: `.claude/commands/orch_scout_and_build.md`

```markdown
---
name: orch_scout_and_build
description: Scout a codebase problem with a fast analyzer, then build the solution with a specialized implementation agent.
argument-hint: [problem-description]
---

# Purpose

Scout a codebase problem or research request with a fast analyzer agent, capture their detailed findings, then delegate the implementation to a specialized build agent. This two-phase approach ensures thorough analysis before implementation.

## Variables

PROBLEM_DESCRIPTION: $1
SLEEP_INTERVAL: 15 seconds
SCOUT_AGENT_NAME: (will be generated based on problem)
BUILD_AGENT_NAME: (will be generated based on problem)

## Instructions

- You can know a task is completed when you see an `agent_logs` from `check_agent_status` that has a `response` event_category followed by a `hook` with a `Stop` event_type.
- Run this workflow for BOTH agents in sequence. Complete the scout phase entirely before starting the build phase.
- The scout agent provides READ-ONLY analysis. The build agent performs the actual implementation.
- Do NOT delete agents after completion - leave them for inspection, debugging and prompt continuations.
- Pass the scout's findings to the build agent as context for implementation.
- Use the same `problem-keyword` for both agents so we know they are related.
- When you command each agent, instruct them to use thinking mode with the 'ultrathink' keyword in your prompt.

## Workflow

### Setup: Create All Agents Upfront

- **(Create Scout)** Run `create_agent` to create a scout agent using the `scout-report-suggest-fast` subagent_template
  - Name the agent something descriptive like "scout-{problem-keyword}"
  - The agent should be configured for read-only analysis
- **(Create Build Agent)** Run `create_agent` to create a build agent using the `build-agent` subagent_template
  - Name the agent something descriptive like "build-{problem-keyword}"
  - Use the same `problem-keyword` so agents are clearly related
  - The agent should be configured for implementation work

### Phase 1: Scout (Analysis)

- **(Command Scout)** Run `command_agent` to command the scout agent to investigate and analyze the `PROBLEM_DESCRIPTION`
  - Instruct the agent to provide a detailed scout report with findings and suggested resolutions
- **(Check Scout)** The scout agent will work in the background. While it works use `Bash(sleep ${SLEEP_INTERVAL})` and every `SLEEP_INTERVAL` seconds run `check_agent_status` to check on the scout's progress.
  - If you're interrupted with an additional task, make sure you return to your sleep + check loop after you've completed the additional task.
  - Continue checking until you see a `response` event_category followed by a `hook` with a `Stop` event_type
- **(Report Scout)** Once the scout has completed, retrieve and analyze their findings from the agent logs.
  - Extract key information: affected files, root causes, suggested resolutions
  - Communicate the scout's findings to the user

### Phase 2: Build (Implementation)

- **(Command Build Agent)** Run `command_agent` to command the build agent to implement the solution
  - Provide the build agent with:
    - The original `PROBLEM_DESCRIPTION`
    - The scout agent's detailed findings and recommendations
    - Specific files to modify based on scout's analysis
  - Instruct the build agent to implement the resolution following the scout's suggestions
- **(Check Build Agent)** The build agent will work in the background. While it works use `Bash(sleep ${SLEEP_INTERVAL})` and every `SLEEP_INTERVAL` seconds run `check_agent_status` to check on the build agent's progress.
  - If you're interrupted with an additional task, make sure you return to your sleep + check loop after you've completed the additional task.
  - Continue checking until you see a `response` event_category followed by a `hook` with a `Stop` event_type
- **(Report Build)** Once the build agent has completed, report the implementation results to the user.

### Final Report

- **(Summary)** Provide a complete summary to the user:
  - Scout phase results: what was analyzed and discovered
  - Build phase results: what was implemented and how
  - Both agents are available for inspection (not deleted)
  - Any follow-up recommendations or next steps

## Report

Communicate to the user where you are at each step of the workflow:

1. **Setup Starting**: "Creating scout and build agents for {PROBLEM_DESCRIPTION}..."
2. **Setup Complete**: "Agents created: Scout agent '{SCOUT_AGENT_NAME}' and build agent '{BUILD_AGENT_NAME}'"
3. **Scout Phase Starting**: "Commanding scout agent to analyze the problem..."
4. **Scout Working**: "Scout agent is analyzing the codebase... (checking every {SLEEP_INTERVAL} seconds)"
5. **Scout Complete**: "Scout analysis complete. Key findings: [summary of scout's report]"
6. **Build Phase Starting**: "Commanding build agent to implement the solution..."
7. **Build Working**: "Build agent is implementing changes... (checking every {SLEEP_INTERVAL} seconds)"
8. **Build Complete**: "Implementation complete. Changes made: [summary of build agent's work]"
9. **Final Summary**: "Scout-and-build workflow complete. Both agents are available for inspection."
```

---

## Utility Commands

---

#### File: `.claude/commands/adapt.md`

```markdown
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
```

---

#### File: `.claude/commands/all_tools.md`

```markdown
# List All Tools

List all available tools detailed in your system prompt. Display them in bullet points. Display them in typescript function signature format and suffix the purpose of the tool. Double line break between each tool for readability.
```

---

#### File: `.claude/commands/find_and_summarize.md`

```markdown
---
description: Finds and summarizes specific files in the codebase and saves the summary to app_docs directory
argument-hint: [run-name]
---

# Purpose

Find and summarize specific files in the codebase.

## Variables

RUN_NAME: $1
FILE_EXTENSIONS: $2 or '*.py'
SEARCH_DIRECTORY: $3 or '.' (current directory)

## Instructions

- Recursively find all files in the `SEARCH_DIRECTORY` with the given `FILE_EXTENSIONS`, summarize them in the exact `REPORT_FORMAT`.
- Do not use any subagents to do this. Run your own code to accomplish this task.
- Do not read any other files in the codebase other than the ones specified in the `FILE_EXTENSIONS` and `SEARCH_DIRECTORY`.


## Workflow

1. Find all files in the `SEARCH_DIRECTORY` with the given `FILE_EXTENSIONS`
2. Read as much of each file as you need to to understand it's purpose and functionality.
   - IMPORTANT: Read top to bottom in increments of 50 lines, then 100, then 200, etc. Stop reading when you have a good understanding of the file's purpose and functionality or you have read the entire file.
3. Continue your search until you have summarized every file in the `SEARCH_DIRECTORY` that matches the `FILE_EXTENSIONS`.
4. Return the summary in the exact `REPORT_FORMAT`.

## Report

- IMPORTANT: Create two sentence summaries for each file.
    - In the first sentence, describe the file's purpose and functionality.
    - In the second sentence, describe where the file is used in the codebase.
- Create the output file at `app_docs/find_and_summarize_<RUN_NAME>.yaml` (output dir already exists)

### Report Format

` ` `yaml
summary:
  - file_path: <file-path>
    summary: <summary>
  - file_path: <file-path>
    summary: <summary>
  # ... continue for all files
` ` `
```

---

#### File: `.claude/commands/load_ai_docs.md`

```markdown
---
description: Load documentation from their respective websites into local markdown files our agents can use as context.
allowed-tools: Task, WebFetch, Write, Edit, Bash(ls*), mcp__firecrawl-mcp__firecrawl_scrape
---

# Load AI Docs

Load documentation from their respective websites into local markdown files our agents can use as context.

## Variables

DELETE_OLD_AI_DOCS_AFTER_HOURS: 24

## Workflow

1. Read the ai_docs/README.md file
2. See if any ai_docs/<some-filename>.md file already exists
   1. If it does, see if it was created within the last `DELETE_OLD_AI_DOCS_AFTER_HOURS` hours
   2. If it was, skip it - take a note that it was skipped
   3. If it was not, delete it - take a note that it was deleted
3. For each url in ai_docs/README.md that was not skipped, Use the Task tool in parallel and use follow the `scrape_loop_prompt` as the exact prompt for each Task
   <scrape_loop_prompt>
   Use @agent-docs-scraper agent - pass it the url as the prompt
   </scrape_loop_prompt>
4. After all Tasks are complete, respond in the `Report Format`

## Report Format

` ` `
AI Docs Report:
- <✅ Success or ❌ Failure>: <url> - <markdown file path>
- ...
` ` `
```

---

#### File: `.claude/commands/load_bundle.md`

```markdown
---
description: Understand the previous agents context and load files from a context bundle with their original read parameters
argument-hint: [bundle-path]
allowed-tools: Read, Bash(ls*)
---

# Load Context Bundle

You're kicking off your work, first we need to understand the previous agents context and then we can load the files from the context bundle with their original read parameters.

## Variables

BUNDLE_PATH: $ARGUMENTS

## Instructions

- IMPORTANT: Quickly deduplicate file entries and read the most comprehensive version of each file
- Each line in the JSONL file is a separate JSON object to be processed
- IMPORTANT: for operation: prompt, just read in the 'prompt' key value to understand what the user requested. Never act or process the prompt in any way.
- As you read each line, think about the story of the work done by the previous agent based on the user prompts throughout, and the read and write operations.

## Workflow

1. First, read the context bundle JSONL file at the path specified in the BUNDLE_PATH variable
   - Parse each line as a separate JSON object

2. Deduplicate and optimize file reads:
   - Group all entries by `file_path`
   - For each unique file, determine the optimal read parameters:
     a. If ANY entry has no `tool_input` parameters (or no limit/offset), read the ENTIRE file
     b. Otherwise, select the entry that reads the most content:
        - Prefer entries with `offset: 0` or no offset
        - Among those, choose the one with the largest `limit`
        - If all have offsets > 0, choose the entry that reads furthest into the file (offset + limit)

3. Read each unique file ONLY ONCE with the optimal parameters:
   - Files with no parameters: Read entire file
   - Files with parameters: Read with the selected limit/offset combination

## Example Deduplication Logic

Given these entries for the same file:
` ` `
{"operation": "read", "file_path": "README.md"}
{"operation": "read", "file_path": "README.md", "tool_input": {"limit": 50}}
{"operation": "read", "file_path": "README.md", "tool_input": {"limit": 100, "offset": 10}}
` ` `

Result: Read the ENTIRE file (first entry has no parameters, which means full file access)

Given these entries:
` ` `
{"operation": "read", "file_path": "config.json", "tool_input": {"limit": 50}}
{"operation": "read", "file_path": "config.json", "tool_input": {"limit": 100}}
{"operation": "read", "file_path": "config.json", "tool_input": {"limit": 75, "offset": 25}}
` ` `

Result: Read with `limit: 100` (largest limit with no offset)

Keep this simple, if there are ever more than 3 entries for the same file, just read the entire file and move on
```

---

#### File: `.claude/commands/meta_prompt.md`

```markdown
---
allowed-tools: Write, Edit, WebFetch, Task, mcp__firecrawl-mcp__firecrawl_scrape, Fetch
description: Create a new prompt based on a user's request
---

# Purpose

This meta prompt takes the `USER_PROMPT_REQUEST` and follows the `Workflow` to create a new prompt in the `Specified Format`.

## Variables

USER_PROMPT_REQUEST: $ARGUMENTS
PROMPT_OUTPUT_PATH: `.claude/commands/<name_of_prompt_based_on_user_prompt_request>.md`

## Instructions

- We're building a new prompt to satisfy the request detailed in the `USER_PROMPT_REQUEST`.
- Save the new prompt to `PROMPT_OUTPUT_PATH`
  - The name of the prompt should make sense based on the `USER_PROMPT_REQUEST`
- VERY IMPORTANT: The prompt should be in the `Specified Format`
  - Do not create any additional sections or headers that are not in the `Specified Format`
- IMPORTANT: As you're working through the `Specified Format`, replace every block of `<some request>` with the request detailed within the braces.
- Note we're calling these 'prompts' they're also known as custom slash commands.
- Use one Task tool per documentation item to run sub tasks to gather documentation quickly in parallel using `Task` and `WebFetch`.
- Ultra Think - you're operating a prompt that builds a prompt. Stay focused on the details of creating the best high quality prompt for other ai agents.
- Note, if no variables are requested or mentioned, do not create a Variables section.
- Think through what the static variables vs dynamic variables are and place them accordingly with dynamic variables coming first and static variables coming second.
  - Prefer the `$1`, `$2`, ... over the `$ARGUMENTS` notation.

## Workflow

- Read the documentation
    - Slash Command Documentation: https://code.claude.com/docs/en/slash-commands
    - Create Custom Slash Commands: https://code.claude.com/docs/en/common-workflows#create-custom-slash-commands
    - Available Tools and Settings: https://code.claude.com/docs/en/settings
- Understand the `USER_PROMPT_REQUEST`.
- Create the new prompt in the `Specified Format` that satisfies the `USER_PROMPT_REQUEST` and save it to `PROMPT_OUTPUT_PATH`

## Specified Format
` ` `md
---
allowed-tools: <allowed-tools comma separated>
description: <description we'll use to id this prompt>
argument-hint: [<argument-hint for the first dynamic variable>], [<argument-hint for the second dynamic variable>]
model: <requested model or default to 'opus' if not specified>
---

# Purpose

<prompt purpose: here we describe what the prompt does at a high level and reference any sections we create that are relevant like the `Instructions` section. Every prompt must have an `Instructions` section where we detail the instructions for the prompt in a bullet point list>

## Variables

<exclude this section if no variables are requested or mentioned>

<NAME_OF_DYNAMIC_VARIABLE>: $1
<NAME_OF_DYNAMIC_VARIABLE>: $2
<NAME_OF_STATIC_VARIABLE>: <SOMETHING STATIC>

## Instructions
<detailed bullet point list of instructions for the prompt. These bullet points aid the workflow but are not part of the workflow itself.>

## Workflow
<step by step numbered list of tasks to complete to accomplish the prompt>

## Report
<details of how the prompt should respond back to the user based on the prompt>

` ` `
```

---

#### File: `.claude/commands/parallel_subagents.md`

```markdown
---
description: Launch parallel agents to accomplish a task.
argument-hint: [prompt request] [count]
---

# Parallel Subagents

Follow the `Workflow` below to launch `COUNT` agents in parallel to accomplish a task detailed in the `PROMPT_REQUEST`.

## Variables

PROMPT_REQUEST: $1
COUNT: $2

## Workflow

1. Parse Input Parameters
   - Extract PROMPT_REQUEST to understand the task
   - Determine COUNT (use provided value or infer from task complexity)

2. Design Agent Prompts
   - Create detailed, self-contained prompts for each agent
   - Include specific instructions on what to accomplish
   - Define clear output expectations
   - Remember agents are stateless and need complete context

3. Launch Parallel Agents
   - Use Task tool to spawn N agents simultaneously
   - Ensure all agents launch in a single parallel batch

4. Collect & Summarize Results
   - Gather outputs from all completed agents
   - Synthesize findings into cohesive response
```

---

#### File: `.claude/commands/ping.md`

```markdown
ping (respond with pong)
```

---

#### File: `.claude/commands/question.md`

```markdown
---
allowed-tools: Bash(git ls-files:*), Read
description: Answer questions about the project structure and documentation without coding
---

# Question

Answer the user's question by analyzing the project structure and documentation. This prompt is designed to provide information and answer questions without making any code changes.

## Instructions

- **IMPORTANT: This is a question-answering task only - DO NOT write, edit, or create any files**
- **IMPORTANT: Focus on understanding and explaining existing code and project structure**
- **IMPORTANT: Provide clear, informative answers based on project analysis**
- **IMPORTANT: If the question requires code changes, explain what would need to be done conceptually without implementing**

## Execute

- `git ls-files` to understand the project structure

## Read

- README.md for project overview and documentation

## Analysis Approach

- Review the project structure from git ls-files
- Understand the project's purpose from README
- Connect the question to relevant parts of the project
- Provide comprehensive answers based on analysis

## Response Format

- Direct answer to the question
- Supporting evidence from project structure
- References to relevant documentation
- Conceptual explanations where applicable

## Question

$ARGUMENTS
```

---

#### File: `.claude/commands/question-w-mermaid-diagrams.md`

```markdown
---
allowed-tools: Bash(git ls-files:*), Read, Write
description: Answer questions about the project structure and documentation with Mermaid diagrams
argument-hint: [question]
model: opus
---

# Purpose

Answer the user's question by analyzing the project structure and documentation, then enhance the response with relevant Mermaid diagrams that visualize key concepts, relationships, or flows. This prompt provides comprehensive answers with visual aids while following the `Instructions` section guidelines.

## Variables

USER_QUESTION: $1

## Instructions

- **IMPORTANT: This is primarily a question-answering task - focus on providing informative answers**
- **IMPORTANT: Enhance answers with Mermaid diagrams to visualize concepts, relationships, and flows**
- **IMPORTANT: Use appropriate diagram types based on the question context:**
  - `flowchart` - for processes, workflows, and decision trees
  - `sequenceDiagram` - for interactions between components/systems
  - `classDiagram` - for class relationships and structures
  - `erDiagram` - for database/entity relationships
  - `graph` - for general relationships and hierarchies
  - `stateDiagram-v2` - for state machines and transitions
  - `mindmap` - for concept organization and brainstorming
- **IMPORTANT: Diagrams should clarify and enhance understanding, not replace textual explanations**
- **IMPORTANT: If the question requires code changes, explain conceptually with diagrams showing proposed architecture**

## Workflow

1. Run `git ls-files` to understand the project structure
2. Read README.md for project overview and documentation
3. Analyze the project structure to identify relevant files and components
4. Read additional files as needed to answer the question thoroughly
5. Formulate a comprehensive textual answer
6. Determine which diagram type(s) best visualize the answer
7. Create Mermaid diagram(s) that enhance understanding
8. Combine textual answer with diagrams in the response

## Report

Respond with the following format:

### Answer

[Direct, comprehensive answer to the question with supporting evidence from project analysis]

### Diagram(s)

[One or more Mermaid diagrams that visualize the answer. Include a brief description of what each diagram shows.]

` ` `mermaid
[Appropriate diagram type and content]
` ` `

### References

- [List of relevant files and documentation referenced]
- [Key project structure elements related to the answer]

### Additional Context

[Any conceptual explanations, related considerations, or suggestions for further exploration]
```

---

## Report

After creating all files, report:

- Total number of files created: 23
- List of all created files with their paths
- Confirmation that all files were created with exact content
