"""Prepare fixed artwork and SVG-only crossover copies; never generate evaluation pages."""

from pathlib import Path
import hashlib
import json
import re
import xml.etree.ElementTree as ET


HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "v0.4" / "runs"
SVG_RE = re.compile(rb'<svg\b[^>]*\bid="art-[012]"[^>]*>.*?</svg>', re.S)
STYLE_RE = re.compile(rb"<style\b[^>]*>(.*?)</style>", re.S)
SCRIPT_RE = re.compile(rb"<script\b[^>]*>(.*?)</script>", re.S)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def parse_artwork(page):
    matches = list(SVG_RE.finditer(page))
    assert len(matches) == 3, "Expected exactly three artwork SVGs"
    artworks = [match.group(0) for match in matches]
    assert [re.search(rb'\bid="(art-[012])"', svg).group(1) for svg in artworks] == [
        b"art-0", b"art-1", b"art-2"
    ]
    for svg in artworks:
        # These drawings already use literal colors. Refuse implicit page color dependencies.
        assert not re.search(rb"var\s*\(|currentcolor|\binherit\b|<style\b|\bclass=", svg, re.I)
        assert not re.search(rb"<(?:image|use|script)\b", svg, re.I)
        node = ET.fromstring(svg)
        ids = {element.attrib["id"] for element in node.iter() if "id" in element.attrib}
        assert len(ids) == len([element for element in node.iter() if "id" in element.attrib])
        for ref in re.findall(rb"url\(#([^)]*)\)", svg):
            assert ref.decode() in ids, ref
        assert node.attrib["aria-labelledby"] in ids
    return artworks


def without_art(page):
    return SVG_RE.sub(b"<!-- ARTWORK SVG -->", page)


def main():
    pages = {
        "033": (SOURCE / "baseline" / "exhibition.html").read_bytes(),
        "040": (SOURCE / "candidate" / "exhibition.html").read_bytes(),
    }
    artworks = {version: parse_artwork(page) for version, page in pages.items()}
    assets_dir = HERE / "inputs" / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    provenance = {
        "purpose": "Identical fixed artwork for all new collection-page conditions",
        "source": "../v0.4/runs/baseline/exhibition.html",
        "source_sha256": sha(pages["033"]),
        "color_dependencies": "None: all artwork fills, strokes and gradient stops use literal colors; no CSS variables, currentColor, inherited color or class selectors",
        "normalization": "No color substitutions required; SVG bytes preserved, with one trailing newline added to each standalone file",
        "scope": "Reused artwork is controlled input, not an unseen asset set or new generation",
        "assets": [],
    }
    for index, svg in enumerate(artworks["033"], 1):
        data = svg + b"\n"
        name = f"work-{index:02}.svg"
        (assets_dir / name).write_bytes(data)
        provenance["assets"].append({
            "file": f"inputs/assets/{name}",
            "source_svg_id": f"art-{index - 1}",
            "source_svg_sha256": sha(svg),
            "file_sha256": sha(data),
            "viewBox": ET.fromstring(svg).attrib["viewBox"],
        })
    (HERE / "asset-provenance.json").write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    cross_dir = HERE / "crossed-exhibition"
    cross_dir.mkdir(exist_ok=True)
    manifest = {
        "purpose": "Diagnostic copies of existing outputs; not new skill evaluation generations",
        "sources": {
            "033": {"file": "../../v0.4/runs/baseline/exhibition.html", "sha256": sha(pages["033"])},
            "040": {"file": "../../v0.4/runs/candidate/exhibition.html", "sha256": sha(pages["040"])},
        },
        "copies": [],
    }
    for layout in ("033", "040"):
        for art in ("033", "040"):
            replacements = iter(artworks[art])
            page = SVG_RE.sub(lambda _: next(replacements), pages[layout])
            assert without_art(page) == without_art(pages[layout])
            assert STYLE_RE.findall(page) == STYLE_RE.findall(pages[layout])
            assert SCRIPT_RE.findall(page) == SCRIPT_RE.findall(pages[layout])
            assert parse_artwork(page) == artworks[art]
            if layout == art:
                assert page == pages[layout], "Diagonal controls must be byte-identical"
            # All source DOM ids, SVG ids and label references remain unique and resolvable.
            all_ids = re.findall(rb'\bid="([^"]+)"', page)
            assert len(all_ids) == len(set(all_ids)), "Duplicate DOM id"
            for target in re.findall(rb'aria-labelledby="([^"]+)"', page):
                assert all(item in all_ids for item in target.split())
            name = f"layout-{layout}__art-{art}.html"
            (cross_dir / name).write_bytes(page)
            manifest["copies"].append({
                "file": name,
                "layout_source": layout,
                "art_source": art,
                "sha256": sha(page),
                "unchanged_non_svg_sha256": sha(without_art(page)),
                "style_sha256": [sha(data) for data in STYLE_RE.findall(page)],
                "script_sha256": [sha(data) for data in SCRIPT_RE.findall(page)],
                "source_identical": page == pages[layout],
                "svg_replacements": 0 if layout == art else 3,
                "static_checks": "Exactly three donor artwork SVGs; non-SVG bytes/style/script unchanged; ids and aria-labelledby references valid",
            })
    (cross_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("Prepared 3 fixed SVG assets and 4 diagnostic copies; static invariants passed.")
    print("Original HTML and runtime skills were not modified. No evaluation pages generated.")


if __name__ == "__main__":
    main()
