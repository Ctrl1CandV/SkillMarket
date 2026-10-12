# Single-Paper Reading Protocol (grad-radar · Stage 1)

When the user gives a paper to this plugin—by specifying it directly or choosing it from a daily brief—follow this protocol. Both entry points share the goal: **give the user a traceable note matched to their background and the paper, with a clear next step for reading**. Scripts store records and notes; this protocol guides judgment and writing. The user may correct an interpretation, and that correction overrides an earlier guess.

By default, support readers with less experience by explaining essential concepts, methodological relationships, and how to interpret evidence. Do not infer ability from a title or affiliation. When the user states their background or reading method, reduce unnecessary setup according to the actual question. Teaching support does not require comprehension questions every time and does not change source, condition, or coverage checks.

## 0. Route by the user's request

| User request | Route |
|---|---|
| “What new papers are worth following today?” | Daily discovery (SKILL stage 1); papers chosen by the user return to this protocol for single-paper reading. |
| “Find an introductory paper for me” / “Recommend a review in this field” | selection-protocol: prioritize venue, year, citations, and other criteria according to the question, reader, and context; state hard requirements. A classic foundational paper may be the primary reading. |
| “Give me a complete summary of this review, focusing on X” | survey-protocol: cover the whole review, explain the requested focus in depth, and still provide substantive treatment of other branches. |
| “Help me read this: <link / arXiv ID / local PDF>” | Identify the paper → read any existing record → single-paper workflow (standard by default). |
| “I lack the background for this; explain it in detail” | Reuse the existing record: adjust explanation using difficulty and add deep notes without starting over. |
| “First tell me if it is worth reading” | Quick card; **do not expand automatically into complete close reading**. |
| “Continue the methods section from last time” | Use `reading_record.py list --status reading` to locate the in-progress paper; read the primary record, existing notes, and user annotations, then continue the unfinished part. |
| “I finished this” / “Pause this paper” | Only this explicit statement permits `set-status`. A read status records `last_read_at` and the material version at that time. |

For a bare title, first run `reading_record.py show --repo . --paper "<title>"` to search existing records. If none is found, use host search or arXiv lookup to identify it. **If identity is ambiguous, list candidates and ask the user; do not guess an ID, DOI, or local path** (AMBIGUOUS_IDENTITY detail already contains candidates). When a title alone cannot establish a unique match, ask for a link or file and retain confirmed details such as the title in the conversation.

## 1. Shared processing order (every paper)

