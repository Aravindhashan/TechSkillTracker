import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import Plot from "react-plotly.js"
import { api } from "@/lib/api"
import { queryKeys } from "@/lib/queryKeys"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import GhostBadge from "@/components/GhostBadge"
import type { SearchResult } from "@/types/api"

type SubTab = "search" | "roi" | "match"

const INK = "#1A1815"
const GRID = "#E4DCC8"

function parseSkills(value: string): string[] {
  return value
    .split(",")
    .map((entry) => entry.trim())
    .filter(Boolean)
}



function MatchBadge({ result, resumeSkillsInput }: { result: SearchResult; resumeSkillsInput: string }) {
  const resumeSkills = parseSkills(resumeSkillsInput)
  const match = useQuery({
    queryKey: queryKeys.match(result.job_id ?? "", resumeSkills.join(",")),
    queryFn: () => api.match({ job_id: result.job_id ?? "", resume_skills: resumeSkills }),
    enabled: !!result.job_id && resumeSkills.length > 0,
  })

  if (resumeSkills.length === 0) return null
  return (
    <div className="mt-3">
      {match.isLoading && <span className="text-xs text-muted-foreground">Scoring match…</span>}
      {match.error && <span className="text-xs text-red-800">{String(match.error)}</span>}
      {match.data && (
        <span className="inline-flex flex-wrap items-center gap-2 rounded-full border border-border bg-card px-3 py-1 text-sm">
          <span className="font-display text-lg leading-none">{match.data.match_score}</span>
          <span className="text-muted-foreground">match</span>
          {match.data.missing_must_have.length > 0 && (
            <span className="text-xs text-muted-foreground">
              missing: {match.data.missing_must_have.join(", ")}
            </span>
          )}
        </span>
      )}
    </div>
  )
}

