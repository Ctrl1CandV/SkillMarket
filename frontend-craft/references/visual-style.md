# Visual Style: Typography, Color, Assets, and Detail

Once the structure works, styling makes hierarchy visible. Styling should strengthen content relationships, not fill empty space with decoration. Restraint need not be bland, and richness need not mean clutter. Do not send a style problem back to layout first; check whether roles and scales are clear.

## Typography roles

- Assign roles to headings, body text, metadata, numbers/code, and controls: font family, weight, size, and contrast against the background. A clear type system may use one family with several weights; two type roles do not require downloading two families.
- Compare samples with the same realistic content before deciding: the longest Chinese heading, mixed Chinese/English text, body paragraphs, strings of numbers, and button labels should appear together. Compare perceived size, darkness, line width, and wrapping. A system stack can be a good choice, but choose it after seeing a sample, not without comparison.
- A declared font-family does not prove the font actually loaded. Check Chinese glyph coverage, available weights, fallback appearance on load failure, and license. Replacing a Latin display font alone may not change the character of a Chinese-language page.
- Build hierarchy through size, weight, color, and spacing together; do not add more levels than needed.

## Color roles and coverage

- First set functional colors: hierarchy for text/background (primary text, secondary text, metadata, boundaries); semantic colors (error, success, selected, link); and one main accent. Consider decoration last.
- Let accent coverage and contrast point to the current task. A small accent area on a large neutral background stands out; if the accent appears everywhere, nothing is emphasized. Describe approximate proportions rather than enforcing a quota.
- Check contrast on the actual background: WCAG AA uses 4.5:1 for body text and 3:1 for large text; control boundaries and state information generally need 3:1. Check hover, focus, and disabled states, not only the default.
- Build dark and light themes independently instead of simply inverting colors. Recheck semantic and accent colors in both themes.
- Grayscale inspection can confirm that hierarchy does not depend on color. It is a helper, not a pass criterion; charts and states still need non-color cues. Do not remove necessary meaning to make everything work in grayscale.

## Asset roles

- Ask what information or mood an image, chart, or graphic serves. Use no asset if there is no real role; do not fill a gap with generic stock imagery. Typography alone can be a complete and expressive design.
- Test candidates at final size before deciding: clear subject, useful whitespace, thoughtful crop, suitable resolution, consistent style within the page, and no loss of the subject on mobile. Reject an unsuitable candidate instead of lowering quality to fill space.
- Choose charts, images, or original diagrams according to the content. Reserve key assets at the structure stage. Use icon families consistently, with aligned stroke weight and text baseline.

## Detail consistency

- Use a small, consistent set of values for borders, radii, shadows, spacing, and icon alignment; if the scale can be counted, the system is usually coherent.
- Changes across default, hover, focus, and disabled states should follow a pattern rather than being improvised element by element.
- Fix an isolated detail locally. If many details feel inconsistent, typography or color roles may be unclear; revisit the roles and scales. Do not force process cycles that do not help.

## Self-check

- Does the accent color cover the part related to the current task?
- Does the typography sample still work on the actual page? Are headings, body, and metadata distinct?
- Is the content complete without the asset? Does the asset visibly improve it?
- Is any border, radius, or shadow an unexplained exception to the page's scale?
