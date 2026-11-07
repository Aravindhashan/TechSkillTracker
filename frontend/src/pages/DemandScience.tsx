import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import Plot from 'react-plotly.js'
import { api } from '../lib/api'
import { queryKeys } from '../lib/queryKeys'

type SubTab = 'survival' | 'anomalies' | 'pmi' | 'communities'

export default function DemandScience() {
  const [sub, setSub] = useState<SubTab>('survival')
  const ds = useQuery({ queryKey: queryKeys.demandScience, queryFn: api.demandScience })

  if (ds.isLoading) return <div className="p-6">Loading…</div>
  if (ds.error) return <div className="p-6 text-red-600">{String(ds.error)}</div>
  const data = ds.data!

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">Demand Science</h1>
      <div className="flex gap-2">
        {([['survival', 'Survival (time-to-fill)'], ['anomalies', 'Anomalies'], ['pmi', 'Skill associations'], ['communities', 'Skill communities']] as [SubTab, string][]).map(([id, label]) => (
          <button
            key={id}
            className={`px-3 py-1 rounded border ${sub === id ? 'bg-slate-900 text-white' : 'bg-white'}`}
            onClick={() => setSub(id)}
          >
            {label}
          </button>
        ))}
      </div>

      {sub === 'survival' && (
        <div className="bg-white rounded-lg shadow p-4">
          <h2 className="font-semibold mb-2">Kaplan–Meier survival curve</h2>
          {data.survival_overall.length === 0 ? (
            <p className="text-gray-500">Not enough data for survival analysis.</p>
          ) : (
            <Plot
              data={[
                {
                  type: 'scatter',
                  mode: 'lines+markers',
                  name: 'Overall',
                  x: (data.survival_overall as Record<string, unknown>[]).map((r) => Number(r.time ?? 0)),
                  y: (data.survival_overall as Record<string, unknown>[]).map((r) => Number(r.survival ?? 0)),
                },
              ]}
              layout={{ height: 400, xaxis: { title: 'Days since first seen' }, yaxis: { title: 'Survival probability' } }}
              style={{ width: '100%' }}
            />
          )}
        </div>
      )}

      {sub === 'anomalies' && (
        <div className="bg-white rounded-lg shadow p-4">
          <h2 className="font-semibold mb-2">Anomalous postings</h2>
          {data.anomalies.length === 0 ? (
            <p className="text-gray-500">No anomalies detected.</p>
          ) : (
            <table className="min-w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 border-b">
                  <th className="py-2 pr-4">Title</th>
                  <th className="py-2 pr-4">Skill</th>
                  <th className="py-2">Reason</th>
                </tr>
              </thead>
              <tbody>
                {data.anomalies.map((a, i) => (
                  <tr key={i} className="border-b last:border-0">
                    <td className="py-2 pr-4">{String((a as Record<string, unknown>)['Job Title'] ?? '')}</td>
                    <td className="py-2 pr-4">{String((a as Record<string, unknown>)['Tech Skill'] ?? '')}</td>
                    <td className="py-2">{String((a as Record<string, unknown>).reason ?? '')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {sub === 'pmi' && (
        <div className="bg-white rounded-lg shadow p-4">
          <h2 className="font-semibold mb-2">Skill pairs by PMI</h2>
          {data.pmi_pairs.length === 0 ? (
            <p className="text-gray-500">Not enough data for association mining.</p>
          ) : (
            <table className="min-w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 border-b">
                  <th className="py-2 pr-4">Skill A</th>
                  <th className="py-2 pr-4">Skill B</th>
                  <th className="py-2 pr-4">Co-occurrence</th>
                  <th className="py-2">PMI</th>
                </tr>
              </thead>
              <tbody>
                {data.pmi_pairs.slice(0, 20).map((p, i) => (
                  <tr key={i} className="border-b last:border-0">
                    <td className="py-2 pr-4">{String((p as Record<string, unknown>).skill_a ?? '')}</td>
                    <td className="py-2 pr-4">{String((p as Record<string, unknown>).skill_b ?? '')}</td>
                    <td className="py-2 pr-4">{String((p as Record<string, unknown>).cooccurrence ?? '')}</td>
                    <td className="py-2">{String((p as Record<string, unknown>).pmi ?? '')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {sub === 'communities' && (
        <div className="bg-white rounded-lg shadow p-4">
          <h2 className="font-semibold mb-2">Skill communities (Louvain)</h2>
          {Object.keys(data.communities).length === 0 ? (
            <p className="text-gray-500">Not enough data for community detection.</p>
          ) : (
            <table className="min-w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 border-b">
                  <th className="py-2 pr-4">Skill</th>
                  <th className="py-2">Community</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(data.communities).map(([skill, c]) => (
                  <tr key={skill} className="border-b last:border-0">
                    <td className="py-2 pr-4">{skill}</td>
                    <td className="py-2">{c}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  )
}