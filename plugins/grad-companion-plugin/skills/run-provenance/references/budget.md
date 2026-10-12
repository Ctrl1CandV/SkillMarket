# Evaluation Budget Reference (run-provenance)

> There are only two kinds of numbers here: **primary-source figures with an arXiv ID** (which can be cited directly) and **values the user enters** (unit prices and accelerator hours). There is no third category.

## Scale anchor: HAL

The public bill for the Holistic Agent Leaderboard (`arXiv:2510.11977`):

- 21,730 rollouts = 9 models × 9 benchmarks
- About **$40,000** and 2.5B tokens
- Derived scale estimate (arithmetic from the two lines above, for intuition only): **about $1.8 / 115,000 tokens per rollout**

Implication: students cannot realistically run the full suite. Nine models × nine benchmarks is an institutional-scale effort; a reasonable individual scope is 1–3 models × 1–2 benchmarks × 20–100 tasks.

## Why samples cannot be cut arbitrarily

`arXiv:2607.12338` studies whether pairwise conclusions from partial runs agree with those from complete benchmarks. Its key point is: “costly evaluations make partial runs tempting. A task fraction alone does not show whether a partial run supports the same pairwise conclusion as the completed benchmark”.

Cutting the task count by a percentage **does not guarantee** that the same “A is better than B” conclusion will hold as in a full run. Before reducing samples, decide whether you need to support an absolute score or a pairwise comparison; the latter is more sensitive to sample size.

## Budget worksheet (fill in before registering)

```text
Number of tasks × number of seeds × cost per run = total budget
```

1. Run a pilot first (3–5 tasks × 1 seed) to confirm the pipeline, then run the full set. Register the pilot run too, with the label `pilot`.
2. The user supplies the per-run cost (API token prices from the price list, local accelerator time from hours); the script does not guess.
3. At least 3 seeds are needed to report ±. The standard deviation from n=2 is weak; for n=1, label the result `(n=1)`. See `table_gen`.
4. Budget warning signs: estimated tokens above several billion or cost above four figures in US dollars. Recommend reducing model count first, then task count, and seed count last (seeds determine whether an error bar can be reported).

## Release checklist (addressing the 83% vs. 38% gap)

`arXiv:2608.05179` audited 24 AI Scientist systems: 83% released code, but only **38% released seeds or execution traces**. Check before release:

- [ ] Code release: point to the commit used in the paper, not “latest main”.
- [ ] List every seed explicitly in the README or scripts.
- [ ] Make the complete command line for key experiments easy to copy and rerun (from the `cmd` field in `meta.json`).
- [ ] Inventory sources of randomness: Python/numpy/torch seeds, CUDA nondeterminism, data shuffling, temperature sampling. Fix or disclose each one.
- [ ] Execution trace (optional, but differentiating): input/output logs and an index of intermediate checkpoints.
