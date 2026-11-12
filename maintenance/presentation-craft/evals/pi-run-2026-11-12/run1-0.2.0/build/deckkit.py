"""Small native-PPTX toolkit: theme constants, text, rules, tables, arrows."""
import os
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn
import copy

# ---------------------------------------------------------------- theme
BG      = "F6FAF8"
INK     = "183C36"
MUTED   = "4B665F"
ACCENT  = "166B5B"
SECOND  = "657B72"
SURFACE = "E8F1EC"
RULE    = "B5CFC4"
PALE    = "CBDCD5"

CJK = "Microsoft YaHei"
LAT = "Arial"

W, H = 13.333, 7.5
LEFT = 0.72
RIGHT = W - 0.72
CW = RIGHT - LEFT


def rgb(h):
    return RGBColor.from_string(h)


# ---------------------------------------------------------------- text
def _apply_run(run, txt, size, color, bold=False, italic=False, font_cjk=CJK, font_lat=LAT):
    run.text = txt
    f = run.font
    f.size = Pt(size)
    f.bold = bold
    f.italic = italic
    f.name = font_lat
    f.color.rgb = rgb(color)
    # east-asian + complex-script fonts
    rPr = run._r.get_or_add_rPr()
    for tag in ("a:ea", "a:cs"):
        el = rPr.find(qn(tag))
        if el is None:
            el = rPr.makeelement(qn(tag), {})
            rPr.append(el)
        el.set("typeface", font_cjk)


def add_text(slide, x, y, w, h, paras, size=22, color=INK, bold=False,
             line=1.22, space_after=6, align=PP_ALIGN.LEFT,
             anchor=MSO_ANCHOR.TOP, margins=(0, 0, 0, 0), autosize_off=True):
    """paras: str | list of (dict|str).

    dict keys: runs=[(text, {overrides})] | t=..., size, bold, color,
               space_before, space_after, line, align
    """
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(margins[0])
    tf.margin_right = Inches(margins[1])
    tf.margin_top = Inches(margins[2])
    tf.margin_bottom = Inches(margins[3])
    tf.vertical_anchor = anchor
    if autosize_off:
        tf.auto_size = None

    if isinstance(paras, str):
        paras = [paras]

    for i, p in enumerate(paras):
        if isinstance(p, str):
            p = {"t": p}
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para.alignment = p.get("align", align)
        para.line_spacing = p.get("line", line)
        para.space_before = Pt(p.get("space_before", 0))
        para.space_after = Pt(p.get("space_after", space_after))
        psize = p.get("size", size)
        pcolor = p.get("color", color)
        pbold = p.get("bold", bold)
        runs = p.get("runs")
        if runs is None:
            runs = [(p.get("t", ""), {})]
        for txt, ov in runs:
            r = para.add_run()
            _apply_run(r, txt, ov.get("size", psize), ov.get("color", pcolor),
                       ov.get("bold", pbold), ov.get("italic", False))
        if p.get("space_line_after"):
            pass
    return box


def add_rect(slide, x, y, w, h, fill=None, line=None, lw=0.9, radius=None,
             dash=None, shape=None):
    if shape is None:
        shape = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
    s = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    if radius:
        try:
            s.adjustments[0] = radius
        except Exception:
            pass
    if fill:
        s.fill.solid()
        s.fill.fore_color.rgb = rgb(fill)
    else:
        s.fill.background()
    if line:
        s.line.color.rgb = rgb(line)
        s.line.width = Pt(lw)
        if dash:
            s.line.dash_style = dash
    else:
        s.line.fill.background()
    s.shadow.inherit = False
    tf = s.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.08)
    tf.margin_top = tf.margin_bottom = Inches(0.04)
    return s


def box_text(shape, text, size=15, color=INK, bold=False, align=PP_ALIGN.CENTER,
             anchor=MSO_ANCHOR.MIDDLE, line=1.05):
    tf = shape.text_frame
    tf.vertical_anchor = anchor
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para.alignment = align
        para.line_spacing = line
        para.space_before = Pt(0)
        para.space_after = Pt(0)
        r = para.add_run()
        _apply_run(r, ln, size, color, bold)


def add_line(slide, x1, y1, x2, y2, color=RULE, lw=1.0, dash=None):
    from pptx.util import Inches as I
    conn = slide.shapes.add_connector(1, I(x1), I(y1), I(x2), I(y2))
    conn.line.color.rgb = rgb(color)
    conn.line.width = Pt(lw)
    if dash:
        conn.line.dash_style = dash
    return conn


def add_arrow(slide, x1, y1, x2, y2, color=SECOND, lw=1.4):
    conn = add_line(slide, x1, y1, x2, y2, color=color, lw=lw)
    ln = conn.line._get_or_add_ln()
    tail = ln.makeelement(qn("a:tailEnd"), {"type": "triangle", "w": "med", "len": "med"})
    ln.append(tail)
    return conn


# ---------------------------------------------------------------- tables
_ORDER = ["a:lnL", "a:lnR", "a:lnT", "a:lnB", "a:lnTlToBr", "a:lnBlToTr",
          "a:cell3D", "a:noFill", "a:solidFill", "a:gradFill", "a:blipFill",
          "a:pattFill", "a:grpFill", "a:headers", "a:extLst"]


