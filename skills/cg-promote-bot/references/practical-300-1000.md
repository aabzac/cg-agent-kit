# Alternative policy: practical-300-1000-v2

Use this named alternative only when the project explicitly adopts it. Preserve its id and
historical verdicts when changing policies. It is a practical selection rule, not a test with
an overall 95% error guarantee; confidence intervals remain descriptive diagnostics.

Origin: Back Track King adopted `practical-300-1000-v1` on 2026-09-16 and added the 52% floor
(v2) the same day. Three days later that contest replaced the common-opponent stages with a
40-game cached boss check (boss-cache-v3), then folded the direct stages into one pooled
1000-game run (v4), and moved to proxy screens in v5 after its self-play gates stopped
predicting boss results; v5 later added arena uploads. See
[its current policy](back-track-king-policy.md). Do not mix this protocol's gates with those
later revisions.

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
