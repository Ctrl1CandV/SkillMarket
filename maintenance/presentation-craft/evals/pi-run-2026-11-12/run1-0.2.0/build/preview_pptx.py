"""Approximate raster preview of a PPTX, drawn from the file's own geometry.

Not an Office/LibreOffice render. It reads shapes, text, tables and pictures
from the PPTX with python-pptx and paints them with Pillow, measuring text with
the same font files (Noto Sans SC) so overflow/overlap can be inspected.
Differences from PowerPoint: font substitution, kerning, autofit and exact
line breaking.
"""
import io
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont
from pptx import Presentation
from pptx.util import Emu
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE_TYPE

HERE = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.dirname(HERE)
FONTS = os.path.join(TASK, ".work", "fonts")
REG = os.path.join(FONTS, "NotoSansSC-Regular.otf")
BOLD = os.path.join(FONTS, "NotoSansSC-Bold.otf")

EMU_PER_IN = 914400
SCALE = 2.0  # px per pt-ish: we render at 2x of 96dpi


def px(emu):
    return emu / EMU_PER_IN * 96.0 * SCALE


def pt_px(pt):
    return pt * 96.0 / 72.0 * SCALE


_font_cache = {}


def font(size_pt, bold=False):
    key = (round(size_pt, 1), bold)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(BOLD if bold else REG,
                                              int(round(pt_px(size_pt))))
    return _font_cache[key]


def color_of(fmt, default=None):
    try:
        if fmt.type is None:
            return default
        rgb = fmt.fore_color.rgb
        return "#" + str(rgb)
    except Exception:
        return default


def shape_color(shape):
    """Return (fill_hex, line_hex, line_w_pt, dash) for an autoshape."""
    fill = None
    try:
        if shape.fill.type is not None:
            fill = color_of(shape.fill, None)
    except Exception:
        fill = None
    line = None
    lw = 1.0
    try:
        if shape.line.fill.type is not None:
            line = color_of(shape.line, None)
            lw = (shape.line.width or 12700) / 12700.0
    except Exception:
        pass
    return fill, line, lw


def wrap_runs(runs, max_w, draw):
    """runs: list of (text, font, color, size). Returns list of lines of tokens."""
    tokens = []
    for text, ft, col, size in runs:
        buf = ""
        for ch in text:
            is_cjk = ord(ch) > 0x2E7F
            if ch == "\n":
                if buf:
                    tokens.append((buf, ft, col, size))
                    buf = ""
                tokens.append(("\n", ft, col, size))
                continue
            if is_cjk or ch == " ":
                if buf:
                    tokens.append((buf, ft, col, size))
                    buf = ""
                tokens.append((ch, ft, col, size))
            else:
                buf += ch
        if buf:
            tokens.append((buf, ft, col, size))

    lines, cur, cur_w = [], [], 0.0
    for tok in tokens:
        text, ft, col, size = tok
        if text == "\n":
            lines.append(cur)
            cur, cur_w = [], 0.0
            continue
        w = draw.textlength(text, font=ft)
        if text == " " and cur_w == 0:
            continue
        if cur_w + w > max_w and cur:
            if text == " ":
                lines.append(cur)
                cur, cur_w = [], 0.0
                continue
            lines.append(cur)
            cur, cur_w = [], 0.0
        cur.append((text, ft, col, w))
        cur_w += w
    lines.append(cur)
    return lines


def draw_text_frame(img, draw, tf, x, y, w, h, shape=None, anchor=None):
    paras = []
    max_size = 0
    for p in tf.paragraphs:
        runs = []
        align = p.alignment
        ls = p.line_spacing or 1.0
        space_before = (p.space_before.pt if p.space_before is not None else 0)
        space_after = (p.space_after.pt if p.space_after is not None else 0)
        for r in p.runs:
            size = r.font.size.pt if r.font.size else 18
            max_size = max(max_size, size)
            bold = bool(r.font.bold)
            col = "#" + str(r.font.color.rgb) if (r.font.color and r.font.color.type
                                                 is not None) else "#000000"
            runs.append((r.text, font(size, bold), col, size))
        if runs:
            paras.append((runs, align, ls, space_before, space_after))

    if not paras:
        return
    if anchor is None:
        anchor = tf.vertical_anchor
    mx_l = px(tf.margin_left or 0)
    mx_r = px(tf.margin_right or 0)
    my_t = px(tf.margin_top or 0)
    my_b = px(tf.margin_bottom or 0)
    avail_w = max(w - mx_l - mx_r, 10)

    laid = []
    total_h = 0.0
    for runs, align, ls, sb, sa in paras:
        lines = wrap_runs(runs, avail_w, draw)
        psize = max(r[3] for r in runs)
        lh = pt_px(psize) * 1.22 * ls
        laid.append((lines, align, lh, pt_px(sb), pt_px(sa), psize))
        total_h += pt_px(sb) + lh * len(lines) + pt_px(sa)

    if anchor == MSO_ANCHOR.MIDDLE:
        ty = y + my_t + (h - my_t - my_b - total_h) / 2
    elif anchor == MSO_ANCHOR.BOTTOM:
        ty = y + h - my_b - total_h
    else:
        ty = y + my_t

    for lines, align, lh, sb, sa, psize in laid:
        ty += sb
        for line in lines:
            line_w = sum(t[3] for t in line)
            if align == PP_ALIGN.RIGHT:
                tx = x + w - mx_r - line_w
            elif align == PP_ALIGN.CENTER:
                tx = x + mx_l + (avail_w - line_w) / 2
            else:
                tx = x + mx_l
            for text, ft, col, tw in line:
                draw.text((tx, ty + lh * 0.08), text, font=ft, fill=col)
                tx += tw
            ty += lh
        ty += sa
    return total_h


