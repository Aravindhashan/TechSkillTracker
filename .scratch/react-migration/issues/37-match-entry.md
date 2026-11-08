# 37: Frontend Match entry

**What to build:** Match scores on search cards + a paste-a-JD flow showing score and missing must-haves.

**Blocked by:** 36 - POST /api/match endpoint.

**Status:** done

- [x] Search cards show a match badge (score + missing must-haves) once resume skills are entered
- [x] "Match a JD" tab: job_id + resume skills → score, matched/missing, health, confidence
- [x] `src/types/api.ts`, `src/lib/api.ts`, `src/lib/queryKeys.ts` expose the `MatchRequest`/`MatchResponse` client
- [x] `npm run build` + `npm run test` pass (17/17)
