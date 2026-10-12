# Judge Agreement Validation Protocol (run-provenance)

> `judge_agreement.py` only calculates agreement rate, κ, and the confusion matrix; **this file explains how to make those results trustworthy**.
> ARR lists an unvalidated LLM-as-judge as its first methodological weakness. Using a judge in a paper without validating agreement is an obvious point for reviewers to challenge. Decide whether κ is high enough for your claim; the ranges below are reference points, not a pass/fail threshold.

## Checklist before running an agreement study

- [ ] **Minimum sample size:** At least 30 examples are needed to calculate κ; 100+ is more convincing, with a confidence interval narrow enough to cite. Do not report κ in a paper with fewer than 30.
- [ ] **Fixed conditions:** Record the judge's temperature (0 or the disclosed value), prompt version, and model version together in the run registration. For example: `run_register.py --method "judge=<model>@temp0"`, using the name of the judge actually used. Changing any one means using a different judge that must be revalidated.
- [ ] **Scoring order:** Fix and record the order in which candidates A and B are shown. If the judge can see the choice order, check position bias by swapping A/B and rerunning one round; report κ for both orders.
- [ ] **Human labels for comparison:** Have at least one person label the examples, preferably two people independently, then compare with the judge. A single annotator's comparison supports only a weak conclusion; say so.
- [ ] **Adjudicate disagreements:** Review each example where the judge and humans disagree. Systematic disagreement (the judge is biased on a particular kind of example) is much more serious than random disagreement and belongs in Limitations.

## Reference ranges (common interpretations, not acceptance criteria)

| κ range | Common interpretation (Landis & Koch convention) |
|---|---|
| 0.81–1.00 | Almost perfect — may be cited as evidence with confidence |
| 0.61–0.80 | Substantial — accepted by many venues, but report confidence intervals and disagreement analysis |
| 0.41–0.60 | Moderate — reviewers may ask why the full set was not labeled by humans; additional stability evidence is needed (for example, several judges and their consensus subset) |
| ≤ 0.40 | Reviewers will generally treat it as unvalidated |

These are **interpretive conventions, not passing thresholds**. Adequacy depends on the strength of the claim; use a stricter standard when the paper's main conclusion depends on the judge.

## Relationship to other plugin components

- An agreement study is an evaluation run: register it with `run_register.py` (record judge identity in the method and agreement/κ in metrics), then bind claims through the normal two-axis workflow.
- The submission-gate checklist asks whether judge agreement was validated when a judge was used. This document is preparation for that check.
