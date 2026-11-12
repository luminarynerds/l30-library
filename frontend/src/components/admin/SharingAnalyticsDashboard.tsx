/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Staff Analytics Dashboard - Social Sharing Metrics
 * Displays comprehensive sharing analytics with charts, metrics, and filters
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import clsx from 'clsx';
import { AlertCircle, TrendingUp, TrendingDown, Users, Share2, Download, Filter, type LucideIcon } from 'lucide-react';

import {
  getSharingDashboard,
  SharingDashboardResponse,
  getPlatformColor,
  getPlatformDisplayName,
  formatDate,
  ResourceType,
  RESOURCE_TYPE_LABELS,
} from '../../api/sharing-analytics-api';
import LoadingSpinner from '../LoadingSpinner';
import { AccessibleChartWrapper } from '../charts/AccessibleChartWrapper';

interface DateRange {
  label: string;
  days: number;
}

const DATE_RANGES: DateRange[] = [
  { label: 'Last 7 days', days: 7 },
  { label: 'Last 30 days', days: 30 },
  { label: 'Last 60 days', days: 60 },
  { label: 'Last 90 days', days: 90 },
  { label: 'Last 180 days', days: 180 },
  { label: 'Last year', days: 365 },
];

const ALL_RESOURCE_TYPES: ResourceType[] = ['book', 'event', 'reading_list', 'author_profile', 'staff_pick'];

const RESOURCE_TYPE_COLORS: Record<string, string> = {
  book: '#6366F1',
  event: '#10B981',
  reading_list: '#F59E0B',
  author_profile: '#EC4899',
  staff_pick: '#8B5CF6',
};

function getResourceTypeDisplayName(type: string): string {
  return RESOURCE_TYPE_LABELS[type as ResourceType] || type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
}

