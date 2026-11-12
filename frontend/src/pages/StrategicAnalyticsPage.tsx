/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useEffect } from "react"
import { Link } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { useStrategicStatusColors } from "../hooks/useChartColors";
import { API_BASE } from '@/api/types';
import {
  BarChart3,
  Target,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Calendar,
  TrendingUp,
  Building2,
  Users,
  ChevronRight,
  Edit2,
  RefreshCw,
  AlertCircle,
  Activity,
} from "lucide-react";
import api from "../api/api";
import toast from "react-hot-toast";
import { useTranslation } from '@/i18n'
import { AdminShell } from '../components/shells/AdminShell'
import PageContainer from '@/components/layout/PageContainer'

// Types
interface StrategicGoal {
  id: number;
  title: string;
  description?: string;
  public_description?: string;
  category?: string;
  department?: string;
  target_date?: string;
  progress: number;
  status: string;
  priority: number;
  is_public: boolean;
  staff_can_update: boolean;
  metrics?: { name: string; current: number; target: number; unit?: string }[];
}

interface ProgressUpdate {
  id: number;
  goal_id: number;
  goal_title: string;
  progress: number;
  note?: string;
  updated_by_name: string;
  created_at: string;
}

interface StrategicAnalytics {
  plan_period: string;
  overall_progress: number;
  goals_completed: number;
  goals_at_risk: number;
  goals_delayed: number;
  goals_on_track: number;
  goals_not_started: number;
  total_goals: number;
  upcoming_deadlines_count: number;
  goals_by_status: Record<string, number>;
  goals_by_department: Record<string, number>;
  goals_by_category: Record<string, number>;
  at_risk_goals: StrategicGoal[];
  upcoming_deadline_goals: StrategicGoal[];
  recent_updates: ProgressUpdate[];
}

interface ActivePlan {
  id: number;
  title: string;
  period_start: string;
  period_end: string;
  status: string;
}

// Status colors mapping
const statusColors: Record<string, { bg: string; text: string; ring: string }> = {
  not_started: { bg: "bg-earth-100 dark:bg-earth-800", text: "text-lsc-dark/70 dark:text-lsc-cream/70", ring: "ring-earth-300" },
  on_track: { bg: "bg-status-success-100 dark:bg-status-success-900/30", text: "text-status-success-700 dark:text-status-success-300", ring: "ring-status-success-300" },
  at_risk: { bg: "bg-status-warning-100 dark:bg-status-warning-900/30", text: "text-status-warning-700 dark:text-status-warning-300", ring: "ring-status-warning-300" },
  delayed: { bg: "bg-status-danger-100 dark:bg-status-danger-900/30", text: "text-status-danger-700 dark:text-status-danger-300", ring: "ring-status-danger-300" },
  completed: { bg: "bg-earth-100 dark:bg-earth-800/30", text: "text-lsc-rose dark:text-lsc-rose-light", ring: "ring-lsc-rose/60" },
};

const statusLabels: Record<string, string> = {
  not_started: "Not Started",
  on_track: "On Track",
  at_risk: "At Risk",
  delayed: "Delayed",
  completed: "Completed",
};

// Helper: days until/since date
function getDaysFromNow(dateStr: string): number {
  const target = new Date(dateStr);
  const now = new Date();
  const diff = target.getTime() - now.getTime();
  return Math.ceil(diff / (1000 * 60 * 60 * 24));
}

// Circular Progress Indicator
function CircularProgress({ value, size = 120, strokeWidth = 10 }: { value: number; size?: number; strokeWidth?: number }) {
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (value / 100) * circumference;

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg className="transform -rotate-90" width={size} height={size}>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth={strokeWidth}
          className="text-lsc-cream dark:text-lsc-brown"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="text-lsc-rose transition-all duration-500"
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{Math.round(value)}%</span>
      </div>
    </div>
  );
}

