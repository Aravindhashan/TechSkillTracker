import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import SearchRoi from "@/pages/SearchRoi"
import { QueryProvider } from "@/providers/QueryProvider"

vi.mock("@/lib/api", () => ({
  api: {
    search: () =>
      Promise.resolve({
        query: "python",
        backend: "lexical fallback",
        results: [
          {
            job_id: "job-1",
            title: "Backend Engineer",
            company: "Acme",
            location: "Bengaluru",
            posted_at: "2026-11-07",
            url: "https://example.com/job",
            skills: ["Python"],
            description: "Python and Postgres",
            score: 1.0,
            semantic_score: 1.0,
            rerank_score: null,
          },
        ],
      }),
    roi: () =>
      Promise.resolve({
        rows: [
          {
            skill: "Python",
            demand: 5,
            share_pct: 20.0,
            months_observed: 2,
            momentum: 0.1,
            monthly_growth_pct: 10.5,
            confidence: "medium",
            premium: null,
            p_value: null,
            roi_score: 1.5,
          },
        ],
      }),
  },
}))

describe("SearchRoi end-to-end", () => {
  it("renders search tab", async () => {
    render(
      <QueryProvider>
        <SearchRoi />
      </QueryProvider>,
    )
    expect(await screen.findByRole("heading", { name: "Search & ROI" })).toBeTruthy()
    expect(screen.getByText(/Semantic job search/)).toBeTruthy()
    expect(screen.getByText(/Skill ROI/)).toBeTruthy()
  })

  it("switches to ROI tab", async () => {
    render(
      <QueryProvider>
        <SearchRoi />
      </QueryProvider>,
    )
    fireEvent.click(screen.getByText(/Skill ROI/))
    expect(await screen.findByText(/Top skills by demand ROI score/)).toBeTruthy()
    expect(await screen.findByText(/Python/)).toBeTruthy()
  })
})