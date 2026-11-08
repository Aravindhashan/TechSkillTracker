interface GhostRisk {
  risk: number
  label: string
}

export default function GhostBadge({ ghost }: { ghost?: GhostRisk | null }) {
  if (!ghost) return null
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border border-border px-2.5 py-0.5 text-xs ${
        ghost.label === "high" ? "border-red-900/30" : ghost.label === "medium" ? "border-amber-900/30" : ""
      }`}
    >
      Estimated risk: {ghost.label} ({ghost.risk.toFixed(2)})
    </span>
  )
}