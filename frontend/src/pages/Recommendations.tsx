import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { queryKeys } from '../lib/queryKeys'

type Mode = 'complementary' | 'role' | 'learning-path'

export default function Recommendations() {
  const [mode, setMode] = useState<Mode>('complementary')
  const [skill, setSkill] = useState('')
  const [role, setRole] = useState('')
  const [currentSkills, setCurrentSkills] = useState('')
  const [targetRole, setTargetRole] = useState('')
  const [submitted, setSubmitted] = useState(false)

  const key = `${skill}|${role}|${currentSkills}|${targetRole}`
  const rec = useQuery({
    queryKey: queryKeys.recommendations(mode, key),
    queryFn: () => {
      if (mode === 'complementary') return api.recommendations({ mode, skill, top_n: 10 })
      if (mode === 'role') return api.recommendations({ mode, role, top_n: 10 })
      return api.recommendations({
        mode,
        current_skills: currentSkills.split(',').map((s) => s.trim()).filter(Boolean),
        target_role: targetRole,
      })
    },
    enabled: submitted,
  })

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">Skill Recommendations</h1>
      <div className="flex gap-2">
        {(['complementary', 'role', 'learning-path'] as Mode[]).map((m) => (
          <button
            key={m}
            className={`px-3 py-1 rounded border ${mode === m ? 'bg-slate-900 text-white' : 'bg-white'}`}
            onClick={() => { setMode(m); setSubmitted(false) }}
          >
            {m === 'complementary' ? 'Complementary Skills' : m === 'role' ? 'Job Role Analysis' : 'Learning Roadmap'}
          </button>
        ))}
      </div>

      <div className="bg-white rounded-lg shadow p-4 space-y-3">
        {mode === 'complementary' && (
          <div>
            <label className="text-sm text-gray-500">Current skill</label>
            <input className="mt-1 w-full border rounded px-2 py-1" value={skill} onChange={(e) => setSkill(e.target.value)} placeholder="e.g. Python" />
          </div>
        )}
        {mode === 'role' && (
          <div>
            <label className="text-sm text-gray-500">Job role</label>
            <input className="mt-1 w-full border rounded px-2 py-1" value={role} onChange={(e) => setRole(e.target.value)} placeholder="e.g. Data Scientist" />
          </div>
        )}
        {mode === 'learning-path' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-sm text-gray-500">Current skills (comma-separated)</label>
              <input className="mt-1 w-full border rounded px-2 py-1" value={currentSkills} onChange={(e) => setCurrentSkills(e.target.value)} placeholder="Python, SQL" />
            </div>
            <div>
              <label className="text-sm text-gray-500">Target role</label>
              <input className="mt-1 w-full border rounded px-2 py-1" value={targetRole} onChange={(e) => setTargetRole(e.target.value)} placeholder="Data Scientist" />
            </div>
          </div>
        )}
        <button className="bg-blue-600 text-white px-4 py-2 rounded" onClick={() => setSubmitted(true)}>
          Get Recommendations
        </button>
      </div>

      {rec.isLoading && <div>Loading…</div>}
      {rec.error && <div className="text-red-600">{String(rec.error)}</div>}
      {rec.data && (
        <div className="bg-white rounded-lg shadow p-4">
          <p className="text-sm text-gray-500 mb-3">{rec.data.status}</p>
          {rec.data.results.length === 0 ? (
            <p className="text-gray-500">No recommendations found.</p>
          ) : (
            <ol className="list-decimal pl-5 space-y-1">
              {rec.data.results.map((r, i) => {
                const item = r as Record<string, unknown>
                return <li key={i}>{String(item.skill ?? item.name ?? JSON.stringify(item))}</li>
              })}
            </ol>
          )}
        </div>
      )}
    </div>
  )
}