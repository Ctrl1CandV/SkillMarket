# Venue Rules Reference (submission-gate)

> **Rules change.** Each rule includes a source and verification date. **Recheck the official site within two weeks of the deadline.** This file is a starting point, not an authority. Update it and the verification date if a rule is outdated.

Verification dates: 2026-08-22 (research finalized) and 2026-08-23 (ARR page rechecked).

## Hard rules

| Venue | Main-text page limit | Hard rule (consequence) | Source |
|---|---|---|---|
| ICLR 2026/2027 | 9 pages at submission; 10 pages for rebuttal/camera-ready | Over length may be desk-rejected; references excluded. **Disclose LLM use; undisclosed substantial use may be desk-rejected** (new in 2026). | iclr.cc/Conferences/2026/AuthorGuide, iclr.cc/Conferences/2027/CallForPapers |
| NeurIPS 2025 | 9 pages including figures and tables | **Missing paper checklist means desk rejection**; margin/font changes may lead to “rejection without further review.” | neurips.cc/Conferences/2025/CallForPapers, neurips.cc/public/guides/PaperChecklist |
| ICML 2026 | **8 pages** | Noncompliance with policy may be “rejected without review.” | icml.cc/Conferences/2026/CallForPapers |
| ACL/ARR | Long paper: 8 pages; short paper: 4 pages (ethics considerations and Limitations are **excluded**, confirmed in source) | **Putting related work only in the appendix to evade the limit may cause desk rejection**; Limitations is required; egregious checklist violations may be desk-rejected since 2024-12. | aclrollingreview.org/authors, /reviewerguidelines |
| AAAI | **Not verified**; check the official CFP before using a page limit | Only submission volume is known: about 23,000 papers for AAAI 2026 (papercopilot). | Check ojs.aaai.org at time of use. |

## Itemized checklist

Produce two sections: “Automatically checked” and “Needs manual confirmation.”

1. **Page count:** Check automatically when a readable PDF is available; if not readable, mark “Needs manual confirmation.” Do not guess.
2. **Checklist presence:** NeurIPS requires one; ARR requires the Responsible NLP checklist.
3. **Limitations presence:** Required for ARR and excluded from its page limit.
4. **Related work in the body:** For ARR, putting it only in the appendix may cause desk rejection.
5. **Anonymity:** Search the body/PDF for author names, acknowledgments, grant numbers, personal repository links, and file metadata (PDF author field).
6. **LLM-use disclosure:** Undisclosed substantial use may be desk-rejected for ICLR from 2026; writing assistance generally needs disclosure. Follow the current CFP wording.
7. **Template unchanged:** Manually compare or diff margins, font sizes, and line spacing with the official template.
8. **File size/format:** Follow the current submission system requirements.

## Review and rebuttal mechanics

- **ARR area chairs are asked to read only approximately the first two author-response comments in each reviewer thread.** Put the strongest argument first; do not respond in reviewer-comment order.
- **Newcomers are exempt from reciprocal reviewing:** ICLR says, “If none of the authors are qualified under this definition, then they are exempt from this requirement.” Student/faculty teams without a top-conference paper need not worry about this requirement.
- See `arr-h-list.md` in this directory for how to classify invalid criticisms and valid weaknesses.

## Acceptance-rate context

Use this only to calibrate expectations when choosing a submission path, not as a decision rule.

| Conference | Latest edition | Acceptance rate |
|---|---|---|
| ICLR 2026 | 19,814 submissions | 26.95% (in 2022: 3,422 submissions / 32.00%; 5.8× submission volume over five years) |
| ACL 2025 | 8,360 submissions | 36.97%, with Findings as an additional route |

Source: papercopilot.com/statistics. For a first paper, the ACL/ARR route may offer higher expected output, and the first topic in the ACL 2026 list was “AI/LLM Agents.”

## Boundary

This skill checks explicit rules and provides evidence. **People make the decision.** It reports “compliant / non-compliant / needs manual confirmation” with the source text; it does not predict “accepted / rejected.”
