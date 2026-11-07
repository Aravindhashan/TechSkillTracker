import { createContext, useContext, useState, type ReactNode } from "react"

interface FilterState {
  selectedSkills: string[]
  selectedLocations: string[]
  setSelectedSkills: (v: string[]) => void
  setSelectedLocations: (v: string[]) => void
}

const FilterContext = createContext<FilterState | null>(null)

export function FilterProvider({ children }: { children: ReactNode }) {
  const [selectedSkills, setSelectedSkills] = useState<string[]>([])
  const [selectedLocations, setSelectedLocations] = useState<string[]>([])
  return (
    <FilterContext.Provider
      value={{ selectedSkills, selectedLocations, setSelectedSkills, setSelectedLocations }}
    >
      {children}
    </FilterContext.Provider>
  )
}

export function useFilters() {
  const ctx = useContext(FilterContext)
  if (!ctx) throw new Error("useFilters must be used within FilterProvider")
  return ctx
}