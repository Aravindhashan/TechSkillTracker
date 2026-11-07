export const queryKeys = {
  health: ["health"] as const,
  marketOverview: (skills: string, locations: string) =>
    ["market", "overview", skills, locations] as const,
  topSkills: (n: number, skills: string, locations: string) =>
    ["market", "top-skills", n, skills, locations] as const,
  locations: (n: number, skills: string, locations: string) =>
    ["market", "locations", n, skills, locations] as const,
  recentPostings: (n: number, skills: string, locations: string) =>
    ["market", "recent-postings", n, skills, locations] as const,
  demandTrends: (topN: number, skills: string, locations: string) =>
    ["market", "demand-trends", topN, skills, locations] as const,
  skillPairs: (minCo: number, skills: string, locations: string) =>
    ["market", "skill-pairs", minCo, skills, locations] as const,
  forecast: (skill: string, months: number, model: string) =>
    ["forecast", skill, months, model] as const,
  recommendations: (mode: string, key: string) => ["recommendations", mode, key] as const,
  search: (query: string, topK: number, rerank: boolean) =>
    ["search", query, topK, rerank] as const,
  roi: (topN: number) => ["roi", topN] as const,
  demandScience: ["demand-science"] as const,
  fairness: ["fairness"] as const,
}