# OWASP CTF Academy

A gamified, hands-on platform for learning the OWASP Top 10 (2025) vulnerability
classes by exploiting them yourself, then capturing a flag to prove it.

Built with Flask + SQLite. Every vulnerability is deliberately planted and
documented in code comments — this is a learning tool, not a production app.

## Status: in progress

| Level | OWASP Category | Status |
|---|---|---|
| 1 | A05:2025 - Injection | ✅ Done |
| 2 | A01:2025 - Broken Access Control | ✅ Done |
| 3 | A07:2025 - Authentication Failures | 🚧 In progress |
| 4 | A02:2025 - Security Misconfiguration | ⏳ Planned |
| 5 | A10:2025 - Mishandling of Exceptional Conditions | ⏳ Planned |

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