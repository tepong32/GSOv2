# GSO continuation

Checkpoint: 2026-10-17, Asia/Singapore. Overall goal remains active and incomplete.
Read [roadmap](docs/inventory-roadmap.md), [data design](docs/grand-integration-design.md),
[claim support](docs/claim-attribution.md), [COA sources](docs/coa-requirements.md),
[receiving](docs/receiving.md) and [validation](docs/validation-2026-10-16.md).

## Published property movement milestone

Branch `codex/property-movement-records`, based on published dbd47c0. Local/remote
baseline was checked before work; Finance candidate a533482/master32ab046 remains
unchanged except append-only GSO coordination. Actual VM v0.23.0 was integrated
and pushed as ce845fc65744f6072dc378f0ab560c91666b8532; feature CI38987081260 and
master CI38987256429 PASS. Remote master/tag matched; canonical clean0/0.
Previous goal turn: progress (implemented and published the movement workflow).
This turn fresh sync reverified ce845fc0/0 and the completed master CI.

[Movement design](docs/property-movements.md): reviewed source annotations and
explicit end-of-day openings, protected source/property/predecessor links, private
packets, independent decisions and retained corrections.0027 gives disposal cases
portable UUIDs without rewriting their old facts/events. Screens select confirmed
sources, bind expiring signed requests, preserve zero/unknown values and show a
working stock reconstruction. They never move custody, stock ledgers or Finance.
Missing/ambiguous/stale history produces no calculated balance. This is not official
SPC formatting, financial valuation or certification of complete external history.

PASS local release gates:
- Full standalone166 discovered/142 run/24 native skips,66.284s,exit0.
- Full native MySQL166/166,169.779s,exit0.
- Actual GRAND native137/137,62.934s,exit0; SQLite136 with21 native skips,31.050s.
  Includes real receipt→named issue→witnessed return→disposal and explicit native
  grants/UAT/owner/zero-Finance-query tests. SQLite discovered before the last native
  authority test was added; native includes it.
- Native focused22/22 including3 concurrency tests; final styled HTTP6/6,0.725s.
- Populated actual GRAND copy:216 existing tables' rows retained, Finance file
  unchanged, expected2 content types/3 permissions added, disposal UUIDs unique.
- Browser desktop/mobile opening0→independent verification→correction1→independent
  verification; pending correction suppresses balance, both verified entries remain.
- Stopped paired restore:219 default/83 Finance tables,12 private files; exact
  manifests/history/balance preserved, missing/tampered movement files rejected.
  Backup: `C:/Users/Administrator/.codex/backups/gsov2-property-movement-recovery-20261017-2q0dm5pv`.

Test logs and known harness corrections are recorded in validation. No operator
migration, grant or deployment. Full goal remains active and incomplete.

## Next work and boundaries

1. The `codex/gso-office-records-entry` milestone passed local validation. GSO
   navigation now reuses native Records authorization and actual assigned-office
   scope. No duplicate registry, tables or invented operational associations.
   See [office records](docs/office-records.md). Standalone1, actual GRAND SQLite17
   (3.934s) and MySQL17 (4.743s) PASS, including existing native Records regressions.
   Browser desktop/mobile GSO→Records→native draft creation PASS. Actual VM/hosted
   publication completed at a7cfb2df928d22575d21a45d12c19c20e908b6ca. Feature
   CI38988203821 and master CI38988402908 PASS; fetched master/tag and clean0/0
   were verified. The scope-audit turn rechecked the master CI and source baseline.
2. Follow the [completion audit](docs/completion-audit.md): next inspect and design
   governed follow-up acceptance of already delivered unresolved quantities, tracing
   existing Finance support and source links before selecting schema. Official SPC,
   complete historical balances, accepted forms and physical cost allocation remain
   unfinished. Do not create official rules or optional fleet scope by inference.
3. GRAND default/finance ownership and explicit permissions remain authoritative.
   No Finance code changes, operator migration/grants or deployment are authorized
   by this code-release workflow. General office filing should reuse GRAND records
   capabilities rather than introduce a duplicate authority.
4. Complete the remaining roadmap and operational/COA acceptance gates. Verify
   publication/amendments/applicability before treating an output as official.
   The overall goal is active, not complete.

## Working locations and continuity

- GSO feature checkout: `C:/Users/Administrator/.codex/worktrees/gsov2-receiving-safety`.
  Canonical: `C:/Users/Administrator/Desktop/GH/GSOv2`, mastera7cfb2d at audit fetch.
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

Current Records browser/preview and test runs are finished. Owned MySQL33317 was
stopped after verifying cleanup. Final logs: `.tmp/office-records-grand-final.log`
and `.tmp/office-records-grand-native-final.log`; preview copy
`.tmp/office-records-preview-bzhdnbrg`. Original runs failed only the native test
relative-template-path assumption; corrected runner uses the GRAND source cwd.
Previous movement milestone: owned MySQL33317 was stopped
normally after verifying no disposable test schemas remain. Preview copy:
`.tmp/property-movement-preview-ea05rtn5`. Logs: `.tmp/property-movement-ui-shell.log`,
`.tmp/property-movement-native-full.log`, `.tmp/property-movement-grand-native.log`,
`.tmp/property-movement-grand-sqlite.log`. Recovery helper is
`.tmp/rehearse_property_movement_recovery.py`. Synthetic screenshots are under
`output/playwright/property-movement-*`.
