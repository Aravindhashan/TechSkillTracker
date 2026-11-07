import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import Forecasting from "@/pages/Forecasting"
import { QueryProvider } from "@/providers/QueryProvider"
import { FilterProvider } from "@/context/FilterContext"

vi.mock("@/lib/api", () => ({
  api: {
    topSkills: () => Promise.resolve({ skills: [{ skill: "Python", count: 12 }] }),
    forecast: () =>
      Promise.resolve({
        skill: "Python",
        status: "success",
        message: null,
        engine: "Prophet",
        selected_by: "mape",
        mape_comparison: {},
        months_ahead: 12,
        forecast: [
          { date: "2026-11-01", actual: 5, forecast: null, lower: null, upper: null },
          { date: "2026-12-01", actual: null, forecast: 6, lower: 5, upper: 7 },
        ],
        insights: ["Stable demand"],
      }),
  },
}))

describe("Forecasting end-to-end", () => {
  it("renders free-text skill input with datalist suggestions", async () => {
    render(
      <QueryProvider>
        <FilterProvider>
          <Forecasting />
        </FilterProvider>
      </QueryProvider>,
    )
    expect(await screen.findByRole("heading", { name: "Demand Forecasting" })).toBeTruthy()
    expect(await screen.findByPlaceholderText(/Type any skill/)).toBeTruthy()
    expect(document.getElementById("forecast-skills")).toBeTruthy()
  })

  it("generates forecast with insights on submit", async () => {
    render(
      <QueryProvider>
        <FilterProvider>
          <Forecasting />
        </FilterProvider>
      </QueryProvider>,
    )
    fireEvent.click(await screen.findByText(/Generate Forecast/))
    expect(await screen.findByText(/Demand Forecast for Python/)).toBeTruthy()
    expect(await screen.findByText(/Stable demand/)).toBeTruthy()
  })
})