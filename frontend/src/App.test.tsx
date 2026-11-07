import { describe, it, expect } from "vitest"
import { render } from "@testing-library/react"
import App from "@/App"
import { QueryProvider } from "@/providers/QueryProvider"

describe("App", () => {
  it("renders without crashing", () => {
    const { container } = render(
      <QueryProvider>
        <App />
      </QueryProvider>,
    )
    expect(container).toBeTruthy()
  })
})