import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import FairnessAudit from "@/pages/FairnessAudit"
import { QueryProvider } from "@/providers/QueryProvider"

vi.mock("@/lib/api", () => ({
  api: {
    fairness: () =>
      Promise.resolve({
        overall: { postings: 5, skills: 3, months: 1 },
        by_location: [],
        by_remote: [],
        by_company_type: [],
        gaps: {
          location_share_range_pp: 0,
          remote_share_gap_pp: 0,
          company_type_share_range_pp: 0,
          adjusted_by_location: {},
          adjusted_by_remote: {},
          adjusted_by_company_type: {},
        },
        confidence: "low",
        notes: ["Low confidence note"],
      }),
  },
}))

describe("FairnessAudit end-to-end", () => {
  it("renders tables and low-confidence state", async () => {
    render(
      <QueryProvider>
        <FairnessAudit />
      </QueryProvider>,
    )
    expect(await screen.findByRole("heading", { name: "Fairness Audit" })).toBeTruthy()
    expect((await screen.findAllByText(/Low confidence/)).length).toBeGreaterThan(0)
    expect(await screen.findAllByText(/By location/)).toBeTruthy()
    expect(await screen.findAllByText(/By remote status/)).toBeTruthy()
    expect(await screen.findAllByText(/By company type/)).toBeTruthy()
  })
})