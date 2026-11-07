import { useQuery } from '@tanstack/react-query'
import Plot from 'react-plotly.js'
import { api } from '../lib/api'

export default function DataVisualization() {
  const trends = useQuery({ queryKey: ['market', 'demand-trends', 5], queryFn: () => api.demandTrends(5) })
  const pairs = useQuery({ queryKey: ['market', 'skill-pairs', 2], queryFn: () => api.skillPairs(2) })

  if (trends.isLoading || pairs.isLoading) return <div className="p-6">Loading…</div>

  const trendRows = (trends.data ?? []) as { skill: string; month: string; count: number }[]
  const skills = Array.from(new Set(trendRows.map((r) => r.skill)))
  const trendData = skills.map((skill) => ({
    type: 'scatter' as const,
    mode: 'lines+markers' as const,
    name: skill,
    x: trendRows.filter((r) => r.skill === skill).map((r) => r.month),
    y: trendRows.filter((r) => r.skill === skill).map((r) => r.count),
  }))

  const pairRows = (pairs.data ?? []) as { skill_a: string; skill_b: string; count: number }[]

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">Data Visualization</h1>
      <div className="bg-white rounded-lg shadow p-4">
        <h2 className="font-semibold mb-2">Technology Demand Trends Over Time</h2>
        <Plot data={trendData} layout={{ height: 450 }} style={{ width: '100%' }} />
      </div>
      <div className="bg-white rounded-lg shadow p-4">
        <h2 className="font-semibold mb-2">Skill Co-occurrence</h2>
        {pairRows.length === 0 ? (
          <p className="text-gray-500">Insufficient data.</p>
        ) : (
          <Plot
            data={[
              {
                type: 'bar',
                orientation: 'h',
                x: pairRows.slice(0, 15).map((p) => p.count).reverse(),
                y: pairRows.slice(0, 15).map((p) => `${p.skill_a} + ${p.skill_b}`).reverse(),
              },
            ]}
            layout={{ height: 450, margin: { l: 200 } }}
            style={{ width: '100%' }}
          />
        )}
      </div>
    </div>
  )
}