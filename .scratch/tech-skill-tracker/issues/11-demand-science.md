# 11: Demand science (survival, anomaly, dedupe, associations, graph)

**What to build:** Add demand-side analysis using first_seen/last_seen: Kaplan-Meier + Cox regression for time-to-fill by skill/location; Isolation Forest/z-score anomaly detection for bad salaries and duplicate spikes; MinHash LSH fuzzy dedupe across Adzuna+JSearch; PMI association mining for skill bundles (e.g. MERN); Louvain community detection on skill graph; word2vec embeddings for skill relatedness.

**Blocked by:** 09 (data ingestion and Postgres store)

**Status:** ready-for-agent

- [ ] Survival analysis: KM curves + Cox regression, time-to-fill by skill/location
- [ ] Anomaly detection: Isolation Forest + z-scores on salaries and posting counts
- [ ] MinHash LSH dedupe across sources (company + title + description hash)
- [ ] PMI association mining on skill co-occurrence (same-company issue fixed)
- [ ] Skill graph + Louvain clustering for skill families
- [ ] Word2vec on skill sequences → relatedness score for skill pairs