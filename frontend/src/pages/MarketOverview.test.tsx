import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import MarketOverview from "@/pages/MarketOverview"
import { QueryProvider } from "@/providers/QueryProvider"
import { FilterProvider } from "@/context/FilterContext"

vi.mock("@/lib/api", () => ({
  api: {
    marketOverview: () => Promise.resolve({
      total_openings: 59,
      unique_skills: 70,
      companies: 38,
      locations: 13,
    }),
    topSkills: () => Promise.resolve({ skills: [{ skill: "Python", count: 12 }] }),
    locations: () => Promise.resolve({ locations: [{ location: "Telangana", count: 8 }] }),
    recentPostings: () => Promise.resolve({
      postings: [
        {
          job_id: "job-1",
          title: "Backend Engineer",
          company: "Acme",
          location: "Bengaluru",
          posted_at: "2026-11-07",
          url: "https://example.com/job",
          is_remote: false,
          skills: ["Python", "PostgreSQL"],
        },
      ],
    }),
  },
}))

describe("MarketOverview end-to-end", () => {
  it("renders metrics and recent postings with Apply Now", async () => {
    render(
      <QueryProvider>
        <FilterProvider>
          <MarketOverview />
        </FilterProvider>
      </QueryProvider>,
    )

    expect(await screen.findByText(/Market Overview/)).toBeTruthy()
    expect(await screen.findByText(/Total Job Openings/)).toBeTruthy()
    expect(await screen.findByText(/Backend Engineer/)).toBeTruthy()
    expect(await screen.findByRole("link", { name: /Apply Now/ })).toBeTruthy()
  })

  it("renders with header filters", async () => {
    render(
      <QueryProvider>
        <FilterProvider>
          <MarketOverview />
        </FilterProvider>
      </QueryProvider>,
    )
    await screen.findByText(/Market Overview/)
    expect(screen.getByText(/Market Overview/)).toBeTruthy()
  })
})