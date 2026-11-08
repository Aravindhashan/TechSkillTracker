# 39: Posting-events logging

**What to build:** Day-one `posting_events` history (seen / reposted / closed) so the ghost-risk badge has data behind it.

**Blocked by:** None (can start immediately).

**Status:** done

- [x] `posting_events(event_id, job_id, event_type, occurred_at)` table in the store
- [x] Ingestion hook logs `seen` on first insert, `reposted` on reactivation, `closed` when marked stale
- [x] Backfill inserts `seen` (at `first_seen`) for existing postings
- [x] Tests cover seen/reposted/closed/backfill

### Notes (live DB, 2026-11-08)
- Backfilled **241 `seen` events** for 241 postings on first `init_db()` — badge has history from day one.
- Live ingestion now logs events on every upsert/close; badge scoring (ticket 40) can read them.
