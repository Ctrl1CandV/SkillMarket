# Project and Branch Decisions

## First answer the questions that change the choice

Determine whether the project is an application, library, documentation, research, or asset repository; whether the main branch should always be usable or represent only a release; whether deployment is continuous; whether older versions remain supported; whether releases have a freeze period; who may merge; whether CI exists; and whether downstream users depend on branch-specific directory layouts. Do not ask the user for facts available in the repository.

Choose a branch model from these facts; team size and code volume are secondary. The following are starting recommendations, not Git requirements; the model can evolve.

| Situation | Long-lived branch starting point | Short-lived branches and end condition |
|---|---|---|
| Personal scripts, small documentation, early prototype | One main branch | Create topic branches only for isolation/review; integrate or explicitly discard them when done. |
| Team application, open-source contribution, continuously delivered site | One integrable main branch | Short-lived feature/fix/docs branches, merged after checks and review. |
| Trunk development with fast CI and small-batch integration | One trunk branch | Direct integration or very short topic branches per team review rules; isolate unreleased features using an existing project mechanism. |
| Scheduled release with a separately stabilized candidate | One main branch, optionally an integration branch | Release branch accepts stabilization fixes only and ends after release and back-merging fixes. |
| Library, SDK, or desktop product supporting multiple versions | One main branch plus supported maintenance branches | For example, release/1.x and release/2.x; backport compatible fixes as needed and archive a version when support ends. |
| Explicit separation between next-version integration and production releases | Main plus develop (use the project's naming) | Consider full Gitflow only here, with feature, release, and hotfix branches; it brings ongoing multi-target back-merges and synchronization costs. |
| Research, design assets, or model experiments | Usually one main branch | Use short-lived experiment branches for code exploration. Track experiment data/results with run IDs and storage manifests instead of permanent branches per run. |

[GitHub flow](https://docs.github.com/en/get-started/using-github/github-flow) is a lightweight process for branches, commits, pull requests, review, and merge. In a [2020 reflection](https://nvie.com/posts/a-successful-git-branching-model/), the author of Gitflow recommended simpler processes for continuous-delivery teams while retaining its usefulness for explicit releases and multi-version maintenance. The choices in the table are recommendations based on those sources and project constraints.

Trunk development and GitHub flow may each use one long-lived main branch, but differ in integration frequency, review, and feature exposure; do not treat the terms as synonyms. An open-source fork concerns permissions and contribution flow, not the required number of long-lived upstream branches. Usually branch from the upstream target, push a topic branch to your own fork, then open a PR.

## Document each branch's lifecycle

For each branch role, state its base, allowed changes, merge destination, required checks, and when it is deleted or no longer maintained. For example, with Gitflow:

| Role | Starts from | Allowed content | Back-merge |
|---|---|---|---|
| feature | Current integration branch | One logical feature with its related tests/docs | Integration branch |
| release | Integration state with current features complete | Fixes, version/release documentation; no next-version features | Release and integration branches |
| hotfix | Affected released version or maintenance branch | Minimal fix and regression test | Affected release line and current development line; handle active release branches per project rules |

See the [original model](https://nvie.com/posts/a-successful-git-branching-model/) for Gitflow's branch bases and back-merge rules; the multi-version maintenance guidance here is a project decision recommendation. After a fix, identify which supported versions need it. Do not merge into every historical branch by default, and do not fix production while missing the active development line.

Follow repository naming. Without a convention, choose a short, purpose-specific name such as feat/export-csv, fix/cache-race, or docs/install. Use host prefixes such as codex/ only when the host or project requires them. Do not present a fixed prefix or branch count as a Git standard.

## Branch file trees and release manifests

Main, feature, development, and maintenance branches ordinarily retain the source, tests, build configuration, migrations, documentation, and lockfiles needed for their respective version. Differences reflect versions or tasks; “main can contain only finished deliverables” is not a general rule.

If the user wants main to contain runtime resources only and dev to contain evaluations or maintenance material, clarify the goal:

1. **They only want smaller release packages:** Prefer package-manager allowlists, release scripts, container build contexts, or git archive exclusions; development material may remain in the source repository.
2. **They explicitly require different branch trees:** Follow existing conventions and record allowed/excluded directories and integration method. Preview the release diff and inspect other changes in the whole source branch.
3. **Material requires separate permissions:** Put it in a repository or external storage with different access control. Branch separation alone is not a reliable confidentiality boundary.

export-ignore excludes files from archives; it does not prevent commit or push and is not necessarily honored by every package manager. See [gitattributes](https://git-scm.com/docs/gitattributes) and [git archive](https://git-scm.com/docs/git-archive).

When maintaining branch-specific directory differences, do not merge all of dev and repeatedly delete extra directories. Follow the existing process to integrate runtime-only commits or apply an exact path diff to the target; preview first and preserve target-specific changes. If a commit mixes runtime resources and maintenance files, split it in unshared, controlled history or create a separate release change. Keep integration/reconciliation records so fixes are not silently missed. Do not rewrite shared dev history on your own to achieve this.

## Environment, release, and permissions

By default, build artifacts from the same source version and promote them through test, staging, and production environments. Manage environment differences through configuration, deployment records, and a secret manager. This is a design recommendation for reducing drift. If environment branches already exist, first determine deployment dependencies and promotion workflow; do not delete branches on your own.

Use traceable tags, commit IDs, and artifact records for releases; do not infer production version from a moving production branch. With SemVer, define public interfaces and compatibility promises before choosing version numbers. Follow project rules for 0.x and prereleases; do not release a version mechanically from a commit subject. [SemVer specification](https://semver.org/)

Merge permissions, required checks, number of reviewers, and signing rules come from the project and platform. Branch protection can enforce them, but writing contribution docs does not activate protection. If platform configuration cannot be inspected, mark it unverified; do not claim the remote branch is protected. [GitHub branch protection](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)

## Establish project conventions

Write or change project documentation only when the user asks to establish or adjust a workflow; ordinary fixes do not require a new governance file. Use the [template](../assets/git-policy-template.md) to record actual branch strategy, file classification, commits, verification, releases, and cleanup boundaries. Distinguish implemented configuration from proposed configuration. If a convention conflicts with reality, explain the impact and adjust only within the user's scope; do not replace project decisions with this skill's recommendations.
