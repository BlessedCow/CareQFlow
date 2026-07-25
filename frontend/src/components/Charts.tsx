import { useMemo } from "react";
import { AuthRequest } from "../types/auth";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
  PieChart,
  Pie,
} from "recharts";
import { format, parseISO } from "date-fns";

interface ChartProps {
  data: AuthRequest[];
  darkMode: boolean;
}

interface LOCChartProps extends ChartProps {
  onLocDoubleClick?: (loc: string) => void;
}

export function TrendChart({ data, darkMode }: ChartProps) {
  const chartData = useMemo(() => {
    const countsByDate = data.reduce((acc, curr) => {
      const dateKey = format(curr.date, "yyyy-MM-dd");

      if (!acc[dateKey]) {
        acc[dateKey] = {
          date: dateKey,
          Approved: 0,
          Denied: 0,
          Pending: 0,
          Total: 0,
        };
      }

      if (curr.status === "Approved") {
        acc[dateKey].Approved += 1;
      } else if (curr.status === "Denied") {
        acc[dateKey].Denied += 1;
      } else if (curr.status === "Pending") {
        acc[dateKey].Pending += 1;
      }

      acc[dateKey].Total += 1;
      return acc;
    }, {} as Record<string, { date: string; Approved: number; Denied: number; Pending: number; Total: number }>);

    return Object.values(countsByDate).sort(
      (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()
    );
  }, [data]);

  const textColor = darkMode ? "#9CA3AF" : "#4B5563";
  const gridColor = darkMode ? "#374151" : "#E5E7EB";

  if (chartData.length === 0) {
    return (
      <div className="h-80 w-full flex items-center justify-center">
        <p
          className={
            darkMode ? "text-sm text-gray-400" : "text-sm text-gray-500"
          }
        >
          No authorization trend data available for the selected filters.
        </p>
      </div>
    );
  }

  return (
    <div className="h-80 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          data={chartData}
          margin={{ top: 5, right: 20, bottom: 5, left: 0 }}
        >
          <CartesianGrid
            strokeDasharray="3 3"
            stroke={gridColor}
            vertical={false}
          />
          <XAxis
            dataKey="date"
            stroke={textColor}
            fontSize={12}
            tickFormatter={(val) => format(parseISO(val), "MMM d")}
            tickMargin={10}
            minTickGap={20}
          />
          <YAxis
            stroke={textColor}
            fontSize={12}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: darkMode ? "#1F2937" : "#FFFFFF",
              borderColor: darkMode ? "#374151" : "#E5E7EB",
              color: darkMode ? "#F3F4F6" : "#111827",
              borderRadius: "8px",
            }}
            labelFormatter={(label) => format(parseISO(label), "MMM d, yyyy")}
          />
          <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "10px" }} />
          <Line
            type="monotone"
            dataKey="Total"
            stroke="#3B82F6"
            strokeWidth={3}
            dot={{ r: 4 }}
            activeDot={{ r: 6 }}
          />
          <Line
            type="monotone"
            dataKey="Approved"
            stroke="#10B981"
            strokeWidth={2}
            dot={{ r: 3 }}
            activeDot={{ r: 5 }}
          />
          <Line
            type="monotone"
            dataKey="Denied"
            stroke="#F43F5E"
            strokeWidth={2}
            dot={{ r: 3 }}
            activeDot={{ r: 5 }}
          />
          <Line
            type="monotone"
            dataKey="Pending"
            stroke="#F59E0B"
            strokeWidth={2}
            dot={{ r: 3 }}
            activeDot={{ r: 5 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function normalizeLocName(loc: unknown): string {
  const normalizedLoc = String(loc ?? "")
    .trim()
    .toLowerCase();

  if (normalizedLoc === "dtx" || normalizedLoc.includes("detox")) {
    return "DTX";
  }

  if (normalizedLoc === "rtc" || normalizedLoc.includes("residential")) {
    return "RTC";
  }

  if (normalizedLoc === "php") {
    return "PHP";
  }

  if (normalizedLoc === "iop") {
    return "IOP";
  }

  return "UNKNOWN";
}

const LOC_COLORS: Record<string, string> = {
  DTX: "#f97316", // Orange
  RTC: "#5c6bc0", // Red
  PHP: "#a855f7", // Purple
  IOP: "#22c55e", // Green
  UNKNOWN: "#64748b", // Gray
};

const DEFAULT_LOC_COLOR = "#64748b";

export function LOCChart({ data, darkMode, onLocDoubleClick }: LOCChartProps) {
  const chartData = useMemo(() => {
    const locCounts = data.reduce((acc, curr) => {
      const loc = normalizeLocName(curr.loc);
      acc[loc] = (acc[loc] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    return Object.entries(locCounts)
      .map(([name, value]) => ({
        name,
        value,
        fill: LOC_COLORS[name] ?? DEFAULT_LOC_COLOR,
      }))
      .sort((a, b) => b.value - a.value);
  }, [data]);

  const handleLocDoubleClick = (entry: unknown) => {
    if (
      typeof entry === "object" &&
      entry !== null &&
      "name" in entry &&
      typeof entry.name === "string"
    ) {
      onLocDoubleClick?.(entry.name);
    }
  };

  return (
    <div className="h-80 w-full flex items-center justify-center">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            innerRadius={80}
            outerRadius={110}
            paddingAngle={2}
            dataKey="value"
            stroke={darkMode ? "#111827" : "#ffffff"}
            strokeWidth={2}
            onDoubleClick={handleLocDoubleClick}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: darkMode ? "#1F2937" : "#FFFFFF",
              borderColor: darkMode ? "#374151" : "#E5E7EB",
              color: darkMode ? "#F3F4F6" : "#111827",
              borderRadius: "8px",
            }}
            itemStyle={{ color: darkMode ? "#F3F4F6" : "#111827" }}
          />
          <Legend
            verticalAlign="bottom"
            height={36}
            iconType="circle"
            wrapperStyle={{ fontSize: "12px", cursor: "pointer" }}
            onDoubleClick={(entry) => {
              if (typeof entry.value === "string") {
                onLocDoubleClick?.(entry.value);
              }
            }}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}

export function DenialChart({ data, darkMode }: ChartProps) {
  const chartData = useMemo(() => {
    const denialCounts = data.reduce((acc, curr) => {
      const denialReason = String(curr.denialReason || "").trim();

      if (!denialReason || denialReason === "N/A") {
        return acc;
      }

      acc[denialReason] = (acc[denialReason] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    return Object.entries(denialCounts)
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => b.value - a.value);
  }, [data]);

  const textColor = darkMode ? "#9CA3AF" : "#4B5563";
  const gridColor = darkMode ? "#374151" : "#E5E7EB";

  if (chartData.length === 0) {
    return (
      <div className="h-80 w-full flex items-center justify-center">
        <p
          className={
            darkMode ? "text-sm text-gray-400" : "text-sm text-gray-500"
          }
        >
          No denial reasons found for the selected filters.
        </p>
      </div>
    );
  }

  return (
    <div className="h-80 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={chartData}
          layout="vertical"
          margin={{ top: 5, right: 30, left: 40, bottom: 5 }}
        >
          <CartesianGrid
            strokeDasharray="3 3"
            stroke={gridColor}
            horizontal={false}
          />
          <XAxis
            type="number"
            stroke={textColor}
            fontSize={12}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            dataKey="name"
            type="category"
            stroke={textColor}
            fontSize={12}
            tickLine={false}
            axisLine={false}
            width={100}
          />
          <Tooltip
            cursor={{ fill: darkMode ? "#374151" : "#F3F4F6" }}
            contentStyle={{
              backgroundColor: darkMode ? "#1F2937" : "#FFFFFF",
              borderColor: darkMode ? "#374151" : "#E5E7EB",
              color: darkMode ? "#F3F4F6" : "#111827",
              borderRadius: "8px",
            }}
          />
          <Bar
            dataKey="value"
            fill="#F43F5E"
            radius={[0, 4, 4, 0]}
            barSize={24}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
