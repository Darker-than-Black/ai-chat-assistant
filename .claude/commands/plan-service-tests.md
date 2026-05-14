---
description: Use when you need to analyze an AppV3 service and generate a unit test specification
argument-hint: [path to service file or class name]
model: opus
---

# Plan Service Tests

Analyze the specified AppV3 service and generate a comprehensive test specification document. Save it to `PLAN_OUTPUT_DIRECTORY/<service-name>-unit-tests.md` that can be used as a blueprint for test implementation.

## Variables

TARGET_SERVICE: $ARGUMENTS
PLAN_OUTPUT_DIRECTORY: `specs/`

## Instructions

- IMPORTANT: If no `TARGET_SERVICE` is provided, STOP immediately and ask.
- Resolve the service file path:
  - If user provided a file path (contains `/` or `.php`), use it directly
  - If user provided a class name (e.g., `AppV3\Player\Services\PlayerService`), convert to path
- Read the service file thoroughly to understand ALL methods and dependencies
- For each model used: READ the model file to verify properties (`$fillable`, `@property` PHPDoc)
- For each Enum/ValueObject: READ the class file to verify actual constants
- Check if factories exist in `database/factories/` or `database/factories/AppV3/[Domain]/`
- Follow the priority classification system to determine which methods need testing
- Generate a comprehensive test spec document

## The Iron Law

```
NO TEST SPEC WITHOUT READING THE ACTUAL SERVICE CODE
```

A spec is complete when a developer can implement all tests without reading the service code.

**No exceptions:**
- Don't assume model properties exist — read the model
- Don't assume enum constants exist — read the enum
- Don't skip reading dependencies
- Incomplete means INCOMPLETE

## Priority Classification System

### Method Priorities

**🔴 Priority 1 — MUST TEST (Critical Security & Financial)**
- Methods protecting money, security, or preventing data corruption
- Financial validations (balance checks, currency matching, amount limits)
- Security checks (permissions, access control, authentication)
- Duplicate prevention (transaction IDs, idempotency)
- Large complex methods (>50 lines) with significant business logic
- Main orchestration methods coordinating multiple services
- Method names: `assert*`, `validate*`, `check*`, `verify*`, `create*`, `process*`, `handle*`
- Throws `InternalLogicException` with financial/security error codes
- Modifies balances, payments, or financial records

**🟡 Priority 2 — SHOULD TEST (Business Rules & Complex Logic)**
- Business rule enforcement, status validations
- Complex conditional logic with business impact
- Session/state validation, game/bonus availability checks
- Medium complexity methods (20-50 lines)
- Job dispatching methods with conditional logic
- Orchestration methods coordinating multiple operations

**🔵 Priority 3 — NICE TO HAVE (Edge Cases)**
- Edge cases with real business impact
- Country-specific, suspicious player restrictions
- Boundary conditions with consequences
- Integration of multiple validations

**⚪ SKIP — Not Worth Testing**
- Pure one-line delegation: `return $this->service->method($args);`
- Trivial getters: `return $this->property;`
- Pure logging wrappers (ONLY Log calls, no business logic)
- Methods <5 lines with no conditional logic

**NEVER SKIP:**
- Methods coordinating multiple services
- Methods with transaction management
- Methods with conditional logic (if/else, switch, loops)
- Methods that create or modify data
- Methods >10 lines
- Main business flow methods

### Test Case Priorities
- 🔴 Core security/financial validation, exception scenarios preventing money loss
- 🟡 Important business rules, common edge cases, happy paths for critical methods
- 🔵 Rare edge cases, additional boundary conditions

## Important Testing Rules

### NEVER Mock DTOs
DTOs are data containers — always use real instances:
```php
// ❌ WRONG
$dto = $this->createMock(SomeDtoInterface::class);
$dto->method('getField')->willReturn('value');

// ✅ CORRECT
$dto = new SomeDto(['field' => 'value', 'other' => 123]);
```

If DTO constructor calls `retrieveClientIpAddress()`, note that setUp() needs:
```php
$this->app->instance('request', \Illuminate\Http\Request::create(
    '/', 'GET', [], [], [], ['REMOTE_ADDR' => '127.0.0.1']
));
```

### Final Classes → Remove `final` Modifier
- Do NOT use `Mockery::mock('alias:' . ClassName::class)`
- Remove `final` keyword from the class and use standard `$this->createMock()`

### Factory Usage
- Use `Model::factory()->make([...])` (no DB) for unit tests
- Check `database/factories/` and `database/factories/AppV3/[Domain]/` for existing factories
- Note missing factories that need to be created during implementation

