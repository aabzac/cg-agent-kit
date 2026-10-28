# Back Track King: v5 with arena uploads (2026-10-27)

Use this as a dated project-policy example when adapting or explicitly adopting the workflow.
Do not silently impose its numbers on another contest or mix them with another named policy.
The goal is practical arena progress with controlled rollback, not proof of superiority at a
fixed statistical confidence level. Thresholds, worker counts and resource limits are choices.

## Provenance and status

Source: `aabzac/summer-challenge-2026-back-track-king`, commit
`2fc49809617350c81f6484b288d7bca46d1f111b`; the inspected files matched that commit.

- [benchmarking-v5.md](https://github.com/aabzac/summer-challenge-2026-back-track-king/blob/2fc49809617350c81f6484b288d7bca46d1f111b/docs/benchmarking-v5.md): v5 adopted 2026-10-21, replication added 2026-10-26.
- [arena-uploads.md](https://github.com/aabzac/summer-challenge-2026-back-track-king/blob/2fc49809617350c81f6484b288d7bca46d1f111b/docs/arena-uploads.md): arena-upload amendment adopted 2026-10-27.
- [boss-v4.md](https://github.com/aabzac/summer-challenge-2026-back-track-king/blob/2fc49809617350c81f6484b288d7bca46d1f111b/docs/boss-v4.md): fresh replication overturned the earlier proxy-blind-spot explanation; screen winners did not replicate.
- [STATUS.md](https://github.com/aabzac/summer-challenge-2026-back-track-king/blob/2fc49809617350c81f6484b288d7bca46d1f111b/docs/STATUS.md): v13's second upload was still pending at this snapshot.

The amendment was adopted, but the first complete two-upload calibration cycle was unfinished.
Do not describe its provisional margin or thresholds as universally validated.

## Adopted main path

Prerequisites: validated engine, zero bot errors, strict process test of the exact artifact and
source-size compliance. Freeze source, full configuration and artifact; draws count as half.
Use the actual selected version, not stale version names in older examples. Local timed series
used two workers with explicit first/subsequent-turn budgets; adapt these to the target runtime.

| Stage | Back Track King rule |
| --- | --- |
| Proxy screen | Candidate and selected control each play 300 games / 150 fresh maps against the validated proxy, on identical maps/seeds/seats in the same run. Continue at candidate minus control >=3 percentage points. |
| Replication | Repeat both arms on 150 NEW maps / 300 games each with the same frozen proxy and control. Require replication delta >0 AND pooled delta over screen plus replication >=3 pp. |
| Regression guard | 300 paired games / 150 fresh maps directly against the selected version; candidate score >=48%. This is a practical floor, not a formal non-inferiority test. |
| Live filter | One session of 40 candidate games plus a same-session matched control on the prescribed cached maps/seeds/seats. Continue at paired delta >=0. |
| Arena trial | Two separate uploads of the SAME candidate artifact, each followed through placement completion, unless the declared early rollback applies. About 120 placement games was observed here, not a universal fixed count. |
| Baseline | At least two completed placement scores from the selected version's own uploads. |
| Normal rollback | Candidate mean placement score is lower than baseline by MORE THAN M AND candidate pooled performance rating is lower by MORE THAN 2 standard errors of the difference. |
| Early rollback | Candidate upload 1 alone is below baseline mean by MORE THAN 2M; omit upload 2 and restore the selected artifact. |
| Promotion | Otherwise promote after the required evidence and other gates are complete, under existing authorization. Missing evidence does not satisfy "otherwise". |

The local pools are paired; arena matchmaking is not under our control. Do not describe the
arena comparison as a paired-seed experiment or substitute a raw arena win rate for its rule.

## Placement records and rollback

1. Fetch the current live entry BEFORE every upload, including a repeat, promoted default or
   rollback. The observed API stopped listing an old agent's games after it was replaced.
2. Assign a distinct upload id and arena agent id to each Submit. Record the artifact SHA-256,
   source revision, configuration hash, time, league and all available replay ids.
3. Wait for the observed completion signal (`percentage=100` here). Freeze the FIRST completed
   placement-score snapshot as that upload's score; later snapshots are separate observations.
   Two snapshots of one upload are not two placements. Partial placement scores are context only.
4. Compute M as 2 times the sample standard deviation of placement scores from repeated uploads
   of one unchanged configuration. The initial policy used a provisional 1.0 CG point until the
   first repeat measurement. Adaptation clarification added by this kit: declare the calibration
   cohort/window and how M is frozen for a candidate before inspecting its result. The source
   specifies the formula and provisional value, but does not fully specify this selection rule.
5. Keep placement variability separate from performance-rating model uncertainty. The source
   tool uses an opponent-score logistic model; its standard errors are model-dependent, and
   opponent scores observed at download time are not necessarily their historical game-time values.
   Record the model, data coverage and limitations instead of claiming universal calibration.
6. On rollback, upload the verified selected artifact and capture it as a new baseline upload.
   On promotion, freeze the version, defaults, pins and decision record. Relabel evidence only
   when configuration identity and code comparability are established. Rebuilding the promoted
   default can change its marker/artifact hash; process-check it and record its upload separately.

## Boundaries and historical alternatives

- The previous 80-game live confirmation with a possible predeclared extension to 120 is
  historical after this amendment. Do not add it back as an extra mandatory gate.
- BTK v4 used pooled blocks of 300/+200/+500 against the selected version. It is DIFFERENT from
  the kit's `practical-300-1000-v2`, which uses a separate fresh 1000-game continuation.
- A candidate equal to the proxy, or an invalid proxy, needs an explicit alternative protocol.
  The source summary in `AGENTS.md` mentions a pooled 1000-game fallback; detailed v5 also
  requires an alternative screen against `neural-v6`. Resolve that source discrepancy in the
  project before executing a fallback; do not silently infer which stages can be skipped.
- Passing a policy stage does not grant arena-upload or promotion permission. Preserve the
  user's existing authorization; if a handoff is needed, supply the exact verified artifact.
