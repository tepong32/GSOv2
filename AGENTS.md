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
  Follow the [property-record design](docs/property-record-design.md): retain supplied
  treatment/useful-life facts without inventing Accounting approval; individual
  custody survives expensing. Class/fund SPC output is distinct from Accounting's
  SPLC. Native dimension associations require separate Finance authority.
  Supplied property determinations lock receipt (if linked), then asset, then case;
  preserve verified predecessors and unknown useful-life/expiry facts. No expiry
  event releases custody. Include private property-determination packets in recovery.
  Native property dimension links need an explicit GSO request to the selected
  Finance owner; ledger grants alone do not expose GSO records. Follow the
  [link design](docs/property-finance-links.md), including direct versus
  journal-backed lock ordering and explicit Department-ID remapping on imports.
  The property working register is a current preparation view: include retired
  and undocumented assets, filter latest verified supplied labels, flag stale
  sources, and never infer historical balances or Finance identities from labels.
  Keep association writes in default, committing under Finance dimension locks;
  a GSO reader sees retained history without an implied live ledger check. Keep
  withdrawal possible when a supporting Finance source is missing or stale.
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
  Personal custody reads do not expand owner-office write authority. Live working
  lists, empty results and retired history never constitute employee clearance.
- HR-reference custody cases retain a supplied private request and qualified
  office findings; never infer separation from account status or issue universal
  clearance. Lock sorted assets before the employee, then the case; recheck the
  asset set and reject changes instead of locking new assets after the employee.
  Named handoffs must keep their target-user lock. Reuse GRAND Records for future
  general filing; do not duplicate its registry. See [case design](docs/hr-custody-review.md).
- Witnessed returns reuse custody movements with independent GSO confirmation and
  private evidence. Retain original employee identity; change physical custody only,
  not maintenance, acquisition value or Finance. Distinguish known GSO returns from
  unlinked legacy names. See [return design](docs/custody-returns.md).
- Supplies services must validate exact decimal quantities/costs before ledger/FIFO
  writes, resolve issue offices from the directory, and retain adjustment reasons.
  GRAND stock mutations require explicit grants and deny Finance UAT viewers.
  Physical counts never establish financial valuation; see [stock counts](docs/stock-counts.md).
- Stock forms bind signed request identities to actor/item/operation. Retry under
  the item lock, compare retained content, and reuse the movement UUID; never
  allocate FIFO or change balance twice. Fresh forms are new operations, not
  duplicate-document detection. Preserve legacy/internal no-ID callers' atomic
  behavior. See [request/issue design](docs/stock-request-design.md).
- Supplied requisitions retain source documents and fixed lines; independent GSO
  review is a document check, not an originating-office signature. Lock sorted
  items before the case; issue through stock services with version checks and
  protected fulfillment links. Closure never reverses physical issues. Include
  private requisition evidence in paired recovery; no stock reservation or Finance
  posting is implied. See [request design](docs/stock-request-design.md).
- Supply returns retain original issue/optional lot lineage and private evidence.
  Lock item before case; independently accept only observed usable quantities,
  capped at original issue/allocation less accepted returns. Never guess cost,
  reopen original allocations or erase issues. Unlinked legacy returns require
  reconciliation. No Finance reversal follows acceptance. See [return workflow](docs/supply-returns.md).
- Supply counts pin today's item/ledger basis and require private evidence plus an
  independent non-uploader's review. Lock item before count; stale bases require
  cancellation/recount. Apply differences through the existing movement service,
  retaining zero-variance decisions without fake movements or invented surplus costs.
  Include count evidence in coordinated recovery; historical counts and official
  supplies forms need separate reconciliation/acceptance, not backdated adjustments.
- Legacy asset, handoff, disposal and verification actions use explicit GRAND
  grants and deny UAT mutations. Read-only history checks may reuse existing action
  grants without enabling writes; never pass read_only=True from mutation services.
  Navigation must use the same scoped view helpers, not implicit superuser perms.
- Receiving in GRAND requires explicit action grants, including for superusers;
  Finance UAT viewers may only read scoped receipts/private evidence. Enforce the
  same policy in services, POST entry points and rendered controls; never cache
  receiving pages or private downloads. Standalone permissions remain supported.
- Claim support pins both claim and receipt facts. Preserve NULL historical receipt
  bases; never backfill approval evidence from today's values. Re-read lines after
  taking receipt locks, keep case → receipt → attribution order, and retain original
  approvals when stale links are withdrawn. See [cost correction design](docs/receipt-cost-corrections.md).

- Receipt cost amendments retain original accepted line/asset/stock values. Require
  private correcting evidence, exact nullable cost and independent GSO review.
  Serialize on receipt before amendment; never lock Finance cases from that path.
  Approval bumps receipt version and makes older claim support stale. New support
  uses the reviewed documentary ceiling, not an Accounting valuation. Include
  `inventory/receipt-amendments` in paired recovery and run its evidence checker.
- Ordinary edits of receipt-linked assets retain unit cost, quantity, supplier and
  purchase-order reference. Check the link after the asset lock without acquiring
  the receipt lock in reverse order. Legacy unlinked entries remain editable;
  never silently repair historical divergence. Documentary cost amendments do not
  revalue the materialized asset or authorize Accounting classification.

## Validation

Recognition source inspection reuses GRAND's explicit ledger-read grant and actual
Finance owner; claim visibility alone is insufficient. It is a live read across
stores, never approval or allocation authority. See [journal inspection](docs/journal-source-preview.md).
Reviewed recognition mappings are separate default-store records. Keep case →
receipt → claim → mapping → posting request → journal lock order; durable default
commit occurs inside the Finance read/lock transaction. Never wrap these mutation
services in an outer default transaction. No Finance writes. Withdraw approved
mappings before their claim support; retain approval history and recheck staleness.
See [mapping design](docs/receipt-journal-mappings.md).

Start with affected tests; expand for model, migration, auth, shared service and
deployment changes. Full shell suite is currently small and is appropriate for
release. Include populated migration replay and recovery preservation checks.
GRAND integration requires its default/finance router and native MySQL tests;
SQLite passes do not establish native concurrency or conditional-constraint safety.
Record PASS / caused failure / evidenced pre-existing failure / not run with reason.

See [COA source matrix](docs/coa-requirements.md),
[recovery boundary](docs/security-and-recovery.md) and
[validation](docs/validation-2026-10-16.md).
