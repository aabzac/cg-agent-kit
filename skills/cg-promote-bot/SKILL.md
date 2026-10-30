---
name: cg-promote-bot
description: Plan CodinGame bot experiments and promotions through validated proxy screens, fresh replication, regression guards and repeated arena placements compared within one league. Use when deciding whether a candidate replaces the selected submission, defining promotion or rollback criteria, interpreting benchmarks or arena uploads, or diagnosing local results that disagree with the arena.
---

# Experiments, evidence and promotion

Read when planning a strategy experiment, interpreting benchmarks or diagnosing disagreement
with the arena. Follow the project's existing policy; the examples below are not universal gates.
Run each series as described in `cg-compare-bots`; this skill decides what the series must show.

## 1. Define the comparison before measuring it

Record the hypothesis, candidate and control revisions, full resolved parameters, map source and
identities, sides, RNG seeds, timing profile, worker count, sample size and decision rule. Use
fresh bots and state for each game. Keep unrelated experimental flags off. A disabled feature
should preserve baseline choices with ample search time; also check runtime effects of extra
initialization, buffers or changed scheduling.

Distinguish three purposes:

- Smoke/regression checks establish legal output, wiring, simulation isolation and the intended
  local behavior. They do not establish match strength.
- Screens and ablations explore whether a mechanism merits further work. Record every tested
  variant, including failures; selected examples and map-size splits are exploratory evidence.
- Confirmation tests a fixed candidate on previously unused, representative maps under a
  predeclared policy. Repeated tuning on the confirmation pool makes it a development pool.

Do not extend a fixed sample until significance appears, change the interval method afterward,
or describe a selected exploratory winner as independent confirmation. An inconclusive
screen is not proof of no benefit and need not ban future research: a new independent experiment
may be justified by mechanism evidence or additional controls, subject to the project's policy.
If using sequential testing, choose a method with appropriate stopping rules before starting.

"One run, no tuning" is for confirming a fixed candidate. A new heuristic bot built from a
post-mortem gets an explicit iteration budget on development maps first; its zeroth iteration
(e.g. one that leaves paint unspent) measures nothing about the idea.

## 2. Select and freeze the project's promotion policy

Read the adopted policy id, amendment date, thresholds and authorization boundaries from
`.ai/project.md`. Do not combine gates from different revisions or rewrite old verdicts.
If no policy exists, propose the staged workflow below and record the chosen parameters before
measuring. Sample sizes and margins are contest settings, not universal constants.

For the latest Back Track King procedure and its exact numbers, read
[the dated policy reference](references/back-track-king-policy.md). It supersedes that contest's
80/120-game live-confirmation stage with a short live filter and repeated arena placements.
Projects that explicitly adopted `practical-300-1000-v2`, BTK's superseded September policy,
keep [that alternative](references/practical-300-1000.md); do not mix it with BTK v4 or v5.

### Stage the evidence from cheap screens to the target population

1. Establish engine fidelity, zero bot errors, source-size compliance and a strict process check
   of the exact submission. Check cold-start costs before expensive strength testing. Give a new
   heuristic an explicit development budget, then freeze it before the promotion series.
2. Validate the screening opponent against the relevant live population: behavior fingerprints,
   performance against the selected version, and known candidate ordering. Record the validation
   id and invalidate it when the proxy, boss, league or relevant meta changes. A proxy equal to
   the candidate cannot screen that candidate; use the project's declared fallback or stop.
3. Screen candidate and selected control against that proxy on identical fresh maps, seeds,
   seats and resource limits, with both arms measured in the same run. Apply the declared
   practical effect threshold; preserve all tried arms, not just the winner.
4. Replicate a passing frozen arm on a new map pool with the same proxy and matched control
   before spending scarce live/API games. Require the declared replication and pooled-effect
   criteria. A failed replication stops the candidate under this policy; do not retune it and
   still call the next run independent confirmation. Pool only when the policy specifies how.
5. Run the selected-version regression guard on its own fresh paired pool. The mirror is a
   guard against damaging existing play, not the sole objective for meta-motivated changes.
   A practical score floor is not a statistical proof of non-inferiority.
6. Use a short paired live session as a filter when the project requires one. Match the maps,
   seeds and seats, refresh the control in the same session, and apply its continuation rule.
   Passing a noisy boss filter does not prove improvement against the arena population.
7. Evaluate the candidate through the declared number of separate arena placements of the
   SAME verified artifact. Before EVERY Submit, including a repeat or rollback, save the current
   live entry and available replays; old agent history may disappear. Then watch the new upload
   through placement: a league promotion at its end can replace the agent and drop its games.
   Use `cg-fetch-replays`. Keep the selected rollback artifact available throughout the trial.
8. Record each upload's agent id, artifact hash, source/configuration identity, league, time,
   placement-completion signal, FIRST completed placement score and whether its games replay
   as the artifact (`cg-fetch-replays`). Multiple snapshots of one upload are not multiple
   placements. Do not mix partial-placement scores with completed ones unless the policy names
   the exception, such as a placement cut short by a league promotion.
