"""Dashboard HTML generator.

Builds a self-contained HTML dashboard from grade data,
with client-side password protection via SHA-256 hashing.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from grade_data.models import GradeReport


def build_dashboard(
    grade_report: GradeReport,
    password_hash: str,
    output_path: str = "docs/index.html",
) -> None:
    """Generate a static HTML dashboard from grade data.

    Creates a self-contained HTML file with inline CSS and JavaScript.
    Features client-side password protection using Web Crypto API,
    course summary cards, missing assignments panel, and expandable
    assignment tables.

    Args:
        grade_report: The grade report to render.
        password_hash: SHA-256 hex digest for password protection.
        output_path: File path to write the HTML output.
    """
    grade_json = json.dumps(grade_report.to_dict(), indent=2)

    html = _build_html(grade_report, password_hash.strip(), grade_json)

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html)


def _build_html(
    grade_report: GradeReport,
    password_hash: str,
    grade_json: str,
) -> str:
    """Build the complete HTML string for the dashboard.

    Args:
        grade_report: The grade report to render.
        password_hash: SHA-256 hex digest for password protection.
        grade_json: Pre-serialized JSON string of the grade data.

    Returns:
        Complete HTML document as a string.
    """
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Grade Tracker — {grade_report.student}</title>
    <style>
{_CSS}
    </style>
</head>
<body>
    <div id="login-screen">
        <div class="login-box">
            <h1>Grade Tracker</h1>
            <p>Enter password to view grades</p>
            <input type="password" id="password-input" placeholder="Password"
                   autocomplete="off">
            <button id="login-btn" onclick="checkPassword()">Unlock</button>
            <p id="login-error" class="error" hidden>Incorrect password</p>
        </div>
    </div>
    <div id="dashboard" hidden>
        <header>
            <h1>Grades for {grade_report.student}</h1>
            <p class="subtitle">{grade_report.grading_period}
                &middot; Updated {grade_report.last_updated}</p>
        </header>
        <div id="missing-panel"></div>
        <div id="course-cards"></div>
        <div id="course-details"></div>
    </div>
    <script>
        const PASSWORD_HASH = "{password_hash}";
        const GRADE_DATA = {grade_json};
{_JS}
    </script>
</body>
</html>
"""


_CSS = """\
        :root {
            --bg: #1a1a2e;
            --surface: #16213e;
            --card: #0f3460;
            --text: #e0e0e0;
            --text-muted: #a0a0b0;
            --accent: #e94560;
            --grade-a: #4caf50;
            --grade-b: #2196f3;
            --grade-c: #ffc107;
            --grade-d: #ff9800;
            --grade-f: #f44336;
            --badge-missing: #f44336;
            --badge-exempt: #78909c;
            --badge-not-included: #78909c;
            --badge-not-graded: #ffc107;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI",
                         Roboto, Helvetica, Arial, sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
        }
        #login-screen {
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
        }
        #login-screen[hidden] { display: none; }
        .login-box {
            text-align: center;
            background: var(--surface);
            padding: 2rem;
            border-radius: 12px;
            max-width: 320px;
            width: 90%;
        }
        .login-box h1 { margin-bottom: .5rem; }
        .login-box p { color: var(--text-muted); margin-bottom: 1rem; }
        .login-box input {
            width: 100%;
            padding: .6rem;
            border: 1px solid var(--card);
            border-radius: 6px;
            background: var(--bg);
            color: var(--text);
            font-size: 1rem;
            margin-bottom: .75rem;
        }
        .login-box button {
            width: 100%;
            padding: .6rem;
            border: none;
            border-radius: 6px;
            background: var(--accent);
            color: #fff;
            font-size: 1rem;
            cursor: pointer;
        }
        .error { color: var(--accent); margin-top: .5rem; }
        header {
            padding: 1.5rem 1rem .5rem;
            text-align: center;
        }
        .subtitle { color: var(--text-muted); margin-top: .25rem; }
        #missing-panel {
            margin: 1rem;
            padding: 1rem;
            background: rgba(244,67,54,.12);
            border-left: 4px solid var(--badge-missing);
            border-radius: 6px;
        }
        #missing-panel:empty { display: none; }
        #missing-panel h2 {
            font-size: 1rem;
            color: var(--badge-missing);
            margin-bottom: .5rem;
        }
        #missing-panel ul { list-style: none; padding: 0; }
        #missing-panel li {
            padding: .25rem 0;
            font-size: .9rem;
        }
        #course-cards {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
            gap: .75rem;
            padding: 0 1rem;
            margin-bottom: 1rem;
        }
        .card {
            background: var(--surface);
            border-radius: 8px;
            padding: 1rem;
            text-align: center;
            cursor: pointer;
            transition: transform .15s;
        }
        .card:hover { transform: translateY(-2px); }
        .card-name { font-size: .85rem; color: var(--text-muted); }
        .card-grade {
            font-size: 2rem;
            font-weight: 700;
            margin: .25rem 0;
        }
        #course-details { padding: 0 1rem 2rem; }
        .course-section {
            background: var(--surface);
            border-radius: 8px;
            margin-bottom: 1rem;
            overflow: hidden;
        }
        .course-header {
            padding: 1rem;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .course-header h3 { font-size: 1rem; }
        .course-header .toggle { font-size: .8rem; color: var(--text-muted); }
        .course-body { display: none; padding: 0 1rem 1rem; }
        .course-body.open { display: block; }
        table { width: 100%; border-collapse: collapse; font-size: .85rem; }
        th {
            text-align: left;
            padding: .4rem .3rem;
            border-bottom: 1px solid var(--card);
            color: var(--text-muted);
            font-weight: 500;
        }
        td { padding: .4rem .3rem; border-bottom: 1px solid var(--card); }
        .badge {
            display: inline-block;
            padding: 1px 6px;
            border-radius: 4px;
            font-size: .75rem;
            font-weight: 600;
        }
        .badge-missing { background: var(--badge-missing); color: #fff; }
        .badge-exempt { background: var(--badge-exempt); color: #fff; }
        .badge-not-included { background: var(--badge-not-included); color:#fff;}
        .badge-not-graded { background: var(--badge-not-graded); color: #000; }
"""

