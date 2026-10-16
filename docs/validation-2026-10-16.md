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

## Employee custody development checkpoint - 2026-10-17

Fresh fetch on clean GSO60d12af showed0/0 before `codex/employee-custody` creation.
Parallel GRAND remains32ab046 with unpublished Form1 work; inspected identity/profile
files have no local differences. Source adapter and migration0017/custody services
are under development, not released. No operator migrations or permission grants.

PASS: initial actual-GRAND source integration33 discovered/28 executed/five native
skips,3.727s; `.tmp/grand-employee-source-sqlite.log`. This preceded source refinements
and custody service changes, so does not validate the final implementation.
PASS: `manage.py test inventory.test_employee_custody_migration --noinput`, one test,
0.815s: historical transfer fields/asset data preserved, distinct per-row public UUIDs,
employee references remain null. No guessed identities from legacy labels.
PASS: `manage.py test inventory --noinput`,67 discovered/58 executed/nine native skips,
9.973s; `.tmp/employee-custody-shell-migration.log`. Migration drift and whitespace
checks passed. Later owner-check ordering adjustment covered by
`manage.py test inventory.test_employee_sources --noinput`:2/2 PASS0.012s, including
rejection of a caller object with a forged owner in favor of the locked database row.

RUNNING: expanded actual-GRAND SQLite integration, log
`.tmp/grand-employee-custody-sqlite.log`, session60414. Poll the confirmed handle;
do not infer failure/restart from a quiet schema-creation phase. Six custody tests
are added alongside the four source tests. Final native races, UI, recovery and
actor-retention review remain before release. No native server or browser is running.

FAIL - CAUSED BY CURRENT WORK: run60414 finished39 discovered with one test error
and five native skips,3.146s. New changed-department test expected ValidationError,
but the existing department-scope check correctly raised PermissionDenied first.
Corrected the test to assert that denial after a fresh user load; separately restore
the department, change the identity name and assert stale-snapshot ValidationError.
No product authority check was loosened. Prior run's disposable databases removed.
Corrected full integration run86403 is live, log
`.tmp/grand-employee-custody-sqlite-corrected.log`; poll before any restart.

Corrected run86403 PASS39 discovered/34 executed/five native skips2.927s. The
subsequent signed HTTP workflow is under validation in `.tmp/grand-custody-http.log`.
PASS: latest shell `manage.py test inventory --noinput`,69 discovered/60 executed/
nine native skips9.666s; `manage.py makemigrations --check --dry-run` clear.
PASS: `scripts/run_mysql_tests.py`, native MySQL8.4.11,69/69 in28.912s; log
`.tmp/custody-native-shell.log`. Includes populated0017 replay and protection of
requested_by/acknowledged_by/cancelled_by historical actors. No operator data used.

FAIL - CAUSED BY CURRENT WORK: new HTTP run42 tests, three errors/five native
skips3.435s. The minimal joined directory query used nested `__pk` in `.only`,
which Django does not resolve as a concrete field in its nested select mask. Fixed
the query to GRAND's concrete `id` fields and retained the minimal column boundary.
Search results also apply GRAND's existing profile-view predicate. Full native
GRAND run is in progress at `.tmp/grand-custody-native.log` (session60476).

PASS: actual GRAND native44/44 in12.481s, `.tmp/grand-custody-native.log`.
Includes duplicate-request and acknowledgment/cancellation races. Existing23 GRAND
W036 warnings remain; none from inventory/inventory_finance. Subsequent final run
covers tighter actor/asset token binding assertions and final UI wording.
PASS: final standalone SQLite69 discovered/60 executed/nine native skips9.882s,
`.tmp/custody-shell-release.log`. Both environments' pip checks clear. Actual GRAND
`check` and `makemigrations inventory inventory_finance --check --dry-run` pass via
isolated harness settings (no operator environment or databases).
PASS: browser search/review/submit then separate recipient acknowledgment. No owner
cancel action offered to incoming recipient from another GSO office. Desktop1440x1000
and mobile390x844 inspected; no page overflow or duplicate IDs; tables scroll inside
panel. Screenshots `output/playwright/custody-*.png`. Missing synthetic logo/avatar
404s only. Sessions and preview8020 stopped; no operator deployment.
PASS: stopped paired SQLite recovery196 default/83 finance tables, retained named
custody/snapshot/accepted actor/audit. Injected loss detected and restored; source
hashes unchanged. Backup `C:/Users/Administrator/.codex/backups/gsov2-custody-recovery-20261017-nj9xiahl`.
Not online MySQL/private-upload/operator recovery. Canonical operator DB hash unchanged.
Parallel Finance fresh fetch0/0; its unpublished Form1 role additions do not change
the UAT predicate used here. Only the separate GSO integration note was edited there.