// Summary Card Component
function SummaryCard({
  title,
  value,
  icon: Icon,
  color = 'warning',
  subtitle,
}: {
  title: string;
  value: string | number;
  icon: React.ElementType;
  color?: 'warning' | 'green' | 'yellow' | 'red' | 'blue' | 'purple' | 'success' | 'accent' | 'danger' | 'category';
  subtitle?: string;
}) {
  const colorClasses: Record<NonNullable<typeof color>, string> = {
    warning: "bg-lsc-rose/10 text-lsc-rose",
    green: "bg-status-success-100 text-status-success-600 dark:bg-status-success-900/30 dark:text-status-success-400",
    yellow: "bg-status-warning-100 text-status-warning-600 dark:bg-status-warning-900/30 dark:text-status-warning-400",
    red: "bg-status-danger-100 text-status-danger-600 dark:bg-status-danger-900/30 dark:text-status-danger-400",
    blue: "bg-earth-100 text-lsc-rose dark:text-lsc-rose-light dark:bg-earth-800/30 dark:text-lsc-rose-light",
    purple: "bg-category-100 text-category-600 dark:bg-category-900/30 dark:text-category-400",
    // Semantic aliases
    success: "bg-status-success-100 text-status-success-600 dark:bg-status-success-900/30 dark:text-status-success-400",
    accent: "bg-earth-100 text-lsc-rose dark:text-lsc-rose-light dark:bg-earth-800/30 dark:text-lsc-rose-light",
    danger: "bg-status-danger-100 text-status-danger-600 dark:bg-status-danger-900/30 dark:text-status-danger-400",
    category: "bg-category-100 text-category-600 dark:bg-category-900/30 dark:text-category-400",
  };

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-5 shadow-sm border border-lsc-border dark:border-earth-700">
      <div className="flex items-center gap-4">
        <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${colorClasses[color]}`}>
          <Icon className="w-6 h-6" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 truncate" title={title}>{title}</p>
          <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{value}</p>
          {subtitle && <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{subtitle}</p>}
        </div>
      </div>
    </div>
  );
}

// Horizontal Bar Chart Component
function HorizontalBarChart({ data, maxValue }: { data: Record<string, number>; maxValue?: number }) {
  const entries = Object.entries(data).sort((a, b) => b[1] - a[1]);
  const max = maxValue || Math.max(...Object.values(data), 1);
  const colors = [
    "bg-lsc-rose",
    "bg-earth-500",
    "bg-status-success-500",
    "bg-category-500",
    "bg-pink-500",
    "bg-cyan-500",
    "bg-status-warning-500",
    "bg-lsc-rose",
  ];

  return (
    <div className="space-y-3">
      {entries.map(([label, value], index) => (
        <div key={label}>
          <div className="flex justify-between text-sm mb-1">
            <span className="text-lsc-dark dark:text-lsc-cream truncate pr-2" title={label || "Unassigned"}>{label || "Unassigned"}</span>
            <span className="text-lsc-dark/70 dark:text-lsc-cream/70 font-medium">{value}</span>
          </div>
          <div className="h-3 bg-lsc-cream dark:bg-lsc-brown rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${colors[index % colors.length]}`}
              style={{ width: `${(value / max) * 100}%` }}
            />
          </div>
        </div>
      ))}
      {entries.length === 0 && (
        <p className="text-center text-lsc-dark/70 dark:text-lsc-cream/70 py-4">No data available</p>
      )}
    </div>
  );
}

