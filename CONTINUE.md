# GSO continuation

Checkpoint: 2026-10-17, Asia/Singapore. Overall goal remains active and incomplete.
Read [roadmap](docs/inventory-roadmap.md), [data design](docs/grand-integration-design.md),
[claim support](docs/claim-attribution.md), [COA sources](docs/coa-requirements.md),
[receiving](docs/receiving.md) and [validation](docs/validation-2026-10-16.md).

## Legacy asset authority alignment

Fresh GSO fetch clean0/0 atb232924, branch `codex/asset-authority`. Prior receiving
releasev0.11.2 is integrated/pushed: branchCI38959271074 PASS43s, primary
CI38959384805 PASS; master/tag verified. GRAND fetched0/0 at32ab046 with parallel
unpublished Form1 changes preserved; its handoff still reports full regression.

Actual copied-GRAND probe reproduced seven legacy mutations allowed to both
ungranted superusers and GSO UAT users. All fourteen now deny. Asset create/edit,
legacy transfer/acknowledgment, disposal, verification and audit reads share the
existing GRAND explicit grant policy; no new roles, schema or account authority.
Read-only history uses scoped existing grants; mutation helpers default to denial
for UAT. Navigation uses actual read helpers, including receiving/stock.

Standalone SQLite91/79 executed/12 skips PASS23.725s; native91/91 PASS80.414s.
Actual GRAND SQLite79/68 executed/11 skips PASS13.933s; final native80/80
PASS25.996s including added same-office UAT handoff denial. Existing23 non-GSO
W036 warnings remain. Browser scoped UAT disposal/count history verified without
write controls; mobile count no page overflow. No schema/storage changes.
Preview8026/browser stopped, both native test schemas removed, owned MySQL33317
shut down normally. Operator DB unchanged. VM patch preview inspected; publication
follows branch CI. Next: reviewed documentary cost amendments and Finance
quantity/cost/JEV relationships. HR-reference clearance and official outputs remain incomplete.

## Receiving authority correction

Started `codex/receiving-authority` from cbdd0d1 after clean fetch0/0. Previous
notes release master CI38957660920 PASS42s. GRAND source remains32ab046;
parallel Form1 changes are preserved. A copied disposable actual-GRAND fixture
reproduced implicit-superuser access and GSO-assigned UAT write access in receiving.
The corrected helper requires explicit GRAND action grants and blocks UAT writes;
scoped reads/private evidence remain available. POST gates and controls share it,
and receiving responses prohibit caching. No schema or role changes.

Final standalone SQLite91/79 executed/12 native skips PASS28.340s; native91/91
PASS72.475s. Actual GRAND native75/75 PASS25.703s; existing23 non-GSO W036
warnings remain. Initial failures were test assertions (expanded cache header,
prose matched instead of create link), corrected without weakening protection.
Browser UAT scoped reads/control absence visually verified; preview8025 stopped.
No schema/storage change, so prior recovery evidence remains applicable.
Actual VM releaseb232924/v0.11.2 published; branch and primary CI passed.

Next: audit legacy asset/transfer/disposal/verification authority before claiming
consistent GRAND policy across GSO. Documentary cost amendments remain planned;
receipt-side claim snapshots are already published. Overall goal is incomplete.

## Published receipt-side claim review basis

Previous turn published counts3ec09d6 and notes217a4d3/v0.10.1. Final notes primary
CI38955602714 PASS50s; feature primary CI38955372028 passed. Fresh fetch and clean
0/0 preceded `codex/receipt-support-basis`. GRAND remains32ab046, fetched0/0;
its active handoff reports full Finance tests running and all Form1 work unpublished.
No GRAND application/test sources or owned Finance33308 server are changed here.

Source review found claim support pins claim facts but uses live receipt facts and
omits them from signed previews. Implementing retained receipt snapshots before
accepted-cost amendments: optional adapter migration0002 leaves old rows NULL;
new confirmation/review reject changed bases, history shows retained values, and
stale/missing approved receipt bases block further support until explicit withdrawal.
Read receipt lines after acquiring their parent lock. See
[cost correction design](docs/receipt-cost-corrections.md); amendment UI itself is
not implemented and no accepted receipt/asset/FIFO is rewritten.

