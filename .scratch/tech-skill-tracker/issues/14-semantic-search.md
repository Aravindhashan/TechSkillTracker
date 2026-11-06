# 14: Semantic job search + skill ROI

**What to build:** Semantic job search with FAISS/pgvector retrieval + cross-encoder reranking. Plus skill ROI estimation: controlled regression (exp, location, role) estimating salary premium per skill, stated as association.

**Blocked by:** 09 (data ingestion and Postgres store), 11 (demand science)

**Status:** done

- [x] Embed job descriptions and postings with sentence-transformers
- [x] FAISS/pgvector index for retrieval (FAISS, with a NumPy cosine fallback)
- [x] Cross-encoder reranking for accuracy
- [x] Skill ROI regression with controls (experience, location, role)
- [x] Streamlit UI: semantic search box + ROI table per skill

**Note:** salary was removed from this project, so ROI is measured on *demand*
(momentum + controlled OLS premium), not salary premium.