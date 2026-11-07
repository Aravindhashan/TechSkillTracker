import { Card, CardContent } from "@/components/ui/card"

interface MetricProps {
  label: string
  value: string | number
}

export default function Metric({ label, value }: MetricProps) {
  return (
    <Card className="rounded-2xl">
      <CardContent className="pt-5">
        <div className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{label}</div>
        <div className="stat-num text-4xl leading-tight mt-1">
          {typeof value === "number" ? value.toLocaleString() : value}
        </div>
      </CardContent>
    </Card>
  )
}