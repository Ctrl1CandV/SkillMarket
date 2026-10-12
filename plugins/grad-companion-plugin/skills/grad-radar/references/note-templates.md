# Reading Note Templates and Writing Standards (grad-radar · Stage 1)

The three depth levels use the existing record format. These outlines serve single-paper reading and may be renamed, combined, or expanded by paper type. For a complete review, use the guide structure in survey-protocol. Do not leave placeholders in a delivered note.

## Note header (for display and traceability; papers/*.json is authoritative)

```markdown
---
paper_id: "<primary record ID>"
arxiv_id: "<base ID, or null for non-arXiv material>"
date: YYYY-MM-DD
mode: <quick|standard|deep>
basis: <abstract|sections|fulltext|...>
source: <arxiv_html|host_pdf|external_parser|user_text|metadata_only>
source_version: <vN or null>
---
```

Header fields should match save-note parameters (the script treats the primary record as authoritative; if the header is wrong, follow the record and correct it at the next update). Older digests without a paper_id header remain readable: weekly-brief links them by arxiv_id; a legacy note proves only that a note exists.

## General presentation principles

1. Start by answering what the paper is about and whether it is worth investing time in. Keep detailed metadata in a short source line or header.
2. Use coherent short paragraphs for body text; use lists and tables for processes, comparisons, and parallel conditions.
3. Quote the source sparingly and accurately. Prefer explanation in your own words with source links; do not copy a whole section or use long quotations to pad the note.
4. Keep author claims, evidence visible in the paper, and assistant explanation distinguishable. They need not be labeled in every sentence, but must not be conflated.
5. **Important numbers require the settings needed to interpret them.** A percentage without context is not a summary of the main result.
6. Put source pointers (section anchors or PDF page numbers) near key conclusions; do not place all citations in a pile at the end.
7. Use figures and tables only when they aid understanding; do not generate a decorative diagram for every paper by default.
8. Describe “not covered” according to actual reading. Do not always say “figures and tables not read” when a table was reviewed. Conversely, the parameters passed to save-note are the factual record.
9. Omit optional sections with no content. For a necessary section with missing evidence, state why.
10. Leave the user-annotation area for the user's own words. The model must not write “my understanding” on the user's behalf.
11. Read extraction-guide first. Preserve causality, numeric settings, negation, and boundaries before improving expression. The opening may be short, but expand the body as needed for understanding. Do not replace a full example and argument with a few labels.
12. Put source details and production notes together near the end; place conclusion-affecting limits and short citations near the relevant text. Do not repeatedly explain production choices in the body.
13. Reconcile core extracted points with the finished note: definitions, mechanisms, result settings, and key failure conditions need a place. Remove repeated wording only; do not erase “no improvement” or “holds only under setting X.” Mark partial results if necessary information was not carried forward.

## Quick-assessment card

```markdown
# <Paper title>

<One sentence: research question and central approach.>

**Why it matters to you:** <Specific connection to the current learning goal; state if the assessment is provisional due to missing background.>
**Reading recommendation:** <Continue with standard reading / read closely / save for later / defer, with one reason.>
**Difficulty:** <Necessary prerequisites; omit if there is no notable barrier.>
**Current finding:** <What the actual material supports, preserving key conditions; say so if only the abstract was read.>

Basis: <Actual source, version, and scope>. <If abstract only, state that the method and experiments were not checked; if body text was read, identify the sections checked and remaining gaps.>
```

“Read chapter X next” must be based on an outline actually retrieved. Without an outline, recommend a **type of section** (“start with the methods section”) instead of inventing a location such as S3 or Figure 2.

## Standard reading note

```markdown
# <Paper title>

<2–4 sentences: research question, central approach, main finding, and relationship to the current goal.>

Reading recommendation: <next depth, why, brief route>
Source: <link or user file with version identified>; material actually used: <section/PDF page range>.

## 1. Clarify the problem
<What the authors are solving and the main obstacle in earlier approaches>
<Only necessary terms and background, connected to concepts the user already knows>

## 2. How the core idea works
<Organize by primary type: method mechanism / survey taxonomy / theory outline / system architecture / evaluation protocol>
<Explain key steps and their relationships; explain one central figure or equation when useful>

## 3. What supports the conclusion
<Select 1–3 valuable pieces of evidence; for each give comparison, necessary conditions, and source>
<Distinguish the authors' interpretation from the scope directly supported by evidence>

## 4. What is most worth remembering
<Transferable problem definition, method idea, theoretical condition, or evaluation lesson; explain why it matters>

## 5. Limitations and unresolved questions
<Limitations stated by the authors, with source pointers>
<Questions the assistant thinks need further checking—label these as analysis, not the authors' conclusions>
<Truthfully state sections, figures, or equations unavailable or restricted by parsing>

## 6. What to read next
<1–2 original sections/figures worth reading personally, what to look for, and why>
<Add comprehension questions only when useful for this learning task; otherwise give a relevant next step or omit. Do not certify mastery automatically.>

## Evidence and coverage
- Read: <actual sections/PDF pages, tables checked, and images viewed>
- Not covered or parsing-limited: <actual gaps>
- Source and version: <link, retrieval time, and version status>
- Personal annotations: <link to .user.md if present>
```

