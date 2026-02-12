# Layla's Grade Tracker — Tracer Code Implementation Plan

## Role

You are a senior Python engineer building a personal automation tool. You follow **tracer code methodology**: wire the entire system end-to-end with stubs first, then iteratively replace stubs with real implementations — always maintaining a working, testable application. You practice TDD (Red-Green-Refactor) and never commit code that fails quality checks.

---

## Goal

Build a system that:
1. Parses PowerSchool grade report emails from Gmail (IMAP)
2. Sends Discord alerts for **new** missing/failing assignments
3. Publishes an interactive dashboard to GitHub Pages
4. Runs unattended on a GitHub Actions cron schedule

**Success criteria**: After each phase, the system runs end-to-end and produces correct output. Tests pass. Quality checks pass.

---

## Architecture

```
Gmail (IMAP) → parse_emails.py → grades.json
                                    ├── alert.py → Discord webhook
                                    └── build_dashboard.py → docs/index.html
```

### Project Structure

```
grade-data/
├── .github/workflows/grades.yml     # CI/CD pipeline
├── docs/index.html                  # Generated dashboard (GitHub Pages)
├── src/grade_data/
│   ├── __init__.py
│   ├── parser.py                    # Email fetching + parsing
│   ├── alerter.py                   # Discord alert logic + state tracking
│   ├── dashboard.py                 # Dashboard HTML generator
│   └── models.py                    # Shared data models
├── tests/
│   ├── unit/
│   │   ├── test_parser.py
│   │   ├── test_alerter.py
│   │   ├── test_dashboard.py
│   │   └── test_models.py
│   ├── integration/
│   │   └── test_pipeline.py
│   ├── fixtures/
│   │   ├── sample_email.txt         # Real email text for test fixtures
│   │   └── sample_grades.json       # Expected parsed output
│   └── conftest.py
├── parse_emails.py                  # CLI entrypoint: runs parser
├── alert.py                         # CLI entrypoint: runs alerter
├── build_dashboard.py               # CLI entrypoint: runs dashboard builder
├── grades.json                      # Parsed grade data (committed)
├── state.json                       # Alert state tracking (committed)
├── requirements.txt
├── requirements-dev.txt
└── pyproject.toml
```

### Dependencies

**Runtime** (`requirements.txt`):
```
requests>=2.31.0
```

IMAP (`imaplib`, `email`), JSON, and hashing are all stdlib. No heavy deps.

**Dev** (`requirements-dev.txt`):
```
pytest>=8.0
pytest-cov>=4.0
```

---

## Tracer Code Phases

### Phase 1: Wire the Skeleton

**Goal**: Every component exists, connects to the next, and produces valid output — but with hardcoded/mock data. The pipeline runs end-to-end. Tests prove the shape of every output.

**Timebox**: ~20% of total effort.

#### Step 1.1 — Data Models (`src/grade_data/models.py`)

Define the data structures that flow through the system. These are the contracts between components.

```python
from dataclasses import dataclass, field

@dataclass
class Assignment:
    """A single graded assignment."""
    date: str                    # ISO format: "2026-01-12"
    name: str
    letter_grade: str            # "A", "B", "C", "D", "F", or "*" (not yet graded)
    points_earned: float
    points_possible: float
    percentage: float
    is_missing: bool
    is_exempt: bool              # marked with ^
    is_not_included: bool        # marked with *
    is_not_yet_graded: bool      # Grade: *   (-/9)

@dataclass
class Course:
    """A single course with its assignments."""
    name: str
    period: str
    instructor: str
    overall_grade: str
    assignments: list[Assignment] = field(default_factory=list)

@dataclass
class GradeReport:
    """Complete grade report for a student."""
    last_updated: str            # ISO 8601 timestamp
    student: str
    grading_period: str
    courses: list[Course] = field(default_factory=list)

@dataclass
class AlertState:
    """Tracks which missing assignments have already been alerted."""
    alerted_missing: list[str] = field(default_factory=list)  # "{course}::{assignment}::{date}"
    last_run: str | None = None
```

