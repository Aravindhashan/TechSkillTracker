import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { queryKeys } from "@/lib/queryKeys"
import Metric from "@/components/Metric"
import { Card, CardContent } from "@/components/ui/card"

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
  const fairness = useQuery({ queryKey: queryKeys.fairness, queryFn: api.fairness })
  if (fairness.isLoading) return <div className="py-10">Loading…</div>
  if (fairness.error) return <div className="py-10 text-red-800">{String(fairness.error)}</div>

  const fairnessData = fairness.data as FairnessResult

  return (
    <div className="space-y-8">
      <div>
        <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground mb-2">08 — Fairness</div>
        <h1 className="text-5xl leading-none">Fairness Audit</h1>
        <p className="mt-3 max-w-2xl text-muted-foreground">
          Demand gaps across locations, remote status, and company types, after controlling for skill and experience.
          All figures are associations in observed postings, not causal effects.
        </p>
      </div>

      {fairnessData.confidence === "low" && (
        <div className="rounded-2xl border border-border bg-card p-4 text-sm">
          Low confidence — fewer than 10 postings or fewer than 3 months of history. Descriptive shares are shown;
          adjusted gaps are withheld until the corpus grows.
        </div>
      )}

      <div className="grid grid-cols-3 gap-4">
        <Metric label="Postings audited" value={fairnessData.overall?.postings ?? 0} />
        <Metric label="Distinct skills" value={fairnessData.overall?.skills ?? 0} />
        <Metric label="Months of history" value={fairnessData.overall?.months ?? 0} />
      </div>

      <div className="grid grid-cols-3 gap-4">
        <Metric label="Location share range" value={`${fairnessData.gaps?.location_share_range_pp ?? 0} pp`} />
        <Metric label="Remote share gap" value={`${fairnessData.gaps?.remote_share_gap_pp ?? 0} pp`} />
        <Metric label="Company-type range" value={`${fairnessData.gaps?.company_type_share_range_pp ?? 0} pp`} />
      </div>

      <GroupTable title="By location" rows={fairnessData.by_location ?? []} adjusted={fairnessData.gaps?.adjusted_by_location} />
      <GroupTable title="By remote status" rows={fairnessData.by_remote ?? []} adjusted={fairnessData.gaps?.adjusted_by_remote} />
      <GroupTable title="By company type" rows={fairnessData.by_company_type ?? []} adjusted={fairnessData.gaps?.adjusted_by_company_type} />

      {(fairnessData.notes ?? []).map((note, index) => (
        <p key={index} className="text-xs text-muted-foreground">
          {note}
        </p>
      ))}
    </div>
  )
}

function GroupTable({
  title,
  rows,
  adjusted,
}: {
  title: string
  rows: GroupRow[]
  adjusted?: Record<string, number | null>
}) {
  if (rows.length === 0)
    return (
      <Card className="rounded-3xl">
        <CardContent className="pt-6">
          <h2 className="text-2xl mb-2">{title}</h2>
          <p className="text-muted-foreground">No postings in range.</p>
        </CardContent>
      </Card>
    )
  return (
    <Card className="rounded-3xl">
      <CardContent className="pt-6">
        <h2 className="text-2xl mb-3">{title}</h2>
        <div className="overflow-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left text-muted-foreground border-b border-border">
                <th className="py-2 pr-4 font-medium">Group</th>
                <th className="py-2 pr-4 font-medium">Postings</th>
                <th className="py-2 pr-4 font-medium">Share %</th>
                <th className="py-2 pr-4 font-medium">Mean exp</th>
                <th className="py-2 pr-4 font-medium">Distinct skills</th>
                <th className="py-2 pr-4 font-medium">Top skill</th>
                <th className="py-2 font-medium">Median ROI</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.group} className="border-b border-border last:border-0">
                  <td className="py-2 pr-4 font-medium">{row.group}</td>
                  <td className="py-2 pr-4">{row.postings}</td>
                  <td className="py-2 pr-4">{row.share_pct}</td>
                  <td className="py-2 pr-4">{row.mean_experience ?? "—"}</td>
                  <td className="py-2 pr-4">{row.distinct_skills}</td>
                  <td className="py-2 pr-4">{row.top_skill ?? "—"}</td>
                  <td className="py-2">{row.median_roi_score ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {adjusted && Object.keys(adjusted).length > 0 ? (
          <p className="mt-3 text-xs text-muted-foreground">
            Adjusted gaps: {Object.entries(adjusted).map(([group, gapValue]) => `${group}: ${gapValue ?? "baseline"}`).join(", ")}
          </p>
        ) : (
          <p className="mt-3 text-xs text-muted-foreground">
            Adjusted gaps need at least three months of history; descriptive shares above are still reported.
          </p>
        )}
      </CardContent>
    </Card>
  )
}