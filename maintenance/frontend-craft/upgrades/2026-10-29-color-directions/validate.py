"""Bounded static validation for the original offline color-studio assets.

Run with Python 3.10+: python validate.py [--root REPO] [--node NODE]
No browser is used. Contrast checks cover the named role pairs used by the
templates; they do not model all CSS inheritance, compositing, or rendered pixels.
"""
from __future__ import annotations

import argparse
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from datetime import datetime, timezone
from urllib.parse import unquote, urlsplit


COLOR_ROLES = set("canvas surface surface-alt text muted border control-border accent on-accent accent-hover accent-active selected selected-text focus brand on-brand brand-muted brand-accent on-brand-accent success success-bg warning warning-bg danger danger-bg".split())
ENTRY_ASSETS = {"index.html", "workbench.html", "editorial.html", "showcase.html", "palettes.css", "studio.css", "templates.css", "palettes.js", "studio.js", "template.js"}


def css_without_comments(value: str) -> str:
    return re.sub(r"/\*.*?\*/", "", value, flags=re.S)


def luminance(value: str) -> float:
    value = value.strip()
    if not re.fullmatch(r"#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?", value):
        raise ValueError(f"Expected an opaque hex color, got {value!r}")
    channels = value[1:]
    if len(channels) == 3:
        channels = "".join(x * 2 for x in channels)
    rgb = [int(channels[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in rgb]
    return sum(x * weight for x, weight in zip(linear, (0.2126, 0.7152, 0.0722)))


def contrast(a: str, b: str) -> float:
    light, dark = sorted((luminance(a), luminance(b)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


class AssetHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids: list[str] = []
        self.refs: list[dict] = []
        self.inline_scripts: list[str] = []
        self._script: list[str] | None = None

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if attrs.get("id"):
            self.ids.append(attrs["id"])
        for attr in ("src", "href", "poster"):
            if attrs.get(attr):
                self.refs.append({"tag": tag, "attribute": attr, "url": attrs[attr],
                                  "navigation": tag == "a" and attr == "href"})
        if attrs.get("srcset"):
            for candidate in attrs["srcset"].split(","):
                self.refs.append({"tag": tag, "attribute": "srcset", "url": candidate.strip().split()[0], "navigation": False})
        if tag == "script" and "src" not in attrs and attrs.get("type", "") not in ("application/json", "application/ld+json"):
            self._script = []

    def handle_data(self, data):
        if self._script is not None:
            self._script.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self._script is not None:
            self.inline_scripts.append("".join(self._script))
            self._script = None


def pair_matrix() -> list[dict]:
    pairs = []
    def add(fg, bg, minimum, use):
        pairs.append({"foreground": fg, "background": bg, "minimum": minimum, "use": use})
    for bg in ("canvas", "surface", "surface-alt"):
        for fg in ("text", "muted", "accent"):
            add(fg, bg, 4.5, "templates.css: body, .muted/.eyebrow/.record-meta, a; .panel/.reading-paper/.article-copy blockquote provide surfaces")
        add("focus", bg, 3, "templates.css :focus-visible with 4px offset, against content surfaces")
    for bg in ("accent", "accent-hover", "accent-active"):
        add("on-accent", bg, 4.5, "templates.css .button / :hover / :active")
    add("selected-text", "selected", 4.5, "templates.css .record[aria-pressed=true] and mark")
    add("focus", "selected", 3, "Selected-control focus combination; same role may be used in gallery preview")
    add("accent", "selected", 3, "templates.css .record[aria-pressed=true] border")
    for fg in ("on-brand", "brand-muted"):
        add(fg, "brand", 4.5, "templates.css .brand-field / .brand-sub / .eyebrow / figcaption")
    add("on-brand-accent", "brand-accent", 4.5, "templates.css .brand-field .button")
    add("brand-accent", "brand", 3, "templates.css .brand-field :focus-visible")
    for kind in ("success", "warning", "danger"):
        add(kind, f"{kind}-bg", 4.5, "templates.css .success / .warning / .danger")
    add("control-border", "surface", 3, "templates.css input/select/textarea and .button.secondary boundary")
    add("danger", "surface", 3, "templates.css input[aria-invalid=true] border and focus outline in detail panel")
    return pairs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[4])
    parser.add_argument("--node", type=Path)
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("static-results.json"))
    args = parser.parse_args()
    root = args.root.resolve()
    studio = root / "frontend-craft/assets/color-studio"
    report = {"checked_at": datetime.now(timezone.utc).isoformat(), "scope": "Static source, local dependencies, JS syntax, opaque role-pair contrast; no browser or rendered-pixel validation", "errors": []}
    errors = report["errors"]
    if not studio.is_dir():
        errors.append("color-studio asset directory is missing")
        report["passed"] = False
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps({"passed": False, "errors": errors}, ensure_ascii=False))
        return 1

    files = sorted(p for p in studio.rglob("*") if p.is_file())
    for missing in sorted(ENTRY_ASSETS - {p.name for p in files if p.parent == studio}):
        errors.append(f"Missing gallery/template dependency: {missing}")
    texts = {p: p.read_text(encoding="utf-8-sig") for p in files if p.suffix in (".html", ".css", ".js")}
    report["files"] = [{"path": p.relative_to(root).as_posix(), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]
    palette_path = studio / "palettes.css"
    palette_css = css_without_comments(texts.get(palette_path, ""))
    palettes = {}
    for match in re.finditer(r'\[data-palette=[\"\']([^\"\']+)[\"\']\]\s*\{([^{}]*)\}', palette_css):
        theme_id, body = match.groups()
        values = dict(re.findall(r"--cs-([\w-]+)\s*:\s*([^;{}]+)", body))
        if theme_id in palettes:
            errors.append(f"Duplicate palette ID: {theme_id}")
        palettes[theme_id] = {key: value.strip() for key, value in values.items()}
        if not re.search(r"color-scheme\s*:\s*(light|dark)\s*;?", body):
            errors.append(f"{theme_id}: missing light/dark color-scheme")
    if not palettes:
        errors.append("No palette blocks parsed")
    used_roles = set()
    for path, source in texts.items():
        if path.suffix in (".html", ".css"):
            used_roles.update(re.findall(r"var\(\s*--cs-([\w-]+)", css_without_comments(source)))
    report["used_roles"] = sorted(used_roles)
    report["palette_contract"] = []
    pairs = pair_matrix()
    report["contrast_pairs"] = pairs
    report["contrast_results"] = []
    for theme_id, values in palettes.items():
        missing = sorted((COLOR_ROLES | used_roles) - set(values))
        report["palette_contract"].append({"id": theme_id, "roles": len(values), "missing": missing})
        if missing:
            errors.append(f"{theme_id}: missing roles {missing}")
        for role in COLOR_ROLES & set(values):
            try:
                luminance(values[role])
            except ValueError as exc:
                errors.append(f"{theme_id}/{role}: {exc}")
        for pair in pairs:
            fg, bg = pair["foreground"], pair["background"]
            if fg not in values or bg not in values:
                continue
            try:
                ratio = contrast(values[fg], values[bg])
            except ValueError:
                continue
            passed = ratio + 1e-9 >= pair["minimum"]
            report["contrast_results"].append({"palette": theme_id, "foreground": fg, "background": bg, "ratio": round(ratio, 4), "minimum": pair["minimum"], "passed": passed})
            if not passed:
                errors.append(f"{theme_id}: {fg} on {bg} = {ratio:.3f}, needs {pair['minimum']}")

    # Gallery cards have independent palettes, but offset outlines are painted on
    # the gallery's neutral canvas. Resolve parent aliases before card inheritance.
    studio_css = css_without_comments(texts.get(studio / "studio.css", ""))
    index_html = texts.get(studio / "index.html", "")
    gallery_root = re.search(r'<html\b[^>]*data-palette=[\"\']([^\"\']+)', index_html)
    gallery_palette = palettes.get(gallery_root.group(1)) if gallery_root else None
    report["gallery_outer_outline_pairs"] = []
    rules = [(selector.strip(), body) for selector, body in re.findall(r"([^{}]+)\{([^{}]*)\}", studio_css)]
    parent_aliases = {}
    if gallery_palette:
        for selector, body in rules:
            if selector == ".studio-page":
                for alias, role in re.findall(r"(--[\w-]+)\s*:\s*var\(\s*--cs-([\w-]+)\s*\)", body):
                    if role in gallery_palette:
                        parent_aliases[alias] = gallery_palette[role]
        for selector in ('.palette-card[aria-pressed="true"]', '.palette-card:focus-visible'):
            bodies = [body for candidate, body in rules if candidate == selector]
            tokens = re.findall(r"(?:^|;)\s*outline(?:-color)?\s*:[^;]*var\(\s*(--[\w-]+)\s*\)", ";".join(bodies))
            if not tokens:
                errors.append(f"Cannot resolve gallery outline role for {selector}; inspect current CSS")
                continue
            token = tokens[-1]
            for theme_id, values in palettes.items():
                foreground = parent_aliases.get(token) if token in parent_aliases else values.get(token.removeprefix("--cs-"))
                if not foreground:
                    errors.append(f"Cannot resolve {token} on {theme_id} gallery card")
                    continue
                ratio = contrast(foreground, gallery_palette["canvas"])
                passed = ratio + 1e-9 >= 3
                report["gallery_outer_outline_pairs"].append({"selector": selector, "card_palette": theme_id, "token": token, "foreground": foreground, "adjacent_canvas": gallery_palette["canvas"], "ratio": round(ratio, 4), "minimum": 3, "passed": passed})
                if not passed:
                    errors.append(f"Gallery {theme_id} {selector}: outline against gallery canvas = {ratio:.3f}, needs 3")
    else:
        errors.append("Cannot resolve gallery root palette for cross-surface outline checks")

    html = {}
    for path, source in texts.items():
        if path.suffix == ".html":
            document = AssetHTML()
            document.feed(source)
            html[path] = document
            if len(document.ids) != len(set(document.ids)):
                errors.append(f"{path.name}: duplicate HTML IDs")
    refs_checked = 0
    navigation = []
    for path, document in html.items():
        for ref in document.refs:
            url = urlsplit(ref["url"])
            if url.scheme or url.netloc:
                if ref["navigation"] and url.scheme in ("http", "https", "mailto"):
                    navigation.append({"file": path.name, "url": ref["url"]})
                elif url.scheme not in ("data", "blob"):
                    errors.append(f"{path.name}: remote or unsupported resource {ref['url']}")
                continue
            dest = (path.parent / unquote(url.path)).resolve() if url.path else path
            refs_checked += 1
            if not dest.is_file():
                errors.append(f"{path.name}: missing local reference {ref['url']}")
            elif url.fragment and dest in html and unquote(url.fragment) not in html[dest].ids:
                errors.append(f"{path.name}: missing fragment {ref['url']}")
    report["local_references_checked"] = refs_checked
    report["external_navigation_only"] = navigation

    css_refs_checked = 0
    for path, source in texts.items():
        if path.suffix == ".css":
            clean = css_without_comments(source)
            if re.search(r"@import\b", clean):
                errors.append(f"{path.name}: CSS @import requires review")
            for ref in re.findall(r"url\(\s*[\"\']?([^\)\"\']+)", clean):
                ref = ref.strip()
                if ref.startswith(("data:", "#")):
                    continue
                css_refs_checked += 1
                url = urlsplit(ref)
                if url.scheme or url.netloc:
                    errors.append(f"{path.name}: remote CSS resource {ref}")
                elif not (path.parent / unquote(url.path)).is_file():
                    errors.append(f"{path.name}: missing CSS resource {ref}")
    report["css_references_checked"] = css_refs_checked

    node_candidates = [args.node, shutil.which("node"), Path(os.environ.get("USERPROFILE", str(Path.home()))) / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe"]
    node = next((str(p) for p in node_candidates if p and Path(p).is_file()), None)
    report["js_syntax"] = []
    metadata = {}
    if node and (studio / "palettes.js").is_file():
        metadata_check = "const fs=require('node:fs'),vm=require('node:vm');const box={window:{}};vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),box,{timeout:1000});process.stdout.write(JSON.stringify({ids:box.window.CraftPalettes.map(p=>p.id),roles:box.window.CraftColorRoles}));"
        result = subprocess.run([node, "-e", metadata_check, str(studio / "palettes.js")], capture_output=True, text=True, encoding="utf-8", errors="replace")
        if result.returncode:
            errors.append("palettes.js metadata could not be evaluated in an isolated empty window")
        else:
            metadata = json.loads(result.stdout)
            if len(metadata["ids"]) != len(set(metadata["ids"])) or set(metadata["ids"]) != set(palettes):
                errors.append("Metadata palette IDs do not exactly match stylesheet recipes")
            for theme_id, values in palettes.items():
                if set(metadata["roles"]) != set(values):
                    errors.append(f"{theme_id}: exported role list differs from actual palette roles")
    report["metadata_contract"] = metadata
    scripts = [(p.name, source, p) for p, source in texts.items() if p.suffix == ".js"]
    scripts.extend((f"{p.name} inline {i + 1}", source, None) for p, doc in html.items() for i, source in enumerate(doc.inline_scripts))
    network_calls = r"\b(?:fetch|XMLHttpRequest|WebSocket|EventSource)\s*\(|\bnavigator\s*\.\s*sendBeacon\s*\(|\bimport\s*\(|\bimport\s+.*?\bfrom\s*[\"\'](?:https?:)?//"
    for name, source, path in scripts:
        if re.search(network_calls, source):
            errors.append(f"{name}: possible network request or dynamic import requires review")
        if not node:
            errors.append(f"{name}: Node runtime not found; syntax not checked")
            continue
        command = [node, "--check", str(path)] if path else [node, "--check"]
        result = subprocess.run(command, input=None if path else source, capture_output=True, text=True, encoding="utf-8", errors="replace")
        report["js_syntax"].append({"file": name, "passed": result.returncode == 0, "diagnostic": (result.stdout + result.stderr).strip()})
        if result.returncode:
            errors.append(f"{name}: JS syntax failed")

    report["limitations"] = ["Role-pair matrix must be reviewed when CSS selectors/backgrounds change; this is not a full CSS cascade or alpha-compositing engine.", "Decorative border, disabled controls, imagery and ornamental swatches are not forced to meet text/control thresholds.", "No browser execution, exports, keyboard interaction, viewport/overflow inspection, font rendering or aesthetic assessment is claimed."]
    report["passed"] = not errors
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "palettes": len(palettes), "pairs_per_palette": len(pairs), "files": len(files), "local_references_checked": refs_checked, "errors": errors, "report": str(args.output)}, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
