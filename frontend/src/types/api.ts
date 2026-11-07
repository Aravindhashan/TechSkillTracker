export interface HealthResponse {
  status: string
  backend: string
  postings: number
  store_available: boolean
  data_age_hours: number | null
}

export interface MarketOverview {
  total_openings: number
  unique_skills: number
  companies: number
  locations: number
}

export interface TopSkill {
  skill: string
  count: number
}

export interface ForecastPoint {
  date: string
  actual: number | null
  forecast: number | null
  lower: number | null
  upper: number | null
}

export interface ForecastResponse {
  skill: string
  status: string
  message: string | null
  engine: string | null
  selected_by: string | null
  mape_comparison: Record<string, number>
  months_ahead: number
  forecast: ForecastPoint[]
  insights: string[]
}

export interface RecommendationItem {
  [key: string]: unknown
}

export interface RecommendationResponse {
  mode: string
  status: string
  message: string | null
  results: RecommendationItem[]
}

export interface SearchRequest {
  query: string
  top_k?: number
  rerank?: boolean
}

export interface SearchResult {
  job_id: string | null
  title: string | null
  company: string | null
  location: string | null
  posted_at: string | null
  url: string | null
  skills: string[]
  description: string
  score: number
  semantic_score: number
  rerank_score: number | null
}

export interface SearchResponse {
  query: string
  backend: string
  results: SearchResult[]
}

export interface RoiRow {
  skill: string
  demand: number
  share_pct: number
  months_observed: number
  momentum: number
  monthly_growth_pct: number
  confidence: string
  premium: number | null
  p_value: number | null
  roi_score: number
}

export interface RoiResponse {
  rows: RoiRow[]
}

export interface DemandScienceResponse {
  survival_overall: Record<string, unknown>[]
  survival_by_skill: Record<string, Record<string, unknown>[]>
  cox: Record<string, unknown>
  anomalies: Record<string, unknown>[]
  pmi_pairs: Record<string, unknown>[]
  communities: Record<string, number>
  relatedness: Record<string, [string, number][]>
}