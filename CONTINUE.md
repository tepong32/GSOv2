# GSO continuation

Checkpoint: 2026-10-17, Asia/Singapore. Overall goal remains active and incomplete.
Read [roadmap](docs/inventory-roadmap.md), [data design](docs/grand-integration-design.md),
[COA sources](docs/coa-requirements.md), [receiving](docs/receiving.md) and
[validation](docs/validation-2026-10-16.md).

## Receiving release candidate

Branch `codex/receiving-inspection`, worktree
`C:/Users/Administrator/.codex/worktrees/gsov2-receiving-safety`, based on `405f360`.
Fresh fetch: HEAD/master 0/0; all listed local changes belong to this feature.
Version Manager inspect and minor preview completed: only VERSION/CHANGELOG updated
by the tool. Release/integration/push pending. Recheck live Git/CI before resuming.
No required PR/protection/ruleset found in the release check.

Implemented migrations 0013/0014: receipt/line/evidence/history, draft corrections,
retained voids, protected uploads/downloads, submission and independent review.
Acceptance atomically materializes accepted assets/supply quantities. Version checks
prevent replay; owner locking protects identifier allocation. No automatic financial
posting/classification, role grants, operator migration or production deployment.
See receiving guide for accepted-receipt reversal and remainder limitations.

0015 replaces transfer/disposal conditional uniqueness with GRAND's nullable generated
marker pattern. Virtual markers permit populated SQLite upgrades; STORED additions
failed in rehearsal. Duplicate preflight stops before DDL without rewriting history.
Native tests cover direct/concurrent inserts, close/reopen and populated upgrades.

Validation: MySQL 45/45 PASS (9.867s), no warnings/skips; SQLite 39 executed plus six
native-only skips PASS (4.943s). Migration drift and pip check PASS; runtime/optional
native dependency audit found no known vulnerabilities. Browser draft creation/list/
draft and accepted detail inspected at 1440x1000 and 390x844; no phone overflow or
nonempty duplicate IDs. Enforced-CSRF HTTP tests cover the complete clerk/reviewer flow.

Read-only evidence check reports missing/changed/unsafe/unreferenced files. Synthetic
SQLite DB+evidence restore passed including corruption recovery. Populated 0012-to-0014
copy preserved 42 rows across 37 tables; 0015 tests preserve lifecycle history.
Rehearsal artifacts: `.codex/backups/gsov2-receiving-rehearsal-20261017-001404`.
Owned MySQL fixture on port 33317 stopped; random test schemas verified removed.
No actual GRAND router/two-store or human acceptance is claimed.

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

1. Complete final release checks and actual VM release/integrate/push; verify remote
   tag/primary and CI, and preserve operator hash. Update this checkpoint.
2. On a new feature branch after fresh sync, implement concrete reviewed Finance
   attribution using existing parties/claims/posting identities, without duplicating
   authority. Recheck actual GRAND state first.
3. Complete COA source/annex review: 2024-006 main four pages verified, remaining
   annexes and relevant 2002-003/2023-004 text need review before official outputs.
4. Continue maintenance, stock counts, custody/clearance, general-office records,
   accepted outputs, GRAND import/router and coordinated recovery work per roadmap.
