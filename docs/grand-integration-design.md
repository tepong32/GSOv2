# GSO and GRAND data design

Design checkpoint: 2026-10-16, Asia/Singapore. Recommended approach selected under
the user's instruction to align the projects and avoid speculative architecture.
Only the portable identity prerequisite below is implemented in this checkpoint.
Receiving and Finance adapters are subsequent work, not available functionality.

## Source of truth inspected

GSO baseline: `64e458a` (physical-count reconciliation release). GRAND published baseline:
`32ab04669da05b868f6c8b8ff37e0f71b3805555` (v172), verified against fetched
`origin/master`. GRAND's active checkout is
`C:/Users/Administrator/.codex/worktrees/finance-form1-treatments/grand`, branch
`codex/finance-form1-print-evidence`; its ongoing Form 1 edits are unpublished.
The canonical GH/grand checkout is older; its CONTINUE points to this worktree.
Read the active handoff on every continuation; these paths are discovery evidence,
not a permanent dependency of the application.

Examined `src/database_routers.py`, `finance/models.py`, `vouchers/models.py`,
`accounting/models.py`, `budget/models.py`, and GRAND docs
`FINANCE_PAYABLE_RELATIONSHIPS.md`, `FINANCE_TRANSACTION_POSTING_RULES.md`,
`FINANCE_PAYABLE_CLAIMS_2026-09-10.md`, `DATABASE_BACKUP.md`. Older feature documents
describe their historical slices; current model definitions take precedence for
the mapping below. No GRAND application code or migrations were changed here.

## Existing records and ownership

| Information | Existing authority | GSO relationship and boundary |
| --- | --- | --- |
| People and offices | `users.User`, `profiles.EmployeeProfile.assigned_department`, `departments.Department` in default | Use existing actors and employee/office directory after migration. Keep shell IDs in a reviewed import map; do not reuse them as GRAND IDs. |
| Supplier/payee | `finance.FinanceParty` in default | It is versioned by department/code/version and release; it does **not** currently have a public UUID. Preserve that composite identity plus label/release evidence. Resolve an existing party through Finance; do not create a second supplier authority or auto-match by name. |
| Payable case | `vouchers.VoucherCase.public_id`, `state_version` in default | Link by case UUID and reviewed version. The requesting office, current processing office, Finance ledger owner and GSO custody owner can differ. |
| Receipt-related payable evidence | `PayableIntake` and `PayableDocumentEvidence` in default | Existing procurement, delivery and inspection/acceptance references are text; present/waived/reviewed status is governed by Finance. A GSO receipt can be supporting evidence; it must not silently mark Finance's checklist present/approved. |
| DV lines | `DisbursementVoucher` / `VoucherLineItem` in default | A line has a local PK, description, account code and amount; it is not a physical-item register and has no portable line UUID today. Do not invent one in a contract. A future adapter must retain a reviewed local-to-source mapping. |
| Obligation | `budget.ObligationRequest.public_id`, `state_version`, `snapshot_checksum` in finance | Preserve authoritative UUID and correction lineage. Do not substitute voucher compatibility `BudgetObligation`. `PayableObligationAllocation` already owns obligation-to-claim capacity. GSO must not consume that budget capacity again. |
| Ledger dimensions | `accounting.Fund`, `LedgerAccount`, `ResponsibilityCenter`, fiscal year in finance | Codes are scoped to Finance owner, not globally unique. ResponsibilityCenter has an explicit core `office_id` snapshot. Pin the reviewed identities/codes and retain labels; do not use physical custodian department as ledger owner. |
| Financial posting | `VoucherPostingRequest.public_id`, kind/version, payload/rule checksums, accounting-entry UUID in default | Reuse this governed path when an eligible voucher transaction needs recognition. Do not introduce GSO journal writes, alternate recipes or a second posting-request queue. |
| Posted amounts | `accounting.JournalEntry.public_id`; `JournalLine.sequence` within entry in finance | Link to entry UUID + line sequence + source/checksum/state evidence, not a database PK alone. Keep reversal/origin lineage. Liability claim-credit lines and asset/expense debit lines serve different purposes. |
| Physical stock/assets | `inventory.Asset`, `ConsumableItem`, `StockMovement` in default | GSO owns accepted quantities, item identity, physical condition and custody. Financial valuation and posting remain Accounting decisions. |

## Smallest useful receiving structure (next implementation)

Use a receipt header and receipt lines, alongside the existing register. Do not
embed a single DV foreign key in `Asset`: a delivery can be partially accepted,
cover several assets/supplies, or be paid in several claims.

**Receipt header:** public UUID, GSO owner office, supplier reference/label snapshot,
delivery reference/date, inspection/acceptance reference/date, recorded actor,
review status/version and retained evidence. Start with draft, submitted, accepted,
returned. Only a separately authorized reviewer can accept another person's entry.
Acceptance records actual inspection evidence; a button cannot stand in for a
physical signature. Corrections after acceptance retain the original and reason.

**Receipt line:** receipt + stable line number, description/specification/unit,
delivered/accepted/rejected quantities, rejection reason, acquisition source
(purchase/donation/transfer/found-at-station/legacy as supported), and documented
cost facts. Enforce accepted + rejected <= delivered; keep unresolved quantity
visible. Rejected/uninspected goods do not enter available stock.

