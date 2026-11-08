import type {
  DemandScienceResponse,
  ForecastResponse,
  HealthResponse,
  MarketOverview,
  RecommendationResponse,
  RoiResponse,
  MatchBatchResponse,
  MatchRequest,
  MatchResponse,
  SearchRequest,
  SearchResponse,
  RecentPosting,
  TopLocation,
  TopSkill,
} from "@/types/api"

const API_BASE =
  (import.meta.env.VITE_API_BASE as string | undefined) ?? "http://localhost:8000"

export interface FilterParams {
  skills?: string[]
  locations?: string[]
}

function filterQuery(filters?: FilterParams): string {
  const params = new URLSearchParams()
  const skills = filters?.skills?.filter(Boolean) ?? []
  const locations = filters?.locations?.filter(Boolean) ?? []
  if (skills.length > 0) params.set("skills", skills.join(","))
  if (locations.length > 0) params.set("locations", locations.join(","))
  const qs = params.toString()
  return qs ? `&${qs}` : ""
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `${res.status} ${res.statusText}`)
  }
  return res.json() as Promise<T>
}

export const api = {
  health: () => request<HealthResponse>("/api/health"),
  marketOverview: (filters?: FilterParams) =>
    request<MarketOverview>(`/api/market/overview?${filterQuery(filters).slice(1)}`),
  topSkills: (n = 10, filters?: FilterParams) =>
    request<{ skills: TopSkill[] }>(`/api/market/top-skills?n=${n}${filterQuery(filters)}`),
  locations: (n = 10, filters?: FilterParams) =>
    request<{ locations: TopLocation[] }>(`/api/market/locations?n=${n}${filterQuery(filters)}`),
  recentPostings: (n = 10, filters?: FilterParams) =>
    request<{ postings: RecentPosting[] }>(`/api/market/recent-postings?n=${n}${filterQuery(filters)}`),
  demandTrends: (topN = 5, filters?: FilterParams) =>
    request<{ skill: string; month: string; count: number }[]>(`/api/market/demand-trends?top_n=${topN}${filterQuery(filters)}`),
  skillPairs: (minCo = 2, filters?: FilterParams) =>
    request<{ skill_a: string; skill_b: string; count: number }[]>(`/api/market/skill-pairs?min_cooccurrence=${minCo}${filterQuery(filters)}`),
  forecast: (skill: string, monthsAhead = 12, modelType = "auto") =>
    request<ForecastResponse>(
      `/api/forecast/${encodeURIComponent(skill)}?months_ahead=${monthsAhead}&model_type=${modelType}`,
    ),
  recommendations: (body: {
    mode: "complementary" | "role" | "learning-path"
    skill?: string
    role?: string
    current_skills?: string[]
    target_role?: string
    top_n?: number
  }) =>
    request<RecommendationResponse>("/api/recommendations", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  search: (body: SearchRequest) =>
    request<SearchResponse>("/api/search", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  roi: (topN = 25) => request<RoiResponse>(`/api/roi?top_n=${topN}`),
  match: (body: MatchRequest) =>
    request<MatchResponse>("/api/match", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  matchBatch: (body: { job_ids: string[]; resume_skills: string[] }) =>
    request<MatchBatchResponse>("/api/match/batch", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  demandScience: () => request<DemandScienceResponse>("/api/demand-science"),
  fairness: () => request<Record<string, unknown>>("/api/fairness"),
  resumeAnalyze: async (file: File) => {
    const form = new FormData()
    form.append("file", file)
    const res = await fetch(`${API_BASE}/api/resume/analyze`, { method: "POST", body: form })
    if (!res.ok) throw new Error(await res.text())
    return res.json()
  },
}