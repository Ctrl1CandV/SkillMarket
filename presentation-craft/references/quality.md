# Content, Visual, and Delivery Checks

## Distinguish review evidence

| Check | What it can confirm | What it cannot replace |
| --- | --- | --- |
| Source materials and full-text review | Coverage of requirements, facts, units, citations, order, notes, and caveats | Visual inspection of the actual output |
| PPTX structural review | Content inventory, obvious overflow, missing media, empty slides, and indicators of native/image slides | Actual text layout, projection readability, authenticity, and aesthetics |
| Rendering the actual file and inspecting images | Missing glyphs, clipping, overlap, layout, chart readability, and deck-wide style | User approval or consistency across every Office/font environment |
| Actual slide show | Initial hidden state, click order, grouped reveal, return, and replay | Static screenshots, XML animation nodes, or software import recognition alone |

Structural review returns a list of issues. A `warning` is a clue to interpret, not automatically a defect; for example, a large background or decorative object outside the page, dense text, or image-based slides. Fix serious problems and review again. Do not remove content or alter statistical presentation just to eliminate a warning.

## Inspect rendered slides

Inspect the real render of every slide and zoom into dense pages. A thumbnail overview helps review composition and consistency, but cannot replace reading each slide. If there are too many slides, review in batches; do not claim full review based on a sample.

Check whether the main point and charts are readable in the presentation setting; whether mixed Chinese and English causes excessive wrapping; whether titles collide with content; whether captions and sources are attached to evidence; and whether table rows and columns, units, color meanings, and source image crops are correct. Then review visual weight, hierarchy, empty space, image quality, type, palette, and composition rhythm. If there is no external reference, label aesthetic conclusions as your own design judgment.

When you find an issue, record the slide and specific impact, revise it, and generate the output again. Review the final exported file. If you change shared fonts, the theme, or chart styling, recheck every affected slide.

## Keep a short review record

`render_pptx.py` creates a `manifest.json` containing the input file hash, PDF hash, and image hash for each slide. After inspecting the rendered pages, write `qa/review.json` in the task directory, not the skill directory. This is a model review record, not an automated visual score. The fields below are examples; actual hashes and page counts must come from the real output, not copied from this sample.

```json
{
  "deck_sha256": "SHA256 of the actual PPTX",
  "content_review": {
    "status": "pass",
    "summary": "Requirements and sources were checked; there is no unlabelled demo data."
  },
  "pages": [
    {
      "page": 1,
      "status": "pass",
      "summary": "Inspected the actual export; the title and evidence are clear, with no clipping or overlap."
    }
  ]
}
```

Use `pass` or `needs_fix` for `status`. Each page summary should report the actual result, rather than mechanically repeating one sentence. Use `needs_fix` for unresolved defects. An old review is no longer valid after the source or output changes.

## Final verification

`scripts/finalize.py` checks whether the current PPTX, structural review, render, and review record are consistent, whether every slide is recorded as passing, and whether the PDF/images still match the reviewed version. Animated or transitioned files also require an actual slide-show record; see [basic animation](basic-motion.md). This script cannot prove that the model really looked at the images or played the deck, and cannot prove that its judgments are correct. Do not edit the record to bypass a real defect.

If the script reports `complete: true`, the evidence chain is complete. In the user response, still accurately state the review scope and subjective judgments. Do not call it independent human acceptance or a 100% quality guarantee. Preserve accurate failure information when rendering is unreliable, key sources are missing, or user requirements are not covered; deliver a labelled draft only if the user explicitly accepts it.