def render_table(img, draw, tbl, x, y):
    ys = y
    for r, row in enumerate(tbl.rows):
        rh = px(row.height)
        xs = x
        for c, cell in enumerate(row.cells):
            cw = px(tbl.columns[c].width)
            fill = color_of(cell.fill, None)
            if fill:
                draw.rectangle([xs, ys, xs + cw, ys + rh], fill=fill)
            # borders from xml
            tcPr = cell._tc.find(
                "{http://schemas.openxmlformats.org/drawingml/2006/main}tcPr")
            if tcPr is not None:
                for tag, coords in (("lnB", ((xs, ys + rh), (xs + cw, ys + rh))),
                                    ("lnT", ((xs, ys), (xs + cw, ys))),
                                    ("lnL", ((xs, ys), (xs, ys + rh))),
                                    ("lnR", ((xs + cw, ys), (xs + cw, ys + rh)))):
                    el = tcPr.find(
                        "{http://schemas.openxmlformats.org/drawingml/2006/main}" + tag)
                    if el is None:
                        continue
                    if el.find("{http://schemas.openxmlformats.org/drawingml/2006/main}noFill") is not None:
                        continue
                    clr = el.find(
                        "{http://schemas.openxmlformats.org/drawingml/2006/main}solidFill/"
                        "{http://schemas.openxmlformats.org/drawingml/2006/main}srgbClr")
                    if clr is not None:
                        wpt = int(el.get("w", "12700")) / 12700.0
                        draw.line(coords, fill="#" + clr.get("val"),
                                  width=max(1, int(pt_px(wpt))))
            draw_text_frame(img, draw, cell.text_frame, xs, ys, cw, rh,
                            anchor=MSO_ANCHOR.MIDDLE)
            xs += cw
        ys += rh
    return ys - y


def render(path, outdir):
    prs = Presentation(path)
    W = px(prs.slide_width)
    H = px(prs.slide_height)
    os.makedirs(outdir, exist_ok=True)
    pages = []
    for idx, slide in enumerate(prs.slides, start=1):
        bg = Image.new("RGB", (int(W), int(H)), "white")
        draw = ImageDraw.Draw(bg)
        for sh in slide.shapes:
            x, y = px(sh.left or 0), px(sh.top or 0)
            w, h = px(sh.width or 0), px(sh.height or 0)
            if sh.shape_type == MSO_SHAPE_TYPE.PICTURE:
                im = Image.open(io.BytesIO(sh.image.blob)).convert("RGBA")
                im = im.resize((max(1, int(w)), max(1, int(h))), Image.LANCZOS)
                bg.paste(im, (int(x), int(y)), im)
                continue
            if sh.has_table:
                render_table(bg, draw, sh.table, x, y)
                continue
            if sh.shape_type == MSO_SHAPE_TYPE.LINE or sh.__class__.__name__ == "Connector":
                col, lw = "#B5CFC4", 1.0
                try:
                    col = color_of(sh.line, col) or col
                    lw = (sh.line.width or 12700) / 12700.0
                except Exception:
                    pass
                draw.line([(x, y), (x + w, y + h)], fill=col,
                          width=max(1, int(pt_px(lw))))
                continue
            if sh.has_text_frame or True:
                fill, line, lw = shape_color(sh)
                if fill and sh.width and sh.height:
                    try:
                        draw.rounded_rectangle([x, y, x + w, y + h],
                                               radius=int(min(w, h) * 0.10) if
                                               sh.adjustments and len(sh.adjustments) else 0,
                                               fill=fill)
                    except Exception:
                        draw.rectangle([x, y, x + w, y + h], fill=fill)
                if line:
                    draw.rectangle([x, y, x + w, y + h], outline=line,
                                   width=max(1, int(pt_px(lw))))
                if sh.has_text_frame and sh.text_frame.text.strip():
                    draw_text_frame(bg, draw, sh.text_frame, x, y, w, h)
        p = os.path.join(outdir, f"slide-{idx:02d}.png")
        bg.save(p)
        pages.append(p)

    # contact sheet
    cols = 3
    rows = (len(pages) + cols - 1) // cols
    tw, th = int(W / 3), int(H / 3)
    sheet = Image.new("RGB", (cols * (tw + 12) + 12, rows * (th + 12) + 12),
                      "#dfe6e3")
    for i, p in enumerate(pages):
        im = Image.open(p).resize((tw, th), Image.LANCZOS)
        r, c = divmod(i, cols)
        sheet.paste(im, (12 + c * (tw + 12), 12 + r * (th + 12)))
    sheet.save(os.path.join(outdir, "contact.png"))
    print(json.dumps({"pages": pages, "contact": os.path.join(outdir, "contact.png")},
                     ensure_ascii=False))


if __name__ == "__main__":
    deck = sys.argv[1]
    outdir = sys.argv[2]
    render(deck, outdir)
