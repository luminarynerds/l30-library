/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useMemo } from 'react'
import { useThemeToggle } from './useThemeToggle'

export interface ChartColorPalette {
  // Primary chart colors (for data series) - tuple type for proper typing
  primary: readonly [string, string, string, string, string, string, string, string]
  // Grid and axis colors
  grid: string
  axis: string
  // Tooltip styles
  tooltip: {
    background: string
    border: string
    text: string
  }
  // Status colors
  status: {
    success: string
    warning: string
    danger: string
    info: string
  }
  // Semantic colors for specific use cases
  orange: string
  brown: string
  teal: string
  coral: string
  darkTeal: string
  darkBlue: string
}

export function getColor(colors: readonly string[], index: number): string {
  return colors[index % colors.length] ?? colors[0] ?? '#7A4040'
}

// Light mode colors
// Series ramp note (colorblind check 2026-07-06): adjacent entries alternate
// lightness and warm/cool so series stay distinguishable without hue vision.
// The old ramp had two near-black entries (#3A3835 / #2D2D2A) and a stale
// mislabeled "lsc-rose" (#7C6545, a brown); the rose entries now use the
// real light-mode accent values.
const LIGHT_COLORS: ChartColorPalette = {
  primary: [
    '#7A4040', // brand rose (light-mode accent)
    '#3A3835', // dark warm brown
    '#B88080', // pale rose (brand 300, light-mode value)
    '#6E8A80', // muted teal
    '#A88B50', // amber-600
    '#C97B5A', // kids default
    '#4A6B5A', // staff default
    '#5270A0', // teen dark
  ] as const,
  grid: '#ECEAE8',
  axis: '#6B6762',
  tooltip: {
    background: '#FAFAF8',
    border: '#EDECEB',
    text: '#2D2D2A',
  },
  status: {
    success: '#3A5A48',
    warning: '#A88B50',
    danger: '#A86040',
    info: '#5270A0',
  },
  orange: '#7C6545',
  brown: '#3A3835',
  teal: '#6E8A80',
  coral: '#C97B5A',
  darkTeal: '#4A6B5A',
  darkBlue: '#5270A0',
}

// Dark mode colors - adjusted for better visibility
// (Same colorblind note as LIGHT_COLORS: the old first two entries were two
// near-identical warm browns; entry 0 is now the dark-mode rose accent.)
const DARK_COLORS: ChartColorPalette = {
  primary: [
    '#E0ADAD', // brand rose (dark-mode accent text tone)
    '#A08A60', // warm muted brown
    '#F8F7F6', // light cream
    '#8AA79E', // softened teal
    '#D4A84E', // muted sandy
    '#D28C6D', // softened coral
    '#6E8A80', // softened dark teal
    '#7C96BC', // softened blue
  ] as const,
  grid: '#3D3B38',
  axis: '#C5C2BD',
  tooltip: {
    background: '#2F2E2C',
    border: '#3D3B38',
    text: '#F8F7F6',
  },
  status: {
    success: '#6E8A80',
    warning: '#D4A84E',
    danger: '#D28C6D',
    info: '#7C96BC',
  },
  orange: '#BFA67D',
  brown: '#A08A60',
  teal: '#8AA79E',
  coral: '#D28C6D',
  darkTeal: '#6E8A80',
  darkBlue: '#7C96BC',
}

export function useChartColors(): ChartColorPalette & { isDark: boolean } {
  const { isDark } = useThemeToggle()

  const colors = useMemo(() => {
    return isDark ? DARK_COLORS : LIGHT_COLORS
  }, [isDark])

  return { ...colors, isDark }
}

export function useChartTooltipStyle(): React.CSSProperties {
  const { tooltip } = useChartColors()

  return useMemo(() => ({
    backgroundColor: tooltip.background,
    border: `1px solid ${tooltip.border}`,
    borderRadius: '8px',
    color: tooltip.text,
  }), [tooltip])
}

export function useChartPrimaryColors(): readonly [string, string, string, string, string, string, string, string] {
  const { primary } = useChartColors()
  return primary
}

export function useLostDamagedColors(): readonly [string, string, string, string, string, string] {
  const { isDark } = useThemeToggle()

  return useMemo(() => {
    if (isDark) {
      return ['#BFA67D', '#A08A60', '#D28C6D', '#F8F7F6', '#D4A84E', '#C9A86E'] as const
    }
    return ['#7C6545', '#634F30', '#A86040', '#A08A60', '#C9A86E', '#D4A84E'] as const
  }, [isDark])
}

export function useRoomReservationColors(): {
  primary: string
  secondary: string
  danger: string
  success: string
  info: string
  warning: string
  purple: string
  pink: string
  grid: string
  axis: string
  tooltipBg: string
  tooltipBorder: string
} {
  const { isDark } = useThemeToggle()

  return useMemo(() => {
    if (isDark) {
      return {
        primary: '#F59E0B',
        secondary: '#6EE7B7',
        danger: '#F87171',
        success: '#4ADE80',
        info: '#60A5FA',
        warning: '#FBBF24',
        purple: '#A78BFA',
        pink: '#F472B6',
        grid: '#3D3B38',
        axis: '#C5C2BD',
        tooltipBg: '#1F2937',
        tooltipBorder: '#374151',
      }
    }
    return {
      primary: '#D97706',
      secondary: '#4A6B5D',
      danger: '#DC2626',
      success: '#059669',
      info: '#3B82F6',
      warning: '#F59E0B',
      purple: '#7C3AED',
      pink: '#EC4899',
      grid: '#F0EDE8',
      axis: '#8B7B6A',
      tooltipBg: '#F9F7F4',
      tooltipBorder: '#E5E1DB',
    }
  }, [isDark])
}

export function useMakerspaceColors(): readonly [string, string, string, string, string, string] {
  const { isDark } = useThemeToggle()

  return useMemo(() => {
    if (isDark) {
      return ['#6EE7B7', '#F59E0B', '#F87171', '#A78BFA', '#4ADE80', '#FB923C'] as const
    }
    return ['#4A6B5D', '#D97706', '#DC2626', '#7C3AED', '#059669', '#EA580C'] as const
  }, [isDark])
}

export function useStrategicStatusColors(): Record<string, string> {
  const { isDark } = useThemeToggle()

  return useMemo(() => {
    if (isDark) {
      return {
        completed: '#60a5fa',
        on_track: '#4ade80',
        at_risk: '#fbbf24',
        delayed: '#f87171',
        not_started: '#9ca3af',
      }
    }
    return {
      completed: '#3b82f6',
      on_track: '#22c55e',
      at_risk: '#eab308',
      delayed: '#ef4444',
      not_started: '#9ca3af',
    }
  }, [isDark])
}

export function useUsageStatisticsColors(): {
  primary: string
  secondary: string
  grid: string
  axis: string
} {
  const { isDark } = useThemeToggle()

  return useMemo(() => {
    if (isDark) {
      return {
        primary: '#F59E0B',
        secondary: '#A78BFA',
        grid: '#3D3B38',
        axis: '#C5C2BD',
      }
    }
    return {
      primary: '#E97D30',
      secondary: '#8884d8',
      grid: '#ECEAE8',
      axis: '#6B6762',
    }
  }, [isDark])
}

export default useChartColors
