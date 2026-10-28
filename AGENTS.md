# Working on cg-agent-kit

This repository is the shared source of CodinGame agent instructions. It is not a contest bot.

- Edit `rules/common.md` for shared rules, `skills/<name>/SKILL.md` for procedures, and `templates/project.md` for the contest-specific template.
- Keep skills portable: use `name` and `description` YAML frontmatter and relative resource links. Do not require a specific agent vendor or an invented contest command.
- Keep `scripts/sync.py` standalone, Python 3.10+ standard library only. Its copy at `.ai/sync.py` must work without this checkout.
- Never overwrite unmanaged files or locally modified generated files. Resolve all path/collision checks before changing any target files.
- Keep `check` read-only and pinned to `.ai/kit.lock.json`; only `update` advances the version. `run` applies the configured tracking/pinned policy before invoking a command.
- Read sources from Git commits, not uncommitted working-tree contents. Preserve offline `--source` operation.
- Validate changes with `python scripts/validate.py` and `python -m unittest discover -s tests -v`.
- Document behavior changes and executable commands in `README.md`. User-facing documentation is in Russian; agent procedures may be in English.
- Do not install these project skills into a user's personal skill catalog unless explicitly requested. Commit and push source changes to this repository when the task includes saving them.

Consumer projects edit `.ai/project.md` for their own rules, then regenerate `AGENTS.md`. Their `.agents/skills/` and `.claude/skills/` copies are generated; shared changes belong here.
