# Back Track King: v5 with arena uploads (adopted 2026-10-27, calibrated 2026-10-28)

Use this as a dated project-policy example when adapting or explicitly adopting the workflow.
Do not silently impose its numbers on another contest or mix them with another named policy.
The goal is practical arena progress with controlled rollback, not proof of superiority at a
fixed statistical confidence level. Thresholds, worker counts and resource limits are choices.

## Provenance and status

Source: `aabzac/summer-challenge-2026-back-track-king`, `master` at commit
`56a6624baeda1965ada7e8e6e62eaa20eee97d17` (2026-10-28); the files were read from that commit.

- [benchmarking-v5.md](https://github.com/aabzac/summer-challenge-2026-back-track-king/blob/56a6624baeda1965ada7e8e6e62eaa20eee97d17/docs/benchmarking-v5.md): v5 adopted 2026-10-21, replication added 2026-10-26.
- [arena-uploads.md](https://github.com/aabzac/summer-challenge-2026-back-track-king/blob/56a6624baeda1965ada7e8e6e62eaa20eee97d17/docs/arena-uploads.md): arena-upload amendment adopted 2026-10-27; placement watching and league rules added that evening; first calibration 2026-10-28.
- [boss-v4.md](https://github.com/aabzac/summer-challenge-2026-back-track-king/blob/56a6624baeda1965ada7e8e6e62eaa20eee97d17/docs/boss-v4.md): fresh replication overturned the earlier proxy-blind-spot explanation; screen winners did not replicate.
- [STATUS.md](https://github.com/aabzac/summer-challenge-2026-back-track-king/blob/56a6624baeda1965ada7e8e6e62eaa20eee97d17/docs/STATUS.md): v13 selected and in Gold since 2026-10-27; its Gold baseline is complete.

The first calibration cycle is complete: v13's Gold baseline is 10.82 and 10.65 (mean 10.73),
so a Gold candidate is rolled back below a mean of about 9.7 when its performance rating
agrees. M rests on one Silver and one Gold pair of uploads of the same artifact, and the Silver
pair includes a placement cut short by a league promotion. Treat M as provisional.

At this commit the documents had not yet recorded which boss the next live filter uses in Gold
or a proxy revalidation for it. The policy requires revalidation whenever the live boss changes.

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
| Arena trial | Two separate uploads of the SAME candidate artifact in the current league, each watched through placement completion, unless the declared early rollback applies. Placements took about 120 games in Silver and 140-141 in Gold here, not a universal fixed count. |
| Baseline | At least two completed placement scores from the selected version's own uploads in the current league. After a league promotion, rebuild it there before judging a candidate. |
| Normal rollback | Within one league: candidate mean placement score is lower than baseline by MORE THAN M AND candidate pooled performance rating is lower by MORE THAN 2 standard errors of the difference. |
| Early rollback | Candidate upload 1 alone is below baseline mean by MORE THAN 2M; omit upload 2 and restore the selected artifact. |
| Promotion | Otherwise promote after the required evidence and other gates are complete, under existing authorization. Missing evidence does not satisfy "otherwise". |

The local pools are paired; arena matchmaking is not under our control. Do not describe the
arena comparison as a paired-seed experiment or substitute a raw arena win rate for its rule.
Win rate, opponent median and the shared-opponent delta are context only: identical bytes gave
shared-opponent deltas of -14.2 ± 8.8 pp in Silver (15 players) and +8.5 ± 7.3 pp in Gold
(23 players).

## Placement records and rollback

1. Fetch the current live entry BEFORE every upload, including a repeat, promoted default or
   rollback. The observed API stopped listing an old agent's games after it was replaced, and
   games played after the last fetch were lost at the next Submit.
2. Assign a distinct upload id and arena agent id to each Submit. Record the artifact SHA-256,
   source revision, configuration hash, time, league and all available replay ids.
3. Watch each placement from the Submit until the observed completion signal (`percentage=100`
   here); the tool polled every 15 minutes and every 3 minutes from 85%. A league promotion at
   the end of placement replaced the agent: CG replayed the placement in the new league as a new
   agent, and the old agent's games disappeared. File the new agent as a further upload with
   `promotedFrom`. Only 85 of ~120 lost results could be recovered from opponents' lists.
4. Freeze the FIRST completed placement-score snapshot as that upload's score; later snapshots
   are separate observations. Two snapshots of one upload are not two placements. If watching
   starts after completion, that snapshot can include later games; record its time. Partial
   scores are context only, with one recorded exception: the promoted v13 upload reached 30.24
   at 92%, and BTK used it as "at least 30.24" in its Silver noise pair. State in the adopted
   policy whether such censored placements enter M.
5. Compute M as 2 times the sample standard deviation of placement scores from repeated uploads
   of one unchanged configuration within one league. History: provisional 1.0 CG point, then
   1.4 from the first (Silver) pair, then about 1.0 from the Silver SD 0.71 pooled with the Gold
   SD 0.12 (pooled 0.51). Pooling across leagues assumes comparable noise in CG points there.
   Adaptation clarification added by this kit: declare the calibration cohort/window and how M
   is frozen for a candidate before inspecting its result. The source re-estimates M as uploads
   accumulate but does not fully specify this selection rule.
6. Keep placement variability separate from performance-rating model uncertainty. The source
   tool fits an opponent-score logistic model with one scale per league (profile likelihood;
   2.0 by default until a league has 60 rated games). Refits move earlier ratings: Gold's scale
   went from 2.60 to 4.05 and v13's first Gold rating from 11.06 ± 0.45 to 10.96 ± 0.70. Opponent
   scores observed at download time are not necessarily their historical game-time values.
   Record the model, data coverage and limitations instead of claiming universal calibration.
7. On rollback, upload the verified selected artifact and capture it as a new baseline upload.
   On promotion, freeze the version, defaults, pins and decision record. Relabel evidence only
   when configuration identity and code comparability are established. Rebuilding the promoted
   default can change its marker/artifact hash; process-check it and record its upload separately.

## Boundaries and historical alternatives

- The previous 80-game live confirmation with a possible predeclared extension to 120 is
  historical after this amendment. Do not add it back as an extra mandatory gate.
- Policy lineage: `practical-300-1000-v1` and its 52% floor revision v2 (both 2026-09-16);
  `practical-300-1000-boss-cache-v3` (2026-09-19), where a 40-game cached boss check replaced the
  common-opponent stages; `practical-1000-futility-boss-cache-v4` (2026-09-20), one pooled
  1000-game run in blocks of 300/+200/+500 with futility looks; v5 (2026-10-21). The kit keeps v2
  as a [named alternative](practical-300-1000.md). Do not mix gates from different revisions.
- A candidate equal to the proxy, or an invalid proxy, needs an explicit alternative protocol.
  The source summary in `AGENTS.md` mentions a pooled 1000-game fallback; detailed v5 also
  requires an alternative screen against `neural-v6`. Resolve that source discrepancy in the
  project before executing a fallback; do not silently infer which stages can be skipped.
- Passing a policy stage does not grant arena-upload or promotion permission. Preserve the
  user's existing authorization; if a handoff is needed, supply the exact verified artifact.