Standalone91 discovered/79 executed/12 native skips PASS30.089s; adapter migration
drift and dependency consistency PASS. Initial GRAND SQLite71/native72 runs each
failed one invalid test fixture (accepted quantity exceeded delivery); corrected
fixture, kept DB constraint. Final actual GRAND SQLite72/61 executed/11 native skips
PASS12.432s and native72/72 PASS30.325s. Logs`.tmp/receipt-basis-{sqlite,native}-final.log`.
Existing23 GRAND W036 warnings remain outside GSO. Both test schema pairs removed;
owned MySQL33317/session27946 shut down normally. Finance33308 untouched.

Actual GRAND browser preview/confirmation/independent approval passes; simulated
fixture-only cost change100→200 leaves original100 visible with a stale warning.
Mobile390/desktop1440 inspected, no page overflow or duplicate IDs; warning contrast
corrected and verified in restarted preview. All preview8024/browser sessions stopped.
Final paired stopped recovery preserves201 default/83 finance tables, both source
snapshots and original approval; deliberate approval-event loss detected/restored.
Backup`.codex/backups/gsov2-receipt-basis-recovery-20261017-8y_nfx_8`; no attachments
in this fixture. Source unchanged during recovery. Operator DB hash unchanged.
Actual external VM minor release543fef8/v0.11.0 integrated/pushed to master after
branch CI38957280486 PASS36s. Remote master/tag match
543fef8d72a30783923984c02fa4ea71157ba6bd. Primary CI38957393614 PASS42s.
Release notes use separate `codex/receipt-basis-release-notes`, fresh clean fetch0/0.
Overall goal stays active.
Next: reviewed documentary cost amendments, after checking receiving authorization
against actual GRAND explicit grants/UAT controls; then financial quantity/cost/JEV
relationships. HR-reference clearance and official outputs remain unfinished.
Source audit for next step: `require_receiving` still uses `actor.has_perm` rather
than GRAND's explicit helper/UAT check already used by maintenance and stock.
Reproduce ungranted-superuser and GSO-assigned UAT cases before the next amendment
feature; preserve standalone behavior and ordinary granted receiving access.

## Published reviewed physical counts

Started `codex/reviewed-stock-counts` after fresh fetch and clean 0/0 at
8809372/v0.9.3 (primary CI38953114417 PASS39s). GRAND fetched 0/0 at32ab046;
parallel Form1 work is preserved. Migration0019 adds one-item count records,
protected evidence/events, signed staff screens and configured low-stock indicators.
Counts pin today's ledger; stale bases require cancellation/recount. Independent
approval creates one exact existing-ledger adjustment, or no movement for zero
variance. Surplus cost remains unknown. No Finance writes or operator migration.
Historical counts need separate reconciliation; this is not an official RPCI.

Final standalone native91/91 PASS74.794s; SQLite91 discovered/79 executed/12 native
skips PASS28.059s. Migration drift and dependency consistency pass. Initial GRAND65
run exposed a test cleanup error after a successful download; corrected the test,
final actual-GRAND native65/65 PASS19.277s, log`.tmp/grand-stock-count-release.log`.
Both disposable schemas removed; owned MySQL33317/session51174 shut down normally.
Existing23 GRAND W036 warnings remain outside GSO; no GSO system-check warnings.

Actual GRAND browser record/upload/independent approval passes; stock10 to8 with
one adjustment-out2 and minimum8 reminder. Desktop/mobile visually checked, no
page overflow or duplicate IDs. Both browsers and preview8023 are stopped.
Stopped paired recovery preserves201 default/83 finance tables and one count file,
including original actors, basis, adjustment and all three events. Missing/changed
files detected and restored; source unchanged. Backup:
`C:/Users/Administrator/.codex/backups/gsov2-stock-count-recovery-20261017-k6d90rer`.
See [count design](docs/stock-counts.md) and [validation](docs/validation-2026-10-16.md).
Actual external VM minor release3ec09d6/v0.10.0 is integrated/pushed to master after
branch CI38955242812 PASS38s. Remote master/tag match
3ec09d6b6e204759c8e5e33b526fc0662e33e25b. Primary CI38955372028 PASS35s.
Documentation follow-up uses `codex/stock-count-release-notes` after fresh clean
fetch 0/0. Operator database hash is unchanged. Overall goal stays incomplete. Next: HR-reference review cases and
Finance cost correction/allocation/JEV relationships, with official supplies forms
and historical count reconciliation separately verified before implementation.

