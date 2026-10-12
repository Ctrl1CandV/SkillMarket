# Benchmark Score Caveats (run-provenance, living document)

> A known-issue reminder automatically attached when benchmark scores are cited. **Mechanical reminder, not a quality judgment**: a match only means that a verified defect or confounding case exists for this benchmark. A person decides whether and how to use or describe it.
>
> Living-document rule: every new entry must have a primary source (an arXiv ID or official issue); do not add entries from memory. Keep outdated entries and mark them `superseded: true` so upstream fixes remain documented.

## Entries (claim_check.py matches benchmark names against this table)

| Benchmark keyword | Primary source | Defect summary | Recommendation when citing |
|---|---|---|---|
| SWE-bench | arXiv:2410.06992 | Solution leakage: 32.67% of successful patches contain issue leakage; after filtering, SWE-Agent+GPT-4 drops from 12.47% to 3.97% | State which subset/version the score uses. If the main conclusion depends on SWE-bench, discuss leakage and the published fix in Limitations at minimum. |
| TAU-bench / τ-bench | arXiv:2608.05699 (title collision) | The first arXiv search result is a video anomaly-understanding paper with the same title and is unrelated to the agent τ^2-bench; citations are easy to get wrong. | Cite the official repository or exact arXiv ID rather than searching by title alone; verify that the ID points to the intended paper in the references. |

## How to use it

1. **Automatic reminder from claim_check.py:** During ledger validation, if a claim's run-bound benchmark name matches a keyword in this table (case-insensitive substring match), the output includes a `benchmark_caveats` warning. This is the only way the script consumes this file.
2. **Manual check when writing or citing from radar:** When a digest or paper cites a public score for a benchmark, check whether it appears in this table.

## What must not be added

- Unverified second-hand complaints from posts or comment sections.
- General claims that “all benchmarks have contamination problems.” A vague suspicion without specific figures and sources does not belong here.
- Historical entries that have been superseded: retain and mark them so old manuscripts do not cite unsupported claims.
