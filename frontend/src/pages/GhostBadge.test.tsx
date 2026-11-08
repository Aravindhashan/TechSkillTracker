import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import GhostBadge from "@/components/GhostBadge"

describe("GhostBadge", () => {
  it("renders estimated risk label and score", () => {
    render(<GhostBadge ghost={{ risk: 0.6, label: "high" }} />)
    expect(screen.getByText(/Estimated risk: high \(0\.60\)/)).toBeTruthy()
  })

  it("renders nothing without ghost risk", () => {
    const { container } = render(<GhostBadge ghost={null} />)
    expect(container.textContent).toBe("")
  })
})