**TDD**: Write tests that verify model creation, serialization to/from JSON, and the assignment key format (`"{course}::{assignment}::{date}"`).

#### Step 1.2 — Stubbed Parser (`src/grade_data/parser.py`)

```python
def fetch_and_parse(gmail_address: str, gmail_password: str) -> GradeReport:
    """Fetch emails from Gmail and parse grade data.

    TODO: Replace with real IMAP connection in Phase 2.
    """
    return GradeReport(
        last_updated=datetime.now(UTC).isoformat(),
        student="Layla H.",
        grading_period="Q3",
        courses=[
            Course(
                name="Math 6",
                period="P1(A)",
                instructor="Motch, Michaela",
                overall_grade="D",
                assignments=[
                    Assignment(
                        date="2026-01-12",
                        name="5.3.4 Lesson",
                        letter_grade="A",
                        points_earned=5.0,
                        points_possible=5.0,
                        percentage=100.0,
                        is_missing=False,
                        is_exempt=False,
                        is_not_included=False,
                        is_not_yet_graded=False,
                    ),
                ],
            ),
        ],
    )
```

**TDD**: Test that `fetch_and_parse()` returns a valid `GradeReport`, that `grades.json` is written correctly, and that the JSON matches the expected schema.

#### Step 1.3 — Stubbed Alerter (`src/grade_data/alerter.py`)

```python
def send_alerts(
    grade_report: GradeReport,
    state: AlertState,
    webhook_url: str,
    dashboard_url: str,
) -> AlertState:
    """Compare missing assignments against state, send Discord alerts for new ones.

    TODO: Replace with real Discord webhook in Phase 2.
    Returns updated AlertState.
    """
    # For now: identify missing, diff against state, return updated state
    # No actual HTTP call yet
    return state
```

**TDD**: Test the diffing logic — given a `GradeReport` with missing assignments and a prior `AlertState`, verify that the function correctly identifies new vs. already-alerted missing assignments.

#### Step 1.4 — Stubbed Dashboard Builder (`src/grade_data/dashboard.py`)

```python
def build_dashboard(
    grade_report: GradeReport,
    password_hash: str,
    output_path: str = "docs/index.html",
) -> None:
    """Generate static HTML dashboard from grade data.

    TODO: Replace with full dashboard in Phase 2.
    """
    html = f"<html><body><h1>Grades for {grade_report.student}</h1></body></html>"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(html)
```

**TDD**: Test that `build_dashboard()` creates `docs/index.html`, that the file contains expected content, and that the password hash is embedded.

#### Step 1.5 — CLI Entrypoints

Wire the three CLI scripts (`parse_emails.py`, `alert.py`, `build_dashboard.py`) to call the stubbed functions with env vars. Each script is thin — just glue.

#### Step 1.6 — GitHub Actions Workflow (`.github/workflows/grades.yml`)

Create the full workflow file. It won't do real work yet (stubs return mock data), but the pipeline shape is correct.

```yaml
name: Update Grades

on:
  schedule:
    - cron: '0 */4 * * *'
  workflow_dispatch:

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Fetch and parse emails
        env:
          GMAIL_ADDRESS: ${{ secrets.GMAIL_ADDRESS }}
          GMAIL_APP_PASSWORD: ${{ secrets.GMAIL_APP_PASSWORD }}
        run: python parse_emails.py
      - name: Send Discord alerts
        env:
          DISCORD_WEBHOOK_URL: ${{ secrets.DISCORD_WEBHOOK_URL }}
          DASHBOARD_URL: ${{ vars.DASHBOARD_URL }}
        run: python alert.py
      - name: Build dashboard
        env:
          DASHBOARD_PASSWORD_HASH: ${{ secrets.DASHBOARD_PASSWORD_HASH }}
        run: python build_dashboard.py
      - name: Commit and push
        run: |
          git config user.name "Grade Bot"
          git config user.email "bot@grades.local"
          git add grades.json state.json docs/
          git diff --staged --quiet || git commit -m "Update grades $(date -u +%Y-%m-%dT%H:%M:%SZ)"
          git push
```

