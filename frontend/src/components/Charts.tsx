import { Bar, CartesianGrid, Cell, ComposedChart, Legend, Line, Pie, PieChart, ReferenceArea, ResponsiveContainer,
  Tooltip, XAxis, YAxis } from "recharts";
import type { WeatherDay } from "../types";
import { growthColor } from "./MapView";

export function Gauge({ value }: { value: number }) {
  const len = Math.PI * 60;
  return (
    <svg viewBox="0 0 140 84" className="gauge" role="img" aria-label={`Probabilità di crescita ${value}%`}>
      <path d="M10 74 A60 60 0 0 1 130 74" fill="none" stroke="#dfe5da" strokeWidth="14" strokeLinecap="round" />
      <path d="M10 74 A60 60 0 0 1 130 74" fill="none" stroke={growthColor(value)} strokeWidth="14" strokeLinecap="round"
        strokeDasharray={`${(value / 100) * len} ${len}`} />
      <text x="70" y="68" textAnchor="middle" className="gauge-num">{value}%</text>
    </svg>
  );
}

export function WeatherChart({ days }: { days: WeatherDay[] }) {
  const data = days.map((d) => ({ date: d.date.slice(5), rain: d.rain, tmax: d.tmax, tmin: d.tmin, inPeriod: d.in_period }));
  const period = data.filter((d) => d.inPeriod);
  return (
    <ResponsiveContainer width="100%" height={230}>
      <ComposedChart data={data} margin={{ top: 8, right: 4, left: -14, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#dfe5da" />
        <XAxis dataKey="date" tick={{ fontSize: 11 }} interval="preserveStartEnd" minTickGap={18} />
        <YAxis yAxisId="rain" tick={{ fontSize: 11 }} unit=" mm" />
        <YAxis yAxisId="temp" orientation="right" tick={{ fontSize: 11 }} unit="°" />
        <Tooltip />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        {period.length ? <ReferenceArea yAxisId="rain" x1={period[0].date} x2={period[period.length - 1].date}
          fill="#b4761b" fillOpacity={0.1} /> : null}
        <Bar yAxisId="rain" dataKey="rain" name="Pioggia (mm)">
          {data.map((d, i) => <Cell key={i} fill={d.inPeriod ? "#2f6fa8" : "#8db4d6"} />)}
        </Bar>
        <Line yAxisId="temp" dataKey="tmax" name="T max" stroke="#c2562b" dot={false} strokeWidth={2} />
        <Line yAxisId="temp" dataKey="tmin" name="T min" stroke="#6a8f5a" dot={false} strokeWidth={2} />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

const FOREST_COLORS = ["#3f6b3a", "#b4761b", "#7a5c3a", "#6a8f5a", "#8a3d2b", "#4e7f8c", "#9b9b5a"];

export function ForestChart({ data }: { data: { label: string; weight: number }[] }) {
  return (
    <div className="forest">
      <ResponsiveContainer width={140} height={140}>
        <PieChart>
          <Pie data={data} dataKey="weight" nameKey="label" innerRadius={34} outerRadius={64} paddingAngle={2}>
            {data.map((_, i) => <Cell key={i} fill={FOREST_COLORS[i % FOREST_COLORS.length]} />)}
          </Pie>
          <Tooltip formatter={(v: number) => `${Math.round(v * 100)}%`} />
        </PieChart>
      </ResponsiveContainer>
      <ul className="legend">
        {data.map((d, i) => (
          <li key={d.label}><i style={{ background: FOREST_COLORS[i % FOREST_COLORS.length] }} />
            {d.label} <b>{Math.round(d.weight * 100)}%</b></li>
        ))}
      </ul>
    </div>
  );
}
