import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import Recommendations from "@/pages/Recommendations"
import { QueryProvider } from "@/providers/QueryProvider"

vi.mock("@/lib/api", () => ({
  api: {
    recommendations: () =>
      Promise.resolve({
        mode: "complementary",
        status: "success",
        message: null,
        results: [{ skill: "PostgreSQL" }],
      }),
  },
}))

describe("Recommendations end-to-end", () => {
  it("renders all three mode tabs", async () => {
    render(
      <QueryProvider>
        <Recommendations />
      </QueryProvider>,
    )
    expect(await screen.findByRole("heading", { name: "Skill Recommendations" })).toBeTruthy()
    expect(screen.getByText(/Complementary Skills/)).toBeTruthy()
    expect(screen.getByText(/Job Role Analysis/)).toBeTruthy()
    expect(screen.getByText(/Learning Roadmap/)).toBeTruthy()
  })

  it("switches to role mode", async () => {
    render(
      <QueryProvider>
        <Recommendations />
      </QueryProvider>,
    )
    fireEvent.click(screen.getByText(/Job Role Analysis/))
    expect(await screen.findByPlaceholderText(/Data Scientist/)).toBeTruthy()
  })

  it("switches to learning-path mode", async () => {
    render(
      <QueryProvider>
        <Recommendations />
      </QueryProvider>,
    )
    fireEvent.click(screen.getByText(/Learning Roadmap/))
    expect(await screen.findByPlaceholderText(/Python, SQL/)).toBeTruthy()
  })
})