**Register outcome:** accepted serialized equipment produces one asset per unit;
accepted ordinary supplies produce a receipt movement on an existing supply item.
Keep explicit receipt-line-to-asset/movement links and unique posting identity so
double submit cannot duplicate stock. Preserve existing legacy pooled assets until
reviewed splitting; do not split historical values automatically. Serial/chassis
matches require review; property-tag uniqueness needs legacy duplicate preflight.
Do not auto-generate official property numbers until the LGU numbering rule is known.

Only add these tables/fields when implementing the corresponding tested workflow.
No generic document, warehouse or procurement engine is needed for this slice.

## Financial relationships (adapter after physical receiving)

An explicit allocation row is needed when a receipt line supports a claim or a
recognized accounting amount. The shape is many-to-many: one receipt line may be
claimed in parts; one claim/JEV can cover multiple receipt lines. It must retain
receipt/line identity, case UUID, financial owner, source version/checksum, purpose,
allocated quantity/amount, actor and reviewed decision. Use a separate relationship
for recognized JEV/line attribution; never equate delivery value with payment net.

Keep gross invoice amount, recoverable/nonrecoverable tax, deductions, freight,
discounts and approved acquisition cost distinct. A source allocation cannot exceed
its approved amount or accepted quantity. Totals are checked in exact Decimal
arithmetic. GRAND uses 18-digit, two-decimal money; new financial amount fields
must match that capacity. Existing GSO unit-cost fields are narrower (13,2) and
quantity uses three decimals for supplies. Widen only with its own migration/test;
define rounding and residual allocation before a cost split is accepted. Unknown
legacy cost is NULL, not zero. Optional FIFO is physical lot allocation, not a
decision that Financial inventory valuation uses FIFO.

No automatic PPE/semi-expendable threshold or depreciation calculation is selected.
Accounting must pin treatment, fund/account, applicable policy release and evidence.
Keep physical custody for semi-expendable items after expense recognition; never
delete an asset because its carrying value reaches zero. Corrections, impairments,
disposal derecognition and recoveries use the existing reviewed Finance workflow.

Use same-database protected relations to GRAND records when the adapter is installed
and migration dependencies are known. Across default/finance, use UUID/composite
identity + retained snapshots, explicit scoped resolution and currentness checks;
no Django cross-store FK. On failure, leave the physical receipt accepted with a
visible unresolved Finance link; do not fake posting or roll back a physical fact
because a later Finance operation failed. Follow GRAND's existing request/recovery
pattern when a real cross-store write becomes necessary. No new sync framework.

## Migration and merge plan

1. **Implemented prerequisite:** additive `0012` assigns distinct public UUIDs to
   existing assets, supply items and stock movements, retaining all integer PKs and
   links. Nullable expansion, per-row backfill, then unique/not-null. Use a write
   pause when applying it; retries cannot assign one shared UUID to historical rows.
2. Preserve migration history `0001`–`0011`; never fake-apply or renumber it during
   merge. GRAND currently has no `inventory` app in the inspected tree. Recheck its
   migration graph at integration time. All inventory migrations route to default.
3. Integration of code and import of data are separate steps. Start GRAND schema
   from its own migration graph, then dry-run a reviewed import keyed by source
   installation + entity + public UUID. Existing users/departments/parties need an
   explicit mapping. Do not move the standalone database over GRAND's default DB.
4. Import assets, supplies, events, lots, allocations, transfers, verification and
   disposal evidence in dependency order. Some historical entities still have local
   PKs only: map source installation/table/PK and retain source hashes. Reconcile
   row counts, quantities, money and evidence checksums before accepting a batch.
   This importer is planned, not implemented. Do not import standalone passwords
   or grant privileges merely because a source user had them.
5. Native MySQL validation is required before GRAND merge: the current GSO app
   already uses conditional unique constraints that MySQL ignores. Resolve those
   existing open-transfer/disposal identities with GRAND's supported generated-key
   approach and duplicate preflights. SQLite tests cannot close this gate.
6. Use GRAND's coordinated default/finance backup and restore procedure, separately
   capturing private uploads and exports. Keep pre-import backup, source package,
   import mapping and reconciliation receipt. Rehearse restore before cutover.

## Acceptance examples for the adapter

- Ten ordered computers: six accepted now, two rejected and two pending; only six
  asset identities result. Later delivery has its own evidence; no duplicate stock.
- One receipt split across two claims; one claim consolidates two receipts and
  several obligations. Existing Budget allocations remain authoritative and are
  neither duplicated nor inferred from receiving quantities.
- One voucher contains equipment, freight and services; only reviewed allocations
  attach to assets. Payment withholding does not reduce acquisition cost silently.
- A posted recognition is reversed or its mapping superseded: GSO retains the old
  linkage and shows review needed; no automatic rewrite of an audit snapshot.
- Department A cannot discover B's vouchers via a GSO link. GSO visibility alone
  does not grant Finance source access; apply original-source and mutation checks,
  including GRAND's UAT-viewer denial rules.
- A retry after interruption resolves the same receipt/allocation identity and
  checks payload/version equality; a different payload cannot reuse that identity.

Production remains unaccepted. Human legal/accounting acceptance cannot be supplied
by choosing the recommended engineering approach.
