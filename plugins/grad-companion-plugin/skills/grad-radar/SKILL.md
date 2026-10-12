---
name: grad-radar
description: Find, select, and read papers and reviews based on the reader's background and learning question. Weigh venue, year, and citation impact by context; provide evidence-grounded information synthesis, complete guides to reviews, close reading of one paper, and daily arXiv discovery for the current topic. By default, support readers with less experience. Accept links, arXiv IDs, or PDFs; provide quick assessments or continued reading. Does not replace systematic literature search.
license: MIT
metadata:
  version: "0.3.0"
---

# grad-radar: Topic-Based Selection, Full Explanations, and Daily Discovery

Choose the workflow based on intent. For a single paper, continue using the existing primary record.

By default, support students and researchers with less reading experience by explaining necessary concepts, mechanisms, and evidence. Adjust depth to the reader's actual background, task, time, and prior reading methods. Always retain source accuracy, important conditions, and the scope of material not read; adjust workflow, length, and comprehension questions as needed.

- **Select papers for a topic:** The user describes a field, technology, or research question → read `references/selection-protocol.md` → state the priority order and hard requirements for this request, verify sources, year, citations, and key paper sections, then recommend a justified primary reading and complementary work. For general recommendations, usually prioritize leading journals/conferences and the past three years. Adapt for foundational or time-sensitive topics. Do not use the daily three-day window.
- **Guide the reader through a full review:** The user asks for a complete summary of a review article → read `references/survey-protocol.md` → cover the full work, expand according to the request, and verify before delivering a guide that can be read directly. Use the section-selection tool for each section in the outline; a short preview does not replace the full text.
- **Read one paper (core workflow):** The user specifies a paper (link/arXiv ID/local PDF) or selects one from a daily brief → follow `references/reading-protocol.md` → produce notes using `references/note-templates.md` → save them with `scripts/reading_record.py`. Keep one primary record and one current main note per paper; record AI organization and the user's reading status separately.
- **Daily discovery (funnel):** Use the current input to determine the topic, question, and preferences → screen metadata, prioritize, and extract a small amount of information → return user-selected papers to the single-paper workflow. Do not persist the current preferences. Most papers need not be read, and only some parts of the papers that are read need close analysis.

## Boundaries (what this skill does not do)

- Topic-based selection serves the current learning question. Preserve actual sources, queries, and trade-offs; do not claim exhaustive coverage or a publishable systematic review. Use an available specialized method when systematic search is needed.
- **The reading method is built into this plugin** (reading-protocol and note-templates define it). Optional external tools such as paper-reader can improve the workflow when available, but their absence does not prevent basic reading. “Cannot continue without an external tool” is not a valid limitation.
- Do not do semantic-vector retrieval, send emails or notifications, or create scheduled tasks automatically. “Daily” means process the current day's window when the user invokes the skill.
- Importance, difficulty, and reading route are **correctable recommendations**. Scripts and models do not decide that a conclusion is valid or that the user has finished reading.

## Path placeholder

`{SKILL_DIR}` means the absolute path to the directory containing this SKILL.md; the caller expands it. Always quote script paths. On Windows, prefix commands with `PYTHONUTF8=1` if Chinese text is garbled.

## Configuration: `.grad/config.json`

Single-paper explanations, topic selection, and daily discovery may use the current conversation directly; do not require project initialization first. Initialize only when the user asks for project configuration, and never overwrite an existing configuration (on `CONFLICT`, run `validate`). Routine work may read existing quantity and time settings, but use the current request for research direction and do not reuse old queries automatically. Read legacy query fields only when the user explicitly asks to use the saved scope:

```bash
uv run --no-project "{SKILL_DIR}/scripts/radar_config.py" init --config ".grad/config.json" --json
uv run --no-project "{SKILL_DIR}/scripts/radar_config.py" validate --config ".grad/config.json" --json
```

- The script supports `keywords`, `categories`, `daily_caps`, `days`, and `reading_profile`; preserve other skill fields such as `venues_watch` and `thesis_rules` unchanged. New templates leave `keywords` and `categories` empty: do not prefill or store research topics. Keep legacy query fields for compatibility, but do not automatically use them for new daily searches. Read them only when the user explicitly asks to reuse the saved scope.
- The low-burden starting defaults are `daily_caps: {must_read: 1, skim: 2}` and `days: 3`. The current request takes precedence; otherwise keep existing settings and do not silently overwrite them. `daily_caps` allows 0 (that tier may return no items) and rejects negative values, booleans, and non-integers.
- `reading_profile` stores first-use background in four fields: direction, learning_goal, known_background, available_minutes. The paper can still be read if these are unset (use an introductory explanation and mark difficulty provisional). If the user says “I have studied X” in the current session, apply it for this session. **Update these fields only when the user explicitly asks you to remember the information:**

