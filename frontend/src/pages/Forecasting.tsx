import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import Plot from 'react-plotly.js'
import { api } from '../lib/api'
import { queryKeys } from '../lib/queryKeys'

const ENGINES = ['auto', 'gradient_boosting', 'sarimax', 'prophet', 'croston', 'exponential_smoothing', 'linear']

export default function Forecasting() {
  const [skill, setSkill] = useState('Python')
  const [months, setMonths] = useState(12)
  const [model, setModel] = useState('auto')
  const [submitted, setSubmitted] = useState(false)

  const top = useQuery({ queryKey: queryKeys.topSkills(20), queryFn: () => api.topSkills(20) })
  const skills = (top.data?.skills ?? []).map((s) => s.skill)

  const forecast = useQuery({
    queryKey: queryKeys.forecast(skill, months, model),
    queryFn: () => api.forecast(skill, months, model),
    enabled: submitted && !!skill,
  })

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">Demand Forecasting</h1>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 bg-white rounded-lg shadow p-4">
        <div>
          <label className="text-sm text-gray-500">Skill</label>
          <select
            className="mt-1 w-full border rounded px-2 py-1"
            value={skill}
            onChange={(e) => setSkill(e.target.value)}
          >
            {skills.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-sm text-gray-500">Months ahead</label>
          <input
            type="number" min={1} max={36}
            className="mt-1 w-full border rounded px-2 py-1"
            value={months}
            onChange={(e) => setMonths(Number(e.target.value))}
          />
        </div>
        <div>
          <label className="text-sm text-gray-500">Engine</label>
          <select
            className="mt-1 w-full border rounded px-2 py-1"
            value={model}
            onChange={(e) => setModel(e.target.value)}
          >
            {ENGINES.map((e) => <option key={e} value={e}>{e}</option>)}
          </select>
        </div>
        <div className="flex items-end">
          <button
            className="bg-blue-600 text-white px-4 py-2 rounded w-full disabled:opacity-50"
            disabled={!skill}
            onClick={() => setSubmitted(true)}
          >
            Generate Forecast
          </button>
        </div>
      </div>

      {forecast.isLoading && <div>Running predictive model…</div>}
      {forecast.error && <div className="text-red-600">{String(forecast.error)}</div>}
      {forecast.data && (
        <div className="space-y-4">
          <div className="bg-white rounded-lg shadow p-4">
            <h2 className="font-semibold">Demand Forecast for {forecast.data.skill}</h2>
            <p className="text-sm text-gray-500">Engine: {forecast.data.engine ?? '—'} · Selected by {forecast.data.selected_by ?? '—'}</p>
            <Plot
              data={[
                {
                  type: 'scatter',
                  mode: 'lines+markers',
                  name: 'Historical',
                  x: forecast.data.forecast.filter((p) => p.actual != null).map((p) => p.date),
                  y: forecast.data.forecast.filter((p) => p.actual != null).map((p) => p.actual),
                },
                {
                  type: 'scatter',
                  mode: 'lines+markers',
                  name: 'Forecast',
                  x: forecast.data.forecast.filter((p) => p.forecast != null).map((p) => p.date),
                  y: forecast.data.forecast.filter((p) => p.forecast != null).map((p) => p.forecast),
                },
              ]}
              layout={{ height: 450 }}
              style={{ width: '100%' }}
            />
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="font-semibold mb-2">Forecast Insights</h3>
            <ul className="list-disc pl-5 space-y-1">
              {forecast.data.insights.map((i, idx) => <li key={idx}>{i}</li>)}
            </ul>
          </div>
        </div>
      )}
    </div>
  )
}