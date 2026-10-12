---
name: skill-search
description: Find agent skills for explicit skill-search requests or for a capability gap in a complex project where a specialized method could help. Use when the user asks to find, search for, or recommend a skill, or asks whether a skill exists for a task. First inspect existing capabilities, then search, verify, and recommend candidates that address the gap. Do not launch a skill search for ordinary tasks or vague requests to “search.”
metadata:
  version: "0.2.0"
---

# Skill Search: Deciding When and How to Search

Find skills that can improve the task and explain why they fit. Search is a means, not the goal. If an existing capability is suitable, use it; if no suitable candidate is found, say so instead of padding a recommendation list.

## First decide whether a search is useful

- If the user explicitly asks to search for, recommend, or compare skills, follow the requested scope. “Search for papers” or “search for open-source projects” is not itself a skill-search request; use context to determine what they want to find.
- For a complex project, first identify a stage that a specialized method could improve, such as cross-tool implementation, a need for domain conventions, or multi-stage verification. Search only when you can describe the expected improvement. Project size, a long prompt, or many steps alone are not reasons to search.
- If the host and existing skills can handle an ordinary task, do it directly. A one-off complex task may still benefit from a skill; repetition is not the only criterion.
- If the user already named a skill, confirm its source and exact identifier, check the CLI, and provide the installation command without running discovery again.

Proactive searches should support an already authorized project. After finding a useful method, return to implementation. If the user only asks for recommendations, deliver recommendations and do not execute the underlying task. A search or recommendation is not authorization to install.

Search for agent skills. Use skill directories to discover candidates and primary sources such as GitHub to locate and verify their ``SKILL.md``, scripts, and templates. If the user also asks for software projects, use the host's relevant capability for that search and evaluate the skills separately; a software repository is not a skill recommendation merely because its name is related.

## Define the search target from the capability gap

State what stage should improve, the expected output, and the current gap. Then check which relevant skills the host already provides. Reuse existing skills when they cover the task; search only for missing capabilities when they cover part of it. Judge by actual capabilities rather than using the user's identity, a domain label, or a plugin name as a fixed entry point.

When the user explicitly asks for external searches, alternatives, or a comparison, use existing skills as a baseline and complete the requested search. If no suitable local skill exists, do not make the user ask again for an external alternative.

For complex projects, focus on the stage most in need of a specialized method. Do not search for a separate skill for every subtask or combine the entire request into one long query. These examples illustrate how to set a target but are not exhaustive:

| Task | Search target | What would make a candidate useful |
| --- | --- | --- |
| A front-end page lacks a clear visual hierarchy | Composition, typography, or visual design methods | It guides concrete design decisions instead of listing framework commands. |
| A cross-tool workflow needs reliable implementation | The actual tools and weak stages, such as end-to-end testing or continuous integration | It fills gaps in implementation steps, failure handling, or verification. |
| A research project needs paper-reading or writing support | One specific need: close reading, literature search, argument writing, or format checks | Reading is not systematic literature search; format checks are not general-purpose writing. |

## Check the CLI before using it

Before invoking the CLI, run:

```sh
npx skills --help
```

Check the current syntax for ``find``, ``add``, and any options you plan to use. Follow the installed version's help instead of copying subcommands from an old skill; an older copy may still mention a removed ``check`` command. Consult subcommand help for options not shown. Verify installation syntax before providing a command. If the CLI cannot be run, say “not verified in this environment”; do not claim it was verified or installed.

## Use a few queries, then read candidate contents

1. Condense the need into a short “task + object/tool” query. For front-end design, use ``frontend design``; for workflow implementation, name the actual stage, such as ``playwright testing`` or ``github actions``, instead of searching only for ``workflow automation``.
2. Run ``npx skills find`` with a query rather than entering an empty-query interaction. For example:

   ```sh
   npx skills find "frontend design"
   ```

3. Prioritize relevant official candidates. If narrowing the source helps verify support, use ``--owner``, for example ``npx skills find "frontend design" --owner anthropics``. Limit by owner only when the source is confirmed; do not use it to hide a mismatch.
4. Start with one search. If the wording does not fit, try one more precise task term. Read a small number of the most relevant candidate files and stop once there is enough evidence to support the task or comparison. Two rounds are usually enough to decide whether more search is useful. Continue only when a specific new lead appears or the user requests broader coverage; do not keep trying synonyms. If irrelevant entries keep dominating results, report that this search found no suitable candidate and return to the task.

