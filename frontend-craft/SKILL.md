---
name: frontend-craft
description: Design and improve attractive, polished, usable web interfaces. Use for product sites, business tools, data interfaces, landing pages, long-form reading pages, and requests such as “the front end looks bad,” “the information is disorganized,” “Chinese text is hard to read,” “it looks like a template,” or “it does not work well on phones.” First clarify content relationships and spatial structure, then use typography, color, and assets to create a coherent visual result. Improve quality by inspecting references, designing directions, and reviewing actual screenshots. In local refinements, preserve specified branding and existing behavior. Not for back-end-only tasks, copy polishing alone, or direct PDF generation; hand off native apps and document layout to specialized skills.
---

# Frontend Craft

Version 0.2.0

Visual appeal and polish are core goals; readability, operability, and correct behavior are minimum requirements, not the whole objective. Design in sequence: understand content relationships, choose a spatial structure, test it with real content, create the visual result with typography, color, and assets, then refine it on narrow screens and through real interactions. Layout comes before styling, but styling is not decoration at the end: decisions about type, color, and assets distinguish a finished page from a wireframe. Tools should also show visual judgment; restraint need not be bland. A correct layout is not automatically attractive—the final composition still needs to be inspected.

## Set the scope for this task

Read the user's request, relevant pages, existing components, and styles. Then briefly state:

- Who uses the page and in what context; what primary task does the page help them complete?
- Which content, behavior, routes, records, and branding must be preserved; which files may change?
- Where the content and data come from; which items are explicitly marked as test examples?
- The role of each reference: business or content references provide entities, workflows, and copy; positive visual references show qualities to learn from; negative examples show specific problems to avoid. One project may serve multiple roles; identify each role separately. An old project does not imply approval of its appearance, and its implementation does not automatically constrain the visual direction.
- The primary devices and checks feasible for this task; state missing facts as assumptions and do not invent aesthetic preferences.

For a local refinement, inspect only the target and adjacent areas, skipping process steps unrelated to this change: if the structure stays the same, do not rearrange it; if only colors change, do not redo the layout. A redesign follows the full process. Ask only when missing information would affect an irreversible decision; otherwise use and explain a reversible default. Do not install dependencies, change the stack, write to personal records, or publish without authorization.

## Load only the relevant parts of the guide

| Current need | Read first |
| --- | --- |
| Grouping, structure, proportions, spacing, or rearranging any interface | [Layout](references/layout.md) |
| Typography, color, assets, or detailed styling | [Visual Style](references/visual-style.md) |
| Research platforms, tables, filters, dashboards, or dense operations | [Workspace Interfaces](references/workspaces.md) |
| Marketing, campaigns, product descriptions, or conversion | [Landing Pages](references/landing.md) |
| Long Chinese text, paper guides, contents, and sources | [Reading Pages](references/reading.md) |
| Any implementation or acceptance check | [Quality and Evidence](references/verification.md) |
| Native apps, PDFs, or cross-media requests | [Boundaries and Handoffs](references/boundaries.md) |
| Ownership and licenses for external components, images, fonts, or methods | [Sources and Licenses](references/sources.md) |

For mixed pages, assign tasks by section. For example, a research platform homepage helps users find an entry point while the paper itself is for reading; do not apply a marketing page's oversized heading and empty space to either.

## Main workflow

### 1. Inspect the current page and references; identify the task and visual problems

For an existing page, capture a real baseline screenshot and key interaction paths. Distinguish observable problems, inferences from source code, and personal preferences. State the evidence and impact, such as “the shortcut text turns white on hover but the background remains light, reducing contrast,” rather than “it lacks polish.” If old pages remain in source, confirm the actual route before reviewing so dead code is not mistaken for the current page.

Inspect actual positive reference images; do not rely only on source code or assumptions based on a project name. Analyze the composition's focal point, proportions of primary and secondary areas, type roles and scale, density and rhythm, color coverage, asset choice and cropping, and how borders, icons, and shadows work together. Explain what suits the current content and what should not be copied. Break down negative examples too, but turn their problems into avoidance criteria instead of copying their layout and reskinning it. If no reference can be inspected, state that limitation and proceed with a provisional direction; do not claim to have compared against a benchmark.

Separate blocking defects, lack of visual polish, and brand drift. First remove issues that prevent use, then address unbalanced proportions, flat hierarchy, weak rhythm, and rough details. Familiar interaction patterns may remain without retaining the old visual style.

### 2. Organize content relationships

Use real content to identify the main object and task, related information that must be seen together, supporting material shown as needed, and local versus global actions. Let the task determine what must remain on screen and what may be collapsed or split into steps; priorities may change by task stage and are not the same as heading levels. Keep related information adjacent because incorrect grouping can mislead actions. Do not delete or downplay supplied facts, functions, or data to make the composition look cleaner. If grouping is unclear, return to the user's task instead of dividing content by data field.

### 3. Choose a spatial structure and allocate room

