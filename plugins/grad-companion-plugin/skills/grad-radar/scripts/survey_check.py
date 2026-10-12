# /// script
# requires-python = ">=3.12"
# ///
"""Read-only consistency check for a survey outline and its production manifest; fetches no material and does not verify facts or teaching quality."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


class InvalidManifest(ValueError):
    pass


def source_identity(row: dict) -> str | None:
    """Normalize declared identity without fetching or guessing a paper."""
    explicit = row.get("source_id")
    value = explicit or row.get("id") or row.get("source_url") or row.get("html_url")
    if not isinstance(value, str) or not value.strip():
        return None
    value = value.strip()
    arxiv = re.fullmatch(r"(?:arxiv:|https?://arxiv\.org/(?:abs|html)/)?"
                        r"(\d{4}\.\d{4,5}|[a-zA-Z.-]+/\d{7})(?:v[1-9]\d*)?", value)
    if arxiv:
        return "arxiv:" + arxiv.group(1)
    doi = re.fullmatch(r"(?:doi:|https?://(?:dx\.)?doi\.org/)(10\.\d{4,9}/\S+)", value, re.I)
    if doi:
        return "doi:" + doi.group(1).lower()
    return value if explicit else None


def markdown_headings(text: str) -> set[str]:
    headings = set()
    fence = None
    for line in text.splitlines():
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if marker:
            run, tail = marker.groups()
            if fence is None:
                fence = (run[0], len(run))
            elif run[0] == fence[0] and len(run) >= fence[1] and not tail.strip():
                fence = None
            continue
        heading = re.match(r"^ {0,3}#{1,6}[ \t]+(.+?)\s*$", line)
        if fence is None and heading:
            headings.add(re.sub(r"\s+#+\s*$", "", heading.group(1)).strip())
    return headings


def check_coverage(outline: object, coverage: object, guide_text: str | None = None) -> dict:
    if guide_text is not None and not isinstance(guide_text, str):
        raise InvalidManifest("Guide body must be a string")
    if isinstance(outline, dict) and "ok" in outline:
        if outline.get("ok") is not True:
            raise InvalidManifest("Outline retrieval did not succeed and cannot be used as evidence of completeness")
        outline = outline.get("data")
    if not isinstance(outline, dict) or not isinstance(coverage, dict):
        raise InvalidManifest("Outline and production manifest must be objects")
    source_sections = outline.get("sections")
    if not isinstance(source_sections, list) or not source_sections:
        raise InvalidManifest("Outline sections must be a non-empty array")
    sections = coverage.get("sections")
    assets = coverage.get("assets")
    if not isinstance(sections, list) or not isinstance(assets, list):
        raise InvalidManifest("Production manifest must include sections and assets arrays")

    def indexed(rows: list, label: str) -> dict:
        result = {}
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"].strip():
                raise InvalidManifest(f"Every {label} entry must have a non-empty string id")
            if row["id"] in result:
                raise InvalidManifest("{} contains duplicate id: {}".format(label, row["id"]))
            result[row["id"]] = row
        return result

    original = indexed(source_sections, "outline")
    registered = indexed(sections, "section")
    indexed(assets, "asset")
    extra = set(registered) - set(original)
    if extra:
        raise InvalidManifest("Manifest contains sections outside the outline: " + ", ".join(sorted(extra)))
    gaps = []
    identity = source_identity(outline)
    if not identity:
        gaps.append("Source identity is unconfirmed")
    if not source_identity(coverage):
        gaps.append("Production manifest is missing source_id")
    elif source_identity(coverage) != identity:
        gaps.append("Production manifest does not match the source identity")
    version = outline.get("version")
    if not isinstance(version, str) or not version.strip():
        gaps.append("Source version is unconfirmed")
    if identity and identity.startswith("arxiv:"):
        if not isinstance(version, str) or not re.fullmatch(r"v[1-9]\d*", version):
            gaps.append("For arXiv sources, version must be a confirmed vN")
    else:
        fingerprint = outline.get("source_sha256")
        if not isinstance(fingerprint, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", fingerprint):
            gaps.append("Non-arXiv source is missing a valid source_sha256")
        elif not isinstance(coverage.get("source_sha256"), str) or coverage["source_sha256"].lower() != fingerprint.lower():
            gaps.append("Production manifest does not match the source fingerprint")
    if not isinstance(outline.get("version_status"), str) or outline["version_status"] not in {"confirmed", "cache-fallback"}:
        gaps.append("Outline version status is unconfirmed")
    if coverage.get("version") != version:
        gaps.append("Production manifest does not match the outline version")
    body_count = 0
    taught_count = 0
    headings = markdown_headings(guide_text) if guide_text is not None else None
    for sid, source in original.items():
        kind = source.get("kind")
        if not isinstance(kind, str) or kind not in {"abstract", "numbered", "appendix", "bibliography", "acknowledgments"}:
            raise InvalidManifest(f"Unknown outline kind: {sid}")
        if kind in {"abstract", "numbered"}:
            body_count += 1
        item = registered.get(sid)
        if item is None:
            gaps.append(f"Section is not registered: {sid}")
            continue
        for flag in ("processed", "checked"):
            if not isinstance(item.get(flag), bool):
                raise InvalidManifest(f"{sid}.{flag} must be a boolean")
        disposition = item.get("disposition")
        if not isinstance(disposition, str) or disposition not in {"taught", "reference-only", "pending"}:
            raise InvalidManifest(f"Unknown section disposition: {sid}")
        if item["checked"] and not item["processed"]:
            raise InvalidManifest(f"{sid} is marked checked but has not been processed")
        if "required" in item and not isinstance(item["required"], bool):
            raise InvalidManifest(f"{sid}.required must be a boolean")
        if disposition == "reference-only":
            if not isinstance(item.get("reason"), str) or not item["reason"].strip():
                raise InvalidManifest(f"{sid} is index-only but has no reason")
            if kind in {"abstract", "numbered"}:
                gaps.append(f"Main section is index-only: {sid}")
            if kind == "appendix" and item.get("required", True):
                gaps.append(f"Required appendix is index-only: {sid}")
            continue
        if disposition == "pending":
            gaps.append(f"Section is pending: {sid}")
            continue
        if not isinstance(item.get("guide_heading"), str) or not item["guide_heading"].strip():
            raise InvalidManifest(f"{sid} is missing the corresponding guide heading")
        if headings is not None and item["guide_heading"].strip() not in headings:
            gaps.append("{} has no matching guide heading: {}".format(sid, item["guide_heading"]))
        if not item["processed"] or not item["checked"]:
            gaps.append(f"Section is not processed/checked: {sid}")
        else:
            taught_count += 1
    if not body_count:
        gaps.append("Outline has no abstract or main section")
    for asset in assets:
        aid = asset["id"]
        if not isinstance(asset.get("kind"), str) or asset["kind"] not in {"figure", "table", "formula"}:
            raise InvalidManifest(f"Unknown asset kind: {aid}")
        if not isinstance(asset.get("required"), bool) or not isinstance(asset.get("checked"), bool):
            raise InvalidManifest(f"{aid} required/checked must be booleans")
        basis = asset.get("basis")
        if not isinstance(basis, str) or basis not in {"text", "visual", "caption-only", "unavailable"}:
            raise InvalidManifest(f"Unknown asset basis: {aid}")
        reliable = basis == "visual" if asset["kind"] == "figure" else basis in {"text", "visual"}
        if asset["checked"] and not reliable:
            raise InvalidManifest(f"{aid} lacks sufficient retrieval evidence to be marked checked")
        if asset["required"] and not asset["checked"]:
            gaps.append(f"Required asset is pending: {aid}")
        if not asset["required"] and not asset["checked"] and (
            not isinstance(asset.get("reason"), str) or not asset["reason"].strip()
        ):
            gaps.append(f"Optional unchecked asset is missing a decision rationale: {aid}")
    return {"coverage_ready": not gaps, "gaps": gaps,
            "sections_in_outline": len(original), "sections_taught_checked": taught_count,
            "assets_declared": len(assets),
            "source_id": identity, "guide_headings_checked": guide_text is not None,
            "verification_scope": "Checks only outline/manifest consistency; does not prove manifest completeness, factual accuracy, sufficient explanation, or that the user has read the material."}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outline-file", required=True)
    parser.add_argument("--coverage-file", required=True)
    parser.add_argument("--guide-file", help="Optional Markdown guide; check whether referenced headings exist")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--require-ready", action="store_true", help="Exit with code 2 when the manifest has gaps")
    args = parser.parse_args()
    try:
        outline = json.loads(Path(args.outline_file).read_text(encoding="utf-8"))
        coverage = json.loads(Path(args.coverage_file).read_text(encoding="utf-8"))
        guide = Path(args.guide_file).read_text(encoding="utf-8") if args.guide_file else None
        data = check_coverage(outline, coverage, guide)
    except (OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": "BAD_INPUT", "detail": str(exc)}, ensure_ascii=False))
        sys.exit(1)
    if args.json:
        print(json.dumps({"ok": True, "data": data}, ensure_ascii=False))
    else:
        print("Manifest is ready for content review" if data["coverage_ready"] else "Manifest has gaps: " + "; ".join(data["gaps"]))
        print(data["verification_scope"])
    if args.require_ready and not data["coverage_ready"]:
        sys.exit(2)


if __name__ == "__main__":
    if sys.stdout and sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    main()
