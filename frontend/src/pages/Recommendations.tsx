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
  const [submitted, setSubmitted] = useState(false)

  const queryKey = `${skill}|${role}|${currentSkills}|${targetRole}`
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
    enabled: submitted,
  })

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">Skill Recommendations</h1>
      <div className="flex gap-2">
        {(["complementary", "role", "learning-path"] as Mode[]).map((candidate) => (
          <button
            key={candidate}
            className={`px-3 py-1 rounded border ${mode === candidate ? "bg-slate-900 text-white" : "bg-white"}`}
            onClick={() => {
              setMode(candidate)
              setSubmitted(false)
            }}
          >
            {MODE_LABELS[candidate]}
          </button>
        ))}
      </div>

      <Card>
        <CardContent className="pt-6 space-y-3">
          {mode === "complementary" && (
            <div>
              <label className="text-sm text-gray-500">Current skill</label>
              <input
                className="mt-1 w-full border rounded px-2 py-1"
                value={skill}
                onChange={(event) => setSkill(event.target.value)}
                placeholder="e.g. Python"
              />
            </div>
          )}
          {mode === "role" && (
            <div>
              <label className="text-sm text-gray-500">Job role</label>
              <input
                className="mt-1 w-full border rounded px-2 py-1"
                value={role}
                onChange={(event) => setRole(event.target.value)}
                placeholder="e.g. Data Scientist"
              />
            </div>
          )}
          {mode === "learning-path" && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-sm text-gray-500">Current skills (comma-separated)</label>
                <input
                  className="mt-1 w-full border rounded px-2 py-1"
                  value={currentSkills}
                  onChange={(event) => setCurrentSkills(event.target.value)}
                  placeholder="Python, SQL"
                />
              </div>
              <div>
                <label className="text-sm text-gray-500">Target role</label>
                <input
                  className="mt-1 w-full border rounded px-2 py-1"
                  value={targetRole}
                  onChange={(event) => setTargetRole(event.target.value)}
                  placeholder="Data Scientist"
                />
              </div>
            </div>
          )}
          <Button onClick={() => setSubmitted(true)}>Get Recommendations</Button>
        </CardContent>
      </Card>

      {recommendations.isLoading && <div>Loading…</div>}
      {recommendations.error && <div className="text-red-600">{String(recommendations.error)}</div>}
      {recommendations.data && (
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-gray-500 mb-3">{recommendations.data.status}</p>
            {recommendations.data.results.length === 0 ? (
              <p className="text-gray-500">No recommendations found.</p>
            ) : (
              <ol className="list-decimal pl-5 space-y-1">
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