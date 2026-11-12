/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Mail, MessageSquare, Megaphone, Sparkles } from 'lucide-react'

type ChannelType = 'email' | 'sms' | 'campaign' | 'ai'

interface ChannelBadgeProps {
  channel: ChannelType
  className?: string
}

const CONFIG: Record<ChannelType, { icon: typeof Mail; label: string; classes: string }> = {
  email: {
    icon: Mail,
    label: 'Email channel',
    classes: 'bg-status-info-50 text-status-info-700 border-status-info-200 dark:bg-status-info-900/20 dark:text-status-info-300 dark:border-status-info-800',
  },
  sms: {
    icon: MessageSquare,
    label: 'Text message channel',
    classes: 'bg-status-success-50 text-status-success-700 border-status-success-200 dark:bg-status-success-900/20 dark:text-status-success-300 dark:border-status-success-800',
  },
  campaign: {
    icon: Megaphone,
    label: 'Campaign tool',
    classes: 'bg-status-warning-50 text-status-warning-700 border-status-warning-200 dark:bg-status-warning-900/20 dark:text-status-warning-300 dark:border-status-warning-800',
  },
  ai: {
    icon: Sparkles,
    label: 'AI-powered tool',
    classes: 'bg-category-50 text-category-700 border-category-200 dark:bg-category-900/20 dark:text-category-300 dark:border-category-800',
  },
}

export type { ChannelType }

export function ChannelBadge({ channel, className = '' }: ChannelBadgeProps) {
  const { icon: Icon, label, classes } = CONFIG[channel]
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium border rounded-full ${classes} ${className}`}
      aria-label={label}
    >
      <Icon className="w-3 h-3" aria-hidden="true" />
      {label}
    </span>
  )
}
