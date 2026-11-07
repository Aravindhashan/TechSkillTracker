import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { api } from '../lib/api'

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
  const mutation = useMutation({ mutationFn: (f: File) => api.resumeAnalyze(f) as Promise<ResumeResult> })

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">Resume Skill-Gap Analysis</h1>
      <div className="bg-white rounded-lg shadow p-4 space-y-3">
        <input
          type="file"
          accept=".pdf,.docx"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
        <button
          className="bg-blue-600 text-white px-4 py-2 rounded disabled:opacity-50"
          disabled={!file || mutation.isPending}
          onClick={() => file && mutation.mutate(file)}
        >
          {mutation.isPending ? 'Analyzing…' : 'Analyze Resume'}
        </button>
        {mutation.error && <div className="text-red-600">{String(mutation.error)}</div>}
      </div>

      {mutation.data && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Metric label="Match %" value={`${mutation.data.match_percentage ?? 0}%`} />
            <Metric label="Weighted match" value={`${mutation.data.weighted_match_percentage ?? 0}%`} />
            <Metric label="Skills you have" value={mutation.data.resume_skills?.length ?? 0} />
            <Metric label="In-demand skills" value={mutation.data.total_demand_skills ?? 0} />
          </div>

          {mutation.data.matched_skills && mutation.data.matched_skills.length > 0 && (
            <div className="bg-white rounded-lg shadow p-4">
              <h2 className="font-semibold mb-2">Skills you already cover</h2>
              <p>{mutation.data.matched_skills.join(', ')}</p>
            </div>
          )}

          {mutation.data.missing_skills && mutation.data.missing_skills.length > 0 && (
            <div className="bg-white rounded-lg shadow p-4">
              <h2 className="font-semibold mb-2">Top missing skills</h2>
              <div className="overflow-auto">
                <table className="min-w-full text-sm">
                  <thead>
                    <tr className="text-left text-gray-500 border-b">
                      <th className="py-2 pr-4">Skill</th>
                      <th className="py-2 pr-4">Demand</th>
                      <th className="py-2 pr-4">% of postings</th>
                      <th className="py-2">Resources</th>
                    </tr>
                  </thead>
                  <tbody>
                    {mutation.data.missing_skills.slice(0, 15).map((m) => (
                      <tr key={m.skill} className="border-b last:border-0">
                        <td className="py-2 pr-4 font-medium">{m.skill}</td>
                        <td className="py-2 pr-4">{m.demand}</td>
                        <td className="py-2 pr-4">{m.percentage}%</td>
                        <td className="py-2">
                          <div className="flex flex-wrap gap-2">
                            {Object.entries(m.resources ?? {}).slice(0, 3).map(([name, info]) => (
                              <a key={name} href={info.url} target="_blank" rel="noreferrer" className="text-blue-600 underline">
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
            </div>
          )}
        </div>
      )}
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