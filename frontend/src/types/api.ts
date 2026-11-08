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

export interface TopLocation {
  location: string
  count: number
}

export interface RecentPosting {
  job_id: string
  title: string | null
  company: string | null
  location: string | null
  posted_at: string | null
  url: string | null
  is_remote: boolean | null
  skills: string[]
}

export interface ForecastPoint {
  date: string
  actual: number | null
  forecast: number | null
  lower: number | null
  upper: number | null
}

export type ForecastEngine =
  | "auto"
  | "gradient_boosting"
  | "sarimax"
  | "prophet"
  | "croston"
  | "exponential_smoothing"
  | "linear"

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

export interface SurvivalPoint {
  time: number
  at_risk: number
  events: number
  survival: number
}

export interface AnomalyRow {
  "Job Title": string
  "Tech Skill": string
  Location?: string
  "Experience Required (in years)"?: number | null
  reason?: string
}

export interface PmiPair {
  skill_a: string
  skill_b: string
  cooccurrence: number
  pmi: number
}

export interface CoxCoefficient {
  covariate: string
  coef: number
  exp_coef: number
  p_value: number
}

export interface MatchRequest {
  job_id: string
  resume_skills: string[]
  resume_years?: number | null
  resume_title?: string | null
}

export interface MatchResponse {
  job_id: string
  match_score: number
  matched_skills: string[]
  missing_must_have: string[]
  missing_nice_to_have: string[]
  experience_gap: number | null
  title_similarity: number | null
  posting_health: string
  confidence: string
}

export interface DemandScienceResponse {
  survival_overall: SurvivalPoint[]
  survival_by_skill: Record<string, SurvivalPoint[]>
  cox: { coefficients?: CoxCoefficient[]; n?: number; events?: number; error?: string } & Record<string, unknown>
  anomalies: AnomalyRow[]
  pmi_pairs: PmiPair[]
  communities: Record<string, number>
  relatedness: Record<string, [string, number][]>
}