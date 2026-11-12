"""Two backends that share one layout API.

- PptxCanvas  -> real, editable PPTX (python-pptx)
- PreviewCanvas -> approximate PNG render of the same primitives (Pillow + Noto Sans SC)

The preview is a layout approximation, NOT a PowerPoint/LibreOffice export: it uses the
same geometry and a metric-compatible CJK font, so it catches overflow, overlap and
column-width problems, but it cannot prove how PowerPoint will typeset the file.
"""
from __future__ import annotations

import os
from typing import Iterable, Sequence

from PIL import Image, ImageDraw, ImageFont
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt
from pptx.oxml.xmlchemy import OxmlElement

CJK_FONT = "Microsoft YaHei"
LATIN_FONT = "Arial"

# layout grid (inches), 13.333 x 7.5
SW, SH = 13.333, 7.5
ML, MR = 0.62, 0.62
CW = SW - ML - MR
TITLE_Y = 0.44
BODY_TOP = 1.62
FOOT_Y = 7.03

ALIGN = {"l": PP_ALIGN.LEFT, "c": PP_ALIGN.CENTER, "r": PP_ALIGN.RIGHT}
ANCHOR = {"t": MSO_ANCHOR.TOP, "m": MSO_ANCHOR.MIDDLE, "b": MSO_ANCHOR.BOTTOM}


def _set_fonts(run, bold=False, size=18, color="183C36", italic=False):
    f = run.font
    f.size = Pt(size)
    f.bold = bold
    f.italic = italic
    f.name = LATIN_FONT
    f.color.rgb = RGBColor.from_string(color)
    rPr = f._rPr
    ea = rPr.find(qn("a:ea"))
    if ea is None:
        ea = OxmlElement("a:ea")
        rPr.insert_element_before(
            ea, "a:cs", "a:sym", "a:hlinkClick", "a:hlinkMouseOver", "a:rtl", "a:extLst"
        )
    ea.set("typeface", CJK_FONT)
    cs = OxmlElement("a:cs")
    cs.set("typeface", LATIN_FONT)  # keep digits/math latin


