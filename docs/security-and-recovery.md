# Security and recovery boundary

This shell is for controlled development. A release is not permission to expose it
to the internet or an assertion that LGU operational acceptance has passed.

## Implemented checkpoint

- Django 5.2.18, Pillow 12.3.0 and python-dotenv 1.2.2 match the inspected GRAND
  application requirements. Django's [5.2.18 security release](https://docs.djangoproject.com/en/5.2/releases/5.2.18/)
  is the verified framework target. Continue dependency audits; a clean audit is
  only a known-vulnerability check, not a penetration test.
- `DEBUG=0` refuses a missing/weak secret, missing/wildcard host list, or missing/
  publicly located private-evidence root. HTTPS redirect, secure session/CSRF
  cookies, HSTS and frame denial are enabled. Development still defaults to DEBUG=1;
  explicitly select production settings. Subdomain HSTS/preload remain off until
  the deployment's complete domain is validated.
- `GSO_DATABASE_PATH` allows disposable test/rehearsal databases without moving the
  operator database. No operator migration is performed by a code release.
- Stock ownership is enforced in list/detail/export and write services. The
  original GSO-wide stock query was broader than its owning department. Service
  inputs now reject replacing identity, ownership and actor fields.
- Runtime SQLite, private evidence and new user uploads are excluded from Git.
  Untracking current data does not remove historical Git objects or revoke any
  credentials previously published. No history rewrite or credential rotation
  is claimed. Before production use, inspect historical exposure privately and
  replace any real credentials/accounts that were distributed in a prototype DB.

## Recovery approach aligned with GRAND

Use GRAND's `docs/DATABASE_BACKUP.md` at integration. It captures default and
finance as separate native dumps under one verified same-server MySQL read lock;
two independently timed snapshots are not an accepted equivalent. GSO tables join
default, not a third authority database. Uploaded evidence and exports need their
own coordinated protected backup; GRAND's database backup alone does not contain
those files. Do not build a separate GSO cloud-sync service.

For this standalone shell, before migrations or imports:

1. Pause application writes/jobs in a controlled maintenance window. Preserve an
   exact operator copy and create a SQLite backup using its backup API; do not copy
   only the main database while ignoring a live WAL.
2. Capture `DISPOSAL_PRIVATE_ROOT`, required media and retained exports to a
   restricted location outside Git/web roots. Record file sizes and SHA-256 hashes.
   Keep configuration/secrets separately protected, with limited restore access.
3. Restore to an isolated database/storage directory. Check SQLite integrity,
   migration state, asset and stock counts/balances, and every referenced evidence
   file. Run the affected workflows there. Do not overwrite operator data for a test.
4. Retain the pre-change set and import mapping until review accepts the migration.
   Once portable UUIDs are exchanged externally, removing/recreating the identity
   migration would change external identities; restore the coordinated backup or
   make a forward repair instead.

The session's operator SQLite snapshot passed integrity_check and its raw copy
matched the original hash. This is **not** a complete backup/restore acceptance:
private evidence, restore drills, encryption, offsite retention, RPO/RTO and
production operating procedures remain to be established and verified.

### Receiving evidence under development

The receiving feature retains files before committing their database metadata.
An injected audit-write failure verifies that metadata/version changes roll back,
but the file survives. Database transactions cannot roll back filesystem writes.
Include these unreferenced files in protected backup and investigate them during
maintenance reconciliation; do not automatically delete them or attach them to a
receipt based on filenames. Compare stored file paths, hashes and sizes to committed
evidence records. Missing or changed referenced files block submission/acceptance.
Run `python manage.py check_receiving_evidence` with the intended database and private
storage configuration during a maintenance window with writes paused, or against an
isolated restored copy. It prints a JSON report and exits nonzero for missing/changed,
unsafe-path or unreferenced files. It never repairs, deletes or attaches files.
Restrict the report like other operational records. Only receiving evidence is
covered; disposal attachments and Accounting import snapshots still require checks.
Do not run against a changing live store and interpret transient results as a verified
backup. Symlink/junction redirection and paths outside receiving storage are rejected.

A synthetic SQLite receipt/evidence restore and deliberate-corruption drill passed
on 2026-10-17; see the validation record. This is not proof of source-document
authenticity, malware scanning, complete operator recovery, or GRAND two-store recovery.

A separate stopped synthetic GRAND preview was backed up/restored as a paired
default/finance SQLite set on 2026-10-17: all 193 default and 83 finance table contents
matched, both integrity/foreign-key checks passed, and loss of an approval event in
the restored copy was detected then recovered. Original source hashes were unchanged.
This database-only rehearsal covers attribution relationships/history; its fixture
had no private attachment set. It does not establish online MySQL backup consistency,
offsite retention, operational RPO/RTO or complete GRAND private-file recovery.

## Supply-count evidence

Include `inventory/stock_counts/` in coordinated private storage backups. Run
`python manage.py check_stock_count_evidence` against the paused/restored intended
store; it reports missing, changed, unsafe and orphan files without repairing them.
Review and downloads check retained hashes and sizes. Filesystem writes cannot roll
back with a failed database transaction; investigate unreferenced files rather than
silently deleting them. A stopped synthetic paired restore preserved201 default and
83 finance tables plus one count file, detected/restored corruption/loss and left
source hashes unchanged. See [validation](validation-2026-10-16.md); this does not
establish online/operator recovery or document authenticity.

## Gates still open

Witnessed returns add private files under `inventory/custody_returns/`; include them
in the coordinated backup alongside both GRAND databases. Run the read-only
`check_custody_return_evidence` on the restored copy. The stopped synthetic rehearsal
preserved198 default/83 finance tables plus one return file, detected/restored file
corruption and loss, and preserved source hashes. See [returns](custody-returns.md)
and [validation](validation-2026-10-16.md); online/operator recovery remains open.

- Use GRAND's authentication, permissions and source-visibility checks during merge,
  including its UAT-viewer mutation denials. This shell is not a replacement IdP.
- Internet deployment needs tested login/reset rate limiting, secret/email setup,
  HTTPS proxy trust configuration, request limits, protected storage, monitoring,
  least-privilege database accounts and a restore rehearsal. No proxy header is
  trusted by default; only configure it for an actual proxy that strips forged headers.
- Native MySQL integration must address existing conditional unique constraints
  and validate write races; SQLite alone is insufficient. Model save hooks are
  application controls and do not make data immune to direct administrator SQL.
- Official-form acceptance, audit retention policy, lost-item accountability and
  safe historical correction workflows remain in the roadmap.

## GRAND legacy inventory authority

Asset register, legacy handoff, disposal and physical-verification actions use
GRAND explicit user/group grants. A superuser flag alone does not grant an action.
Finance UAT membership denies all mutation checks even when action grants exist.
Scoped reads retain explicit grants: history pages may use the existing workflow
action permission in read-only mode, while forms/services use the mutation check.
This preserves review access without granting edit, acknowledgment, disposal or
count authority. No grants are installed automatically. Standalone permissions
remain compatible. Navigation resolves real scoped read helpers. Maintenance and
stock audit reads also require explicit grants in GRAND.

The internal read_only argument is only for read routes/navigation; it must never
be derived from request input or passed by mutation services. Department/owner,
independent review and lifecycle checks still apply separately. No data migration,
public service, authentication backend or Finance posting path is introduced.
