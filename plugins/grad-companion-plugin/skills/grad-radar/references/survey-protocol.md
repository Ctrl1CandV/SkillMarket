# Complete Guide to a Review Article

Use for requests such as “give me a complete summary of this review, focusing on X.” For an explanation of selected sections, use single-paper reading. This workflow treats the review itself as the source; it does not mean the cited papers were independently read in full.

## 1. Fix the version and inventory the source

Record the question to understand, existing background, and focus. By default, support readers with less experience, adjusting prerequisite explanations and examples to their actual background. Reuse a stated reading method or topic goal. Read the version specified by the user; otherwise confirm the version actually obtained and never guess if it is unconfirmed.

First retrieve the abstract, introduction, full outline, main taxonomy figure, and conclusion to establish the authors' scope and structure. This is not completion of the full review.

Retrieve every body section, key figure/table/equation, and appendix needed to understand the main text. For HTML, first run arxiv_html.py --outline and then call --sections for each section in the outline. For PDF, use a reading capability actually available on the host and distinguish physical from printed page numbers. A file's existence, successful parsing, or returned section does not by itself mean it was processed or checked.

Use a production inventory that lists each source section/asset, its location, whether it was retrieved/processed/checked, its corresponding guide heading, and any gap. References and acknowledgments may serve as indexes. A nonessential appendix may be skipped with a reason, but main sections must not disappear from a “complete” inventory because they were considered irrelevant.

For a formal journal PDF with no arXiv vN, fix the material with its DOI/source identifier, version description, and SHA-256 of the actual retrieved file; do not fabricate v1. Record source_id in both the source inventory and production inventory. Verify that both refer to the same paper and material, not merely that both say “v1.” Record retrieval time separately from the literature cutoff used by the review.

## 2. Process the full work in batches

Read along natural section boundaries. When splitting a long section, retain parent headings, terminology, local relationships, and version. First use extraction-guide to record taxonomies, criteria, mechanisms, roles of representative papers, comparisons, evidence, and limitations; preserve the raw extraction.

Explain the requested focus in depth. For other branches, describe core content, role, and differences; do not reduce them to headings. Return to the source when cross-section taxonomies or terminology conflict; do not force different dimensions into one scheme. Check middle sections, footnotes, negative findings, conclusions, and necessary appendices deliberately.

Intermediate records must make it possible to trace section details, cross-section relationships, and how source material carries into the guide. Use section extractions, comparison matrices, and mapping lists, or combine them into one extraction document. Manage a complex review in separate files; a short review does not require three separate files or a fixed set of column names. Choose comparison dimensions such as assumptions, mechanisms, evidence conditions, costs, and failures based on the actual taxonomy and current question. If representative work is known only through the review, label it as secondary evidence. Check the original paper only when a substantive judgment about its performance, conflict, or implementation depends on it; do not endorse claims on the review author's behalf.

First synthesize within the authors' stated scope. Search for later developments only when the user asks for an update or the current question depends on changes since the literature cutoff. Put such material in a separate “Later developments” section. For other tasks, report the authors' cutoff and the scope actually processed; do not launch a new search automatically or rewrite the authors' classification and conclusions under the pretext of an update. Reading one review, writing a guide to it, and conducting a systematic review across many papers are distinct tasks; do not promise unrequested systematic searching.

If the budget is insufficient, retain processed sections, extraction, and the next section according to save authorization, then deliver a “partial guide.” Continue from the source and extraction in the next session. Reduce the number of papers handled at once or split the work into batches; do not force the entire review into a fixed word count.

## 3. Organize the reader-facing guide

```markdown
# <Accurate title> — Review Guide

<Scope, central question, why it fits this request; link to the fixed-version source>
<Where to start; whether this is complete or partial and any material gaps>

## Contents
<Clickable contents matching the real headings below>

## <Background and the authors' organization>
<Explain necessary concepts, field questions, and basis for the taxonomy>

## <Topics or branches organized for this review>
<Mechanisms, differences, examples/comparisons, relevant figures, and conditions; explain the requested topic fully>
<Repeat topic sections as useful; no fixed count required>

## <Comparison, evaluation, or debate>
<Settings, level of evidence, and scope; do not present a review's list as a performance ranking>

## <Limitations, open questions, and relation to the current request>
<Separate author-stated limitations from editorial analysis; note the review's literature cutoff>

## What to read next
<A few actual source locations and a reason for each based on the current goal; comprehension questions as needed. Claim-checking or implementation tasks may give another next step.>

## Source and coverage
<Detailed locations/source entry points, actual scope, and gaps; save production logs separately>
```

Write headings for the actual content instead of filling a template mechanically. Use figures/tables to explain taxonomies, processes, or differences; distinguish explanations of original figures from teaching diagrams. No decorative figure is required for every review. Explain whether taxonomy dimensions are exclusive, composable, or hierarchical. A source inventory may go in an appendix, but keep important differences and failure conditions in the body.