#### Phase 1 Gate Check

- [ ] All components exist and connect
- [ ] `python parse_emails.py` writes `grades.json` (with mock data)
- [ ] `python alert.py` reads `grades.json` + `state.json`, identifies missing (no HTTP yet)
- [ ] `python build_dashboard.py` writes `docs/index.html`
- [ ] All tests pass
- [ ] Quality checks pass

**At this point, the skeleton is demoable.** You can run the full pipeline locally and see it produce output. Nothing is real yet, but everything is wired.

---

### Phase 2: Replace Stubs with Real Implementations

**Goal**: One by one, replace each stub with production logic. TDD each replacement. Never break the skeleton — if a feature is harder than expected, keep the stub and move on.

**Timebox**: ~70% of total effort.

**Priority order** (highest demo impact first):

#### P0: Email Parser (Core Business Logic)

This is the heart of the system. Replace the stubbed `fetch_and_parse()` with real IMAP + parsing logic.

##### Email Format Reference

Emails come from `pwsupport@unionsd.org` with subject `"Progress report for Layla H."`. Body is **plain text**:

```
PowerSchool SIS Union Elementary

Grading period:  Q3
Student       :  Layla H.
Course        :  Math 6
Period        :  P1(A)
Instructor    :  Motch, Michaela

Current overall grade**:  D

    01/12/2026  5.3.4 Lesson                           Grade: A  (5/5 = 100%)
    01/12/2026  5.3.4 RP                               Grade: A  (10/10 = 100%)
    01/12/2026  Ch 5 Check #3                          Grade: D  (6/9 = 66.67%)
    ...

^ - Score is exempt from final grade
* - Assignment is not included in final grade
** - This final grade may include assignments that are not yet published by the teachers.
```

##### Parsing Rules

- Each email = one course. Multiple emails arrive for the same student.
- **Assignment line regex**: `^\s+(\d{2}/\d{2}/\d{4})\s+(.+?)\s{2,}Grade:\s+(\S+)\s+\((.+?)\)$`
- Extract: date, assignment name, letter grade, raw score (e.g., `"5/5 = 100%"`)
- **Missing assignment** = score of `0` out of non-zero possible (e.g., `0/10 = 0%`) AND NOT marked with `^` (exempt) or `*` (not included)
- Parse `Current overall grade**:` line for each course
- Parse `Course`, `Period`, `Instructor` from the header block
- `*` on an assignment = "not included in final grade" — track but flag `is_not_included`
- `^` on an assignment = "exempt from final grade" — track but flag `is_exempt`

##### Edge Cases (Write Tests First)

| Case | Input | Expected |
|------|-------|----------|
| Not-yet-graded | `Grade: *   (-/9)` | `is_not_yet_graded=True`, NOT missing |
| Score > 100% | `10.74/10 = 107.4%` | `percentage=107.4` |
| Special chars in name | `"Ch. 5: Review (Part 2)"` | Parsed correctly |
| `**` in overall grade | `Current overall grade**:  D` | Literal `**`, not footnote |
| Zero score, exempt | `0/10 = 0%` with `^` | `is_missing=False` (exempt) |
| Zero score, not included | `0/10 = 0%` with `*` | `is_missing=False` (not included) |
| Zero score, normal | `0/10 = 0%` no flag | `is_missing=True` |

##### IMAP Strategy

- Connect via IMAP SSL to `imap.gmail.com`
- Search for emails from `pwsupport@unionsd.org` within last 7 days (configurable)
- Parse the **most recent** email per course (dedup by course name)
- Use `email.message_from_bytes()` → `get_payload(decode=True)`
- Handle multi-part emails by iterating parts, grabbing `text/plain`

