# OWASP CTF Academy

A gamified, hands-on platform for learning the OWASP Top 10 (2025) vulnerability
classes by exploiting them yourself, then capturing a flag to prove it.

Built with Flask + SQLite. Every vulnerability is deliberately planted and
documented in code comments — this is a learning tool, not a production app.

## Status: all 5 core levels complete

| Level | OWASP Category | Status |
|---|---|---|
| 1 | A05:2025 - Injection | ✅ Done |
| 2 | A01:2025 - Broken Access Control | ✅ Done |
| 3 | A07:2025 - Authentication Failures | ✅ Done |
| 4 | A02:2025 - Security Misconfiguration | ✅ Done |
| 5 | A10:2025 - Mishandling of Exceptional Conditions | ✅ Done |

## Level highlights

- **Level 1 (Injection)**: classic SQL injection login bypass via unescaped
  string concatenation. Demonstrates why parameterized queries matter.
- **Level 2 (Broken Access Control)**: IDOR — view another user's private
  note by changing an ID, no ownership check on the backend. Includes a
  realistic, non-sequential ID scheme and a discoverable in-app hint.
- **Level 3 (Authentication Failures)**: a login with *zero* SQL injection
  risk (properly parameterized), but no rate limiting at all. Includes a
  50-entry password wordlist and a real Python `requests`-based brute-force
  script (`scripts/brute_force_level3.py`) that cracks it in under a second.
- **Level 4 (Security Misconfiguration)**: a debug page left exposed at
  `/debug/status`, discoverable only by checking `/robots.txt` — a real
  recon technique. Demonstrates that "security through obscurity" (hiding
  a path instead of actually protecting it) isn't real security.
- **Level 5 (Mishandling of Exceptional Conditions)**: a "members only" check
  wrapped in `try/except` that was "defensively" written to grant access on
  *any* error instead of denying it — so a non-numeric `membership_id` (e.g.
  `abc`) bypasses the check entirely. While building this level, caught and
  fixed two real bugs of my own: the flag was originally shown on *any*
  successful access (including the legitimate `membership_id=1` case),
  giving away the answer before the exploit was even attempted; and the
  "Check Access" form caused a jarring scroll-to-top on every submission.
  Fixed by deriving a separate `exploit_triggered` flag (only true when
  access was granted *via* the exception path) to gate the flag display,
  and by anchoring the form's redirect to the relevant section of the page.

## Features

- **Two difficulty modes**: Beginner (sequential unlocks, tutorial hints) and
  Expert (all levels open, no hints).
- **Hearts/lives system**: wrong flag submissions cost a heart.
- **Event logging**: every meaningful action (failed attempts, successful
  exploits, heart loss) is logged to a database table — the foundation for
  an upcoming honeypot/detection layer.

## Running locally

```bash
python -m venv venv
venv\Scripts\Activate   # Windows
pip install flask
python app.py
```

Then visit `http://127.0.0.1:5001`.

## Roadmap

- Honeypot system (fake routes that log/penalize suspicious probing)
- Remaining OWASP categories (Supply Chain, Crypto Failures, Insecure Design,
  Integrity Failures, Logging & Alerting Failures) as a v2 expansion
- Production-style deployment (Linux host, WSGI server, reverse proxy)