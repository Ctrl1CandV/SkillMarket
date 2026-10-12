# Tracking Files, Keeping Them Local, and External Storage

## Classify by purpose

First inspect how the project is built, tested, and delivered, then classify actual paths. The following are recommendations, not decisions to make mechanically from file extensions.

| Category | Usual treatment | Decision criteria |
|---|---|---|
| Source code, tests, build/dependency declarations, CI, database migrations, installation docs | Track in Git | A fresh clone should explain and rebuild this version; small test fixtures must be distributable and sanitized. |
| Team configuration, format rules, .gitignore, necessary .gitattributes | Track in Git | Include shareable defaults; avoid personal absolute paths and real credentials. |
| Dependency lockfiles | Track according to tool conventions; usually keep them | Keep synchronized with the manifest. Do not ignore them universally because they are generated or because the project is a library. |
| Installed dependency directories, virtual environments, compiler caches, reproducible logs | Ignore; clean selectively when needed | Confirm they can really be rebuilt. Do not decide from the name alone that build/ or dist/ is disposable. |
| Compiled output, generated code, web sites, exported PDFs | Usually use artifact storage; sometimes track | Track when downstream users consume it directly, generated code is required by policy, or rebuilding is unreliable. Record how it is generated and its update rules. |
| Secrets, tokens, private keys, credential-bearing connection strings, real .env files | Secret manager or secure local storage | Never put in ordinary branches or LFS. Example files contain placeholders only. |
| Private notes, personal IDE settings, temporary drafts | Local or user-selected private storage | Shared team IDE settings may be tracked; do not include personal state with them. |
| Raw data, model weights, large videos, binary design sources | Use LFS or external storage based on permissions/size | Keep license, availability, version identity, and integrity records. LFS suits assets that need to collaborate alongside source revisions. |
| Research configuration, seeds, environment declarations, small result indexes | Usually track in Git | Store raw run output elsewhere; preserve versions, data identifiers, and a reproduction entry point instead of putting every output in Git. |
| Review records and historical notes required by the project | Track or store on the agreed branch | Keep material with continuing use. Temporary work notes do not automatically belong in Git. |

