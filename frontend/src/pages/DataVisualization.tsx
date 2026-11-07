import { useQuery } from "@tanstack/react-query"
import Plot from "react-plotly.js"
import { api } from "@/lib/api"
import { queryKeys } from "@/lib/queryKeys"
import { Card, CardContent } from "@/components/ui/card"

const INK = "#1A1815"
const GRID = "#E4DCC8"
const PALETTE = ["#1A1815", "#5C5548", "#8A8171", "#B8AE9C", "#6B645A", "#39352B", "#CDC2A6", "#4A4438"]
const chartLayout = {
  height: 450,
  paper_bgcolor: "rgba(0,0,0,0)",
  plot_bgcolor: "rgba(0,0,0,0)",
  font: { family: "Inter, sans-serif", color: INK },
  xaxis: { gridcolor: GRID },
  yaxis: { gridcolor: GRID },
}

export default function DataVisualization() {
  const trends = useQuery({ queryKey: queryKeys.demandTrends(5), queryFn: () => api.demandTrends(5) })
  const pairs = useQuery({ queryKey: queryKeys.skillPairs(2), queryFn: () => api.skillPairs(2) })

  if (trends.isLoading || pairs.isLoading) return <div className="py-10">Loading…</div>

  const trendRows = trends.data ?? []
  const skillNames = Array.from(new Set(trendRows.map((row) => row.skill)))
  const trendData = skillNames.map((skill, i) => ({
    type: "scatter" as const,
    mode: "lines+markers" as const,
    name: skill,
    x: trendRows.filter((row) => row.skill === skill).map((row) => row.month),
    y: trendRows.filter((row) => row.skill === skill).map((row) => row.count),
    line: { color: PALETTE[i % PALETTE.length] },
    marker: { color: PALETTE[i % PALETTE.length] },
  }))

  const pairRows = pairs.data ?? []

  return (
    <div className="space-y-8">
      <div>
        <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground mb-2">02 — Data Viz</div>
        <h1 className="text-5xl leading-none">Demand Trends</h1>
      </div>
      <Card className="rounded-3xl">
        <CardContent className="pt-6">
          <h2 className="text-2xl mb-3">Technology Demand Trends Over Time</h2>
          <Plot data={trendData} layout={chartLayout} style={{ width: "100%" }} />
        </CardContent>
      </Card>
      <Card className="rounded-3xl">
        <CardContent className="pt-6">
          <h2 className="text-2xl mb-3">Skill Co-occurrence</h2>
          {pairRows.length === 0 ? (
            <p className="text-muted-foreground">Insufficient data.</p>
          ) : (
            <Plot
              data={[
                {
                  type: "bar",
                  orientation: "h",
                  x: pairRows.slice(0, 15).map((pair) => pair.count).reverse(),
                  y: pairRows.slice(0, 15).map((pair) => `${pair.skill_a} + ${pair.skill_b}`).reverse(),
                  marker: { color: INK },
                },
              ]}
              layout={{ ...chartLayout, margin: { l: 200 } }}
              style={{ width: "100%" }}
            />
          )}
        </CardContent>
      </Card>
    </div>
  )
}