```bash
uv run --no-project "{SKILL_DIR}/scripts/radar_config.py" profile --config ".grad/config.json" \
  --direction "<direction>" --known-background "python,attention mechanisms" --available-minutes 20 --json
```

- For daily retrieval, turn the current topic into explicit `--keywords`/`--categories` parameters; do not write it into the configuration. Check `effective_params` to ensure the categories and keywords actually appear in the query. `--config` remains available when the user explicitly requests its query settings. Precedence is explicit CLI > configuration explicitly specified for this request > defaults. Reading the configuration does not modify it. Saved reading background may support single-paper explanations; it does not automatically become the topic for daily filtering.

## Single-paper reading (main workflow)

For requests such as “help me read this,” “is it worth reading,” “explain it in more detail,” or “continue the last paper”:

1. **Read the protocol:** Follow `references/reading-protocol.md` `0 for routing and `1 for the processing order. First run `show` to find an existing record; if one exists, do not ask again for recorded progress or background.
2. **Retrieve content:** For arXiv, use `arxiv_html.py` (inspect the outline first, then retrieve sections needed for the task; a complete review guide must process the full work). If the user specifies version vN, read vN. Use the host's available capability for a local PDF. With only an abstract, the maximum deliverable is quick. With identity information alone, provide an original-source link, not a content note.
3. **Extract and write:** Read `references/extraction-guide.md`. First make an evidence-and-conditions list for key claims, then compress it into a coherent explanation using `references/note-templates.md`. Before and after compression, verify definitions, mechanisms, settings, results, and limitations. If the content is insufficient, deliver partial results. A complete review has a separate survey-protocol; do not use the short card standard.
4. **Save:** Use scripts when the user asks for notes, requests an update, or an existing project convention requires saving. For conversation-only explanations or recommendations, deliver directly. For public content production, use an explicitly named isolated directory; do not initialize or rewrite a personal `.grad`. On first save, run `register` for an idempotent record:

```bash
uv run --no-project "{SKILL_DIR}/scripts/reading_record.py" register --repo . --input-file <identity-source-category-json> --json
uv run --no-project "{SKILL_DIR}/scripts/reading_record.py" save-note --repo . --paper <id> \
  --note-file <note-body> --mode quick|standard|deep --basis sections \
  --sections S1,S3 --limitations "Figure 3 was extracted from its caption only" --json
```

5. **Reply:** Provide the result in a form the user can read directly and include the note path when saved. A learning guide may include a few useful locations in the original and comprehension checks. For a quick assessment, claim check, or reader with an existing method, finish according to the task; do not generate questions mechanically. Do not guess a location when there is no outline.
6. **Update reading status only from the user's statement:** Use this one path when the user expresses reading status (an AI-generated note does not equal completion; scripts prohibit agent-assigned status):

```bash
uv run --no-project "{SKILL_DIR}/scripts/reading_record.py" set-status --repo . --paper <id-or-versioned-id> \
  --status read --user-quote "<user's own words>" [--read-version v1] --json
```

After v1 was read and v2 is retrieved, say “v1 was read; current material is v2.” Do not claim that v2 was read or erase reading history. **The version read is determined by the user's statement** (use `--read-version` or a version-qualified lookup such as `--paper 2410.06992v1`). If no version is specified, leave `last_read_version` null; do not treat the current material version as the version read. By default the script rejects wholesale replacement when notes conflict with manual edits or have been merged. `--merge` may append additions repeatedly without losing human content, and subsequent ordinary saves to a merged note retain append protection. Use `--force` only when a full rewrite is truly needed; the old note is snapshotted to history. Never overwrite the user's `.user.md` annotations. If no readable source is available, do not save any note ( `--basis unavailable` is rejected); use `--record-failure` to record only the retrieval failure and materials needed.

## Daily discovery

Reuse topic, question, and preferences from the current request and the same task conversation. Ask only when missing information would change the search scope. Without a defined scope, do not assume an LLM/Agent topic or infer interest from reading records. Split the current goal into keywords and choose categories; specify categories only when they narrow the search, and do not guess category IDs. Omit `--categories` when searching keywords alone.

```bash
uv run --no-project "{SKILL_DIR}/scripts/arxiv_fetch.py" \
  --keywords "<current comma-separated keyword group>" --days 3 --json
```

- Use the current request's `days` or an existing time setting; default to 3 when unspecified. Repeating the keyword argument means OR between groups and AND within a group; categories may be added for the current scope. This normal workflow keeps query, metadata filtering, prioritization, limited extraction, and reading of selected papers; it does not require persistent research preferences.
- The script runs sequentially at one request every three seconds with exponential backoff on 429. Do not call it in parallel. The default window is three days (arXiv indexing can lag by 1–3 days). `new: false` marks an item retrieved before; avoid repeating it for the same scope. Another topic may still justify it based on current relevance; do not use seen status as an interest filter.
- For empty results without a network error, suspect indexing lag first and expand the window once (for example, `--days 5`). If still empty, report that accurately. Separate network errors (`NETWORK`/`RATE_LIMITED`) from “no matching papers”; **do not present offline status as zero new papers**.
- If results are truncated (`truncated: true`), state that; do not claim all new papers were covered.

