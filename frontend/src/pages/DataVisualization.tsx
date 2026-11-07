import { useQuery } from "@tanstack/react-query"
import Plot from "react-plotly.js"
import { api } from "@/lib/api"
import { queryKeys } from "@/lib/queryKeys"
import { Card, CardContent } from "@/components/ui/card"

export default function DataVisualization() {
  const trends = useQuery({ queryKey: queryKeys.demandTrends(5), queryFn: () => api.demandTrends(5) })
  const pairs = useQuery({ queryKey: queryKeys.skillPairs(2), queryFn: () => api.skillPairs(2) })

  if (trends.isLoading || pairs.isLoading) return <div className="p-6">Loading…</div>

  const trendRows = trends.data ?? []
  const skillNames = Array.from(new Set(trendRows.map((row) => row.skill)))
  const trendData = skillNames.map((skill) => ({
    type: "scatter" as const,
    mode: "lines+markers" as const,
    name: skill,
    x: trendRows.filter((row) => row.skill === skill).map((row) => row.month),
    y: trendRows.filter((row) => row.skill === skill).map((row) => row.count),
  }))

  const pairRows = pairs.data ?? []

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">Data Visualization</h1>
      <Card>
        <CardContent className="pt-6">
          <h2 className="font-semibold mb-2">Technology Demand Trends Over Time</h2>
          <Plot data={trendData} layout={{ height: 450 }} style={{ width: "100%" }} />
        </CardContent>
      </Card>
      <Card>
        <CardContent className="pt-6">
          <h2 className="font-semibold mb-2">Skill Co-occurrence</h2>
          {pairRows.length === 0 ? (
            <p className="text-gray-500">Insufficient data.</p>
          ) : (
            <Plot
              data={[
                {
                  type: "bar",
                  orientation: "h",
                  x: pairRows.slice(0, 15).map((pair) => pair.count).reverse(),
                  y: pairRows.slice(0, 15).map((pair) => `${pair.skill_a} + ${pair.skill_b}`).reverse(),
                },
              ]}
              layout={{ height: 450, margin: { l: 200 } }}
              style={{ width: "100%" }}
            />
          )}
        </CardContent>
      </Card>
    </div>
  )
}