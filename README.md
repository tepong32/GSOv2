# GRAND GSO Inventory concept

This repository is a standalone development shell for the GSO asset inventory module intended for integration into the municipal GRAND application. The active product code lives in `inventory/`. Its local `user` app and Django project settings exist only to make the concept runnable; GRAND integration should use GRAND's existing `users.User`, `profiles.EmployeeProfile`, and `departments.Department` records.

## Current workflow

- The department dashboard links to an asset register and shows live counts by status.
- Employees search and filter records, open an asset detail page, and add or update records according to their granted permissions.
- “Delete” is implemented as retirement. It removes an asset from active use while retaining its row and an immutable change snapshot.
- Each asset records its department scope, creator, last editor, and timestamps. Create, update, and retirement actions write audit events.
- The register is database-backed. Excel and Google Sheets are not live data stores; exports/imports can be added as explicit workflows later.
- Equipment and vehicles have separate types. Record each new tagged unit as its own asset and retain optional COA, fund, purchase-order, voucher, and journal references for later Finance reconciliation. COA mappings are references for review, not automatic accounting entries.
- Consumables have an append-only movement register for receipts, issues, returns, and reasoned adjustments. Quantity-only tracking is the default. FIFO lot allocation can be enabled per supply item; when enabled, issues use the oldest available receipt lot first. Unit cost is optional and does not create or post a Finance journal. GSO can export movement history to CSV; department users with view access see only their issue history.
- Asset and stock CSVs are controlled interchange exports for review and reconciliation. They are not, by themselves, accepted COA forms or accounting entries.

## Access model

The assigned department scopes each view. GSO staff with the appropriate permission can manage the complete register; other departments can be granted read access to assets assigned to their office. Scope alone grants no actions. Django model permissions control each operation, and checks run in both the request view and write service:

| Permission | Capability |
| --- | --- |
| `inventory.view_asset` | View and search GSO assets or assets assigned to the user's office |
| `inventory.add_asset` | Create asset records |
| `inventory.change_asset` | Update asset records |
| `inventory.delete_asset` | Retire an asset; the database row is retained |
| `inventory.view_asset_audit` | View change history |
| `inventory.export_asset_register` | Export the scoped asset register and accounting references as CSV |
| `inventory.view_consumableitem` | View GSO supply items (department users see only items with issues to their department) |
| `inventory.add_consumableitem` | Add a supply item |
| `inventory.receive_stock` | Record receipts and returns |
| `inventory.issue_stock` | Issue supplies to a department |
| `inventory.adjust_stock` | Record a balance adjustment with a reason |
| `inventory.view_stock_audit` | View supply movement history |
| `inventory.export_stock_register` | Export supply movement history as CSV |

For standalone concept work, create Django Groups in `/admin/` and assign the permissions above. Suggested groups are GSO Viewer, GSO Clerk, and GSO Asset Steward. `/admin/` manages accounts, departments, groups, and permissions; asset changes go through the scoped inventory workflow. Keep `is_staff` limited to people who need Django admin; ordinary inventory users do not need staff access. Public registration and Google OAuth are intentionally not enabled in this shell.

## Run locally

1. Create and activate a virtual environment.
2. Install `requirements.txt`.
3. Run `python manage.py migrate`.
4. Create an administrator with `python manage.py createsuperuser`.
5. In `/admin/`, create/confirm the General Services department, create employee accounts, and assign inventory permissions through Groups.
6. Run `python manage.py runserver` and sign in at `/login/`.

The local settings use SQLite, Asia/Manila time, and console email for password reset. Set `SKEY`, `DEBUG`, `ALLOWED_HOSTS`, and mail settings through environment variables for a controlled deployment; the fallback secret is only for local development.

## GRAND integration target

The module uses `settings.AUTH_USER_MODEL` for actors. `inventory.access.department_for_user()` reads GRAND's `employeeprofile.assigned_department`; the fallback to the local `user.User.department` exists only for this standalone shell. The inventory stores a numeric `department_id` and a label snapshot rather than a foreign key, following GRAND's finance-domain pattern and keeping the module portable across database boundaries. In GRAND, both the asset table and its user foreign keys should use the default database; do not route GSO assets to the separate Finance database.

Integration should:

1. Add `inventory` to GRAND's installed apps and include its namespaced URLs.
2. Keep GRAND's shared login, HR provisioning, user profiles, and department directory; remove the local `user` app and local auth templates/settings.
3. Keep this module's GSO scope and action checks. A GSO dashboard card is only a route entry; it does not grant access. Replace the planned Inventory Register entry in GRAND's GSO workspace preset with the namespaced `inventory:asset-list` route and reuse GRAND's shared dashboard shell.
4. Assign the `inventory` permissions to existing GRAND Groups or users. A department assignment by itself should not grant read/write/delete.
5. Route `inventory` migrations to the default database. Finance's database separation remains unchanged.
6. Import and reconcile legacy data before the new register becomes authoritative. The former `home.Item` schema is preserved under `home/` as a reference and is no longer installed or routed. Its fields map to the new asset form as follows: date → purchase date; OBR number → OBR/reference; category and subcategory → category text; brand/supplier/price/quantity/status/return date/notes → corresponding asset fields. Derive the asset name from the old category/brand after review, and confirm whether each row represents one item or a pooled quantity. Review old status values before mapping them to the new in-service, maintenance, transferred, and retired states.

Property transfer acknowledgements, maintenance work orders, document attachments, official COA reports, and automatic journal posting remain future work. Supply movements and asset references provide auditable source data for later GRAND integration and reconciliation.