9. Apply the predeclared arena rule only after the required candidate and baseline evidence is
   complete, except for an explicitly allowed early rollback. Compare placement scores within
   one league only; after a league promotion, rebuild the selected version's baseline there.
   Report any policy-required opponent-adjusted performance and its model assumptions. Raw win
   rates and shared-opponent deltas move with the opponents the matchmaker served: in Back Track
   King, identical bytes showed shared-opponent deltas of -14.2 and +8.5 pp. Keep them as context.
10. Estimate placement noise from repeated uploads of an unchanged configuration/build in one
    league, using a declared calibration cohort/window and margin rule; state any pooling across
    leagues as an assumption. Keep model uncertainty separate from upload-to-upload variability;
    two placements give a fragile noise estimate. Missing required baseline placements, rating
    inputs or uncertainty estimates mean pending evidence, not an automatic pass. Label any
    predeclared provisional margin as provisional.
11. Follow the declared rollback/promotion logic exactly. A practical policy may promote when
    all gates pass and the candidate is not clearly worse; do not silently add a significance
    requirement for superiority or claim superiority from that decision. Keep the failure rule's
    AND/OR conditions explicit. Early rollback replaces the remaining candidate trial, not the
    obligation to preserve evidence and restore the verified selected artifact.
12. Record the decision, then freeze source AND effective parameters, update pins/defaults and
    the version catalog under the project's authorization. Relabel upload evidence only after
    checking configuration identity and code comparability. A promoted default may have a new
    display/build marker; revalidate the rebuilt artifact and log its upload separately. Passing
    checks does not itself authorize an upload or promotion; use existing user authorization.

Keep one candidate summary: policy revision, hypothesis, all arms, proxy validation id, each
stage's pools/results, artifact hashes, upload ids, margin calibration, final verdict and next
action. Preserve rejected evidence. Amend policies prospectively; label retrospective reuse of
old screens explicitly and preserve the original verdict alongside the re-evaluation.

## 3. Preserve paired evidence and independent map coverage

Play A as P0 and P1 on the SAME initialization, not merely alternating sides on different maps.
Identify maps by a hash of their full initialization, not just replay filename; distinguish map
seed from bot RNG/run seed. Empty, malformed or missing explicitly selected map pools must fail,
not silently switch to a generator. Validate a ported generator against canonical maps before
calling its distribution authentic; an approximate generator remains a separate test domain.

Both sides of one map, and repetitions of that map, are dependent observations. Choose an
uncertainty method appropriate to the sampling design, grouping by map where applicable. A
per-game binomial/Wilson interval does not automatically cover paired, repeated-map results.
Report both game count and distinct-map count. Repeated games can probe stochastic variation
on known maps but do not supply new independent map coverage. No fixed game count guarantees
a particular interval width, and no confidence interval fixes an unrepresentative opponent pool.

Separate the practical effect threshold from statistical uncertainty. For example, a project
may require at least 55% plus a lower 95% bound above 50%; 55.7% with a 44.6-66.8% interval
does not pass that rule. Hoeffding bounds are one conservative option, not a mandatory method.
Choose sample sizes with the desired effect and actual interval method in mind; 300-game
screens and 1000-game confirmations are examples, not universally sufficient evidence.

Retain machine-readable per-game scores, winner, P0/P1-to-A/B mapping, map hash, errors and
timing, as well as aggregates. Include effective parameters, code revision/dirty-state identity,
runtime version, worker count and numerical search budgets. Preserve enough evidence outside
disposable build output to recover the promoted configuration and decision. Compare candidates
through a common opponent using individual results matched by maps, sides, opponent config and
timing; for fresh confirmation, rerun both. Do not compare unrelated historical percentages
or infer a direct head-to-head advantage from a common-opponent comparison.

An explicit project policy may cache an expensive external/boss control for a regression gate.
Retain its individual canonical results, control build/configuration, collection dates and
boss/league identity; replay the same initializations, seeds and seats with the candidate.
Freeze sample size and the comparison rule before play. Reused maps are a regression pool,
not fresh confirmation or proof of noninferiority; the saved control score remains a sample.
Refresh after control/boss/league changes or a development cycle guided by this pool; an
unchanged boss ID cannot rule out hidden updates. A required local continuation
may overlap a sequential remote batch; isolate strict process timing checks and predeclare
completion/stopping rules for both branches. Boss success cannot rescue a failed direct gate.

Live boss gates are noisy: in Back Track King an unchanged control ranged from 11 to 17 wins
of 40 across sessions. Use the policy's current continuation rule and paired uncertainty, not
a universal game-count prescription. Its 2026-10-27 policy uses 40 games only as a live filter
and moves final selection to repeated arena placements; 80/120-game confirmation is historical.
Refresh cached controls after outcome-guided development on their maps. A league promotion
changes the live boss: revalidate the proxy and refresh boss controls in the new league.

