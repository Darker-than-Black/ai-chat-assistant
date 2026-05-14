---
description: Use when you have a test specification and need to implement unit tests for an AppV3 service
argument-hint: [path to test spec]
model: opus
---

# Implement Service Tests

Implement unit tests for an AppV3 service according to the provided test specification. Follow the spec exactly and implement step-by-step.

## Variables

PATH_TO_SPEC: $ARGUMENTS

## Instructions

- IMPORTANT: If no `PATH_TO_SPEC` is provided, STOP immediately and ask.
- Read the test spec first — understand the full plan before coding
- Follow test priorities: implement 🔴 Priority 1 first, then 🟡, then 🔵
- Use Laravel model factories — never create manual helper methods
- Run tests after implementing each priority level
- Use `invokeMethod()` from parent TestCase for protected/private methods

## The Iron Law

```
NO COMPLETION CLAIM WITHOUT ALL TESTS PASSING
```

Claiming tests are done without running them? Start over.

**No exceptions:**
- Don't claim "should pass" — prove it passes
- Don't skip running the full test suite
- Don't leave failing tests
- Green or it didn't happen

## Verification Gate (MANDATORY)

BEFORE claiming implementation is complete:

1. **RUN**: `docker compose exec app-backend ./vendor/bin/phpunit tests/appV3/[Domain]/Services/[Service]Test.php`
2. **VERIFY**: All tests pass with 0 failures
3. **RUN**: `docker compose exec app-backend ./vendor/bin/phpunit` (full suite)
4. **VERIFY**: No regressions
5. **ONLY THEN**: Claim completion

## Red Flags — STOP Implementation

- Writing tests without reading the service code
- Mocking DTOs instead of using real instances
- Using Mockery alias for final classes instead of removing `final`
- Skipping factory creation and using manual helpers
- Not running tests after each priority batch
- Claiming completion without full suite verification

## Announcement (MANDATORY)

Before starting work, announce:

"I'm using /implement-service-tests to implement tests from [path]. I will follow priorities, verify each batch, and ensure all tests pass."

## Test Implementation Patterns

### Test Class Structure

```php
<?php declare(strict_types=1);

namespace appV3\[Domain]\Services;

use TestCase;
// Import all dependencies, models, DTOs, exceptions

class [Service]Test extends TestCase
{
    private [Service] $service;
    private [Dependency1] $dependency1;
    // ... all mocked dependencies

    protected function setUp(): void
    {
        parent::setUp();

        $this->dependency1 = $this->createMock(Dependency1::class);
        // ... mock all dependencies

        $this->service = new [Service](
            $this->dependency1,
            // ... in constructor order
        );
    }

    protected function tearDown(): void
    {
        Mockery::close();
        parent::tearDown();
    }
}
```

### Comment Guidelines (MINIMAL)

Only use these section markers once per test:
- `// Arrange` — before test data setup
- `// Act` — before calling the method under test
- `// Assert` — before assertions

DO NOT add obvious comments like:
- `// Mock playerService->savePlayer()` — obvious from code
- `// Create mock DTO` — obvious from code
- `// Expect exception` — obvious from `$this->expectException()`

### NEVER Mock DTOs — Use Real Instances

```php
// ❌ WRONG
$dto = $this->createMock(SomeDtoInterface::class);
$dto->method('getField')->willReturn('value');

// ✅ CORRECT
$dto = new SomeDto(['field' => 'value', 'other' => 123]);
```

If DTO constructor calls `retrieveClientIpAddress()`, add to setUp():
```php
$this->app->instance('request', \Illuminate\Http\Request::create(
    '/', 'GET', [], [], [], ['REMOTE_ADDR' => '127.0.0.1']
));
```

### Final Classes → Remove `final`, Use Standard Mocks

```php
// ❌ WRONG
$mock = Mockery::mock('alias:' . FinalClass::class);

// ✅ CORRECT — remove final from class, then:
$mock = $this->createMock(FinalClass::class);
```

### Exception Message Assertions

```php
// ✅ ALWAYS use translation function
$this->expectExceptionMessage(__("internal_errors." . InternalErrorCodeEnum::ERROR_CODE));

// ❌ NEVER hardcode strings
$this->expectExceptionMessage('Some error text');
```

