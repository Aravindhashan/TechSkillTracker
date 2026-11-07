import { Card, CardContent } from "@/components/ui/card"

interface MetricProps {
  label: string
  value: string | number
}

export default function Metric({ label, value }: MetricProps) {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="text-sm text-muted-foreground">{label}</div>
        <div className="text-2xl font-bold">
          {typeof value === "number" ? value.toLocaleString() : value}
        </div>
      </CardContent>
    </Card>
  )
}