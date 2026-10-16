# GSO alignment foundation validation — 2026-10-16

Scope: UUID migration/export prerequisite, dependency update, stock-owner fix,
service input restrictions and deployment settings. Full shell suite selected
because these affect shared models, permissions, migrations and dependencies.
Working directory: `C:/Users/Administrator/.codex/worktrees/gsov2-receiving-safety`.
Runtime below: `C:/xxx/_INSTALLS/_HERE/_xxx/gsov2-development/Scripts/python.exe`
(Python 3.11; newly installed isolated environment, original venv unchanged).

| Command / check | Actual result |
| --- | --- |
| `git fetch --prune origin`, status, `git rev-list --left-right --count HEAD...origin/master` before edits | PASS: 0/0 at `64e458a`; operator DB modification identified and preserved. |
| Original `.venv/Scripts/python.exe manage.py test --verbosity 1` before changes | PASS: 7 tests, 0.657 s. This baseline has limited historical workflow coverage. |
| `python manage.py test --verbosity 1` after changes | PASS: 16 tests, 2.166 s, no skips. Includes original seven and nine foundation/migration/security cases. |
| `python manage.py makemigrations --check --dry-run` | PASS: no model/migration drift. |
| `python manage.py check` | PASS: no issues. |
| `python -m pip check` | PASS: no broken requirements. |
| `python -m pip_audit -r requirements.txt --progress-spinner off` | PASS: no known vulnerabilities reported for resolved requirements at check time. |
| `python manage.py check --deploy` with synthetic `DEBUG=0`, strong test secret, explicit host and absolute private path | PASS with W005 and W021 warnings: subdomain HSTS and preload deliberately disabled pending actual domain rollout. No production settings/secrets used. |
| `git diff --check` | PASS. |
| SQLite backup API snapshot + integrity_check; SHA-256 comparison of operator original/raw copy | PASS: integrity_check `ok`; raw copy and original bytes equal; no operator migration. |
| `GSO_DATABASE_PATH=<protected restored copy> python manage.py migrate --noinput` | PASS: actual operator snapshot copied to an isolated path, migrated through 0012; original table counts, link identities, distinct UUIDs and SQLite integrity verified. Original DB hash unchanged. |
| Feature GitHub workflow at `e642d9e`, run `38927980234` | PASS: dependency consistency/audit, system checks, migration drift and full regression on Ubuntu/Python 3.11. |
| Native MySQL and actual GRAND router/import integration | NOT RUN — ENVIRONMENTAL: not configured for this standalone shell; parallel Finance's native environment is not borrowed or disrupted. Required before GRAND merge. |
| Browser layout / official form outputs | NOT RUN — OUT OF SCOPE: no templates/UI fields or official outputs changed. Django HTTP tests exercise export, list, detail and rejected cross-office action routes. |
| Full data/evidence restore, penetration testing, LGU acceptance | NOT RUN — ENVIRONMENTAL: requires coordinated target deployment, evidence set and operational review. No production-readiness claim. |

Populated migration replay goes from 0011 to current using distinct historical
assets (including duplicate legacy tags), a supply item and receipt movements;
PKs/links/balance survive and every new UUID is populated and distinct. The migration
does not silently deduplicate, split pooled assets, map actors or infer financial data.

Stock tests cover a GSO clerk with action permissions attempting another GSO owner's
list/detail/export/receive/issue/adjust/edit routes and direct service mutations.
Cross-owner access is denied; authorized exports retain the owning UUID and distinguish
zero cost from unknown cost. Identity/owner/actor changes through service dictionaries
are rejected without extra records/audit events.

Two synthetic Git untracking trials failed safely while designing local integration:
checkout refused to overwrite an untracked test file; fast-forward refused to remove
a modified untracked test file. Operator files were never involved. This demonstrates
why canonical integration must preserve data externally rather than force checkout.
The rehearsal directory is under `.codex/worktrees/gso-untrack-rehearsal-tcs6r8bi`.

Version Manager inspect and preview preceded the actual release commit/tag. Preview
initially proposed rewriting historical baseline version mentions; these were
expressed as immutable baseline commit references before release so historical facts
were preserved. Only VERSION and CHANGELOG were then automatically updated.
Canonical/remote primary and tag were verified at `e642d9e`; operator bytes were
rechecked unchanged after integration. Primary CI and later documentation status
are linked from CONTINUE.md. Local tests do not stand in for a future GitHub run.