### Mock Expectations

```php
// Called once
$this->mock->expects($this->once())->method('doSomething');

// Never called
$this->mock->expects($this->never())->method('doSomething');

// Multiple calls with different args
$this->mock->expects($this->exactly(2))
    ->method('doSomething')
    ->withConsecutive([[$arg1]], [[$arg2]])
    ->willReturnOnConsecutiveCalls($result1, $result2);
```

### CacheManager Mocking

```php
$this->cacheManagerPersonal = $this->createMock(CacheManagerPersonal::class);

$this->cacheManager
    ->expects($this->once())
    ->method('usePersonalCache')
    ->willReturn($this->cacheManagerPersonal);

$this->cacheManagerPersonal
    ->expects($this->once())
    ->method('getWithFallbackFunction')
    ->willReturnCallback(function ($key, $callback, $ttl) {
        return $callback();
    });
```

### TransactionRunner Mocking

```php
$this->transactionRunner
    ->expects($this->once())
    ->method('run')
    ->willReturnCallback(function ($callback) {
        return $callback();
    });
```

### Factory Usage (NO manual helpers)

```php
// Create without saving to DB (unit tests)
$user = User::factory()->make(['id' => 1, 'currency' => 'USD']);

// With relationships
$user = User::factory()->make(['id' => 1]);
$tagCollection = new EloquentCollection();
$tagCollection->push(Tag::factory()->make(['tag' => PlayerTag::NO_CASINO_TAG]));
$user->setRelation('tags', $tagCollection);

// State methods
$balance = PlayerBalance::factory()->withSufficientFunds(5000)->make();
```

### Testing Protected Methods

```php
$this->invokeMethod($this->service, 'protectedMethod', [$arg1, $arg2]);
```

### Test Method Naming

`test[MethodName]_[Scenario]` — examples:
- `testAssertUserHasPermission_PlayerBlocked`
- `testAssertBalanceFit_InsufficientBalance`
- `testCreateBet_SuccessWithValidData`

### Creating Missing Factories

Location: `database/factories/AppV3/[Domain]/[Model]Factory.php`

```php
<?php

namespace Database\Factories\AppV3\[Domain];

use AppV3\[Domain]\Models\[Model];
use Illuminate\Database\Eloquent\Factories\Factory;

class [Model]Factory extends Factory
{
    protected $model = [Model]::class;

    public function definition(): array
    {
        return [
            // CRITICAL: Match model's $fillable array
            'id' => $this->faker->randomNumber(),
            'player_id' => $this->faker->randomNumber(),
            'amount' => $this->faker->numberBetween(100, 10000),
            'currency' => $this->faker->randomElement(['USD', 'EUR', 'INR']),
            'status' => 'active',
            'created_at' => now(),
            'updated_at' => now(),
        ];
    }

    // Optional state methods
    public function active(): self
    {
        return $this->state(fn() => ['status' => 'active']);
    }
}
```

## Workflow

1. **Read Spec** — Parse the test spec at `PATH_TO_SPEC`. Extract service path, dependencies, method analysis, phases
2. **Phase 1: Infrastructure** — Create test class skeleton, mock all dependencies in setUp(), create missing factories
3. **Phase 2: Priority 1 Tests** — Implement all 🔴 tests. Run and verify: `docker compose exec app-backend ./vendor/bin/phpunit tests/appV3/[Domain]/Services/[Service]Test.php`
4. **Phase 3: Priority 2 Tests** — Implement all 🟡 tests. Run and verify
5. **Phase 4: Priority 3 Tests** — Implement all 🔵 tests. Run and verify
6. **Phase 5: Validation** — Run full test suite, verify no regressions, mark spec tasks complete

## Report

After completion, provide:

```
✅ Implemented unit tests for [ServiceName]

Test file: tests/appV3/[Domain]/Services/[Service]Test.php
Factories created: [N]
Tests implemented: [X] total
  - 🔴 Priority 1: [A] tests
  - 🟡 Priority 2: [B] tests
  - 🔵 Priority 3: [C] tests

Test Results:
✓ All tests passing: [X]/[X]
✓ Execution time: [N]s
✓ No regressions in full test suite

Files changed:
[git diff --stat output]
```
