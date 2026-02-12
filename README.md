# grade-data

Automated grade tracking for PowerSchool progress reports. Parses email
notifications, sends Discord alerts for missing assignments, and publishes a
password-protected dashboard to GitHub Pages.

## How It Works

1. **Parse**: A scheduled GitHub Actions workflow fetches PowerSchool progress
   report emails from Gmail via IMAP, extracts assignment data, and writes
   `grades.json`.
2. **Alert**: Compares current grades against saved state and sends Discord
   webhook notifications for newly missing or resolved assignments.
3. **Dashboard**: Generates a self-contained HTML dashboard (password-protected
   via SHA-256 + Web Crypto API) and deploys it to GitHub Pages.

## Setup

### 1. Gmail App Password

1. Go to [Google Account Security](https://myaccount.google.com/security).
2. Enable **2-Step Verification** if not already enabled.
3. Navigate to **App Passwords** and generate a password for "Mail".
4. In Gmail settings, ensure **IMAP** is enabled under
   Settings > Forwarding and POP/IMAP.

### 2. Discord Webhook

1. In your Discord server, go to **Server Settings > Integrations > Webhooks**.
2. Click **New Webhook**, choose a channel, and copy the webhook URL.

### 3. GitHub Configuration

Add the following **secrets** in your repository
(Settings > Secrets and variables > Actions):

| Secret                   | Description                                    |
|--------------------------|------------------------------------------------|
| `GMAIL_ADDRESS`          | Gmail address receiving PowerSchool emails     |
| `GMAIL_APP_PASSWORD`     | Gmail app password (not your regular password)  |
| `DISCORD_WEBHOOK_URL`    | Discord webhook URL for the alerts channel     |
| `DASHBOARD_PASSWORD_HASH`| SHA-256 hash of the dashboard password         |

Generate the password hash:

```bash
echo -n "your-family-password" | shasum -a 256 | cut -d' ' -f1
```

Add the following **variable**:

| Variable        | Description                                          |
|-----------------|------------------------------------------------------|
| `DASHBOARD_URL` | Full URL to your GitHub Pages site (e.g., `https://username.github.io/grade-data/`) |

### 4. Enable GitHub Pages

1. Go to Settings > Pages.
2. Set **Source** to "Deploy from a branch".
3. Set **Branch** to `main` and folder to `/docs`.
4. Run the workflow manually the first time to populate initial data.

## Development

### Prerequisites

- Python 3.11+
- pip

### Installation

```bash
git clone <repository-url>
cd grade-data
pip install -r requirements-dev.txt
pre-commit install
```

### Running Quality Checks

Always use the project scripts (never invoke tools directly):

```bash
./scripts/check-all.sh     # Run all 7 quality checks
./scripts/test.sh           # Run unit tests with coverage
./scripts/test.sh --all     # Run unit + integration tests
./scripts/lint.sh           # Ruff linting + mypy type checking
./scripts/format.sh         # Black + isort formatting
./scripts/security.sh       # Bandit + Safety scanning
./scripts/mutation.sh       # Mutation testing
```

### Project Structure

```
grade-data/
├── grade_data/             # Main package
│   ├── __init__.py
│   ├── main.py
│   ├── models.py           # Data models (Assignment, Course, GradeReport, AlertState)
│   ├── parser.py           # Email parsing and IMAP fetching
│   ├── alerter.py          # Discord webhook alerts and state tracking
│   └── dashboard.py        # Static HTML dashboard generator
├── tests/
│   ├── unit/               # Fast, isolated unit tests
│   ├── integration/        # Cross-component pipeline tests
│   └── fixtures/           # Sample email and expected output data
├── scripts/                # Quality control scripts
├── parse_emails.py         # CLI: fetch emails → grades.json
├── alert.py                # CLI: grades.json → Discord alerts
├── build_dashboard.py      # CLI: grades.json → docs/index.html
├── .github/workflows/      # CI/CD pipeline
├── pyproject.toml          # Tool configurations
└── CLAUDE.md               # AI development guidelines
```

### Quality Standards

| Metric               | Threshold |
|----------------------|-----------|
| Test coverage        | >= 90%    |
| Docstring coverage   | >= 95%    |
| Mutation score       | >= 80%    |
| Cyclomatic complexity| <= 10     |

## License

MIT License
