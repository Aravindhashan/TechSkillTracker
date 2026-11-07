import type {
  DemandScienceResponse,
  ForecastResponse,
  HealthResponse,
  MarketOverview,
  RecommendationResponse,
  RoiResponse,
  SearchRequest,
  SearchResponse,
  TopLocation,
  TopSkill,
} from "@/types/api"

const API_BASE =
  (import.meta.env.VITE_API_BASE as string | undefined) ?? "http://localhost:8000"

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
  marketOverview: () => request<MarketOverview>("/api/market/overview"),
  topSkills: (n = 10) => request<{ skills: TopSkill[] }>(`/api/market/top-skills?n=${n}`),
  locations: (n = 10) => request<{ locations: TopLocation[] }>(`/api/market/locations?n=${n}`),
  demandTrends: (topN = 5) =>
    request<{ skill: string; month: string; count: number }[]>(`/api/market/demand-trends?top_n=${topN}`),
  skillPairs: (minCo = 2) =>
    request<{ skill_a: string; skill_b: string; count: number }[]>(`/api/market/skill-pairs?min_cooccurrence=${minCo}`),
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