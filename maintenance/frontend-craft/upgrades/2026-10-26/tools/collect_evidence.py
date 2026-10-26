"""Inventory existing evidence; never infer a successful check from a file."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import hashlib
import json
from PIL import Image

REPO = Path(__file__).resolve().parents[5]
UPGRADE = Path(__file__).resolve().parents[1]
EVIDENCE = UPGRADE / "evidence"
TZ = timezone(timedelta(hours=8))


def inventory():
    paths = list(EVIDENCE.rglob("*"))
    paths += list((UPGRADE / "reports").rglob("*"))
    paths += list((UPGRADE / "user-review").rglob("*"))
    paths += [UPGRADE / "ACCEPTANCE-ADDENDUM-2026-10-26.md"]
    paths += [UPGRADE / "delivery/original-package.zip", UPGRADE / "delivery/original-package-archive.json"]
    paths += list((REPO / "frontend-craft/assets/references").rglob("*"))
    entries = []
    for path in sorted(paths):
        if not path.is_file() or path == EVIDENCE / "manifest.json":
            continue
        if "__pycache__" in path.parts or path.suffix == ".log":
            continue
        rel = path.relative_to(REPO).as_posix()
        item = {
            "path": rel,
            "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "file_modified_at": datetime.fromtimestamp(path.stat().st_mtime, TZ).isoformat(),
            "purpose": "retained source or execution record; not itself a pass assertion",
        }
        if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
            with Image.open(path) as image:
                item.update(kind="screenshot", encoding=image.format,
                            pixel_width=image.width, pixel_height=image.height)
            item["purpose"] = "original browser capture; CSS viewport/state belongs to the associated record"
        if "/user-review/" in rel:
            item["context_record"] = "maintenance/frontend-craft/upgrades/2026-10-26/reports/user-review-status.md"
            item["purpose"] = "user comparison viewer or its verification; no user preference or acceptance is inferred"
        elif "/canonical/" in rel:
            item["context_record"] = "maintenance/frontend-craft/upgrades/2026-10-26/evidence/canonical/captures.json"
            item["purpose"] = "neutral paired capture or independent interaction record; consult state metadata and blind comparison"
        elif "/runs/" in rel:
            scene, label = rel.split("/runs/")[1].split("/")[:2]
            item.update(scene=scene, label=label, attempt=1,
                        context_record=f"maintenance/frontend-craft/upgrades/2026-10-26/evidence/runs/{scene}/{label}/BUILD.md")
        elif "/style-lab/" in rel:
            item["context_record"] = "maintenance/frontend-craft/upgrades/2026-10-26/reports/style-lab-review.md"
        elif "/assets/references/" in rel:
            item["context_record"] = "frontend-craft/references/exemplar-index.json"
        elif "/reports/" in rel:
            item["purpose"] = "review or execution record; inspect stated scope and raw evidence rather than infer pass"
        entries.append(item)
    output = {
        "schema_version": 1,
        "generated_at": datetime.now(TZ).isoformat(),
        "path_base": "repository root, five parents above this manifest directory",
        "limitations": "mtime is file metadata, not an invented observation timestamp; inspect context records and raw artifacts.",
        "entries": entries,
    }
    (EVIDENCE / "manifest.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"files": len(entries), "missing": []}))


if __name__ == "__main__":
    inventory()
