---
name: git-governance
description: Establish or follow Git practices for different projects, including branch choices, tracked and local-only files, ignore rules, commits, synchronization, pull requests, releases, and safe cleanup. Use when initializing a repository, organizing version control, preparing a commit or push, or resolving Git collaboration issues. Choose a workflow that fits the project; do not impose Gitflow or Conventional Commits on every project.
metadata:
  version: "1.0.1"
---

# Git Project Governance

Make the project's history understandable, reproducible, and collaborative while preserving the user's existing work. This skill is for AI systems that can read files or use Git. It does not depend on a particular model, hosting platform, MCP, or plugin. If execution tools are unavailable, provide precise steps and state what was not done.

## Distinguish Git mechanics from conventions

- A Git commit is a local snapshot. Push updates remote references and transfers the objects they need; it does not mean “upload only the files selected this time.” A file deleted from the latest commit may still appear in history that will be pushed.
- A branch is a reference to a commit, used to isolate work or maintain versions. Branch names do not define file permissions, and a local branch is not a privacy boundary.
- Commit formats, branch names, merge strategies, and release gates are project conventions. Follow the user's current instruction first, then repository contribution guides, automated checks, and established practice. State recommendations separately from Git's technical constraints.
- Reuse an existing process when it solves the problem. When adding a rule, explain what problem it addresses. Do not add permanent branches automatically just because the project is large, uses many AI agents, or has many directories.

