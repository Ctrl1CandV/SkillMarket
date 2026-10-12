---
name: presentation-craft
description: Create or improve complete slide decks for lab meetings, paper presentations, courses, and other live talks. Organize material and evidence, design layouts, create editable PPTX files, basic click animations, or web presentations with free local tools, and inspect the actual output. Use when the user requests a presentable deliverable, not when they only want tools found or an ordinary article written.
---

# Presentation Craft

The goal is a finished deck with trustworthy content, a complete narrative, readability on a projector, and visual polish. Use the host's existing AI and free local authoring and rendering tools; do not depend on additional paid APIs, asset libraries, or cloud quotas. Free software does not mean the host's AI quota is free, and open-source models do not all have the same reliability.

## Receive the task

Read the materials and explicit requirements. Confirm the audience, purpose, duration, playback software, output format, language, evidence that must appear, and visual references. Ask only when missing information would materially change the content or deliverable; otherwise use and explain a reversible default. If unspecified, use Chinese, a 16:9 aspect ratio, a fully editable PPTX, and rebuildable source files. For a live presentation, add basic click-to-reveal animations on slides where staged explanation helps; keep other slides static. Follow a request for static slides. Choose the slide count based on the material and duration rather than forcing a template or fixed length.

If the user asks only for an outline, design, or local edits, stay within that scope. Before editing an existing file, preserve a copy. Change only the requested content and necessary related slides; do not re-extract all source material.

## Choose tools for the deliverable

Read [Toolchains and Runtime](references/toolchains.md) and check which dependencies are available:

```text
python scripts/doctor.py
```

- By default, use PptxGenJS to create the PPTX directly; it suits native text, tables, charts, and later editing.
- For basic item-by-item reveals, sequential images, or staged process explanations, prefer native PPTX animations. Read [Basic Motion](references/basic-motion.md) and add appear or fade effects for deliberate content steps after generating the deck. Do not switch the deliverable to a website, PDF, or multiple static copies just because basic animation is needed.
- For equations, code, interactivity, or web visuals that matter more, consider Slidev; deliver an actual PPTX/PDF or an offline website the user accepts.
- If the user provides a template, preserve its master, fonts, and content structure where possible to avoid needless loss during conversion.
- Do not run multiple generation engines just to complete the process. An image-based PPTX can suit fixed display, but do not present full-slide images as an editable deck when the user asked for editability. Explain actual editing limits for complex shapes and equations.

Reuse the host runtime where possible. Keep code, assets, and QA in the task directory, not in the skill directory. If a tool is missing, install the smallest free dependency into the task or a dedicated environment, subject to host permissions; do not change global configuration to bypass restrictions. No additional plugin, permanent MCP service, browser account, or cloud subscription is needed.

## From materials to design

1. **Build the argument.** Read [Story and Evidence](references/story-and-evidence.md) and organize the central question, narrative order, key figures and tables, conclusions, and limitations. Give every slide a purpose, a one-sentence point, and supporting evidence. Put detailed explanations in speaker notes or an appendix. If the user has detailed requirements, retain a coverage table so required content is not omitted for appearance.
2. **Set the visual direction.** Read [Design](references/design.md); use [Style Directions](references/styles.md) when a choice is needed. This skill does not require a palette or fixed template; examples show only one possible direction. Use references that can actually be viewed and identify their role. If none are available, choose a reasonable direction for the material and do not claim comparison with a benchmark. Test the direction on realistic long headings, mixed Chinese and English text, and the densest evidence slide before extending it across the deck. If the direction is already clear, proceed directly.
3. **Create the deliverable.** Let evidence and reading order determine layouts. Keep typography, color, spacing, and chart semantics consistent across the deck while varying composition according to each slide's purpose. Use real data or original charts. Do not redraw original research figures with generative tools in a way that changes values. Preserve citations, captions, units, error values, and necessary explanations. Use decorative assets only when they serve a clear purpose.

## Review the actual output

Use [Quality Checks](references/quality.md) to inspect content, visuals, and exports separately. Add animations to the final file, then review it again. The following scripts are deterministic helpers; they do not judge academic truth or aesthetics and do not replace inspecting images and playback.

```text
python scripts/audit_pptx.py task/deck.pptx --report task/qa/audit.json
python scripts/render_pptx.py task/deck.pptx --out-dir task/qa/render-01
```

Inspect the rendered image for every slide. Also review a thumbnail overview for pacing, style, and repeated layouts. Distinguish defects that block reading, major visual gaps, and personal preferences. Fix missing or clipped text, overlap, and data or citation errors first; then improve composition, hierarchy, image quality, and visual consistency. Avoiding overflow is only a baseline, not proof of visual appeal.

After revisions, regenerate the file and review affected slides. The final review must match the final deliverable. Record results in `qa/review.json` in the format specified by the quality reference. For a PPTX deliverable, you can verify that the evidence matches the current file:

```text
python scripts/finalize.py task/deck.pptx --audit task/qa/audit.json --render task/qa/render-01/manifest.json --review task/qa/review.json --report task/qa/final.json
```

Do not fabricate visual inspection records or alter check results to bypass a known defect. If a tool is unavailable, use a feasible free alternative. If the actual deliverable still cannot be rendered, say that visual verification is incomplete; do not claim a browser preview or XML check passed export verification. A user who explicitly accepts a draft may receive one with accurate limitations; do not call it complete.

For an animated deck, inspect the initial state, every click, returning, and replay during actual playback. Static PDF/PNG, XML nodes, or successful import into presentation software do not replace playback checks. Record what was actually checked and clearly state anything not verified because playback was unavailable.

## Delivery

Provide the requested final format and enough source files and local assets to rebuild or continue editing. Usually the PPTX and source file are sufficient; provide PDF, thumbnail overview, and appendix as requested or needed. Keep QA and experiment files in the task directory instead of giving the user all of them.

Briefly explain content and design choices, actual editability, checks performed, and remaining limitations. A successful generation alone does not guarantee that “everything looks good”; report what the actual deliverable supports and do not give unsupported overall scores or guarantees.