class PptxCanvas:
    def __init__(self):
        self.prs = Presentation()
        self.prs.slide_width = Inches(SW)
        self.prs.slide_height = Inches(SH)
        self.slide = None
        self.notes = ""

    # --- pages -----------------------------------------------------------
    def new_slide(self, bg="F6FAF8"):
        self.slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        r = self.rect(0, 0, SW, SH, bg, name="bg")
        return self.slide

    def set_notes(self, text: str):
        self.notes = text
        self.slide.notes_slide.notes_text_frame.text = text

    # --- primitives ------------------------------------------------------
    def rect(self, x, y, w, h, fill=None, line=None, lw=1.0, radius=0.0,
             dash=None, name=None):
        shape_type = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
        sp = self.slide.shapes.add_shape(shape_type, Inches(x), Inches(y), Inches(w), Inches(h))
        if radius:
            sp.adjustments[0] = min(0.5, radius / min(w, h))
        if fill:
            sp.fill.solid()
            sp.fill.fore_color.rgb = RGBColor.from_string(fill)
        else:
            sp.fill.background()
        if line:
            sp.line.color.rgb = RGBColor.from_string(line)
            sp.line.width = Pt(lw)
            if dash:
                from pptx.enum.dml import MSO_LINE_DASH_STYLE
                sp.line.dash_style = MSO_LINE_DASH_STYLE.DASH
        else:
            sp.line.fill.background()
        sp.shadow.inherit = False
        if name:
            sp.name = name
        return sp

    def line(self, x1, y1, x2, y2, color="B5CFC4", w=1.0, dash=False):
        sp = self.slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(min(x1, x2)),
                                        Inches(min(y1, y2)), Inches(max(abs(x2 - x1), 0.008)),
                                        Inches(max(abs(y2 - y1), 0.008)))
        sp.fill.solid()
        sp.fill.fore_color.rgb = RGBColor.from_string(color)
        sp.line.fill.background()
        sp.shadow.inherit = False
        return sp

    def polyline(self, pts: Sequence[tuple[float, float]], color="166B5B", w=2.0):
        if len(pts) < 2:
            return None
        U = 1000  # local units per inch
        start = (int(round(pts[0][0] * U)), int(round(pts[0][1] * U)))
        b = self.slide.shapes.build_freeform(start[0], start[1], scale=(Inches(1).emu / U, Inches(1).emu / U))
        b.add_line_segments([(int(round(p[0] * U)), int(round(p[1] * U))) for p in pts[1:]], close=False)
        sp = b.convert_to_shape()
        sp.fill.background()
        sp.line.color.rgb = RGBColor.from_string(color)
        sp.line.width = Pt(w)
        sp.shadow.inherit = False
        return sp

    def oval(self, cx, cy, r, fill="166B5B", line=None, lw=1.0):
        sp = self.slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(cx - r), Inches(cy - r),
                                         Inches(2 * r), Inches(2 * r))
        sp.fill.solid()
        sp.fill.fore_color.rgb = RGBColor.from_string(fill)
        if line:
            sp.line.color.rgb = RGBColor.from_string(line)
            sp.line.width = Pt(lw)
        else:
            sp.line.fill.background()
        sp.shadow.inherit = False
        return sp

    def text(self, x, y, w, h, s, size=18, bold=False, color="183C36", align="l",
             anchor="t", italic=False, leading=1.0, space_after=0, name=None):
        tb = self.slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        tf.vertical_anchor = ANCHOR[anchor]
        lines = s.split("\n")
        for i, ln in enumerate(lines):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.alignment = ALIGN[align]
            p.line_spacing = leading
            if space_after:
                p.space_after = Pt(space_after)
            run = p.add_run()
            run.text = ln
            _set_fonts(run, bold=bold, size=size, color=color, italic=italic)
        if name:
            tb.name = name
        return tb

    def table(self, x, y, col_w, rows, row_h, header_rows=1, size=16, header_size=15,
              aligns=None, header_fill="E8F1EC", rule="B5CFC4", text_color="183C36",
              header_color="183C36", cell_fills=None, bold_cells=(), name=None,
              first_col_color=None, spans=()):
        nrows, ncols = len(rows), len(col_w)
        covered = {(r, c0 + k) for (r, c0, n) in spans for k in range(1, n)}
        total_w = sum(col_w)
        gt = self.slide.shapes.add_table(nrows, ncols, Inches(x), Inches(y),
                                         Inches(total_w), Inches(sum(row_h)))
        tbl = gt.table
        # kill default banding/first-row styling
        tblPr = tbl._tbl.tblPr
        tblPr.set("bandRow", "0")
        tblPr.set("firstRow", "0")
        for sid in tblPr.findall(qn("a:tableStyleId")):
            tblPr.remove(sid)
        for j, wd in enumerate(col_w):
            tbl.columns[j].width = Inches(wd)
        for i, hh in enumerate(row_h):
            tbl.rows[i].height = Inches(hh)
        for (r, c0, n) in spans:
            if n > 1:
                tbl.cell(r, c0).merge(tbl.cell(r, c0 + n - 1))
        for i, row in enumerate(rows):
            for j, val in enumerate(row):
                if (i, j) in covered:
                    continue
                cell = tbl.cell(i, j)
                cell.margin_left = Inches(0.06)
                cell.margin_right = Inches(0.06)
                cell.margin_top = Inches(0.02)
                cell.margin_bottom = Inches(0.02)
                cell.vertical_anchor = MSO_ANCHOR.MIDDLE
                cell.fill.solid()
                fill = None
                if cell_fills and (i, j) in cell_fills:
                    fill = cell_fills[(i, j)]
                elif i < header_rows:
                    fill = header_fill
                if fill:
                    cell.fill.fore_color.rgb = RGBColor.from_string(fill)
                else:
                    cell.fill.background()
                tf = cell.text_frame
                tf.word_wrap = True
                p = tf.paragraphs[0]
                al = "l"
                if aligns:
                    al = aligns[j]
                p.alignment = ALIGN[al]
                run = p.add_run()
                run.text = str(val)
                bold = (i < header_rows) or ((i, j) in bold_cells)
                size_i = header_size if i < header_rows else size
                col = header_color if i < header_rows else text_color
                if first_col_color and j == 0 and i >= header_rows:
                    col = first_col_color
                _set_fonts(run, bold=bold, size=size_i, color=col)
        # hairline rules drawn as separate shapes (no cell borders in the XML)
        gy = y
        for i in range(header_rows):
            gy += row_h[i]
        self.rect(x, gy - 0.012, total_w, 0.012, rule)
        if name:
            gt.name = name
        return gt

    def save(self, path):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self.prs.save(path)


# ---------------------------------------------------------------- preview
PX = 140  # pixels per inch


def _is_cjk(ch: str) -> bool:
    o = ord(ch)
    return (
        0x3000 <= o <= 0x9FFF or 0xFF00 <= o <= 0xFF65 or 0x2000 <= o <= 0x206F
        or ch in "、。，；：？！（）【】《》“”‘’—…"
    )


