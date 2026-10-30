# Project architecture (Java 17 + Gradle reference)

Contents: [Commands](#gradle-tasks-properties-via--pnamevalue),
[Core interfaces](#core-interfaces), [Referee / arena](#referee--arena),
[Submission artifact](#submission-artifact), [Experiment lifecycle](#experiment-lifecycle),
[Visualizer](#visualizer).

```
src/main/java/<pkg>/core      GameState, Action, Rules, Pathing, Protocol        ships to CG
src/main/java/<pkg>/bot       Bot, Params, Timer, MainBot, BotFactory
                              current/   the bot being developed                 ships to CG
                              vNN/       frozen copies = reference opponents
src/main/java/<pkg>/submit    CGRunner (ships), FileMerger
src/main/java/<pkg>/referee   Referee, MapGenerator, Replay (JSON for the visualizer)
src/main/java/<pkg>/runner    LocalRunner, BenchmarkRunner, Maps, ProcessBot, ProcessCheck
src/main/java/<pkg>/tools     CgFetch, CgReplay, CgValidate, CgRender, Cg*Study
src/main/resources/<pkg>/bot/versions/vNN.properties  frozen effective parameters
src/test/java/<pkg>/core      JUnit 5 rules tests (+ ASCII map builder)
visualizer/index.html         canvas viewer, ?file=<replay json>
docs/rules/<league>.md        statements verbatim; inferred rules in a separate file
docs/STATUS.md SUMMARY.md PLAN.md BOTS.md DEVLOG.md bot-architecture.html replay_format.md
AGENTS.md  README.md          agent rules; with cg-agent-kit edit .ai/project.md instead
replays/local replays/cg replays/rendered      gitignored corpora/derived files
```

Dependencies: Gson (JSON for replays/CG API), JUnit 5. Nothing else ships.

## Gradle tasks (properties via `-Pname=value`)

`run` (bot0, bot1, seed, map) · `bench` (bot1, bot2, games, maps, threads) · `submit` ·
`procCheck` (bot, games) · `cgFetch` (top, agent, player, limit) · `cgValidate` (path) ·
`cgRender` (path) · `cgStudy` (path, bot).
Bot spec syntax: `name` or `name?KEY=v,KEY2=v` (comma, not `&` — cmd.exe
eats `&`). Quote properties with `.` or `?` in PowerShell.

## Core interfaces

```java
interface Bot {
    String name();
    void init(GameState s, int myId);
    List<Action> play(GameState s, int myId, long budgetMs);
    default void warmup(GameState s, int myId, long ms) { /* loop play() on copies */ }
}
```

- `GameState`: static map arrays + dynamic arrays + `copy()`/`copyFrom()`; constants for rules
  numbers; small derived caches (paths, income) recomputed by `Rules`.
- `Rules`: `expand/validate` player commands, `resolve(s, a0, a1)` for a full simultaneous turn,
  `gameOver`, scoring helpers. Referee, validator and bots call only this.
- `Pathing`: BFS/Dijkstra with scratch buffers sized per state; one instance per thread.
- `Protocol`: `TokenReader` over `System.in` bytes (never `Scanner`), `readInit/readTurn`, and the
  writers the referee uses to feed an external process.
- `Params`: public fields with defaults; `apply(String)`, `copy()`, `diff()` (for bot names);
  include `NOISE`/`SEED` for symmetry breaking and `DEBUG`/`MESSAGE`.
  `BotFactory` constructs references using a full versioned parameter snapshot, then applies
  explicit overrides. Missing snapshots and unknown overrides fail instead of silently using
  live defaults. New fields unread by an older frozen implementation need not be backfilled.
  Test that changing live defaults cannot change reference parameters. Record code revision as
  well: shared core/runtime changes mean a snapshot is not an archived executable.
- `CGRunner`: constants `FIRST_TURN_MS`, `TURN_MS`, `MARGIN_MS`, `WARMUP_MS`; cross-checks derived
  state (e.g. connections) against what the server sends and logs mismatches to stderr.
- `FileMerger`: whitelist of packages/files → strips `package`/own imports, turns top-level
  `public class` into `static class` inside `class Player`, adds `main` trampoline, compiles the
  result with `javax.tools` as a check.

## Referee / arena

Keep stable machine ids separate from readable bot labels in commands, reports and replays.
Distinguish promoted versions, retained experiments and independent reference styles. Preserve
useful rejected experiments as named parameter recipes rather than a class copy per flag;
retaining an opponent does not promote it. Never retarget an existing experiment id to changed
code or defaults: record a new revision. See the source/configuration requirements above.

- `Referee.play(initial, bot0, bot1, seed, record)` → `Result{score, winner, turns, errors,
  timing, replay}`. Strict-invalid flag mirrors CG (invalid command = loss or ignored, per statement).
- `BenchmarkRunner.run(specA, specB, games, maps, threads)`: fixed seeds, each map played twice
  with sides swapped and fresh bots/state, map-aware uncertainty, per-side win rate, avg score
  diff, avg turns, time/move (avg/max/slow), error counts. Save per-game JSON, full configs,
  map identities and timing profile; see the evidence rules in `cg-promote-bot`.
- `Maps`: replay maps or a generator whose fidelity is checked separately. Explicit empty or
  invalid replay pools fail. Deduplicate initialization hashes for independent-map accounting.
- `ProcessBot`: runs `java -cp build/submit/classes Player` (or any command) over the text
  protocol with per-turn timeouts; `ProcessCheck` plays it on both seats vs an in-process bot and
  fails on timeouts/protocol errors, extra stdout lines and unexpected stderr. It also replays
  every game with the in-process source bot under the artifact's parameters and requires the same
  command lines from both players (a documented marker excepted), so it catches packaging that
  changes play on the positions reached; a game where either run lost a player cannot be compared
  and fails. This does not test the bot's logic. Prefer no timeout grace; measure full startup
  and later-turn response times, and disclose any local grace used. Local hardware is not CG's;
  process checks complement aligned search budgets and arena evidence, rather than guaranteeing
  server timing.

## Submission artifact

Run `submit` BEFORE `procCheck`; verify the artifact produced from the candidate configuration,
not a stale previously built Player. Record source revision, effective parameters and artifact
hash for the version handed to the user. Experimental runs must not silently replace it.

Make the artifact's bytes depend only on the code (fixed encoding, line endings and file order),
so its hash identifies it. Print a short build id where replays keep it (`cg-fetch-replays`): a
hash prefix of the artifact with its own id literal blank. Derive a configuration id from
strategy code and parameters only, so builds that differ just in the runner or marker count as
one configuration in repeated uploads (`cg-promote-bot`); a runner change can still change play,
so such a build still passes `procCheck`. Every build overwrites `build/`: keep the rollback
artifact as a commit whose `submit` rebuilds it byte for byte, checked on a clean export of that
commit, plus a kept copy named by its hash. Replace the previous artifact only after the new one
compiles. Source lesson: Code Royale, 2026-10-29/30 (`docs/arena-uploads.md`); every marked
artifact matched the in-process bot in all games of both 200-game `procCheck` runs.

Check the current contest's source-size limit and its counting convention (bytes/characters).
Default-off code can still enlarge the submission or allocate startup buffers; keep a per-feature
source-size ledger. Keep packaging whitelists explicit. If compacting source, preserve strings,
text blocks, token boundaries and code adjacent to comments; naive line/regex deletion is not a
general Java minifier. Compile and test representative semantics, then rerun process checks after
packaging changes. A successful compile alone does not establish behavior preservation. Do not
promise a particular size limit or copy a contest-specific compaction shortcut into all projects.

## Experiment lifecycle

Keep active strategy code, retained reference opponents and historical evidence distinct.
Retire rejected or parked mechanisms from active code deliberately when their maintenance or
submission-size cost matters. Keep an immutable runnable version for references still used by
the benchmark panel or by reproducibility checks; closed research can remain in recorded Git
history. Reject retired flags on active versions instead of silently accepting a no-op.

Move or remove mechanism-specific tests together with intentionally retired code. Keep tests for
the selected bot, retained proxies/references, engine, protocol, packaging and frozen-version
identity. Never remove a failing test for retained behavior merely to obtain a green suite.
For behavior-preserving cleanup, compare fixed-state decisions with enough time to finish,
verify unchanged retained submission hashes where byte identity is intended, then repeat the
appropriate timed/process checks when emitted code changes. Equal parameters alone do not prove
equal executable behavior. Keep the result as a cleanup verdict, not a strength promotion.

Commit compact protocols, results and machine-readable evidence needed to reconstruct decisions.
Keep large replay corpora/archives under the project's storage policy; record their size, SHA-256
and durable retrieval location or Git provenance in a manifest. Keep required regression fixtures
available to a clean checkout instead of depending on an ignored local archive. Ignoring a file
does not preserve it elsewhere, and untracking files does not remove them from Git history.
Archive closed journal periods without losing their text or links; leave an index and only
current decisions in STATUS/PLAN. Preserve old verdicts and attach later corrections explicitly.

Source lesson: Back Track King (`master` at `56a6624`), `docs/repo-cleanup-v1.md` and
`docs/prune-v1.md`.
Its exact retention set, file-size limit and local commit policy are project choices.

## Visualizer

Single HTML file, canvas, no build. Reads the referee's replay JSON
(`{meta, map, turns[{actions, placed, score, events...}]}`); play/step/slider, hover info,
per-entity colours. `cgRender` validates canonical CG input before exporting this format;
`cgValidate` itself is read-only and fails on divergence, malformed or empty input.

Keep provenance explicit: for example `replays/cg/` for canonical arena inputs,
`replays/cg/bot/` for canonical boss inputs, and `replays/rendered/cg/{arena,bot}/` for derived
visualizer files. Raw capture fallbacks are not canonical replays and must not enter benchmarks
through recursive directory scanning. Preserve compact regression inputs in test resources.
