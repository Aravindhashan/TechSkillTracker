import { useState } from 'react'
import { FilterProvider, useFilters } from './context/FilterContext'
import MarketOverview from './pages/MarketOverview'
import DataVisualization from './pages/DataVisualization'
import Forecasting from './pages/Forecasting'
import Recommendations from './pages/Recommendations'
import ResumeAnalysis from './pages/ResumeAnalysis'
import DemandScience from './pages/DemandScience'
import SearchRoi from './pages/SearchRoi'
import FairnessAudit from './pages/FairnessAudit'

const TABS = [
  { id: 'market', label: 'Market Overview', component: MarketOverview },
  { id: 'viz', label: 'Data Visualization', component: DataVisualization },
  { id: 'forecast', label: 'Demand Forecasting', component: Forecasting },
  { id: 'recs', label: 'Skill Recommendations', component: Recommendations },
  { id: 'resume', label: 'Resume Analysis', component: ResumeAnalysis },
  { id: 'science', label: 'Demand Science', component: DemandScience },
  { id: 'search', label: 'Search & ROI', component: SearchRoi },
  { id: 'fairness', label: 'Fairness Audit', component: FairnessAudit },
]

function Shell() {
  const [active, setActive] = useState('market')
  const ActiveComponent = TABS.find((t) => t.id === active)?.component ?? MarketOverview
  const { selectedSkills, setSelectedSkills } = useFilters()

  return (
    <div className="flex min-h-screen bg-gray-50">
      <aside className="w-64 bg-slate-900 text-white p-4 flex flex-col gap-4">
        <h1 className="text-lg font-bold">Tech Skill Tracker</h1>
        <nav className="flex flex-col gap-1">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setActive(t.id)}
              className={`text-left px-3 py-2 rounded-md text-sm transition ${
                active === t.id ? 'bg-slate-700 font-semibold' : 'hover:bg-slate-800'
              }`}
            >
              {t.label}
            </button>
          ))}
        </nav>
        <div className="mt-auto border-t border-slate-700 pt-4">
          <label className="text-xs text-slate-400">Skill filter</label>
          <input
            className="mt-1 w-full px-2 py-1 rounded bg-slate-800 text-sm border border-slate-700"
            placeholder="comma-separated skills"
            value={selectedSkills.join(', ')}
            onChange={(e) =>
              setSelectedSkills(
                e.target.value
                  .split(',')
                  .map((s) => s.trim())
                  .filter(Boolean),
              )
            }
          />
        </div>
      </aside>
      <main className="flex-1 overflow-auto">
        <ActiveComponent />
      </main>
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