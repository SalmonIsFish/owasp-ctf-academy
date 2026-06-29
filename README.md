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
| 6 | Capstone - Chained Exploitation | 🚧 In Progress (Session A complete) |

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
- **Level 6 (Hacker — The Storefront, capstone)**: a multi-page mini
  e-commerce site requiring a *chained* exploit rather than one isolated
  bug. Unlocks only once all 5 prior levels are solved — in both Beginner
  and Expert mode, the one level where difficulty doesn't matter. No
  hearts here; this level is meant to feel like a real, lightly time-boxed
  pentest engagement rather than a tutorial puzzle.

  **The chain:** checkout sums client-submitted hidden price fields instead
  of re-deriving totals from the product catalog (price tampering), letting
  a $129.99 item be "purchased" for $0.01 by editing one HTML attribute in
  dev tools. The resulting order is then accessible via a sequential,
  unauthenticated order-ID lookup (IDOR) — the same root vulnerability
  class as Level 2, but discovered here as the second half of a chain
  rather than in isolation. Walking the order IDs surfaces a honeytoken: a
  decoy flag that looks real but, if submitted, marks the player
  "suspicious" and starts a live, server-enforced 120-second countdown
  (displayed via a small JS badge — the server, not the client, is always
  the source of truth for whether time has actually run out). The real
  flag sits in a separate order, reachable in the same IDOR sweep.

  Session A (storefront + the planted vulnerability chain) is complete and
  tested end-to-end in-browser. Sessions B (a "toy" WAF — pattern-blocking
  + rate-limiting middleware) and C (honeypot fake endpoints + a live
  security-alert dashboard tying into `event_log`) are planned next.

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

- Level 6 Sessions B & C: WAF-style middleware (pattern blocking +
  rate limiting) and a honeypot/security-alert dashboard, layered on top
  of the Session A storefront to require *bypassing defenses* before
  reaching the planted vulnerabilities
- Remaining OWASP categories (Supply Chain, Crypto Failures, Insecure Design,
  Integrity Failures, Logging & Alerting Failures) as a v2 expansion
- Production-style deployment (Linux host, WSGI server, reverse proxy)