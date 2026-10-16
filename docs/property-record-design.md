# Property records and Finance relationships

Design decision, 2026-10-17. The supplied-document workflow below is implemented;
native Finance links are implemented separately in the optional adapter; SPC
output and Accounting treatment approval remain separate requirements.
GSO source:25004cc; GRAND source:32ab046. Finance's unpublished work is preserved.

## Evidence and consequence

Re-inspected pages2,3,7,8 of the retained [COA2024-006 official ONAR copy](https://naro.law.upd.edu.ph/storage/01JT2JXVWNE95WHFN0FE53KQC9.pdf).
The [source receipt and wider review](coa-requirements.md) retain its hash and limits.
Sections3.1–3.8 distinguish recognition, acquisition, issuance and historical
transitions. AnnexA.2 specifies a property-unit SPC by class and fund, including
item numbers, useful life, expiry, source references, quantity/cost, custody and
balance. Accounting's SPLC is separate. Publication date, later amendments and
local adoption remain unverified; do not equate filing date with effectivity.

The following choices are engineering decisions. They do not add a tax rule,
recognition recipe, automatic accountability cancellation or local signatory policy.

## Use existing identities; add retained documentary facts

| Fact | Current source | Selected treatment |
| --- | --- | --- |
| Individual physical item | Asset.public_id; new receiving makes one asset per accepted serialized unit | Keep that identity for PPE and semi-expendable property, including after expense recognition. Do not turn the item into consumable stock. |
| Acquired/received value | ReceivingLine and its registered_asset; documentary amendments are separate | Retain original and effective documentary cost separately. Neither is an approved financial carrying value. Unknown stays unknown. |
| Property type | Asset.inventory_class is only a reporting group | Retain a supplied PPE/semi-expendable determination with its source, date and stated authority. Never infer it from cost, item type or account-code text. |
| Useful life and expiry | Not represented | Retain the documented duration with its unit, explicit start basis and supplied expiry date when known. Do not invent defaults, compute release of accountability, or discard custody at expiry. |
| Fund and account | Asset has free-text fund/account labels; GRAND has native UUIDs | Source labels remain labels. A separately reviewed optional adapter link pins Finance owner plus Fund/LedgerAccount UUIDs and content snapshots; no cross-store FK or name matching. |
| Issue/transfer/return | AssetTransfer UUID and retained actors/dates/references | Reuse acknowledged movements. Pending/cancelled requests are not physical issues. Preserve source-document and actual custody-event dates separately. |
| Disposal | AssetDisposalCase and its events/evidence | Reuse completed disposal facts. A missing count or expired useful life is not disposal. |
| Legacy grouped quantity | Asset permits historical pooled rows | Flag for explicit reconciliation; do not silently split identity, cost or custody among invented units. |

The implemented vertical workflow records and independently checks a supplied property
determination for an existing individually tracked asset. Bundle treatment,
documented useful-life/expiry facts, source fund/class labels and reason in one
revision, with one private source packet, public UUID, explicit source date,
recorder, checker, state version and immutable decision history. Correction creates
a successor retaining its predecessor; cancellation/rejection preserves evidence.
This checks a supplied determination, not a new GSO power to approve Accounting
treatment. UI wording must distinguish documentary verification from Accounting
approval. Unknown or missing source facts stay explicit and block official output.

Keep the record in inventory/default with protected Asset/native-user relations.
Migration0024 adds PropertyDetermination and PropertyDeterminationEvent, together
with entry/review/history/private-download screens and scoped asset navigation.
Lock linked receipt first, then asset, then property case; same-version retries must not
produce duplicate effective revisions. Source files and the current asset/receipt
basis must still agree at verification. A changed receipt cost basis requires review,
not silent reclassification. Receipt locking serializes against documentary cost
amendments without reversing receipt acceptance's lock order. Do not acquire
Finance locks from the core workflow.

Only one pending entry per asset is permitted by an ordinary unique constraint on
a virtual generated marker. Verify/reject requires a different recorder/reviewer;
cancel requires the record grant. Dedicated view/record/review permissions plus
owning-GSO asset visibility are checked in services and HTTP. GRAND UAT mutations
and ungranted superusers are denied; no automatic role grants. Source entry uses
signed actor/asset/basis/request identity with a30-minute form lifetime; exact
replays retain the same record. Decisions require the current pending version.

Useful life is an exact positive duration with explicit unit and start basis, or
NULL. Supplied expiry may remain unknown even when duration is known; no date is
computed. Source fund/class labels are documentary text. Receipt-origin assets and
legacy individual assets are supported; pooled quantities are rejected pending
reconciliation. Verified predecessors remain intact when successors are checked.
Changes to retained asset/receipt basis display a review warning. History checks
detect drift but do not authenticate documents or defeat privileged administrators.

Private packets use `inventory/property-determinations/<UUID>/...`, the existing
PDF/image validation and15MB limit. No public media route is created; downloads are
scoped attachments with no-store/nosniff. Include this namespace in paired recovery
and run `check_property_evidence`. Failed database transactions may leave unreferenced
files for that read-only checker to report; they are not silently deleted.

## GRAND authority and dimension link

The [implementation design](property-finance-links.md) now supplies the explicit
GSO-to-Finance request boundary missing from this initial design. The optional
adapter implements it; a ledger grant alone cannot expose a GSO-owned packet.

Inspected accounting/models.py: Fund, LedgerAccount and ResponsibilityCenter have
public UUIDs, owner department, codes and effective/active facts. Used dimensions
have governed edit rules. A code is unique within its ledger owner, not globally.
Inspected inventory_finance/journal_sources.py and journal_mappings.py: existing
recognition mappings already pin fund/account identities from a posted debit.

Reuse an existing current reviewed recognition mapping when it establishes the
relevant dimension facts, retaining that mapping UUID and its source snapshot.
It still does not establish useful life, property treatment or full acquisition
valuation. Do not require a payable/JEV link for donated or legacy property whose
support legitimately follows another documented path; unresolved links stay absent.

For an explicit native dimension association, require the real Finance owner and
existing ledger visibility plus a dedicated mutation grant. A GSO record grant or
ledger-read grant alone cannot approve that association. Recheck actual permission
helpers at implementation. Deny UAT mutations and implicit superuser bypasses.
Never grant permissions on migration. Pin owner/UUID/code/label/effective facts,
and preserve stale/archived source history. Use the established durable default
commit inside the necessary Finance read/lock transaction; no Finance writes.
Native race tests must establish the final lock order before this path ships.

## Output and remaining prerequisites

The property working register (`property-records/`) now provides a paginated,
owner-scoped preparation view across assets, including retired and undocumented
items. Filters use only the latest verified supplied treatment/class/fund labels;
a pending successor never replaces those labels. Missing documents, grouped
quantities, missing dates/cost/life/class/fund/tag and changed source facts remain
visible for review. Each displayed determination's history and private file are
checked on the read. Invalid filters return errors and no records. No totals,
historical balances, native Finance identity inference or official-form readiness
are asserted. This view performs no mutations or Finance queries and needs the
existing property-document view authority. It is a preparation aid, not the SPC.

The eventual SPC is a class/fund working projection of retained item and movement
facts, not a second quantity ledger. Its property/item numbering must be explicitly
recorded and checked against the applicable source instructions before official
output. A one-asset audit list cannot be presented as the completed class/fund SPC.
Grouping must not net away individual custody. Legacy opening balances, transfers
between funds/classes, unknown source dates and discrepancies need explicit reviewed
entries; they cannot be reconstructed from today's labels or created_at timestamps.

Rechecked retained AnnexA.2 instruction page8 during the working-register slice.
It distinguishes the assigned property number from receipt/issue item numbers.
The latter examples encode acquisition year, annually renewed acquisition order,
and item series. Existing Asset.property_tag must not silently double as all three
identifiers. Next card work must retain explicitly supplied source numbering and
document dates for acquisitions and acknowledged movements before reconstructing
balances. The instruction's balance is received quantity less issues/transfers/
disposals, which is distinct from continuing individual custody after issue.
Therefore neither active asset count nor total named custody can populate that
balance. Opening stock and external transfers require documented reconciliation.

Physical receipt cost-component allocation remains a separate unfinished workflow:
documented allocation targets need exact quantities, source amounts, component
basis and rounding/residual treatment. Existing claim/journal support amounts are
not that allocation. Preserve gross consideration, taxes, freight, deductions and
acquisition value separately; Accounting owns inclusion/treatment decisions.

Acceptance for the supplied-document workflow: known/unknown useful life; no guessed
expiry; supplied semi-expendable determination below/above an apparent threshold
without automatic override; stale source rejection; independent review; protected
history and successor correction; forged/stale HTTP posts; owner/UAT denial;
unchanged custody/Finance; populated migration; native competing reviews; paired
restore retaining source bytes and decisions. Official SPC/PAR/ICS parity and local
acceptance remain separate, visible gates. This design does not satisfy them.