// Donut Chart for Status Distribution
function StatusDonutChart({ data }: { data: Record<string, number> }) {
  const statusColorMap = useStrategicStatusColors();
  const total = Object.values(data).reduce((sum, v) => sum + v, 0);
  if (total === 0) {
    return (
      <div className="flex items-center justify-center h-48">
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">No goals yet</p>
      </div>
    );
  }

  const statusOrder = ["completed", "on_track", "at_risk", "delayed", "not_started"];

  let cumulativePercentage = 0;
  const segments = statusOrder
    .filter((status) => (data[status] ?? 0) > 0)
    .map((status) => {
      const percentage = ((data[status] ?? 0) / total) * 100;
      const segment = {
        status,
        percentage,
        offset: cumulativePercentage,
        color: statusColorMap[status] || statusColorMap.not_started,
      };
      cumulativePercentage += percentage;
      return segment;
    });

  return (
    <div className="flex flex-col items-center">
      <div className="relative w-40 h-40 mb-4">
        <svg viewBox="0 0 100 100" className="transform -rotate-90">
          {segments.map((segment, _i) => {
            const dashArray = `${segment.percentage * 2.51327} ${251.327 - segment.percentage * 2.51327}`;
            const dashOffset = -segment.offset * 2.51327;
            return (
              <circle
                key={segment.status}
                cx="50"
                cy="50"
                r="40"
                fill="none"
                stroke={segment.color}
                strokeWidth="20"
                strokeDasharray={dashArray}
                strokeDashoffset={dashOffset}
                className="transition-all duration-500"
              />
            );
          })}
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="text-center">
            <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{total}</p>
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Total</p>
          </div>
        </div>
      </div>
      <div className="flex flex-wrap justify-center gap-3">
        {segments.map((segment) => (
          <div key={segment.status} className="flex items-center gap-1.5">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: segment.color }} />
            <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
              {statusLabels[segment.status]} ({data[segment.status]})
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// Line Chart Placeholder for Progress Over Time
function ProgressLineChart({ data }: { data: { date: string; progress: number }[] }) {
  const { t } = useTranslation();
  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 bg-lsc-cream/50 dark:bg-lsc-brown/50 rounded-lg">
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('strategicAnalytics.noProgressDataYet')}</p>
      </div>
    );
  }

  const maxProgress = Math.max(...data.map((d) => d.progress), 100);
  const minProgress = 0;
  const range = maxProgress - minProgress;

  // Simple SVG line chart
  const width = 100;
  const height = 40;
  const points = data.map((d, i) => {
    const x = (i / (data.length - 1 || 1)) * width;
    const y = height - ((d.progress - minProgress) / (range || 1)) * height;
    return `${x},${y}`;
  });

  return (
    <div className="space-y-4">
      <div className="h-48 bg-lsc-cream/50 dark:bg-lsc-brown/50 rounded-lg p-4 flex items-end">
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-full" preserveAspectRatio="none">
          {/* Grid lines */}
          <line x1="0" y1={height * 0.25} x2={width} y2={height * 0.25} stroke="currentColor" strokeWidth="0.2" className="text-lsc-border dark:text-earth-700" />
          <line x1="0" y1={height * 0.5} x2={width} y2={height * 0.5} stroke="currentColor" strokeWidth="0.2" className="text-lsc-border dark:text-earth-700" />
          <line x1="0" y1={height * 0.75} x2={width} y2={height * 0.75} stroke="currentColor" strokeWidth="0.2" className="text-lsc-border dark:text-earth-700" />
          {/* Line */}
          <polyline
            points={points.join(" ")}
            fill="none"
            stroke="currentColor"
            strokeWidth="1"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="text-lsc-rose"
          />
          {/* Area fill */}
          <polygon
            points={`0,${height} ${points.join(" ")} ${width},${height}`}
            className="fill-lsc-rose/20"
          />
          {/* Data points */}
          {data.map((d, i) => {
            const x = (i / (data.length - 1 || 1)) * width;
            const y = height - ((d.progress - minProgress) / (range || 1)) * height;
            return (
              <circle
                key={i}
                cx={x}
                cy={y}
                r="1.5"
                className="fill-lsc-rose"
              />
            );
          })}
        </svg>
      </div>
      <div className="flex justify-between text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
        <span>{data[0]?.date ? new Date(data[0]!.date).toLocaleDateString() : ""}</span>
        <span>{data[data.length - 1]?.date ? new Date(data[data.length - 1]!.date).toLocaleDateString() : ""}</span>
      </div>
    </div>
  );
}

