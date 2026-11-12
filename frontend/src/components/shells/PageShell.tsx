/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from 'react'
import { Loader2, AlertCircle } from 'lucide-react'

interface PageShellProps {
  title: string
  subtitle?: string
  icon?: React.ReactNode
  actions?: React.ReactNode
  loading?: boolean
  error?: string | null
  children: React.ReactNode
  className?: string
}

export function PageShell({
  title,
  subtitle,
  icon,
  actions,
  loading = false,
  error = null,
  children,
  className,
}: PageShellProps) {
  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 motion-safe:animate-spin text-lsc-dark/70 dark:text-lsc-cream/70" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <AlertCircle className="h-8 w-8 text-status-danger-500" />
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{error}</p>
      </div>
    )
  }

  return (
    <div className={className}>
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream flex items-center gap-3">
              {icon}
              {title}
            </h1>
            {subtitle && (
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">
                {subtitle}
              </p>
            )}
          </div>
          {actions && <div className="flex items-center gap-2">{actions}</div>}
        </div>
      </div>
      {children}
    </div>
  )
}