Generated does not mean “do not track”: npm recommends committing package-lock.json, while Cargo explains Cargo.lock determinism and constraints for library consumers. Follow current official documentation and project conventions for the actual tool. [npm lockfile](https://docs.npmjs.com/cli/v11/configuring-npm/package-lock-json/), [Cargo FAQ](https://doc.rust-lang.org/cargo/faq.html)

Do not ignore *.json, *.yaml, *.csv, *.pdf, *.lock, all of data/, or every hidden directory by default; they may contain configuration, test data, a manuscript, or a deliverable. Review framework-template ignore rules against the actual project.

## Turn classification into a commit checklist

Before staging, list exact files or a directory reviewed file by file. For each, state target branch, purpose in this change, whether it is tracked, destination (commit/local/external/pending), and reason. A short note in the task record is enough for a small change; a governance document is not required every time. Check both ends of additions, modifications, deletions, and renames; do not filter only untracked files.

| Content likely to slip into a commit | Default handling | Exceptions to verify |
|---|---|---|
| testt/, temporary debugging directory, one-off smoke file | Do not stage until purpose is known; keep local and clean only after confirming it is reproducible | If it is a test source maintained by the team, track it according to project rules. Do not decide from a suspected typo. |
| Formal tests/ and regression fixtures | Usually track with the relevant source | A release package may exclude them. If the repository deliberately separates runtime and maintenance branches, put them in the defined location; do not ignore tests globally. |
| private/, personal notes, internal drafts, real configuration | By default keep local or in separately permissioned storage; exclude from all ordinary branches | A directory named private may contain legitimate code; inspect contents and project rules. Share materials only when explicitly allowed and sanitized. |
| Agent plans, conversation exports, temporary review/verification reports, screenshots | Keep local unless the current task needs a maintained record; when retention is required, use the maintenance location | Reusable conventions, user docs, and formal design decisions may have a clear purpose. Do not exclude something solely because AI generated it. |
| Project documentation | Keep installation, interfaces, build, and usage documents required for the version | Handle meeting notes, work diaries, evaluations, and archives according to branch and permissions. Do not omit references needed by the citation chain. |

When adding a skill/plugin, follow relative references from SKILL.md and check its scripts, references, and templates so recipients can run it. Evaluation code and runtime dependencies are different categories. Before running git add -- DIRECTORY, confirm every added file in that directory is on the checklist; otherwise stage explicit paths.

Put **shared project ignore rules** in an appropriate .gitignore; personal rules belong in the local exclude file. For already tracked files, follow the later instructions; adding an ignore rule does not untrack them. Maintenance files tracked only on dev and excluded from main should be managed through branch integration scope; do not globally ignore them on dev as a substitute for branch rules.

Before commit, reconcile git diff --cached --name-status against the checklist. Before push, check paths from every pending commit too. Being under an allowed directory does not mean a file is authorized for this task; both branch scope and task checklist must be satisfied. For an unknown classification, retain the file and keep it out of the commit; do not delete it automatically.

## Three ignore layers

- .gitignore: shared project ignore rules, versioned with the repository.
- Repository-local exclude: personal helper rules for this repository, usually .git/info/exclude. In a worktree, locate the actual path with git rev-parse --git-path info/exclude.
- core.excludesFile: user's personal ignore rules across repositories. Do not change global configuration for one project.

Ignore rules affect only untracked files. Tracked files are still inspected and committed. assume-unchanged and skip-worktree are index features; do not use them as a reliable way to hide local configuration from a commit. [gitignore documentation](https://git-scm.com/docs/gitignore), [Git FAQ](https://git-scm.com/docs/gitfaq)

When tracking a default configuration while keeping local differences, separate versioned defaults/example from an ignored local override and make the program's loading behavior explicit. Do not hide a local password with a Git flag on a tracked configuration.

The following are optional rule snippets, not a complete generic template. Confirm the path and purpose before copying:

```gitignore
# Use only when these are reinstallable/rebuildable in this project
node_modules/
.venv/
__pycache__/
*.py[cod]
/coverage/

# Local environment; first confirm examples contain placeholders
.env
.env.*
!.env.example
!.env.sample

# Allow small fixtures rather than ignoring the parent directory
/data/*
!/data/fixtures/
```

/name/ is anchored at the current .gitignore level; name/ can match directories of the same name below it. A negation cannot re-include files inside an ignored parent directory. Verify a candidate rule:

```sh
git check-ignore -v -- path/to/local-file
git ls-files -- path/to/file
git ls-files --others --exclude-standard
git ls-files --others --ignored --exclude-standard
```

By default, check-ignore does not report tracked files. To diagnose which rules match them, use git check-ignore -v --no-index -- path/to/file. Exit code 1 means no match and is not an execution failure. [git check-ignore](https://git-scm.com/docs/git-check-ignore)

## Stop tracking a file while keeping its local copy

Use for local configuration or caches that should no longer be tracked. First inspect staged and unstaged state and make a safe backup if needed; do not use -f to bypass state checks. After adding a precise ignore rule:

```sh
git rm --cached -- path/to/local-file
git diff --cached --name-status
```

--cached removes the path from the index but leaves the worktree file in place. The next commit records its deletion from the version tree. This does not erase history. Other collaborators updating to that deletion commit may lose their previously tracked copy, so arrange local configuration migration first. It may also remove a mistakenly staged addition from the first commit. Do not run git rm -r --cached . to rebuild the entire index for one path. [git rm](https://git-scm.com/docs/git-rm)

Stopping tracking, deleting a file from disk, and purging history are three different operations. If the file contains sensitive information, follow [credential exposure handling](recovery-and-cleanup.md); ignore rules and deleting the latest copy are not enough.

## Large files and reproducibility metadata

Check whether a large file must be versioned with source, how often it changes, and whether downstream users can use LFS. LFS stores a pointer in Git and content in LFS storage. Confirm host support, permissions, quota, and that content can be downloaded before choosing it; do not hardcode one host's limits. [Git LFS](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-git-large-file-storage)

When using LFS, commit the relevant .gitattributes and pointer and verify that the content is available. A new tracking rule does not automatically convert older commits to LFS. Treat history migration as a separate, explicitly authorized operation. For external storage, record artifact/data ID, version, checksum, license, retrieval method, and required access. Avoid keeping expiring signed URLs with credentials in a manifest.

For large ordinary Git files, inspect the history to be pushed, not only the current worktree size; a commit that deletes a large file may still push its old object. Do not rewrite repository history without first investigating.

## Cross-platform and nested repositories

Put shared line-ending, binary-detection, and archive rules in .gitattributes. Before adopting * text=auto or script-specific EOL rules, inspect existing behavior. git add --renormalize can produce a broad diff and should be reviewed separately, not mixed into a feature fix. [gitattributes](https://git-scm.com/docs/gitattributes)

Check case-only renames, executable bits, symlinks, and platform-specific paths; Linux CI and a case-insensitive local filesystem may behave differently. If a nested .git directory appears, determine whether it is a submodule, independent project, or accidental nesting; do not delete .git to “tidy up.” For a submodule, record an accessible URL and exact commit instead of committing a local independent repository as an ordinary directory.
