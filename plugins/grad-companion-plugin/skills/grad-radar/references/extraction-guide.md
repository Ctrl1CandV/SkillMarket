# Preserve Useful Information Before Writing the Explanation

Extract information according to the current request and paper type. Keep source locations and conditions in the extraction so the author can return to the original. Do not summarize only from an earlier abstract or AI summary. Identity alone does not support content conclusions; an abstract supports only what it actually reports.

First identify the question the user wants to understand and their background. By default, explain for a reader with less experience. Let the task define coverage: topic selection may use only relevant sections, while a complete review preserves every major branch. Do not treat all information in one paper as mandatory for every response. Omit details unrelated to the goal, but preserve conditions and counterexamples needed for the current explanation. State what was not read.

## 0. Read in stages; compression rate is not quality

Use Keshav's three-pass approach as a reference: first identify the question, type, background, contribution, and whether deeper reading is worthwhile; next inspect the mechanism, key figures/tables, and supporting evidence; when deeper understanding is needed, reconstruct the argument or method and examine its assumptions. “Reconstruct” here means reason through the material while reading; it does not mean the experiment was reproduced. Adjust depth to the task rather than requiring three complete reads of every paper. [Waterloo author guide, hosted by a UCSD course](https://cseweb.ucsd.edu/~dstefan/cse227-spring22/papers/keshav%3Ahow.pdf)

Compression should remove repetition while preserving information that determines understanding or the meaning of the conclusion. There is no fixed length or ratio. First extract from the specified, fixed version of the original, then write the explanation. Do not repeatedly summarize an old AI summary. If the body is unavailable, narrow the deliverable accordingly.

## 1. Choose information by paper type

| Type | Main thread to extract | Most easily lost |
|---|---|---|
| method | Problem/gap in prior work → inputs and outputs → changes and steps → comparisons and ablations → scope | How information passes between steps; whether gains depend on settings; negative results |
| evaluation | Object measured → data/ground truth → environment and interface → criteria → findings | Sample subset, denominator, test coverage, and whether results remain comparable after protocol changes |
| system | Requirements → module responsibilities → data/control flow → bottlenecks and trade-offs → measurements | What each module actually does; resource/budget conditions and failures |
| theory | Definitions → assumptions → conclusion → proof outline → counterexample/boundary | Quantifiers, necessary conditions, gaps in the proof; intuition is not proof |
| survey | Scope/cutoff → taxonomy dimensions → branch mechanisms and differences → evidence/limitations | Whether dimensions are exclusive, composable, or orthogonal; the evidence level behind a review's summary |

For a mixed paper, organize around its primary task and retain secondary contributions. Do not fill every column mechanically.

## 2. What to preserve for each key point

Use concise bullets or a table in the working extraction: **information/claim, evidence and exact version location, necessary conditions, attribution (author claim/direct evidence/teaching explanation), and gap**. Include only content supported by material actually inspected.

Give each core point that must survive into the final note a short ID. Record where it goes in the final note (retained, merged with which item, or deferred with a reason). Keep source locations separate from explanations and use your own words. Do not drop key results, assumptions, counterexamples, or taxonomy branches just to shorten the note. An ordinary short note can use a simple table; no database or new personal record is required.

- **Motivation and contribution:** In what setting did prior methods fail? Which specific stage does this paper change?
- **Method:** Inputs/outputs, assumptions, and relationships between steps. Explain symbols and purpose near equations; state unrecoverable derivation gaps accurately.
- **Experiments:** Dataset/task, train/test split, comparison, model/tool and budget, metric and denominator, core result. Preserve settings that affect comparison.
- **Evidence:** Keep ablations, failures, negative results, and limitations. Do not turn correlation into causation or task performance into universal ability.
- **Numbers:** Preserve units, denominators, comparison, budget, and variability when reported. Distinguish percentage points from relative change, mean from best result, and author-reported from independently calculated values. If body text and a table conflict, point it out without selecting the more favorable number.
- **Resources:** Locate original code, data, and implementation details. A link alone does not mean it was run, reproduced, or verified as useful.
- **Learning value:** State the specific concept, reading method, difference, and connection to the current question; do not turn every paper into a new research opportunity.

## 3. Check figures, tables, and equations against actual material

For a figure, inspect the actual image and caption; identify arrows, legend, groups, axes, and the claim it supports. If only the caption is available, do not describe unseen content. For a table, verify headers, rows/columns, units, subsets, and footnotes; check that settings match before comparing tables. For an equation, identify symbols, conditions, and key steps; do not fill garbled text from prior knowledge.

If figures or tables fail to extract, other evidence-based content may still be delivered. But when the gap affects the core mechanism, do not claim it was fully explained. Work described by a review must be attributed as “summarized by the review”; do not say the original paper was read independently.

## 4. Write prose readers can follow

Start with the question and necessary terminology, then explain the mechanism or argument, using a running example or comparison, and state conditions and boundaries. Label self-created examples “supporting explanation” and keep original definitions intact. Use sections as appropriate; do not force every note into the same five headings.

Keep previews short; expand the body to the level needed for understanding. Remove repetition and production notes, but keep motivation, reasoning, examples, numeric settings, negative findings, and attribution to the author/editor. If using de-ai-flavor, follow this principle: do not compress the note into a list of conclusions or apply a global word replacement.

### Two review examples (illustrative only; not experimental data)

- “Success rate rose from 40% to 60%”: first verify task, denominator, comparison, and budget. If the source lacks settings, mark it as needing verification; do not invent a claim such as “a 50% improvement and universally superior.”
- “Tests passed”: state which outputs and conditions they check. Passing existing tests does not establish that every real requirement is correct, and does not prove an internal reasoning process.

## 5. Recheck after writing

Recheck key definitions, causal claims, numbers, scope, and negation item by item; verify that sources support the adjacent statements. Then read as a learner: can the reader explain how inputs become outputs, how two methods differ, and under which conditions a conclusion holds? Check source support and readability separately; word count and heading count are not substitutes.

Reconcile the key-point list before and after compression. At minimum, verify that the main contribution retains its meaning; the core mechanism can be restated; results retain their settings; important negative findings/limitations remain; citations support adjacent claims; and unread material has an entry point and reason. For a theory paper, check assumptions, conclusion, and proof outline instead of experiments. If claims, conditions, or evidence remain incomplete, label the explanation partial and list the next step. Do not hide missing support behind fluent prose.

When comparing papers, state their common task and settings, real differences, and whether the results are comparable. Do not treat several short summaries pasted together as synthesis. This approach draws on [Stanford CS224U literature review requirements](https://web.stanford.edu/class/cs224u/projects.html), but does not adopt its course-specific paper, page, or format quotas.

A learning guide may end with a few original passages worth reading and why, plus comprehension checks when useful. For claim checking or implementation, give the relevant open questions or actions instead; do not force a quiz. If there is only an abstract and no outline, describe section types without inventing section numbers.
