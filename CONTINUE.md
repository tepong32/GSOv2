# GSO continuation

Checkpoint: 2026-10-17, Asia/Singapore. Overall goal remains active and incomplete.
Read [roadmap](docs/inventory-roadmap.md), [data design](docs/grand-integration-design.md),
[COA sources](docs/coa-requirements.md), [receiving](docs/receiving.md) and
[validation](docs/validation-2026-10-16.md).

## Current source integration checkpoint

Branch `codex/finance-receipt-attribution` in
`C:/Users/Administrator/.codex/worktrees/gsov2-receiving-safety`, based on published
`9ae80c0`. Fresh fetch shows 0/0 against remote master; intended changes are local.
Optional read-only source resolver uses GRAND's actual workbench/case visibility,
case lock, owner and party identity. No routes, allocation writes or migrations added.
GRAND replaces DV lines on re-preparation: retain reviewed case/version/line snapshots;
do not add a protected line FK that blocks that existing Finance workflow.

PASS: four pure tests; six actual GRAND SQLite integration tests including fresh
inventory migrations, core users/departments, receipt/audit creation in default,
no inventory table/queries in finance, and outsider denial. Seven native MySQL
integration tests PASS (0.953s) with source replacement on separate connections.
Logs: `.tmp/grand-inventory-validation-latest.log`, `.tmp/grand-native-validation-latest.log`.
Tests use clean detached GRAND `32ab046` at
`C:/Users/Administrator/.codex/worktrees/gsov2-grand-source-validation`.

Stronger native lock-proof PASS: seven tests in 0.925s, exit 0; log
`.tmp/grand-native-lock-proof.log`. MySQL performance_schema confirmed the reader
blocked while preparation held the case lock, then rejected the replaced source line.
Both random schemas were verified removed; owned MySQL server stopped normally.
Native success does not establish populated import, coordinated recovery, routes/UI
integration or reviewed financial attribution.

Release preparation: Version Manager README/inspect/patch preview completed; only
VERSION/CHANGELOG would change. No branch protection/rulesets found. Full standalone
suite PASS (49 discovered, 43 executed, six native skips, 4.124s); migration drift
and pip check PASS. Operator hash unchanged. Source resolver prerequisite is ready
for vm-release, branch CI, integration/push and primary verification. Do not describe
it as a completed financial attribution workflow.

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
2. On a new feature branch after fresh sync, implement concrete reviewed Finance
   attribution using existing parties/claims/posting identities, without duplicating
   authority. Recheck actual GRAND state first.
3. All 21 pages of the retained 2024-006 copy are visually reviewed. Establish
   publication/amendments and review relevant 2002-003/2023-004 text before official outputs.
4. Continue maintenance, stock counts, custody/clearance, general-office records,
   accepted outputs, GRAND import/router and coordinated recovery work per roadmap.
