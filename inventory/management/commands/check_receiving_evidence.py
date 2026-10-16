"""Read-only evidence reconciliation for maintenance windows and restored copies."""
import hashlib
import json
import os
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from inventory.models import ReceivingEvidence


class Command(BaseCommand):
    help = "Check receiving evidence hashes and report unreferenced files. Never changes data or files."

    def handle(self, *args, **options):
        storage = ReceivingEvidence._meta.get_field("file").storage
        if not hasattr(storage, "location"):
            raise CommandError("This check requires the configured local private file storage.")
        root = Path(storage.location).resolve()
        namespace = root / "inventory" / "receiving"
        report = {"checked": 0, "missing": [], "changed": [], "unsafe": [], "unreferenced": []}
        referenced = set()
        for record in ReceivingEvidence.objects.order_by("pk").iterator():
            name = record.file.name
            path = root / name
            try:
                path.resolve().relative_to(namespace)
                if ".." in Path(name).parts or path.resolve() != path:
                    raise ValueError
            except ValueError:
                report["unsafe"].append({"id": record.pk, "path": name})
                continue
            referenced.add(path.resolve())
            report["checked"] += 1
            try:
                digest = hashlib.sha256()
                size = 0
                with path.open("rb") as source:
                    for block in iter(lambda: source.read(1024 * 1024), b""):
                        digest.update(block)
                        size += len(block)
            except OSError:
                report["missing"].append({"id": record.pk, "path": name})
                continue
            if digest.hexdigest() != record.sha256 or size != record.size:
                report["changed"].append({"id": record.pk, "path": name})

        def unreadable(error):
            raise CommandError("Cannot enumerate receiving storage; check filesystem access.") from error

        if namespace.resolve() != namespace:
            report["unsafe"].append({"path": "inventory/receiving"})
        else:
            for directory, dirs, files in os.walk(namespace, followlinks=False, onerror=unreadable):
                for name in list(dirs):
                    path = Path(directory) / name
                    if path.resolve() != path:
                        report["unsafe"].append({"path": path.relative_to(root).as_posix()})
                        dirs.remove(name)
                for name in files:
                    path = Path(directory) / name
                    relative = path.relative_to(root).as_posix()
                    if path.resolve() != path:
                        report["unsafe"].append({"path": relative})
                    elif path.resolve() not in referenced:
                        report["unreferenced"].append(relative)
        self.stdout.write(json.dumps(report, indent=2))
        if any(report[key] for key in ("missing", "changed", "unsafe", "unreferenced")):
            raise CommandError("Receiving evidence requires investigation. No data or files were changed.")