## Published supplies ledger validation

Previous turn published return notes v0.9.1/e7483a6; branchCI38951646913 and primary
CI38951773610 PASS. Fresh fetch and clean0/0 preceded `codex/stock-ledger-validation`.
GRAND remains32ab046, fetched0/0; unrelated Form1 changes preserved.
Inspection found a direct-service precision gap and implicit GRAND stock authority.
Regression test reproduced acceptance of0.0004 despite three-place storage. Services
now reject invalid precision/nonfinite/negative values, require adjustment reasons,
resolve issue destination labels, validate catalog minimums and preserve omitted FIFO.
GRAND stock permissions reuse explicit grants and deny UAT mutations.
Standalone76 discovered/67 executed/nine native skips PASS14.660s; native76/76
PASS49.834s. Actual GRAND native63/63 PASS19.761s. Both disposable schemas removed
and owned MySQL33317 session61913 shut down normally. See
[stock-count design](docs/stock-counts.md). No schema or operator
data changes. This published integrity prerequisite supports reviewed physical counts;
HR-reference clearance and financial relationships remain in scope.

Actual VM patch releasecbece6c, tagv0.9.2, is integrated/pushed to master after
branchCI38952776429 PASS31s. Remote master/tag matchcbece6c9d2875d1b255be29c03ac29ce72ae23ba.
PrimaryCI38952884082 PASS41s. Documentation follow-up uses separate
`codex/stock-ledger-release-notes`, created after clean fetch0/0. The reviewed physical-count workflow is tracked above; it was not part of this fix.

## Published witnessed returns

Custody-review notes published as v0.8.1 at efbc671; branch CI38947862792 and
primary CI38948007851 passed. Fresh fetch and clean 0/0 preceded branch
`codex/witnessed-custody-returns`; a further fetch found no upstream changes.
[Witnessed returns](docs/custody-returns.md) are published at2a7bb5f, tagv0.9.0.
Migration0018, services, private evidence/checker and signed staff screens are implemented.
Standalone SQLite71 discovered/62 executed/nine native skips PASS17.436s;
populated0017-to0018 preservation PASS1/1. Initial GRAND service SQLite55 discovered,
48 executed/seven native skips PASS5.792s. Standalone native71/71 PASS51.702s.
Initial actual-GRAND native60/60 PASS17.049s. Expanded61-test run had one fixture
error: maintenance closure correctly required recorded work. Corrected the test;
final native61/61 PASS16.937s, log`.tmp/grand-returns-native-corrected.log`.
Both disposable schemas removed; owned MySQL33317 shut down normally.
Existing23 GRAND warnings remain outside GSO.
Browser record/upload/independent confirmation/returned review passes desktop/mobile;
both sessions and preview8022 stopped. Paired stopped recovery preserves198 default,
83 finance tables and one return file; corruption/loss detected and restored with
source unchanged. Backup `.codex/backups/gsov2-return-recovery-20261017-tiw0kkdn`.
No operator database or Finance implementation changes. Clearance remains unimplemented.
Next: HR-reference review cases/unresolved-item decisions, then consumable counts;
Finance cost correction/allocation and recognized-JEV relationships remain separate gaps.

Actual external VM minor release2a7bb5f was pushed on the feature branch. Branch
CI38951280608 PASS before canonical master fast-forward/push. Remote master/tag
match2a7bb5f978ee1747e869472c243312dc6a683dd1. PrimaryCI38951482546 PASS50s.
Release notes use separate `codex/custody-return-release-notes` after clean fetch0/0.

## Published custody review milestone

