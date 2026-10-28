---
name: cg-promote-bot
description: Plan CodinGame bot experiments and decide promotions with predeclared evidence rules, the preferred practical 300/1000 protocol, matched common-opponent and boss gates, meta-matched opponents and aligned timing. Use when deciding whether a candidate replaces the selected submission, designing a screen or confirmation, interpreting benchmarks, or diagnosing local results that disagree with the arena.
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

## Preferred practical 300/1000 protocol

This is the user's preferred practical selection policy, not a statistical test with an overall
95% error guarantee. Use it when requested or when establishing a new project's policy; an
existing explicit project policy takes precedence until deliberately updated. Record adoption
in project rules, reports and decision tooling. Confidence intervals remain descriptive diagnostics.
Current revision: `practical-300-1000-v2`, with a strict >52% continuation floor after 300 games.

1. Freeze candidate A, selected control B, and an older or behaviorally different opponent C.
   Predeclare fresh representative map pools, both sides per map, identical nominal time budgets,
   workers, full parameters and all branch rules. Draws count as half a win.
2. A vs B: exactly 300 games / 150 distinct maps. A score >=60% passes the direct stage.
   A score <=52% stops evaluation: retain the candidate/evidence, with no automatic continuation.
   Only for 52% < score <60%, run separate fixed 1000 games / 500 new maps: pass at >=55%
   in those 1000 alone. Exactly 52% stops; exactly 60% passes the direct stage.
   Do not pool the 300 with the 1000, tune between stages, retry failures or stop early on a
   running win rate. A completed direct-stage failure stops promotion evaluation.
3. After direct-stage success, run A vs C and B vs C, 300 games each, on the SAME new 150 maps,
   sides, seeds, C parameters, timing profile and worker count. Compare matched per-map scores.
   Candidate minus control >=3 percentage points passes this stage. This margin is a chosen
   practical cutoff, not a confidence interval or proof of superiority.
4. Otherwise run A vs C and B vs C, 1000 games each, on the SAME separate new 500 maps.
   Use only this larger matched sample: pass if candidate score >= control score; a tie passes.
   If it fails, retain the candidate and evidence without promotion or another automatic retry.
5. Both strength stages are required. Fast passage of the first 300 skips only the direct 1000;
   it never skips the common-opponent, error, engine-fidelity or exact-artifact process checks.
   Preserve project authorization boundaries: passing checks does not authorize arena upload
   or silently changing the selected submission.

The 52% floor is a cost/sensitivity tradeoff, not proof that a stopped candidate is weak or an
empirically optimal threshold. Prefer it over 53% when avoiding premature rejection matters:
one percentage point is only three win-equivalent points in 300 games. A higher floor saves
more work but discards more borderline candidates. Choose it before play; do not adjust it to
rescue or reject a seen result. It applies only to the first direct 300, not to the 1000-game
55% threshold or the common-opponent stages. Preserve historical policy ids and decisions.

Reuse a completed 300-game screen only when explicitly applying a newly adopted rule to an
existing candidate: verify unchanged implementation/configuration, label the policy change as
retrospective, preserve the old verdict, and use fresh maps for all subsequent stages. A prior
unmatched opponent percentage cannot substitute for either member of the matched comparison.
Record all outcomes and the selected branch; inconclusive old evidence is not proof of no gain.

## 2. Preserve paired evidence and independent map coverage

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

Live boss gates are noisy. 40 games carry a standard error of about 7.5-8 pp, so a 95% interval
is roughly ±15 pp; in Back Track King an unchanged control drifted between 11 and 17 wins of 40
over weeks. Use 80-120 or more paired games (same maps, seeds and seats as a fresh control) for
decisions; 40 games are a screen. Refresh the cached control after any outcome-guided development
on its maps.

## 3. Check that local benches measure the arena

Before the strength loop, check whether self-play against your own frozen versions reproduces
the arena/boss meta: game length, disruption/attack rate, share of turns with full resource use,
project completion rate. In Back Track King the mirror bench played 90-turn passive games while
the arena played 47-57-turn games with 99% sabotage; every mechanism motivated by arena data
failed the mirror bench for structural reasons and was discarded. This was the most expensive
lesson of that contest.

If the meta differs, build and **validate** a meta-matched local opponent: fit its decisions on
the boss/leader replay corpus and check that it reproduces the stats and the known ordering of
past candidates. Decision rule for meta-motivated mechanisms: non-inferiority versus self
(>=48-50%) AND a gain versus the proxy, then live confirmation. Record which rule applies to a
candidate before play.

## 4. Separate fidelity, mechanism and population strength

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

## 5. Match timing without claiming identical execution

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
