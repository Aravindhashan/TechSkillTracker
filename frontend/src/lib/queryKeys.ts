export const queryKeys = {
  health: ["health"] as const,
  marketOverview: ["market", "overview"] as const,
  topSkills: (n: number) => ["market", "top-skills", n] as const,
  locations: (n: number) => ["market", "locations", n] as const,
  recentPostings: (n: number) => ["market", "recent-postings", n] as const,
  demandTrends: (topN: number) => ["market", "demand-trends", topN] as const,
  skillPairs: (minCo: number) => ["market", "skill-pairs", minCo] as const,
  forecast: (skill: string, months: number, model: string) =>
    ["forecast", skill, months, model] as const,
  recommendations: (mode: string, key: string) => ["recommendations", mode, key] as const,
  search: (query: string, topK: number, rerank: boolean) =>
    ["search", query, topK, rerank] as const,
  roi: (topN: number) => ["roi", topN] as const,
  demandScience: ["demand-science"] as const,
  fairness: ["fairness"] as const,
}