Sections describe content goals, not length quotas. For theory, evidence may be a proof outline; a survey may be valuable for its taxonomy. Do not force “how much did it improve?” into every paper.

## How to expand a deep note

Keep the short opening from standard notes, then expand relevant sections as needed: prerequisites and a symbol table limited to what this reading uses; a step-by-step method example, key formula explanation, or argument chain; interpretation of central figures/tables with settings and limitations; a local comparison with a paper the user already knows (only if material for both papers is available); or a staged reading plan (“understand A this time, continue with B next time”). Put long derivations in an appendix section and link to it from the body. Keep the first screen readable.

## Saving (use scripts when requested or required by project convention)

```bash
uv run --no-project "{SKILL_DIR}/scripts/reading_record.py" save-note --repo . \
  --paper <paper_id-or-arXiv-ID-or-title-fragment> --note-file <temporary-note-file> \
  --mode quick|standard|deep --basis sections \
  --sections S1,S3 --limitations "Figure 3 extracted from caption only; equation (7) garbled" --json
```

For PDFs, physical pages are a **comma-separated list of integers**. Omit --pages for HTML, which has no physical page numbering:

```bash
uv run --no-project "{SKILL_DIR}/scripts/reading_record.py" save-note --repo . \
  --paper <id> --note-file <temporary-note-file> --mode quick --basis sections \
  --pages 3,4,5,6,7,8 --figures "Figure 2" --tables "Table 4" \
  --limitations "Other images have captions only; table cells not checked individually" --json
```

- Pass `--source-version` only when the version is **actually confirmed** (confirmed/cache-fallback); use the version reported at retrieval. Omit it when unconfirmed (unknown); the script records null and does not inherit an old version from the material record.
- When merging notes, the old `note.source_version` remains the baseline for the primary note, including when unknown. Check actual versions for added sections in `note.coverage_sources`; a flat field cannot claim the whole note uses one version.
- Fill `--sections/--figures/--tables/--pages` with items actually checked. Leave the list empty when nothing was checked; do not claim full coverage.
- With `basis=abstract`, `mode` automatically downgrades to quick to prevent misrepresentation. `basis=unavailable` cannot produce a note; use `--record-failure` to record the retrieval failure only.
- `basis=metadata` means identity information only and cannot save a content note; use abstract when an abstract is available. For `basis=sections`, provide actual section numbers or physical pages; do not claim body reading with an empty range.
- If a note conflicts because it was manually edited or merged, the script rejects wholesale replacement by default. Follow the current request: use `--merge` to append (repeatable) or ask the user to resolve it first. **Do not swallow annotations.**
- **Never describe save-note as “the user has finished reading.”** set-status is the only path for reading status.

## Good and bad examples (review before writing)

| Weak | Better |
|---|---|
| “Introduces an innovative framework and achieves significant improvement.” | State which stage changed, compared with what, and the result under which settings. Do not add missing numbers. |
| “This paper is important; read it closely.” | “It explains the assumption behind method X that you are learning; start with the definitions and central figure, then read the experiments.” |
| “The method is complex and requires deep understanding.” | “The main barrier is conditional probability and the variational lower bound; review those concepts before equation (3).” |
| “Proves the method is generally superior to existing methods.” | “The authors observed an advantage on the tasks and budgets reported in the paper; this does not establish performance in other settings.” |
| The model writes “my understanding is...” in the user's annotation. | The AI note labels its text “supporting explanation”; .user.md remains for the user's own words. |

## Human review (answer after a trial read; word count, heading count, and model self-rating are not substitutes)

- Without opening the paper, can the reader explain the question and key approach?
- With the source open, can the reader locate the most important conclusion in the note?
- Does a less experienced reader know what to learn first, rather than being buried in more terminology?
- Do surveys, methods, and theories receive meaningfully different treatment rather than one template with substituted words?
- Are the authors' conclusions, assistant explanations, and unknowns separated?
- Can the note support a decision about what to read next?
- **Three-part metric check: whose output, numerator, denominator.** For coverage/accuracy metrics, state whether this scores model responses or reference material and which subset is the denominator. A metric averaged only over tasks where a central claim exists cannot be compared directly with one over all tasks.
- **Check how far a mechanism actually guarantees.** When saying a component or constraint works, verify what the source guarantees and what it does not. For example, a typed operator may ensure candidates stay in a valid representation space while feasibility still depends on whether the generated evaluation function is correct. Do not claim guarantees absent from the paper.
- **Output evidence is not evidence of an internal process.** Evaluation of final answers (coverage, consistency, judge ratings) shows what the model “expressed,” not what it “thought” or “understood.” Label claims about internal processes as hypotheses.
