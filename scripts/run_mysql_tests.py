"""Run GSO tests against fresh schemas on an explicitly disposable loopback MySQL server."""
import argparse
import os
from pathlib import Path
import sys
import tempfile
from uuid import uuid4


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("labels", nargs="*")
    parser.add_argument("--verbosity", type=int, choices=(0, 1, 2, 3), default=1)
    args = parser.parse_args()
    password = os.environ.get("GSO_TEST_MYSQL_PASSWORD")
    try:
        port = int(os.environ.get("GSO_TEST_MYSQL_PORT", ""))
    except ValueError:
        parser.error("Set GSO_TEST_MYSQL_PORT to the disposable server's loopback port.")
    if not password or not 1 <= port <= 65535:
        parser.error("A nonempty GSO_TEST_MYSQL_PASSWORD and valid port are required.")
    user = os.environ.get("GSO_TEST_MYSQL_USER", "root")
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    # Never load operator .env or write tests into configured evidence directories.
    import dotenv
    dotenv.load_dotenv = lambda *a, **kw: False
    os.environ.update(DJANGO_SETTINGS_MODULE="src.settings", DEBUG="1", SKEY="synthetic-mysql-tests-only")
    import pymysql
    pymysql.install_as_MySQLdb()
    with pymysql.connect(host="127.0.0.1", port=port, user=user, password=password) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT VERSION(), @@sql_mode")
            version, mode = cursor.fetchone()
    if "MariaDB" in version or not {"STRICT_TRANS_TABLES", "STRICT_ALL_TABLES"}.intersection(mode.split(",")):
        parser.error("Native MySQL with strict SQL mode is required.")
    from django.conf import settings
    runtime_root = root / ".tmp"
    runtime_root.mkdir(exist_ok=True)
    runtime = Path(tempfile.mkdtemp(prefix="mysql-tests-", dir=runtime_root))
    schema = "gso_test_" + uuid4().hex
    settings.DATABASES = {"default": {
        "ENGINE": "django.db.backends.mysql", "NAME": schema,
        "TEST": {"NAME": schema}, "HOST": "127.0.0.1", "PORT": port,
        "USER": user, "PASSWORD": password, "OPTIONS": {"charset": "utf8mb4"},
    }}
    settings.MEDIA_ROOT = runtime / "media"
    settings.DISPOSAL_PRIVATE_ROOT = runtime / "private"
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    import django
    django.setup()
    from django.core.management import call_command
    print(f"MySQL {version}, loopback port {port}, fresh schema {schema}; artifacts {runtime}", flush=True)
    call_command("test", *args.labels, interactive=False, keepdb=False, verbosity=args.verbosity)


if __name__ == "__main__":
    main()
