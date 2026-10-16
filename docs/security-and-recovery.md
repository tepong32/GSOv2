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

## Gates still open

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
