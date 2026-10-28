---
name: cg-bot-contest
description: Set up and run a CodinGame bot-programming contest project (Spring, Summer, Fall or Winter Challenge and multiplayer arena games) with a rules engine shared by bot and referee, a local arena, replay validation, a single-file submission, versioning and dev-log discipline, and a strength loop. Use when the user starts a CodinGame contest, asks how to structure a bot project, wants a local referee, arena or visualizer, or asks how to climb leagues methodically.
---

# CodinGame bot contest

Proven workflow from Spring 2026 (Troll Farm) and Summer 2026 (Back Track King). Default stack is
Java 17 + Gradle unless the user prefers otherwise; the process is language-independent.
For an existing project, read its working agreement, `docs/STATUS.md` if present, roadmap and
experiment log first. Preserve its promotion policy unless the user explicitly changes it.
Game-specific weights, time limits and the numbers quoted from past contests are not universal.

Related skills: `cg-fetch-replays` (CG API, replay corpora, boss and IDE capture),
`cg-validate-simulator` (engine fidelity), `cg-compare-bots` (paired series),
`cg-promote-bot` (evidence rules and the preferred practical 300/1000 protocol) and
`cg-profile-bot` (timing). Layout and interfaces are in [architecture.md](architecture.md);
read [pitfalls.md](pitfalls.md) before the first bench or when diagnosing runtime/engine issues.

## Phase 0 — orient (first hour)

1. Read the statement of the current league; save it **verbatim** to `docs/rules/<league>.md`.
   Only the current league's rules are visible; higher leagues add rules. Plan to re-capture at
   every promotion. Referee source is often linked from the statement: port the map generator 1:1.
2. Leaderboard snapshot (see `cg-fetch-replays`): size, open leagues, languages of the top 10.
   Inspect the actual runtime limits before attributing ranking differences to language choice.
3. Download a representative replay corpus (about 100 is a useful starting point). The observed
   `gameResult/findByGameId` response includes both players' stdout; see `cg-fetch-replays` for
   access and terminal-event caveats. Replays are ground truth for rules and development data for
   "what do strong bots do". If the contest is over, also harvest the forum post-mortems of the
   top 10 before planning anything.

## Phase 1 — infrastructure before strategy (day 1)

Build in this order; each item is small and unblocks the next.

1. `core`: state as primitive arrays, `Action` parse/format, `Rules.resolve(state, a0, a1)`,
   pathing helpers with per-thread scratch buffers. JUnit tests from statement examples,
   tie-breaks included.
2. `cgFetch` + `cgValidate`: replay downloaded games through `Rules` and diff placements,
   scores, paths, end turn against viewer events (procedure in `cg-validate-simulator`).
   **Do not trust any bench until this is 100%.** Hidden rules (only readable in higher leagues)
   can usually be inferred here: write a small study tool that histograms the unexplained events.
3. `Bot` interface, `Params` (all weights as public fields, reflection `apply("K=v,K2=v")`,
   `NOISE`/`SEED`), `Timer`, `MainBot`, `CGRunner` (fast token reader, JIT warm-up on turn 1 that
   really reaches search, margin under the turn limit, derived-state cross-check against server
   input), `FileMerger` → `build/submit/Player.java` with a compile check and a source-size check.
4. Referee + maps from replays (or a generator validated against them) + `BenchmarkRunner`
   (paired maps with both seats on the same initialization, map-aware uncertainty, per-side
   rates, timing, errors, full resolved parameters in every JSON report) +
   `ProcessBot`/`ProcessCheck` (merged file as a real process over the protocol on both seats,
   without timeout grace: timeouts!).
5. `cgRender` exports validated replay data separately from read-only `cgValidate`.
   Serve the visualizer over localhost HTTP; check the available browser's access constraints.
6. Docs: the working agreement (below), `docs/STATUS.md`, `docs/PLAN.md` (roadmap with
   checkboxes), `docs/BOTS.md` (version table with bench numbers), `docs/DEVLOG.md` (hypothesis →
   result → decision, failures included) and agent rules for engine fidelity and frozen versions.
   STATUS is half a page: arena entry, league, boss id and rating, selected version, last verdict,
   flags on. Keep it current; otherwise agents reconstruct state from megabytes of log and get it
   wrong.
7. Use the project's version-control workflow; commit when requested. Large replay corpora and
   `build/` can be gitignored; preserve compact regression fixtures and experiment evidence.

## Phase 2 — leagues

- v00 = trivial legal bot, v01 = greedy. Submit as early as possible: leaving Wood exposes the full
  statement. By default the user pastes the verified submission; identify the exact artifact.
- After each promotion: capture statement, reconcile with inferred rules, add tests, re-run
  `cgValidate`.

## Phase 3 — strength loop (rest of the contest)

