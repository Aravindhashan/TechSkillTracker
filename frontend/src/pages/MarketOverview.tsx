import { useQuery } from '@tanstack/react-query'
import Plot from 'react-plotly.js'
import { api } from '../lib/api'
import { queryKeys } from '../lib/queryKeys'

export default function MarketOverview() {
  const overview = useQuery({ queryKey: queryKeys.marketOverview, queryFn: api.marketOverview })
  const topSkills = useQuery({ queryKey: queryKeys.topSkills(10), queryFn: () => api.topSkills(10) })
  const locations = useQuery({ queryKey: ['market', 'locations', 10], queryFn: () => api.locations(10) })

  if (overview.isLoading) return <div className="p-6">Loading…</div>
  if (overview.error) return <div className="p-6 text-red-600">{String(overview.error)}</div>

  const o = overview.data!
  const skills = topSkills.data?.skills ?? []
  const locs = (locations.data as { locations?: { location: string; count: number }[] } | undefined)?.locations ?? []

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">Market Overview</h1>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Metric label="Total Job Openings" value={o.total_openings} />
        <Metric label="Unique Technologies" value={o.unique_skills} />
        <Metric label="Companies Hiring" value={o.companies} />
        <Metric label="Locations" value={o.locations} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow p-4">
          <h2 className="font-semibold mb-2">Top 10 In-Demand Skills</h2>
          <Plot
            data={[{ type: 'bar', x: skills.map((s) => s.count), y: skills.map((s) => s.skill), orientation: 'h' }]}
            layout={{ height: 400, margin: { l: 120 } }}
            style={{ width: '100%' }}
          />
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <h2 className="font-semibold mb-2">Job Distribution by Location</h2>
          <Plot
            data={[{ type: 'pie', values: locs.map((l) => l.count), labels: locs.map((l) => l.location), hole: 0.4 }]}
            layout={{ height: 400 }}
            style={{ width: '100%' }}
          />
        </div>
      </div>
    </div>
  )
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-white rounded-lg shadow p-4">
      <div className="text-sm text-gray-500">{label}</div>
      <div className="text-2xl font-bold">{value.toLocaleString()}</div>
    </div>
  )
}