Directory ranking is only a clue. Past checks found that front-end design with high supply can be easier to match, while niche topics such as paper reading and literature reviews can be crowded out by popular skills with similar wording. Do not treat ranking as semantic relevance or say that a candidate does not exist in the ecosystem just because this search did not find one.

If the CLI is unavailable or fails, distinguish a failed search from unsuitable results. If you need to inspect a skills.sh page, use ``curl -A "Mozilla/5.0"`` to read the specific candidate; in Windows PowerShell, use ``curl.exe``. A fetch timeout does not mean the directory has no results. If the candidate contents were not retrieved, keep its status unverified instead of stacking more APIs or inventing details.

## Verify candidates before recommending them

Check relevance first, then source, then popularity. Install counts do not replace reading the candidate.

- **Task fit:** Read the source ``SKILL.md`` and confirm how it improves the task, what it produces, and its boundaries. Merely containing words such as ``research`` or ``workflow`` does not make a candidate relevant.
- **Source threshold:** Prefer confirmed official organizations such as ``anthropics`` and ``vercel-labs``. Confirm the owner and original files; directory tags and republisher names are not proof of official status. For community sources, cite concrete support from the contents rather than relying on rank.
- **Usability:** When the contents reference scripts, templates, or other skills, check that the required resources exist and that the host has their dependencies. Mark a candidate as unverified rather than usable when only a listing is available, contents cannot be read, or key resources are missing.
- **Metric definitions:** If installs or stars are reported, first determine whether they refer to one skill, the whole repository, or an unknown scope. Repository stars indicate interest in the repository; path copies within one repository are not independent popularity evidence. Do not report repository-level installs as installs for an individual skill, and do not use numbers with unclear scope as a reason to recommend.
- **Low-popularity signal:** Only when the metric is confirmed to cover one skill, treat fewer than 100 installs as a reason for closer verification, not as proof of poor quality. High install counts do not remove the need for the checks above. Do not substitute unverified thresholds such as 1K installs or 100 stars.

Past checks found that ``skills.sh`` sometimes apportioned find-skills repository-wide installs to individual skills, and SkillsMP stars were repeated across multiple skill paths in the same repository. Therefore, explain the scope of any number using evidence from the current search date; do not present a previously observed number as current.

## Real counterexample: a popular Feishu skill pollutes a paper search

Searches for ``paper reading research`` and ``literature review`` once returned entries such as ``lark-doc`` and ``mail`` from ``open.feishu.cn``, with displayed install counts above 740K. They matched wording around documents and mail but did not meet the need for close paper reading or literature reviews.

Wrong: recommend the first-ranked entry and claim that “many users have verified its paper-reading ability.” Right: read the contents, confirm the mismatch, and exclude it. Reuse an existing suitable paper-reading skill when available; use a more precise query when additional skills or comparisons are needed. A single-paper reading skill does not cover systematic literature search. If no suitable candidate remains, describe the gap instead of recommending an unrelated skill.

## Deliver recommendations and stop

List only enough candidates to support a choice. For each, include the skill name and original source link, one concrete reason it fits the task, a key limitation, and the exact installation command. If a metric matters, state its scope and the date it was checked; numbers are not required to make a recommendation based on the contents.

Build installation commands from the verified owner, repository, and skill identifier, for example ``npx skills add <owner/repo> --skill <skill-name>``, replacing placeholders in the final command. For an available local skill, give its entry point instead of asking the user to install it again. Do not install when the user only asks for recommendations. If installation is explicitly authorized, stay within the requested scope and do not default to a global installation or a confirmation-skipping option.

If no candidate fits, say which query was tried and what capability is still missing. If the underlying task was already authorized, continue with it instead of stopping to ask “Would you like me to help?” If the user only asked for a skill search, explain how the task can be done without expanding into implementation.

## Final checklist

- Is this an explicit skill-search request, or a complex task with a describable expected benefit from a specialized method? Can an ordinary task be completed directly?
- Did you check existing capabilities, search only for gaps, and complete any external search or comparison the user explicitly requested?
- Was the command checked against current help? Are the source, skill identifier, and required resources supported by evidence?
- Do recommendations match the task based on their contents? Are individual-skill metrics, repository-level metrics, and unknown scopes kept distinct?
- Were popular but irrelevant candidates excluded? If no suitable result was found, did you stop and say so?
- Did you do only the authorized recommendation, task, or installation, without adding unrelated work just to search?
