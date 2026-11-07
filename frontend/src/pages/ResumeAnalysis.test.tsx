import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import ResumeAnalysis from "@/pages/ResumeAnalysis"
import { QueryProvider } from "@/providers/QueryProvider"

vi.mock("@/lib/api", () => ({
  api: {
    resumeAnalyze: () =>
      Promise.resolve({
        resume_skills: ["Python", "Docker"],
        matched_skills: ["Python"],
        missing_skills: [
          { skill: "React", demand: 5, percentage: 10.0, resources: { YouTube: { url: "https://example.com" } } },
        ],
        match_percentage: 25.0,
        weighted_match_percentage: 30.0,
        total_postings: 10,
        total_demand_skills: 4,
      }),
  },
}))

describe("ResumeAnalysis end-to-end", () => {
  it("renders upload controls", async () => {
    render(
      <QueryProvider>
        <ResumeAnalysis />
      </QueryProvider>,
    )
    expect(await screen.findByRole("heading", { name: "Resume Skill-Gap Analysis" })).toBeTruthy()
    expect(await screen.findByText(/Analyze Resume/)).toBeTruthy()
  })
})