/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import {
  BookOpen, Users, TrendingUp, Star, UserCheck, Layers,
} from 'lucide-react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell, AreaChart, Area,
} from 'recharts'
import { AnimatedCounter, StaggeredList } from './DemoAnimations'

export function DashboardScene() {
  const metrics = [
    { label: 'Checkouts (30d)', value: 4127, trend: 12, icon: BookOpen, color: 'blue' as const },
    { label: 'Active Patrons', value: 2847, trend: 8, icon: Users, color: 'green' as const },
    { label: 'New Registrations', value: 64, trend: 23, icon: UserCheck, color: 'purple' as const },
    { label: 'Program Attendance', value: 892, trend: 15, icon: Star, color: 'orange' as const },
  ]

  const collectionData = [
    { category: 'Fiction', items: 8420, checkouts: 12840, turnover: 1.52 },
    { category: 'Non-Fiction', items: 6310, checkouts: 5670, turnover: 0.90 },
    { category: "Children's", items: 5890, checkouts: 9240, turnover: 1.57 },
    { category: 'YA', items: 3210, checkouts: 4830, turnover: 1.50 },
    { category: 'DVDs/Media', items: 4120, checkouts: 6180, turnover: 1.50 },
    { category: 'Digital', items: 3500, checkouts: 9533, turnover: 2.72 },
  ]

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StaggeredList staggerMs={100}>
          {metrics.map((m) => {
            const colorMap = { blue: 'bg-earth-100 text-lsc-rose dark:text-lsc-rose-light dark:bg-earth-800/30 dark:text-lsc-rose-light', green: 'bg-status-success-100 text-status-success-600 dark:bg-status-success-900/30 dark:text-status-success-400', purple: 'bg-category-100 text-category-600 dark:bg-category-900/30 dark:text-category-400', orange: 'bg-status-warning-100 text-status-warning-600 dark:bg-status-warning-900/30 dark:text-status-warning-400' }
            return (
              <div key={m.label} className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm p-4 border border-lsc-border dark:border-earth-700 hover:shadow-md hover:-translate-y-0.5 transition-all">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{m.label}</p>
                    <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream mt-1">
                      <AnimatedCounter end={m.value} />
                    </p>
                    <p className="text-xs text-status-success-600 dark:text-status-success-400 mt-0.5">+{m.trend}% vs last month</p>
                  </div>
                  <div className={`p-2.5 rounded-full ${colorMap[m.color]}`}>
                    <m.icon className="w-5 h-5" />
                  </div>
                </div>
              </div>
            )
          })}
        </StaggeredList>
      </div>

      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 overflow-hidden">
        <div className="p-4 border-b border-lsc-border dark:border-earth-700">
          <h4 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
            <Layers className="w-4 h-4 text-emerald-600" />
            Collection Performance by Category
          </h4>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-earth-50 dark:bg-earth-700/50">
              <tr>
                <th className="text-left p-3 text-lsc-dark/70 dark:text-lsc-cream/70 font-medium">Category</th>
                <th className="text-right p-3 text-lsc-dark/70 dark:text-lsc-cream/70 font-medium">Items</th>
                <th className="text-right p-3 text-lsc-dark/70 dark:text-lsc-cream/70 font-medium">Checkouts (YTD)</th>
                <th className="text-right p-3 text-lsc-dark/70 dark:text-lsc-cream/70 font-medium">Turnover Rate</th>
                <th className="text-right p-3 text-lsc-dark/70 dark:text-lsc-cream/70 font-medium">Health</th>
              </tr>
            </thead>
            <tbody>
              {collectionData.map((row) => (
                <tr key={row.category} className="border-t border-earth-100 dark:border-earth-700">
                  <td className="p-3 text-lsc-dark dark:text-lsc-cream font-medium">{row.category}</td>
                  <td className="p-3 text-right text-lsc-dark/70 dark:text-lsc-cream/70">{row.items.toLocaleString()}</td>
                  <td className="p-3 text-right text-lsc-dark/70 dark:text-lsc-cream/70">{row.checkouts.toLocaleString()}</td>
                  <td className="p-3 text-right text-lsc-dark/70 dark:text-lsc-cream/70">{row.turnover.toFixed(2)}</td>
                  <td className="p-3 text-right">
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
                      row.turnover >= 1.5
                        ? 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900/30 dark:text-status-success-400'
                        : row.turnover >= 1.0
                        ? 'bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900/30 dark:text-status-warning-400'
                        : 'bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900/30 dark:text-status-danger-400'
                    }`}>
                      {row.turnover >= 1.5 ? 'Excellent' : row.turnover >= 1.0 ? 'Good' : 'Review'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg p-4 border border-lsc-border dark:border-earth-700">
        <h4 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light" />
          Monthly Checkouts Trend
        </h4>
        <ResponsiveContainer width="100%" height={180}>
          <BarChart data={[
            { month: 'Mar', checkouts: 3200 }, { month: 'Apr', checkouts: 3450 },
            { month: 'May', checkouts: 3100 }, { month: 'Jun', checkouts: 3800 },
            { month: 'Jul', checkouts: 4050 }, { month: 'Aug', checkouts: 3900 },
            { month: 'Sep', checkouts: 4200 }, { month: 'Oct', checkouts: 3750 },
            { month: 'Nov', checkouts: 4127 }, { month: 'Dec', checkouts: 3950 },
            { month: 'Jan', checkouts: 4300 }, { month: 'Feb', checkouts: 4500 },
          ]} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" vertical={false} />
            <XAxis dataKey="month" tick={{ fontSize: '0.6875rem', fill: '#9ca3af' }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: '0.6875rem', fill: '#9ca3af' }} axisLine={false} tickLine={false} width={40} />
            <Tooltip
              contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb', fontSize: '0.75rem' }}
              formatter={(value) => [Number(value).toLocaleString(), 'Checkouts']}
            />
            <Bar dataKey="checkouts" radius={[4, 4, 0, 0]} animationDuration={1500}>
              {[3200, 3450, 3100, 3800, 4050, 3900, 4200, 3750, 4127, 3950, 4300, 4500].map((_, i) => (
                <Cell key={i} fill={i === 11 ? '#f97316' : '#93c5fd'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg p-4 border border-lsc-border dark:border-earth-700">
        <h4 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
          <Users className="w-4 h-4 text-status-success-600" />
          Active Patron Growth
        </h4>
        <ResponsiveContainer width="100%" height={140}>
          <AreaChart data={[
            { month: 'Mar', patrons: 2410 }, { month: 'Apr', patrons: 2455 },
            { month: 'May', patrons: 2490 }, { month: 'Jun', patrons: 2540 },
            { month: 'Jul', patrons: 2610 }, { month: 'Aug', patrons: 2650 },
            { month: 'Sep', patrons: 2695 }, { month: 'Oct', patrons: 2720 },
            { month: 'Nov', patrons: 2760 }, { month: 'Dec', patrons: 2790 },
            { month: 'Jan', patrons: 2820 }, { month: 'Feb', patrons: 2847 },
          ]} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
            <defs>
              <linearGradient id="patronGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis dataKey="month" tick={{ fontSize: '0.6875rem', fill: '#9ca3af' }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: '0.6875rem', fill: '#9ca3af' }} axisLine={false} tickLine={false} width={40} domain={[2300, 'auto']} />
            <Tooltip
              contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb', fontSize: '0.75rem' }}
              formatter={(value) => [Number(value).toLocaleString(), 'Active Patrons']}
            />
            <Area type="monotone" dataKey="patrons" stroke="#10b981" strokeWidth={2} fill="url(#patronGradient)" animationDuration={2000} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
