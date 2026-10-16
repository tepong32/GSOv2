# GSO continuation

Checkpoint: 2026-10-16 (Asia/Singapore). The active goal is a practical, secure LGU
inventory/general-services system integrated with GRAND; it is **not complete**.

## Current work

Feature branch `codex/receiving-safety`, worktree
`C:/Users/Administrator/.codex/worktrees/gsov2-receiving-safety`, from fetched
`origin/master` `64e458a`. At initial inspection local and remote commits matched;
the canonical `db.sqlite3` was modified and has been preserved, not migrated.

This checkpoint adds portable asset/supply/movement UUIDs and export columns,
GRAND-matched dependencies, production-setting checks, corrected stock ownership
and service input boundaries. Runtime SQLite and the tracked user image are
removed from the new Git tree while local files/history are retained. Existing
count/reconciliation, disposal and handoff capabilities remain the prior baseline.

User direction: spend time on actual Finance data relationships, avoid invented
requirements/over-engineering, and record notes for the parallel Finance work.
[Data design](docs/grand-integration-design.md) maps inspected GRAND models and
sets the small receiving/inspection workflow before financial attribution.
[COA evidence](docs/coa-requirements.md) explicitly distinguishes source metadata,
verified text and outstanding annex/transition review. No official-form compliance,
automatic accounting, production readiness or complete inventory system is claimed.

A separate integration note was written at
`C:/Users/Administrator/.codex/worktrees/finance-form1-treatments/grand/docs/GSO_INTEGRATION_REVIEW.md`.
It is an **unpublished local note only**, preserving GRAND's current no-publication
boundary and concurrent code/CONTINUE edits. Do not stage or release the Finance work
from this task. Do not change its current Form 1 priority just to add inventory hooks.

## Validation and preservation

[Validation log](docs/validation-2026-10-16.md) records scope and exact commands.
Full shell suite: 16/16 pass. Migration drift, system checks, pip consistency and
dependency audit pass. Production system check has only the documented HSTS
subdomain/preload warnings. No native MySQL, real GRAND merge, official-form replay,
internet deployment or full recovery acceptance has occurred.

Operator preservation material is outside Git at
`C:/Users/Administrator/.codex/backups/gsov2-20261016-before-untracking`:
exact database copy, SQLite backup API snapshot, tracked user image, hash manifest.
The snapshot passed integrity_check. This is not a complete evidence backup.
The canonical operator database must retain its original hash throughout release.

Release/integration status must be verified against live Git and CI before resuming.
Use the Version Manager preview/release workflow; only completed GSO work belongs
in that release. Never commit the preserved runtime files or publish GRAND changes.

## Next work

1. Complete/verify this checkpoint's VM release, remote regression check, primary
   integration and preservation checks; update actual release status here.
2. Fetch/check sync again, then use a new feature branch for the receipt header/
   line workflow in the design: inspection evidence, partial/rejected quantities,
   independently accepted serialized assets/supply movements and retry protection.
3. Retrieve the full official COA 2024-006 text and relevant 2002-003/2023-004 annexes;
   retain exact applicable sections before official treatment/form implementation.
4. Follow with reviewed source allocations using existing GRAND Finance identities
   and policies. Recheck its active worktree, avoid code dependency on local paths,
   and implement only concrete adapters needed by the tested flow.
5. Continue maintenance, stock counts/requisitions, employee custody/clearance,
   general-office records and accepted outputs as [roadmapped](docs/inventory-roadmap.md).
   Native MySQL constraint/race checks and coordinated recovery remain integration gates.
