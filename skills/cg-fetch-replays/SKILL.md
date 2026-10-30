---
name: cg-fetch-replays
description: Fetch and use CodinGame leaderboards, battle lists and replays through the observed public services, decode replay frames, keep seat, agent and capture provenance, calibrate league targets from boss games, and capture IDE or boss games. Use when downloading a replay corpus, studying arena or boss games, attributing builds in replays, or building a CodinGame fetch, capture or save tool.
---

# CodinGame replay APIs and provenance

The public read endpoints below were observed without login in Spring 2026 (Troll Farm) and
Summer 2026 (Back Track King). Treat this as an integration reference, not a stable API
contract: inspect the current response shape and access requirements. IDE test execution needs
an authenticated session, not a public read call. Validate rules against downloaded games with
`cg-validate-simulator`.

Listed service calls use `POST https://www.codingame.com/services/<service>` with `Content-Type:
application/json`, body is a JSON array of positional arguments. Java `HttpClient` is enough.

| service | body | returns |
|---|---|---|
| `Leaderboards/getFilteredChallengeLeaderboard` | `["<challenge-public-id>", null, "global", {"active":false,"column":"","filter":""}]` | `users[]` with `pseudo`, `rank`, `score`, `agentId`, `league.divisionIndex`, `programmingLanguage`, placement progress `percentage`/`inProgress`; `leagues` |
| `gamesPlayersRanking/findLastBattlesByAgentId` | `[agentId, null]` | recent games: `gameId`, `done`, `players[{position, nickname, playerAgentId}]` |
| `gameResult/findByGameId` | `[gameId, null]` | full replay: `frames[]`, `agents[]`, `refereeInput` (seed), `metadata`, `ranks`, `scores` |

Challenge public id = the slug in the contest URL (e.g. `summer-challenge-2026-back-track-king`).
Leagues: `divisionIndex` counts from Wood upwards; Legend appears only after it opens.
After the contest the arena continues as a multiplayer puzzle: Back Track King then read its
leaderboard with `Leaderboards/getFilteredPuzzleLeaderboard` and the same slug and body, and its
Silver boss had a new agent ID. Re-resolve boss and agent IDs after that transition.

## Replay (`gameResult`) structure

The frame/view layouts below were observed in Back Track King. Decode each game's actual
viewer format and grouping; do not assume every contest emits one frame per player per turn.

- `frames[0]`: init; `view` = `" 0\n{ "global": { "graphics": "<map string>" }, ... }"`.
- Then one frame per agent per turn, each with that agent's **`stdout`** (its full command line)
  and `agentId` (0/1). The last agent's frame of a turn has `keyframe=true` and
  `view = " N\n{ "duration": ms, "graphics": "<events>" }"`.
- Final keyframe: `"endScreen": [[score0, score1], ...]`.
- `metadata`: per-player stats with `_0/_1` suffixes — often reveals rule concepts before you can
  read them (e.g. counters for mechanics of higher leagues).
