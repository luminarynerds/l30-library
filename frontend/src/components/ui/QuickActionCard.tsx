/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from 'react'
import { Link } from 'react-router-dom'
import { ChevronRight } from 'lucide-react'

export interface QuickActionCardProps {
  title: string
  description: string
  icon: React.ElementType
  to: string
  iconBgColor?: string
  badge?: string | number
  className?: string
}

export function QuickActionCard({
  title,
  description,
  icon: Icon,
  to,
  iconBgColor = 'bg-lsc-rose',
  badge,
  className = '',
}: QuickActionCardProps) {
  return (
    <Link
      to={to}
      className={`flex items-center gap-3 p-4 bg-lsc-cream dark:bg-lsc-brown/20 hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 rounded-xl transition-colors relative ${className}`}
    >
      <div className={`w-12 h-12 ${iconBgColor} rounded-xl flex items-center justify-center flex-shrink-0`}>
        <Icon className="w-6 h-6 text-white" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-semibold text-lsc-dark dark:text-lsc-cream">{title}</p>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{description}</p>
      </div>
      {badge != null && (
        <span className="absolute top-2 right-2 bg-status-danger-500 text-white text-xs font-bold rounded-full w-6 h-6 flex items-center justify-center">
          {badge}
        </span>
      )}
      <ChevronRight className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70 ml-auto flex-shrink-0" />
    </Link>
  )
}