Previous goal turn made verified progress: custody236c5e1 and release notes55fc7bf
are published. Final documentation branchCI38945566281 and primaryCI38945701870
passed; remote master/tag match55fc7bf and operator DB hash is unchanged.
Fresh fetch0/0 and clean tree, then created `codex/custody-review`. GRAND also fetched
0/0 with its unrelated Form1 changes preserved. Rechecked actual profile visibility,
permissions and absence of structured employee separation in profiles/users.

The [custody review workbench](docs/custody-review.md) is written: personal retained
assignments, owning-office review, separate legacy records and pending handoffs,
minimal current-HR comparisons, GET-only/no-store and bounded search/pagination.
No new schema or clearance decision. Own custody remains visible after HR moves
without granting owner-office write access. GRAND's explicit permission helper still
requires an assigned department; GSO can review retained history when the employee
cannot access it. At that checkpoint, clearance cases, returns and signoff were next.

Standalone4/4 boundary tests PASS0.454s, full shell70 discovered/61 executed/nine
native skips PASS11.670s. SQLite GRAND49 tests had one test expectation failure:
missing department correctly denies the recipient through GRAND's helper. Corrected
the test, not the authority check. Expanded native run37525 PASS50/50 in14.501s, no skips; log
`.tmp/grand-custody-review-native.log`. Both disposable schemas removed and owned
MySQL33317 session82727 shut down normally.
Browser office/legacy and moved-employee personal views inspected on isolated
`.tmp/custody-review-preview-6ypwa4un`, port8021 and browser sessions are now stopped. Mobile390 client/scroll widths match; no overflow
elements or duplicate IDs. Screenshots output/playwright/custody-review-*.png.
Published through the actual VM minor releasefb2eae2, tagv0.8.0. BranchCI38947590308
passed before canonical master fast-forward/push. Remote master/tag match
`fb2eae2c59df7669cb228eb344bc3f1521f1469a`; operator DB hash unchanged.
PrimaryCI38947689210 PASS. Release notes use separate
`codex/custody-review-release-notes`, created after clean fetch0/0.
The subsequent witnessed-return milestone is recorded above. HR-reference review
cases and clearance conclusions remain unimplemented. Overall goal remains incomplete.

## Published maintenance milestone

See [maintenance workflow](docs/maintenance.md). Migration0016, services, staff
screens, private evidence, asset/dashboard links and recovery checker are implemented.
Final standalone MySQL65/65 PASS15.703s; SQLite65 discovered/56 executed/nine native
skips PASS7.048s. Three races cover duplicate starts, handoff versus maintenance and
duplicate closure. Populated0015-to0016 preserves existing inventory history.
Drift/pip checks passed. Actual GRAND SQLite29 discovered/24 executed/five native
skips PASS2.777s; native GRAND29/29 PASS8.430s. Existing23 GRAND W036 warnings remain,
none in GSO apps. Both disposable schemas removed and owned MySQL stopped normally.

Browser login/open/work/upload/complete inspected desktop1440x1000/mobile390x844.
Completed mobile width390 matches viewport and no duplicate IDs. Only favicon404.
Browser and preview port8019 stopped. Synthetic source remains at
`.tmp/maintenance-preview-_g03g7vp`. Stopped DB+private-file recovery reconciled
37 tables and one file, detected/restored corrupted and missing evidence, and left
source unchanged; backup `C:/Users/Administrator/.codex/backups/gsov2-maintenance-recovery-20261017-nzu80ff7`.
Not online MySQL/operator recovery. Actual external Version Manager release3905a74,
tagv0.6.0, was pushed on `codex/asset-maintenance`. BranchCI38941638939 passed before
canonical master fast-forward/push; primaryCI38941747339 passed at the same commit.
Remote master/tag verified and operator DB hash unchanged. No operator migration,
permissions grant or deployment. Finance coordination note updated only.

Documentation releases f6ea69e and60d12af are published; final branchCI38942013769 and
primaryCI38942094327 passed. Remote master/tag verified, operator hash unchanged.

## Published employee custody milestone