## Workflow

1. **Read the Service** — Extract class name, namespace, domain, all dependencies, all methods with signatures
2. **Read Dependencies** — Read models (check `$fillable`, properties), enums (check actual constants), DTOs
3. **Check Factories** — Verify which model factories exist, note missing ones
4. **Analyze Methods** — Classify each method by priority, plan test cases
5. **Generate Spec** — Create comprehensive test spec document
6. **Save & Report** — Write to `PLAN_OUTPUT_DIRECTORY/<service-name>-unit-tests.md`

## Test Spec Format

```md
# Plan: Unit Tests for [Service]

## Task Description
Create focused, logically justified unit tests for `appV3/[Domain]/Services/[Service].php`.

## Objective
Comprehensive PHPUnit test suite covering all significant business logic.

## Problem Statement
The `[Service]` class currently lacks unit test coverage. This [N]-line service handles critical operations including [key operations].

## Relevant Files

### Service Under Test
- `appV3/[Domain]/Services/[Service].php` ([N] lines)

### Dependencies to Mock
[List all constructor dependencies with full class paths]

### Models Used
[List all models with verified properties from reading model files]

### DTOs Used
[List all DTOs — these will NOT be mocked, real instances used]

### Model Factories
**Existing** (use in tests):
[List existing factories]

**Missing** (need to create):
[List models without factories]

### Test Pattern References
- `tests/appV3/Player/Services/PlayerServiceTest.php`
- `tests/appV3/Casino/Services/SlotBetServiceTest.php`
- `tests/TestCase.php`

### New Files
- `tests/appV3/[Domain]/Services/[Service]Test.php`
- `database/factories/AppV3/[Domain]/[Model]Factory.php` (if needed)

## Method Analysis

[For each method:]

### Tested Methods

- 🔴 `visibility function methodName(Type $param): ReturnType`
  - **Description**: What the method does and why this priority
  - **Test cases**:
    - 🔴 **Test Case Description** — Reasoning
    - 🟡 **Test Case Description** — Reasoning

### Skipped Methods

- ⚪ `visibility function methodName(Type $param): ReturnType`
  - **Description**: Why skipped (pure delegation, trivial getter, etc.)

## Method Analysis Summary

**Total**: [N] methods analyzed
- 🔴 Priority 1: [X] methods, [A] tests
- 🟡 Priority 2: [Y] methods, [B] tests
- 🔵 Priority 3: [Z] methods, [C] tests
- ⚪ Skipped: [W] methods
**Total tests**: [A+B+C]

## Step by Step Tasks

### 1. Test Infrastructure Setup
- [ ] **Create test class skeleton** — test file extending TestCase
  - Status:
  - Comments:
- [ ] **Set up dependencies** — Mock [N] dependencies in setUp()
  - Status:
  - Comments:
- [ ] **Create missing factories** — [list models needing factories]
  - Status:
  - Comments:

### 2. Priority 1 Tests (Security & Financial)
[List specific test tasks]

### 3. Priority 2 Tests (Business Rules)
[List specific test tasks]

### 4. Priority 3 Tests (Edge Cases)
[List specific test tasks]

### 5. Validation
- [ ] **Run tests** — Execute and verify all pass
  - Status:
  - Comments:
- [ ] **Run full suite** — Ensure no regressions
  - Status:
  - Comments:

## Acceptance Criteria

1. [X] tests total covering all significant business logic
2. All tests pass with 0 failures
3. No regressions in full test suite
4. All dependencies properly mocked
5. All critical exception scenarios tested
6. Fast execution (<5 seconds)

## Validation Commands

```bash
docker compose exec app-backend ./vendor/bin/phpunit tests/appV3/[Domain]/Services/[Service]Test.php
docker compose exec app-backend ./vendor/bin/phpunit --testdox tests/appV3/[Domain]/Services/[Service]Test.php
docker compose exec app-backend ./vendor/bin/phpunit
```
```

## Report

After generating the test spec, provide:

```
✅ Test Specification Created

File: PLAN_OUTPUT_DIRECTORY/<service-name>-unit-tests.md
Service: [Full\Class\Name]
Domain: [Domain]
Dependencies: [N] to mock

Test Breakdown:
🔴 Priority 1 (Security & Financial): [A] tests
🟡 Priority 2 (Business Rules): [B] tests
🔵 Priority 3 (Edge Cases): [C] tests
Total: [X] tests

Next Steps:
1. Review the spec
2. Implement with: /implement-service-tests specs/<service-name>-unit-tests.md
```
