# GSO continuation

Checkpoint: 2026-10-17, Asia/Singapore. Overall goal remains active and incomplete.
Read [roadmap](docs/inventory-roadmap.md), [data design](docs/grand-integration-design.md),
[claim support](docs/claim-attribution.md), [COA sources](docs/coa-requirements.md),
[receiving](docs/receiving.md) and [validation](docs/validation-2026-10-16.md).

## Disposal evidence integrity — local validation complete

Previous turn: progress. Actual VM published577c549/v0.21.1; branchCI38983516424
and masterCI38983686513 PASS. Remote master/tag verified, canonical clean0/0,
operator database unchanged. Fresh sync this turn: clean0/0 at577c549; Finance
candidate a533482 unchanged except coordination note, master32ab046.
New branch `codex/disposal-evidence-integrity`.

Inventory0026 adds a blank-by-default attachment SHA-256; old records and events
are preserved without fabricated historical hashes. Shared save service validates
all upload groups before file writes, captures actual byte counts/hashes. Downloads
check and rewind the same open file; missing/changed files return409. Authorization
and completion check retained files, allowing legacy unknown hashes explicitly
but still rejecting missing/size-changed files. Strict source verification rejects
legacy unknowns; do not treat operational completion as verified SPC evidence.
Read-only `check_disposal_evidence` reports unknown, missing, changed, unsafe and
unreferenced files without modifying them. UI distinguishes retained baselines.

Shell142 (121 run/21 native skips) PASS44.109s. Focused6 PASS0.351s after recovery
caught and fixed a reopened-missing-file ValueError. Full native standalone142 finished with one new test-fixture error: manually
closing an already-consumed streaming response fired request_finished twice and
closed MySQL's test transaction. Redundant close removed in standalone and GRAND
tests. Final standalone native143/143 PASS124.530s; corrected full actual GRAND
135/135 PASS55.812s, exit0. Affected native12/12 PASS1.955s after both fixes.
All disposable schemas removed; owned MySQL normal shutdown confirmed.
Populated actual GRAND copy preserved216 prior non-migration tables and Finance
bytes. Desktop/mobile inspected, table scroll remains contained; browser/preview
stopped. Recovery217/83 tables/9 files PASS at
`C:/Users/Administrator/.codex/backups/gsov2-disposal-evidence-recovery-20261017-wm6udr7g`.
See validation record for limitations and remaining release gates. Overall goal active.

## Next work and boundaries

1. Local validation is complete. Run actual Version Manager release, hosted
   feature checks, fast-forward/push master, hosted master checks and remote verification.
   Keep initial failure evidence alongside the final passes.
2. After release and fresh sync, use a new feature branch for reviewed property
   movement annotations/openings. Reuse receipt, acknowledged handoff, witnessed
   return and completed disposal facts; never derive stock effects from custody alone.
   Follow [property design](docs/property-record-design.md). Official SPC, complete
   historical balances, accepted forms and physical cost allocation remain unfinished.
3. GRAND default/finance ownership and explicit permissions remain authoritative.
   No Finance code changes, operator migration/grants or deployment are authorized
   by this code-release workflow. General office filing should reuse GRAND records
   capabilities rather than introduce a duplicate authority.
4. Complete the remaining roadmap and operational/COA acceptance gates. Verify
   publication/amendments/applicability before treating an output as official.
   The overall goal is active, not complete.

## Working locations and continuity

- GSO feature checkout: `C:/Users/Administrator/.codex/worktrees/gsov2-receiving-safety`.
  Canonical: `C:/Users/Administrator/Desktop/GH/GSOv2`, master577c549 at last fetch.
- Finance active checkout: `C:/Users/Administrator/.codex/worktrees/finance-form1-treatments/grand`;
  candidate a533482, remote master32ab046. Re-read its CONTINUE and fetch before
  adapter changes. Append-only coordination is docs/GSO_INTEGRATION_REVIEW.md;
  preserve its unrelated work and do not publish the Finance branch.
- Actual GRAND test source: `C:/Users/Administrator/.codex/worktrees/gsov2-grand-v173-validation`.
  Python runtimes are under `C:/xxx/_INSTALLS/_HERE/_xxx/gsov2-development` and
  `C:/xxx/_INSTALLS/_HERE/_xxx/grand-auth-venv`. Read [native testing](docs/native-testing.md).
- Operator db.sqlite3 SHA256 remains
  `5c6c3c66e46d8a6f4a95799806ec96f4ef3fda923027adba29d63e9f337a2039`.
  Test/preview files are disposable copies; operator data has not been migrated.
- [Historical checkpoints](docs/continuity-history.md) preserve earlier release,
  test and recovery evidence. Old pending plans there are not current instructions.
  [AGENTS](AGENTS.md) holds durable constraints; the roadmap owns scope, feature
  design files own behavior, and validation owns actual commands/results.

No live local test or preview processes remain. Full GRAND27511 and standalone
66565 ended0; MySQL66795 shut down normally after schema cleanup. Logs:
`.tmp/disposal-evidence-grand-final.log`, `.tmp/disposal-evidence-native-final.log`.
Actual VM publication and hosted gates follow; no operator migration or deployment.
