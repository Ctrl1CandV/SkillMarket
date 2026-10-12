# Free Tools and Runtime

## Choosing dependencies

Prefer a document or slide runtime already provided by the host. In Codex desktop, call `load_workspace_dependencies` and use the returned Node, Python, and package paths. Other hosts should use existing environments or task-local dependencies. Do not put one machine's absolute path into source files or skills.

`scripts/doctor.py` reports whether Node, PptxGenJS, python-pptx, LibreOffice, and PDF rasterization tools are available. A missing optional engine does not mean every workflow is blocked. The script does not install software, access model services, or verify generated output.

## Native PPTX workflow

PptxGenJS (MIT) creates text, shapes, tables, charts, images, and notes in JavaScript. It is suitable when the task needs an editable PPTX. Reuse an installed package; when it is actually missing, run `npm install pptxgenjs` in the task project. Do not install it globally by default.

- Set the canvas, such as `LAYOUT_WIDE` at about 13.33 × 7.5 inches, before adding slides. Use the real canvas dimensions; do not mix coordinates from other sizes.
- Define a small set of theme fonts, colors, and spacing values, then adapt individual elements to the content. Prefer native text and charts; complex system diagrams can use high-resolution or vector assets.
- Use real data in native charts. Add notes with `slide.addNotes(...)`; do not put speaker notes in slide body text.
- Write colors as six-digit hexadecimal values without `#`; do not encode transparency in the color string.
- Create new options objects for each object to avoid sharing nested objects that the library may mutate. State the actual editability limits for equations and complex diagrams.
- Wait for asynchronous `writeFile` to finish, then inspect and render the file. Deliver the JavaScript and assets actually used with rebuildable relative paths.
- PptxGenJS creating native objects does not automatically create entrance animations. For basic click-to-appear/fade, use the post-processing script in [basic animation](basic-motion.md), then inspect the final animated file. A static export is not a substitute for an animated deliverable.

For a user-provided PPTX template, `python-pptx` can make appropriate local edits. Preserve rich-text runs, original media, and layouts; do not destroy formatting by clearing whole paragraphs. Check support for complex charts, SmartArt, masters, and embedded objects before editing; do not blindly rebuild the original.

## Web workflow

Slidev (MIT) works well for equations, code, diagrams, and web-based presentations. The host AI writes Markdown, Vue/HTML, and styles; Slidev does not need its own model API. Use a user's existing Slidev project or initialize one in the task directory. First check the installed version's help and export support.

Example:

```text
npm init slidev@latest
npm install -D playwright-chromium
npm run dev
```

Export locally through the project's CLI:

```text
npx slidev export slides.md --format pdf
npx slidev export slides.md --format pptx --with-clicks false
```

A regular PPTX uses full-slide images; notes may be preserved. Official docs as of 2026-10-09 also list `--format pptx-editable`, but first confirm the local version supports it. That mode converts some objects back into native shapes; equations, SVG, canvas, and complex effects may remain images, and some slides may fall back to a full-slide image. Do not claim the whole deck is editable just because the file extension is `.pptx`.

Inspect both the web rendering and the final PPTX export. Step animations may increase the exported page count; turn off export by click steps unless the user needs a stepped copy. Ensure equations, code, and legends remain complete in the final static file.

If only an offline web deck or PDF meets the visual goal but the user requested PPTX, keep working on export. Do not substitute a link without asking. The user can choose a fixed image-based PPTX when appropriate; preserve precise data figures and source files.

## Render the actual PPTX

`scripts/render_pptx.py` converts the deck to PDF with LibreOffice, then generates actual slide PNGs with `pdftoppm`; it can also rasterize through PyMuPDF when installed. Pillow is optional for contact sheets. The script uses an isolated temporary profile and a new output directory, and does not overwrite existing QA files.

On Windows, it can locate an existing LibreOffice install automatically or accept `--soffice`. If Poppler is not on `PATH`, pass `--pdftoppm`. The first run records a new input hash and slide inventory. After edits, render into a new directory so an old preview cannot be mistaken for the latest result.

LibreOffice can render fonts and some charts differently from PowerPoint. Leave room for text and choose fonts that are actually installed. If the user gives you the final presentation environment, check key slides there. Fix or report render-conversion and font failures; a file opening successfully is not enough.

## Services not needed as core dependencies

PPTAgent's review and export workflow can be consulted, but this skill does not require its full runtime. Nature-paper2ppt offers references on academic storytelling and source tracking for original figures; it is not a mandatory shared skill. A local Presenton installation can be used when the user already has it; its cloud service and additional cloud models are not automatically free. Availability, export limits, and watermark policies for NotebookLM, Gamma, Canva, and similar services can change, so do not make any of them the only delivery path.

## Sources and limits

Verified on 2026-10-09. The workflow and helper scripts in this skill are independent implementations. They do not copy restricted Anthropic PPTX skill code or third-party skill packages. External projects do not need to be bundled with this skill.

- [PptxGenJS](https://github.com/gitbrent/PptxGenJS): native PPTX authoring, MIT.
- [Slidev export](https://sli.dev/guide/exporting): web and export formats, including image/native object limits.
- [Slidev AI support](https://sli.dev/guide/work-with-ai): official skill/MCP is optional and not required by this skill.
- [PPTAgent skill](https://github.com/icip-cas/PPTAgent/tree/main/skills/pptagent): reference for reviewing source material and final PPTX.
- [nature-paper2ppt](https://github.com/yuan1z0825/nature-skills/tree/main/skills/nature-paper2ppt): reference for academic argument, original figures, and notes.