- The `view` strings are game-specific (referee's viewer module). Decode them once into a
  `docs/replay_format.md` table: event type → data layout → meaning. Typical: placement, action
  issued, scoring, state change, path/highlight animations.
- Use `gameResult.agents[].index` as the authoritative in-game P0/P1 slot. In observed battle
  records, `lastBattles.players[].position` is finishing order, NOT that slot. Prefer
  `agents[].codingamer.pseudo` when available; otherwise join battle nicknames by the matching
  agent identity (`playerAgentId`), never by array order or finishing place. Keep frame-local
  indices separate from globally identifying arena agent IDs. Test a P1 win and a timeout loss.

## Using replays

1. `CgValidate`: rebuild the initial state from the global graphics, feed both stdout lines per
   turn into `Rules.resolve`, compare with viewer events (placements, scores, paths, end turn,
   final score). Inspect mismatches: parser/indexing/terminal-event errors can resemble rules
   errors. Preserve source responses, fail on empty/malformed input, and never silently discard
   divergent games to report a perfect rate.
2. Rule inference works well: hidden thresholds, syntax variants, end conditions were all
   recovered from ~100 replays and confirmed 100% before the statement was visible.
3. `Cg*Study`: winner's action frequencies by turn, target classification, game length, idle
   turns, and **agreement of our bot with the winner's moves on the same states** — a
   self-play-independent signal of what the meta looks like.
4. Calibrate the league target before tuning: `gameResult.agents[]` of a boss game carries the
   boss's rating (`score`), which is what promotion must exceed; `findLastBattlesByAgentId` on
   the boss agent lists its last 500 battles. Join opponents to the current leaderboard: players
   who have since been promoted show the win rate against this exact boss that promotion took
   (Back Track King Silver: about 55% overall, 70-95% for fast promotions). Their games against
   the boss are the most targeted corpus available; compare them phase by phase with your own
   boss games (income split, connection counts, what the opponent's hits actually target) before
   choosing a mechanism. Self-play may not reproduce the boss situation at all.

Timeouts can retain stdout that arrived too late to execute. Use failure/status and terminal
events to distinguish usable commands from retained text. Establish from the game's referee
whether the surviving player's final actions/scoring occur and how a loss score is applied;
do not universalize Back Track King's observed terminal -1 score. Cover this in replay tests.
Store source game ID, agent IDs, slot mapping and capture origin; analyze each uploaded arena
entry separately. Do not mix boss games into arena-strength statistics by default.

## Preserve arena uploads before replacing them

Before an authorized upload, archive the live entry's battle list and available canonical
replays. In Back Track King, replacing the live agent made its battle list empty; previously
downloaded games remained the only available evidence, and games played after the last fetch
were lost at the next Submit. Verify the current game's API behavior, but do not rely on being
able to discover an old upload's games after replacing it.

Follow every new upload through placement, not only before the next Submit. In Back Track King
a league promotion at the end of placement replaced the agent: CG replayed the placement in the
new league as a new agent. The old agent's list was gone at the next fetch, and
`findLastBattlesByTestSessionHandle` also listed only the live agent. The contest's tool polled
every 15 minutes, every 3 minutes from 85% placement, until `percentage` was 100 with
`inProgress` false, and filed the promoted agent as the next upload with `promotedFrom`.
Treat an empty list for a known agent as a replaced agent, not as zero games. Lost results can
be partly recovered from opponents' last-battles lists (85 of ~120 there, from 102 opponents):
such rows have no replays or map data and over-represent late placement, so mark them recovered.

Store each upload separately with its agent ID, artifact/build and configuration hashes,
submission/fetch times, league, placement-completion state and rating snapshots. Preserve the
first observed completed-placement snapshot as that upload's placement result; later ratings
are separate observations. Partial-placement imports are historical context, not interchangeable
completed placements. Do not replace missing results with a later score or an estimate. CG
scores do not compare across leagues; keep the league with every score and comparison.

Re-uploading one artifact creates another upload of the same configuration, not a new strategy.
Check configuration identity before grouping/relabeling uploads; keep distinct build hashes,
agent IDs and upload numbers. Record opponent-rating provenance and timestamp: a rating obtained
at fetch time is not necessarily the rating at match time. Resume downloads by game ID and keep
request budgets/backoff separate from the promotion decision. Use `cg-promote-bot` to interpret
repeated placements; fetching evidence does not authorize an upload or rollback.

Source: Back Track King `docs/arena-uploads.md`, adopted 2026-10-27, with placement watching
and league rules added that evening (`master` at `56a6624`, 2026-10-28).

## IDE / boss replay capture

Observed working flow in Back Track King:

1. Capture an authorized IDE PLAY MY CODE request and its `TestSession/play` response. A
   userscript can observe the returned `gameId`; an independent runner can reproduce the
   observed request with a separately imported session. Do not guess undocumented arguments.
2. Fetch `[gameId, null]` through `gameResult/findByGameId` and save the canonical result. If
   a game ID is already known, a CLI fetcher can do this without a userscript. An observer is
   useful for automatic discovery/capture, not as a second rules/replay engine. Wait for a
   final outcome before treating a response as a completed game; early responses may be partial.
3. Save boss inputs separately from arena inputs. Request selector -2 mapped to a positive
   boss agent ID here; verify canonical identity and league, not a nickname, sign or folder.
4. Retain the original test response as a clearly labelled raw fallback if canonical retrieval
   fails. Do not present that fallback as successfully normalized/validated replay data.

For independent automation, browser login does not authenticate the script; sanitized HARs
omit credentials. With authorized session export, import locally into ignored private
storage, never chat or logs. The observed play call also saves supplied IDE code: preserve
the original and avoid concurrent IDE edits. Persist intent before game creation, then resume
read-only retrieval by game ID. Do not blindly repeat an uncertain creation request; arena
history may omit IDE games. Respect rate limits with paced calls/backoff. Record transport
attempts separately from completed games; never discard an executed bot failure as transport.

For build attribution, emit a short version/configuration marker through a game-supported
message channel retained in canonical replays (stderr may be absent). Without such a channel a
command the referee rejects harmlessly can carry it (Code Royale: the build id as a turn-0 `TRAIN`
of site ids, only warned about while no barracks exist). Establish from the referee source and
replays that it cannot remove the bot, and confirm on the first marked upload that every game
carries it and the simulator reproduces its warning. Match the marker to an immutable local
artifact manifest; missing/unknown markers stay unknown. This is self-reported identity, not
remote execution attestation; the requested build or destination folder is insufficient.

To check which code played, replay each downloaded arena game through the validated simulator:
on every turn with a confirmed state, compare the output of a kept copy of the uploaded artifact
with the agent's recorded stdout, then continue with both players' recorded commands. Verdicts:
SAME (all recorded turns compared, no difference), DIFF (a difference, or no answer where the
agent answered), PARTIAL (no difference, some turns not compared) or ERROR; the upload is
confirmed only when every game is SAME. SAME confirms the play, the marker names the build. The
same replay with another bot counts the games a change touched. Code Royale found all 420
placement games of seven uploads SAME, and v02's UNSTICK changed 2 and 4 of 60 games compared
with v01. Agreement covers the positions reached; it is not attestation of the code.

An IDE rerun is a new simulation, not necessarily playback of the downloaded historical game:
code, configuration and randomness can differ. Stderr export is debugging evidence, not a
substitute for canonical replay actions and events.

For a localhost save server, enforce one listening instance and expose an identity/version
health check; do not silently kill unrelated processes on a port. Use the userscript manager's
authorized request mechanism where page fetch is blocked. A green save notification must mean
the server confirmed the expected destination; a browser-download fallback should say so and
report why server saving failed. A running console alone does not prove which server answered.

## Browser and IDE access

- File navigation, page-side localhost fetch and userscript requests can have different access
  rules. Check the active browser/tool surface; serving the viewer over localhost HTTP often
  avoids file URL restrictions, but does not by itself solve cross-origin request permissions.
- The established submission workflow is that the user pastes the verified artifact into the
  CG IDE, runs PLAY MY CODE, then TEST IN ARENA. Do not infer upload authorization from a request
  to analyze or fetch games. Statement text of a league may require promotion; ask
  the user (logged in) to reach the league, then read the statement in the browser and save it.
- A userscript can additionally export stderr for debugging. Keep it separate from replay capture.
