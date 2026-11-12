/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from 'react'
import { Loader2, AlertCircle } from 'lucide-react'
import { StaffLayout } from '../staff/StaffLayout'

interface AdminShellProps {
  title: string
  subtitle?: string
  icon?: React.ReactNode
  actions?: React.ReactNode
  loading?: boolean
  error?: string | null
  children: React.ReactNode
  maxWidth?: string
}

export function AdminShell({
  title,
  subtitle,
  icon,
  actions,
  loading = false,
  error = null,
  children,
  maxWidth = 'max-w-none',
}: AdminShellProps) {
  if (loading) {
    return (
      <StaffLayout title={title}>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 motion-safe:animate-spin text-lsc-rose" />
        </div>
      </StaffLayout>
    )
  }

  return (
    <StaffLayout title={title} hideDefaultHeader={!!icon}>
      <div className={`${maxWidth} mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6`}>
        {(icon || subtitle || actions) && (
          <div className="mb-8">
            <div className="flex items-center justify-between">
              <div>
                {icon && (
                  <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream flex items-center gap-3">
                    {icon}
                    {title}
                  </h1>
                )}
                {subtitle && (
                  <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">
                    {subtitle}
                  </p>
                )}
              </div>
              {actions && <div className="flex items-center gap-2">{actions}</div>}
            </div>
          </div>
        )}
        {error ? (
          <div className="flex flex-col items-center justify-center h-64 gap-4">
            <AlertCircle className="h-8 w-8 text-status-danger-500" />
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{error}</p>
          </div>
        ) : (
          children
        )}
      </div>
    </StaffLayout>
  )
}