Fresh fetch0/0 and clean tree at60d12af, then branch `codex/employee-custody` in
`C:/Users/Administrator/.codex/worktrees/gsov2-receiving-safety`. Read
[employee custody design](docs/employee-custody-design.md). Actual GRAND profiles,
permissions and HR source were inspected. No structured separation/clearance model
was found; disabled login is not employment termination. A minimal read-only
employee-source resolver and migration0017/custody services are written. New nullable
protected employee links/snapshots retain legacy text; transfer UUID migration uses
per-row backfill. Named recipient must personally acknowledge a different initiator's
handoff with unchanged identity/department. Generic edits and office-only handoffs
cannot erase named custody. Partial register edits no longer clear an omitted office.
Asset-first locks unify transfer start/ack/cancel; start checks current locked owner.

Initial source run PASS33 discovered/28 executed/five native skips3.727s (intermediate
source). Expanded actual-GRAND SQLite run60414 ended with one test expectation
error: after HR moved the employee, existing department scope correctly denied
acknowledgment with PermissionDenied before snapshot comparison. Corrected that
expectation and added same-office name-change rejection. Corrected run86403 completed39 discovered/34 executed/five native skips PASS2.927s.
Signed employee search/review/confirm screens and links are now written. Tokens bind
actor, asset, source custody and employee fingerprint; request UUID makes retries
idempotent even after closure. Incoming named handoffs are visible across GSO offices
without granting owner write authority. All three transfer actor FKs now PROTECT.

Latest standalone SQLite69 discovered/60 executed/nine native skips PASS9.882s;
native MySQL69/69 PASS28.912s; drift/dependency checks clear. Logs
`.tmp/custody-shell-release.log` and `.tmp/custody-native-shell.log`.
Actual GRAND HTTP run87126 found three query errors (`__pk` in nested `.only`);
fixed to concrete GRAND `id` and retained profile visibility filtering. Native
run60476 PASS44/44 in12.481s, including the two new races. Final native run35547
PASS44/44 in11.095s after tightened actor/asset binding assertions and UI wording;
log `.tmp/grand-custody-native-final.log`. Both disposable schemas removed; owned
MySQL33317 session88427 shut down normally. No preview/browser/server remains.

Browser requester/recipient handoff passed, desktop1440x1000/mobile390x844 inspected.
Sessions closed and preview8020 stopped. Synthetic paired source remains
`.tmp/grand-source-tests-nhoggi1i`. Recovery PASS:196 default/83 finance tables,
identity snapshot/accepted actor/audit retained, injected loss detected/restored;
source unchanged. Backup `.codex/backups/gsov2-custody-recovery-20261017-nj9xiahl`.
Not online MySQL/private-upload/operator recovery. External VM minor release236c5e1 (v0.7.0) is published. BranchCI38945305792 passed
before canonical master fast-forward/push. Remote master/tag match
`236c5e1e265bc1a63b97a9d3271133e94b598f10`. PrimaryCI38945433056 PASS.
No operator migration, grants or deployment. Release notes follow on separate
`codex/custody-release-notes`, created from a clean fetch0/0 checkpoint.
Clearance/HR separation remain unimplemented. Overall goal is incomplete.

## Published reviewed claim support

Published claim support at`28da3f1`. Optional `inventory_finance` includes
same-store protected receipt/case/owner/actor relationships, source snapshots,
proposal/independent approval/rejection/withdrawal, immutable event saves and
scoped GRAND-base screens. Signed previews bind actor/case/content and expire.

Approval locks the case and receipt, caps claim-line totals and receipt-wide totals
across claims, rejects stale/replaced source evidence, and blocks UAT/self-review.
Unknown/zero receipt cost cannot create claim support. This does not post accounting,
reserve Budget capacity, allocate physical quantities or establish acquisition cost.
Accepted-receipt cost correction and recognized-JEV attribution remain incomplete.
No automatic grants, operator migrations, deployment or parallel Finance edits.

