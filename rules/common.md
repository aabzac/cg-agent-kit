# Common CodinGame working rules

## Sources and project context

- Keep shared rules in `cg-agent-kit/rules/common.md` and shared skills in
  `cg-agent-kit/skills/`. Change those sources when improving the common method.
- Keep contest-specific commands, mechanics references, limits and paths in
  `.ai/project.md`. Generated `AGENTS.md`, `CLAUDE.md`, `.agents/skills/` and
  `.claude/skills/` copies are maintained by the synchronizer; do not edit them.
- Read `.ai/project.md` before selecting a build, test or match command. Treat
  missing values as unknown; inspect the repository to discover valid commands.
  Ask for missing information if the repository does not establish it.
- Use the contest's concrete settings in place of generic defaults. Resolve
  contradictory instructions explicitly before an affected experiment.
- Preserve unrelated files and work in progress. Record the current revision and
  dirty state before changing a baseline or running a comparison.

## Mechanics and executable behavior

- Treat the official rules and the matching referee version as primary evidence.
  Record the league and version; distinguish confirmed behavior from assumptions.
- Keep the bot's stdout strictly within the required protocol. Send diagnostic
  output to stderr and keep diagnostics outside performance measurements.
- Check startup and per-turn limits separately. Account for the actual language,
  runtime, compiler flags and process lifetime used by the platform.
- Validate simulation changes against authoritative transitions before relying on
  them for search or performance claims. Local self-consistency is not proof that
  a simulator implements the game correctly.

## Experiments and conclusions

- State the hypothesis and success metric before a comparison. Freeze candidate,
  baseline, harness and referee revisions; preserve any uncommitted patch and
  relevant configuration needed to reconstruct the run.
- Use reproducible seeds, identical scenarios and balanced player positions.
  Swap sides for two-player games; use documented seat rotations for multiplayer.
- Keep tuning seeds separate from a fresh evaluation set. Do not repeatedly tune
  against a set still described as a holdout.
- Report sample size, draws, failures, timeouts, opponent mix and uncertainty.
  Treat matches sharing a seed/scenario as a group when estimating uncertainty;
  seat swaps are not independent samples.
- Keep raw results and a compact experiment record at the project-defined path.
  Include exact commands, revisions, seeds, environment and artifact locations.
- Distinguish a successful build, a simulator check, a local strength comparison
  and a platform ranking result. Claim only the improvement the evidence supports.
- Measure relevant worst cases and tail latency as well as averages. Recheck bot
  legality and strength after performance changes that alter search behavior.

## Completion

- Run checks proportionate to the change. Report what passed, what was not run,
  any remaining uncertainty and how to reproduce the relevant result.
- Keep shared methodology independent of a specific contest's language, paths or
  strategy. Put those details in the contest's `.ai/project.md`.
