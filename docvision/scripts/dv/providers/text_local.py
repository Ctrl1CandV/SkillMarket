"""Read a PDF's embedded text with the small core runtime, without OCR."""

from __future__ import annotations

from importlib.metadata import version
from pathlib import Path

from .. import util
from ..base import DocVisionError, Options, RawBlock, RawDoc, RawPage
from ..detect import inspect_input
from .common import assemble_markdown


def invisible_text_pages(source: str, indices: list[int], *, min_chars: int = 40,
                         min_share: float = 0.03) -> list[tuple[int, int, int]]:
    """Pages whose text layer holds many characters that leave no ink when rendered.

    Only pages with text inside form XObjects (figures) are rendered, at 72 dpi in grayscale.
    A character counts as invisible when no pixel in its box is darker than near-white, so light
    or white text on a dark figure still counts as visible. Returns (page, invisible, total).
    """
    try:
        import pypdfium2 as pdfium
        import pypdfium2.raw as pdfium_raw
    except ImportError:
        return []
    found = []
    try:
        document = pdfium.PdfDocument(source)
    except Exception:
        return []
    try:
        for index in indices:
            page = document[index]
            if not any(obj.type == pdfium_raw.FPDF_PAGEOBJ_TEXT and obj.level > 0
                       for obj in page.get_objects(max_depth=8)):
                continue
            _, height = page.get_size()
            image = page.render(scale=1.0, grayscale=True).to_pil()
            pixels, (columns, rows) = image.load(), image.size
            textpage = page.get_textpage()
            total = invisible = 0
            for char in range(textpage.count_chars()):
                text = textpage.get_text_range(char, 1)
                if not text.strip() or text in "￾�":
                    continue
                total += 1
                left, bottom, right, top = textpage.get_charbox(char)
                x0, y0 = max(0, int(left)), max(0, int(height - top))
                x1, y1 = min(columns - 1, max(x0, int(right + 0.999))), min(rows - 1, max(y0, int(height - bottom + 0.999)))
                if x0 >= columns or y0 >= rows or x1 < 0 or y1 < 0 or \
                        min(pixels[x, y] for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)) >= 235:
                    invisible += 1
            if total and invisible >= min_chars and invisible / total >= min_share:
                found.append((index + 1, invisible, total))
    except Exception:
        return found  # a best-effort warning must never block reading the text layer
    finally:
        document.close()
    return found


def convert(source: str, opts: Options) -> tuple:
    if util.is_url(source) or util.suffix_of(source) != ".pdf":
        raise DocVisionError("text-local expects a local PDF with an embedded text layer.",
                             hint="For scans/images, use OCR or render pages for visual reading.")
    if opts.mode not in {"auto", "text"}:
        raise DocVisionError("text-local cannot perform OCR or recognize formulas/tables.",
                             hint="Use --mode text, or select an OCR provider for this task.")
    inspect_input(source, opts)
    try:
        from pypdf import PdfReader
        from pypdf.errors import PdfReadError
    except ImportError as exc:
        raise DocVisionError("PDF text-layer reading needs the core pypdf dependency.",
                             hint="Run `docvision setup --profile core --yes`.") from exc
    model = f"pypdf {version('pypdf')} text extraction"
    pages: list[RawPage] = []
    empty: list[int] = []
    warnings = ["Text layer only: reading order, formulas, tables and figures are not visually verified. "
                "Use the original page image for important details; no block coordinates are inferred."]
    try:
        with Path(source).open("rb") as stream:
            reader = PdfReader(stream)
            if reader.is_encrypted and not reader.decrypt(""):
                raise DocVisionError("The PDF requires a password before text can be read.",
                                     hint="Provide a locally decrypted copy, then retry.")
            total = len(reader.pages)
            selected = util.parse_pages(opts.pages, total)
            indices = list(range(total)) if selected is None else selected
            if not indices:
                raise DocVisionError("The selected page range contains no PDF pages.")
            metadata = {"provider": "text-local", "model": model,
                        "pages": [index + 1 for index in indices], "source_pages": total}
            if opts.dry_run:
                return None, metadata
            for index in indices:
                page = reader.pages[index]
                text = (page.extract_text() or "").replace("\r\n", "\n").replace("\r", "\n").strip()
                number = index + 1
                blocks = [RawBlock(type="text", markdown=text, text=text, page=number,
                                   meta={"extraction": "pdf-text-layer"})] if text else []
                pages.append(RawPage(page=number, width=float(page.mediabox.width),
                                     height=float(page.mediabox.height), markdown=text, blocks=blocks))
                if not text:
                    empty.append(number)
    except (PdfReadError, OSError, ValueError) as exc:
        raise DocVisionError(f"Could not extract the PDF text layer: {exc}",
                             hint="Check the PDF, or render the selected pages for visual reading.") from exc
    if len(empty) == len(pages):
        raise DocVisionError("No embedded text was found on the selected pages; this may be a scanned PDF.",
                             hint="Use `docvision pages <file.pdf> --output <page-dir> --pages <range>` "
                                  "and open the page images, or run OCR with --tier standard.")
    if empty:
        warnings.append(f"Pages {empty} have no embedded text and may be scans or blank pages. "
                        "Their page entries are retained; render them or run OCR before treating the reading as complete.")
    hidden = invisible_text_pages(source, indices)
    by_page = {page.page: page for page in pages}
    for number, count, total in hidden:
        for block in by_page[number].blocks:
            block.meta["invisible_chars"] = count  # `read` repeats the warning on this page
    if hidden:
        listed = ", ".join(f"page {page}: about {count} of {total} characters" for page, count, total in hidden)
        warnings.append(f"Text that is not visible on the rendered page was extracted ({listed}). "
                        "Usually an embedded figure is a cropped page from another PDF, and the cropped-away text "
                        "(sometimes a whole draft page or another table) is still in the file. The text of these pages "
                        "mixes in content that is not on the page: quote only what the page image shows, "
                        "or OCR these pages with --tier standard --pages <n>.")
    return RawDoc(markdown=assemble_markdown(pages), pages=pages, provider="text-local",
                  model=model, warnings=warnings), metadata
