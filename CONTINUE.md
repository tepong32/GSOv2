# GSO continuation

Checkpoint: 2026-10-17, Asia/Singapore. Overall goal remains active and incomplete.
Read [roadmap](docs/inventory-roadmap.md), [data design](docs/grand-integration-design.md),
[claim support](docs/claim-attribution.md), [COA sources](docs/coa-requirements.md),
[receiving](docs/receiving.md) and [validation](docs/validation-2026-10-16.md).

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

Current documentation branch `codex/maintenance-release-notes` in
`C:/Users/Administrator/.codex/worktrees/gsov2-receiving-safety`; based on3905a74 after
fresh fetch0/0. Publish this release-result update through the documentation-only
Version Manager workflow, then fetch again and create a separate next-feature branch.

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
