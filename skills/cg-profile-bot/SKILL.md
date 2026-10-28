---
name: cg-profile-bot
description: Profile CodinGame bots and validate performance changes under realistic turn budgets. Use for timeout diagnosis, search bottlenecks, memory pressure, allocation analysis, or measuring whether an optimization helps without weakening play.
---

# Profile a CodinGame bot

## Fix the measurement conditions

1. Read `.ai/project.md` for language/runtime, build flags, platform limits and the
   profiling command. Inspect the build and harness before choosing a profiler.
2. Record bot and harness revisions, dirty patches, compiler/runtime versions,
   optimization flags, hardware, operating system and relevant resource settings.
3. Use the submission-equivalent release build. Distinguish profiler-instrumented
   runs from timing runs; heavy instrumentation and diagnostic output distort latency.
4. Separate process startup/first-turn work from subsequent turns. For managed runtimes
   such as Java, account for class loading, JIT compilation, garbage collection and
   warmup while preserving the platform's real process lifetime. Do not warm up away
   startup cost when the platform charges it to the first-turn budget.

## Capture representative work

5. Select fixed replay states or scenarios spanning opening, typical, dense, late-game
   and known worst cases. Include both the development set and fresh validation states.
6. Measure whole-turn wall time under the actual budget, plus CPU time or allocations
   when useful. Keep parsing, decision logic and output overhead in the accounted path.
7. Record sample counts, median, tail percentiles, observed maximum and timeouts.
   State the percentile method and avoid precise tail claims from a tiny sample.
8. Where available, record search nodes, simulations, depth, branching, cache hits
   and allocations. Use these to explain a change, not as substitutes for latency
   or playing strength. Preserve deterministic seeds or work limits for diagnosis.
9. Alternate or interleave baseline/candidate measurements to reduce thermal and
   background-load bias. Avoid concurrent matches that create unrepresentative contention.

When the platform starts a fresh process per game, reproduce that lifetime for timing-sensitive
strength checks, especially after adding work outside the cooperative turn timer. Compare the
same maps/seats against a same-session control; do not extrapolate a continuously warmed local
bench to the platform. Inspect completed search work and budget saturation by game phase as
well as response times: zero timeouts can coexist with much less search and weaker decisions.
Back Track King's `docs/cold-timing-30x20-v1.md` (2026-10-22, retained at `2fc4980`) demonstrated
this distinction; its board dimensions and millisecond budgets are not general defaults.

## Optimize and validate

10. Use profiler evidence to select a bottleneck. Form a specific hypothesis and
    change one relevant mechanism at a time before measuring again.
11. Check correctness after changes to state reuse, caching, allocations, move ordering
    or numeric representations. Preserve required protocol behavior and legal actions.
12. Compare equal-work runs to diagnose implementation speed, then equal-time runs
    to evaluate the actual production search. Keep the two conclusions separate.
13. Recheck startup cost, worst cases, memory and tail latency on fresh scenarios.
    A faster average with more deadline misses is not a successful budget improvement.
14. Leave measured headroom for platform variability; do not claim that local hardware
    proves compliance with a remote machine's time limit.
15. Use `cg-compare-bots` when the change affects search decisions, depth, pruning,
    randomness or available computation. A speedup alone does not prove stronger play.

## Record the result

Save exact commands, environment, revisions, scenario list, raw timings and profiler
artifacts at the project-defined location. Report the measured bottleneck, before/after
latency and failure counts, behavior checks, and remaining platform uncertainty.
Identify unavailable measurements instead of estimating them as if observed.