def cell_border(cell, edge="B", color=RULE, lw=0.75, none=False):
    tag = {"L": "a:lnL", "R": "a:lnR", "T": "a:lnT", "B": "a:lnB"}[edge]
    tcPr = cell._tc.get_or_add_tcPr()
    for old in tcPr.findall(qn(tag)):
        tcPr.remove(old)
    ln = tcPr.makeelement(qn(tag), {"w": str(int(lw * 12700)), "cap": "flat",
                                    "cmpd": "sng", "algn": "ctr"})
    if none:
        ln.append(ln.makeelement(qn("a:noFill"), {}))
    else:
        fill = ln.makeelement(qn("a:solidFill"), {})
        clr = fill.makeelement(qn("a:srgbClr"), {"val": color})
        fill.append(clr)
        ln.append(fill)
    idx = _ORDER.index(tag)
    successors = _ORDER[idx + 1:]
    inserted = False
    for child in list(tcPr):
        ctag = child.tag.split("}")[-1]
        if ("a:" + ctag) in successors:
            child.addprevious(ln)
            inserted = True
            break
    if not inserted:
        tcPr.append(ln)


def cell_fill(cell, color):
    if color is None:
        cell.fill.background()
    else:
        cell.fill.solid()
        cell.fill.fore_color.rgb = rgb(color)


def add_table(slide, x, y, col_w, row_h, rows, font=17, header_font=None,
              header_fill=None, aligns=None, header=True, color=INK,
              row_fills=None, bold_rows=(), muted_rows=(),
              margins=(0.1, 0.1, 0.05, 0.05), valign=MSO_ANCHOR.MIDDLE,
              line=1.0):
    """rows: list of list of str (or dict {t, bold, color, align})."""
    nrows, ncols = len(rows), len(rows[0])
    width = Inches(sum(col_w))
    height = Inches(sum(row_h))
    gf = slide.shapes.add_table(nrows, ncols, Inches(x), Inches(y), width, height)
    tbl = gf.table
    # strip the built-in table style -> "No Style, No Grid"
    tblPr = tbl._tbl.tblPr
    for sid in tblPr.findall(qn("a:tableStyleId")):
        tblPr.remove(sid)
    sid = tblPr.makeelement(qn("a:tableStyleId"), {})
    sid.text = "{2D5ABB26-0587-4C30-8999-92F81FD0307C}"
    tblPr.append(sid)
    tbl.first_row = False
    tbl.horz_banding = False

    for i, cw in enumerate(col_w):
        tbl.columns[i].width = Inches(cw)
    for r, rh in enumerate(row_h):
        tbl.rows[r].height = Inches(rh)

    header_font = header_font or font
    for r, row in enumerate(rows):
        is_header = header and r == 0
        for c, val in enumerate(row):
            cell = tbl.cell(r, c)
            if isinstance(val, dict):
                txt = val.get("t", "")
                cbold = val.get("bold", is_header or (r in bold_rows))
                ccolor = val.get("color", MUTED if r in muted_rows else color)
                calign = val.get("align")
            else:
                txt = val
                cbold = is_header or (r in bold_rows)
                ccolor = MUTED if r in muted_rows else color
                calign = None
            fill = header_fill if is_header else (row_fills or {}).get(r)
            cell_fill(cell, fill if (fill or is_header) else None)
            cell.margin_left = Inches(margins[0])
            cell.margin_right = Inches(margins[1])
            cell.margin_top = Inches(margins[2])
            cell.margin_bottom = Inches(margins[3])
            cell.vertical_anchor = valign
            tf = cell.text_frame
            tf.word_wrap = True
            para = tf.paragraphs[0]
            if calign is None:
                if aligns:
                    calign = aligns[c]
                else:
                    calign = PP_ALIGN.LEFT
            para.alignment = calign
            para.line_spacing = line
            para.space_before = Pt(0)
            para.space_after = Pt(0)
            for k, seg in enumerate(str(txt).split("\n")):
                p2 = para if k == 0 else tf.add_paragraph()
                p2.alignment = para.alignment
                p2.line_spacing = line
                p2.space_before = Pt(0)
                p2.space_after = Pt(0)
                run = p2.add_run()
                _apply_run(run, seg, header_font if is_header else font,
                           ccolor, cbold)
    return gf


def table_rules(gf, rows, col_w, row_h, y, x, rules=(), color=RULE, lw=0.75):
    """Kept for reference; borders are applied via cell_border on cells."""
    pass


# ------------------------------------------------------- text measurement
_FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "..", ".work", "fonts")
_measure_cache = {}


def _pil_font(size_pt, bold=False):
    from PIL import ImageFont
    name = "NotoSansSC-Bold.otf" if bold else "NotoSansSC-Regular.otf"
    key = (name, round(size_pt * 10))
    if key not in _measure_cache:
        _measure_cache[key] = ImageFont.truetype(
            os.path.join(_FONT_DIR, name), int(round(size_pt * 10)))
    return _measure_cache[key]


def text_width_in(txt, size_pt, bold=False):
    """Approximate rendered width in inches (Noto Sans SC metrics)."""
    f = _pil_font(size_pt, bold)
    return f.getlength(txt) / 10.0 / 72.0


def count_lines(txt, size_pt, width_in, bold=False):
    """Greedy char wrap count, close to PowerPoint's for CJK-heavy text."""
    if not txt:
        return 0
    lines, cur = 1, 0.0
    for ch in txt:
        w = text_width_in(ch, size_pt, bold)
        if cur + w > width_in and cur > 0:
            lines += 1
            cur = 0.0 if ch == " " else w
        else:
            cur += w
    return lines
