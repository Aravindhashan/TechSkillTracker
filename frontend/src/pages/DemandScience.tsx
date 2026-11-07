import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import Plot from "react-plotly.js"
import { api } from "@/lib/api"
import { queryKeys } from "@/lib/queryKeys"
import { Card, CardContent } from "@/components/ui/card"

type SubTab = "survival" | "anomalies" | "pmi" | "communities" | "relatedness"

const INK = "#1A1815"
const GRID = "#E4DCC8"

export default function DemandScience() {
  const [sub, setSub] = useState<SubTab>("survival")
  const [relatedSkill, setRelatedSkill] = useState("")
  const science = useQuery({ queryKey: queryKeys.demandScience, queryFn: api.demandScience })

  if (science.isLoading) return <div className="py-10">Loading…</div>
  if (science.error) return <div className="py-10 text-red-800">{String(science.error)}</div>
  const data = science.data!

  return (
    <div className="space-y-8">
      <div>
        <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground mb-2">06 — Science</div>
        <h1 className="text-5xl leading-none">Demand Science</h1>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {(
          [
            ["survival", "Survival (time-to-fill)"],
            ["anomalies", "Anomalies"],
            ["pmi", "Skill associations"],
            ["communities", "Skill communities"],
            ["relatedness", "Relatedness"],
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

      {sub === "survival" && (
        <Card className="rounded-3xl">
          <CardContent className="pt-6">
            <h2 className="text-2xl mb-3">Kaplan–Meier survival curve</h2>
            {data.survival_overall.length === 0 ? (
              <p className="text-muted-foreground">Not enough data for survival analysis.</p>
            ) : (
              <Plot
                data={[
                  {
                    type: "scatter",
                    mode: "lines+markers",
                    name: "Overall",
                    x: data.survival_overall.map((point) => point.time),
                    y: data.survival_overall.map((point) => point.survival),
                    line: { color: INK },
                    marker: { color: INK },
                  },
                ]}
                layout={{
                  height: 400,
                  paper_bgcolor: "rgba(0,0,0,0)",
                  plot_bgcolor: "rgba(0,0,0,0)",
                  font: { family: "Inter, sans-serif", color: INK },
                  xaxis: { gridcolor: GRID, title: "Days since first seen" },
                  yaxis: { gridcolor: GRID, title: "Survival probability" },
                }}
                style={{ width: "100%" }}
              />
            )}
          </CardContent>
        </Card>
      )}

      {sub === "anomalies" && (
        <Card className="rounded-3xl">
          <CardContent className="pt-6">
            <h2 className="text-2xl mb-3">Anomalous postings</h2>
            {data.anomalies.length === 0 ? (
              <p className="text-muted-foreground">No anomalies detected.</p>
            ) : (
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="text-left text-muted-foreground border-b border-border">
                    <th className="py-2 pr-4 font-medium">Title</th>
                    <th className="py-2 pr-4 font-medium">Skill</th>
                    <th className="py-2 font-medium">Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {data.anomalies.map((anomaly, index) => (
                    <tr key={index} className="border-b border-border last:border-0">
                      <td className="py-2 pr-4">{anomaly["Job Title"]}</td>
                      <td className="py-2 pr-4">{anomaly["Tech Skill"]}</td>
                      <td className="py-2">{anomaly.reason ?? ""}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </CardContent>
        </Card>
      )}

      {sub === "pmi" && (
        <Card className="rounded-3xl">
          <CardContent className="pt-6">
            <h2 className="text-2xl mb-3">Skill pairs by PMI</h2>
            {data.pmi_pairs.length === 0 ? (
              <p className="text-muted-foreground">Not enough data for association mining.</p>
            ) : (
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="text-left text-muted-foreground border-b border-border">
                    <th className="py-2 pr-4 font-medium">Skill A</th>
                    <th className="py-2 pr-4 font-medium">Skill B</th>
                    <th className="py-2 pr-4 font-medium">Co-occurrence</th>
                    <th className="py-2 font-medium">PMI</th>
                  </tr>
                </thead>
                <tbody>
                  {data.pmi_pairs.slice(0, 20).map((pair, index) => (
                    <tr key={index} className="border-b border-border last:border-0">
                      <td className="py-2 pr-4">{pair.skill_a}</td>
                      <td className="py-2 pr-4">{pair.skill_b}</td>
                      <td className="py-2 pr-4">{pair.cooccurrence}</td>
                      <td className="py-2">{pair.pmi}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </CardContent>
        </Card>
      )}

      {sub === "communities" && (
        <Card className="rounded-3xl">
          <CardContent className="pt-6">
            <h2 className="text-2xl mb-3">Skill communities (Louvain)</h2>
            {Object.keys(data.communities).length === 0 ? (
              <p className="text-muted-foreground">Not enough data for community detection.</p>
            ) : (
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="text-left text-muted-foreground border-b border-border">
                    <th className="py-2 pr-4 font-medium">Skill</th>
                    <th className="py-2 font-medium">Community</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(data.communities).map(([skill, community]) => (
                    <tr key={skill} className="border-b border-border last:border-0">
                      <td className="py-2 pr-4">{skill}</td>
                      <td className="py-2">{community}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </CardContent>
        </Card>
      )}

      {sub === "relatedness" && (
        <Card className="rounded-3xl">
          <CardContent className="pt-6">
            <h2 className="text-2xl mb-3">Word2Vec skill relatedness</h2>
            {Object.keys(data.relatedness).length === 0 ? (
              <p className="text-muted-foreground">
                Not enough data for embeddings (need gensim + at least 5 postings with multiple skills).
              </p>
            ) : (
              <>
                <div className="mb-4 max-w-sm">
                  <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Skill</label>
                  <select
                    className="mt-2 w-full rounded-full border border-border bg-card px-4 py-2 text-sm focus:outline-none focus:border-foreground"
                    value={relatedSkill || Object.keys(data.relatedness)[0] || ""}
                    onChange={(event) => setRelatedSkill(event.target.value)}
                  >
                    {Object.keys(data.relatedness).map((skillName) => (
                      <option key={skillName} value={skillName}>
                        {skillName}
                      </option>
                    ))}
                  </select>
                </div>
                {(() => {
                  const selected = relatedSkill || Object.keys(data.relatedness)[0]
                  const relatedRows = (data.relatedness[selected] ?? []).map((entry) => ({
                    skill: entry[0],
                    similarity: entry[1],
                  }))
                  return relatedRows.length === 0 ? (
                    <p className="text-muted-foreground">No related skills found.</p>
                  ) : (
                    <table className="min-w-full text-sm">
                      <thead>
                        <tr className="text-left text-muted-foreground border-b border-border">
                          <th className="py-2 pr-4 font-medium">Skill</th>
                          <th className="py-2 font-medium">Similarity</th>
                        </tr>
                      </thead>
                      <tbody>
                        {relatedRows.map((relatedRow) => (
                          <tr key={relatedRow.skill} className="border-b border-border last:border-0">
                            <td className="py-2 pr-4">{relatedRow.skill}</td>
                            <td className="py-2">{relatedRow.similarity.toFixed(3)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )
                })()}
              </>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}