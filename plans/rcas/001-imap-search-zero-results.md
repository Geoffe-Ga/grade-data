# RCA-001: IMAP Search Returns Zero Emails

**Date**: 2026-02-12
**Status**: Fixed and deployed
**Severity**: Critical (entire pipeline produces empty data)

## Symptom

The GitHub Actions workflow runs successfully but `grades.json` contains:
```json
{"last_updated": "...", "student": "", "grading_period": "", "courses": []}
```

Workflow log output:
```
Found 0 emails from 'pwsupport@unionsd.org' since 05-Feb-2026
Saved grades for  (0 courses)
```

## Timeline

| Commit | Change | Result |
|--------|--------|--------|
| `f1b44b7` | Changed search from FROM to SUBJECT-based | 0 results (wrong subject string) |
| `ced9ae1` | Fixed workflow permissions | Unrelated to search |
| `ceecdc9` | Added diagnostic logging | Revealed 107 emails in INBOX, 0 matching |
| `13d8eee` | Reverted to FROM-based search | Still 0 results |

## Investigation

### Evidence Collected

1. **Diagnostic IMAP search** (from workflow run `ceecdc9`):
   - `SINCE "05-Feb-2026"` in INBOX: **107 emails found**
   - `SUBJECT "Progress Report From Dartmouth Middle School"`: **0 matches**
   - First 10 subjects logged: all marketing/unrelated emails, zero PowerSchool

2. **Real email analysis** (`Progress report for Layla H..eml`):
   - `From: "pwsupport@unionsd.org" <pwsupport@unionsd.org>`
   - `To: Undisclosed-Recipient:;` (email was **BCC'd**)
   - `Delivered-To: geoffe.gallinger@gmail.com`
   - Subject: `Progress report for Layla H.`
   - Content-Type: `multipart/alternative` (text/plain + text/html + image)

3. **Key deduction**: 107 emails exist in INBOX during the date range, but
   **zero** are from `pwsupport@unionsd.org`. The PowerSchool emails are
   demonstrably delivered to this Gmail account (Delivered-To header), so they
   must exist somewhere other than INBOX.

## Root Cause

**The PowerSchool emails are not in INBOX.** They are in `[Gmail]/All Mail`
(and possibly a custom label) but NOT in the primary inbox.

This happens because:

1. **BCC delivery**: PowerSchool sends grade reports via BCC
   (`To: Undisclosed-Recipient:;`). The recipient's address only appears
   in the `Delivered-To` envelope header.

2. **Gmail auto-filtering**: Gmail commonly auto-archives or categorizes
   BCC'd bulk notifications. A Gmail filter (user-created or automatic)
   is skipping the inbox for these emails, sending them directly to a
   label or archive.

3. **Code assumes INBOX**: `parser.py:285` hardcodes `conn.select("INBOX")`,
   which only searches the primary inbox folder.

### Why Tests Didn't Catch This

The test suite mocks `imaplib.IMAP4_SSL` entirely:
```python
mock_conn.select.return_value = ("OK", [b"1"])
mock_conn.search.return_value = ("OK", [b"1"])
```

The mock returns canned success responses regardless of which folder is
selected. No test asserts that `select()` is called with the correct folder,
and no test simulates the "emails exist in All Mail but not INBOX" scenario.

## Fix Plan (TDD)

### Step 1: Regression Tests (RED)

Write tests that **fail** against the current code:

1. **`test_fetch_selects_all_mail_folder`**: Assert that `conn.select` is
   called with `"[Gmail]/All Mail"` (not `"INBOX"`).

2. **`test_fetch_falls_back_when_all_mail_unavailable`**: If
   `[Gmail]/All Mail` fails (non-Gmail server), fall back to `INBOX`.

3. **`test_fetch_logs_selected_folder`**: Verify log output includes which
   folder was searched.

### Step 2: Implementation (GREEN)

Update `fetch_emails()` to:
1. Try `conn.select('"[Gmail]/All Mail"')` first
2. Fall back to `conn.select("INBOX")` if that fails
3. Log which folder was selected

### Step 3: Refactor (REFACTOR)

- Extract folder selection into a helper function
- Update existing tests to be folder-aware
- Update sample fixture if needed for multipart format

## Affected Files

| File | Change |
|------|--------|
| `grade_data/parser.py` | Fix folder selection in `fetch_emails()` |
| `tests/unit/test_parser.py` | Add regression tests, update existing mocks |

## Validation

- [ ] Regression tests fail before fix (RED)
- [ ] Regression tests pass after fix (GREEN)
- [ ] All 111+ existing tests still pass
- [ ] `./scripts/check-all.sh` passes (7/7)
- [ ] Deploy to GitHub Actions and verify emails are found
