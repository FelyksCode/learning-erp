"use client";

import {
  Area,
  CartesianGrid,
  ComposedChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { TrendPoint } from "@/lib/api";

function money(n: number) {
  return n.toLocaleString(undefined, { style: "currency", currency: "USD", maximumFractionDigits: 2 });
}

export default function SalesChart({ trend }: { trend: TrendPoint[] }) {
  if (trend.length === 0) {
    return (
      <p className="grid h-full place-items-center text-center text-sm text-pencil">
        No sales recorded in this period yet.
      </p>
    );
  }

  return (
    <ResponsiveContainer width="100%" height="100%">
      <ComposedChart data={trend} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
        <CartesianGrid stroke="#e2d6bc" strokeDasharray="1 4" vertical={false} />
        <XAxis
          dataKey="date"
          tick={{ fontSize: 10, fill: "#6e6555", fontFamily: "var(--f-mono)" }}
          tickFormatter={(d: string) => d.slice(5)}
          axisLine={{ stroke: "#b9a67f" }}
          tickLine={false}
        />
        <YAxis
          yAxisId="qty"
          tick={{ fontSize: 10, fill: "#6e6555", fontFamily: "var(--f-mono)" }}
          width={32}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          yAxisId="rev"
          orientation="right"
          tick={{ fontSize: 10, fill: "#6e6555", fontFamily: "var(--f-mono)" }}
          width={48}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip
          cursor={{ stroke: "#b9a67f", strokeDasharray: "2 3" }}
          contentStyle={{
            background: "#fcf9f0",
            border: "1px solid #b9a67f",
            borderRadius: 4,
            fontSize: 11,
            fontFamily: "var(--f-mono)",
          }}
          formatter={(value, name) =>
            name === "revenue" ? [money(Number(value)), "Revenue"] : [Number(value), "Units"]
          }
        />
        <Area
          yAxisId="qty"
          dataKey="qty_sold"
          name="qty_sold"
          stroke="#262119"
          strokeWidth={1.25}
          fill="#b9a67f"
          fillOpacity={0.35}
        />
        <Area
          yAxisId="rev"
          dataKey="revenue"
          name="revenue"
          stroke="#2d4fa1"
          strokeWidth={1.5}
          fill="#2d4fa1"
          fillOpacity={0.08}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
