"""Shared types for docvision providers.

The provider contract is deliberately small: every backend converts one input
into the same RawDoc shape.  Rendering, verification and citation handling live
outside the providers so a new backend only has to solve extraction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class DocVisionError(RuntimeError):
    """A failure that should be shown to the user with an actionable hint."""

    def __init__(self, message: str, *, hint: str | None = None, code: str | None = None):
        super().__init__(message)
        self.hint = hint
        self.code = code


@dataclass
class Options:
    """Conversion options shared by all providers."""

    provider: str = "auto"
    tier: str = "standard"  # fast | standard | quality
    mode: str = "auto"  # auto | text | ocr | formula | table | chart
    pages: str | None = None
    lang: str = "ch"
    device: str = "auto"
    timeout: int = 900
    allow_remote: bool = False
    keep_raw: bool = False
    images: bool = True
    force: bool = False
    resume: bool = False
    dry_run: bool = False
    workers: int = 1
    max_mb: int = 200
    output: Path | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class RawBlock:
    type: str = "text"
    markdown: str = ""
    text: str = ""
    page: int = 1
    bbox: list[float] | None = None  # normalised [x0, y0, x1, y1]
    level: int | None = None
    asset: str | None = None  # relative to the output assets directory
    confidence: float | None = None
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class RawPage:
    page: int
    width: float | None = None
    height: float | None = None
    markdown: str = ""
    blocks: list[RawBlock] = field(default_factory=list)


@dataclass
class RawDoc:
    markdown: str
    pages: list[RawPage] = field(default_factory=list)
    assets: dict[str, bytes] = field(default_factory=dict)
    provider: str = ""
    model: str = ""
    warnings: list[str] = field(default_factory=list)
    usage: dict[str, Any] = field(default_factory=dict)
    raw_files: dict[str, bytes] = field(default_factory=dict)


def block_markdown(block_type: str, text: str, *, level: int | None = None,
                   asset: str | None = None) -> str:
    """Render one block to Markdown without pretending to be a full renderer."""
    t = (text or "").strip()
    if block_type in {"heading", "title"}:
        hashes = "#" * max(1, min(6, int(level or 2)))
        return f"{hashes} {t}".strip()
    if block_type == "table":
        return t
    if block_type == "formula":
        if not t:
            return ""
        if t.startswith("$$") or t.startswith("$"):
            return t
        return f"$$\n{t}\n$$"
    if block_type == "image":
        return f"![image]({asset})" if asset else "![image]()"
    if block_type == "code":
        return f"```\n{t}\n```"
    return t


def make_doc(markdown: str, pages: list[RawPage] | None = None, **kwargs: Any) -> RawDoc:
    return RawDoc(markdown=markdown or "", pages=pages or [], **kwargs)


def guess_extension(name: str) -> str:
    return Path(name).suffix.lower()
