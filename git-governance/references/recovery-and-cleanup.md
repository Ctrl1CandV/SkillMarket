# Cleanup, Rollback, and Recovery

## Identify the object before choosing an operation

“Do not upload” and “safe to delete” are not equivalent. A cache may be rebuildable; a local database, experiment results, ignored configuration, or private draft may have no other copy. Git cannot restore ordinary files that were never recorded.

| User goal | Preferred action | Risks and facts to establish |
|---|---|---|
| Remove a file from the next commit while preserving current edits | With an existing HEAD, git restore --staged -- PATH | Changes only the index; do not also use --worktree. Without an initial commit, use an operation suitable for the initial index. |
| Keep a tracked file local from now on | Ignore rule + git rm --cached -- PATH | Preserves the current worktree and commits removal from the version tree; history remains. |
| Reverse a normal commit already shared | git revert COMMIT | Creates a reverse commit and may conflict; does not remove sensitive history. |
| Clean up unshared commits used only by you | Amend/rebase after preserving a recovery reference | Changes commit IDs; confirm scope, worktree, and whether others depend on it. |
| Discard specified uncommitted changes | Inspect diff and make a necessary backup, then restore only those paths | Worktree restore overwrites the relevant changes; it is not unstaging. |
| Delete rebuildable untracked files | Dry-run clean on exact paths, then clean | Git has no recycle bin for ordinary files; inspect the preview list first. |
| Delete a merged local branch | Check integration and branch use, then branch -d | Squash/rebase may cause the safe deletion check to reject it; do not jump to -D. |

Command semantics: [git restore](https://git-scm.com/docs/git-restore), [git rm](https://git-scm.com/docs/git-rm), and [git revert](https://git-scm.com/docs/git-revert). Reverting a merge commit requires choosing the mainline parent and affects future merge semantics; do not mechanically use -m 1.

When authorization is already clear, act within its scope; do not ask again just because the operation appears in a risk table. If “clean up” is vague, first inventory, preview, explain impact, and make reversible changes. For deletion, overwrite, remote deletion, or rewriting shared history that still lacks authorization, confirm the exact objects. One approval does not authorize all future destructive work.

## Clean untracked files

Use a path known to be disposable as the boundary and preview it first:

§§§sh
git clean -nd -- path/to/disposable-output/
§§§

Proceed only after confirming the output contains exactly the targets, necessary copies are preserved, and scope is authorized; then use the same command with git clean -fd -- path/to/disposable-output/. Preview again if file or path state changes before execution.

-X selects only ignored files; -x includes ignored files too. Either may delete real .env files, local data, and virtual environments. Ignored does not mean reproducible. Never use git clean -fdx as a universal fix for build, sync, or commit problems. Do not use -ff to bypass nested-repository protections. [git clean](https://git-scm.com/docs/git-clean)

For filesystem deletion, resolve and verify that the absolute destination is within an authorized directory. Avoid traversal through path concatenation, symlinks, or junctions. On Windows, use native path operations in the same shell, such as PowerShell -LiteralPath; do not pass enumerated paths into a different shell. Do not delete .git, manually edit internal objects, or run gc --prune=now to “clean up the project.”

## What can actually be preserved and restored

Before a change, preserve the appropriate material: a recovery branch/tag can retain committed history; uncommitted text can be saved as a diff (both staged and unstaged); untracked, binary, and ignored content needs a separate suitable backup. One ordinary diff does not preserve all of these, and a Git bundle does not save worktree files.

Stash does not include untracked files by default. -u adds untracked files; -a also includes ignored files and removes them from the worktree. Do not blindly stash everyone else's changes or include real secrets in a stash. When needed, select paths and record the stash ID; prefer apply, inspect, then drop. Do not clear all stashes automatically. [git stash](https://git-scm.com/docs/git-stash)

If a branch was deleted or HEAD moved by mistake, inspect git reflog and git log --all. Confirm the target commit and create a recovery reference before deciding how to restore the worktree. Reflog is local and expires; it cannot guarantee recovery of all history or uncommitted files. Do not make reset --hard the first recovery step. [git reflog](https://git-scm.com/docs/git-reflog)

For a lost file never added/committed/stashed, first check editor history or an actual backup; do not promise Git can recover it. Preserve unintegrated commits from a deleted branch with a reference first. Deleting a remote branch removes a ref; it does not guarantee deletion of all objects or third-party copies.

## Handle ordinary rejection separately from force-push

Diagnose non-fast-forward rejection, branch protection, and hook rejection separately. For ordinary fixes, fetch, integrate, and run required checks. Do not force-push, disable hooks, or turn off protections to bypass rejection.

If a task explicitly requires replacing shared history, first prepare a reviewable result and record the affected remote/ref, full current remote OID, expected new history, and collaborator recovery plan. Execute only after scope-specific authorization. For ordinary history cleanup, retain the old reference. For an exposure incident, store backups only in a controlled location; do not publish a backup branch.

Use an explicit expected OID in the lease to limit the overwrite scope. Replace uppercase placeholders:

§§§sh
git push --force-with-lease=refs/heads/TOPIC:EXPECTED_OID REMOTE HEAD:refs/heads/TOPIC
§§§

EXPECTED_OID must be the actual remote value retrieved and reviewed. Do not copy a stale value that merely looks correct; if the remote gains commits during preparation, inspect them again. Bare --force-with-lease depends on a remote-tracking ref and a background fetch can weaken its protection. A lease checks only the expected ref value; it does not prove the replacement is correct and is not authorization. [git push lease documentation](https://git-scm.com/docs/git-push)

## Credentials or private data entered history

1. Stop further propagation. Identify affected paths, commits/branches, and visibility; do not repeat the content in chat, logs, or issues. Do not upload a sample to a service for “verification” without authorization.
2. Revoke or rotate an exposed credential first. If you lack account permission, say the owner must do it. Do not say a credential is invalidated just because its file was deleted.
3. Determine whether the content was only staged accidentally, entered an unshared local commit, or was pushed/appeared in a PR, tag, cache, LFS, or copy. The first cases can be handled within their scope; shared history needs platform and collaborator coordination.
4. Set up future ignore/local configuration and decide whether history removal is needed based on exposure. Adding .gitignore, committing deletion, or reverting does not erase old content.
5. If history removal is required, follow the current official platform process and suitable tools. Test the result in a controlled copy; identify all affected refs and copies before updating the remote under authorization. Avoid assembling arbitrary commands to rewrite the whole repository. Record limitations when you cannot control forks, clones, or caches.

See the [GitHub guide to removing sensitive data](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository) for process and restrictions on history rewrites. Do not assume GitHub's cache/support process applies to other hosts. Account and service changes require user authorization.

## Retire branches and worktrees

Before deletion, check for unintegrated commits, active PRs, downstream dependencies, and use by another worktree. After squash/rebase, confirm equivalent changes reached the target and preserve necessary references; do not fake a merge just to satisfy -d. For remote deletion, confirm the exact remote/ref and authorization; deleting a local branch does not delete the remote. Before deleting a worktree, inspect ignored files that must be retained. Do not force-remove unfinished work.
