# Quality and Evidence

## Keep four kinds of conclusions separate

1. **Source review:** rules, structure, routes, and state implementation.
2. **Automated checks:** builds, unit tests, HTML links/dependencies, and contrast calculations.
3. **Actual use:** real browser clicks, keyboard, loading, and recovery.
4. **Visual review:** judgment of layout, hierarchy, Chinese text, and assets after inspecting real screenshots.

These are complementary; none substitutes for another. If there was no independent review, call it self-review. If there was no browser, say verification is pending. Do not invent scores.

## Minimum verification matrix

| Dimension | Default check | Observable pass condition |
|---|---|---|
| Desktop | 1280×800 or the project's primary viewport | Main task is clear; no obstruction or unexplained empty space; rows/columns are organized. |
| Phone | 390×844; use 320px width when needed | No unexpected horizontal scrolling; content and actions remain available. |
| Text zoom | 200%; test 400% reflow when needed | Controls/content are reachable; local two-dimensional scrolling is allowed where appropriate. |
| Keyboard | Tab/Shift+Tab, Enter/Space, Escape when applicable | Focus is visible and ordered meaningfully; dialog focus returns correctly. |
| States | Loading, empty, error, selected, success, disabled | Copy matches the real state; failures recover; user input is not lost. |
| Accessibility | Labels, semantics, image alternatives, color, motion preferences | Meaning does not rely on color alone; automated scans are not presented as full certification. |
| Long content | Longest title, mixed-language text, long lists, bottom of page | Important content is not clipped; text is not shrunk just to pass. |

Scale checks to the task; do not retest the whole site for a spacing-only change. Target WCAG AA contrast of 4.5:1 for body text and 3:1 for large text (18pt or 14pt bold, not a vague “18px”). Aim for 3:1 for necessary control boundaries/state information, applying the actual success criterion. Focus, hover, and disabled states have separate applicable conditions; do not check only default colors.

## Review visual polish

A usability matrix is a baseline, not a substitute for visual acceptance. Inspect screenshots of a representative page alongside positive references and record each gap and next correction:

- **Composition and proportions:** primary/secondary area, focal point, and whether the first screen and later sections form a coherent page rather than a stack of containers.
- **Typography and rhythm:** scale relationships, weight, line length, line spacing, and group spacing for headings/body/metadata; enough density variation without losing order.
- **Color and assets:** whether color coverage and emphasis are appropriate; consistency of style, clarity, and cropping for images/charts/icons; for a text-only page, whether the typography itself is expressive.
- **Details:** accuracy and consistency of borders, radii, shadows, icon baselines, controls, and states, including at narrow widths.

Use positive references to compare visual quality, not to require copying their layout/assets. Use negative examples to check whether the rejected problems remain. Compare before/after evidence with the same content, viewport, and state; explain differences when comparing across projects. Name actual strengths and gaps from the composition instead of claiming benchmark quality based on rule count, a successful build, or an invented score. If no screenshots were viewed, say “visual review not performed.” If they were viewed but not approved by the user, say “visual self-review,” not “user accepted.”

Handle gaps by layer: return to layout when structure fails (reversed priority, misleading grouping, broken reading order, or split relationships on mobile); use [Visual Style](visual-style.md) for styling issues (type roles, color coverage, asset quality, detail scale); fix isolated detail issues locally. Judge structure by whether a real reader can quickly identify the right priority and grouping, not whether the designer can explain it. Do not require proof of an aesthetic score. After a local fix, inspect affected and adjacent areas; do not retest the whole site just to complete a process.

## Close the evidence loop

Load the official browser skill → check the target page → capture a snapshot of content/state → perform real actions → observe state → inspect a screenshot when visual judgment is needed → record findings → fix → capture/recheck the same state. Follow the official skill's browser limits; do not open an unauthorized automation back door.

For every check, retain version/file hash, page, viewport, data/state, action, observation, evidence file or session call, and conclusion. The existence of a screenshot file does not prove it was inspected. Before/after images need matching content, viewport, and state; a screenshot of a different page cannot prove improvement.

Example blocker record: “Official browser returned Browser is not available in subagent; no screenshot was captured; 390/1280 viewport, keyboard, and interactions await verification in the main session. Completed static checks do not change this status.”

Report performance only from actual tool results; do not claim Core Web Vitals passed because no external dependency was added. Do not upload screenshots with private data to external services. Do not use a document-only visual judge for Web; for PDFs follow the PDF skill's rendering checks.
