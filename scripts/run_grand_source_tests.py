"""Validate the read-only GSO adapter against an explicit GRAND checkout in fresh databases."""
import argparse
import os
from pathlib import Path
import sys
import tempfile
from uuid import uuid4


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grand-root", type=Path, required=True)
    parser.add_argument("--mysql", action="store_true", help="Use fresh schemas on an explicitly configured disposable loopback MySQL server.")
    args = parser.parse_args()
    grand = args.grand_root.resolve()
    if not (grand / "src/settings/dev.py").is_file() or not (grand / "vouchers/case_exports.py").is_file():
        parser.error("Choose a GRAND checkout with its current settings and voucher visibility module.")
    gso = Path(__file__).resolve().parents[1]
    sys.path[:0] = [str(grand), str(gso)]
    import dotenv
    dotenv.load_dotenv = lambda *a, **kw: False
    os.environ["DJANGO_SETTINGS_MODULE"] = "src.settings.dev"
    from django.conf import settings
    runtime_root = gso / ".tmp"
    runtime_root.mkdir(exist_ok=True)
    runtime = Path(tempfile.mkdtemp(prefix="grand-source-tests-", dir=runtime_root))
    settings.DATABASES = {alias: {"ENGINE": "django.db.backends.sqlite3", "NAME": str(runtime / f"unused-{alias}.sqlite3"),
                                 "TEST": {"NAME": str(runtime / f"test-{alias}.sqlite3")}}
                          for alias in ("default", "finance")}
    if args.mysql:
        password = os.environ.get("GSO_TEST_MYSQL_PASSWORD")
        try:
            port = int(os.environ.get("GSO_TEST_MYSQL_PORT", ""))
        except ValueError:
            parser.error("Set GSO_TEST_MYSQL_PORT to the disposable loopback server port.")
        if not password or not 1 <= port <= 65535:
            parser.error("A nonempty GSO_TEST_MYSQL_PASSWORD and valid port are required.")
        import pymysql
        pymysql.install_as_MySQLdb()
        credentials = dict(host="127.0.0.1", port=port,
                           user=os.environ.get("GSO_TEST_MYSQL_USER", "root"), password=password)
        with pymysql.connect(**credentials) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT VERSION(), @@sql_mode")
                version, mode = cursor.fetchone()
        if "MariaDB" in version or not {"STRICT_TRANS_TABLES", "STRICT_ALL_TABLES"}.intersection(mode.split(",")):
            parser.error("Native MySQL with strict SQL mode is required.")
        prefix = "gso_grand_test_" + uuid4().hex
        settings.DATABASES = {alias: {
            "ENGINE": "django.db.backends.mysql", "NAME": f"{prefix}_{alias}",
            "TEST": {"NAME": f"{prefix}_{alias}"}, "HOST": credentials["host"],
            "PORT": port, "USER": credentials["user"], "PASSWORD": password,
            "OPTIONS": {"charset": "utf8mb4"},
        } for alias in ("default", "finance")}
        print(f"MySQL {version}; disposable loopback port {port}; schema prefix {prefix}", flush=True)
    settings.MEDIA_ROOT = runtime / "media"
    settings.DISPOSAL_PRIVATE_ROOT = runtime / "private-evidence"
    settings.INSTALLED_APPS = [*settings.INSTALLED_APPS, "inventory.apps.InventoryConfig",
                               "inventory_finance.apps.InventoryFinanceConfig"]
    settings.GRAND_EXPORT_ROOT = runtime / "exports"
    settings.GRAND_BACKUP_ROOT = runtime / "backups"
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.ROOT_URLCONF = "gso_integration_tests.urls"
    import django
    django.setup()
    from django.core.management import call_command
    print(f"GRAND source: {grand}; isolated runtime: {runtime}", flush=True)
    call_command("test", "gso_integration_tests.grand_claim_sources", "gso_integration_tests.grand_attribution",
                 "gso_integration_tests.grand_attribution_http",
                 "gso_integration_tests.grand_maintenance",
                 "gso_integration_tests.grand_employee_sources",
                 "gso_integration_tests.grand_employee_custody",
                 "gso_integration_tests.grand_employee_custody_http",
                 "gso_integration_tests.grand_employee_custody_races",
                 "gso_integration_tests.grand_custody_review",
                 "gso_integration_tests.grand_custody_returns",
                 "gso_integration_tests.grand_custody_return_http",
                 "gso_integration_tests.grand_custody_return_races",
                 "gso_integration_tests.grand_stock_authority",
                 "gso_integration_tests.grand_stock_counts",
                 "gso_integration_tests.grand_receipt_basis",
                 "gso_integration_tests.grand_receiving_authority",
                 "gso_integration_tests.grand_asset_authority",
                 "gso_integration_tests.grand_receipt_amendments",
                 "gso_integration_tests.grand_journal_sources",
                 "gso_integration_tests.grand_journal_mappings",
                 interactive=False, keepdb=False, verbosity=1)


if __name__ == "__main__":
    main()
