# Prompt Engineering Skill

**Skill Name**: `prompt-engineering`
**Purpose**: Transform vague requests into effective, actionable prompts that produce better outcomes
**When to use**: Before creating plan files, delegating to agents, or when Claude's responses miss the mark

---

## The 6-Component Framework

A good prompt contains:

1. **Role or Persona** - Who the AI should be
2. **Goal / Task Statement** - Exactly what you want done
3. **Context or References** - Key data the model needs
4. **Format or Output Requirements** - How you want the answer
5. **Examples or Demonstrations** - Show, don't just tell
6. **Constraints / Additional Instructions** - Boundaries that improve quality

---

## Before & After Examples

### Example 1: Code Review Request

**❌ Ineffective:**
```
Review this code.
```

**✅ Effective:**
```
Role: You are a senior Python engineer focused on code quality.

Task: Review the FastAPI endpoint in src/api/users.py for:
- Security vulnerabilities
- Performance issues
- Code style violations

Context: This is a user registration endpoint that will handle
~1000 requests/day in production.

Format: Provide findings as a numbered list with:
- Issue description
- Severity (Critical/Medium/Low)
- Specific line number
- Recommended fix

Example:
1. SQL Injection Risk (Critical)
   Line 45: Direct string interpolation in query
   Fix: Use parameterized queries

Constraints:
- Only flag issues with confidence > 80%
- Skip minor style issues if functionality is correct
```

### Example 2: Bug Fix Plan

**❌ Ineffective:**
```
Help me fix the login bug.
```

**✅ Effective:**
```
Role: Backend debugging specialist with FastAPI expertise.

Task: Create a root cause analysis and fix plan for login failures.

Context:
- Error: "401 Unauthorized" on POST /auth/login
- Happens intermittently (30% of requests)
- Started after deploying commit abc123
- JWT token validation in src/auth/jwt.py

Format: Create plan/YYYY-MM-DD_LOGIN_BUG_FIX.md with:
## Root Cause
## Reproduction Steps
## Fix Strategy
## Testing Plan

Example Root Cause:
```markdown
## Root Cause
Location: src/auth/jwt.py:67
Race condition in token cache invalidation causes
valid tokens to be rejected when cache refreshes.
```

Constraints:
- Must include specific file:line references
- Fix must maintain backward compatibility
- Include test cases that prevent regression
```

### Example 3: Feature Implementation

**❌ Ineffective:**
```
Add a search feature.
```

**✅ Effective:**
```
Role: Full-stack engineer implementing search functionality.

Task: Design and implement user search for the FastAPI backend.

Context:
- User model: id, email, name, created_at
- Database: PostgreSQL with ~10K users
- Need to search by name or email
- Must support partial matches

Format:
1. API endpoint specification (method, route, request/response)
2. Database query strategy (SQL with indexing recommendations)
3. Test cases (unit + integration)
4. Implementation plan following 2-gate workflow

Example API Spec:
```
GET /api/users/search?q=john&limit=10
Response: {
  "results": [{"id": 1, "name": "John Doe", "email": "john@example.com"}],
  "total": 1
}
```

Constraints:
- ≥90% test coverage required
- Query must use DB indexes (no table scans)
- Return max 100 results
- Follow existing API patterns in src/api/
```

---

## Quick Improvement Checklist

When writing a prompt, ask:

- [ ] **Role**: Did I specify who Claude should be?
- [ ] **Goal**: Is the task specific and measurable?
- [ ] **Context**: Have I provided relevant background data?
- [ ] **Format**: Did I specify the output structure?
- [ ] **Examples**: Did I show what good looks like?
- [ ] **Constraints**: Are boundaries and requirements clear?

**Missing 3+ items?** → Rewrite the prompt.

---

## Plan File Standards

All files in `plan/` should use this framework:

```markdown
# YYYY-MM-DD_FEATURE_NAME.md

## Role
You are a [specific role with relevant expertise].

## Goal
[Specific, measurable task with clear success criteria]

## Context
- Current state: [what exists now]
- Problem: [what needs solving]
- Constraints: [technical limitations, requirements]
- References: [file paths, API endpoints, prior work]

## Output Format
[Specify structure: numbered steps, code blocks, decision matrix, etc.]

## Examples
[Show concrete examples of what you want]

## Requirements
- [Specific constraint 1]
- [Specific constraint 2]
- Must follow 2-gate workflow (TDD → Pre-commit)
```

---

## Common Prompt Failures

### Failure: Too Vague
```
❌ "Make it better"
✅ "Reduce cyclomatic complexity in src/services/payment.py from 15 to ≤10
    by extracting validation logic into separate functions"
```

### Failure: Missing Context
```
❌ "Why isn't this working?"
✅ "POST /api/orders returns 500 error. Expected 201.
    Request: {"items": [1,2,3]}
    Error log: [paste stack trace]
    File: src/api/orders.py:145"
```

### Failure: No Format Specified
```
❌ "Analyze the architecture"
✅ "Create architecture analysis with:
    - Component diagram (mermaid syntax)
    - Data flow (numbered steps)
    - Bottlenecks (table with component, issue, impact)"
```

### Failure: No Examples
```
❌ "Write good commit messages"
✅ "Use conventional commits format:
    Example: 'feat(api): add user search endpoint (#42)'"
```

---

## Template: Prompt Improvement

When you receive a vague request, transform it:

**Original:**
> [User's vague request]

**Clarifying Questions (if needed):**
- What role/expertise is relevant here?
- What's the specific, measurable goal?
- What context am I missing?
- What format do you want?
- Can I show you an example?
- What constraints matter?

**Improved Prompt:**
[Rewritten with all 6 components]

---

## Integration with Stay Green

Effective prompts accelerate the 2-gate workflow:

- **Gate 1 (TDD)**: Clear prompts → clear tests → clear implementation
- **Gate 2 (Quality)**: Specified constraints → fewer iterations

**Time investment**: 2 minutes improving prompt saves 20 minutes debugging unclear requirements.

---

## Anti-Patterns

❌ **Don't**:
- Assume Claude knows your project structure
- Use pronouns without referencing ("fix that bug")
- Skip examples when the task is non-trivial
- Forget to specify output format
- Write novel-length prompts (be concise but complete)

✅ **Do**:
- Reference specific files and line numbers
- Show concrete examples
- Specify success criteria
- Use the 6-component checklist
- Iterate: if the response misses, improve the prompt

---

**Remember**: Every plan file is a prompt. Make it effective.
