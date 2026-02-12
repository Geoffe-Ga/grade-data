# Tracer Code Development

**When to use**: Complex projects, interview coding sessions, or any scenario where you need a working demo within a fixed time constraint. Assumes TDD discipline (see `testing.md` and `interview-pairing.md` for details).

## Core Concept

From *The Pragmatic Programmer* by Hunt & Thomas:

> Tracer code is not disposable: you write it for keeps. It contains all the error checking, structuring, documentation, and self-checking that any piece of production code has. It simply is not fully functional.

**Tracer code wires together the entire system end-to-end with the bare minimum at each layer.** Every endpoint returns real responses, every layer connects to the next, but business logic starts as stubs returning hello-world or mock data. You then iteratively replace stubs with real implementations — one at a time — always maintaining a working, demoable application.

## Why Tracer Code

- **Always demoable**: At every point in development, the app runs and does something
- **Early integration**: Catches architectural mismatches immediately, not at the end
- **Time-box friendly**: If the clock runs out, you have a working skeleton — not a half-finished feature
- **Interview essential**: The worst outcome is having nothing to show. Tracer code prevents that entirely

## The Process

### Phase 1: Wire the Skeleton (10-15% of time budget)

Build the thinnest possible end-to-end path through the system:

1. **Define the API surface** — All endpoints with request/response models (Pydantic)
2. **Stub every endpoint** — Return mock/hardcoded data that matches the response model
3. **Connect all layers** — Router → Service → Model, even if service methods are one-liners
4. **Verify it runs** — Hit every endpoint, confirm valid responses
5. **Write smoke tests** — One test per endpoint proving it returns 200 with expected shape

```python
# Phase 1 example: stubbed endpoint
@router.post("/billing/calculate", response_model=BillingResponse)
async def calculate_billing(request: BillingRequest) -> BillingResponse:
    """Calculate billing cost from impressions and CPM."""
    # TODO: implement real calculation
    return BillingResponse(cost=0.0, currency="USD")
```

```python
# Phase 1 example: stubbed service
class BillingService:
    """Billing calculation service."""

    def calculate(self, impressions: int, cpm: float) -> float:
        """Calculate cost from impressions and CPM."""
        # TODO: implement
        return 0.0
```

**Gate check**: `./scripts/check-all.sh` passes. You now have a demoable skeleton.

### Phase 2: Prioritize and Iterate (75-80% of time budget)

Replace stubs with real implementations **one at a time**, in priority order:

1. **Rank features by demo impact** — What makes the most impressive demo? Do that first.
2. **For each feature**:
   - Write a failing test (Red)
   - Implement the real logic (Green)
   - Refactor if needed
   - Run quality checks
   - Commit
3. **Never break the skeleton** — If a feature is harder than expected, keep the stub and move on
4. **Reassess priority after each feature** — The plan may shift as you learn

**Priority heuristic for interviews**:
- **P0**: Core business logic (the thing they asked you to build)
- **P1**: Input validation and meaningful error responses
- **P2**: Edge cases and secondary features
- **P3**: Nice-to-haves (logging, metrics, advanced error handling)

```python
# Phase 2: replacing the stub with real logic
class BillingService:
    """Billing calculation service."""

    def calculate(self, impressions: int, cpm: float) -> float:
        """Calculate cost from impressions and CPM."""
        return impressions * (cpm / 1000)
```

### Phase 3: Polish (5-10% of time budget)

With remaining time, harden what you have:

- Add edge case tests for implemented features
- Improve error messages
- Add docstrings to public API
- Clean up any remaining TODOs in implemented code
- **Do NOT start new features** — polish what works

## Decision Framework

At any point during development, ask:

> "If the clock ran out right now, would I have something to demo?"

- **Yes** → Keep going, pick the next highest-impact feature
- **No** → Stop what you're doing. Get back to green. Stub it out and move on.

## Anti-Patterns

- **Going deep before going wide** — Perfecting one endpoint while others don't exist
- **Big-bang integration** — Building all layers of one feature before touching the next
- **Gold-plating stubs** — Adding complexity to features that aren't yet the priority
- **Breaking green to add a feature** — If it's not working, revert and stub it
- **Refusing to stub** — A stub that returns mock data is infinitely better than unfinished code that doesn't compile

## Integration with Interview Workflow

1. **Narrate the plan**: "I'm going to wire up the full API surface first with stubs, then implement features by priority"
2. **Demo the skeleton early**: Show the interviewer all endpoints responding — this builds confidence
3. **Announce each iteration**: "Now I'm replacing the billing stub with real calculation logic"
4. **TDD each replacement**: Write test → implement → verify (demonstrates discipline)
5. **Time-check at 50%**: Are P0 features done? If not, simplify scope

## Tracer Code vs. Prototyping

| | Tracer Code | Prototype |
|---|---|---|
| **Quality** | Production-grade (tests, types, validation) | Throwaway |
| **Kept?** | Yes — it IS the application | No — rewritten from scratch |
| **Purpose** | Incrementally build the real thing | Explore feasibility |
| **Architecture** | Real structure from day one | Whatever works |

Tracer code is not a prototype. It's the real application, built incrementally from the outside in.
