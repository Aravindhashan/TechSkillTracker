import { useQuery } from "@tanstack/react-query"
import Plot from "react-plotly.js"
import { api } from "@/lib/api"
import { queryKeys } from "@/lib/queryKeys"
import Metric from "@/components/Metric"
import { Card, CardContent } from "@/components/ui/card"

export default function MarketOverview() {
  const overview = useQuery({ queryKey: queryKeys.marketOverview, queryFn: api.marketOverview })
  const topSkills = useQuery({ queryKey: queryKeys.topSkills(10), queryFn: () => api.topSkills(10) })
  const locations = useQuery({ queryKey: queryKeys.locations(10), queryFn: () => api.locations(10) })

  if (overview.isLoading) return <div className="p-6">Loading…</div>
  if (overview.error) return <div className="p-6 text-red-600">{String(overview.error)}</div>

  const overviewData = overview.data!
  const skills = topSkills.data?.skills ?? []
  const locationRows = locations.data?.locations ?? []

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">Market Overview</h1>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Metric label="Total Job Openings" value={overviewData.total_openings} />
        <Metric label="Unique Technologies" value={overviewData.unique_skills} />
        <Metric label="Companies Hiring" value={overviewData.companies} />
        <Metric label="Locations" value={overviewData.locations} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardContent className="pt-6">
            <h2 className="font-semibold mb-2">Top 10 In-Demand Skills</h2>
            <Plot
              data={[{ type: "bar", x: skills.map((s) => s.count), y: skills.map((s) => s.skill), orientation: "h" }]}
              layout={{ height: 400, margin: { l: 120 } }}
              style={{ width: "100%" }}
            />
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <h2 className="font-semibold mb-2">Job Distribution by Location</h2>
            <Plot
              data={[{ type: "pie", values: locationRows.map((loc) => loc.count), labels: locationRows.map((loc) => loc.location), hole: 0.4 }]}
              layout={{ height: 400 }}
              style={{ width: "100%" }}
            />
          </CardContent>
        </Card>
      </div>
    </div>
  )
}