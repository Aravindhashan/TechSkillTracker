import { useQuery } from "@tanstack/react-query"
import Plot from "react-plotly.js"
import { api } from "@/lib/api"
import { queryKeys } from "@/lib/queryKeys"
import Metric from "@/components/Metric"
import { Card, CardContent } from "@/components/ui/card"

const INK = "#1A1815"
const GRID = "#E4DCC8"
const chartLayout = {
  height: 400,
  paper_bgcolor: "rgba(0,0,0,0)",
  plot_bgcolor: "rgba(0,0,0,0)",
  font: { family: "Inter, sans-serif", color: INK },
  xaxis: { gridcolor: GRID },
  yaxis: { gridcolor: GRID },
}

export default function MarketOverview() {
  const overview = useQuery({ queryKey: queryKeys.marketOverview, queryFn: api.marketOverview })
  const topSkills = useQuery({ queryKey: queryKeys.topSkills(10), queryFn: () => api.topSkills(10) })
  const locations = useQuery({ queryKey: queryKeys.locations(10), queryFn: () => api.locations(10) })

  if (overview.isLoading) return <div className="py-10">Loading…</div>
  if (overview.error) return <div className="py-10 text-red-800">{String(overview.error)}</div>

  const overviewData = overview.data!
  const skills = topSkills.data?.skills ?? []
  const locationRows = locations.data?.locations ?? []

  return (
    <div className="space-y-8">
      <div>
        <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground mb-2">01 — Overview</div>
        <h1 className="text-5xl leading-none">Market Overview</h1>
        <p className="mt-3 max-w-xl text-muted-foreground">
          Headline demand, the skills everyone is hiring for, and where they are hiring from.
        </p>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Metric label="Total Job Openings" value={overviewData.total_openings} />
        <Metric label="Unique Technologies" value={overviewData.unique_skills} />
        <Metric label="Companies Hiring" value={overviewData.companies} />
        <Metric label="Locations" value={overviewData.locations} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card className="rounded-3xl">
          <CardContent className="pt-6">
            <h2 className="text-2xl mb-3">Top 10 In-Demand Skills</h2>
            <Plot
              data={[{ type: "bar", x: skills.map((s) => s.count), y: skills.map((s) => s.skill), orientation: "h", marker: { color: INK } }]}
              layout={{ ...chartLayout, margin: { l: 120 } }}
              style={{ width: "100%" }}
            />
          </CardContent>
        </Card>
        <Card className="rounded-3xl">
          <CardContent className="pt-6">
            <h2 className="text-2xl mb-3">Job Distribution by Location</h2>
            <Plot
              data={[{ type: "pie", values: locationRows.map((loc) => loc.count), labels: locationRows.map((loc) => loc.location), hole: 0.45, marker: { colors: [INK, "#5C5548", "#8A8171", "#B8AE9C", "#D8CFBB", "#4A4438", "#6B645A", "#9A917F", "#CDC2A6", "#39352B"] } }]}
              layout={{ ...chartLayout, height: 400 }}
              style={{ width: "100%" }}
            />
          </CardContent>
        </Card>
      </div>
    </div>
  )
}