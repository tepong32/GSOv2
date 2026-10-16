# GRAND GSO Inventory concept

This repository is a standalone development shell for the GSO asset inventory module intended for integration into the municipal GRAND application. The active product code lives in `inventory/`. Its local `user` app and Django project settings exist only to make the concept runnable; GRAND integration should use GRAND's existing `users.User`, `profiles.EmployeeProfile`, and `departments.Department` records.

## Current workflow

- The department dashboard links to an asset register and shows live counts by status.
- Employees search and filter records, open an asset detail page, and add or update records according to their granted permissions.
- Asset records are not deleted through the application. Disposal is handled through a review case so a request cannot silently retire an asset.
- Each asset records its department scope, creator, last editor, and timestamps. Create, update, and retirement actions write audit events.
- GSO can start a handoff to another department. The receiving department gets a pending item and explicitly acknowledges receipt; only then does the asset assignment change. GSO can cancel a pending handoff with a reason. The request, acknowledgement, cancellation, and resulting assignment snapshot are retained.
- GSO can start a dated physical verification round. The system snapshots all non-retired assets in the GSO register, then staff record each as found and matched, found with a discrepancy, or not found. Checks capture observed location/custodian and condition; discrepancy and missing results require a note. Re-checks append immutable history, and a round cannot close while assets remain unchecked. Results support LGU inventory control and audit preparation; they do not replace required physical inventory forms or certify compliance.
- The register is database-backed. Excel and Google Sheets are not live data stores; exports/imports can be added as explicit workflows later.
- Equipment/furniture and vehicles have separate record types. Each asset has a controlled inventory/accounting class (ICT, office, printing, communications, other machinery, furniture and fixtures, transportation, or other) and an item type (such as desktop, laptop, printer, UPS, desk, chair, or motor vehicle). Additional description preserves legacy labels without driving classification. Existing rows default to “Needs Accounting review” and “Other / describe below” until classified.
- Inventory class and item type support consistent tracking and reporting; they do not set an official COA account or determine PPE versus semi-expendable treatment. Accounting confirms the COA code/title and treatment under the applicable LGU rules. Retain optional fund, purchase-order, voucher, journal, and mapping-review references for later Finance reconciliation. No accounting entries are posted.
- Consumables have an append-only movement register for receipts, issues, returns, and reasoned adjustments. Quantity-only tracking is the default. FIFO lot allocation can be enabled per supply item; when enabled, issues use the oldest available receipt lot first. Unit cost is optional and does not create or post a Finance journal. GSO can export movement history to CSV; department users with view access see only their issue history.
- Disposal requests start from an assigned asset record. The requester describes the condition, attaches at least one condition photo and a signed request form, and may add supporting records. On smartphones, the photo field offers the rear camera through the browser while still allowing image selection. GSO can review the case, request more information, authorize it with an authority reference and document, reject it with a reason, or record completed disposal with method, date, reference, and completion evidence. The asset remains in the register until completion is recorded.
- Disposal attachments are stored in a private directory and opened through a permission-checked application route. Generated filenames include the asset tag (or asset ID), case number, document type, and a unique suffix; original filenames remain in the case record. Attachments and case history cannot be replaced or deleted through application workflows. Configure `DISPOSAL_PRIVATE_ROOT` to a protected, backed-up location outside any web-served media directory in deployment; configure the web server's request size limit to allow the documented maximum 50 MB total per request.
- Recommended production media design and a comparison with Namecheap local storage and a self-managed remote media server are documented in [Media storage decision](docs/media-storage-decision.md). The current concept uses private local storage; cloud object storage is a deployment/integration change, not yet implemented.
- The disposal workflow organizes evidence; it does not generate or certify official COA forms. GSO and Accounting must confirm the applicable LGU process and supporting documents. The case can hold inspection/appraisal reports, resolutions, vehicle records, waste-material records, and disposal receipts as supporting documents.
- Asset and stock CSVs are controlled interchange exports for review and reconciliation. They are not, by themselves, accepted COA forms or accounting entries.

## Access model

The assigned department scopes each view. GSO staff with the appropriate permission can manage the complete register; other departments can be granted read access to assets assigned to their office. Scope alone grants no actions. Django model permissions control each operation, and checks run in both the request view and write service:

