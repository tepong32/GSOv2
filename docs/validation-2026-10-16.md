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

## Receiving HTTP and failure-path checkpoint — 2026-10-17 (unpublished)

Feature branch `codex/receiving-inspection`, based on `405f360`; fetched master
comparison 0/0 before work, with only the unfinished receiving changes present.
Commands use `C:/xxx/_INSTALLS/_HERE/_xxx/gsov2-development/Scripts/python.exe`.

- PASS: `manage.py test inventory.test_receiving --verbosity 1`, 16 tests (0.632 s),
  including complete CSRF-enforced create/line/upload/submit/return/correct/accept
  requests, invalid quantities, self-review denial and view-only permission denial.
- FAIL - CAUSED BY CURRENT WORK: first expanded full run, 32/33; new upload-failure
  test exposed that settings override did not replace the instantiated FileField
  storage. Fixed test isolation by patching the field to temporary FileSystemStorage.
- PASS: `manage.py test --verbosity 1`, 33 tests (2.561 s) after the fix. Audit failure
  rolls back receipt metadata while preserving the unreferenced uploaded file.
- PASS: `manage.py makemigrations --check --dry-run`; `git diff --check`.
- NOT RUN - OUT OF SCOPE for this checkpoint: visual desktop/mobile review, native
  MySQL races, populated 0013/0014 migration/restore, official form acceptance.
  These remain outstanding gates; the feature has not been released or deployed.

Full shell suite is appropriate here because changes touch permissions, shared
asset services, schema and stock materialization. Tests use synthetic records;
the operator database and parallel Finance code were not changed.

## Receiving migration and recovery checkpoint — 2026-10-17 (unpublished)

Fresh fetch again showed HEAD/master 0/0; unfinished feature files remained local.

- PASS: populated copy of the preserved `migration-rehearsal.sqlite3` migrated from
  inventory 0012 through 0014 via `manage.py migrate --noinput`. Compared every row
  in 37 pre-existing application tables (42 rows), excluding migration/content-type/
  permission framework metadata. SQLite integrity and foreign-key checks passed.
  Source SHA-256 remained
  `45264e6e574f76563b2e9ac591882a100688f017bae5675d452c4b17a5ace0d5`.
- PASS: separate synthetic DB seeded through receiving services, accepted six reams
  from a partial delivery, captured SQLite via backup API with writes stopped and
  copied private evidence. All 34 tables compared exactly after restore; file SHA-256
  maps matched, SQLite integrity/FK checks passed. `manage.py check_receiving_evidence`
  reported two checked files with no findings. Deliberate corruption of one restored
  file produced nonzero status and one changed-file finding; copying the source file
  back restored a clean result. Source files stayed unchanged.
- PASS: `manage.py test --verbosity 1`, 35 tests (2.768 s). Added read-only command
  tests distinguish missing/changed/unreferenced files and reject outside paths;
  failed-upload evidence remains preserved and is flagged for investigation.
- NOT RUN - OUT OF SCOPE for this checkpoint: desktop/mobile browser inspection,
  MySQL concurrency/router testing, real operator and GRAND two-store recovery.

Local drill manifests and isolated databases/files:
`C:/Users/Administrator/.codex/backups/gsov2-receiving-rehearsal-20261017-001404/`
(`migration-result.json`, `restore-result.json`). They are protected local rehearsal
artifacts, not repository fixtures or evidence of production acceptance. The original
operator database, original backup, and parallel Finance code were not modified.

## Receiving browser checkpoint — 2026-10-17 (unpublished)

Fresh fetch: branch and remote primary still 0/0; feature changes local. Playwright
CLI ran in a named `gso-receiving` session against loopback port 8017 and a disposable
`browser.sqlite3` copied from the synthetic drill. No operator login or database used.

- FAIL - CAUSED BY CURRENT WORK: receiving-only user hit the asset dashboard's 403
  after sign-in. Fixed dashboard entry to check receiving permission and redirect
  to receiving when asset view permission is absent; asset data remains inaccessible.
- FAIL - CAUSED BY CURRENT WORK: line and evidence `kind` fields shared an HTML ID,
  causing duplicate/missing accessible labels. Fixed distinct form auto-ID formats.
- PASS: browser login, delivery-draft creation and detail navigation; corrected
  Workspace route lands at receiving for the restricted user. Draft/accepted detail
  screenshots inspected at desktop 1440×1000 and phone 390×844. Phone document width
  equals viewport (390), and draft DOM has no duplicate nonempty IDs.
- PASS: `manage.py test --verbosity 1`, 36 tests (2.652 s), including regression
  checks for receiving-only landing and unique form IDs/labels.
- NOT RUN - OUT OF SCOPE: complete reviewer journey in browser; it is covered by
  enforced-CSRF HTTP tests, not claimed as browser acceptance. Native MySQL checks
  and human acceptance remain pending. Initial console errors were the diagnosed
  dashboard 403 and missing favicon; receiving screens returned HTTP 200.

Screenshots: ignored `output/playwright/receiving-desktop.png`,
`receiving-phone.png`, `receiving-accepted-phone.png`. Browser logs and screenshots
are excluded from Git to avoid accidentally publishing session evidence.

## Native MySQL receiving checkpoint — 2026-10-17 (unpublished)

Fresh fetch: 0/0 vs remote primary with unfinished local changes. Initialized a separate
owned MySQL 8.4.11 fixture under `C:/xxx/_INSTALLS/_HERE/_xxx/gsov2-mysql-validation-20261017`,
bound to 127.0.0.1:33317 with X protocol disabled and a generated local password.
The parallel Finance server was not used or modified.

