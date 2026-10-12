# SkillMarket

A repository for personal skills and plugins. It turns experience from projects into reusable methods and improves them through actual use.

- [de-ai-flavor](de-ai-flavor/SKILL.md): Identify common writing problems such as vague, awkward, or repetitive prose, and improve new or existing documents, page copy, and replies.
- [readable-reply](readable-reply/SKILL.md): Make AI replies easier to read by avoiding fragments, excessive formatting, and unnecessary length.
- [frontend-craft](frontend-craft/SKILL.md): Improve page composition, typography, color, and visual details while preserving usability and readability. Still in active development.
- [grad-companion](plugins/grad-companion-plugin/): Support paper reading, research records, experiment tracking, and progress reviews during graduate study.
- [agent-parliament](plugins/agent-parliament-plugin/skills/orchestrator/SKILL.md): Organize planning, challenge, implementation, review, and verification without dedicated MCP services; one agent can run the stages in sequence.
- [skill-search](skill-search/SKILL.md): Find skills for explicit skill-search requests or capability gaps in complex projects; inspect existing capabilities and candidate contents, distinguish metric definitions, and stop when no suitable option is found.
- [presentation-craft](presentation-craft/SKILL.md): Create presentations for lab meetings, papers, and courses with free local tools; organize evidence, choose a visual style, produce editable PPTX files with basic click animations, and inspect the exported slides and playback.
- [git-governance](git-governance/SKILL.md): Choose a Git workflow for the project and manage branches, tracked and local-only files, commits, collaboration, releases, and safe cleanup; distinguish Git mechanics, team conventions, and release checklists.

The \`main\` branch contains skills, plugins, and the README. Skill and plugin directories contain only the entry points, references, scripts, and templates needed at runtime. The \`dev\` branch also contains test records, optimization documents, and historical versions under \`maintenance/\`, grouped by skill or plugin. Two page examples (Evening Radio and Street-Corner Flora) are in \`maintenance/frontend-craft/evals/\` on \`dev\`.

Do not commit private materials, real configuration, credentials, or one-off test drafts to any branch. When integrating into \`main\`, select only runtime resources and index changes, inspect the full file list first, and avoid bringing in \`dev\` maintenance materials. Commit messages should identify the skill, actual changes, and any relevant verification.
