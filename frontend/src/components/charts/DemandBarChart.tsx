"use client";

import {
  Bar,
  BarChart,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { formatCount } from "@/lib/format";

export interface DemandDatum {
  label: string;
  value: number;
}

interface TooltipPayload {
  active?: boolean;
  payload?: { payload: DemandDatum }[];
}

/*
 * A single-series ranked bar chart. Magnitude is carried by bar length, so one
 * hue is used throughout — the near-monochrome palette has no second step that
 * would stay distinguishable, and no categorical identity is being encoded.
 */
function DemandTooltip({
  active,
  payload,
  valueLabel,
}: TooltipPayload & { valueLabel: string }) {
  if (!active || !payload?.length) {
    return null;
  }

  const datum = payload[0].payload;

  return (
    <div className="rounded-lg border border-border bg-surface px-3 py-2 shadow-lg">
      <p className="text-sm font-medium text-text">{datum.label}</p>
      <p className="text-xs text-text-muted">
        {formatCount(datum.value)} {valueLabel}
      </p>
    </div>
  );
}

interface DemandBarChartProps {
  data: DemandDatum[];
  valueLabel: string;
  categoryWidth?: number;
}

export function DemandBarChart({
  data,
  valueLabel,
  categoryWidth = 150,
}: DemandBarChartProps) {
  // Each row keeps a fixed slot so long lists stay readable rather than squashed.
  const chartHeight = Math.max(160, data.length * 32);

  return (
    <div style={{ height: chartHeight }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 4, right: 48, bottom: 4, left: 0 }}
          barCategoryGap={2}
        >
          <XAxis type="number" hide />
          <YAxis
            type="category"
            dataKey="label"
            width={categoryWidth}
            tickLine={false}
            axisLine={false}
            tick={{ fill: "var(--color-text-muted)", fontSize: 12 }}
          />
          <Tooltip
            content={<DemandTooltip valueLabel={valueLabel} />}
            cursor={{ fill: "var(--color-surface-muted)" }}
          />
          <Bar
            dataKey="value"
            fill="var(--color-accent)"
            radius={[0, 4, 4, 0]}
            barSize={16}
            isAnimationActive={false}
          >
            <LabelList
              dataKey="value"
              position="right"
              offset={8}
              fill="var(--color-text-muted)"
              fontSize={12}
              formatter={(value) => formatCount(Number(value ?? 0))}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
