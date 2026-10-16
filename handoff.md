# GSOv2 Work Handoff

## Current checkpoint

- Repo: `GSOv2`
- Working branch: `gso/asset-receiving-tagging`
- Base: `master` at release `v0.2.0`
- Feature checkpoint: guided receiving and tagging for newly delivered equipment and vehicles
- Current branch commit: see `git log -1`; this is a work-in-progress checkpoint, not a release
- `master` already contains the physical count and Accounting reconciliation workflow, released as `v0.2.0`

## What is in progress

The Add asset workflow now captures the delivery/receiving date and reference, inspection reference and notes, and the person who received or inspected the item. Saving creates the asset register entry and its receiving record in one transaction. A receiving record is immutable and retained with the asset. Intake is one tagged asset per entry; likely duplicates by property tag, serial number, or chassis number are shown for review and require explicit confirmation before saving.

Key files:

- `inventory/forms.py` — `AssetReceivingForm` and possible-duplicate checks
- `inventory/models.py` — immutable `AssetReceivingRecord`
- `inventory/services.py` — atomic `receive_asset` workflow
- `inventory/views.py` and `inventory/urls.py` — asset create/detail presentation
- `inventory/templates/inventory/asset_form.html` and `asset_detail.html` — intake and receipt details
- `inventory/migrations/0012_assetreceivingrecord.py` — receiving record table
- `docs/inventory-roadmap.md` and `README.md` — roadmap and user-facing description

## Checks completed

- Django `check`: passed
- `makemigrations --check --dry-run`: passed
- `git diff --check`: passed
- Checks used the available Python 3.13 interpreter with a temporary PIL import shim because this checkout's Python 3.11 virtual environment points to a missing Windows Store interpreter. The shim was temporary and was removed. A full receiving workflow smoke test has not yet been run under the project's supported runtime.
- `db.sqlite3` has a pre-existing local modification. It was deliberately excluded from commits and should remain untouched unless its owner confirms otherwise.

## Pick up here

1. Confirm the branch and working tree with `git status --short --branch`; do not stage `db.sqlite3`.
2. Restore or recreate a working Python environment that matches the project's dependencies, then run migrations and the Django checks.
3. Exercise receiving end-to-end: normal asset receipt, duplicate tag/serial/chassis warning, explicit confirmation for a distinct item, and checking receipt details on the asset page. Confirm the atomic save leaves neither a partial asset nor an unlinked receipt if saving fails.
4. Review the form for clarity and confirm all delivery/inspection fields required by GSO staff are covered. The intake currently records one tagged item at a time and does not invent Accounting's COA mapping.
5. Update this handoff and roadmap if the implementation changes. Once the workflow is verified, commit any fixes on this branch, fast-forward merge it to `master`, push, and use the Version Manager for the release. The current baseline is `v0.2.0`; a minor feature release would be `v0.3.0`.
6. Continue with the next roadmap feature, maintenance history, on its own branch from the updated `master`.

## Release and integration boundaries

The feature branch is not merged or version-released. The Version Manager's release flow also creates a tag and pushes, so do not use it for an unfinished checkpoint. Preserve separate feature branches; only release after checks and review. Follow the remaining sequence in `docs/inventory-roadmap.md`.
