import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { queryKeys } from '../lib/queryKeys'

interface GroupRow {
  group: string
  postings: number
  share_pct: number
  mean_experience: number | null
  distinct_skills: number
  top_skill: string | null
  median_momentum: number | null
  median_roi_score: number | null
}

interface FairnessResult {
  overall?: { postings: number; skills: number; months: number }
  by_location?: GroupRow[]
  by_remote?: GroupRow[]
  by_company_type?: GroupRow[]
  gaps?: {
    location_share_range_pp?: number
    remote_share_gap_pp?: number
    company_type_share_range_pp?: number
    adjusted_by_location?: Record<string, number | null>
    adjusted_by_remote?: Record<string, number | null>
    adjusted_by_company_type?: Record<string, number | null>
  }
  confidence?: string
  notes?: string[]
}

export default function FairnessAudit() {
  const fair = useQuery({ queryKey: queryKeys.fairness, queryFn: api.fairness })
  if (fair.isLoading) return <div className="p-6">Loading…</div>
  if (fair.error) return <div className="p-6 text-red-600">{String(fair.error)}</div>

  const r = fair.data as FairnessResult

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">Fairness Audit</h1>
      <p className="text-gray-500 text-sm max-w-3xl">
        Demand gaps across locations, remote status, and company types, after controlling for skill and experience.
        All figures are associations in observed postings, not causal effects.
      </p>

      {r.confidence === 'low' && (
        <div className="bg-amber-50 border border-amber-200 text-amber-800 rounded p-3 text-sm">
          Low confidence — fewer than 10 postings or fewer than 3 months of history. Descriptive shares are shown;
          adjusted gaps are withheld until the corpus grows.
        </div>
      )}

      <div className="grid grid-cols-3 gap-4">
        <Metric label="Postings audited" value={r.overall?.postings ?? 0} />
        <Metric label="Distinct skills" value={r.overall?.skills ?? 0} />
        <Metric label="Months of history" value={r.overall?.months ?? 0} />
      </div>

      <div className="grid grid-cols-3 gap-4">
        <Metric label="Location share range" value={`${r.gaps?.location_share_range_pp ?? 0} pp`} />
        <Metric label="Remote share gap" value={`${r.gaps?.remote_share_gap_pp ?? 0} pp`} />
        <Metric label="Company-type range" value={`${r.gaps?.company_type_share_range_pp ?? 0} pp`} />
      </div>

      <GroupTable title="By location" rows={r.by_location ?? []} adjusted={r.gaps?.adjusted_by_location} />
      <GroupTable title="By remote status" rows={r.by_remote ?? []} adjusted={r.gaps?.adjusted_by_remote} />
      <GroupTable title="By company type" rows={r.by_company_type ?? []} adjusted={r.gaps?.adjusted_by_company_type} />

      {(r.notes ?? []).map((n, i) => (
        <p key={i} className="text-xs text-gray-400">{n}</p>
      ))}
    </div>
  )
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-white rounded-lg shadow p-4">
      <div className="text-sm text-gray-500">{label}</div>
      <div className="text-2xl font-bold">{value}</div>
    </div>
  )
}

function GroupTable({ title, rows, adjusted }: { title: string; rows: GroupRow[]; adjusted?: Record<string, number | null> }) {
  if (rows.length === 0) return <div className="bg-white rounded-lg shadow p-4"><h2 className="font-semibold mb-2">{title}</h2><p className="text-gray-500">No postings in range.</p></div>
  return (
    <div className="bg-white rounded-lg shadow p-4">
      <h2 className="font-semibold mb-2">{title}</h2>
      <div className="overflow-auto">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="text-left text-gray-500 border-b">
              <th className="py-2 pr-4">Group</th>
              <th className="py-2 pr-4">Postings</th>
              <th className="py-2 pr-4">Share %</th>
              <th className="py-2 pr-4">Mean exp</th>
              <th className="py-2 pr-4">Distinct skills</th>
              <th className="py-2 pr-4">Top skill</th>
              <th className="py-2">Median ROI</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.group} className="border-b last:border-0">
                <td className="py-2 pr-4 font-medium">{r.group}</td>
                <td className="py-2 pr-4">{r.postings}</td>
                <td className="py-2 pr-4">{r.share_pct}</td>
                <td className="py-2 pr-4">{r.mean_experience ?? '—'}</td>
                <td className="py-2 pr-4">{r.distinct_skills}</td>
                <td className="py-2 pr-4">{r.top_skill ?? '—'}</td>
                <td className="py-2">{r.median_roi_score ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {adjusted && Object.keys(adjusted).length > 0 ? (
        <p className="mt-3 text-xs text-gray-500">
          Adjusted gaps: {Object.entries(adjusted).map(([g, v]) => `${g}: ${v ?? 'baseline'}`).join(', ')}
        </p>
      ) : (
        <p className="mt-3 text-xs text-gray-400">
          Adjusted gaps need at least three months of history; descriptive shares above are still reported.
        </p>
      )}
    </div>
  )
}