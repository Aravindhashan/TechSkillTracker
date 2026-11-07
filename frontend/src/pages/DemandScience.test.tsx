import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import DemandScience from "@/pages/DemandScience"
import { QueryProvider } from "@/providers/QueryProvider"

vi.mock("@/lib/api", () => ({
  api: {
    demandScience: () =>
      Promise.resolve({
        survival_overall: [{ time: 5, at_risk: 10, events: 2, survival: 0.8 }],
        survival_by_skill: {},
        cox: {},
        anomalies: [],
        pmi_pairs: [{ skill_a: "Python", skill_b: "PostgreSQL", cooccurrence: 2, pmi: 1.2 }],
        communities: { Python: 0, PostgreSQL: 0 },
        relatedness: { Python: [["PostgreSQL", 0.9]] },
      }),
  },
}))

describe("DemandScience end-to-end", () => {
  it("renders all five sub-tabs", async () => {
    render(
      <QueryProvider>
        <DemandScience />
      </QueryProvider>,
    )
    expect(await screen.findByRole("heading", { name: "Demand Science" })).toBeTruthy()
    expect(screen.getByText(/Survival/)).toBeTruthy()
    expect(screen.getByText(/Anomalies/)).toBeTruthy()
    expect(screen.getByText(/Skill associations/)).toBeTruthy()
    expect(screen.getByText(/Skill communities/)).toBeTruthy()
    expect(screen.getByText(/Relatedness/)).toBeTruthy()
  })

  it("shows survival curve by default", async () => {
    render(
      <QueryProvider>
        <DemandScience />
      </QueryProvider>,
    )
    expect(await screen.findByText(/Kaplan/)).toBeTruthy()
  })

  it("shows relatedness skill selector and similarity", async () => {
    render(
      <QueryProvider>
        <DemandScience />
      </QueryProvider>,
    )
    fireEvent.click(screen.getByText(/Relatedness/))
    expect(await screen.findByText(/Word2Vec skill relatedness/)).toBeTruthy()
    expect(await screen.findByText(/PostgreSQL/)).toBeTruthy()
    expect(await screen.findByText(/0.900/)).toBeTruthy()
  })
})