Mechanics references: [Git push](https://git-scm.com/docs/git-push) and [the original Gitflow article and the author's later reflection](https://nvie.com/posts/a-successful-git-branching-model/). These references were checked on 2026-10-12; consult current official documentation when versions or platforms differ.

## Read according to the task

| Current task | Read |
|---|---|
| New repository, too many branches, release process, different directories retained by different branches | [Project and Branch Decisions](references/project-policy.md) |
| Choosing tracked files, local-only files, large files, ignore rules, platform differences | [File Management](references/files.md) |
| Commits, synchronization, push, pull requests, collaboration with people or multiple AI agents, merges, releases | [Commits and Collaboration](references/commits-and-collaboration.md) |
| Discarding changes, cleanup, rollback, force push, history pollution, credential exposure | [Cleanup and Recovery](references/recovery-and-cleanup.md) |

Read only the references needed for the current task. To create project conventions, use the [policy template](assets/git-policy-template.md), fill in actual decisions, and save it in an appropriate project location.

## Workflow

### 1. Establish repository facts

Read applicable AGENTS.md and CONTRIBUTING files, README, existing Git policy, CI and package-manager configuration. Inspect .gitignore, .gitattributes, and commit conventions. Run commands appropriate to the task:

```sh
git --version
git rev-parse --show-toplevel
git status --short --branch --untracked-files=all
git diff --stat
git diff --cached --stat
git branch -vv
git worktree list
git remote
git log -8 --format="%h %s"
```

These commands reveal the repository location, user changes, staged content, branches, other worktrees, remote names, and recent message style. A repository with no commits, remote, or upstream can be in a normal initial state. Handle each separately; do not run init, add a remote, or push for the first time just to remove an error. For a detached HEAD, first decide whether the task needs a new branch.

Display only necessary output. Remote URLs, diffs, filenames, and commit messages can contain private information. When checking credentials, report the path and type of issue; do not repeat secrets. When machine-parsing file lists, use Git's -z output; never split paths on spaces.

Record the current branch, target base, existing changes, and task scope. Determine whether the task includes a commit, push, pull request, or release; these are separate actions. Reuse authorization already given in the conversation instead of asking again. Complete ordinary local edits and checks directly. Ask only when a critical fact or authorization is missing for a dependent operation, while continuing independent work.

### 2. Choose branches and file handling

For routine tasks, follow the existing branch plan. For a new project, choose the smallest adequate branching strategy based on release cadence, parallel work, supported versions, and review needs. Verify the actual default branch name instead of assuming it is main; the development base may be dev, develop, or a maintenance branch.

Classify files by purpose: track in Git, keep local, store externally, delete only after verification, or leave undecided. Generated files do not all need to be ignored, and documentation, data, and configuration do not all need to be uploaded. Consider purpose, reproducibility, sensitivity, and maintenance cost.

Before committing, establish the exact path list for this change. Check what belongs on the target branch, what must be excluded, and what dependencies are necessary; inspect each new directory file by file. For testt/, private/, temporary tests, agent drafts, review notes, or project documents, use the [commit checklist in File Management](references/files.md) to determine purpose and destination. Do not stage an unclassified file or guess whether to retain or delete it from its directory name.

The branch file tree, remote repository visibility, and release-package contents are three separate questions. By default, share a complete source tree that can be built; determine deliverables with packaging rules. If the project already varies directories by branch, follow its rules and consider whether a merge would bring in those directories. Do not reorganize an existing repository without authorization.

### 3. Work without disturbing existing changes

- A dirty worktree can support local edits. Do not clear, commit, or stash all user changes just to make it clean. Before and after changes, be able to attribute the diff to this task.
- When context must switch or multiple people work concurrently, prefer a suitable independent worktree. Inspect existing worktrees first and decide whether uncommitted changes should be included; a worktree does not copy them automatically.
- Different AI agents must not use one index to run add, commit, or branch switching in parallel. Separate branches and directories may still share references and Git configuration, so coordinate integration.
- Do not change global identity, line endings, hooks, or default pull behavior for one project. If identity is missing, obtain the real identity or use a repository-level identity specified by the user; never invent an author.

### 4. Review the actual snapshot before committing

Commit only when the task includes a commit. Inspect the staged file list first and preserve staged work that belongs to others. Stage this task's changes by explicit paths or hunks; do not run unverified git add ., git add -A, or git commit -a.

```sh
git diff --cached --name-status
git diff --cached --stat
git diff --cached --check
git diff --cached
```

Check that the complete change is on the correct branch; source, relevant tests, dependency declarations, and required lockfiles are in sync; no user changes, credentials, logs, data, or build outputs were included; and the commit subject accurately summarizes the staged diff. Inspect sensitive material locally without displaying it in the conversation.

Compare every staged addition, modification, deletion, and rename with the task's file list. Resolve any out-of-scope path before proceeding. Derive the commit message from the final snapshot; its subject should say what changed on which object. Explain reasons and impact in the body for complex changes. Meet the acceptance rules in [Commits and Collaboration](references/commits-and-collaboration.md) before committing. After the operation, verify the actual commit with git show --name-status --format=fuller HEAD instead of relying on the pre-commit plan.

Use project-required checks that match the change. When the worktree contains extra modifications, passing tests on the worktree does not prove the staged snapshot is valid. If needed, verify the candidate snapshot and its untracked dependencies in an isolated environment. Fix failures or explain blockers; do not bypass rules with --no-verify or report tests as passing when they were not run.

### 5. Synchronize, deliver, and report status

When current remote facts are needed, fetch first and inspect target references and divergence; remote-tracking references may be stale. Choose merge, rebase, or fast-forward before executing. Do not guess based on ambiguous pull configuration.

Before pushing, inspect the actual remote, target branch, all pending commits, and file history to be pushed. If a push triggers CI, deployment, or release, include that consequence in the authorization scope. Use an explicit target and avoid --all, --mirror, or bulk tag pushes. Follow the project's gates for merging and release.

At the end, report the conventions chosen or reused, changes and checks, current branch, whether a commit, push, pull request, or release was made, and any remaining user action. Do not conflate “done locally,” “updated remotely,” and “released.”

## Boundaries that should not be guessed

- Do not overwrite user changes or include someone else's staged content just to commit this task.
- “Clean up the repository” does not automatically authorize deleting all ignored or untracked files, all stashes, remote branches, or history. Identify the objects and their recoverability first; see the cleanup reference for details.
- Routine synchronization does not require rewriting shared history. If a task truly requires it, identify the references to be replaced, impact, and recovery plan first. Execute only with explicit authorization; do not infer permission from the fact that lease is safer.
- Private repositories, dev branches, LFS, .gitignore, and release exclusion rules are not credential-storage solutions.

## Self-check

Before finishing, ask five questions: Does each action fit the user's task? Is the branch strategy based on actual needs? Does file classification explain the difference between local retention and deletion? Do commits and pushes contain out-of-scope content? Do high-risk operations have evidence, authorization, and recovery measures? When uncertain, narrow the action and complete the verifiable parts first.
