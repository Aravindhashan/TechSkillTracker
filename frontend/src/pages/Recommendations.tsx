import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { queryKeys } from "@/lib/queryKeys"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"

type Mode = "complementary" | "role" | "learning-path"

const MODE_LABELS: Record<Mode, string> = {
  complementary: "Complementary Skills",
  role: "Job Role Analysis",
  "learning-path": "Learning Roadmap",
}

export default function Recommendations() {
  const [mode, setMode] = useState<Mode>("complementary")
  const [skill, setSkill] = useState("")
  const [role, setRole] = useState("")
  const [currentSkills, setCurrentSkills] = useState("")
  const [targetRole, setTargetRole] = useState("")

  const queryKey = `${skill}|${role}|${currentSkills}|${targetRole}`
  const canFetch =
    (mode === "complementary" && !!skill.trim()) ||
    (mode === "role" && !!role.trim()) ||
    (mode === "learning-path" && !!targetRole.trim())
  const recommendations = useQuery({
    queryKey: queryKeys.recommendations(mode, queryKey),
    queryFn: () => {
      if (mode === "complementary") return api.recommendations({ mode, skill, top_n: 10 })
      if (mode === "role") return api.recommendations({ mode, role, top_n: 10 })
      return api.recommendations({
        mode,
        current_skills: currentSkills.split(",").map((entry) => entry.trim()).filter(Boolean),
        target_role: targetRole,
      })
    },
    enabled: canFetch,
  })

  return (
    <div className="space-y-8">
      <div>
        <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground mb-2">04 — Recommendations</div>
        <h1 className="text-5xl leading-none">Skill Recommendations</h1>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {(["complementary", "role", "learning-path"] as Mode[]).map((candidate) => (
          <button
            key={candidate}
            className={`rounded-full px-4 py-1.5 text-sm transition ${
              mode === candidate ? "bg-primary text-primary-foreground" : "border border-border bg-card hover:border-foreground/40"
            }`}
            onClick={() => {
              setMode(candidate)
            }}
          >
            {MODE_LABELS[candidate]}
          </button>
        ))}
      </div>

      <Card className="rounded-3xl">
        <CardContent className="pt-6 space-y-4">
          {mode === "complementary" && (
            <div>
              <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Current skill</label>
              <input
                className="mt-2 w-full rounded-full border border-border bg-card px-4 py-2 text-sm focus:outline-none focus:border-foreground"
                value={skill}
                onChange={(event) => setSkill(event.target.value)}
                placeholder="e.g. Python"
              />
            </div>
          )}
          {mode === "role" && (
            <div>
              <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Job role</label>
              <input
                className="mt-2 w-full rounded-full border border-border bg-card px-4 py-2 text-sm focus:outline-none focus:border-foreground"
                value={role}
                onChange={(event) => setRole(event.target.value)}
                placeholder="e.g. Data Scientist"
              />
            </div>
          )}
          {mode === "learning-path" && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Current skills (comma-separated)</label>
                <input
                  className="mt-2 w-full rounded-full border border-border bg-card px-4 py-2 text-sm focus:outline-none focus:border-foreground"
                  value={currentSkills}
                  onChange={(event) => setCurrentSkills(event.target.value)}
                  placeholder="Python, SQL"
                />
              </div>
              <div>
                <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Target role</label>
                <input
                  className="mt-2 w-full rounded-full border border-border bg-card px-4 py-2 text-sm focus:outline-none focus:border-foreground"
                  value={targetRole}
                  onChange={(event) => setTargetRole(event.target.value)}
                  placeholder="Data Scientist"
                />
              </div>
            </div>
          )}
          <Button className="rounded-full" disabled={!canFetch}>
            Get Recommendations
          </Button>
        </CardContent>
      </Card>

      {recommendations.isLoading && <div className="py-10">Loading…</div>}
      {recommendations.error && <div className="py-10 text-red-800">{String(recommendations.error)}</div>}
      {recommendations.data && (
        <Card className="rounded-3xl">
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground mb-3">{recommendations.data.status}</p>
            {recommendations.data.results.length === 0 ? (
              <p className="text-muted-foreground">No recommendations found.</p>
            ) : (
              <ol className="list-decimal pl-5 space-y-2">
                {recommendations.data.results.map((item, index) => {
                  const record = item as Record<string, unknown>
                  return <li key={index}>{String(record.skill ?? record.name ?? JSON.stringify(record))}</li>
                })}
              </ol>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}