class PreviewCanvas:
    def __init__(self, font_dir):
        self.img = None
        self.draw = None
        self.font_dir = font_dir
        self._cache = {}
        self.page_no = 0

    def font(self, size_pt, bold):
        key = (round(size_pt, 1), bold)
        if key not in self._cache:
            name = "NotoSansSC-Bold.otf" if bold else "NotoSansSC-Regular.otf"
            px = int(round(size_pt * PX / 72))
            self._cache[key] = ImageFont.truetype(os.path.join(self.font_dir, name), px)
        return self._cache[key]

    def new_slide(self, bg="F6FAF8"):
        self.page_no += 1
        self.img = Image.new("RGB", (int(SW * PX), int(SH * PX)), "#" + bg)
        self.draw = ImageDraw.Draw(self.img)

    def set_notes(self, text):
        pass

    def rect(self, x, y, w, h, fill=None, line=None, lw=1.0, radius=0.0, dash=None, name=None):
        box = [x * PX, y * PX, (x + w) * PX - 1, (y + h) * PX - 1]
        r = min(radius, w / 2, h / 2) * PX
        if fill or line:
            self.draw.rounded_rectangle(box, radius=r, fill="#" + fill if fill else None,
                                        outline="#" + line if line else None,
                                        width=max(1, int(round(lw))))

    def line(self, x1, y1, x2, y2, color="B5CFC4", w=1.0, dash=False):
        self.draw.rectangle([min(x1, x2) * PX, min(y1, y2) * PX,
                             max(x1, x2) * PX, max(y1, y2) * PX], fill="#" + color)

    def polyline(self, pts, color="166B5B", w=2.0):
        self.draw.line([(p[0] * PX, p[1] * PX) for p in pts], fill="#" + color,
                       width=max(1, int(round(w * PX / 72))), joint="curve")

    def oval(self, cx, cy, r, fill="166B5B", line=None, lw=1.0):
        self.draw.ellipse([(cx - r) * PX, (cy - r) * PX, (cx + r) * PX, (cy + r) * PX],
                          fill="#" + fill, outline=("#" + line) if line else None,
                          width=max(1, int(round(lw))))

    def _tokens(self, s):
        toks, buf = [], ""
        for ch in s:
            if _is_cjk(ch) or ch == " ":
                if buf:
                    toks.append(buf)
                    buf = ""
                toks.append(ch)
            elif ch in "-/":
                buf += ch
            else:
                buf += ch
        if buf:
            toks.append(buf)
        return toks

    def _wrap(self, s, font, max_w):
        lines = []
        for para in s.split("\n"):
            cur = ""
            for tok in self._tokens(para):
                trial = cur + tok
                if self.draw.textlength(trial, font=font) <= max_w or not cur:
                    cur = trial
                else:
                    if tok == " ":
                        lines.append(cur)
                        cur = ""
                    else:
                        lines.append(cur)
                        cur = tok if tok != " " else ""
            lines.append(cur)
        return lines

    def text(self, x, y, w, h, s, size=18, bold=False, color="183C36", align="l",
             anchor="t", italic=False, leading=1.0, space_after=0, name=None):
        f = self.font(size, bold)
        max_w = w * PX * 0.99
        lines = self._wrap(s, f, max_w)
        lh = size * PX / 72 * 1.33 * leading
        total = lh * len(lines) + space_after * (len(lines) - 1) * PX / 72
        if anchor == "t":
            ty = y * PX
        elif anchor == "m":
            ty = y * PX + (h * PX - total) / 2
        else:
            ty = y * PX + h * PX - total
        for ln in lines:
            lw = self.draw.textlength(ln, font=f)
            tx = x * PX
            if align == "c":
                tx = x * PX + (w * PX - lw) / 2
            elif align == "r":
                tx = x * PX + w * PX - lw
            self.draw.text((tx, ty), ln, font=f, fill="#" + color)
            ty += lh + space_after * PX / 72

    def table(self, x, y, col_w, rows, row_h, header_rows=1, size=16, header_size=15,
              aligns=None, header_fill="E8F1EC", rule="B5CFC4", text_color="183C36",
              header_color="183C36", cell_fills=None, bold_cells=(), name=None,
              first_col_color=None, spans=()):
        span_at = {(r, c0): n for (r, c0, n) in spans}
        ncols = len(col_w)
        cy = y
        for i, row in enumerate(rows):
            cx = x
            hh = row_h[i]
            j = 0
            while j < ncols:
                n = span_at.get((i, j), 1)
                cw = sum(col_w[j:j + n])
                fill = None
                if cell_fills and (i, j) in cell_fills:
                    fill = cell_fills[(i, j)]
                elif i < header_rows:
                    fill = header_fill
                if fill:
                    self.rect(cx, cy, cw, hh, fill)
                if (i, j) not in {c for (r, c0, k) in spans for c in range(c0 + 1, c0 + k)}:
                    bold = (i < header_rows) or ((i, j) in bold_cells)
                    col = header_color if i < header_rows else text_color
                    if first_col_color and j == 0 and i >= header_rows:
                        col = first_col_color
                    al = aligns[j] if aligns else "l"
                    self.text(cx + 0.06, cy, cw - 0.12, hh, str(row[j]),
                              size=header_size if i < header_rows else size,
                              bold=bold, color=col, align=al, anchor="m")
                j += n
                cx += cw
            cy += hh

    def save(self, path):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self.img.save(path)
