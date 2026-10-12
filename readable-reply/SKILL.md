---
name: readable-reply
description: Improve the paragraph structure and formatting of replies from ChatGPT and other AI systems. Use for longer explanations, analyses, research, reviews, troubleshooting, and recommendations, especially when the user says the response is hard to read, has too many line breaks, or is broken into fragments. Organize body text into complete, natural paragraphs; use headings, lists, and tables to support understanding. For standalone writing, courses, and finished front-end copy, use de-ai-flavor instead; do not apply this skill merely because the work is delivered in chat.
metadata:
  version: "1.0.1"
---

# Readable Replies: Paragraph Density and Formatting

## Why adjust the formatting?

Putting each sentence in its own paragraph, inserting a line break after every line, or adding a heading or list every few sentences can fragment an otherwise coherent explanation. Terminals, chat interfaces, and Markdown renderers handle line breaks differently, so do not infer reading difficulty from a fixed number of lines. Focus on whether readers can follow the point, find the answer, and act on it.

The goal is not to eliminate structure, but to make structure serve understanding. This skill only changes conversational replies and does not depend on de-ai-flavor. Reformatting must not change facts, conditions, negation, sources, code, or commands.

## Three principles

### R1. Keep paragraphs coherent (most important)

- Organize body text into natural paragraphs, each expressing a complete idea. Keep related sentences together rather than inserting manual line breaks between sentences or clauses. Start a new paragraph when the idea changes, while avoiding walls of text.
- Merge a series of “one sentence + blank line” fragments when they belong to the same point. Do not add text to reach a sentence or word count; short answers and necessary cautions can stand alone.
- Put a few parallel phrases in one sentence with commas or semicolons. Use a list when readers need to carry out or check items one by one.
- To emphasize a sentence, place it near the start or end of a paragraph instead of giving it an isolated bold line.

### R2. Structure should add value

- **Lists:** Use for parallel options, procedures, checklists, or information that readers need to cite item by item. Prefer prose for continuous causal explanations.
- **Tables:** Use to compare items along the same dimensions; even two options may justify a table. Each cell should be understandable on its own, and columns should convey useful distinctions.
- **Headings:** Use when the topic changes or navigation is helpful, not according to the number of lines on screen. Avoid headings followed by only a transition sentence.
- **Block quotes:** Reserve for quotations. Bold only a few important conclusions or cautions; do not use bold labels throughout as a substitute for paragraph topic sentences.

### R3. Separate length from layout

- Merge synonymous repetition and empty transitions while retaining necessary reasoning, distinct rationales, and conditions or cautions that affect what the reader should do.
- Usually answer the question directly at the start of the first paragraph, then explain the reasoning. If a premise must be clarified first, state the premise that affects the answer.
- Let the task determine the length. Do not use blank space to make an answer look substantial or compress an explanation into a summary just to make it shorter.

## Before and after

The fictional troubleshooting example below changes only the organization, not the diagnosis.

Fragmented version:

```text
The request timed out.

It may not be a network problem.

Server queuing can also cause a timeout.

Check the request logs first.

Then compare them with server processing time.
```

Readable version:

```text
The request timing out does not necessarily mean there is a network problem; server queuing can cause timeouts too. Check the request logs, then compare them with server processing time to determine whether the time was spent in transit or waiting for processing.
```

If you need to provide multiple commands, decision branches, or recovery steps, present them in code blocks and lists instead of burying executable actions in a long paragraph.

## Exceptions (R1 does not apply)

- Procedures, command sequences, checklists, code, and configuration files naturally use one item per line; leave them that way.
- Follow the user's request for an outline, table, or bullet-point format.
- Standalone writing (courses, articles, reports, emails) and finished front-end copy follow their own conventions, whether or not they are delivered in chat. Use de-ai-flavor when they need more natural prose.

## Final check

1. Have hard line breaks unnecessarily split one idea? Have different ideas been crowded into one long paragraph?
2. Do headings, lists, and tables help readers locate, compare, or act on information, or do they merely add whitespace?
3. After merging text, are facts, limitations, citations, and necessary explanations preserved? Can the code and steps still be used as written?
4. Does the opening answer the question or state the premise that prevents an answer? If it is already clear, stop editing.