PASS: 26 MySQL8.4.11 actual-GRAND service/HTTP/race tests (7.930s, no skips), including
cross-case receipt capacity and CSRF/signed-preview controls. Log
`.tmp/grand-attribution-capacity-http-native.log`. Existing 23 GRAND W036 conditional
uniqueness warnings remain; none concern inventory or inventory_finance. Both random
schemas removed and owned MySQL server stopped normally.
PASS: standalone49 discovered/43 executed/six native skips (3.370s), actual GRAND
model checks, both app migration drift, pip check and whitespace check.

Browser: real GRAND clerk login, preview/submit, separate reviewer approval and
withdrawal at1440x1000/390x844. Original approval and full history retained; mobile
checks found no horizontal overflow/duplicate IDs. Screenshots output/playwright/claim-*.png.
Isolated media lacks default GRAND logo/avatar (404s). Browser sessions and port8018
stopped. Synthetic paired SQLite preview files remain under
`.tmp/grand-source-tests-i2l7amgw`; no operator data.

Recovery PASS: stopped paired source backed up/restored, all193 default/83 finance
tables reconciled, integrity/FKs valid. Injected loss of an approval event was detected
and recovered; source hashes unchanged. Evidence:
`C:/Users/Administrator/.codex/backups/gsov2-attribution-rehearsal-20261017-011803`.
This database-only rehearsal does not cover private uploads or online MySQL recovery.

Published via actual Version Manager minor release28da3f1, v0.5.0. BranchCI38938855245
passed before fast-forward/push to master. Remote master/tag match and operator hash
is unchanged. MasterCI38939041377 passed at the verified release commit. No branch rulesets/protection found.
Parallel Finance integration note updated without code/migration/shared-handoff edits.

Financial cost-correction, JEV links, stock counts, clearance and wider
general-office records remain open in the roadmap.

## Published receiving milestone

Receiving `7d3547f` and documentation `9ae80c0` are published; primary checks
38932087704 and 38932337771 passed. Migrations0013/0014 provide draft corrections,
protected evidence, independent acceptance and atomic asset/stock materialization.
0015 provides portable lifecycle uniqueness and duplicate preflight. Accepted receipt
reversal and incremental remainder processing remain unimplemented; see receiving guide.

Published native suite: 45/45 PASS, including competing acceptance/asset identifiers,
lifecycle uniqueness and populated upgrades. Synthetic backup/restore rehearsals
preserved data and evidence, including corruption detection. Evidence artifacts:
`.codex/backups/gsov2-receiving-rehearsal-20261017-001404`.
No production deployment, operator migration or human acceptance is claimed.

## Preservation and parallel work

Canonical repo: `C:/Users/Administrator/Desktop/GH/GSOv2`, primary `master`.
Operator DB/photo are ignored and must not be migrated by code release. Backup:
`.codex/backups/gsov2-20261016-before-untracking` (raw DB, backup snapshot, image,
manifest and stash reference). Operator DB SHA-256:
`5c6c3c66e46d8a6f4a95799806ec96f4ef3fda923027adba29d63e9f337a2039`.
Preserve ignored files and historical evidence. This is not complete operator recovery.
Previous published foundation: `e642d9e`, documentation `405f360`; primary CI
38928123403 and 38928528769 passed.

GRAND active worktree: `.codex/worktrees/finance-form1-treatments/grand`, branch
`codex/finance-form1-print-evidence`. Form1 work remains unpublished. Separate
`docs/GSO_INTEGRATION_REVIEW.md` holds GSO notes and populated generated-column
upgrade advice. No Finance code/migrations/shared handoff changed. Do not publish its
parallel work; fetch and inspect its current source before adapter work.

## Next work

1. Check live primary/documentation CI and fetch sync before the next feature;
   preserve operator data and use a separate feature branch.
2. Select the next roadmap workflow on a separate branch. Claim support and basic
   maintenance are published; accepted-receipt cost correction
   and recognized-JEV linkage still need explicit design against current GRAND.
3. All 21 pages of the retained 2024-006 copy are visually reviewed. Establish
   publication/amendments and review relevant 2002-003/2023-004 text before official outputs.
4. Continue maintenance corrections, stock counts, custody/clearance, general-office records,
   accepted outputs, GRAND import/router and coordinated recovery work per roadmap.