**TDD**: Write tests against the sample email text as a fixture string. Test every edge case in the table above. Mock IMAP for the fetch layer.

#### P1: Discord Alerter

Replace the stubbed `send_alerts()` with real webhook logic.

##### Alert Behavior

1. Compare current missing assignments against `state.json`'s `alerted_missing` list
2. **New missing assignments exist** (not in state):
   - Send embed listing ONLY new missing, grouped by course
   - If also previously-alerted missing still outstanding, append: `"X other missing assignments still outstanding → View Dashboard"`
   - Update `state.json` with newly alerted
3. **No new missing** (all already alerted):
   - Send nothing
4. **Previously-missing no longer missing** (student turned it in):
   - Remove from `state.json` (cleanup)
   - Optionally send positive message: `"Layla completed: {assignment} in {course}"`

##### Discord Embed Format

```
🚨 New Missing Assignments for Layla

**Math 6** (Overall: D)
  • 6.2.1 RP — due 01/27 (0/10)

**Soc Sci 6** (Overall: F)
  • AE Social Class Notes — due 01/28 (0/10)

📊 8 other missing assignments still outstanding → View Dashboard
```

- Red embed (`0xFF0000`) for missing alerts
- Green embed (`0x00FF00`) for completed messages
- Webhook URL from `DISCORD_WEBHOOK_URL` env var
- Dashboard URL from `DASHBOARD_URL` env var

##### State Schema (`state.json`)

```json
{
  "alerted_missing": [
    "Math 6::6.1.1 RP::2026-01-21",
    "Soc Sci 6::Brainpop: Mummies! Quiz::2026-01-26"
  ],
  "last_run": "2026-02-11T08:00:00Z"
}
```

Key format: `{course_name}::{assignment_name}::{date}`

**TDD**: Test state diffing (new vs. already-alerted), embed message formatting, state cleanup when assignments completed. Mock `requests.post` for the webhook call.

#### P2: Dashboard Builder

Replace the stubbed `build_dashboard()` with a real, self-contained HTML dashboard.

##### Requirements

- Single self-contained HTML file (inline CSS + JS, no external CDNs except optionally a font)
- Data injected as `<script>const GRADE_DATA = {...}</script>` at build time

##### Password Protection

- `DASHBOARD_PASSWORD_HASH` env var = SHA-256 hex digest of family password
- On page load: if `sessionStorage` has no auth flag, show only a centered password input
- Hash user input with `crypto.subtle.digest('SHA-256', ...)` (Web Crypto API, no libs)
- Match → set `sessionStorage` flag, reveal dashboard. No match → error message
- `sessionStorage` = persists for tab session, not after close
- Grade data JSON is still in page source — acceptable for threat model (6th graders, not hackers). Do NOT encrypt the data blob.

##### Dashboard Features

1. **Header**: "Layla's Grade Tracker" + last updated timestamp
2. **Summary cards**: one per course — course name, overall grade, color indicator (A=green, B=blue, C=yellow, D=orange, F=red)
3. **Missing assignments panel**: prominent red section, all current missing/zero assignments with course and date — most visually prominent section
4. **Course detail accordion/tabs**: expand to see assignment table
   - Columns: Date, Assignment, Grade, Score, Status
   - Status badges: "Missing" (red), "Exempt" (gray), "Not Included" (gray), "Not Yet Graded" (yellow)
   - Sort by date descending
5. **Grade distribution**: simple bar or counts of A/B/C/D/F per course
6. **Mobile responsive**: primary viewing on phone
7. **Dark mode friendly**: CSS variables for theming

**TDD**: Test that `build_dashboard()` produces valid HTML, that the password hash is injected, that the grade data JSON is embedded, and that the output file is written to the correct path.

#### P3: Error Handling & Resilience

