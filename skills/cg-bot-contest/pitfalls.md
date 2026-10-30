# Pitfalls collected across contests

## Benches and statistics

- **Deterministic self-play mirrors**: two copies of the same bot pick the same cells/actions and
  every game is a draw or a 0-0. Add `NOISE` (multiplicative jitter on candidate values) and
  `SEED` params; mix the player id into the seed. Test different seeds and both sides; draws
  alone do not establish a wiring bug. Treat enabling noise as a strategy change, not a cure
  that must be shipped in every game.
- No fixed game count implies a fixed CI width. Paired sides and repeated maps are dependent;
  keep distinct-map identities and use the evidence rules in `cg-promote-bot`.
- Self-play may not reproduce the arena meta (e.g. game length, aggression). Compare your
  self-play stats with replay stats (`cgStudy`) and build a reference opponent that matches the
  meta before trusting benches for meta-dependent features.
- Do not diagnose a proxy's failure from one selected local winner losing live. Replicate the
  fixed candidate on fresh maps with a same-run control before changing the proxy. In Back Track
  King's `docs/boss-v4.md` (2026-10-26), two apparent gains reversed on replication; a replay
  action-agreement gap in already-won tails did not establish a strength-prediction defect.
  Keep the original numbers and explicitly correct the superseded interpretation.
- Win rate and average score diff can disagree (robust-but-low-scoring styles). In win/loss
  games only the win rate matters; large negative score diffs still deserve a look for blunders.
- Parallel arena timing can show JIT/GC contention outliers. Align nominal search budgets first,
  then check the submission process separately. Passing locally is not a CG-host guarantee.

## Java on CodinGame

- Read the actual first/later-turn allowances. Budget input, preparation, JIT warm-up and safety
  margin on one clock; fixed 500-ms warm-up or 10-15-ms margins are examples, not defaults for
  all contests. Check time inside expensive work, not only at phase entry.
- Verify warm-up reaches search: tiny calls can end immediately when shorter than a phase
  reserve. Phase reservations can still be overrun by an atomic evaluation. See the timing rules
  in `cg-promote-bot`.
- Read input with a byte-level token reader, never `Scanner`. Print with one `StringBuilder` per
  turn. No allocation in the hot path (arrays, scratch buffers in `Pathing`).
- Cross-check derived state against what the server sends (e.g. active connections/flags) and
  log mismatches to stderr — this catches engine drift in the arena.
- `public static Action wait()` clashes with `Object.wait()` — name it `waitAction()`.
- A local variable named `java` shadows the package in `java.io.File` — use `Path.of(...)`.
- `FileMerger`: `public [final|abstract|sealed] class|interface|enum|record` → `static ...`;
  compile-check the merged file every time; keep the shipped whitelist explicit.

- For runtime-only changes, freeze policy/RNG and compare features and complete actions on fixed
  replay states with ample time; measure latency without profiling instrumentation. Report
  allocations separately: fewer allocations need not mean faster turns. For CG under-spending,
  inspect accepted action prefixes and legal continuations; stderr wall-time warnings alone
  are not server deadline failures.

## Windows shell

- PowerShell splits `-Ppath=replays/cg/x.json` at `.` and treats `?` specially → quote the whole
  property. `gradlew.bat` (cmd.exe) swallows `&` → use `,` between params.
- PowerShell 5.1 `Set-Content` writes ANSI by default and mangles non-ASCII (em dashes → `?`);
  use `-Encoding ascii/utf8` or the file tools. `Out-File -Encoding utf8` adds a BOM (breaks git
  commit messages) — write commit messages with `[IO.File]::WriteAllText`.
- No heredocs in PowerShell: pass multi-line commit messages via `git commit -F <file>`.

## Rules and engine

- Statement examples are the first unit tests; tie-break rules (e.g. direction order N/E/S/W)
  need explicit tests because they change which player gets credit.
- Both command syntaxes (`ACTION id` and `ACTION x y`) may be valid — replays show them.
- Effects of an action can be cumulative across both players (e.g. instability counters). Test
  the hypothesis on replays with a histogram before coding it.
- Game-end conditions are often unstated in lower leagues; check every early-ending replay.
- When the validator flags a diff, first check the comparison itself (e.g. cells cleared by an
  event being counted as "placements") before doubting the rule.
- Requested actions, accepted actions and retained stdout are different evidence. Check player
  indexing, skipped commands, timeouts and final scoring before diagnosing a strategic failure.

- Reused path searches must preserve exact paths, tie-breaking and exposed scratch results,
  not just distances. Reset on board/source/semantic blocking changes; buffer identity is
  insufficient. Differentially test fresh versus reused searches, including zero-cost ties,
  incremental/interrupted calls and perspective changes. When resuming Dijkstra after reaching
  a target, preserve any popped-but-not-expanded vertex.
- A green validator covers only files it actually read. Check expected replay IDs/counts and
  explicitly include new capture folders when traversal is nonrecursive. Compare map hashes
  only under the same serialization/canonicalization scheme; name raw-graphics and protocol-init
  hashes separately so a representation mismatch is not mistaken for a different map.

## Process

- Freeze source AND full effective parameters; a name such as v03 is not sufficient provenance.
  Inspect raw reports before copying conclusions from DEVLOG: summaries can be stale or wrong.
- A disabled experiment is not necessarily free: it can increase source size, initialization,
  allocations or code loading. Test baseline preservation and the actual submission artifact.
- Keep `docs/PLAN.md` ticked; the user should be able to see remaining steps without reading the
  dev log.
- Documentation volume: when DEVLOG/BOTS exceed a few hundred KB, the STATUS page and a
  reverse-chronological experiment index are mandatory, or the arena state gets lost (in Back
  Track King the arena ran an older candidate for two weeks while the selected version's upload
  stayed unticked). Archive closed periods losslessly; distinguish selected version, current
  arena agent/configuration and pending upload rather than appending history to the active status.
- Repeated records: copying each result into every document makes commits too long to follow and
  loads history into every session. In Code Royale (2026-10-30) an upload commit repeated the same
  numbers in 100-130 lines of text over 8-9 files besides its JSON evidence, and the current-state
  section of `.ai/project.md`, loaded into every session through `AGENTS.md`, had grown to 10.6 KB.
  Write each fact once and point to it; give the user a short summary of their own
  (`docs/SUMMARY.md` there since `8ad5492`, in Russian: the state now, then 3-5 lines per
  decision, without hashes or ids).
- When the next step requires the user's upload or arena observation, identify the verified
  artifact and the requested action; do not silently start another tuning cycle.
