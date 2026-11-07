import { useQuery } from "@tanstack/react-query"
import Plot from "react-plotly.js"
import { api } from "@/lib/api"
import { queryKeys } from "@/lib/queryKeys"
import { useFilters } from "@/context/FilterContext"
import Metric from "@/components/Metric"
import { Button } from "@/components/ui/button"
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
  const { selectedSkills, selectedLocations } = useFilters()
  const skillParam = selectedSkills.join(",")
  const locationParam = selectedLocations.join(",")
  const filters = { skills: selectedSkills, locations: selectedLocations }
  const overview = useQuery({
    queryKey: queryKeys.marketOverview(skillParam, locationParam),
    queryFn: () => api.marketOverview(filters),
  })
  const topSkills = useQuery({
    queryKey: queryKeys.topSkills(10, skillParam, locationParam),
    queryFn: () => api.topSkills(10, filters),
  })
  const locations = useQuery({
    queryKey: queryKeys.locations(10, skillParam, locationParam),
    queryFn: () => api.locations(10, filters),
  })
  const recentPostings = useQuery({
    queryKey: queryKeys.recentPostings(10, skillParam, locationParam),
    queryFn: () => api.recentPostings(10, filters),
  })

  if (overview.isLoading) return <div className="py-10">Loading…</div>
  if (overview.error) return <div className="py-10 text-red-800">{String(overview.error)}</div>

  const overviewData = overview.data!
  const skills = topSkills.data?.skills ?? []
  const locationRows = locations.data?.locations ?? []
  const postings = recentPostings.data?.postings ?? []

  return (
    <div className="space-y-8">
      <div>
        <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground mb-2">01 — Overview</div>
        <h1 className="text-5xl leading-none">Market Overview</h1>
        <p className="mt-3 max-w-xl text-muted-foreground">
          Headline demand, the skills everyone is hiring for, and where they are hiring from.
        </p>
        {(selectedSkills.length > 0 || selectedLocations.length > 0) && (
          <p className="mt-2 text-sm text-muted-foreground">
            Filtered: {[selectedSkills.join(", "), selectedLocations.join(", ")].filter(Boolean).join(" · ")}
          </p>
        )}
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Metric label="Total Job Openings (last 24h)" value={overviewData.total_openings} />
        <Metric label="Unique Technologies (last 24h)" value={overviewData.unique_skills} />
        <Metric label="Companies Hiring (last 24h)" value={overviewData.companies} />
        <Metric label="Locations (last 24h)" value={overviewData.locations} />
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

      <Card className="rounded-3xl">
        <CardContent className="pt-6">
          <h2 className="text-2xl mb-1">Recent Job Postings</h2>
          <p className="text-sm text-muted-foreground mb-4">
            The latest openings — click Apply Now to open the posting.
          </p>
          {recentPostings.isLoading ? (
            <div className="py-6 text-muted-foreground">Loading postings…</div>
          ) : recentPostings.error ? (
            <div className="py-6 text-red-800">{String(recentPostings.error)}</div>
          ) : postings.length === 0 ? (
            <div className="py-6 text-muted-foreground">No recent postings found.</div>
          ) : (
            <div className="overflow-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="text-left text-muted-foreground border-b border-border">
                    <th className="py-2 pr-4 font-medium">Title</th>
                    <th className="py-2 pr-4 font-medium">Company</th>
                    <th className="py-2 pr-4 font-medium">Location</th>
                    <th className="py-2 pr-4 font-medium">Posted</th>
                    <th className="py-2 pr-4 font-medium">Skills</th>
                    <th className="py-2 font-medium">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {postings.map((posting) => (
                    <tr key={posting.job_id} className="border-b border-border last:border-0 align-top">
                      <td className="py-3 pr-4 font-medium">{posting.title ?? "Untitled role"}</td>
                      <td className="py-3 pr-4">{posting.company ?? "—"}</td>
                      <td className="py-3 pr-4">{posting.location ?? "—"}</td>
                      <td className="py-3 pr-4 whitespace-nowrap">{posting.posted_at ? posting.posted_at.slice(0, 10) : "—"}</td>
                      <td className="py-3 pr-4 max-w-56">
                        {posting.skills.length > 0 ? posting.skills.join(", ") : "—"}
                      </td>
                      <td className="py-3">
                        {posting.url ? (
                          <Button asChild className="rounded-full" size="sm">
                            <a href={posting.url} target="_blank" rel="noreferrer">
                              Apply Now
                            </a>
                          </Button>
                        ) : (
                          <Button className="rounded-full" size="sm" disabled>
                            Apply Now
                          </Button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}