const SharingAnalyticsDashboard: React.FC = () => {
  const [selectedDays, setSelectedDays] = useState(30);
  const [selectedResourceTypes, setSelectedResourceTypes] = useState<ResourceType[]>([]);
  const [showResourceFilter, setShowResourceFilter] = useState(false);
  const [isDarkMode, setIsDarkMode] = useState(() =>
    typeof document !== 'undefined' ? document.documentElement.classList.contains('dark') : false
  );

  // Detect system dark mode preference
  useEffect(() => {
    const htmlElement = document.documentElement;
    const observer = new MutationObserver(() => {
      setIsDarkMode(htmlElement.classList.contains('dark'));
    });

    observer.observe(htmlElement, { attributes: true, attributeFilter: ['class'] });
    return () => observer.disconnect();
  }, []);

  // Fetch dashboard data
  const { data, isLoading, error, refetch } = useQuery<SharingDashboardResponse>({
    queryKey: ['sharing-analytics', selectedDays, selectedResourceTypes],
    queryFn: () => getSharingDashboard({
      days: selectedDays,
      ...(selectedResourceTypes.length > 0 ? { resourceTypes: selectedResourceTypes } : {}),
    }),
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  });

  const toggleResourceType = (type: ResourceType) => {
    setSelectedResourceTypes(prev =>
      prev.includes(type)
        ? prev.filter(t => t !== type)
        : [...prev, type]
    );
  };

  const clearResourceFilter = () => {
    setSelectedResourceTypes([]);
  };

  // CSV export
  const exportCSV = useCallback(() => {
    if (!data) return;

    const rows: string[][] = [];

    // Summary section
    rows.push(['Sharing Analytics Summary']);
    rows.push(['Metric', 'Value']);
    rows.push(['Total Shares', String(data.total_shares)]);
    rows.push(['Unique Sharers', String(data.unique_sharers)]);
    rows.push(['Avg Shares/User', String(data.avg_shares_per_user)]);
    rows.push(['Top Platform', getPlatformDisplayName(data.top_platform)]);
    rows.push(['Top Platform %', `${data.top_platform_percentage.toFixed(1)}%`]);
    rows.push([]);

    // Platform breakdown
    rows.push(['Platform Breakdown']);
    rows.push(['Platform', 'Shares', 'Percentage']);
    data.platform_breakdown.forEach(p => {
      rows.push([getPlatformDisplayName(p.platform), String(p.share_count), `${p.percentage.toFixed(1)}%`]);
    });
    rows.push([]);

    // Top shared resources
    rows.push(['Top Shared Resources']);
    rows.push(['Title', 'Type', 'Author', 'Shares']);
    data.top_shared_resources.forEach(r => {
      rows.push([r.title, r.resource_type, r.author || '', String(r.share_count)]);
    });
    rows.push([]);

    // Top sharers
    rows.push(['Top Active Sharers']);
    rows.push(['Name', 'Email', 'Favorite Platform', 'Total Shares']);
    data.top_sharers.forEach(s => {
      rows.push([s.user_name, s.email, s.favorite_platform ? getPlatformDisplayName(s.favorite_platform) : '', String(s.total_shares)]);
    });
    rows.push([]);

    // Trends
    rows.push(['Share Trends']);
    rows.push(['Date', 'Total Shares', 'Unique Sharers']);
    data.share_trends.forEach(t => {
      rows.push([t.date, String(t.total_shares), String(t.unique_sharers)]);
    });

    const csvContent = rows.map(row =>
      row.map(cell => `"${cell.replace(/"/g, '""')}"`).join(',')
    ).join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `sharing-analytics-${selectedDays}d-${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }, [data, selectedDays]);

  const textColor = isDarkMode ? '#FFF4E6' : '#1F2937';
  const gridColor = isDarkMode ? '#523F2F' : '#E5E7EB';
  const borderColor = isDarkMode ? '#523F2F' : '#E5E7EB';

  if (error) {
    return (
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-6">
        <div className="flex items-start gap-4 p-4 bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-lg">
          <AlertCircle className="w-5 h-5 text-status-danger-600 dark:text-status-danger-400 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-semibold text-sm text-status-danger-900 dark:text-status-danger-200">Error Loading Data</h3>
            <p className="text-sm mt-1 text-status-danger-800 dark:text-status-danger-300">
              {error instanceof Error ? error.message : 'Failed to load sharing analytics'}
            </p>
            <button
              onClick={() => refetch()}
              className="mt-3 px-3 py-2 text-xs font-medium rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 transition-colors"
            >
              Try Again
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (isLoading || !data) {
    return <LoadingSpinner />;
  }

  // Build resource type breakdown from top_shared_resources
  const resourceTypeBreakdown = data.top_shared_resources.reduce<Record<string, number>>((acc, r) => {
    acc[r.resource_type] = (acc[r.resource_type] || 0) + r.share_count;
    return acc;
  }, {});
  const resourceTypeChartData = Object.entries(resourceTypeBreakdown).map(([type, count]) => ({
    type: getResourceTypeDisplayName(type),
    rawType: type,
    shares: count,
  })).sort((a, b) => b.shares - a.shares);

  return (
    <div className="space-y-6">
      {/* Header with Title and Filters */}
      <div className="flex flex-col gap-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
              Social Sharing Analytics
            </h1>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
              Track and analyze social media sharing metrics across the library
            </p>
          </div>

          <div className="flex items-center gap-2">
            {/* Resource Type Filter Toggle */}
            <button
              onClick={() => setShowResourceFilter(!showResourceFilter)}
              className={clsx(
                'flex items-center gap-2 px-3 py-2 text-xs font-semibold rounded-lg transition-colors border',
                selectedResourceTypes.length > 0
                  ? 'bg-lsc-rose/10 border-lsc-rose text-lsc-rose'
                  : 'bg-lsc-white dark:bg-earth-800 border-lsc-border dark:border-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 hover:border-lsc-rose'
              )}
            >
              <Filter className="w-4 h-4" />
              {selectedResourceTypes.length > 0
                ? `${selectedResourceTypes.length} type${selectedResourceTypes.length > 1 ? 's' : ''}`
                : 'Filter'}
            </button>

            {/* CSV Export */}
            <button
              onClick={exportCSV}
              className="flex items-center gap-2 px-3 py-2 text-xs font-semibold rounded-lg transition-colors border bg-lsc-white dark:bg-earth-800 border-lsc-border dark:border-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 hover:border-lsc-rose hover:text-lsc-rose"
              title="Export as CSV"
            >
              <Download className="w-4 h-4" />
              Export
            </button>
          </div>
        </div>

        {/* Resource Type Filter Panel */}
        {showResourceFilter && (
          <div className="flex flex-wrap items-center gap-2 p-3 bg-lsc-cream/50 dark:bg-earth-700/50 rounded-lg border border-lsc-border dark:border-earth-700">
            <span className="text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wider mr-1">
              Content Type:
            </span>
            {ALL_RESOURCE_TYPES.map(type => (
              <button
                key={type}
                onClick={() => toggleResourceType(type)}
                className={clsx(
                  'px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors',
                  selectedResourceTypes.includes(type)
                    ? 'bg-lsc-rose text-white'
                    : 'bg-lsc-white dark:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-rose/10'
                )}
              >
                {RESOURCE_TYPE_LABELS[type]}
              </button>
            ))}
            {selectedResourceTypes.length > 0 && (
              <button
                onClick={clearResourceFilter}
                className="px-3 py-1.5 text-xs font-semibold rounded-lg text-status-danger-600 dark:text-status-danger-400 hover:bg-status-danger-50 dark:hover:bg-status-danger-900/20 transition-colors"
              >
                Clear
              </button>
            )}
          </div>
        )}

        {/* Date Range Selector */}
        <div className="w-full overflow-x-auto">
          <div className="flex items-center gap-2 p-1 bg-lsc-cream dark:bg-earth-800 rounded-xl min-w-max">
            {DATE_RANGES.map((range) => (
              <button
                key={range.days}
                onClick={() => setSelectedDays(range.days)}
                className={clsx(
                  'px-4 py-2 text-xs font-semibold rounded-lg whitespace-nowrap transition-colors',
                  selectedDays === range.days
                    ? 'bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream shadow-sm'
                    : 'text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream'
                )}
              >
                {range.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Key Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Total Shares"
          value={data.total_shares}
          icon={Share2}
          {...(data.shares_trend ? { trend: data.shares_trend } : {})}
          isDarkMode={isDarkMode}
        />
        <MetricCard
          title="Unique Sharers"
          value={data.unique_sharers}
          icon={Users}
          isDarkMode={isDarkMode}
        />
        <MetricCard
          title="Avg Shares/User"
          value={data.avg_shares_per_user.toFixed(2)}
          icon={TrendingUp}
          isDarkMode={isDarkMode}
        />
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm border border-lsc-border dark:border-earth-700">
          <p className="text-xs font-semibold uppercase tracking-widest text-lsc-dark/70 dark:text-lsc-cream/70">
            Top Platform
          </p>
          <p className="text-2xl font-bold mt-2 text-lsc-dark dark:text-lsc-cream">
            {getPlatformDisplayName(data.top_platform)}
          </p>
          <p className="text-sm mt-2 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">
            {data.top_platform_percentage.toFixed(1)}% of total shares
          </p>
        </div>
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Share Trends Line Chart */}
        <div className="lg:col-span-2 bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm border border-lsc-border dark:border-earth-700">
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
            Share Trends
          </h2>
          <AccessibleChartWrapper
            title="Share Trends"
            description="Line chart showing total shares and unique sharers over the selected time period."
            data={data.share_trends.map(t => ({
              date: formatDate(t.date),
              total_shares: t.total_shares,
              unique_sharers: t.unique_sharers,
            }))}
            columns={[
              { key: 'date', label: 'Date' },
              { key: 'total_shares', label: 'Total Shares' },
              { key: 'unique_sharers', label: 'Unique Sharers' },
            ]}
          >
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={data.share_trends}>
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke={gridColor}
                  opacity={0.3}
                />
                <XAxis
                  dataKey="date"
                  stroke={textColor}
                  tickFormatter={(date) => formatDate(date)}
                  tick={{ fontSize: '0.75rem' }}
                />
                <YAxis stroke={textColor} tick={{ fontSize: '0.75rem' }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: isDarkMode ? '#1F2937' : '#FFFFFF',
                    border: `1px solid ${borderColor}`,
                    borderRadius: '0.5rem',
                    color: textColor,
                  }}
                  formatter={(value) => [value, 'Shares']}
                  labelFormatter={(date) => `Date: ${formatDate(String(date))}`}
                />
                <Legend wrapperStyle={{ color: textColor }} />
                {/* Total Shares — solid line, circle dots */}
                <Line
                  type="monotone"
                  dataKey="total_shares"
                  stroke="#6366F1"
                  strokeWidth={2}
                  dot={{ r: 4 }}
                  activeDot={{ r: 6 }}
                  name="Total Shares"
                />
                {/* Unique Sharers — dashed line, square dots for non-color differentiation (WCAG 1.4.1) */}
                <Line
                  type="monotone"
                  dataKey="unique_sharers"
                  stroke="#10B981"
                  strokeWidth={2}
                  strokeDasharray="5 5"
                  dot={{ r: 4, strokeWidth: 2, fill: '#10B981', stroke: '#10B981' }}
                  activeDot={{ r: 6 }}
                  name="Unique Sharers"
                />
              </LineChart>
            </ResponsiveContainer>
          </AccessibleChartWrapper>
        </div>

        {/* Platform Breakdown Pie Chart */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm border border-lsc-border dark:border-earth-700">
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
            Platform Breakdown
          </h2>
          <AccessibleChartWrapper
            title="Platform Breakdown"
            description="Pie chart showing share distribution across social media platforms."
            data={data.platform_breakdown.map(p => ({
              platform: getPlatformDisplayName(p.platform),
              share_count: p.share_count,
              percentage: p.percentage.toFixed(1),
            }))}
            columns={[
              { key: 'platform', label: 'Platform' },
              { key: 'share_count', label: 'Shares' },
              { key: 'percentage', label: 'Percentage (%)' },
            ]}
          >
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={data.platform_breakdown}
                  dataKey="share_count"
                  nameKey="platform"
                  cx="50%"
                  cy="50%"
                  outerRadius={100}
                  // Percentage labels provide a non-color channel for differentiation (WCAG 1.4.1)
                  // eslint-disable-next-line @typescript-eslint/no-explicit-any
                  label={({ platform, percentage }: Record<string, any>) =>
                    `${getPlatformDisplayName(platform)} ${percentage.toFixed(0)}%`
                  }
                >
                  {data.platform_breakdown.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={getPlatformColor(entry.platform)}
                    />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: isDarkMode ? '#1F2937' : '#FFFFFF',
                    border: `1px solid ${borderColor}`,
                    borderRadius: '0.5rem',
                    color: textColor,
                  }}
                  formatter={(value) => [value, 'Shares']}
                />
              </PieChart>
            </ResponsiveContainer>
          </AccessibleChartWrapper>
        </div>
      </div>

      {/* Resource Type Breakdown Bar Chart */}
      {resourceTypeChartData.length > 1 && (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm border border-lsc-border dark:border-earth-700">
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
            Shares by Content Type
          </h2>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={resourceTypeChartData} layout="vertical">
              <CartesianGrid
                strokeDasharray="3 3"
                stroke={gridColor}
                opacity={0.3}
                horizontal={false}
              />
              <XAxis type="number" stroke={textColor} tick={{ fontSize: '0.75rem' }} />
              <YAxis
                dataKey="type"
                type="category"
                stroke={textColor}
                tick={{ fontSize: '0.75rem' }}
                width={120}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: isDarkMode ? '#1F2937' : '#FFFFFF',
                  border: `1px solid ${borderColor}`,
                  borderRadius: '0.5rem',
                  color: textColor,
                }}
                formatter={(value) => [value, 'Shares']}
              />
              <Bar dataKey="shares" radius={[0, 4, 4, 0]}>
                {resourceTypeChartData.map((entry) => (
                  <Cell
                    key={entry.rawType}
                    fill={RESOURCE_TYPE_COLORS[entry.rawType] || '#6B7280'}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Top Shared Resources */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm border border-lsc-border dark:border-earth-700">
        <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
          Top Shared Resources
        </h2>
        {data.top_shared_resources.length === 0 ? (
          <p className="text-center py-8 text-lsc-dark/70 dark:text-lsc-cream/60">
            No shared resources found for the selected period{selectedResourceTypes.length > 0 ? ' and filters' : ''}.
          </p>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-lsc-border dark:border-earth-700">
            <table className="w-full text-sm">
              <thead className="bg-lsc-cream dark:bg-earth-700">
                <tr>
                  <th className="text-left py-3 px-4 font-semibold text-lsc-dark dark:text-lsc-cream">
                    Title
                  </th>
                  <th className="text-left py-3 px-4 font-semibold text-lsc-dark dark:text-lsc-cream">
                    Type
                  </th>
                  <th className="text-left py-3 px-4 font-semibold text-lsc-dark dark:text-lsc-cream">
                    Author
                  </th>
                  <th className="text-right py-3 px-4 font-semibold text-lsc-dark dark:text-lsc-cream">
                    Shares
                  </th>
                </tr>
              </thead>
              <tbody>
                {data.top_shared_resources.map((resource, index) => (
                  <tr
                    key={`${resource.resource_type}-${resource.resource_id}`}
                    className={clsx(
                      'transition-colors duration-150 border-b border-lsc-border dark:border-earth-700',
                      index % 2 === 0
                        ? 'bg-lsc-white dark:bg-earth-800'
                        : 'bg-lsc-cream/50 dark:bg-earth-700/50'
                    )}
                  >
                    <td className="py-3 px-4 font-medium text-lsc-dark dark:text-lsc-cream">
                      {resource.title}
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className="px-2 py-1 rounded-full text-xs font-semibold"
                        style={{
                          backgroundColor: `${RESOURCE_TYPE_COLORS[resource.resource_type] || '#6B7280'}20`,
                          color: RESOURCE_TYPE_COLORS[resource.resource_type] || '#6B7280',
                        }}
                      >
                        {getResourceTypeDisplayName(resource.resource_type)}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-lsc-dark/70 dark:text-lsc-cream/70">
                      {resource.author || '\u2014'}
                    </td>
                    <td className="py-3 px-4 text-right font-bold text-lsc-rose dark:text-lsc-rose-light">
                      {resource.share_count}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Top Sharers */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm border border-lsc-border dark:border-earth-700">
        <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
          Top Active Sharers
        </h2>
        {data.top_sharers.length === 0 ? (
          <p className="text-center py-8 text-lsc-dark/70 dark:text-lsc-cream/60">
            No active sharers found for the selected period.
          </p>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-lsc-border dark:border-earth-700">
            <table className="w-full text-sm">
              <thead className="bg-lsc-cream dark:bg-earth-700">
                <tr>
                  <th className="text-left py-3 px-4 font-semibold text-lsc-dark dark:text-lsc-cream">
                    Name
                  </th>
                  <th className="text-left py-3 px-4 font-semibold text-lsc-dark dark:text-lsc-cream">
                    Email
                  </th>
                  <th className="text-left py-3 px-4 font-semibold text-lsc-dark dark:text-lsc-cream">
                    Favorite Platform
                  </th>
                  <th className="text-right py-3 px-4 font-semibold text-lsc-dark dark:text-lsc-cream">
                    Total Shares
                  </th>
                </tr>
              </thead>
              <tbody>
                {data.top_sharers.map((sharer, index) => (
                  <tr
                    key={sharer.user_id}
                    className={clsx(
                      'transition-colors duration-150 border-b border-lsc-border dark:border-earth-700',
                      index % 2 === 0
                        ? 'bg-lsc-white dark:bg-earth-800'
                        : 'bg-lsc-cream/50 dark:bg-earth-700/50'
                    )}
                  >
                    <td className="py-3 px-4 font-medium text-lsc-dark dark:text-lsc-cream">
                      {sharer.user_name}
                    </td>
                    <td className="py-3 px-4 text-lsc-dark/70 dark:text-lsc-cream/70">
                      {sharer.email}
                    </td>
                    <td className="py-3 px-4">
                      {sharer.favorite_platform ? (
                        <span className="px-2 py-1 rounded-full text-xs font-semibold bg-lsc-rose/10 text-lsc-rose dark:bg-lsc-rose/20">
                          {getPlatformDisplayName(sharer.favorite_platform)}
                        </span>
                      ) : (
                        <span className="text-lsc-dark/70 dark:text-lsc-cream/70">{'\u2014'}</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-right font-bold text-lsc-rose dark:text-lsc-rose-light">
                      {sharer.total_shares}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Metadata Footer */}
      <div className="bg-lsc-cream/50 dark:bg-earth-700/50 border border-lsc-border dark:border-earth-700 rounded-lg py-3 px-4 text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70">
        <span>Last updated: {new Date(data.metadata.generated_at).toLocaleString()} (UTC)</span>
        {data.metadata.cached && <span className="ml-3 opacity-75">&bull; Cached data</span>}
        {selectedResourceTypes.length > 0 && (
          <span className="ml-3 opacity-75">
            &bull; Filtered: {selectedResourceTypes.map(t => RESOURCE_TYPE_LABELS[t]).join(', ')}
          </span>
        )}
      </div>
    </div>
  );
};

interface MetricCardProps {
  title: string;
  value: string | number;
  icon?: LucideIcon;
  trend?: {
    direction: 'up' | 'down' | 'stable';
    change_percentage: number;
  };
  isDarkMode: boolean;
}

const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  icon: Icon,
  trend,
  isDarkMode,
}) => {
  const getTrendColor = (direction: string) => {
    switch (direction) {
      case 'up':
        return isDarkMode ? 'text-status-success-400' : 'text-status-success-600';
      case 'down':
        return isDarkMode ? 'text-status-danger-400' : 'text-status-danger-600';
      default:
        return isDarkMode ? 'text-lsc-cream/60' : 'text-lsc-dark/70 dark:text-lsc-cream/60';
    }
  };

  const getTrendIcon = (direction: string) => {
    switch (direction) {
      case 'up':
        return <TrendingUp className="w-4 h-4" />;
      case 'down':
        return <TrendingDown className="w-4 h-4" />;
      default:
        return null;
    }
  };

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm border border-lsc-border dark:border-earth-700">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-xs font-semibold uppercase tracking-widest text-lsc-dark/70 dark:text-lsc-cream/70">
            {title}
          </p>
          <p className="text-2xl font-bold mt-2 text-lsc-dark dark:text-lsc-cream">
            {typeof value === 'number' && value > 999
              ? `${(value / 1000).toFixed(1)}K`
              : value}
          </p>
          {trend && (
            <div className={clsx(
              'text-xs mt-2 flex items-center gap-1 font-semibold',
              getTrendColor(trend.direction)
            )}>
              {getTrendIcon(trend.direction)}
              <span>
                {trend.direction === 'stable' ? 'Stable' : ''}
                {trend.direction === 'up' && '+'}
                {trend.direction !== 'stable' && `${trend.change_percentage}%`}
              </span>
            </div>
          )}
        </div>
        {Icon && (
          <div className="p-2 rounded-lg bg-lsc-rose/10 dark:bg-lsc-rose/20 ml-3">
            <Icon className="w-5 h-5 text-lsc-rose" />
          </div>
        )}
      </div>
    </div>
  );
};

export default SharingAnalyticsDashboard;
