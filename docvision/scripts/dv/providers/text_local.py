"""Read a PDF's embedded text with the small core runtime, without OCR."""

from __future__ import annotations

from importlib.metadata import version
from pathlib import Path

from .. import util
from ..base import DocVisionError, Options, RawBlock, RawDoc, RawPage
from ..detect import inspect_input
from .common import assemble_markdown


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
    return RawDoc(markdown=assemble_markdown(pages), pages=pages, provider="text-local",
                  model=model, warnings=warnings), metadata
