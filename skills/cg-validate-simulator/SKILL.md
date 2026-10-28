---
name: cg-validate-simulator
description: Validate a CodinGame simulator against official mechanics and an authoritative referee. Use when implementing or changing game transitions, investigating divergent replays, or checking whether a simulator is reliable enough for search and experiments.
---

# Validate a CodinGame simulator

## Define the authority and comparison

1. Read `.ai/project.md` and locate the official rules, referee version and league.
   Record their exact versions and any known discrepancies. Do not assume that a
   referee from another league implements the same legal actions or scoring.
2. Identify the simulator interface and state representation. Map units, ownership,
   coordinates, resources, scores, turn counters and terminal conditions to the referee.
3. Separate full referee state from information observable by each player. Validate
   both the transition and observation projection without exposing hidden information
   to the bot or granting the simulator facts unavailable during real play.
4. Build a reproducible adapter that feeds the same initial state and action sequence
   to both implementations. Record game seeds and random outcomes where accessible.
   If exact RNG synchronization is impossible, test controlled deterministic transitions
   separately and describe what stochastic behavior remains unverified.

## Exercise the mechanics

5. Compare state after every meaningful transition, not only the final winner.
   Compare exact integer/discrete fields; justify any tolerance for floating-point fields
   using the game's actual rounding and precision rules.
6. Cover legal and invalid actions, no-op behavior, minimum/maximum resources,
   boundaries, collisions, ties, simultaneous actions, elimination and game termination.
7. Test action ordering: movement, costs, attacks, damage, death, spawning, scoring,
   regeneration and visibility updates. Derive the actual order from the referee.
8. Check rounding, integer overflow where relevant, coordinate conventions, timing
   counters and special first/last-turn behavior. Exercise league-specific mechanics.
9. Add generated legal action sequences with fixed seeds and targeted edge cases.
   Check conservation and other invariants as additional evidence; invariants alone
   cannot establish agreement with the official implementation.

## Diagnose and prevent divergence

10. Stop at the first divergent transition. Save the smallest useful reproducer:
    versions, seed or initial state, prior actions, triggering action and field-level diff.
11. Reduce the state/action sequence while preserving the divergence. Determine
    whether the defect is in the simulator, adapter, observation mapping or assumption.
12. Fix the underlying rule and add a focused regression case from that reproducer.
    Rerun the failing case plus affected mechanics and a representative seeded batch.
13. If only observed replays are available, validate observable outputs and mark hidden
    transitions unverified. Do not label replay agreement as full-state equivalence.
14. If the authoritative referee cannot be run, report the narrower evidence from
    source inspection and invariant tests. Keep unsupported mechanics explicit.

## Report reliability

Record the referee/league version, simulator revision, tested mechanics, scenario
and transition counts, remaining limitations and replay locations. Distinguish
observed agreement from a proof of correctness. State which remaining gaps could
invalidate search, strength comparisons or performance conclusions.
