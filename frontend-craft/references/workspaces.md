# Content- and Operation-Oriented Interfaces

Help people find objects, compare information, and complete actions efficiently while delivering a polished tool experience. This is not a marketing showcase, but “usable” alone does not mean “well designed.”

- Extract proportions, typography hierarchy, color coverage, and detail precision from positive visual references, then adapt them to current information density. Business references and old admin tools do not define appearance automatically.
- Precision comes from proportion, alignment, spacing rhythm, and details—not uniform type size, gray boxes, or low contrast. Build a representative page and inspect it beside the benchmark. Preserve familiar interactions without mechanically keeping the old skin.
- List actual entities and relationships: orders, customers, inventory, tasks, documents, and so on. Separate system recommendations from user status. Do not display unknown values as 0% or unsaved changes as success.
- Use stable rows/columns and positions for high-frequency objects so returning users can predict where information is. Choose structure using [Layout](layout.md).
- A home page should provide one trustworthy entry point and searchable objects. Grouping should aid selection, not repeat the entire sidebar. If new and returning users need different content, base it on actual state, not guesses.
- Place toolbars near the objects they affect. State filter scope, current count, and how to clear it. “No filter results” and “no data” are different empty states. A failed update must not become an empty result.
- When text is unreadable, first adjust column width, hierarchy, and content grouping before reducing font size. Do not use 12px metadata for a long passage carrying a conclusion. Aim for 44px for common interaction targets. The WCAG 2.2 AA 24px minimum target criterion includes exceptions and spacing; do not confuse it with the same standard.
- Dense does not mean crowded: reduce repeated containers and unify row spacing while preserving group gaps. Do not make content “fit” by shrinking text, lowering contrast, or banning line wrapping.
- When graphics express relationships, provide a text alternative and explain the relationship. Distinguish source relationships from recommended reading order. Do not try to solve an unreadable graphic solely by infinite zoom.

## Representative interaction path

Search for an object → see the match count → open details/evidence → return to the original filter position. Check long names and mixed Chinese/English, no results, clearing, and retry after a load failure. If the page saves changes, also test save → reload/read back → failure preserves the content.

shadcn data-table may inform composition on demand and Radix may inform focus behavior, but check components already in the project first. Native input, button, and details may suffice; do not install React/Tailwind for a small prototype.
