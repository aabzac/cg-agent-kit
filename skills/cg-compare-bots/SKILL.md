---
name: cg-compare-bots
description: Compare CodinGame bot versions with reproducible paired matches and honest uncertainty. Use for evaluating a strategy change, checking a strength regression, choosing between candidates, or interpreting local tournament results.
---

# Compare CodinGame bots

## Establish the comparison

1. Read `.ai/project.md`, the match harness and relevant existing experiment records.
   Identify the game's scoring, draws, number of players and legal player positions.
2. State one hypothesis, the primary metric and a decision criterion before running.
   Separate win rate, score difference, rank and runtime; do not substitute one for another.
3. Freeze both versions, opponents, referee, harness, build flags and configuration.
   Record commits plus dirty patches or immutable source/binary hashes where necessary.
   Do not run both versions from an output path that later builds overwrite.
4. Verify that both builds run legally. Treat protocol errors and timeouts as outcomes
   under a stated policy, and report their counts separately from normal losses.

## Run a reproducible series

5. Choose and record a seed list, opponent mix, sample budget and stopping rule.
   Keep exploratory/tuning scenarios separate from a fresh evaluation set.
6. Pair candidate and baseline on the same scenarios and equivalent opponents.
   For two-player games, swap sides. For multiplayer, use full seat rotations or a
   documented balanced subset appropriate to the budget. Record any missing rotation.
7. Preserve game and bot randomness separately where available. The same game seed
   does not guarantee the same random stream after bots choose different actions.
8. Use equivalent resource limits and avoid CPU contention that changes timeout rates.
   Start with a small smoke batch, then run the planned comparison without tuning midway.
9. Save one raw record per match: scenario/seed, seats, versions, outcome/score/rank,
   legality, timeout status, elapsed time and replay/log location when available.

## Interpret the evidence

10. Report completed and planned counts, distinct scenarios, seat balance, draws,
    failures and the declared treatment of incomplete matches. Never silently drop losses.
11. Compute the primary metric using the correct scoring convention. State whether
    a reported rate counts draws as half a point or excludes them from its denominator.
12. Estimate uncertainty at the independent scenario/seed-group level, preserving
    paired baseline/candidate results and their seat rotations when resampling.
    Use grouped bootstrap or another justified paired method; do not treat swapped
    matches or repeated bot seeds within one scenario as independent evidence.
13. Inspect per-opponent and per-seat results for material regressions. Label these
    as exploratory if they were selected after seeing the aggregate outcome.
14. If evidence is weak, say that the result is inconclusive. More trials of the same
    narrow scenarios do not establish broad generalization to the platform population.
15. Evaluate the chosen candidate on the fresh set once. If its results guide another
    change, relabel that set as development data and obtain a new final evaluation set.

## Record the result

Write a compact entry at the project-defined experiment location with:

- Hypothesis, exact commands, revisions, patches, flags and environment.
- Seeds, seat schedule, opponent versions, metric definition and raw artifact paths.
- Effect estimate, uncertainty method, distinct scenario count and failure counts.
- Decision, observed regressions, and limitations of the local evidence.

Report unavailable harness capabilities or missing measurements explicitly. Do not
claim a platform ranking gain from a local comparison alone. For a promotion decision, apply the
project's policy; `cg-promote-bot` describes the preferred practical 300/1000 protocol and the
common-opponent and boss gates.