export default function SearchRoi() {
  const [sub, setSub] = useState<SubTab>("search")
  const [query, setQuery] = useState("")
  const [topK, setTopK] = useState(8)
  const [rerank, setRerank] = useState(true)
  const [resumeSkillsInput, setResumeSkillsInput] = useState("")
  const [matchJobId, setMatchJobId] = useState("")
  const [matchResumeInput, setMatchResumeInput] = useState("")

  const search = useQuery({
    queryKey: queryKeys.search(query, topK, rerank),
    queryFn: () => api.search({ query, top_k: topK, rerank }),
    enabled: sub === "search" && !!query.trim(),
  })

  const roi = useQuery({
    queryKey: queryKeys.roi(25),
    queryFn: () => api.roi(25),
    enabled: sub === "roi",
  })

  const matchSkills = parseSkills(matchResumeInput)
  const pasteMatch = useQuery({
    queryKey: queryKeys.match(matchJobId.trim(), matchResumeInput),
    queryFn: () => api.match({ job_id: matchJobId.trim(), resume_skills: matchSkills }),
    enabled: sub === "match" && !!matchJobId.trim() && matchSkills.length > 0,
  })

  return (
    <div className="space-y-8">
      <div>
        <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground mb-2">07 — Search & ROI</div>
        <h1 className="text-5xl leading-none">Search & ROI</h1>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {(
          [
            ["search", "Semantic job search"],
            ["roi", "Skill ROI"],
            ["match", "Match a JD"],
          ] as [SubTab, string][]
        ).map(([id, label]) => (
          <button
            key={id}
            className={`rounded-full px-4 py-1.5 text-sm transition ${
              sub === id ? "bg-primary text-primary-foreground" : "border border-border bg-card hover:border-foreground/40"
            }`}
            onClick={() => setSub(id)}
          >
            {label}
          </button>
        ))}
      </div>

      {sub === "search" && (
        <div className="space-y-6">
          <Card className="rounded-3xl">
            <CardContent className="pt-6 space-y-4">
              <input
                className="w-full rounded-full border border-border bg-card px-4 py-2 text-sm focus:outline-none focus:border-foreground"
                placeholder="e.g. backend engineer with python and postgres"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
              />
              <input
                className="w-full rounded-full border border-border bg-card px-4 py-2 text-sm focus:outline-none focus:border-foreground"
                placeholder="Your skills (comma-separated, e.g. Python, SQL) — scores every result below"
                value={resumeSkillsInput}
                onChange={(event) => setResumeSkillsInput(event.target.value)}
              />
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4 items-end">
                <div>
                  <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Results</label>
                  <input
                    type="number"
                    min={3}
                    max={25}
                    className="mt-2 w-full rounded-full border border-border bg-card px-4 py-2 text-sm"
                    value={topK}
                    onChange={(event) => setTopK(Number(event.target.value))}
                  />
                </div>
                <label className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={rerank} onChange={(event) => setRerank(event.target.checked)} />
                  Rerank with cross-encoder
                </label>
                <Button className="rounded-full" disabled={!query.trim()}>
                  Search
                </Button>
              </div>
            </CardContent>
          </Card>

          {search.isLoading && <div className="py-10">Searching…</div>}
          {search.error && <div className="py-10 text-red-800">{String(search.error)}</div>}
          {search.data && (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">Retrieved with {search.data.backend}.</p>
              {search.data.results.length === 0 ? (
                <p className="text-muted-foreground">No matching postings found.</p>
              ) : (
                search.data.results.map((result, index) => (
                  <Card key={result.job_id ?? `${result.title ?? "posting"}-${index}`} className="rounded-3xl">
                    <CardContent className="pt-6">
                      <div className="font-display text-xl">
                        {result.title ?? "Untitled role"} · {result.company ?? "Unknown"} · {result.score.toFixed(3)}
                      </div>
                      <div className="text-sm text-muted-foreground mt-1">
                        {result.location} · posted {result.posted_at ?? "n/a"}
                      </div>
                      {result.description && <p className="mt-2 text-sm">{result.description}</p>}
                      {result.skills.length > 0 && (
                        <p className="mt-2 text-xs text-muted-foreground">Skills: {result.skills.join(", ")}</p>
                      )}
                      {(result.ghost_risk || resumeSkillsInput.trim()) && (
                        <div className="mt-2 flex flex-wrap items-center gap-2">
                          <GhostBadge ghost={result.ghost_risk} />
                          <MatchBadge result={result} resumeSkillsInput={resumeSkillsInput} />
                        </div>
                      )}
                      {result.url && (
                        <a href={result.url} target="_blank" rel="noreferrer" className="inline-block mt-3 rounded-full border border-border px-4 py-1 text-sm hover:border-foreground">
                          View posting
                        </a>
                      )}
                    </CardContent>
                  </Card>
                ))
              )}
            </div>
          )}
        </div>
      )}

      {sub === "match" && (
        <div className="space-y-6">
          <Card className="rounded-3xl">
            <CardContent className="pt-6 space-y-4">
              <p className="text-sm text-muted-foreground">
                Score your profile against one posting. Paste a `job_id` from Recent Postings,
                then your skills — you get a weighted score and must-haves you lack.
              </p>
              <input
                className="w-full rounded-full border border-border bg-card px-4 py-2 text-sm focus:outline-none focus:border-foreground"
                placeholder="Job ID, e.g. jobspy:… or ashby:…"
                value={matchJobId}
                onChange={(event) => setMatchJobId(event.target.value)}
              />
              <input
                className="w-full rounded-full border border-border bg-card px-4 py-2 text-sm focus:outline-none focus:border-foreground"
                placeholder="Your skills (comma-separated, e.g. Python, SQL, Docker)"
                value={matchResumeInput}
                onChange={(event) => setMatchResumeInput(event.target.value)}
              />
            </CardContent>
          </Card>

          {pasteMatch.isLoading && <div className="py-10">Scoring match…</div>}
          {pasteMatch.error && <div className="py-10 text-red-800">{String(pasteMatch.error)}</div>}
          {pasteMatch.data && (
            <Card className="rounded-3xl">
              <CardContent className="pt-6">
                <h2 className="text-2xl">
                  Match score: <span className="font-display">{pasteMatch.data.match_score}</span>
                </h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  Health: {pasteMatch.data.posting_health} · confidence: {pasteMatch.data.confidence}
                </p>
                <div className="mt-2">
                  <GhostBadge ghost={pasteMatch.data.ghost_risk} />
                </div>
                <div className="mt-4 space-y-2 text-sm">
                  <p>
                    <span className="font-medium">Matched: </span>
                    {pasteMatch.data.matched_skills.join(", ") || "—"}
                  </p>
                  <p>
                    <span className="font-medium">Missing must-haves: </span>
                    {pasteMatch.data.missing_must_have.join(", ") || "—"}
                  </p>
                  <p>
                    <span className="font-medium">Missing nice-to-haves: </span>
                    {pasteMatch.data.missing_nice_to_have.join(", ") || "—"}
                  </p>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {sub === "roi" && (
        <div className="space-y-6">
          {roi.isLoading && <div className="py-10">Loading…</div>}
          {roi.error && <div className="py-10 text-red-800">{String(roi.error)}</div>}
          {roi.data && roi.data.rows.length === 0 && (
            <Card className="rounded-3xl">
              <CardContent className="pt-6 text-muted-foreground">Not enough dated postings to estimate skill ROI.</CardContent>
            </Card>
          )}
          {roi.data && roi.data.rows.length > 0 && (
            <>
              <Card className="rounded-3xl">
                <CardContent className="pt-6 overflow-auto">
                  <table className="min-w-full text-sm">
                    <thead>
                      <tr className="text-left text-muted-foreground border-b border-border">
                        <th className="py-2 pr-4 font-medium">Skill</th>
                        <th className="py-2 pr-4 font-medium">Demand</th>
                        <th className="py-2 pr-4 font-medium">Share %</th>
                        <th className="py-2 pr-4 font-medium">Momentum</th>
                        <th className="py-2 pr-4 font-medium">Premium</th>
                        <th className="py-2 pr-4 font-medium">ROI score</th>
                        <th className="py-2 font-medium">Confidence</th>
                      </tr>
                    </thead>
                    <tbody>
                      {roi.data.rows.map((row) => (
                        <tr key={row.skill} className="border-b border-border last:border-0">
                          <td className="py-2 pr-4 font-medium">{row.skill}</td>
                          <td className="py-2 pr-4">{row.demand}</td>
                          <td className="py-2 pr-4">{row.share_pct}</td>
                          <td className="py-2 pr-4">{row.momentum}</td>
                          <td className="py-2 pr-4">{row.premium ?? "—"}</td>
                          <td className="py-2 pr-4">{row.roi_score}</td>
                          <td className="py-2">{row.confidence}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </CardContent>
              </Card>
              <Card className="rounded-3xl">
                <CardContent className="pt-6">
                  <h2 className="text-2xl mb-3">Top skills by demand ROI score</h2>
                  <Plot
                    data={[
                      {
                        type: "bar",
                        orientation: "h",
                        x: roi.data.rows.slice(0, 15).map((row) => row.roi_score).reverse(),
                        y: roi.data.rows.slice(0, 15).map((row) => row.skill).reverse(),
                        marker: { color: INK },
                      },
                    ]}
                    layout={{
                      height: 450,
                      paper_bgcolor: "rgba(0,0,0,0)",
                      plot_bgcolor: "rgba(0,0,0,0)",
                      font: { family: "Inter, sans-serif", color: INK },
                      xaxis: { gridcolor: GRID },
                      yaxis: { gridcolor: GRID },
                      margin: { l: 150 },
                    }}
                    style={{ width: "100%" }}
                  />
                </CardContent>
              </Card>
            </>
          )}
        </div>
      )}
    </div>
  )
}