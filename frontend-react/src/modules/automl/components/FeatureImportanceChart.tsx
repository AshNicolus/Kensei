import {
  Bar,
  BarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { FeatureImportance } from "@/modules/automl/api/types";

interface Props {
  data: FeatureImportance[];
  max?: number;
}

export function FeatureImportanceChart({ data, max = 12 }: Props) {
  const top = data.slice(0, max).map((d) => ({
    feature: d.feature.length > 22 ? d.feature.slice(0, 21) + "…" : d.feature,
    importance: d.importance,
  }));
  if (top.length === 0) return null;
  return (
    <div className="h-[280px] w-full">
      <ResponsiveContainer>
        <BarChart
          data={top}
          layout="vertical"
          margin={{ top: 4, right: 24, left: 8, bottom: 4 }}
        >
          <XAxis
            type="number"
            stroke="hsl(var(--muted-foreground))"
            fontSize={11}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            type="category"
            dataKey="feature"
            stroke="hsl(var(--muted-foreground))"
            fontSize={11}
            tickLine={false}
            axisLine={false}
            width={120}
          />
          <Tooltip
            cursor={{ fill: "hsl(var(--accent))" }}
            contentStyle={{
              backgroundColor: "hsl(var(--popover))",
              border: "1px solid hsl(var(--border))",
              borderRadius: 6,
              fontSize: 12,
            }}
            formatter={(v: number) => v.toFixed(4)}
          />
          <Bar
            dataKey="importance"
            fill="hsl(var(--primary))"
            radius={[0, 4, 4, 0]}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
