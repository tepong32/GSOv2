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

Native integration limitation: the clean published GRAND source at `32ab046`
emitted 23 models.W036 warnings for conditional uniqueness in account, accounting,
departments, finance, leave_mgt, reporting, tracepoint and vouchers. None concern
inventory. These constraints are not created by MySQL; the seven passing tests do
not establish safety for those unrelated workflows. This is evidenced existing
GRAND schema behavior, not a new GSO migration regression. The exact model list is
retained in `.tmp/grand-native-lock-proof.log`, and the parallel Finance review note
flags the issue. Do not claim the full integrated system is production-ready.


## Reviewed attribution draft - 2026-10-17 (unpublished)

PASS: `grand-auth-venv/Scripts/python.exe scripts/run_grand_source_tests.py --grand-root
C:/Users/Administrator/.codex/worktrees/gsov2-grand-source-validation`, SQLite,
15 discovered, 14 executed, one native-only skip, 0.581s, exit 0. Actual GRAND
migration graph plus optional inventory_finance initial migration. Eight new tests
cover approval/withdrawal history, no Finance queries, scoped reads, retry identity,
amount precision/capacity, unaccepted receipts, UAT/self-review denial, stale versions,
replacement requiring withdrawal and stale review replay. Both schemas destroyed.
Log `.tmp/grand-attribution-validation.log`; source freeze under its recorded runtime.
Native capacity races, populated upgrades and UI are NOT RUN - pending implementation.


PASS: native attribution draft run, 19 tests in 4.128s, MySQL 8.4.11, exit 0.
Includes separate-connection competing approvals, duplicate approval and identical
request retries. Both schemas removed, owned server stopped. Log
`.tmp/grand-attribution-native.log`. Existing GRAND W036 warnings remain as recorded.
This did not test aggregate support across different claims against one receipt's
value; code review identified that missing control and it must be fixed before release.
UI HTTP run is pending; browser verification not performed yet.


FAIL - CAUSED BY CURRENT WORK: first HTTP run (23 discovered, four native skips,
2.573s) failed the expiry fixture because globally mocking signing.loads also broke
session decoding. Fixed by signing an old-timestamp proposal only. Other tested HTTP
paths passed; the corrected combined run is pending. Receipt-wide cross-claim capacity
checks and tests were added after this run and are not credited to its result.


PASS: corrected combined MySQL/HTTP run, 26 tests, 7.930s, exit0, no skips.
Receipt-wide cap across claims and unknown-cost rejection are covered, including
independent-connection approvals of different cases against the same receipt.
Log `.tmp/grand-attribution-capacity-http-native.log`. Existing GRAND W036 warnings
remain documented. Both test schemas removed; owned server stopped normally.

PASS: Playwright actual-browser clerk login, preview, submit, separate reviewer login,
approve and withdraw. Original approval and all three events remain visible. Screens
inspected at1440x1000 and390x844; proposed/approved mobile width checks show no
horizontal overflow or duplicate IDs. Screenshots output/playwright/claim-*.png.
Preview limitation: isolated media omits GRAND defaults grand-mark.svg and
 default_user_dp.png, causing image404s. No operator media was copied. Browser sessions
closed and preview port8018 stopped. Ctrl-C ended preview with exit1 before automatic
SQLite deletion; its two synthetic databases remain for recovery rehearsal.


## Claim support release checks and recovery - 2026-10-17

PASS: stopped synthetic paired SQLite recovery under
`C:/Users/Administrator/.codex/backups/gsov2-attribution-rehearsal-20261017-011803`.
All193 default and83 finance tables matched row counts/content hashes after restore;
integrity and foreign-key checks passed. Deleted a synthetic approval event from the
restored copy, detected the mismatch, restored again, and verified proposed/approved/
withdrawn history plus retained withdrawn status. Source hashes unchanged. Manifest
records per-table hashes. Database-only coverage; no private attachment fixture set.

PASS: full standalone suite49 discovered/43 executed/six native skips,3.370s.
Actual GRAND `check` and `makemigrations inventory inventory_finance --check --dry-run`
passed; no migration drift. Pip check and whitespace check passed. GitHub reports no
rulesets and no master branch protection; use branchCI before integration regardless.

## Maintenance development checks - 2026-10-17

Fresh `git fetch origin` on `codex/asset-maintenance` showed HEAD/origin/master 0/0
at28da3f1; only the prior release handoff was dirty before new feature work.
Migration0016, operational services, staff screens and private evidence are in
development. These results do not establish release or production readiness.

PASS: `python manage.py test inventory --noinput`: 60 discovered, 54 executed,
six native-only skips,4.192s before adding three native maintenance races. Eleven
maintenance service/HTTP tests exercise authorization, lifecycle exclusion, stale
writes, validation, event rollback, custody/cost preservation, evidence corruption,
download scope/headers, CSRF and open/work/close rendering. Model drift check and
`git diff --check` passed.