Choose an organization based on the relationships: continuous reading, a list with details, a comparison table, main content with a support panel, a step-by-step flow, or an exploratory feed. These are options, not a template catalog. They can be combined, but each section must have a clear purpose. First determine the space needed for body text, tables, media, and long content; then allocate room for navigation and supporting areas. Explain what stays fixed, what expands, and what gives way when space is limited. Use a small set of spacing values to show relationships within groups, between groups, and across sections. Prefer alignment and whitespace over borders when they suffice. Do not enforce fixed proportions or column counts, or start from a standard admin shell. Cards, sidebars, and tables are useful when grouping, comparison, or boundaries call for them; do not ban them merely to avoid templates. Reserve room for important images and charts at this stage. See [Layout](references/layout.md) for methods and examples.

### 4. Test with real content at low styling, then choose a representative page

For a new page or full redesign with an unclear direction, create low-cost structural alternatives before deciding. They should differ meaningfully in grouping, primary-object placement, primary-to-secondary proportions, or reading order—not just in their skin. Compare alternatives only when there is a genuine trade-off, such as quick comparison in a list versus reading grouped items individually. If the direction is clear, create one design; there is no required number of options. Keep the same base typography, colors, and assets across alternatives. Include real text lengths and necessary type hierarchy instead of drawing only gray boxes; grayscale or reduced color can help inspect structure, but comparisons must still show structural differences. Skip alternatives for local refinements and inspect the actual page directly. If the user gives no feedback, choose based on the task and visual evidence. Label the choice as a design judgment; do not record it as a user preference.

Implement a representative page and key path that express the direction and expose difficult content. Use realistic Chinese headings, English terms, data, and error messages; short placeholder text must not conceal layout problems. If production data is unavailable, label examples as samples and do not present them as the user's progress, customer reviews, or achievements. List key states and implement those needed: default, hover, focus, selected, loading, empty, error, disabled, success, and long content. Errors should preserve input and offer a recovery action. “Saved successfully” requires real save and reload evidence. Clearly label a sample without a back end as an in-page demonstration only.

### 5. Finish the visual design after the structure works

Styling should reinforce the hierarchy established in steps 2–3, not start a new layout. Turn words such as “refined” and “restrained” into decisions that can be checked in the composition:

- **Typography:** Assign roles and weights for headings, body text, metadata, numbers, and controls. Compare samples with realistic long content before deciding; declaring a font does not prove it actually loaded.
- **Color:** Give hierarchy colors, semantic colors, and one primary accent distinct roles. Use the accent's coverage and contrast to direct attention to the current task; do not let it drift across unrelated areas. Check contrast on the actual background.
- **Assets:** Decide what information or mood each asset serves, test candidates at their final size, then choose. Do not fill space with unrelated decoration or ban expressive visuals in the name of restraint.
- **Details:** Use a small, consistent set of border, radius, shadow, and icon-alignment values.

Express colors, type sizes, and spacing as a small set of variables. Reuse existing variables only when they fit the direction, and retain branding the user explicitly specified. See [Visual Style](references/visual-style.md) for methods.

### 6. Inspect actual results and refine by layer

Load the host's official browser skill and use supported operations to open the page. Confirm the DOM and state, then inspect real screenshots on desktop and narrow screens. On long pages, inspect lower sections; check Chinese line wrapping and keyboard navigation. Record the version, viewport, route, and state for each screenshot. A generated image of an interface is not evidence that the page runs.

A narrow screen requires reorganizing the task, not scaling everything down proportionally. Check whether related groups were split apart, actions moved too far from their objects, and selected items, filters, or reading position can be preserved. A support panel may become a drawer, a step, or a section below the main content; whether a list remains depends on the task.

Review screenshots of the representative page alongside positive references. Check structure (relative importance, reading order, and density) and styling (typographic rhythm, color coverage, asset quality, and consistency of detail). Compare visual polish, not pixel-level duplication, and explain differences in content and viewport. Use negative examples to confirm that their specific problems were avoided, not as similarity targets. In each round, list a few of the largest remaining gaps and identify their layer: if the structure fails, revisit steps 2–3; if typography or assets fail, reconsider their roles; if details fail, make local changes. Fix task blockers and reading problems first, then major visual gaps, and recheck affected areas. Do not force unnecessary cycles to complete a process, but do not stop merely because nothing overflows.

If you have only a small prototype, static test, or build result, do not call it a “visual pass.” Self-review is not user acceptance and does not prove benchmark-level quality. If the tool is unavailable, preserve the exact error and list what remains to be verified; do not treat a judge using a different medium as Web acceptance.

### 7. Deliver a limited, honest result

Explain the changes, reasons for the choices, checks completed, checks not completed, and remaining work. Save evidence using the organization already present in the task directory; do not modify an installed skill. Without authorization, do not write an extra long report or create a Git commit.

Example delivery:

> Preserved the paper filters and record format while regrouping headings, sources, and actions. Sources no longer compete with the paper body for the main column, and actions stay with their item. At 390px, filters become an expandable section and selected filters remain visible. Checked samples of mixed Chinese and English typography; the accent color now marks only the active filter. Verified empty-filter behavior and error recovery. Reviewed desktop and narrow-screen screenshots. Keyboard navigation and 200% zoom were not checked, so this is not a claim of full-device acceptance.
