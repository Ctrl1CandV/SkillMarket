# Project Git Policy Template

This template helps define a policy; it is not evidence that a project has implemented one. Fill in actual decisions and remove irrelevant sections. Mark unknown facts “unverified”; do not leave placeholders as final policy. It can be added to an existing CONTRIBUTING file or the project's designated Git-policy document.

## Current state and decisions

- Project purpose, delivery audience, and reproduction entry point:
- Remote roles (upstream, personal fork, release repository):
- Actual main-branch name and availability requirements:
- Release cadence and whether push/tag triggers deployment:
- Supported version lines and end-of-support conditions:
- Selected workflow, reasons, and conditions for creating branches:

## Branch lifecycle

| Branch role/name | Base | Allowed changes | Integration target | Check/review gates | End condition |
|---|---|---|---|---|---|
| Fill in for this project | | | | | |

Which development/maintenance lines receive backports, and how they are recorded:

## Files and delivery

| Exact paths or category | Track/local/external/clean | Reason, reproduction, or retrieval method | Permissions and owner |
|---|---|---|---|
| Fill in for this project | | | |

- Rules for keeping manifests and lockfiles synchronized:
- Location and loading behavior for local configuration and shared defaults/examples:
- Version IDs, checksums, and retrieval methods for large files/LFS/external storage:
- Scope of .gitignore, local exclude, and .gitattributes:
- Release-package manifest and packaging tool:
- Allowed paths and integration/reconciliation for branch-specific directories:
- Rebuildable cleanup targets and local data that must be retained:

| Target branch | Required paths/dependencies | Allowed maintenance material | Exclusions | Pre-integration checks |
|---|---|---|---|---|
| Fill in for this project | | | | |

- Destination for testt/, formal tests, private/, temporary reports, and project docs:
- How to build the exact path list for each commit and handle out-of-scope staged content:

## Commits and review

- Subject format, language, scope, and breaking-change marker:
- Message review: subject identifies object/change; body adds reason/impact; text matches final staged snapshot:
- How to split logical changes and requirements for related tests/docs:
- Staged-snapshot review and verification commands:
- PR/MR target, template, review, and merge strategy:
- Author identity, signing, or DCO rules, if applicable:
- Branch protection and required checks; distinguish “verified enabled” from “recommended”:

## Releases and operation boundaries

- Tag/version policy and mapping between artifacts and commits:
- Release checks, release permissions, rollback, and backport rules:
- Who performs and authorizes commit, push, PR, merge, and deployment:
- Conditions for rewriting shared history/force-push, exact refs, and recovery procedure:
- Preview, preservation, and scope checks before deleting files/branches/worktrees:
- Owner and platform process for credential revocation/rotation:

## Maintenance

- Policy owner, verification date, and review triggers:
- Facts not yet verified or settings not yet implemented:
