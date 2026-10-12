# Commits, Synchronization, Collaboration, and Releases

## A commit is one logical change

A feature, its regression tests, and necessary documentation usually belong together. Independent formatting, dependency upgrades, file moves, and behavior changes should be split into reviewable/revertible logical changes. Do not create one commit per file, and do not put a whole day's changes into a single commit. Update the manifest and required lockfile together.

First read contribution guidelines, commitlint/release configuration, and recent commit subjects. Follow established format. If no format exists and automated changelog generation is needed, Conventional Commits may be recommended; a small project may use consistent, specific descriptive subjects instead. Language, subject length, and issue format are team choices. Do not claim Git requires 50/72 characters or English imperative messages.

For Conventional Commits, use a shape such as:

```text
type(scope)!: concise, specific change

Explain the trigger, reason, and impact; include verification or migration details when needed.

BREAKING CHANGE: incompatible behavior and migration steps
Refs: #123
```

Use scope, !, body, and footer only when needed. Either ! or BREAKING CHANGE: may identify an incompatible change. This skill recommends explaining migration when compatibility changes are complex. feat means a feature; fix means a fix. Optional team types include docs, test, refactor, perf, build, ci, and chore. The specification does not require all these types and not every tool supports custom types. [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/)

Examples include fix(cache): prevent stale results after invalidation and docs(install): add Windows installation steps. Avoid update, changed files, and assorted improvements. Use refactor only when behavior is unchanged; do not hide feature or compatibility changes under that label. The subject describes the change; the body explains why. Do not copy the full diff or AI conversation.

Do not invent passing tests, issue IDs, signatures, DCO consent, or Co-authored-by. If the repository requires signing or DCO, use a configured, valid identity; do not declare unconfirmed copyright permission on the user's behalf.

### Acceptance checks for agent-generated commit messages

Determine the final staged changes first, then write the subject. Do not generate a message from the user's entire request, a plan, or all worktree changes. Check:

1. The subject names a recognizable object and specific action/behavior so the reader can understand the change without chat history.
2. Subject and body match actual changes; do not claim unstaged, unimplemented, or failed work is complete.
3. If one subject must say “and other changes” to cover independent items, consider splitting commits. Related source, tests, and docs may remain one logical change.
4. Add only necessary reason, impact, migration, and actual verification in the body. An accurate subject is enough for a small change; do not fill the body with empty boilerplate.
5. A date, type, or issue ID does not replace a description. Even when following repository style, be specific. WIP may be acceptable on a private work branch by team convention, but do not leave a vague WIP subject on final delivery.

| Vague message | Example revised from an actual snapshot |
|---|---|
| update / 10.12 edit skill | 10.12 git-governance: add branch file checklist and commit-message review |
| fix: fix problem and clean files | fix(config): stop tracking local credentials and add example defaults |
| improve docs and tests (but the change only archives an evaluation) | 10.12 git-governance maintenance: record file-scope review and verification |

These are invented examples of descriptive and Conventional Commit styles. Replace them with facts from the current snapshot; do not copy security handling or verification that was not done.

## From staging to commit

First determine ownership and scope of existing staged content. If the same file mixes this task and user changes, stage exact hunks. If interactive patching is unavailable, preserve the file and explain that scope must be resolved; do not stage it wholesale. Example paths are placeholders:

```sh
git add -- path/to/source path/to/test
git diff --cached --name-status
git diff --cached --check
git diff --cached
git commit -F path/to/commit-message.txt
git show --stat --oneline HEAD
git status --short --branch
```

A commit includes the entire index, not only the files just added. Even path-limited commits may bypass the meaning of existing staged content. If unrelated content is staged, isolate it or preserve it precisely; do not rewrite the user's index by accident.

Put multi-line commit messages and PR bodies in a safe temporary file and pass them with -F or a platform's body-file/structured argument. Quote paths for the actual shell. Do not interpolate user text into an executable command. Do not leave the message file in the repository or add --no-verify to bypass a hook rejection.

## Decide the target before synchronizing

origin is a common name, not necessarily the upstream to push to. In a fork, the common pattern is fetching from upstream and pushing to a personal origin. Confirm each remote's purpose and push URL; hide credentials in output.

After confirming the actual remote and base, fetch and inspect current state. Replace uppercase placeholders before running; the snippets contain no shell redirection operators:

