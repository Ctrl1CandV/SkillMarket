# ARR Review Guide: Invalid Criticisms (H) and Valid Weaknesses (M/T/R/G)

Source: aclrollingreview.org/reviewerguidelines (full text retrieved and rechecked 2026-08-23; entries are quotations or faithful summaries).
Use this to classify review comments during rebuttal: H items are “invalid criticisms that can be challenged”; M/T/R/G items are valid weaknesses that need empirical responses.
**Before use:** the guide can change. Recheck the version for the current cycle before an important rebuttal.

## H1–H17: Not automatically weaknesses (may be challenged)

| # | Criticism | Why it is invalid (source's point) |
|---|---|---|
| H1 | The result is unsurprising | “Many findings seem obvious in retrospect…” That does not mean the community already knows them or can use them as building blocks. |
| H2 | The result conflicts with my expectations | The reviewer may be experiencing confirmation bias. |
| H3 | The result is not novel | If the reviewer believes similar work exists, they **must provide a citation**. Replication and analysis contributions are within the CFP scope and deserve fair review. |
| H4 | There is no precedent in the literature | “Papers that are more novel tend to be harder to publish”; reviewers can be overly conservative about newer work. |
| H5 | The result does not beat the latest SOTA | **SOTA results are neither necessary nor sufficient for a scientific contribution.** Engineering work can contribute on efficiency, generalization, interpretability, fairness, and other dimensions. |
| H6 | The result is negative | Publishing only positive results is a known field pathology; the community needs to know when something systematically does not work. |
| H7 | The method is too simple | “The goal is to solve the problem, not to solve it in a complex way.” Simple methods can be less fragile and easier to deploy. |
| H8 | The paper does not use my preferred methodology (such as deep learning) | NLP is interdisciplinary. Models, resources, surveys, analyses, position papers, and theory are all valid contributions. |
| H9 | The topic is too niche | “A main track paper may well make a big contribution to a narrow subfield.” |
| H10 | The work evaluates only a non-English language | English-only papers have the same limitation; monolingual work in any language matters. |
| H11 | The paper has language errors | “As long as the writing is clear enough,” scientific content takes priority over prose polish. |
| H12 | A citation is missing | It is only a problem if the work was formally published **more than three months before the deadline** (`published` does not mean an arXiv preprint). Otherwise, it is a suggestion. For resubmission, compare against work published more than three months before the original deadline. |
| H13 | The paper could run another experiment X | The paper needs sufficient evidence for **its stated claims**. Additional experiments are nice-to-have suggestions, not reasons to reject. |
| H14 | The paper should compare against closed model X | This is reasonable only when it directly affects the claim; test contamination and missing details about closed models can make the comparison meaningless. |
| H15 | The paper should use a different approach | “I would write this differently” is not a weakness. It matters only if the author's choice **prevents answering the research question** or the framing misleads. |
| H16 | Limitations are not weaknesses | Content already disclosed in Limitations should not itself be listed as a weakness or rejection reason. To say it overturns the paper, the reviewer needs a separate argument. |
| H17 | Few citations mean the result is invalid | Citation count does not establish validity. |

## M/T/R/G: Valid weaknesses (require evidence, not just rebuttal)

**M — Method:** M1 Unvalidated reliability of an LLM-as-judge (especially common in Agent papers); M2 reproducibility (hyperparameters, public code/data); M3 undisclosed data-quality issues; M4 unjustified model/benchmark choice; M5 incomplete assumptions or proofs.

**T — Data and release terms:** T1 research-ethics issues in data collection; T2 unclear license/release terms.

**R — Experimental results:** R1 analysis problems (misleading statistics, p-hacking, **cherry-picking the best run, including prompt tuning**, or poorly tuned baselines); R2 claim scope is too broad for the sampled population; R3 presenting an assumption as a conclusion; R4 misleading framing/overclaiming; R5 **missing statistical significance evaluation (error bars, confidence intervals, tests)** and discussion of sources of variation.

**G — General:** G1 unclear research question/contribution; G2 reliance on a bad precedent; G3 missing or misrepresented related work (different from H12: this concerns inaccurate description); G4 undefined key terms; G5 citations do not support the cited content.

## How to use in a rebuttal

1. Classify every review comment: H match (may challenge, citing the table's source point); M/T/R/G match (provide experiments/evidence or a concrete revision commitment); neither (neutral suggestion, consider it politely).
2. **Order responses for the reality that area chairs read only the first two comments:** put the strongest response for each thread in positions 1–2. Challenging an invalid criticism may feel satisfying, but answer an empirical R weakness first when both are present.
3. When challenging H items, cite the guide's wording. Area chairs and reviewers know it. Phrase it as “the guide classifies this as a suggestion rather than a weakness,” not as an accusation against the reviewer.
4. For R5 (error bars) and R1 (best-of-N): give a table from registered multi-seed runs if available; otherwise commit to rerun and state a date.

## Boundary

This list helps **authors understand and respond to reviews**. It does not generate reviews or judge the quality of the user's paper.
