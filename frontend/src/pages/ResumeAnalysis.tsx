import { useState } from "react"
import { useMutation } from "@tanstack/react-query"
import { api } from "@/lib/api"
import Metric from "@/components/Metric"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"

interface MissingSkill {
  skill: string
  demand: number
  percentage: number
  resources: Record<string, { url: string; icon?: string; description?: string }>
}

interface ResumeResult {
  resume_skills?: string[]
  matched_skills?: string[]
  missing_skills?: MissingSkill[]
  match_percentage?: number
  weighted_match_percentage?: number
  total_postings?: number
  total_demand_skills?: number
  experience_years?: number | null
  education?: string[]
  filename?: string
  resume_id?: string | null
}

export default function ResumeAnalysis() {
  const [file, setFile] = useState<File | null>(null)
  const mutation = useMutation({
    mutationFn: (selected: File) => api.resumeAnalyze(selected) as Promise<ResumeResult>,
  })

  return (
    <div className="space-y-8">
      <div>
        <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground mb-2">05 — Resume</div>
        <h1 className="text-5xl leading-none">Resume Skill-Gap Analysis</h1>
        <p className="mt-3 max-w-xl text-muted-foreground">
          Upload your resume (PDF or DOCX) to see how well it matches live demand.
        </p>
      </div>
      <Card className="rounded-3xl">
        <CardContent className="pt-6 flex flex-wrap items-center gap-4">
          <input type="file" accept=".pdf,.docx" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
          <Button className="rounded-full" disabled={!file || mutation.isPending} onClick={() => file && mutation.mutate(file)}>
            {mutation.isPending ? "Analyzing…" : "Analyze Resume"}
          </Button>
          {mutation.error && <div className="text-red-800 text-sm">{String(mutation.error)}</div>}
        </CardContent>
      </Card>

      {mutation.data && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Metric label="Match %" value={`${mutation.data.match_percentage ?? 0}%`} />
            <Metric label="Weighted match" value={`${mutation.data.weighted_match_percentage ?? 0}%`} />
            <Metric label="Skills you have" value={mutation.data.resume_skills?.length ?? 0} />
            <Metric label="In-demand skills" value={mutation.data.total_demand_skills ?? 0} />
          </div>

          {mutation.data.matched_skills && mutation.data.matched_skills.length > 0 && (
            <Card className="rounded-3xl">
              <CardContent className="pt-6">
                <h2 className="text-2xl mb-2">Skills you already cover</h2>
                <p>{mutation.data.matched_skills.join(", ")}</p>
              </CardContent>
            </Card>
          )}

          {mutation.data.missing_skills && mutation.data.missing_skills.length > 0 && (
            <Card className="rounded-3xl">
              <CardContent className="pt-6">
                <h2 className="text-2xl mb-3">Top missing skills</h2>
                <div className="overflow-auto">
                  <table className="min-w-full text-sm">
                    <thead>
                      <tr className="text-left text-muted-foreground border-b border-border">
                        <th className="py-2 pr-4 font-medium">Skill</th>
                        <th className="py-2 pr-4 font-medium">Demand</th>
                        <th className="py-2 pr-4 font-medium">% of postings</th>
                        <th className="py-2 font-medium">Resources</th>
                      </tr>
                    </thead>
                    <tbody>
                      {mutation.data.missing_skills.slice(0, 15).map((missing) => (
                        <tr key={missing.skill} className="border-b border-border last:border-0">
                          <td className="py-2 pr-4 font-medium">{missing.skill}</td>
                          <td className="py-2 pr-4">{missing.demand}</td>
                          <td className="py-2 pr-4">{missing.percentage}%</td>
                          <td className="py-2">
                            <div className="flex flex-wrap gap-3">
                              {Object.entries(missing.resources ?? {}).slice(0, 3).map(([name, info]) => (
                                <a
                                  key={name}
                                  href={info.url}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="underline underline-offset-4 decoration-border hover:decoration-foreground"
                                >
                                  {name}
                                </a>
                              ))}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  )
}