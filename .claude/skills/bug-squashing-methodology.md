# Bug Squashing Methodology

**When to use**: Critical bugs blocking functionality, especially those discovered during testing or user reports.

## Core Principle

**Document → Understand → Fix → Verify** - Never skip straight to coding. Root cause analysis prevents recurrence and builds institutional knowledge.

## The 5-Step Process

### 1. Root Cause Analysis (RCA)

Create `RCA_ISSUE_XXX.md` with:
- **Problem Statement**: Error message, reproduction steps
- **Root Cause**: Exact line/logic causing failure
- **Analysis**: Why it happens, what was confused/wrong
- **Impact**: Severity, scope, frequency
- **Contributing Factors**: Why wasn't it caught earlier?
- **Fix Strategy**: Options with recommendation
- **Prevention**: How to avoid similar bugs

**Example**:
```markdown
## Root Cause
Location: `src/services/business_logic.py:45`
Code assumes input is always a list, but API endpoint can
receive single objects. Missing type validation → runtime error.
```

### 2. GitHub Issue

File issue with:
- Clear title: `bug(component): Brief description`
- Reproduction steps
- Root cause summary
- Proposed fix
- Link to RCA document
- Labels: `bug`

**Purpose**: Trackability, team awareness, automatic linking when PR merged

### 3. Branch & Fix

```bash
git checkout -b fix-component-issue-XXX
```

**Fix Guidelines**:
- **TDD first**: Write failing test → Fix → Verify (Gate 1)
- **Simplest solution**: Remove wrong assumption vs. add complexity
- **Clear naming**: Rename variables that caused confusion
- **Add comments**: Explain why, not what

### 4. The 2-Gate Workflow

**Gate 1 - TDD (Test-Driven Development)**:

Follow Red-Green-Refactor for the bug fix:

1. **🔴 Red**: Write a test that reproduces the bug (should fail)
   ```bash
   ./scripts/test.sh --all
   ```

2. **🟢 Green**: Write minimal code to fix the bug (test passes)
   ```bash
   ./scripts/test.sh --all
   ```

3. **♻️ Refactor**: Clean up the fix while keeping tests green
   ```bash
   ./scripts/test.sh --all
   ```

**Gate 2 - Pre-Commit Quality Checks**:

```bash
pre-commit run --all-files
```

Iterate until all checks pass:
- ✓ Code formatting (Black + isort)
- ✓ Linting (Ruff)
- ✓ Type checking (MyPy)
- ✓ Complexity analysis (≤10 per function)
- ✓ Security scanning (Bandit)
- ✓ Tests with coverage (≥90%)
- ✓ File hygiene checks

**Rule**: Never commit until BOTH gates are green ✅

### 5. Commit & PR

**Commit Message Format**:
```
fix(component): brief description (#XXX)

## Problem
[What failed and why - reference RCA]

## Solution
[What you changed]

## Changes
- File: specific change
- File: specific change

## Testing
- Gate 1: ✅ TDD complete (test reproduces → fix → passes)
- Gate 2: ✅ All pre-commit checks pass

## Impact
- Fixes Issue #XXX
- Scope: what's affected

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

**PR Body**: Similar structure, reference RCA document

## What Makes This Effective

1. **RCA prevents recurrence**: Understanding root cause → better prevention
2. **Documentation = knowledge**: Future developers understand "why"
3. **2-gate workflow = quality**: TDD + quality checks catch issues before commit
4. **GitHub integration**: Auto-closes issues, tracks history
5. **Commit discipline**: Clear history, easy rollback if needed

## Anti-Patterns to Avoid

❌ **Don't**:
- Skip RCA for "obvious" bugs (they're rarely obvious)
- Write fix before writing the test (breaks TDD)
- Lower quality thresholds to "fix faster"
- Bypass pre-commit hooks with `--no-verify`
- Create commits like "fix bug" or "update file"

✅ **Do**:
- Spend 10 minutes on RCA even for simple bugs
- Write test that reproduces the bug FIRST (Gate 1 Red)
- Fix root cause, not symptoms
- Let both gates complete before commit
- Write detailed commit messages
- Reference issues in commits (`#XXX`)

## Time Investment

- **RCA**: 10-15 minutes (saves hours debugging recurrence)
- **Issue filing**: 5 minutes (enables tracking)
- **Fix (TDD)**: Varies (test-first adds upfront time, saves debugging)
- **Gate verification**: 5-10 minutes (automated)

**Total overhead**: ~20-30 minutes per bug
**Value**: Prevents recurrence, builds knowledge, maintains quality

## TDD for Bug Fixes

The TDD cycle is especially powerful for bug fixes:

1. **🔴 Red**: Write a test that fails because of the bug
   - This proves you can reproduce it
   - The test will prevent regression

2. **🟢 Green**: Fix the bug (test now passes)
   - Proves the fix works
   - Minimal code to make test pass

3. **♻️ Refactor**: Improve the fix
   - Clean up any quick fixes
   - Add defensive code if needed
   - Tests still pass

## Integration with Stay Green

This methodology IS the Stay Green workflow applied to bugs:
- **Gate 1 (TDD)**: Test the bug, fix it, refactor
- **Gate 2 (Quality)**: All pre-commit checks pass
- **No Shortcuts**: Complete both gates before commit

Use for any bug blocking functionality or discovered in testing.