After retrieving the list, **read `references/tiering.md`** for prioritization. Continue using machine enums `must_read`/`skim`/`archive` internally, but display “priority reading,” “quick look,” and “other candidates” to the user. `must_read` is this search's recommendation tier, not `importance=core` and not a reading task. Quantity: follow the current request, then existing `daily_caps`; if neither specifies it, use the low-burden default of 1+2. Do not pad a short list; put remaining items in a brief index. Order evidence by the current question, not by fixed paper type or field. Do not retrieve full texts for dozens of candidates by default; only selected papers enter the single-paper workflow. Give a falsifiable reason for each paper and state that the ranking is heuristic, not a quality judgment.

A new arXiv submission is only a recent candidate; it does not automatically satisfy “top conference” or “highly cited.” For high-quality recommendations, verify the final primary reading's source and content using selection-protocol. Read a user-specified paper normally even if it does not meet recommendation criteria.

When the user asks to save a brief or a project convention requires it, save the daily brief as `.grad/radar/YYYY-MM-DD.md`. First check date, search scope, and parameters. Reuse an existing brief for the same date and scope by default; if scope changes, use a distinct filename or preserve the old version before refreshing as requested. Do not mistake a previous brief on another topic for current results. The brief records this search and its decisions, not preferences to reuse automatically:

```markdown
---
date: YYYY-MM-DD
papers:
  - tier: must_read
    arxiv_id: "<base ID>"
    paper_id: "arxiv-<base ID>"
    path: "radar/digest/arxiv-<base ID>.md"
  - tier: skim
    arxiv_id: "<ID>"
    paper_id: null
    path: null
---
```

This header is a machine-readable contract: `papers` covers every paper in this period; `tier` is `must_read`/`skim`/`archive`; `arxiv_id` is a string; `paper_id` links to a primary record (null if not registered); `path` is relative to `.grad/` and null when there is no note. The body is for people; downstream tools such as weekly-brief read the header. End the brief with at most one current learning suggestion (for example, “finish the paper already in progress”).

The shared deduplication ledger `~/.grad-radar/seen.jsonl` means only that a base ID was retrieved or seen. Seen does not mean the user read it or is interested in it. Do not infer future preferences from seen papers. Single-paper processing, notes, and reading status remain in the primary records under the project's `.grad/`. Feedback on daily tiers affects only the current result; do not change the configuration or plugin rules.

## Section slicing (HTML main path)

```bash
uv run --no-project "{SKILL_DIR}/scripts/arxiv_html.py" <id|idvN> --outline --json
uv run --no-project "{SKILL_DIR}/scripts/arxiv_html.py" <id|idvN> --sections 3,3.2 --json
```

Read the outline first, then fetch sections. Output includes `version`, `version_status`, and `fetched_at`. Cache entries are isolated by version and retain their original retrieval time when reused. If an explicitly requested version returns 404, report it; do not silently switch versions.

## Fallback chain (in order; state where a failure occurred)

1. `arxiv.org/html/<id>` provides a LaTeXML structure → slice by section (primary path, `source: arxiv_html`).
2. `NO_HTML` (no LaTeXML; very old or image-only submission) → ask whether the user has a PDF or use a host capability or an external parser such as MinerU if available (`source: host_pdf`/`external_parser` plus `parser_name`).
3. User pastes body text or an abstract → `source: user_text`.
4. Reliable abstract but no body → quick mode with `basis: abstract`. Identity/title only → original-source link and, when authorized, register identity only. `basis: metadata` cannot save a content note.

## Non-negotiable rules

- Give a falsifiable reason for each paper and tier. Do not invent arXiv IDs, section numbers, or numbers; report scripts accurately.
- List unread sections under “not covered.” Do not pretend to have read the full text; a figure caption is not the figure.
- Briefs and notes are created or updated only when authorized; do not silently overwrite. Repeated display or rereading must not create duplicate notes.
- Record-maintenance timestamps (created_at/updated_at/note.generated_at) are never the time the user finished reading.

## Error contract

When a script returns `{"ok": false, "error": ..., "detail": ...}`, report it accurately and do not retry blindly. `RATE_LIMITED`/`NETWORK` means offline or try later; prior material may be used only if clearly labeled old. For `NO_CONFIG`/`BAD_CONFIG`, check the configuration specified for this request; routine discovery may use explicit query parameters instead. For `BAD_ARGS` with no scope, ask for the current scope rather than searching all fields with an empty configuration. For `AMBIGUOUS_IDENTITY`, list candidates and ask the user to choose. For `CONFLICT`, explain what old content was protected and the available options. For `NOT_FOUND`, say that the record does not exist. `ok: true` means only that the script completed, not that the note is high quality.
