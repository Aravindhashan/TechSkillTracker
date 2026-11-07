import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import DataVisualization from "@/pages/DataVisualization"
import { QueryProvider } from "@/providers/QueryProvider"
import { FilterProvider } from "@/context/FilterContext"

vi.mock("@/lib/api", () => ({
  api: {
    demandTrends: () =>
      Promise.resolve([{ skill: "Python", month: "2026-11-01", count: 3 }]),
    skillPairs: () =>
      Promise.resolve([{ skill_a: "Python", skill_b: "PostgreSQL", count: 2 }]),
  },
}))

describe("DataVisualization end-to-end", () => {
  it("renders demand trends and co-occurrence sections", async () => {
    render(
      <QueryProvider>
        <FilterProvider>
          <DataVisualization />
        </FilterProvider>
      </QueryProvider>,
    )

    expect(await screen.findByRole("heading", { name: "Demand Trends" })).toBeTruthy()
    expect(await screen.findByText(/Technology Demand Trends Over Time/)).toBeTruthy()
    expect(await screen.findByText(/Skill Co-occurrence/)).toBeTruthy()
  })

  it("renders with header filters", async () => {
    render(
      <QueryProvider>
        <FilterProvider>
          <DataVisualization />
        </FilterProvider>
      </QueryProvider>,
    )
    await screen.findByRole("heading", { name: "Demand Trends" })
    expect(screen.getByRole("heading", { name: "Demand Trends" })).toBeTruthy()
  })
})