PASS: final actual-GRAND native44/44 in11.095s, no skips,
`.tmp/grand-custody-native-final.log`, including tightened actor/asset token binding.
Both schemas removed; verified no GSO test schemas remain on owned33317, followed by
normal SQL SHUTDOWN and process completion. No preview/browser/test server remains.
VM inspect/preview plans the custody minor release, updates only VERSION/CHANGELOG.
Repository has no rulesets or master protection; branchCI remains the release gate.

Published custody commit236c5e1 through the actual external Version Manager.
BranchCI38945305792 PASS before canonical master fast-forward/push; remote master
and tag match236c5e1e265bc1a63b97a9d3271133e94b598f10. Final release diff changed
only intended feature/docs and generated VERSION/CHANGELOG. PrimaryCI38945433056
PASS. No operator migration/grants/deployment. Release-result documentation
uses separate `codex/custody-release-notes`, created after clean fetch0/0.

## Custody review workbench - 2026-10-17

Fresh clean55fc7bf fetch0/0 before `codex/custody-review`. GRAND fetched0/0 with
unrelated unpublished Form1 work preserved. No new schema or data mutation workflow.
PASS: `manage.py test inventory.test_employee_sources --noinput`,4/4 in0.454s.
PASS: `manage.py test inventory --noinput`,70 discovered/61 executed/nine native
skips11.670s, `.tmp/custody-review-shell.log`; model drift clear.
FAIL - CAUSED BY CURRENT WORK: actual GRAND SQLite49 discovered, one incorrect test
expectation and seven native skips5.273s, `.tmp/grand-custody-review.log`. GRAND's
explicit-permission helper requires a department; missing-department employee gets
403. Corrected expectation and checked GSO can still view the retained assignment;
no permission rule loosened. Native expanded run37525 is in progress.

PASS: `scripts/run_grand_source_tests.py --grand-root <clean32ab046> --mysql`,50/50
in14.501s, no skips; `.tmp/grand-custody-review-native.log`. Covers all six new review
cases including retained-identity JSON search on native MySQL. Existing23 GRAND W036
warnings remain; none in GSO. Both schemas removed; owned33317 SQL SHUTDOWN completed.
PASS: real GRAND browser office/legacy and moved-employee personal views at1440x1000
and390x844. Personal scope retains assignment, flags HR movement and omits owner
register link. Client/scroll width390, no overflow elements or duplicate IDs.
Screenshots `output/playwright/custody-review-*.png`; only synthetic logo/avatar404s.
Browser sessions and preview8021 stopped. Synthetic fixture retained separately at
`.tmp/custody-review-preview-6ypwa4un`, copied from the previous preserved fixture.
NOT RUN - OUT OF SCOPE: a new migration/recovery rehearsal and full standalone native
suite. This slice changes only GRAND read queries/screens and a dashboard link;
no models, services, file formats or writes changed. Existing populated/recovery
proof remains applicable. Full shell SQLite70 and actual-GRAND native50 cover the
impacted behavior; tests explicitly preserve inventory state and avoid Finance queries.

Release completed through actual Version Manager minor commitfb2eae2. Branch
CI38947590308 PASS before canonical master fast-forward/push. Remote master/tag
matchfb2eae2c59df7669cb228eb344bc3f1521f1469a. Operator hash remains
5c6c3c66e46d8a6f4a95799806ec96f4ef3fda923027adba29d63e9f337a2039.
No installation, operator migration or grants. PrimaryCI38947689210 PASS.
Documentation follow-up uses separate `codex/custody-review-release-notes`, created
from a clean fetch0/0 checkpoint. No source/schema changes in this follow-up.

## Witnessed custody returns — 2026-10-17

Fresh fetch and clean0/0 at efbc671 preceded `codex/witnessed-custody-returns`.
Further fetch0/0 confirmed no upstream change. Finance checkout was fetched and
unrelated Form1 changes preserved; only its authorized GSO integration note changed.
Scope includes schema, custody services, authorization, private files and HTTP, so
full standalone SQLite/native and actual GRAND native integration are appropriate.