- Gmail connection fails → exit with error code (GitHub Actions shows failure)
- Discord webhook fails → log error, don't fail the run (grades should still update)
- No new emails found → log, skip — don't wipe existing `grades.json`
- `state.json` doesn't exist → create with `{"alerted_missing": [], "last_run": null}`

---

### Phase 3: Polish

**Goal**: Harden what works. Do NOT start new features.

**Timebox**: ~10% of total effort.

- [ ] Add edge case tests for all implemented features
- [ ] Improve error messages (clear, actionable)
- [ ] Ensure all public functions have Google-style docstrings
- [ ] Clean up remaining TODOs in implemented code
- [ ] Verify mobile responsiveness of dashboard
- [ ] Write README with setup instructions (see below)

---

## README Content (for Phase 3)

The README should cover:

1. **Gmail App Password Setup**:
   - Google Account → Security → 2-Step Verification → App Passwords
   - Generate password for "Mail"
   - IMAP must be enabled in Gmail settings

2. **Discord Webhook Setup**:
   - Server Settings → Integrations → Webhooks → New Webhook
   - Copy the webhook URL

3. **GitHub Setup**:
   - Add secrets: `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD`, `DISCORD_WEBHOOK_URL`, `DASHBOARD_PASSWORD_HASH`
   - Generate password hash: `echo -n "your-family-password" | shasum -a 256 | cut -d' ' -f1`
   - Add variable: `DASHBOARD_URL` (e.g., `https://username.github.io/repo-name/`)
   - Enable GitHub Pages from `docs/` folder on `main` branch
   - Run workflow manually first time to populate initial data

---

## Required Secrets & Variables

| Name | Type | Description |
|------|------|-------------|
| `GMAIL_ADDRESS` | Secret | Gmail address receiving PowerSchool emails |
| `GMAIL_APP_PASSWORD` | Secret | Gmail app password (not regular password) |
| `DISCORD_WEBHOOK_URL` | Secret | Discord webhook URL for alerts channel |
| `DASHBOARD_PASSWORD_HASH` | Secret | SHA-256 hash of dashboard password |
| `DASHBOARD_URL` | Variable | Full URL to GitHub Pages dashboard |

---

## Constraints

### DO

- Use stdlib for IMAP (`imaplib`, `email`), JSON, hashing
- Commit `grades.json` and `state.json` to the repo — they ARE the data store
- Keep the dashboard self-contained (single HTML file, inline CSS/JS)
- All credentials from environment variables / GitHub secrets
- TDD every feature: write test first, then implement
- Run quality checks before each commit

### DO NOT

- Use a database — JSON files committed to repo are the data store
- Use a web framework — no Flask, no FastAPI. This is a batch script
- Use external CSS/JS CDNs (except optionally a font)
- Store credentials in code
- Parse HTML emails — PowerSchool emails are plain text
- Encrypt the dashboard data blob — unnecessary for the threat model
- Start a new feature before the current one passes all tests

---

## Data Schema Reference

### `grades.json`

```json
{
  "last_updated": "2026-02-11T08:00:00Z",
  "student": "Layla H.",
  "grading_period": "Q3",
  "courses": [
    {
      "name": "Math 6",
      "period": "P1(A)",
      "instructor": "Motch, Michaela",
      "overall_grade": "D",
      "assignments": [
        {
          "date": "2026-01-12",
          "name": "5.3.4 Lesson",
          "letter_grade": "A",
          "points_earned": 5.0,
          "points_possible": 5.0,
          "percentage": 100.0,
          "is_missing": false,
          "is_exempt": false,
          "is_not_included": false,
          "is_not_yet_graded": false
        }
      ]
    }
  ]
}
```

### `state.json`

```json
{
  "alerted_missing": [
    "Math 6::6.1.1 RP::2026-01-21",
    "Soc Sci 6::Brainpop: Mummies! Quiz::2026-01-26"
  ],
  "last_run": "2026-02-11T08:00:00Z"
}
```
