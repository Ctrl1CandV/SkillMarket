---
name: thesis-cn
description: Compliance checks for Chinese-language degree theses, including consistency between Chinese and English abstracts, GB/T 7714 references, section numbering, figure and table lists, and compliant writing-quality feedback. Trigger words include degree thesis, graduation thesis, Chinese thesis, dissertation, abstract consistency, reference format, GB/T 7714, figure and table list, and plagiarism risk. Does not help evade AI-generated-content detection. Read institution-specific thresholds from user configuration; never hardcode them.
license: MIT
---

# thesis-cn: Compliance Checks for Chinese-Language Theses

Chinese-language degree theses and conference papers follow different requirements: GB/T 7714, Chinese and English abstracts, and institution-specific formatting rules. This skill performs mechanical checks and compliance-focused feedback.

**Institution-specific rules have not been verified:** the Chongqing University of Posts and Telecommunications graduate-school website was unavailable during research, and no primary source was found for plagiarism thresholds or detailed formatting templates. Therefore, read these values from `.grad/config.json`. **Guide the user to fill them in on first use.** For unset values, write null and state “Not configured; unable to check this item.” Never guess or hardcode them:

```json
"thesis_rules": {
  "duplicate_check_threshold": null,
  "format_template_ref": null,
  "other_school_rules": {}
}
```

## State clearly what this skill does not do

**Do not lower AI-detection rates or help evade plagiarism checks.** Some community projects with 500+ stars pursue those aims, but that is an ethically questionable direction and separate from making a thesis clear. This skill improves compliance and points out verifiable writing-quality issues, such as long direct quotations without citations, incomplete paraphrasing, and inconsistent terminology. Fixing these may reduce plagiarism risk as a side effect; it is not the goal.

## Path placeholder

`{SKILL_DIR}` is the absolute path to the directory containing this SKILL.md; the caller expands it.

## Workflow

### 1. Institution rules

Read `thesis_rules` from `.grad/config.json`. If it is missing, generate a template for the user to complete. Mark every unset item “Not checked (not configured)” in the resulting report.

### 2. Consistency between Chinese and English abstracts

Compare each item:

- **Terminology alignment:** Match specialized terms consistently across languages (for example, use “agent” consistently for intelligent-agent concepts and distinguish retrieval augmentation from retrieval-augmented generation (RAG)). Inconsistent translations of the same concept are a common problem.
- **Same number of contributions:** Three items in Chinese and two in English is a mismatch; compare them one by one.
- **Compare every number:** Experimental values, including decimal places in percentages, must match in both abstracts.
- Differences in tense and voice are normal (English often uses past tense) and do not count as inconsistencies.

### 3. Reference formatting

**Read `{SKILL_DIR}/references/gbt7714.md`.** Version rule F05: GB/T 7714-2025 fully replaced the 2015 edition on 2026-07-01 (official metadata was checked), but the current reference document is based on the 2015 edition and marked `legacy_2015`. Until the official 2025 text is obtained, each reported item must say “Based on the 2015 edition rules; the corresponding 2025 rule remains to be checked.” **Do not claim compliance with the 2025 edition, and do not classify unknown rules as definite violations.** If the institution has a formal template or detailed rules with a real source in `thesis_rules`, those take precedence. Check the bibliography item by item and report the item number, issue, and suggested correction. Deduplicate by DOI or title first. Check arXiv citations separately; they are electronic resources, not journal articles.

### 4. Sections, figures, and tables

- Check three-level section numbering (1 / 1.1 / 1.1.1) and report skipped or duplicated numbers.
- Number figures and tables by chapter (for example, Figure 2-3 and Table 3-1; follow the institution's template).
- **Generate the lists of figures and tables:** extract all figure and table captions from the body and create list pages after the table of contents.

### 5. Compliance-focused writing-quality feedback

Report only verifiable issues: more than N consecutive sentences share wording with a source without direct-quotation marking; a paraphrase retains the source's sentence structure; or key terminology is inconsistent throughout. Include a location and evidence with every item. Rewriting methods and organization are the responsibility of the academic-writing skill; if available, refer the user to it instead of repeating its content.

## Output format

```markdown
# Thesis Compliance Report · YYYY-MM-DD
## Abstract consistency (n items)
- ❌ Contribution count: 3 in Chinese / 2 in English — the third Chinese item is ...
## Reference formatting (n items)
- ❌ [12] Conference paper marked [J]; should be [C]//...
## Sections, figures, and tables
- ⚠️ Figure 3-2 is missing from the list.
## Writing quality
- ⚠️ Four consecutive sentences in `2.3 closely match [source]; no citation was found.
## Not checked
- Plagiarism threshold (not configured)
```

Report findings only; the user makes edits. Judgment belongs to people.
