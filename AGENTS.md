# GSOv2 repository guide

Standalone Django shell for the LGU General Services inventory module destined for
GRAND. Product code is `inventory/`; `user/` and `src/` are local adapters. `home/`
is retained legacy evidence, not an active application.
Optional GRAND-only relationships belong in `inventory_finance/`; do not install
that app in the standalone shell or duplicate GRAND authority models to make it run.
Its tests use the isolated actual-GRAND harness; see the handoff for development status.

## Start and continue

- Before work, fetch the configured remote and compare branch history **and** local
  file status. Record differences; never overwrite operator databases or other work.
- Read [CONTINUE.md](CONTINUE.md), [roadmap](docs/inventory-roadmap.md),
  [GRAND data design](docs/grand-integration-design.md), and affected tests/history.
- New features use `codex/` branches and worktrees under `~/.codex/worktrees`.
  Use the user's external Version Manager: inspect README, inspect/preview, stage
  intended files, release, integrate/push and verify remote. Honor actual review gates.
- Version Manager replaces exact version tokens in discovered docs. Preserve
  historical validation by identifying commits there; retain release tags in the
  changelog and CONTINUE. Inspect previews and generated diffs before integration.
- Document durable decisions here, current state in CONTINUE, feature scope in the
  roadmap, and actual commands/results in the validation record. Do not claim
  proposed tables, official forms, deployment, or human acceptance already exist.

## Durable boundaries

- Follow GRAND's current source and canonical handoff, not the stale operator
  checkout. Keep GSO operational tables in `default`; `accounting` and `budget`
  remain in `finance`. No cross-database foreign keys or automatic GSO postings.
- Reuse GRAND users, employee profiles, departments, parties, voucher cases and
  governed posting/recovery paths. Never duplicate their authorities here. Numeric
  IDs are installation-local; public UUIDs are portable identities, not permissions.
- Physical receipt, custody, financial recognition and payment are distinct facts.
  Match delivery/claim/journal lines explicitly; do not infer relations from tags,
  free-text references, vendor names, coincident IDs or matching amounts.
- Accounting owns account/treatment/valuation decisions. Inventory classes and
  optional FIFO allocation do not establish financial valuation policy. Check COA
  issuer, date, scope and applicability before implementing an official rule.
- Enforce department and action permissions in views and services. Preserve audit
  and correction history, private evidence, and independent review where required.
  Do not grant roles, change the operator database, or deploy as part of a code release.
- Back up data and evidence outside Git. GRAND's coordinated two-store recovery
  procedure is the integration target; a CSV or Git tag is not a data backup.
- Prefer the smallest vertical workflow using established services. No generic
  synchronization bus, duplicate ERP, speculative schema, or automatic accounting.
- Lifecycle uniqueness uses GRAND's generated nullable-marker pattern with ordinary
  unique constraints. GSO markers are virtual so populated SQLite upgrades work;
  test populated migrations as well as fresh MySQL schemas. Never auto-deduplicate
  historical cases to make a migration pass.
- Maintenance is operational history. Lock asset before case; an open case blocks
  register edits, handoff and disposal starts. Preserve custody and acquisition cost;
  documented repair amounts do not authorize payment or capitalization. Include
  private maintenance files in recovery and run their read-only evidence checker.
- Named custody reuses GRAND users/profiles through nullable protected links; never
  infer employees from legacy labels. Recheck minimal identity snapshots at handoff
  and require the selected employee to acknowledge a different initiator's request.
  Account deactivation is not employment termination or clearance. HR moves do not
  automatically move inventory; preserve recorded custody for documented review.

## Validation

Start with affected tests; expand for model, migration, auth, shared service and
deployment changes. Full shell suite is currently small and is appropriate for
release. Include populated migration replay and recovery preservation checks.
GRAND integration requires its default/finance router and native MySQL tests;
SQLite passes do not establish native concurrency or conditional-constraint safety.
Record PASS / caused failure / evidenced pre-existing failure / not run with reason.

See [COA source matrix](docs/coa-requirements.md),
[recovery boundary](docs/security-and-recovery.md) and
[validation](docs/validation-2026-10-16.md).
