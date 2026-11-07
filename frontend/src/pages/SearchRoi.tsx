import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import Plot from 'react-plotly.js'
import { api } from '../lib/api'
import { queryKeys } from '../lib/queryKeys'

type SubTab = 'search' | 'roi'

export default function SearchRoi() {
  const [sub, setSub] = useState<SubTab>('search')
  const [query, setQuery] = useState('')
  const [topK, setTopK] = useState(8)
  const [rerank, setRerank] = useState(true)
  const [submitted, setSubmitted] = useState(false)

  const search = useQuery({
    queryKey: queryKeys.search(query, topK, rerank),
    queryFn: () => api.search({ query, top_k: topK, rerank }),
    enabled: submitted && sub === 'search' && !!query.trim(),
  })

  const roi = useQuery({
    queryKey: queryKeys.roi(25),
    queryFn: () => api.roi(25),
    enabled: sub === 'roi',
  })

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">Search & ROI</h1>
      <div className="flex gap-2">
        <button
          className={`px-3 py-1 rounded border ${sub === 'search' ? 'bg-slate-900 text-white' : 'bg-white'}`}
          onClick={() => setSub('search')}
        >
          Semantic job search
        </button>
        <button
          className={`px-3 py-1 rounded border ${sub === 'roi' ? 'bg-slate-900 text-white' : 'bg-white'}`}
          onClick={() => setSub('roi')}
        >
          Skill ROI
        </button>
      </div>

      {sub === 'search' && (
        <div className="space-y-4">
          <div className="bg-white rounded-lg shadow p-4 space-y-3">
            <input
              className="w-full border rounded px-2 py-2"
              placeholder="e.g. backend engineer with python and postgres"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4 items-end">
              <div>
                <label className="text-sm text-gray-500">Results</label>
                <input type="number" min={3} max={25} className="mt-1 w-full border rounded px-2 py-1" value={topK} onChange={(e) => setTopK(Number(e.target.value))} />
              </div>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={rerank} onChange={(e) => setRerank(e.target.checked)} />
                Rerank with cross-encoder
              </label>
              <button className="bg-blue-600 text-white px-4 py-2 rounded" onClick={() => setSubmitted(true)} disabled={!query.trim()}>
                Search
              </button>
            </div>
          </div>

          {search.isLoading && <div>Searching…</div>}
          {search.error && <div className="text-red-600">{String(search.error)}</div>}
          {search.data && (
            <div className="space-y-3">
              <p className="text-sm text-gray-500">Retrieved with {search.data.backend}.</p>
              {search.data.results.length === 0 ? (
                <p className="text-gray-500">No matching postings found.</p>
              ) : (
                search.data.results.map((r) => (
                  <div key={r.job_id ?? Math.random().toString()} className="bg-white rounded-lg shadow p-4">
                    <div className="font-semibold">
                      {r.title ?? 'Untitled role'} · {r.company ?? 'Unknown'} · score {r.score.toFixed(3)}
                    </div>
                    <div className="text-sm text-gray-500">{r.location} · posted {r.posted_at ?? 'n/a'}</div>
                    {r.description && <p className="mt-2 text-sm">{r.description}</p>}
                    {r.skills.length > 0 && <p className="mt-1 text-xs text-gray-500">Skills: {r.skills.join(', ')}</p>}
                    {r.url && <a href={r.url} target="_blank" rel="noreferrer" className="text-blue-600 underline text-sm">View posting</a>}
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      )}

      {sub === 'roi' && (
        <div className="space-y-4">
          {roi.isLoading && <div>Loading…</div>}
          {roi.error && <div className="text-red-600">{String(roi.error)}</div>}
          {roi.data && roi.data.rows.length === 0 && (
            <div className="bg-white rounded-lg shadow p-4 text-gray-500">
              Not enough dated postings to estimate skill ROI.
            </div>
          )}
          {roi.data && roi.data.rows.length > 0 && (
            <>
              <div className="bg-white rounded-lg shadow p-4 overflow-auto">
                <table className="min-w-full text-sm">
                  <thead>
                    <tr className="text-left text-gray-500 border-b">
                      <th className="py-2 pr-4">Skill</th>
                      <th className="py-2 pr-4">Demand</th>
                      <th className="py-2 pr-4">Share %</th>
                      <th className="py-2 pr-4">Momentum</th>
                      <th className="py-2 pr-4">Premium</th>
                      <th className="py-2 pr-4">ROI score</th>
                      <th className="py-2">Confidence</th>
                    </tr>
                  </thead>
                  <tbody>
                    {roi.data.rows.map((r) => (
                      <tr key={r.skill} className="border-b last:border-0">
                        <td className="py-2 pr-4 font-medium">{r.skill}</td>
                        <td className="py-2 pr-4">{r.demand}</td>
                        <td className="py-2 pr-4">{r.share_pct}</td>
                        <td className="py-2 pr-4">{r.momentum}</td>
                        <td className="py-2 pr-4">{r.premium ?? '—'}</td>
                        <td className="py-2 pr-4">{r.roi_score}</td>
                        <td className="py-2">{r.confidence}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="bg-white rounded-lg shadow p-4">
                <h2 className="font-semibold mb-2">Top skills by demand ROI score</h2>
                <Plot
                  data={[
                    {
                      type: 'bar',
                      orientation: 'h',
                      x: roi.data.rows.slice(0, 15).map((r) => r.roi_score).reverse(),
                      y: roi.data.rows.slice(0, 15).map((r) => r.skill).reverse(),
                    },
                  ]}
                  layout={{ height: 450, margin: { l: 150 } }}
                  style={{ width: '100%' }}
                />
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}