Put short citations next to claims, and conditions/limitations next to conclusions. Distinguish the authors' summaries, supporting examples, editorial connections, and timely updates. Check sources separately for any new developments; do not present them as part of the original review. Keep reference numbering, retrieval timestamps, and tool logs out of repeated body text.

## 4. Completeness checks

Compare the guide with every source section. Ensure important definitions, all major categories/branches, mechanism differences, key evidence, limitations, and necessary appendices are represented. Having every heading in the contents does not prove adequate coverage. Keep the guide partial if a key image was not viewed or a table/equation cannot be read and this affects the explanation.

Read the body as a learner and look for over-compression. If a section contains only approach names, module labels, or a list of future directions, restore what the source does, why it does it, when it fails, and how representative implementations differ. For example, do not reduce retrieval to “match by similarity”; explain indexing on write, query matching, selection, and use. Do not turn open questions into parallel slogans. It is not necessary to copy the bibliography item by item; a current reader must understand key mechanisms and their rationale. Default to beginner-friendly explanations, reducing prerequisites for an experienced reader as appropriate; never remove conditions a claim depends on.

As needed, run scripts/survey_check.py to check inventory consistency:

```bash
uv run --no-project "{SKILL_DIR}/scripts/survey_check.py" \
  --outline-file <arxiv_html-outline-json-or-equivalent-manual-outline> \
  --coverage-file <production-inventory-json> --json
```

The outline may be the full output from arxiv_html.py --outline --json (ok/data) or its data object. Preserve the source outline; do not delete sections to make a check pass. Example coverage-file structure:

```json
{
  "version": "v1",
  "source_id": "arxiv:2404.13501",
  "sections": [
    {"id": "abstract", "processed": true, "checked": true, "disposition": "taught", "guide_heading": "Overview"},
    {"id": "S1", "processed": true, "checked": true, "disposition": "taught", "guide_heading": "Why this problem matters"},
    {"id": "bib", "processed": false, "checked": false, "disposition": "reference-only", "reason": "Kept as a reference index; cited full text not read independently"}
  ],
  "assets": [
    {"id": "Figure 1", "kind": "figure", "required": true, "checked": false, "basis": "caption-only", "issue": "Original figure not yet viewed"}
  ]
}
```

The sections list must cover every item in the original outline. Numbered sections and abstract must be actually processed, checked, and represented by guide_heading. Appendices are required by default and follow the same standard; if nonessential, explicitly set required=false and provide a reason. Bibliography/acknowledgments may be reference-only, with an explanation. Build the asset inventory by inspecting the actual full text. Required assets use required=true. Checking a figure requires visual inspection; checking a table/equation may use text or visual. Any unchecked asset claimed to be nonessential needs a reason. Do not omit unknown or unprocessed assets. A cache-fallback may fix a previously known version; state whether a newer online version was checked.

arxiv_html outlines include id, which the checker normalizes as source_id arxiv:<base ID>; use the same source_id in the production inventory. A manual outline must also include source_id. For non-arXiv material, set the same non-empty version description and source_sha256 (64 hexadecimal characters) in both inventories, and set outline version_status to confirmed. Old inventories without identity can still check section coverage but cannot report coverage_ready; provide the real identity rather than entering arbitrary values to pass the check.

For an existing Markdown guide, add --guide-file <guide.md>. The checker verifies that guide_heading appears as a real body heading (excluding code blocks) and reports missing headings. It cannot verify the quality of explanations beneath the headings.

coverage_ready means only that the declared scope, version, and required assets passed mechanical checks. It cannot detect omissions outside the inventory or false entries and cannot prove that the explanation is comprehensive. Source-fact checks and reader-facing review must still pass separately before calling the guide “complete.” Without confirmed version or when material gaps remain, deliver a partial result.

## 5. Saving

Follow existing save authorization. Put the inventory, extraction, and guide in the user-specified or project-approved output directory. Do not initialize personal research records to produce public web content. To update an existing AI primary note, use reading_record and protect annotations and version coverage. If a complete guide incorporates an old version, do not merely change its version label and call the new version complete.

reading_record.py --source-version currently accepts only arXiv vN. For non-arXiv PDFs, keep DOI, version description, and file fingerprint in the review inventory and source line; omit that option in save-note. Do not fabricate vN or pass published. The absence of an arXiv version number in the primary record does not replace material traceability in the inventory.

A guide may be delivered as “complete” only when identity/version are fixed; body and necessary assets have no material coverage gaps; cross-section relationships explain the taxonomy and differences; core content is reconciled before and after compression; source verification passes; and a reader-facing review passes. Matrices, combined extractions, or another structure suited to the paper are all acceptable. A successful inventory check cannot replace content criteria. If they are unmet, preserve progress within the authorized scope and deliver a partial guide.
