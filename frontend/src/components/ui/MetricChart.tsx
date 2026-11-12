/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from 'react'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts'

export interface MetricChartProps {
  title: string
  icon?: React.ElementType
  data: Record<string, unknown>[]
  type?: 'line' | 'bar'
  dataKeys: {
    key: string
    color?: string
    name?: string
  }[]
  xAxisKey?: string
  height?: number
  className?: string
}

const defaultColors = ['#9e5a2d', '#3b82f6', '#22c55e', '#ef4444', '#a855f7']

export function MetricChart({
  title,
  icon: Icon,
  data,
  type = 'line',
  dataKeys,
  xAxisKey = 'name',
  height = 300,
  className = '',
}: MetricChartProps) {
  const ChartComponent = type === 'bar' ? BarChart : LineChart

  return (
    <div className={`bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm p-6 border border-lsc-border dark:border-earth-700 ${className}`}>
      <div className="flex items-center gap-2 mb-4">
        {Icon && <Icon className="w-5 h-5 text-lsc-rose" />}
        <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">{title}</h3>
      </div>
      <ResponsiveContainer width="100%" height={height}>
        <ChartComponent data={data}>
          <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
          <XAxis
            dataKey={xAxisKey}
            tick={{ fontSize: '0.75rem' }}
            className="text-lsc-dark/70 dark:text-lsc-cream/70"
          />
          <YAxis
            tick={{ fontSize: '0.75rem' }}
            className="text-lsc-dark/70 dark:text-lsc-cream/70"
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'var(--tooltip-bg, #fff)',
              border: '1px solid var(--tooltip-border, #e5e7eb)',
              borderRadius: '8px',
              fontSize: '12px',
            }}
          />
          {dataKeys.length > 1 && <Legend />}
          {dataKeys.map((dk, index) =>
            type === 'bar' ? (
              <Bar
                key={dk.key}
                dataKey={dk.key}
                fill={dk.color ?? defaultColors[index % defaultColors.length] ?? '#6b7280'}
                name={dk.name || dk.key}
                radius={[4, 4, 0, 0]}
              />
            ) : (
              <Line
                key={dk.key}
                type="monotone"
                dataKey={dk.key}
                stroke={dk.color ?? defaultColors[index % defaultColors.length] ?? '#6b7280'}
                name={dk.name || dk.key}
                strokeWidth={2}
                dot={false}
              />
            )
          )}
        </ChartComponent>
      </ResponsiveContainer>
    </div>
  )
}
