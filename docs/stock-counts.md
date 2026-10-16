# Supplies ledger and physical counts

Current development branch: `codex/stock-ledger-validation`. See [CONTINUE](../CONTINUE.md)
for publication and validation evidence. Counts and independently reviewed count
adjustments remain unimplemented; this prerequisite hardens their underlying ledger.

## Existing ledger controls

Supply catalog, movements and optional FIFO lots remain in GRAND `default`.
Quantities have three decimal places; optional unit costs have two. Service writes
now validate field precision/range before balance comparisons, ledger insertion or
FIFO allocation. They reject non-finite numbers and negative costs instead of relying
on database rounding. Adjustments require a nonblank reason. Issues require a valid
department and recipient, and retain the department label resolved from the actual
directory rather than a caller-supplied label. Catalog minimums are validated and
partial catalog edits preserve an omitted FIFO setting. Existing history is unchanged.

GRAND stock actions use its explicit user/group grant helper and assigned-department
gate. Finance UAT viewers cannot create/change catalogs or receive/issue/adjust stock.
Their scoped read/export grants remain usable. Implicit superuser privilege is not a
GRAND stock action grant; the standalone shell retains its existing access adapter.
Item-owner checks still run after locking the current item row. These changes do
not write Finance, infer accounting valuation, grant permissions or migrate data.

## Next count workflow

Implement dated physical counts against the scoped ledger with retained count
evidence, observed quantity, variance reason and independent review. Record the
actual item identity, unit and ledger basis used at count time. An intervening
movement must invalidate a pending adjustment basis; recheck under the existing
item lock before approving, and require recount/review instead of overwriting the
current balance. Approved differences create append-only stock adjustments exactly
once; a zero variance still retains the count and review without a fake movement.

Keep ordinary supplies quantity-only. Where FIFO was explicitly enabled, use the
existing allocation service; a count surplus must not invent a financial unit cost.
Do not conflate consumables with semi-expendable equipment requiring named custody.
Low-stock indicators should use the existing minimum quantity, without adding a
notification service before staff validate the workflow. Existing direct adjustment
history remains distinguishable from future reviewed count adjustments.

These are selected engineering controls, not asserted COA form requirements.
Applicable supplies-count forms and signatories still need primary-text and local
validation before official output. HR-reference clearance cases and Finance
cost/allocation/JEV relationships remain separate work in the [roadmap](inventory-roadmap.md).