Read `cg-promote-bot` before designing or interpreting an experiment. First check that self-play
reproduces the arena meta (its measurement-alignment section): in Back Track King a mismatched
mirror bench discarded every arena-motivated mechanism. For boss batches and replay build
attribution, see the IDE/boss capture section of `cg-fetch-replays`. Repeat, one hypothesis at
a time:

1. Find the gap: a `cgStudy`-style tool comparing the winner's moves in replays with the bot's
   moves on the same states (agreement %, action frequencies, game length, idle turns, resources
   spent per turn and whether placed assets ever earn, e.g. paint and cells in Back Track King).
   Also watch lost arena games in the visualizer.
2. Add a default-off `Params` flag and captured-state regression tests. A repaired position is
   mechanism evidence, not proof of overall strength. Keep other experiments explicitly off.
3. Predeclare a paired-map screen against a frozen reference, then apply the project's decision
   rule (including its fixed continuation and stopping conditions). Separate exploratory tuning
   from confirmation on held-out maps; also test an older or behaviorally different opponent.
   Exact simulation does not guarantee accurate opponent replies.
4. For promotion, freeze strategy source AND full effective parameters, record code revision and
   evidence, build with `submit`, then run `procCheck` on that exact artifact. Check applicable
   source-size limits; repeat artifact checks after packaging changes. See
   [architecture.md](architecture.md).
5. Record outcomes (including inconclusive/rejected experiments) in BOTS/DEVLOG/STATUS and update
   PLAN. Leave unpromoted flags off; do not silently replace the known-good submission.

## Opponent model and search

- If one chooser models both sides inside a rollout or search, every "be more aggressive" change
  also makes the simulated opponent more dangerous to your own plans and suppresses your
  construction. Keep per-side parameters; always test the self-only variant; consider an
  explicitly opponent-like second scenario instead of a copy of yourself.
- Check that "two opponent scenarios" really differ (e.g. not the same route inserted from both
  ends with equal value).
- A myopic target valuation (current-board income only) never pre-empts unfinished enemy
  projects and wastes free attack points; cumulative, irreversible resources (instability in
  Back Track King) are worth spending every turn on the opponent's predicted corridors.
- Horizon-limited rollouts overvalue plans that complete late through regions the real opponent
  will destroy; diagnose with recorded cut positions before adding risk terms.

## Compute diagnostics and selective recomputation

- **Budget sensitivity.** An isolated generous-budget comparison can reveal whether more compute
  helps an unchanged policy (Back Track King: 100 ms instead of 36 ms gave +7 pp). Freeze policy,
  RNG setup and search caps; verify each arm's allowance after seat swaps, and measure actual work
  and phase completion. This is a local diagnostic, not deadline readiness; separate map pools do
  not form a measured budget-response curve.
- **Profile before buying milliseconds** (procedure in `cg-profile-bot`). In Back Track King, 8 of
  11 board refreshes per simulated turn served target selection and evaluated regions whose delta
  was provably zero. Cut algorithmically (skip zero-effect evaluations, region indices, choose
  targets once per turn); +2/+4/+9 ms budgets failed on strength or hit 50-52 ms timeouts.
- **Monotone updates.** Prove which results cannot change under the specific state delta. With
  deletion-only edge changes and unchanged costs/tie-breaking, an untouched canonical shortest
  path and prior unreachability can be reused. Recompute invalidated results and retain separate
  future-reachability and terminal guards, even when active paths survive. Differentially test
  fresh versus reused searches, including ties.
- **WARN telemetry.** Threshold-triggered logs describe only warned turns; their median is not
  the all-turn median. Do not set extra budget to deadline minus max/median WARN or assume the
  latency distribution shifts unchanged. Measure full input-to-valid-output tails and actual
  failures per game, keeping startup/later turns separate and retaining outliers.
- **Source size.** Keep a per-feature source-size ledger: disabled flags still cost characters
  (three Back Track King candidates died at 100,447-119,594 of 100,000 characters).

## Working agreement for the project rules

Put it in `.ai/project.md` when the repository uses cg-agent-kit (`AGENTS.md` is generated from
it there), otherwise in `AGENTS.md`.

- Rules live only in `core`; every rules change needs a test and a green `cgValidate`.
- One hypothesis → one recorded experiment; a promoted strategy gets a new frozen version.
- Reference source and effective parameters are immutable; use explicit overrides for ablations.
- Bench at the submission's nominal search budget; process IO/warm-up checks are additional.
  Screen meta-motivated mechanisms against a validated meta-matched opponent and confirm them live
  with enough paired games.
- Hot path allocation-free; keep the timer margin; `submit` + `procCheck` before every paste.
- Write everything down (also failures). Statement text verbatim per league; keep STATUS current.