_JS = """\
        // --- Password protection ---
        function checkPassword() {
            const input = document.getElementById('password-input').value;
            crypto.subtle.digest('SHA-256',
                new TextEncoder().encode(input)
            ).then(buf => {
                const hash = Array.from(new Uint8Array(buf))
                    .map(b => b.toString(16).padStart(2, '0')).join('');
                if (hash === PASSWORD_HASH.trim()) {
                    sessionStorage.setItem('authed', '1');
                    showDashboard();
                } else {
                    document.getElementById('login-error').hidden = false;
                }
            }).catch(() => {
                document.getElementById('login-error').textContent =
                    'Unlock requires HTTPS.';
                document.getElementById('login-error').hidden = false;
            });
        }
        document.addEventListener('DOMContentLoaded', () => {
            if (sessionStorage.getItem('authed') === '1') showDashboard();
            const inp = document.getElementById('password-input');
            inp.addEventListener('keydown', e => {
                if (e.key === 'Enter') checkPassword();
            });
        });
        function showDashboard() {
            document.getElementById('login-screen').hidden = true;
            document.getElementById('dashboard').hidden = false;
            renderDashboard();
        }

        // --- Rendering ---
        function gradeColor(letter) {
            const map = {A:'var(--grade-a)',B:'var(--grade-b)',
                         C:'var(--grade-c)',D:'var(--grade-d)',
                         F:'var(--grade-f)'};
            return map[letter && letter[0]] || 'var(--text)';
        }
        function statusBadge(a) {
            const b = '<span class="badge badge-';
            if (a.is_missing)
                return b+'missing">Missing</span>';
            if (a.is_exempt)
                return b+'exempt">Exempt</span>';
            if (a.is_not_included)
                return b+'not-included">Not Included</span>';
            if (a.is_not_yet_graded)
                return b+'not-graded">Not Graded</span>';
            return '';
        }
        function formatDate(iso) {
            const d = new Date(iso);
            return d.toLocaleDateString('en-US', {
                month: 'short', day: 'numeric', year: 'numeric',
                hour: 'numeric', minute: '2-digit'
            });
        }
        function renderDashboard() {
            const d = GRADE_DATA;
            // Format the updated date in the subtitle
            const sub = document.querySelector('.subtitle');
            if (sub && d.last_updated) {
                sub.textContent = (d.grading_period || '') +
                    ' \u00b7 Updated ' + formatDate(d.last_updated);
            }
            if (!d.courses.length) {
                document.getElementById('course-cards').innerHTML =
                    '<p style="text-align:center;color:var(--text-muted);' +
                    'padding:2rem">No grade data available yet.</p>';
                return;
            }
            // Missing panel
            const missing = [];
            d.courses.forEach(c => {
                c.assignments.forEach(a => {
                    if (a.is_missing) missing.push({course: c.name, ...a});
                });
            });
            const mp = document.getElementById('missing-panel');
            if (missing.length) {
                mp.innerHTML = '<h2>Missing Assignments</h2><ul>' +
                    missing.map(m =>
                        `<li><strong>${m.course}</strong>: ${m.name} (${m.date})</li>`
                    ).join('') + '</ul>';
            }
            // Course cards
            const cc = document.getElementById('course-cards');
            cc.innerHTML = d.courses.map((c,i) =>
                `<div class="card" onclick="toggleCourse(${i})">` +
                `<div class="card-name">${c.name}</div>` +
                `<div class="card-grade" ` +
                `style="color:${gradeColor(c.overall_grade)}">` +
                `${c.overall_grade}</div>` +
                `<div class="card-name">${c.period}</div></div>`
            ).join('');
            // Course detail sections
            const cd = document.getElementById('course-details');
            cd.innerHTML = d.courses.map((c,i) => {
                const sorted = [...c.assignments].sort((a,b) =>
                    b.date.localeCompare(a.date));
                const rows = sorted.map(a =>
                    `<tr><td>${a.date}</td><td>${a.name}</td>` +
                    `<td style="color:` +
                    `${gradeColor(a.letter_grade)}">` +
                    `${a.letter_grade}</td>` +
                    `<td>${a.points_earned}/${a.points_possible}</td>` +
                    `<td>${statusBadge(a)}</td></tr>`
                ).join('');
                return `<div class="course-section" id="course-${i}">` +
                    `<div class="course-header" onclick="toggleCourse(${i})">` +
                    `<h3>${c.name} — ${c.instructor}</h3>` +
                    `<span class="toggle">&#9660;</span></div>` +
                    `<div class="course-body"><table>` +
                    `<tr><th>Date</th><th>Assignment</th><th>Grade</th>` +
                    `<th>Score</th><th>Status</th></tr>` +
                    rows + `</table></div></div>`;
            }).join('');
        }
        function toggleCourse(i) {
            const body = document.querySelector(`#course-${i} .course-body`);
            body.classList.toggle('open');
        }
"""
