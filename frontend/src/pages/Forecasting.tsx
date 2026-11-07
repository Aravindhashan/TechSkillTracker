import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import Plot from "react-plotly.js"
import { api } from "@/lib/api"
import { queryKeys } from "@/lib/queryKeys"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import type { ForecastEngine } from "@/types/api"

const ENGINES: ForecastEngine[] = [
  "auto",
  "gradient_boosting",
  "sarimax",
  "prophet",
  "croston",
  "exponential_smoothing",
  "linear",
]

export default function Forecasting() {
  const [skill, setSkill] = useState("Python")
  const [months, setMonths] = useState(12)
  const [model, setModel] = useState<ForecastEngine>("auto")
  const [submitted, setSubmitted] = useState(false)

  const top = useQuery({ queryKey: queryKeys.topSkills(20), queryFn: () => api.topSkills(20) })
  const skills = (top.data?.skills ?? []).map((entry) => entry.skill)

  const forecast = useQuery({
    queryKey: queryKeys.forecast(skill, months, model),
    queryFn: () => api.forecast(skill, months, model),
    enabled: submitted && !!skill,
  })

  const points = forecast.data?.forecast ?? []
  const historical = points.filter((point) => point.actual != null)
  const forecastPoints = points.filter((point) => point.forecast != null)
  const ciPoints = points.filter((point) => point.upper != null && point.lower != null)

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">Demand Forecasting</h1>
      <Card>
        <CardContent className="pt-6 grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="text-sm text-gray-500">Skill</label>
            <select
              className="mt-1 w-full border rounded px-2 py-1"
              value={skill}
              onChange={(event) => setSkill(event.target.value)}
            >
              {skills.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-sm text-gray-500">Months ahead</label>
            <input
              type="number"
              min={1}
              max={36}
              className="mt-1 w-full border rounded px-2 py-1"
              value={months}
              onChange={(event) => setMonths(Number(event.target.value))}
            />
          </div>
          <div>
            <label className="text-sm text-gray-500">Engine</label>
            <select
              className="mt-1 w-full border rounded px-2 py-1"
              value={model}
              onChange={(event) => setModel(event.target.value as ForecastEngine)}
            >
              {ENGINES.map((engine) => (
                <option key={engine} value={engine}>
                  {engine}
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-end">
            <Button className="w-full" disabled={!skill} onClick={() => setSubmitted(true)}>
              Generate Forecast
            </Button>
          </div>
        </CardContent>
      </Card>

      {forecast.isLoading && <div>Running predictive model…</div>}
      {forecast.error && <div className="text-red-600">{String(forecast.error)}</div>}
      {forecast.data && (
        <div className="space-y-4">
          <Card>
            <CardContent className="pt-6">
              <h2 className="font-semibold">Demand Forecast for {forecast.data.skill}</h2>
              <p className="text-sm text-gray-500">
                Engine: {forecast.data.engine ?? "—"} · Selected by {forecast.data.selected_by ?? "—"}
              </p>
              <Plot
                data={[
                  {
                    type: "scatter",
                    mode: "lines+markers" as const,
                    name: "Historical",
                    x: historical.map((point) => point.date),
                    y: historical.map((point) => point.actual),
                  },
                  {
                    type: "scatter",
                    mode: "lines+markers" as const,
                    name: "Forecast",
                    x: forecastPoints.map((point) => point.date),
                    y: forecastPoints.map((point) => point.forecast),
                  },
                  ...(ciPoints.length > 0
                    ? [
                        {
                          type: "scatter" as const,
                          mode: "lines" as const,
                          name: "Upper bound",
                          x: ciPoints.map((point) => point.date),
                          y: ciPoints.map((point) => point.upper),
                          line: { width: 0 },
                          showlegend: false,
                          hoverinfo: "skip" as const,
                        },
                        {
                          type: "scatter" as const,
                          mode: "lines" as const,
                          name: "Confidence interval",
                          x: ciPoints.map((point) => point.date),
                          y: ciPoints.map((point) => point.lower),
                          fill: "tonexty" as const,
                          line: { width: 0 },
                          fillcolor: "rgba(255, 165, 0, 0.2)",
                        },
                      ]
                    : []),
                ]}
                layout={{ height: 450 }}
                style={{ width: "100%" }}
              />
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <h3 className="font-semibold mb-2">Forecast Insights</h3>
              <ul className="list-disc pl-5 space-y-1">
                {forecast.data.insights.map((insight, index) => (
                  <li key={index}>{insight}</li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}