## 4. Check that local benches measure the arena

Before the strength loop, check whether self-play against your own frozen versions reproduces
the arena/boss meta: game length, disruption/attack rate, share of turns with full resource use,
project completion rate. In Back Track King the mirror bench played 90-turn passive games while
the arena played 47-57-turn games with 99% sabotage; every mechanism motivated by arena data
failed the mirror bench for structural reasons and was discarded. This was the most expensive
lesson of that contest.

If the meta differs, build and **validate** a meta-matched local opponent: fit its decisions on
the boss/leader replay corpus and check that it reproduces the stats and the known ordering of
past candidates. For meta-motivated mechanisms, use a declared regression guard versus self
alongside proxy gain, fresh replication and the project's live/arena stages. Record the complete
rule before play. Check fresh replication and stratify diagnostic states before blaming the proxy:
a replay action-agreement gap can come from different game phases or already-decided positions,
while a failed live transfer can come from selecting a noisy screen winner. Revalidate a changed
proxy against behavior AND predictive candidate ordering; better action agreement alone is not enough.

## 5. Separate fidelity, mechanism and population strength

First validate the relevant replay corpus, especially when local results disagree with CG.
Check player identity and terminal failures before attributing a divergence to engine rules.
Stratify arena observations by submitted agent/version, league, placement stage, map properties
and opponent behavior. Record fetch time and distinguish user-reported rank from API snapshots.
A boss win streak and improvement against similar historical bots are not population-level
validation. Prefer behaviorally varied controls; a retuned old bot is a stress profile, not proof
that it represents a new class of arena opponents.

Select a small opponent panel for behavioral coverage, not version count: many near-clones can
overweight one family. A candidate that failed promotion may still expose useful weaknesses as
an optional opponent. Keep per-opponent results visible; an aggregate win rate can hide a failure
against one style and is not, by itself, a promotion decision.

Watch representative losses and preserve compact pre-turn fixtures. Explicitly label analyses as:

- Known-state evaluation: information legally available before the turn.
- Predicted-reply evaluation: hypothesized opponent actions based only on that information.
- Recorded-action counterfactual: the opponent's actual simultaneous actions are already known.

The last is an oracle diagnostic, not an implementable prediction policy. Reset to the recorded
state for each one-turn counterfactual; do not add its deltas as recoverable final-match points.
Do not score timeout/disqualification turns as normal strategic missed opportunities.

Before widening search or retuning evaluation, trace a missed action through generation,
pruning, affordable execution and ranking on fixed pre-turn states. Deeper search cannot
recover a discarded candidate; test candidate coverage separately from evaluator quality.

Evaluate the affordable actions actually emitted, not only the hypothetical completed plan.
However, a hard veto on temporary income loss can reject useful investments. A regression
fix establishes that a mechanism changed; only broader tests establish whether the tradeoff helps.

For reply models, separately examine prediction quality, evaluation quality and search cost.
Measure decision impact as well as exact action agreement: freeze our candidates/evaluator.
As an oracle diagnostic, evaluate the original choice and oracle-best alternative against
the same recorded reply, counting strict value gains. Poor agreement alone need not justify
a wider model.
Resolve simultaneous combinations through the shared core. Deduplicate candidates by actual
actions when distinct long-term plans yield the same move. Preserve a legal fallback if search
cannot finish; do not rank candidates on unequal partial reply coverage without an explicit rule.
More replies or a wider beam may worsen model bias, conservatism or deadline pressure. A smaller
beam doing better does not by itself identify which of these caused the difference.

Useful new candidates can still weaken play by displacing ordinary comparisons. Measure
coverage at nominal and ample time; test optional search after completing the baseline
comparisons, on the same clock, keeping the saved answer until a new comparison completes.

## 6. Match timing without claiming identical execution

Derive nominal local search budgets from the submission's clock accounting: total allowance
minus input/preparation, safety margin and first-turn warm-up where applicable. Record numbers,
not only a profile name. Keep legacy timing explicitly labelled. The external process still
receives the full protocol deadline; do not subtract the safety margin twice.

Fixed maps/parameters reproduce inputs, not every time-limited decision: JIT, GC, CPU contention,
hardware and warm-up RNG consumption can change explored candidates. Use modest parallelism
and avoid competing CPU-heavy jobs during timing-sensitive comparisons. Measure phase usage,
search completion and expensive atomic operations; a phase cutoff is not a hard time bound.

Test that warm-up actually reaches the expensive branches. A warm-up call shorter than a phase
reserve can do no search. Preserve a usable action while exploring; any early fallback affected
by later actions needs legality/value revalidation. Neither reserves nor fallbacks are automatic
strength improvements. Confirm protocol, startup and later-turn latency using the newly built
submission in a separate process on representative and difficult maps. Local process results,
especially with a timeout grace period, are still not a guarantee about the CG host.
