import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import Plot from "react-plotly.js"
import { api } from "@/lib/api"
import { queryKeys } from "@/lib/queryKeys"
import { Card, CardContent } from "@/components/ui/card"

type SubTab = "survival" | "anomalies" | "pmi" | "communities"

export default function DemandScience() {
  const [sub, setSub] = useState<SubTab>("survival")
  const science = useQuery({ queryKey: queryKeys.demandScience, queryFn: api.demandScience })

  if (science.isLoading) return <div className="p-6">Loading…</div>
  if (science.error) return <div className="p-6 text-red-600">{String(science.error)}</div>
  const data = science.data!

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">Demand Science</h1>
      <div className="flex gap-2">
        {(
          [
            ["survival", "Survival (time-to-fill)"],
            ["anomalies", "Anomalies"],
            ["pmi", "Skill associations"],
            ["communities", "Skill communities"],
          ] as [SubTab, string][]
        ).map(([id, label]) => (
          <button
            key={id}
            className={`px-3 py-1 rounded border ${sub === id ? "bg-slate-900 text-white" : "bg-white"}`}
            onClick={() => setSub(id)}
          >
            {label}
          </button>
        ))}
      </div>

      {sub === "survival" && (
        <Card>
          <CardContent className="pt-6">
            <h2 className="font-semibold mb-2">Kaplan–Meier survival curve</h2>
            {data.survival_overall.length === 0 ? (
              <p className="text-gray-500">Not enough data for survival analysis.</p>
            ) : (
              <Plot
                data={[
                  {
                    type: "scatter",
                    mode: "lines+markers",
                    name: "Overall",
                    x: data.survival_overall.map((point) => point.time),
                    y: data.survival_overall.map((point) => point.survival),
                  },
                ]}
                layout={{ height: 400, xaxis: { title: "Days since first seen" }, yaxis: { title: "Survival probability" } }}
                style={{ width: "100%" }}
              />
            )}
          </CardContent>
        </Card>
      )}

      {sub === "anomalies" && (
        <Card>
          <CardContent className="pt-6">
            <h2 className="font-semibold mb-2">Anomalous postings</h2>
            {data.anomalies.length === 0 ? (
              <p className="text-gray-500">No anomalies detected.</p>
            ) : (
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-500 border-b">
                    <th className="py-2 pr-4">Title</th>
                    <th className="py-2 pr-4">Skill</th>
                    <th className="py-2">Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {data.anomalies.map((anomaly, index) => (
                    <tr key={index} className="border-b last:border-0">
                      <td className="py-2 pr-4">{anomaly["Job Title"]}</td>
                      <td className="py-2 pr-4">{anomaly["Tech Skill"]}</td>
                      <td className="py-2">{anomaly.reason ?? ""}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </CardContent>
        </Card>
      )}

      {sub === "pmi" && (
        <Card>
          <CardContent className="pt-6">
            <h2 className="font-semibold mb-2">Skill pairs by PMI</h2>
            {data.pmi_pairs.length === 0 ? (
              <p className="text-gray-500">Not enough data for association mining.</p>
            ) : (
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-500 border-b">
                    <th className="py-2 pr-4">Skill A</th>
                    <th className="py-2 pr-4">Skill B</th>
                    <th className="py-2 pr-4">Co-occurrence</th>
                    <th className="py-2">PMI</th>
                  </tr>
                </thead>
                <tbody>
                  {data.pmi_pairs.slice(0, 20).map((pair, index) => (
                    <tr key={index} className="border-b last:border-0">
                      <td className="py-2 pr-4">{pair.skill_a}</td>
                      <td className="py-2 pr-4">{pair.skill_b}</td>
                      <td className="py-2 pr-4">{pair.cooccurrence}</td>
                      <td className="py-2">{pair.pmi}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </CardContent>
        </Card>
      )}

      {sub === "communities" && (
        <Card>
          <CardContent className="pt-6">
            <h2 className="font-semibold mb-2">Skill communities (Louvain)</h2>
            {Object.keys(data.communities).length === 0 ? (
              <p className="text-gray-500">Not enough data for community detection.</p>
            ) : (
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-500 border-b">
                    <th className="py-2 pr-4">Skill</th>
                    <th className="py-2">Community</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(data.communities).map(([skill, community]) => (
                    <tr key={skill} className="border-b last:border-0">
                      <td className="py-2 pr-4">{skill}</td>
                      <td className="py-2">{community}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}