PASS: `manage.py test inventory --noinput`,71 discovered/62 executed/nine native
skips17.436s; `.tmp/returns-shell-final.log`. PASS: `scripts/run_mysql_tests.py`,
71/71 in51.702s; `.tmp/returns-native-shell.log`. Populated0017-to0018 test preserves
existing named custody and transfer identities, defaults old movements to
handoffs and enforces the new kind constraint; isolated1/1 PASS1.048s and included
in both full suites. `makemigrations --check --dry-run` and `pip check` PASS.

PASS: initial GRAND service SQLite55 discovered/48 executed/seven native skips in
5.792s, `.tmp/grand-returns-services.log`. Initial expanded actual GRAND MySQL60/60
PASS17.049s, `.tmp/grand-returns-native.log`, including three return races. Final
expanded61-test run adds maintenance overlap and later-custodian evidence privacy.
FAIL - CAUSED BY CURRENT WORK: that run ended61 tests/one error19.332s because the
new maintenance test attempted completion without recording work. The existing guard
correctly rejected it. Corrected the fixture to record work before closing, preserving
the production guard. Corrected native run61/61 PASS16.937s,
`.tmp/grand-returns-native-corrected.log`; both schemas removed and owned MySQL33317
shut down normally. Existing23 native GRAND W036 warnings remain outside GSO.

PASS: actual GRAND browser record receipt, upload retained evidence, independently
confirm and review known GSO-held asset, desktop1440x1000/mobile390x844. Recording
officer cannot confirm. Confirmed page and returned workbench have matching375px
client/scroll widths (15px scrollbar), no duplicate IDs. Screenshots under
`output/playwright/custody-return-*.png` visually inspected. Only synthetic
logo/favicon404s; no application workflow errors. Both browser sessions and
preview8022 stopped. Fixture `.tmp/grand-source-tests-xrmc1cx7` retained.

PASS: stopped synthetic paired SQLite and private-evidence recovery reconciled198
default and83 finance tables plus one retained return file. Original identity,
independent actors, confirmed assignment and three return events survive. Checker
detected corrupted and missing evidence; restored files pass and source remains
unchanged. Backup `C:/Users/Administrator/.codex/backups/gsov2-return-recovery-20261017-tiw0kkdn`.
NOT RUN - OUT OF SCOPE: online MySQL/operator restoration, deployment, role grants
and human COA/Accounting/HR acceptance. This rehearsal is synthetic stopped recovery.

Release2a7bb5f used actual external Version Manager. BranchCI38951280608 PASS before
canonical master fast-forward/push; remote master/tag match
2a7bb5f978ee1747e869472c243312dc6a683dd1. PrimaryCI38951482546 PASS50s.
Operator DB SHA-256 remains5c6c3c66e46d8a6f4a95799806ec96f4ef3fda923027adba29d63e9f337a2039.
No operator migration, role grant or deployment. Release notes use separate
`codex/custody-return-release-notes` after clean fetch0/0.

## Supplies service integrity — 2026-10-17

Fresh fetch and clean0/0 at e7483a6 before `codex/stock-ledger-validation`.
Actual GRAND source/helper rechecked against fetched32ab046; parallel Form1 edits
preserved. This is a service/permission repair before physical counts, with no schema
or storage-format changes. Expanded standalone/native and actual-GRAND tests cover
the shared receiving-to-stock dependency and explicit authority.

FAIL - PRE-EXISTING reproduced: a direct receipt of0.0004 did not raise validation
despite three-place ledger fields; regression1/1 failed0.348s before the fix,
`.tmp/stock-validation-before.log`. The new service validates decimal fields before
balance/FIFO/persistence and full-cleans the pending model before saving.
FAIL - CAUSED BY CURRENT WORK: initial targeted test expected ValidationError for a
missing department, while the existing resolver correctly raises PermissionDenied.
Corrected the test expectation and removed accidentally rediscovered imported tests;
no authority rule weakened. See `.tmp/stock-validation-after.log`.

PASS: `manage.py test inventory --noinput`,76 discovered/67 executed/nine native
skips14.660s, `.tmp/stock-validation-shell.log`. PASS: `scripts/run_mysql_tests.py`,
76/76 in49.834s, `.tmp/stock-validation-native.log`. Includes five new regression
cases for precision, nonfinite/range/cost failures with no partial writes, required
adjustment reasons, exact fractional FIFO, partial catalog edits and trusted issue
department labels. `makemigrations --check --dry-run` PASS: no schema changes.
PASS: actual-GRAND native63/63 in19.761s, `.tmp/grand-stock-validation-native.log`.
The two new authority tests verify explicit grants, owner boundaries, UAT write
denials/read grants, real department labels and no Finance queries. Existing23
GRAND W036 warnings remain outside GSO. Disposable schemas removed; owned MySQL33317
shut down normally. `pip check` PASS.