FAIL - CAUSED BY CURRENT WORK: first `python scripts/run_mysql_tests.py inventory`
had six errors in63 tests,12.096s. The new download test called `response.close()`
directly, emitting request_finished outside Django test client's streaming wrapper
and closing the enclosing MySQL test transaction. Later errors cascaded from that
closed connection. Corrected the test to consume `response.streaming_content`
through the wrapper and assert the actual downloaded bytes. No product workaround
or transaction-validation bypass was introduced. First log `.tmp/maintenance-native.log`.

PASS: reran the full native command on a new random schema: 63/63,12.802s, no skips
and no system-check issues. Log `.tmp/maintenance-native-corrected.log`. Added races
cover competing maintenance starts, maintenance versus asset handoff and duplicate
completion, asserting one retained result. Historical lifecycle migration tests now
restore graph leaves rather than leaving the database at0015. MySQL8.4.11 used only
owned loopback33317; verified no `gso_test_` schemas remain and normal shutdown.

NOT RUN - OUT OF SCOPE of this checkpoint: actual-GRAND maintenance authorization,
browser review, populated0016 upgrade and evidence backup/restore/reconciliation.
These remain required before release. No operator migration, grant, deployment,
Finance code edit, vm-commit, integration or push occurred for this feature yet.

## Maintenance final validation and recovery - 2026-10-17

PASS: targeted `manage.py test inventory.test_maintenance inventory.test_maintenance_migration
inventory.test_receiving --noinput`:33 tests,2.011s. New maintenance evidence checker
reuses the receiving checker's namespace-safe local inspection, detecting corruption,
missing files and orphan uploads without modifying them. Populated0015-to0016 replay
compares every pre-existing inventory table and preserves the legacy maintenance
status without inventing cases. Full native `scripts/run_mysql_tests.py inventory`
then passed65/65,15.703s, including the populated migration and three races.
Log `.tmp/maintenance-final-native.log`.

PASS: actual GRAND32ab046 SQLite integration29 discovered/24 executed/five native
skips,2.777s, log `.tmp/grand-maintenance-sqlite.log`. Real employee profiles and
GRAND explicit grants/UAT controls were used. An ungranted superuser cannot manage
maintenance; another owner cannot read the case; repair operations issue no queries
to the Finance store. The existing claim source/attribution/HTTP checks also passed.
Actual GRAND model checks and `makemigrations inventory inventory_finance --check
--dry-run` passed in isolated settings; no schema drift. No GRAND source edits.

PASS: real browser login, asset navigation, opening a case, saving work/cost/reference,
uploading a private bill and completing with a returned-to-service outcome. Screens
visually checked at1440x1000 and390x844: `output/playwright/maintenance-open-desktop.png`,
`maintenance-open-mobile.png`, `maintenance-completed-mobile.png`. Completed mobile
has viewport/scroll width390 and no duplicate IDs. Initial favicon404 is the only
observed browser console resource error. Browser closed; preview port8019 stopped.

PASS: stopped synthetic SQLite/private-file recovery at
`C:/Users/Administrator/.codex/backups/gsov2-maintenance-recovery-20261017-nzu80ff7`.
Backed up, restored and reconciled all37 tables using row counts/content SHA-256;
integrity/FKs valid. Completed case and all four events preserved. Reconciliation
checked the retained bill, detected deliberate corruption and loss in the restored
copy, then passed after copying back the backup evidence. Source database hash
unchanged. Manifest records table/file hashes. This is not an online MySQL or
operator-data restoration claim. Synthetic source retained in
`.tmp/maintenance-preview-_g03g7vp`; no live preview/browser process remains.

PASS: full shell `manage.py test --noinput`:65 discovered/56 executed/nine native
skips,7.048s; `.tmp/maintenance-release-shell.log`. Migration drift, `pip check`
and whitespace checks pass. GitHub API shows no rulesets or master protection.
External Version Manager README reviewed; inspect/preview proposed the maintenance minor release
updating only VERSION/CHANGELOG.

PASS: final actual-GRAND native command `scripts/run_grand_source_tests.py --grand-root
C:/Users/Administrator/.codex/worktrees/gsov2-grand-source-validation --mysql`:29/29,
8.430s, no skips. Log `.tmp/grand-maintenance-native.log`. The same23 existing GRAND
W036 warnings remain, none in inventory/inventory_finance. Both disposable schemas
removed; no `gso_test_` or `gso_grand_test_` schema remains. Owned MySQL stopped
normally. Canonical master remains28da3f1 and operator DB hash matches preservation
checkpoint before release. External vm-commit and branch/primary CI are next.

Release completed: actual external Version Manager minor commit3905a74 (tag recorded
in CONTINUE and the changelog),
feature branch `codex/asset-maintenance` pushed. BranchCI38941638939 PASS (29s),
including dependency audit, model/drift checks and full regression. Canonical clean
master fast-forwarded and pushed; remote master/tag match
`3905a74f7a0c566334145e063474cb49fe71cf53`. PrimaryCI38941747339 PASS (27s).
Operator database SHA-256 remains
`5c6c3c66e46d8a6f4a95799806ec96f4ef3fda923027adba29d63e9f337a2039`.
No deployment or operator migration. Parallel Finance note updated without changing
its source/migrations/shared handoff. Release-result documentation uses separate
`codex/maintenance-release-notes`, created after fresh fetch0/0 with clean worktree.
