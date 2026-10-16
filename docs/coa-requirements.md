# COA sources and GSO workflow coverage

Research checkpoint: 2026-10-16. This is a traceable implementation backlog, not a
certification of compliance or an exhaustive legal opinion. Issuance numbers alone
are ambiguous: distinguish COA circulars, COA memoranda, joint circulars and other
agencies' similarly numbered documents. Before official outputs, inspect the actual
annex, effectivity and amendments with the LGU Accountant and relevant process owner.

## Verified sources and limits

| Source | What was verified | Application and remaining verification |
| --- | --- | --- |
| [COA Circular 92-386, 20 October 1992](https://www.coa.gov.ph/wpfd_file/coa-circular-no-92-386-october-20-1992/) | COA's indexed listing identifies LGU supply/property management rules. Direct page retrieval failed in this session. | Baseline source for custody, receipt, inspection and accountability. Full text and later amendments still need section-level review; do not invent mandatory fields from its title. |
| [COA Circular 2002-003, 20 June 2002](https://www.coa.gov.ph/wpfd_file/coa-circular-no-2002-003-june-20-2002/) | COA's indexed listing identifies the NGAS manual for LGUs. | Start official LGU form/accounting mapping here; do not assume national-agency or barangay annex numbers apply unchanged to a municipality. Exact applicable editions/annexes remain to be compared. |
| [COA Circular 2023-004, 14 June 2023](https://www.coa.gov.ph/wpfd_file/coa-circular-no-2023-004-june-14-2023/) | COA's indexed issuance listing identifies updated documentary requirements amending 2012-001. | Align GSO evidence with GRAND's existing versioned Finance document rules. Do not build a competing hardcoded checklist. Obtain and review the relevant procurement/receipt annex before declaring completeness. COA's FAQ has a date typo (2003); use the issuance listing's 2023 date. |
| [COA Circular 2024-006, 14 March 2024 — UP Law ONAR record](https://naro.law.upd.edu.ph/issuances/3842) | Official registry metadata specifically identifies supplemental **LGU** implementation of Circular 2022-004 and the increase from PHP15,000 to PHP50,000. | Important LGU-specific companion to 2022-004. The browser limit was overcome by downloading the official copy on 2026-10-17. Main circular pages 1–4 were visually inspected; annexes still require review. See the source receipt below. |
| [DBM-COA Joint Circular 2024-1, 30 January 2024](https://www.dbm.gov.ph/index.php/joint-circulars?catid=342&id=2627%3Ajoint-circular-no-2024-01-dbm-coa&view=article) and [government-hosted circular](https://www.prc.gov.ph/sites/default/files/COA-DBM%20JOINT%20CIRCULAR%20NO.%202024-1%20DATED%20JANUARY%2030%2C%202024.pdf) | DBM identifies the revised disposal manual; the government-hosted text addresses LGUs among covered entities. | Existing disposal case retains request, authority and completion evidence. This does not yet validate every mode, committee, valuation, document or approval requirement in the manual. |
| [COA PPE inventory-report FAQ](https://www.coa.gov.ph/FAQS/when-should-the-inventory-report-of-property-plant-and-equipment-be-submitted/) | Annual count, December 31 reporting date and January 31 submission are stated in the FAQ. | Existing dated verification and working reconciliation support this work. Confirm the municipal form and signatories before generating an official RPCPPE; a FAQ alone is not an approved local template. |

No claim is made that this search found every superseding issuance as of the research
date. No commercial document summaries are used as the authority for executable rules.

## Product coverage derived from those sources and the user's scope

The workflow choices below are engineering recommendations; they are not quoted
statutory requirements. Build one complete workflow at a time and preserve GRAND's
governed Accounting/Budget decisions.

| Workflow | Current shell | Next work / authority boundary |
| --- | --- | --- |
| Asset and supply registers | Present, scoped permissions and audit history | Receiving/inspection/tagging; explicit physical item versus supply catalog distinction; reviewed classification. |
| Receipt evidence | Asset purchase references and stock receipt movements only | Receipt header/lines, accepted/rejected quantities, private evidence and independent acceptance; Finance readiness remains separate. |
| Custody and accountability | Department handoffs with acknowledgement | Employee identities from GRAND, PAR/ICS references and validated outputs, returns and exit-clearance evidence. Never infer signatures. |
| Stock cards / requisition and issue | Quantity ledger, optional FIFO, department issues | Reviewed requisition/issue/return lineage, dated stock counts and adjustments; confirm RSMI/RPCI and semi-expendable registers/forms before official generation. |
| Physical counts and Accounting reconciliation | Dated counts, unregistered findings, private Accounting snapshot, working CSV | Signed committee/source evidence and accepted official output; preserve missing/duplicate/unreconciled states. |
| Disposal / loss | Disposal evidence and decisions; no dedicated loss case | Compare revised disposal manual; distinguish loss investigation/relief from authorized disposal. No automatic retirement or Finance derecognition from a missing-item finding. |
| Maintenance and other GSO records | Vehicle identifiers only; maintenance status | Repair/service history first; then vehicle use/fuel/service records and accountable office requests where confirmed in scope. Avoid inventing procurement or HR authority. |
| Financial attribution | Free-text fund/account/PO/voucher/journal references | Explicit reviewed line allocations using [GRAND's actual models](grand-integration-design.md); no journal posting from this shell. |

The source matrix must be updated with exact sections and tested fields as each
official workflow is implemented. Pending legal/form validation does not block
ordinary receipt and custody development using explicitly non-official working records.

## Primary-text follow-up — 2026-10-17

Downloaded the [official ONAR copy](https://naro.law.upd.edu.ph/storage/01JT2JXVWNE95WHFN0FE53KQC9.pdf):
21 scanned pages, 17,796,221 bytes, SHA-256
`1b00c4e1359868972a84a732dda442619eed040877fb6460acc502250fe15c53`.
Local research copy: `C:/Users/Administrator/.codex/worktrees/gsov2-source-research/coa-2024-006.pdf`.
Text extraction yielded no text; rendered main pages 1–4 were inspected directly.

Verified section-level findings (paraphrased): section 2 covers all LGUs. Sections
3.1–3.4 distinguish qualifying PPE at PHP50,000 and above from below-threshold
semi-expendable property, require PAR/ICS accountability, and distinguish acquisition
from issuance accounting. Sections 3.5–3.8 prescribe retrospective treatment and
separate transitions for prior acquisitions still held versus previously issued.
Sections 4–5 refer to account and entry annexes. Section 8 ties effectivity to
publication; the publication date was not established here.

Design consequence: retain separate receipt, issuance, acquisition date and custody
facts; do not treat semi-expendable equipment as disposable consumables. GRAND
Accounting must apply reviewed treatment and correction lineage. Annex form fields,
account definitions and illustrative entries remain unverified; inspect pages 5–21
before implementing those details. No automatic historical reclassification is authorized.
