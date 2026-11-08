import { useEffect, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import Plot from "react-plotly.js"
import { api } from "@/lib/api"
import { queryKeys } from "@/lib/queryKeys"
import { useFilters } from "@/context/FilterContext"
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

const INK = "#1A1815"
const GRID = "#E4DCC8"

export default function Forecasting() {
  const { selectedSkills, selectedLocations } = useFilters()
  const locationParam = selectedLocations.join(",")
  const [skill, setSkill] = useState(selectedSkills[0] ?? "Python")
  const [months, setMonths] = useState(12)
  const [model, setModel] = useState<ForecastEngine>("auto")

  useEffect(() => {
    if (selectedSkills[0]) setSkill(selectedSkills[0])
  }, [selectedSkills])

  const top = useQuery({
    queryKey: queryKeys.topSkills(50, "", locationParam),
    queryFn: () => api.topSkills(50, { locations: selectedLocations }),
  })
  const skills = (top.data?.skills ?? []).map((entry) => entry.skill)

  const forecast = useQuery({
    queryKey: queryKeys.forecast(skill, months, model),
    queryFn: () => api.forecast(skill, months, model),
    enabled: !!skill.trim(),
  })

  const points = forecast.data?.forecast ?? []
  const historical = points.filter((point) => point.actual != null)
  const forecastPoints = points.filter((point) => point.forecast != null)
  const ciPoints = points.filter((point) => point.upper != null && point.lower != null)

  return (
    <div className="space-y-8">
      <div>
        <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground mb-2">03 — Forecasting</div>
        <h1 className="text-5xl leading-none">Demand Forecasting</h1>
        {(selectedSkills.length > 0 || selectedLocations.length > 0) && (
          <p className="mt-2 text-sm text-muted-foreground">
            Filtered: {[selectedSkills.join(", "), selectedLocations.join(", ")].filter(Boolean).join(" · ")}
          </p>
        )}
      </div>
      <Card className="rounded-3xl">
        <CardContent className="pt-6 grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Skill</label>
            <input
              list="forecast-skills"
              className="mt-2 w-full rounded-full border border-border bg-card px-4 py-2 text-sm focus:outline-none focus:border-foreground"
              value={skill}
              onChange={(event) => setSkill(event.target.value)}
              placeholder="Type any skill, e.g. Python"
            />
            <datalist id="forecast-skills">
              {skills.map((name) => (
                <option key={name} value={name} />
              ))}
            </datalist>
          </div>
          <div>
            <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Months ahead</label>
            <input
              type="number"
              min={1}
              max={36}
              className="mt-2 w-full rounded-full border border-border bg-card px-4 py-2 text-sm focus:outline-none focus:border-foreground"
              value={months}
              onChange={(event) => setMonths(Number(event.target.value))}
            />
          </div>
          <div>
            <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Engine</label>
            <select
              className="mt-2 w-full rounded-full border border-border bg-card px-4 py-2 text-sm focus:outline-none focus:border-foreground"
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
            <Button className="w-full rounded-full" disabled={!skill.trim()}>
              Generate Forecast
            </Button>
          </div>
        </CardContent>
      </Card>

      {forecast.isLoading && <div className="py-10">Running predictive model…</div>}
      {forecast.error && <div className="py-10 text-red-800">{String(forecast.error)}</div>}
      {forecast.data && (
        <div className="space-y-6">
          <Card className="rounded-3xl">
            <CardContent className="pt-6">
              <h2 className="text-2xl">Demand Forecast for {forecast.data.skill}</h2>
              <p className="mt-1 text-sm text-muted-foreground">
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
                    line: { color: INK },
                    marker: { color: INK },
                  },
                  {
                    type: "scatter",
                    mode: "lines+markers" as const,
                    name: "Forecast",
                    x: forecastPoints.map((point) => point.date),
                    y: forecastPoints.map((point) => point.forecast),
                    line: { color: INK, dash: "dash" },
                    marker: { color: INK },
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
                          fillcolor: "rgba(26,24,21,0.12)",
                        },
                      ]
                    : []),
                ]}
                layout={{
                  height: 450,
                  paper_bgcolor: "rgba(0,0,0,0)",
                  plot_bgcolor: "rgba(0,0,0,0)",
                  font: { family: "Inter, sans-serif", color: INK },
                  xaxis: { gridcolor: GRID },
                  yaxis: { gridcolor: GRID },
                }}
                style={{ width: "100%" }}
              />
            </CardContent>
          </Card>
          <Card className="rounded-3xl">
            <CardContent className="pt-6">
              <h3 className="text-xl mb-2">Forecast Insights</h3>
              <ul className="list-disc pl-5 space-y-1 text-sm">
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