// At-Risk Goals Table
function AtRiskGoalsTable({ goals }: { goals: StrategicGoal[] }) {
  const { t } = useTranslation();
  if (goals.length === 0) {
    return (
      <div className="text-center py-8">
        <CheckCircle2 className="w-12 h-12 mx-auto text-status-success-500 mb-3" />
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('strategicAnalytics.noAtRiskOrDelayed')}</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b border-lsc-border dark:border-earth-700">
            <th className="text-left py-3 px-4 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Goal</th>
            <th className="text-left py-3 px-4 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Department</th>
            <th className="text-center py-3 px-4 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Progress</th>
            <th className="text-left py-3 px-4 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Target Date</th>
            <th className="text-center py-3 px-4 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Status</th>
            <th className="text-right py-3 px-4 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Action</th>
          </tr>
        </thead>
        <tbody>
          {goals.map((goal) => {
            const daysOverdue = goal.target_date ? -getDaysFromNow(goal.target_date) : 0;
            const statusStyle = statusColors[goal.status]! || statusColors.not_started;

            return (
              <tr key={goal.id} className="border-b border-lsc-border/50 dark:border-earth-700/50 hover:bg-lsc-cream/50 dark:hover:bg-lsc-brown/50">
                <td className="py-3 px-4">
                  <p className="font-medium text-lsc-dark dark:text-lsc-cream">{goal.title}</p>
                  {goal.category && (
                    <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{goal.category}</span>
                  )}
                </td>
                <td className="py-3 px-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  {goal.department || "-"}
                </td>
                <td className="py-3 px-4">
                  <div className="flex items-center justify-center gap-2">
                    <div className="w-16 h-2 bg-lsc-cream dark:bg-lsc-brown rounded-full overflow-hidden">
                      <div
                        className="h-full bg-lsc-rose rounded-full"
                        style={{ width: `${goal.progress}%` }}
                      />
                    </div>
                    <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 w-10">{goal.progress}%</span>
                  </div>
                </td>
                <td className="py-3 px-4">
                  <div className="text-sm">
                    <p className="text-lsc-dark dark:text-lsc-cream">
                      {goal.target_date ? new Date(goal.target_date).toLocaleDateString() : "-"}
                    </p>
                    {daysOverdue > 0 && (
                      <p className="text-xs text-status-danger-600 dark:text-status-danger-400">{daysOverdue} days overdue</p>
                    )}
                  </div>
                </td>
                <td className="py-3 px-4 text-center">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusStyle.bg} ${statusStyle.text}`}>
                    {statusLabels[goal.status]}
                  </span>
                </td>
                <td className="py-3 px-4 text-right">
                  <Link
                    to={`/admin/strategic?goal=${goal.id}`}
                    className="inline-flex items-center gap-1 text-sm text-lsc-rose hover:underline"
                  >
                    <Edit2 className="w-4 h-4" />
                    Edit
                  </Link>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// Upcoming Deadlines Table
function UpcomingDeadlinesTable({ goals }: { goals: StrategicGoal[] }) {
  const { t } = useTranslation();
  if (goals.length === 0) {
    return (
      <div className="text-center py-8">
        <Calendar className="w-12 h-12 mx-auto text-lsc-dark/30 dark:text-lsc-cream/60 mb-3" />
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('strategicAnalytics.noUpcomingDeadlinesInThe')}</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b border-lsc-border dark:border-earth-700">
            <th className="text-left py-3 px-4 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Goal</th>
            <th className="text-left py-3 px-4 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Department</th>
            <th className="text-center py-3 px-4 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Progress</th>
            <th className="text-left py-3 px-4 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Target Date</th>
            <th className="text-center py-3 px-4 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Days Left</th>
          </tr>
        </thead>
        <tbody>
          {goals.map((goal) => {
            const daysRemaining = goal.target_date ? getDaysFromNow(goal.target_date) : 0;
            const urgencyColor = daysRemaining <= 7 ? "text-status-danger-600 dark:text-status-danger-400" : daysRemaining <= 14 ? "text-status-warning-600 dark:text-status-warning-400" : "text-status-success-600 dark:text-status-success-400";

            return (
              <tr key={goal.id} className="border-b border-lsc-border/50 dark:border-earth-700/50 hover:bg-lsc-cream/50 dark:hover:bg-lsc-brown/50">
                <td className="py-3 px-4">
                  <p className="font-medium text-lsc-dark dark:text-lsc-cream">{goal.title}</p>
                </td>
                <td className="py-3 px-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  {goal.department || "-"}
                </td>
                <td className="py-3 px-4">
                  <div className="flex items-center justify-center gap-2">
                    <div className="w-16 h-2 bg-lsc-cream dark:bg-lsc-brown rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${goal.progress >= 75 ? "bg-status-success-500" : goal.progress >= 50 ? "bg-lsc-rose" : "bg-status-warning-500"}`}
                        style={{ width: `${goal.progress}%` }}
                      />
                    </div>
                    <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 w-10">{goal.progress}%</span>
                  </div>
                </td>
                <td className="py-3 px-4 text-sm text-lsc-dark dark:text-lsc-cream">
                  {goal.target_date ? new Date(goal.target_date).toLocaleDateString() : "-"}
                </td>
                <td className={`py-3 px-4 text-center font-medium ${urgencyColor}`}>
                  {daysRemaining} days
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// Recent Activity Feed
function RecentActivityFeed({ updates }: { updates: ProgressUpdate[] }) {
  if (updates.length === 0) {
    return (
      <div className="text-center py-8">
        <Activity className="w-12 h-12 mx-auto text-lsc-dark/30 dark:text-lsc-cream/60 mb-3" />
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">No recent activity</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {updates.map((update) => (
        <div
          key={update.id}
          className="flex items-start gap-3 p-3 rounded-lg bg-lsc-cream/50 dark:bg-lsc-brown/50"
        >
          <div className="w-10 h-10 rounded-full bg-lsc-rose/10 flex items-center justify-center shrink-0">
            <TrendingUp className="w-5 h-5 text-lsc-rose" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
              {update.goal_title}
            </p>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              Progress updated to <span className="font-medium">{update.progress}%</span>
              {update.note && <span> - "{update.note}"</span>}
            </p>
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
              by {update.updated_by_name} on {new Date(update.created_at).toLocaleDateString()}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}

// Main Page Component
export default function StrategicAnalyticsPage() {
  const { t } = useTranslation()
  const { user } = useAuth();
  const isAdmin = user && ["admin", "super_admin", "director", "staff"].includes(user.role);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [analytics, setAnalytics] = useState<StrategicAnalytics | null>(null);
  const [_activePlan, setActivePlan] = useState<ActivePlan | null>(null);
  const [dateRange, setDateRange] = useState<"30d" | "90d" | "year" | "all">("all");
  const [refreshing, setRefreshing] = useState(false);

  const fetchData = async () => {
    try {
      setError(null);
      const [analyticsRes, planRes] = await Promise.all([
        api.get(`${API_BASE}/strategic/analytics${dateRange !== "all" ? `?range=${dateRange}` : ""}`),
        api.get(`${API_BASE}/strategic/plans/active`).catch(() => null),
      ]);
      // Transform API response to match component expectations
      const raw = analyticsRes as Record<string, unknown>;
      const statusData = (raw.goals_by_status || {}) as Record<string, number>;
      const deptArray = (raw.goals_by_department || []) as { department: string; count: number }[];
      const catArray = (raw.goals_by_category || []) as { category: string; count: number }[];
      const deptRecord: Record<string, number> = {};
      deptArray.forEach((d) => { deptRecord[d.department || "Unassigned"] = d.count; });
      const catRecord: Record<string, number> = {};
      catArray.forEach((c) => { catRecord[c.category || "Uncategorized"] = c.count; });
      const deadlines = (raw.upcoming_deadlines || []) as StrategicGoal[];
      const updates = (raw.recent_progress_updates || []) as { goal_id: number; goal_title: string; progress: number; note?: string; updated_by?: string; updated_at: string }[];
      setAnalytics({
        plan_period: (raw.plan_period as string) || "",
        overall_progress: (raw.overall_progress as number) || 0,
        goals_completed: statusData.completed || 0,
        goals_at_risk: statusData.at_risk || 0,
        goals_delayed: statusData.delayed || 0,
        goals_on_track: statusData.on_track || 0,
        goals_not_started: statusData.not_started || 0,
        total_goals: (raw.total_goals as number) || 0,
        upcoming_deadlines_count: deadlines.length,
        goals_by_status: statusData,
        goals_by_department: deptRecord,
        goals_by_category: catRecord,
        at_risk_goals: (raw.at_risk_goals || []) as StrategicGoal[],
        upcoming_deadline_goals: deadlines,
        recent_updates: updates.map((u) => ({
          id: u.goal_id,
          goal_id: u.goal_id,
          goal_title: u.goal_title,
          progress: u.progress,
          note: u.note ?? '',
          updated_by_name: u.updated_by || "System",
          created_at: u.updated_at,
        })),
      });
      setActivePlan(planRes);
    } catch (err: unknown) {
      Sentry.captureException(err instanceof Error ? err : new Error(String(err)));
      setError("Failed to load strategic analytics. Please try again.");
      toast.error(t('strategicAnalytics.failedToLoadAnalyticsData'));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    if (isAdmin) {
      fetchData();
    } else {
      setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAdmin, dateRange]);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchData();
  };

  // Access denied for non-admins
  if (!isAdmin) {
    return (
      <div className="min-h-screen bg-lsc-cream dark:bg-lsc-dark py-12 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-12">
            <Target className="w-16 h-16 mx-auto text-lsc-border mb-4" />
            <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">Staff-Only Area</h1>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">
              Strategic Analytics is only available to administrators.
            </p>
            <Link
              to="/staff"
              className="inline-flex items-center gap-2 mt-6 px-6 py-3 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose/90"
            >
              <ChevronRight className="w-5 h-5" />
              Go to Staff Dashboard
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen bg-lsc-cream dark:bg-lsc-dark py-8 px-4">
        <div className="max-w-7xl mx-auto">
          <div className="motion-safe:animate-pulse space-y-6">
            <div className="h-10 bg-lsc-white dark:bg-earth-800 rounded-lg w-64" />
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="h-28 bg-lsc-white dark:bg-earth-800 rounded-xl" />
              ))}
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="h-80 bg-lsc-white dark:bg-earth-800 rounded-xl" />
              <div className="h-80 bg-lsc-white dark:bg-earth-800 rounded-xl" />
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (error || !analytics) {
    return (
      <div className="min-h-screen bg-lsc-cream dark:bg-lsc-dark py-12 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-12">
            <AlertCircle className="w-16 h-16 mx-auto text-status-danger-500 mb-4" />
            <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">{t('strategicAnalytics.unableToLoadAnalytics')}</h1>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">
              {error || "No active strategic plan found. Please create a plan first."}
            </p>
            <div className="flex justify-center gap-4 mt-6">
              <button
                onClick={handleRefresh}
                className="inline-flex items-center gap-2 px-6 py-3 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose/90"
              >
                <RefreshCw className="w-5 h-5" />
                Retry
              </button>
              <Link
                to="/staff/admin/strategic"
                className="inline-flex items-center gap-2 px-6 py-3 border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream rounded-xl hover:bg-lsc-cream dark:hover:bg-lsc-brown"
              >
                Manage Plans
              </Link>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Empty state - no strategic plan configured
  if (!analytics || (analytics.total_goals === 0 && !analytics.plan_period)) {
    return (
      <div className="min-h-screen bg-lsc-cream dark:bg-lsc-dark py-12 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-12">
            <Target className="w-16 h-16 mx-auto text-lsc-border dark:text-earth-600 mb-4" />
            <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">No Strategic Plan Configured</h1>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-2 max-w-md mx-auto">
              Strategic analytics will appear here once a strategic plan has been created and goals have been added.
            </p>
            <div className="flex justify-center gap-4 mt-6">
              <Link
                to="/staff"
                className="inline-flex items-center gap-2 px-6 py-3 border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream rounded-xl hover:bg-lsc-cream dark:hover:bg-lsc-brown"
              >
                Back to Dashboard
              </Link>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (

    <AdminShell title="Strategic Analytics">    <div className="min-h-screen bg-lsc-cream dark:bg-lsc-dark">
      <PageContainer width="wide" className="py-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
          <div>
            <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream flex items-center gap-3">
              <BarChart3 className="w-8 h-8 text-lsc-rose" />
              Strategic Analytics
            </h1>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
              Strategic Plan {analytics.plan_period}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <select
              value={dateRange}
              onChange={(e) => setDateRange(e.target.value as typeof dateRange)}
              className="px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
            >
              <option value="30d">Last 30 days</option>
              <option value="90d">Last 90 days</option>
              <option value="year">Last year</option>
              <option value="all">All time</option>
            </select>
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className="p-2 rounded-lg bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown disabled:opacity-50"
            >
              <RefreshCw className={`w-5 h-5 ${refreshing ? "motion-safe:animate-spin" : ""}`} />
            </button>
          </div>
        </div>

        {/* Summary Cards with Circular Progress */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {/* Overall Progress - Special card with circular indicator */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-5 shadow-sm border border-lsc-border dark:border-earth-700 sm:col-span-2 lg:col-span-1">
            <div className="flex items-center gap-4">
              <CircularProgress value={analytics.overall_progress} size={80} strokeWidth={8} />
              <div>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Overall Progress</p>
                <p className="text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
                  {analytics.total_goals} Goals
                </p>
              </div>
            </div>
          </div>

          <SummaryCard
            title="Goals Completed"
            value={analytics.goals_completed}
            icon={CheckCircle2}
            color="success"
            subtitle={`${Math.round((analytics.goals_completed / (analytics.total_goals || 1)) * 100)}% of total`}
          />

          <SummaryCard
            title="Goals At Risk"
            value={analytics.goals_at_risk + analytics.goals_delayed}
            icon={AlertTriangle}
            color="yellow"
            subtitle={`${analytics.goals_delayed} delayed, ${analytics.goals_at_risk} at risk`}
          />

          <SummaryCard
            title="Upcoming Deadlines"
            value={analytics.upcoming_deadlines_count}
            icon={Clock}
            color="accent"
            subtitle="Next 30 days"
          />
        </div>

        {/* Charts Section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {/* Progress Over Time */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm border border-lsc-border dark:border-earth-700">
            <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-lsc-rose" />
              Progress Over Time
            </h2>
            <ProgressLineChart data={[]} />
          </div>

          {/* Goals by Status */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm border border-lsc-border dark:border-earth-700">
            <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
              <Target className="w-5 h-5 text-lsc-rose" />
              Goals by Status
            </h2>
            <StatusDonutChart data={analytics.goals_by_status} />
          </div>

          {/* Goals by Department */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm border border-lsc-border dark:border-earth-700">
            <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
              <Building2 className="w-5 h-5 text-lsc-rose" />
              Goals by Department
            </h2>
            <HorizontalBarChart data={analytics.goals_by_department} />
          </div>

          {/* Goals by Category */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm border border-lsc-border dark:border-earth-700">
            <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
              <Users className="w-5 h-5 text-lsc-rose" />
              Goals by Category
            </h2>
            <HorizontalBarChart data={analytics.goals_by_category} />
          </div>
        </div>

        {/* At-Risk Goals Table */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 mb-8">
          <div className="px-6 py-4 border-b border-lsc-border dark:border-earth-700">
            <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-status-warning-500" />
              At-Risk & Delayed Goals
            </h2>
          </div>
          <AtRiskGoalsTable goals={analytics.at_risk_goals} />
        </div>

        {/* Upcoming Deadlines Table */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 mb-8">
          <div className="px-6 py-4 border-b border-lsc-border dark:border-earth-700">
            <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
              <Calendar className="w-5 h-5 text-earth-600" />
              Upcoming Deadlines (Next 30 Days)
            </h2>
          </div>
          <UpcomingDeadlinesTable goals={analytics.upcoming_deadline_goals} />
        </div>

        {/* Recent Activity Feed */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700">
          <div className="px-6 py-4 border-b border-lsc-border dark:border-earth-700">
            <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
              <Activity className="w-5 h-5 text-lsc-rose" />
              Recent Activity
            </h2>
          </div>
          <div className="p-6">
            <RecentActivityFeed updates={analytics.recent_updates} />
          </div>
        </div>
      </PageContainer>
    </div>
  </AdminShell>
  );
}