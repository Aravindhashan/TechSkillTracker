import { useState } from "react"
import { FilterProvider, useFilters } from "@/context/FilterContext"
import MarketOverview from "@/pages/MarketOverview"
import DataVisualization from "@/pages/DataVisualization"
import Forecasting from "@/pages/Forecasting"
import Recommendations from "@/pages/Recommendations"
import ResumeAnalysis from "@/pages/ResumeAnalysis"
import DemandScience from "@/pages/DemandScience"
import SearchRoi from "@/pages/SearchRoi"
import FairnessAudit from "@/pages/FairnessAudit"

const TABS = [
  { id: "market", label: "Overview", component: MarketOverview },
  { id: "viz", label: "Data Viz", component: DataVisualization },
  { id: "forecast", label: "Forecasting", component: Forecasting },
  { id: "recs", label: "Recommendations", component: Recommendations },
  { id: "resume", label: "Resume", component: ResumeAnalysis },
  { id: "science", label: "Science", component: DemandScience },
  { id: "search", label: "Search & ROI", component: SearchRoi },
  { id: "fairness", label: "Fairness", component: FairnessAudit },
]

function Shell() {
  const [active, setActive] = useState("market")
  const ActiveComponent = TABS.find((tab) => tab.id === active)?.component ?? MarketOverview
  const { selectedSkills, setSelectedSkills } = useFilters()

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-10 border-b border-border bg-background/90 backdrop-blur">
        <div className="mx-auto max-w-6xl px-5">
          <div className="flex items-baseline justify-between py-4">
            <div className="font-display text-2xl leading-none">
              Tech Skill Tracker
            </div>
            <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
              Live demand
            </div>
          </div>
          <nav className="flex gap-1.5 overflow-x-auto pb-3">
            {TABS.map((tab, index) => (
              <button
                key={tab.id}
                onClick={() => setActive(tab.id)}
                className={`whitespace-nowrap rounded-full px-4 py-1.5 text-sm transition ${
                  active === tab.id
                    ? "bg-primary text-primary-foreground"
                    : "border border-border bg-card hover:border-foreground/40"
                }`}
              >
                <span className="mr-1.5 text-xs opacity-60 font-display">
                  {String(index + 1).padStart(2, "0")}
                </span>
                {tab.label}
              </button>
            ))}
          </nav>
          <div className="flex items-center gap-3 pb-4">
            <span className="text-sm text-muted-foreground whitespace-nowrap">Skill filter</span>
            <input
              className="w-full max-w-md rounded-full border border-border bg-card px-4 py-1.5 text-sm placeholder:text-muted-foreground/70 focus:outline-none focus:border-foreground"
              placeholder="comma-separated skills"
              value={selectedSkills.join(", ")}
              onChange={(event) =>
                setSelectedSkills(
                  event.target.value
                    .split(",")
                    .map((skill) => skill.trim())
                    .filter(Boolean),
                )
              }
            />
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-5 py-8">
        <ActiveComponent />
      </main>
      <footer className="border-t border-border">
        <div className="mx-auto max-w-6xl px-5 py-6 text-xs text-muted-foreground flex justify-between">
          <span className="font-display text-base text-foreground">Tech Skill Tracker</span>
          <span>Demand-only — no salary data</span>
        </div>
      </footer>
    </div>
  )
}

export default function App() {
  return (
    <FilterProvider>
      <Shell />
    </FilterProvider>
  )
}