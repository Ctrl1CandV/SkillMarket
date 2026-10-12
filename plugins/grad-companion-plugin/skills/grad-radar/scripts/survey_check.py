# /// script
# requires-python = ">=3.12"
# ///
"""只读核对综述目录与制作清单；不获取材料、不证明事实或讲解质量。"""
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
        raise InvalidManifest("导读正文必须为字符串")
    if isinstance(outline, dict) and "ok" in outline:
        if outline.get("ok") is not True:
            raise InvalidManifest("目录获取未成功，不能作为完整性依据")
        outline = outline.get("data")
    if not isinstance(outline, dict) or not isinstance(coverage, dict):
        raise InvalidManifest("目录与制作清单必须为对象")
    source_sections = outline.get("sections")
    if not isinstance(source_sections, list) or not source_sections:
        raise InvalidManifest("目录 sections 必须是非空数组")
    sections = coverage.get("sections")
    assets = coverage.get("assets")
    if not isinstance(sections, list) or not isinstance(assets, list):
        raise InvalidManifest("制作清单必须包含 sections 与 assets 数组")

    def indexed(rows: list, label: str) -> dict:
        result = {}
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"].strip():
                raise InvalidManifest(f"{label} 各项需要非空字符串 id")
            if row["id"] in result:
                raise InvalidManifest(f"{label} id 重复：{row['id']}")
            result[row["id"]] = row
        return result

    original = indexed(source_sections, "目录")
    registered = indexed(sections, "章节")
    indexed(assets, "资产")
    extra = set(registered) - set(original)
    if extra:
        raise InvalidManifest("清单存在目录外章节：" + ", ".join(sorted(extra)))
    gaps = []
    identity = source_identity(outline)
    if not identity:
        gaps.append("原文身份未确认")
    if not source_identity(coverage):
        gaps.append("制作清单缺少 source_id")
    elif source_identity(coverage) != identity:
        gaps.append("制作清单与原文身份不一致")
    version = outline.get("version")
    if not isinstance(version, str) or not version.strip():
        gaps.append("原文版本未确认")
    if identity and identity.startswith("arxiv:"):
        if not isinstance(version, str) or not re.fullmatch(r"v[1-9]\d*", version):
            gaps.append("arXiv 版本须为实际确认的 vN")
    else:
        fingerprint = outline.get("source_sha256")
        if not isinstance(fingerprint, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", fingerprint):
            gaps.append("非 arXiv 材料缺少有效 source_sha256")
        elif not isinstance(coverage.get("source_sha256"), str) or coverage["source_sha256"].lower() != fingerprint.lower():
            gaps.append("制作清单与原文材料指纹不一致")
    if not isinstance(outline.get("version_status"), str) or outline["version_status"] not in {"confirmed", "cache-fallback"}:
        gaps.append("目录版本状态未确认")
    if coverage.get("version") != version:
        gaps.append("制作清单与目录版本不一致")
    body_count = 0
    taught_count = 0
    headings = markdown_headings(guide_text) if guide_text is not None else None
    for sid, source in original.items():
        kind = source.get("kind")
        if not isinstance(kind, str) or kind not in {"abstract", "numbered", "appendix", "bibliography", "acknowledgments"}:
            raise InvalidManifest(f"未知目录 kind：{sid}")
        if kind in {"abstract", "numbered"}:
            body_count += 1
        item = registered.get(sid)
        if item is None:
            gaps.append(f"未登记章节：{sid}")
            continue
        for flag in ("processed", "checked"):
            if not isinstance(item.get(flag), bool):
                raise InvalidManifest(f"{sid}.{flag} 必须是布尔值")
        disposition = item.get("disposition")
        if not isinstance(disposition, str) or disposition not in {"taught", "reference-only", "pending"}:
            raise InvalidManifest(f"未知章节 disposition：{sid}")
        if item["checked"] and not item["processed"]:
            raise InvalidManifest(f"{sid} 未处理却记为已核对")
        if "required" in item and not isinstance(item["required"], bool):
            raise InvalidManifest(f"{sid}.required 必须是布尔值")
        if disposition == "reference-only":
            if not isinstance(item.get("reason"), str) or not item["reason"].strip():
                raise InvalidManifest(f"{sid} 仅作索引需要 reason")
            if kind in {"abstract", "numbered"}:
                gaps.append(f"主体章节仅作索引：{sid}")
            if kind == "appendix" and item.get("required", True):
                gaps.append(f"必要附录仅作索引：{sid}")
            continue
        if disposition == "pending":
            gaps.append(f"章节待完成：{sid}")
            continue
        if not isinstance(item.get("guide_heading"), str) or not item["guide_heading"].strip():
            raise InvalidManifest(f"{sid} 缺导读承接标题")
        if headings is not None and item["guide_heading"].strip() not in headings:
            gaps.append(f"导读未找到承接标题：{sid} → {item['guide_heading']}")
        if not item["processed"] or not item["checked"]:
            gaps.append(f"章节未处理/核对：{sid}")
        else:
            taught_count += 1
    if not body_count:
        gaps.append("目录没有摘要或主体章节")
    for asset in assets:
        aid = asset["id"]
        if not isinstance(asset.get("kind"), str) or asset["kind"] not in {"figure", "table", "formula"}:
            raise InvalidManifest(f"未知资产 kind：{aid}")
        if not isinstance(asset.get("required"), bool) or not isinstance(asset.get("checked"), bool):
            raise InvalidManifest(f"{aid} required/checked 必须是布尔值")
        basis = asset.get("basis")
        if not isinstance(basis, str) or basis not in {"text", "visual", "caption-only", "unavailable"}:
            raise InvalidManifest(f"未知资产 basis：{aid}")
        reliable = basis == "visual" if asset["kind"] == "figure" else basis in {"text", "visual"}
        if asset["checked"] and not reliable:
            raise InvalidManifest(f"{aid} 的获取依据不足以记为已核对")
        if asset["required"] and not asset["checked"]:
            gaps.append(f"必要资产待核：{aid}")
        if not asset["required"] and not asset["checked"] and (
            not isinstance(asset.get("reason"), str) or not asset["reason"].strip()
        ):
            gaps.append(f"非必要未核资产缺少取舍理由：{aid}")
    return {"coverage_ready": not gaps, "gaps": gaps,
            "sections_in_outline": len(original), "sections_taught_checked": taught_count,
            "assets_declared": len(assets),
            "source_id": identity, "guide_headings_checked": guide_text is not None,
            "verification_scope": "仅核目录与登记自洽；不证明清单完整、事实正确、讲解充分或本人已读"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outline-file", required=True)
    parser.add_argument("--coverage-file", required=True)
    parser.add_argument("--guide-file", help="可选 Markdown 导读，核对承接标题是否存在")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--require-ready", action="store_true", help="清单有缺口时退出码 2")
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
        print("清单可进入内容复核" if data["coverage_ready"] else "清单存在缺口：" + "；".join(data["gaps"]))
        print(data["verification_scope"])
    if args.require_ready and not data["coverage_ready"]:
        sys.exit(2)


if __name__ == "__main__":
    if sys.stdout and sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    main()