```sh
git fetch REMOTE
git rev-list --left-right --count HEAD...REMOTE/BASE
git log --oneline --left-right HEAD...REMOTE/BASE
```

Here, HEAD...REMOTE/BASE is for checking divergence. For PR changes, git diff REMOTE/BASE...HEAD shows changes since the merge base; git diff REMOTE/BASE HEAD compares the two trees. They answer different questions. Confirm the comparison base and semantics before using them. [git diff](https://git-scm.com/docs/git-diff)

| State | Handling |
|---|---|
| Local branch is behind, with no local-only commits | git merge --ff-only REMOTE/BASE is suitable; first ensure local files will not be overwritten. |
| Only local commits exist | No extra merge is needed “to synchronize”; review them and push if required by the task. |
| Both sides have unique commits | Rebase a private topic if conventions allow. For a shared branch, usually merge or use an integration branch; do not rewrite collaborators' history automatically. |
| No upstream or a new branch | Explicitly choose remote and same-named/specified target, then establish tracking; do not assume any existing ref is the release target. |

Preserve necessary changes before merge/rebase. A normal pull may integrate differently depending on configuration; do not use it blindly when that configuration is unclear. “Shared” depends not only on whether a branch was pushed but also on whether anyone relies on it.

Resolve conflicts by reading both sides and their intent; do not choose ours/theirs globally. During rebase, ours/theirs may differ from intuition. After resolving, stage each path, inspect the conflict list, and run affected checks before the relevant --continue. To stop, use the matching merge --abort, rebase --abort, or cherry-pick --abort. A merge is not guaranteed to reconstruct a pre-existing dirty worktree perfectly. [git rebase](https://git-scm.com/docs/git-rebase), [git merge warning](https://git-scm.com/docs/git-merge)

## A push publishes refs and history

If the task includes pushing, inspect the destination repository, branch, and any deployment triggered by it. Review every commit the target does not yet have, not only HEAD; for a new remote or unrelated history, review the entire outgoing history. If a large or sensitive file ever entered Git, follow the cleanup reference.

Use an explicit refspec for an ordinary push:

```sh
git push --dry-run REMOTE HEAD:refs/heads/TOPIC
git push -u REMOTE HEAD:refs/heads/TOPIC
```

A dry run previews only part of a push; it does not prove that server hooks, CI, permissions, or sensitive-file checks will pass. Do not push --all, --mirror, or --tags by default. Do not describe “committed” as “uploaded.” If a push is rejected as non-fast-forward, fetch again and inspect new commits; do not force-push to complete ordinary synchronization. [git push](https://git-scm.com/docs/git-push)

## Multiple people, agents, and worktrees

Give parallel tasks their own working directory and branch. Inspect current worktrees and branch usage before creating a new one; start it from the correct base. A branch tree contains only committed content from its base. Move necessary changes from the original worktree deliberately; dependencies, ignored configuration, and runtime environment do not appear automatically. [git worktree](https://git-scm.com/docs/git-worktree)

A worktree shares the object database and some repository state; it is not a full sandbox. Coordinate shared refs, remote operations, and config. Do not reset/rebase a branch used by another task or clean its directory on its behalf. After work, check uncommitted and ignored files that must be retained before safely removing the worktree. Follow host management tools when available.

## Pull requests, merging, and releases

Make PR/MR source and target branches explicit. Describe the actual problem, final behavior, verification, and compatibility/migration impact using the platform template. Check the full diff for scope. Work may be shared early as a draft for review, but do not call it releasable before it passes gates. [GitHub flow](https://docs.github.com/en/get-started/using-github/github-flow)

Use the project's merge policy: merge preserves branch structure; squash condenses a logical task into one commit; rebase merge replays commits linearly. Squash or replay changes commit IDs, so checking whether something was integrated cannot rely only on ancestry or branch --merged. If release automation uses subjects, check the final subject entering the target branch, such as a squash PR title.

Before release, confirm commit/tag, version, changelog, package contents, build, and platform-required checks. Inspect archives/package output for local configuration or unnecessary files. Do not move published tags casually; a fix usually gets a new version and must be back-merged to affected development/maintenance lines. Push only explicit tags. A release page, package, and deployment system are separate actions and require task authorization. See [SemVer](https://semver.org/) for public API and compatibility versioning.