1. Confirm the request, target paper, and desired depth (use the default in `3` if unspecified).
2. Run `reading_record.py show` to read existing records and `reading_profile` from `config.json`. **Do not ask again for information already known.**
3. Based on title and abstract, provisionally classify importance, difficulty, and paper_type, with a separate one-sentence reason for each; set `provisional=true` at this stage.
4. Confirm the source, actual version, and currently readable scope (`6: sources and fallbacks).
5. Select sections, figures, tables, and necessary prerequisites for the task. **There is no fixed list of sections that must never be read**; background, settings, and appendices may all be relevant.
6. First use `extraction-guide.md` to preserve useful information and original locations. Then write the explanation at the chosen depth using `note-templates.md`. If body text is insufficient, narrow the actual deliverable. Identity information alone does not justify a content summary.
7. Save only when requested or required by project convention. A recommendation or conversation-only explanation does not require a saved note. To save, use `register` on first use and `save-note`; protect personal annotations (`7`). The initial version and classification may be provisional; after reading, update the actual source and classification with `update-context`. `reading.mode` is the depth of the note actually produced; do not upgrade it through a context update when source material is insufficient.
8. Reply with content the user can read directly and include the note path when saved. A learning guide usually gives a few locations in the original and why to read them; add comprehension checks only when useful to this learning task. For quick assessment, reproduction, or claim checking, give next steps that fit the goal rather than a fixed closing format. Explain clearly without boilerplate. If time is limited, shorten the current unit, but do not remove conditions and examples needed to understand that unit.

## 2. Classify three dimensions separately

| Dimension | Values | Basis | Avoid |
|---|---|---|---|
| importance | core / relevant / peripheral / unknown | Relationship to the user's learning goal, foundational value, representativeness | Treating citation count, venue, or publication date as importance |
| difficulty | accessible / needs_background / challenging / unknown | Background already mastered, required prerequisites, complexity of reasoning | Saying only “difficult” without naming the barrier; treating the number of new terms as a score |
| paper_type | method / survey / theory / system / evaluation / other | How the paper's main task and contribution are organized | Classifying mechanically from title keywords; downgrading every review |

- For a mixed-type paper, choose one primary type and describe secondary characteristics in prose; do not create weighted multi-label scores.
- selection-protocol orders venue, citations, year, and related criteria for the current context. Treat them as hard thresholds only when the user specifies them. Here, importance means relevance to the current learning goal. Meeting selection criteria does not automatically mean core. Do not refuse to read a paper the user specified just because it fails recommendation criteria.
- After reading the body, update the classification if appropriate using `update-context --classification-json` and explain why.
- An “important and accessible” paper still needs key settings and conclusions checked; ease does not justify skipping evidence. For a “relevant and moderate” paper, standard notes may focus on understanding the idea and key experiments.

## 3. Three reading depths

| mode | User-facing label | Purpose | Minimum material | Approximate output |
|---|---|---|---|---|
| quick | Quick assessment | Decide whether to invest more time | Reliable abstract (**title alone cannot support a content summary**) | Roughly 150–300 Chinese characters |
| standard | Standard reading | Explain the question, core mechanism, key evidence, and scope | Body sections directly relevant to the explanation | Usually about 800–1,500 Chinese characters |
| deep | Focused deep reading | Resolve a substantial and difficult comprehension question | Specified core sections and necessary context, with figures/formulas when available | Keep the opening short; expand as needed |

Lengths are presentation guidance, not acceptance thresholds. Do not invent content to meet a count or remove settings that affect the conclusion to make a note shorter.

A quick assessment may use some body text; describe the scope actually available. A short deliverable does not mean only the abstract was read. Identity alone provides an original-source entry point, not a fourth “reading complete” mode. The length of a complete review guide depends on the work; completeness depends on whole-work coverage and checks, not on a deep label.

**Decision order:** (1) Follow the depth the user explicitly requested. (2) Source availability **limits the actual deliverable**: if deep was requested but only an abstract was retrieved, deliver quick and clearly state it is incomplete; save-note automatically downgrades and warns. (3) Without an explicit request, a paper supplied directly by the user defaults to standard; daily initial screening defaults to quick. (4) Suggest deep for a core paper, but decide whether to expand now based on the user's available time. (5) needs_background/challenging changes explanation and reading order; it is not a reason to archive a paper. (6) Peripheral papers normally stay quick; if the user wants detail, use standard or deep.

## 4. Reading focus by paper type (organization of section 2 in standard notes)

| Primary type | Read first | Note focus | Suggested stopping point (not certification) |
|---|---|---|---|
| method | Problem definition, overview diagram, core modules, key comparisons | What changed from the baseline; why the mechanism might work; where evidence reaches | Explain the input, processing, output, and main comparison in the reader's own words. |
| survey | Scope, taxonomy figure, main branches, representative work | Map the problem; distinguish branches; suggest an entry sequence related to the user's goal | Describe main approaches and differences, then choose the next paper. |
| theory | Definitions, theorems, assumptions, proof outline | Conditions for the conclusion; key derivation; intuition and counterexample boundaries | State the conclusion, necessary assumptions, and one case where an assumption fails. |
| system | Requirements, architecture, module interfaces, performance cost | Data/control flow, bottlenecks, trade-offs, measurement conditions | Explain module roles and one major performance trade-off. |
| evaluation | Measurement goal, sample/task construction, protocol, main findings | What is measured; comparison conditions; generalizability; failure cases | Describe the measurement target, protocol, and at least one limit on the conclusion. |
| other | Use abstract and outline to establish the structure | Standard outline plus what prevents accurate classification | Answer “question, approach, evidence” without forcing a template. |

A foundational survey may be core: focus on its taxonomy and reading order rather than forcing it into a “how much did the method improve?” template.

## 5. Scale background explanations and derivations

- For a first-time reader, start with a few essential concepts: give intuition, explain their role in the paper, and add a short example when useful. Adjust the amount to the reader and current unit. Skip concepts already mastered; add further prerequisites in stages instead of turning the task into an unrequested full course.
- Label self-created examples, analogies, and derivations as **supporting explanations**; never present them as experiments by the authors.
- For equations, explain symbols, inputs and outputs, and why the equation appears before unpacking key steps.
- If a derivation has missing steps that cannot be reconstructed, identify the gap and suggest the original source or prerequisite material. **Do not fabricate a proof.**
- The user's personal interpretation belongs only in the user's annotation section; do not present an assistant's guess as “my understanding.”

## 6. Sources and fallbacks (determine what can be delivered)

Retrieval priority: arXiv HTML via `arxiv_html.py` with section extraction; a user-provided local PDF using a reading capability actually available on the host; then an external parser such as MinerU if available. Store the source enum in primary-record `source.parser`: `arxiv_html`, `host_pdf`, `external_parser` (also record `parser_name`), `user_text` (text pasted directly by the user), or `metadata_only` (abstract only). Do not mislabel another reading tool as MinerU.

- **When the user specifies version vN, read vN.** Without a specified version, retrieve a fixed version that can actually be confirmed (`arxiv_html.py` reports version/version_status/fetched_at). If version cannot be confirmed, record `version=null` and `version_status=unknown`; do not guess v1.
- For complex layout, scans, or key images that cannot be read, state exactly what was not read. If it affects core understanding, stop at an abstract card or a partial note.
- **Extracting only a figure caption does not mean the figure was viewed; extracted table text does not mean its structure was checked; garbled equations must be identified.** Record these limitations in `--limitations` and “Not covered.”
- If no reliable text is available, register only identity and the retrieval failure. save-note rejects empty content; do not fabricate a summary.
- Separate network errors from “no matching paper.” An empty result is not automatically an indexing delay; within rate limits, one expanded-window attempt such as `--days 5` may be made.
- If `--sections` returns `not_found`, report that the requested section number was not found; do not guess missing numbering.

## 7. Saving and personal annotations

- Keep one primary record per paper (`.grad/radar/papers/<paper_id>.json`) and one current primary note (`radar/digest/...`). During initial registration, an existing digest is linked automatically (note.path retains the old path; the file is not moved).
- When updating a paper note, the script snapshots the old draft under `digest/history/`. If the primary note has manual edits, the script rejects wholesale replacement by default. Use `--merge` to append a “Further Reading” section when that fits the user's intent, or ask the user to resolve it first. **Do not swallow annotations.**
- The user maintains `<paper-key>.user.md`. Preserve their words when organizing annotations.
- “Continue,” “add,” or “redo” itself authorizes the requested update; do not repeatedly confirm. But **displaying the same note again must not create another note**, and saving identical content must not create another history entry.
- When adding another version, preserve source scope per version in `note.coverage_sources`. The primary note's baseline `source_version` does not mean every added section came from that version. If old-version content remains, do not merely change the title to a new version and call it complete.

## 8. Initial background configuration (four useful fields)

`reading_profile` stores only direction, learning_goal, known_background, and available_minutes.

- Reading may proceed when these are empty: use an introductory explanation and mark difficulty provisional.
- Do not require a questionnaire or guess the user's courses, advisor's research direction, or compute resources. Statements such as “I have studied X” or “I only want a quick overview” take effect immediately in the current session. Persist them with `radar_config.py profile ...` **only when the user asks you to remember them**.
- Priority: current request > same-task conversation > authorized single-paper reading profile > plugin defaults. Existing config works; treat new fields as optional. Reading background and topic do not automatically carry over to future daily searches.

## 9. Scenario quick reference

- **Twenty minutes after class for a new paper:** use daily_caps to return a short list. If continuing an important in-progress paper is more useful, say so directly, for example, “No new paper today; continue X.”
- **A key methods paper was found:** default to standard, reuse its existing record instead of registering it twice, and do not simply hand the user to an external tool.
- **Important but difficult:** keep importance and difficulty separate; list prerequisites, explain key formulas in layers with sources, complete one clear reading unit at a time, and provide an entry point for the next unit.
- **Abstract only:** deliver a quick card and state that deep reading is incomplete; save-note records the actual downgrade.
- **Continue with existing annotations:** read the primary record, note, and .user.md first; answer the user's question, then mark new content separately.