| Permission | Capability |
| --- | --- |
| `inventory.view_asset` | View and search GSO assets or assets assigned to the user's office |
| `inventory.add_asset` | Create asset records |
| `inventory.change_asset` | Update asset records |
| `inventory.delete_asset` | Legacy permission; direct retirement is disabled. Use the reviewed disposal workflow |
| `inventory.view_asset_audit` | View change history |
| `inventory.export_asset_register` | Export the scoped asset register and accounting references as CSV |
| `inventory.transfer_asset` | Start and cancel GSO asset handoffs |
| `inventory.acknowledge_asset_transfer` | Acknowledge pending handoffs addressed to the user's department |
| `inventory.request_asset_disposal` | Submit a disposal assessment request for an assigned asset |
| `inventory.review_asset_disposal` | Review GSO disposal cases and record decisions |
| `inventory.start_asset_verification` | Start a dated physical verification round from the GSO register |
| `inventory.record_asset_verification` | Record or re-check physical findings during an open round |
| `inventory.close_asset_verification` | Close a round after every listed asset has a result |
| `inventory.view_consumableitem` | View GSO supply items (department users see only items with issues to their department) |
| `inventory.add_consumableitem` | Add a supply item |
| `inventory.receive_stock` | Record receipts and returns |
| `inventory.issue_stock` | Issue supplies to a department |
| `inventory.adjust_stock` | Record a balance adjustment with a reason |
| `inventory.view_stock_audit` | View supply movement history |
| `inventory.export_stock_register` | Export supply movement history as CSV |

For standalone concept work, create Django Groups in `/admin/` and assign the permissions above. Give GSO staff `transfer_asset`, `review_asset_disposal`, and the three verification permissions as appropriate; give receiving department staff `view_asset` and `acknowledge_asset_transfer`; give department staff submitting requests `view_asset` and `request_asset_disposal`. GSO reviewers can also initiate requests for assets in GSO scope. Suggested groups are GSO Viewer, GSO Clerk, GSO Asset Steward, Department Asset Receiver, and Department Asset Requester. `/admin/` manages accounts, departments, groups, and permissions; asset changes go through the scoped inventory workflow. Keep `is_staff` limited to people who need Django admin; ordinary inventory users do not need staff access. Public registration and Google OAuth are intentionally not enabled in this shell.

## Run locally

1. Create and activate a virtual environment.
2. Install `requirements.txt`.
3. Run `python manage.py migrate`.
4. Create an administrator with `python manage.py createsuperuser`.
5. In `/admin/`, create/confirm the General Services department, create employee accounts, and assign inventory permissions through Groups.
6. Run `python manage.py runserver` and sign in at `/login/`.

The local settings use SQLite, Asia/Manila time, and console email for password reset. Set `SKEY`, `DEBUG`, `ALLOWED_HOSTS`, `DISPOSAL_PRIVATE_ROOT`, and mail settings through environment variables for a controlled deployment; the fallback secret is only for local development. The phone camera option uses a standard HTML file input with `capture`; the browser and device control the camera prompt, so users may need to grant camera permission and some browsers may offer the photo library instead.

## GRAND integration target

The module uses `settings.AUTH_USER_MODEL` for actors. `inventory.access.department_for_user()` reads GRAND's `employeeprofile.assigned_department`; the fallback to the local `user.User.department` exists only for this standalone shell. The inventory stores a numeric `department_id` and a label snapshot rather than a foreign key, following GRAND's finance-domain pattern and keeping the module portable across database boundaries. In GRAND, both the asset table and its user foreign keys should use the default database; do not route GSO assets to the separate Finance database.

Integration should:

1. Add `inventory` to GRAND's installed apps and include its namespaced URLs.
2. Keep GRAND's shared login, HR provisioning, user profiles, and department directory; remove the local `user` app and local auth templates/settings.
3. Keep this module's GSO scope and action checks. A GSO dashboard card is only a route entry; it does not grant access. Replace the planned Inventory Register entry in GRAND's GSO workspace preset with the namespaced `inventory:asset-list` route and reuse GRAND's shared dashboard shell.
4. Assign the `inventory` permissions to existing GRAND Groups or users. A department assignment by itself should not grant read/write/delete.
5. Route `inventory` migrations to the default database. Finance's database separation remains unchanged.
6. Import and reconcile legacy data before the new register becomes authoritative. The former `home.Item` schema is preserved under `home/` as a reference and is no longer installed or routed. Its fields map to the new asset form as follows: date → purchase date; OBR number → OBR/reference; category and subcategory → additional item description; brand/supplier/price/quantity/status/return date/notes → corresponding asset fields. Existing rows require later selection of an inventory class and item type. Derive the asset name from the old category/brand after review, and confirm whether each row represents one item or a pooled quantity. Review old status values before mapping them to the new in-service, maintenance, transferred, and retired states.

Maintenance work orders, employee exit clearance, official COA report generation, and automatic journal posting remain future work. Supply movements, acknowledged custody handoffs, disposal case evidence, physical verification history, and asset references provide traceable source data for later GRAND integration and reconciliation.
