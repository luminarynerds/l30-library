/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import type React from 'react'

export interface DemoScene {
  id: number
  title: string
  subtitle: string
  icon: React.ElementType
  color: string
  bgGradient: string
  durationMinutes: number
  talkingPoints: string[]
}

export interface AnimatedCounterProps {
  end: number
  duration?: number
  prefix?: string
  suffix?: string
  className?: string
}

export interface TimelineEvent {
  time: string
  action: string
  result: string
  icon: React.ElementType
}