- FAIL - CAUSED BY CURRENT WORK: initial 36-test MySQL run had six errors following
  the streamed-download test. It explicitly closed the response after Django's test
  streaming iterator already closed it; the second request-finished signal closed
  the transactional test connection. Removed the redundant close.
- PASS: `python scripts/run_mysql_tests.py`, all 39 tests, 7.021 s, no skips. Includes
  concurrent same-receipt stock acceptance, two receipts with duplicate tags, and
  normal asset creation competing with receiving. Each permits one result and one
  controlled validation conflict. Fresh schema migrations through 0014 completed.
- PASS: `python manage.py test --verbosity 1`, 39 discovered, 36 executed and three
  native-only skips, 3.214 s. SQLite cannot prove row locking.
- OPEN - PRE-EXISTING: W036 for conditional unique constraints on AssetTransfer and
  AssetDisposalCase, confirmed in baseline models. MySQL does not create these
  constraints. A portable replacement and transition race checks are still required;
  a green receiving suite does not establish those unrelated lifecycle invariants.

The committed native runner follows GRAND's isolated testing approach without
replacing its default/finance router or claiming two-store integration validation.

## Portable lifecycle integrity — 2026-10-17 (unpublished)

Compared GRAND's actual `accounting.BankStatementMatch.active_identity_marker` and
migration 0011. Applied the same nullable-marker/ordinary-uniqueness design to GSO
pending transfers and open disposal cases, with duplicate preflight before DDL.

- FAIL - CAUSED BY CURRENT WORK: populated SQLite rehearsal rejected addition of a
  STORED generated column, despite passing empty-schema tests. Changed the unpublished
  markers to virtual columns; this preserves the same DB-enforced uniqueness and
  permits upgrades on populated SQLite. Added an automated populated-upgrade test.
- PASS: `scripts/run_mysql_tests.py`, all 45 tests, 9.867 s, no skips or warnings.
  Direct and concurrent inserts enforce one open record; closed histories remain;
  reopening a conflicting row fails. Populated migration preserves original fields.
  Duplicate native cases cause preflight failure before marker columns are added,
  with both historical records retained.
- PASS: `manage.py test --verbosity 1`, 45 discovered, 39 executed and six native-only
  skips, 4.943 s. `manage.py makemigrations --check --dry-run`: no changes.
- PASS: isolated populated SQLite drill copy `lifecycle-0015.sqlite3` upgraded to0015
  after the virtual-marker fix; original operator data remained untouched.

This resolves the prior W036 finding for current models. The separate server is owned
by this task; normal test runs removed their random schemas. No Finance schema or
production configuration was changed.

## Receiving publication evidence - 2026-10-17

Version Manager README/inspect/preview preceded the actual minor release, commit
`7d3547fcc86e570e79db4bfc67f742335c38cf2d`. Preview touched only VERSION/CHANGELOG;
historical evidence was preserved. Explicit intended files were staged. No runtime
DB/uploads, browser artifacts or parallel Finance work were published.

PASS: optional-native/runtime dependency audit (no known vulnerabilities), pip check,
system check and diff whitespace check. Feature CI38932007629 passed before canonical
master was fast-forwarded and pushed. Remote master/tag matched the release commit;
canonical status was clean and operator DB hash matched the preservation manifest.
No operator migration or deployment occurred. Primary GSO checks CI38932087704 passed
at the release commit. This follow-up changes documentation only. The broader integration,
Finance attribution and remaining roadmap remain incomplete.


## GRAND source adapter checkpoint - 2026-10-17 (unpublished)

PASS: four standalone payload tests (0.001s); actual GRAND source tests, five tests
(0.080s), using clean published GRAND 32ab046 and isolated SQLite default/finance
schemas. Command: `grand-auth-venv/Scripts/python.exe scripts/run_grand_source_tests.py
--grand-root C:/Users/Administrator/.codex/worktrees/gsov2-grand-source-validation`.
Log: `.tmp/grand-source-validation-latest.log`. That run did not install inventory.

FAIL - CAUSED BY CURRENT WORK in initial harness fixtures: duplicate profile creation
and stale reverse-profile cache from GRAND's user creation signal. Fixed by updating
the signal-created profile and refreshing the fixture user; completed run above passes.

PASS: `gsov2-development/Scripts/python.exe manage.py test inventory --verbosity 1`,
49 discovered, 43 executed, six native-only skips, 3.537s. Scope: optional source
adapter plus existing operational regression coverage. No operator database changes.
PASS: expanded runner installs inventory and applies the full migration graph with
GRAND's users and database router. Six tests in 0.090s, exit 0; log
`.tmp/grand-inventory-validation-latest.log`. New test creates receipt/audit records
using core identities, proves no Finance queries/table, and denies an outsider.
Both fresh SQLite databases were destroyed normally. Native concurrency, populated
imports and routes/UI integration remain NOT RUN - OUT OF SCOPE for this checkpoint.

PASS: first native GRAND integration run, seven tests in 0.953s, MySQL 8.4.11,
actual GRAND router and inventory migrations, exit 0. Log
`.tmp/grand-native-validation-latest.log`; both test schemas destroyed. Source
replacement used a separate connection but did not yet assert observed lock waiting.
PASS: strengthened native run, seven tests in 0.925s, exit 0; log
`.tmp/grand-native-lock-proof.log`. performance_schema confirmed the reader waited
while preparation held the case lock and then rejected the replaced line. Both test
schemas were verified absent and the owned MySQL server shut down normally.
Full standalone release suite PASS: 49 discovered, 43 executed, six native skips,
4.124s. Migration drift, pip check and diff check PASS. Operator hash unchanged.
