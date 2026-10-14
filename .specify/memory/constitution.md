<!--
Sync Impact Report
- Version change: (none) → 1.0.0
- Modified principles: template placeholders → Fansboda-specific principles
  - [PRINCIPLE_1_NAME] → I. Private Invite-Only Access
  - [PRINCIPLE_2_NAME] → II. Schema Ownership Outside This App
  - [PRINCIPLE_3_NAME] → III. Tests Gate Changes
  - [PRINCIPLE_4_NAME] → IV. Defense in Depth
  - [PRINCIPLE_5_NAME] → V. Stay On The Existing Stack
- Added sections: Security & Data Constraints; Development Workflow
- Removed sections: none (template scaffold replaced in place)
- Follow-up TODOs: none
-->

# Fansboda Constitution

## Core Principles

### I. Private Invite-Only Access

Fansboda is a private application for Metallen AB. It MUST NOT become a
public product.

- Signup MUST reject emails that are not on `ALLOWED_EMAILS`.
- Authenticated routes MUST require a logged-in, whitelisted user
  (`@allowed_user_required` or `@role_required`).
- Admin-only surfaces MUST use `@admin_required`.
- New accounts MAY be created by the app. Schema ownership for `user`
  stays with this application’s models; do not expose open registration.

Rationale: the app handles tenant billing and internal stock views. Any
unauthenticated or non-whitelisted access is a defect.

### II. Schema Ownership Outside This App

This Flask app MUST NOT create or migrate Neon schema on deploy.

- MUST NOT reintroduce Flask-Migrate, Alembic, or `flask db upgrade`
  in CI/CD.
- MUST NOT call `db.create_all()` in development or production app
  startup. Tests MAY use `create_all()` on in-memory SQLite only.
- SQLAlchemy models MUST map to tables that already exist. When Neon
  columns change, update the model to match. Do not generate migrations
  here.
- `metrics` is filled by an external ingestion pipeline. This app
  reads it. Do not treat the web app as the source of stock history.
- The `user` table is written by login/signup and lockout logic. Those
  writes are allowed. DDL for `user` is still owned outside this repo
  unless an explicit constitution amendment says otherwise.

Rationale: Neon schema already exists. Duplicate DDL caused failed
upgrades and conflicting ownership.

### III. Tests Gate Changes

Behavior changes MUST ship with tests that would fail if the behavior
regressed.

- Route, auth, form, and model changes MUST update `tests/`.
- Security-sensitive changes (auth, CSRF, roles, error pages, email
  whitelist) MUST include or extend tests in `tests/test_security.py`
  or `tests/test_security_integration.py`.
- CI MUST keep running pytest before image push. Do not weaken that
  gate to land a feature.
- UI changes MUST be verified in the browser (or the closest substitute)
  before the work is called done.

Rationale: this is a small private app; tests are cheaper than a broken
login or a leaked 500 page.

### IV. Defense in Depth

Security controls already in the stack MUST stay on by default.

- Forms and state-changing POSTs MUST use Flask-WTF CSRF.
- Talisman CSP MUST stay environment-specific. New script/style sources
  MUST be added to the CSP allowlist, not bypassed with `'unsafe-inline'`
  scripts in production.
- Passwords MUST be bcrypt-hashed. Lockout on failed logins MUST remain.
- Secrets MUST live in environment variables or GCP Secret Manager. MUST
  NOT commit `.env`, service-account JSON, or certificate private keys.
- Production cookies MUST remain Secure and HttpOnly.
- CORS MUST stay limited to Fansboda hostnames.
- Generic 500 pages MUST NOT leak exception details when `DEBUG` is
  false.
- Dev-only diagnostic routes MUST stay behind `@dev_only` (404 in
  production).

Rationale: the app sends email and holds credentials. Convenience
shortcuts around these controls are not acceptable.

### V. Stay On The Existing Stack

New work MUST fit the current architecture unless the constitution is
amended.

- Backend: Flask 3 application factory, blueprints under `src/routes/`,
  SQLAlchemy models, Jinja2 templates, Bootstrap 5 + existing JS.
- Runtime: Gunicorn behind Nginx on the GCP VM. Docker Compose for
  dev and production. uv for local Python dependencies.
- Data: Neon PostgreSQL via `DATABASE_URL` (Secret Manager fallback
  allowed).
- Do not add a new framework, SPA, extra datastore, or background
  worker unless the feature cannot be done with the current stack.
- Prefer small, local changes over new abstraction layers.

Rationale: one VM, one Flask app, two features. Extra moving parts
increase ops cost without benefit.

## Security & Data Constraints

- Electricity-bill emails MUST go through the existing Gmail service
  account path. Do not log message bodies or recipient lists at info
  level.
- Stock heat scores and charts MUST be derived from `Metric` rows. Do
  not invent prices client-side except for display formatting.
- Health checks (`GET /health`) MAY stay unauthenticated. Everything
  else that shows tenant or market data MUST be authenticated.
- Rate limiting and TLS terminate at Nginx. Application code MUST
  still assume the network is hostile.

## Development Workflow

- Default local package workflow is uv (`uv sync`, `uv run`). Do not
  require a manually activated virtualenv.
- Feature work follows Spec Kit when a feature is specified:
  specify → plan → tasks → implement. Smaller fixes MAY skip to
  implementation if they do not change product behavior.
- Do not commit unless asked. Do not force-push `main`/`master`.
- Deploy remains GitHub Actions → Docker Hub → GCP VM over IAP.
  Certificate renewal follows `LETSENCRYPT_CERT_RENEWAL_RUNBOOK.md`.
- Keep `dev` and production compose files separate. Do not point a
  local debug server at production secrets unless explicitly requested.

## Governance

This constitution is the default for agent and human work in this
repository. If a practice in docs or older comments conflicts (for
example leftover Flask-Migrate notes), this file wins.

Amendments:

- PATCH: wording and clarifications that do not change obligations.
- MINOR: new principle or materially stronger rule.
- MAJOR: removal or incompatible redefinition of a principle.

PRs and agent sessions that touch auth, schema, deploy, or secrets MUST
check compliance with sections I–IV. Unjustified complexity MUST be
rejected.

Spec Kit commands (`/speckit-specify`, `/speckit-plan`, and later steps)
MUST read this file and treat MUST rules as constraints, not suggestions.

**Version**: 1.0.0 | **Ratified**: 2026-08-29 | **Last Amended**: 2026-08-29
