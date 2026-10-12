# Basic Native PPTX Animation

The goal is step-by-step explanation in an ordinary presentation: a click reveals the next point, image, or process step. Use appear by default; use a short fade when a softer entrance is useful. Titles, backgrounds, page numbers, and essential context should already be visible when a slide opens. Let the content determine the number of clicks. Do not animate every decorative element or enable automatic slide advance by default.

## Workflow

When body points should appear one at a time, make each point a separate native text box. The helper script animates objects; multiple paragraphs inside one text box appear together. It does not build text paragraph by paragraph. Keep charts as native charts and reveal each as a complete object; the script does not animate chart series. Related text, shapes, arrows, and captions in one step may appear together.

After laying out the deck with PptxGenJS, run `scripts/animate_pptx.py`. The script uses only the Python standard library to write a standard animation timeline into the PPTX. It does not call PowerPoint, a cloud model, or a paid API, and it does not turn slides into images. The input is not overwritten; untouched slides, images, charts, and notes remain unchanged.

First list the top-level object IDs and text in the current file; do not guess IDs:

```text
python scripts/animate_pptx.py task/deck.pptx --list
```

Create `task/motion.json` for slides that need step-by-step builds. In this example, replace the page numbers and IDs with real objects. Each inner list in `steps` represents one click; objects in the same step appear together:

```json
{
  "slides": [
    {"page": 2, "effect": "appear", "steps": [[8, 9], [10], [11, 12]]},
    {"page": 3, "effect": "fade", "duration_ms": 300, "steps": [[7], [8, 9]]}
  ]
}
```

```text
python scripts/animate_pptx.py task/deck.pptx --plan task/motion.json --output task/deck-animated.pptx
```

Review and render the final animated file. Deliver the animated file, source deck, assets, and click plan. Supported top-level objects include text, shapes, images, charts/tables, and groups. To control group members separately, change the grouping during authoring. Object IDs must be unique, and each object may appear in only one reveal step. Slides with existing animations are rejected to avoid overwriting the user's animation; use the original authoring tool to preserve or edit that timeline. The tool supports UTF-8 XML, appear, and fade only. It does not claim to support exits, motion paths, Morph, or complex triggers.

## Review and limits

Structural review counts animations and checks object references. Also open the final file in the presentation software and run the slide show. Verify that unrevealed objects start hidden, one click starts only the next step, grouped objects appear together, navigation works after the final step, and returning to or replaying the slide works.

Add actual slide-show results to `qa/review.json`, with `pages` covering every slide that has animations or transitions:

```json
{
  "animation_review": {
    "status": "pass",
    "method": "slideshow",
    "player": "Name and version of the software actually used",
    "pages": [2, 3],
    "summary": "Record actual checks of initial visibility, click order, grouped reveals, return, and replay."
  }
}
```

Do not set `method: slideshow` or mark the review passed if you only checked import recognition or XML. `finalize.py` requires a slide-show record for animated files; a static preview cannot stand in for animation verification. Support varies across PowerPoint, WPS, and Impress versions, so report the software actually tested and any remaining limits. A PDF is a reading/layout preview, not a substitute for an animated PPTX. Do not replace requested object animation with a series of static slides.

Standards references: [Microsoft PresentationML ShapeTarget](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.presentation.shapetarget) and [PowerPoint Effect](https://learn.microsoft.com/en-us/office/vba/api/powerpoint.effect). The division between native animation and generation tools was also informed by [pptx-motion-lite](https://github.com/yinzige/pptx-motion-lite). This script is an independent implementation limited to appear/fade and explicit click plans; it does not depend on or bundle that skill.
