# GSO continuation

Checkpoint: 2026-10-17, Asia/Singapore. Overall goal remains active and incomplete.
Read [roadmap](docs/inventory-roadmap.md), [completion audit](docs/completion-audit.md),
[data design](docs/grand-integration-design.md), [COA sources](docs/coa-requirements.md)
and [validation](docs/validation-2026-10-16.md) before substantial work.

## Receiving follow-up checkpoint

Branch `codex/receipt-followup-acceptance`, baseline78c19e8. Previous goal turn was
progress: actual VM scope-audit release integrated/pushed with featureCI38988773596
and masterCI38988917720 PASS. Before this work GSO was fetched clean0/0; Finance
candidate a533482/master32ab046 remained unchanged except append-only GSO notes.

[Follow-up design](docs/receiving-followups.md): migration0028 adds a protected
original-line relation and retained physical basis to the existing receiving header.
Each child has one line and its own private documents, independent review and
materialization. Original-before-child locks enforce cumulative remaining capacity.
Signed request replay, correction screens and original/child navigation are included.
Original accepted quantities/version/history and ordinary Finance/property snapshots
stay unchanged. Child working property receipt date is its later inspection date.
Adapter0006 depends on inventory0028 with no schema/data operations. No Finance DML,
new authority registry, operator migration/grants or deployment.

Local validation:
- Full standalone176 discovered/151 run/25 native skips PASS,66.987s.
- Full native MySQL176/176 PASS,165.538s,including competing follow-up acceptance.
- Native focused10/10 PASS,2.888s,including populated0027-to-0028 preservation.
- Final receiving/HTTP/migration SQLite30/30 PASS,2.108s after header-edit guard.
- Actual GRAND SQLite141 discovered/120 run/21 skips PASS,31.864s.
- Actual GRAND native142/142 PASS,59.470s,exit0,terminal24710. Includes retaining
  an approved original Finance attribution while separately approving child support,
  with no Finance queries. Initial fixture stale-basis failure is documented and
  corrected; production stale-source protection remains unchanged.
- Populated actual GRAND copy retained218 prior tables' old columns/rows, with
  explicitly checked native Budget7 content types/42 permission metadata additions
  and no role grants. Finance file unchanged. Final adapter dependency/drift PASS.
- Browser desktop/mobile original remainder2 -> draft1 -> correction1.5 -> packet
  uploads -> submit -> distinct reviewer accepts -> original remainder0.5 PASS.
- Stopped paired restore219 default/83 Finance tables and16 files PASS; stock7.5,
  remainder0.5, original/child history retained; missing/tampered packets rejected.
  Backup: `C:/Users/Administrator/.codex/backups/gsov2-receiving-followup-recovery-20261017-f7bss3tn`.

The full shell runs preceded the added migration test and final header-only guard;
targeted checks above cover those changes. See validation for exact commands and
harness failures/corrections. VM README/inspect/preview select the next minor
release; only VERSION/CHANGELOG are generated. This is the pre-release checkpoint:
verify actual Git/tag/hosted receipts before deciding whether publication remains.
Do not repeat a completed release based only on this note.

## Next work and limits

Verify the actual VM/hosted publication receipts before integration. Then continue the finite
completion audit: trace accepted-quantity correction/reversal eligibility against
actual custody, stock/FIFO and Finance-support history before choosing the next
workflow. Do not rewrite accepted records or invent Accounting valuation, official
forms, numbering/signatures, historical imports or conditional fleet scope.

Official SPC/PAR/ICS/RPCPPE/RPCI/RSMI acceptance, complete imported history,
physical cost allocation/valuation and operational recovery/deployment remain
unfinished. Native GRAND Records already serves general-office filing through the
published dashboard entrya7cfb2d; do not duplicate its registry or invent inventory
association types. GRAND's own production NO-GO remains authoritative.

## Locations and preserved state

- Feature checkout: `C:/Users/Administrator/.codex/worktrees/gsov2-receiving-safety`.
  Canonical: `C:/Users/Administrator/Desktop/GH/GSOv2`, baseline master78c19e8.
- Finance active: `C:/Users/Administrator/.codex/worktrees/finance-form1-treatments/grand`;
  candidate a533482, remote master32ab046. Fetch/read its own CONTINUE before work.
  Only append to docs/GSO_INTEGRATION_REVIEW.md for coordination; no Finance publish.
- Actual GRAND test source: `C:/Users/Administrator/.codex/worktrees/gsov2-grand-v173-validation`;
  clean and0/0 with fetched candidate a533482. See [native testing](docs/native-testing.md).
- Python runtimes: `C:/xxx/_INSTALLS/_HERE/_xxx/gsov2-development` and
  `C:/xxx/_INSTALLS/_HERE/_xxx/grand-auth-venv`.
- Operator db.sqlite3 SHA256 remains
  `5c6c3c66e46d8a6f4a95799806ec96f4ef3fda923027adba29d63e9f337a2039`.
- Browser receiving-followup and preview52001 are stopped. Synthetic preview:
  `.tmp/receiving-followup-preview-z7_ru0hv`. Owned MySQL33317 was stopped after
  verifying no disposable test schemas remain. Final native log:
  `.tmp/followup-grand-native-final.log`; other results `.tmp/followup-*.log`.

[Historical checkpoints](docs/continuity-history.md) and the validation record
preserve earlier release/test/recovery evidence. AGENTS contains durable rules;
feature documents own behavior; this handoff owns immediate state.