NOT RUN - OUT OF SCOPE: a new browser layout or recovery rehearsal. No screen,
file format, migration or backup boundary changed. The shared service path and actual
permission helper are tested; prior paired recovery evidence remains applicable.
No operator migration, permission grant, deployment, Finance posting or official
supplies form is claimed. Physical-count workflow remains next work.

Actual VM patch releasecbece6c integrated/pushed to canonical master after
branchCI38952776429 PASS31s; remote master/tag match
cbece6c9d2875d1b255be29c03ac29ce72ae23ba. PrimaryCI38952884082 PASS41s.
Operator DB SHA-256 unchanged at5c6c3c66e46d8a6f4a95799806ec96f4ef3fda923027adba29d63e9f337a2039.
Documentation follow-up uses separate `codex/stock-ledger-release-notes` after
clean fetch0/0, with no code, schema or storage changes.

## Reviewed supplies counts — 2026-10-17

Fresh fetch and clean 0/0 at8809372 preceded `codex/reviewed-stock-counts`.
GRAND source pinned to fetched32ab046; parallel Form1 changes preserved. Full native
suites are appropriate for new tables, protected user/movement links, shared stock
adjustments, permissions and private files. No operator data migrated.

PASS: `python manage.py test --verbosity 1`,91 discovered/79 executed/12 native
skips in28.059s, `.tmp/stock-count-release-sqlite.log`. PASS:
`python scripts/run_mysql_tests.py`,91/91 in74.794s,
`.tmp/stock-count-release-native.log`, native MySQL8.4.11 on owned loopback33317.
Includes populated0018-to0019 ledger/lot/allocation preservation, generated pending
uniqueness, quantity constraints, duplicate record/approval and receipt-vs-review
races, stale/offsetting movement detection, audit-failure atomic rollback, exact
fractional FIFO, unknown surplus cost, zero-variance review, reviewer-only cancel,
signed-token/CSRF/actor boundaries, private download and integrity failures.
Earlier intermediate native90/90 PASS70.770s and91/91 PASS75.130s are superseded.
PASS: `manage.py makemigrations --check --dry-run`, no changes; `python -m pip check`,
no broken requirements; `git diff --check`.

FAIL - CAUSED BY CURRENT WORK: initial actual-GRAND65-test run had one test cleanup
error (`file_to_stream` is None after the test client wraps/exhausts a successful
stream). Removed the redundant manual close; the test client's exhausted streaming
wrapper closes the source. No application authority or evidence guard was changed.
PASS: final `python scripts/run_grand_source_tests.py --grand-root
C:/Users/Administrator/.codex/worktrees/gsov2-grand-source-validation --mysql`,
65/65 in19.277s, `.tmp/grand-stock-count-release.log`. Native GRAND permissions,
UAT denials/scoped reads, protected actors, evidence boundaries and zero Finance
queries pass. Existing23 GRAND W036 warnings remain outside GSO. Both test schemas
removed; owned MySQL33317 shut down normally. PASS: `python -m pip_audit -r
requirements.txt`, no known vulnerabilities found.

PASS: actual GRAND browser, isolated fixture`.tmp/grand-source-tests-4_1avirq` on8023:
clerk records8 against10, uploads synthetic PDF; separate reviewer approves an
adjustment-out2, retained ledger becomes8 and configured minimum8 is flagged.
Recorder has no self-approval action. Desktop1440x1000/mobile390x844 inspected;
mobile client/scroll widths both375 (scrollbar excluded), no duplicate IDs on review.
Stock table retains its existing panel scroll without page overflow. Screenshots
`output/playwright/stock-count-*.png` visually inspected. Only synthetic GRAND
logo/favicon404s; no workflow errors. Both browser sessions and preview stopped.

PASS: `.tmp/rehearse_stock_count_recovery.py` backed up/restored stopped paired
SQLite and private files outside Git. All201 default/83 finance table contents,
integrity/foreign-key checks, approved count/native actors, original UUID basis,
linked adjustment and three events survive. `check_stock_count_evidence` detects
changed/missing files, restored evidence passes and original hashes stay unchanged.
Backup `C:/Users/Administrator/.codex/backups/gsov2-stock-count-recovery-20261017-k6d90rer`.
NOT RUN - OUT OF SCOPE: online MySQL/operator recovery, role grants, deployment,
official supplies form acceptance and historical-count reconciliation. These remain
separate gates; this release does not establish financial valuation or post journals.
