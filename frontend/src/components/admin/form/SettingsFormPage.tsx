/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from 'react'
import { Save, RefreshCw } from 'lucide-react'
import { StaffLayout } from '../../staff/StaffLayout'
import { clsx } from '../../../utils/helpers'

export interface SettingsFormPageProps {
  title: string
  subtitle?: string
  icon?: React.ElementType
  loading?: boolean
  saving?: boolean
  disabled?: boolean
  onSave: () => void | Promise<void>
  saveLabel?: string
  banner?: React.ReactNode
  footer?: React.ReactNode
  children: React.ReactNode
  /** When true, skip StaffLayout wrapper (use when embedded in another layout like AdminShell) */
  bare?: boolean
}

export function SettingsFormPage({
  title,
  subtitle,
  icon: Icon,
  loading = false,
  saving = false,
  disabled = false,
  onSave,
  saveLabel,
  banner,
  footer,
  children,
  bare = false,
}: SettingsFormPageProps): React.ReactElement {
  if (loading) {
    const spinner = (
      <div className="flex items-center justify-center h-64">
        <RefreshCw
          className="w-8 h-8 motion-safe:animate-spin text-lsc-rose dark:text-lsc-rose-light"
          aria-hidden="true"
        />
      </div>
    )
    return bare ? spinner : <StaffLayout title={title}>{spinner}</StaffLayout>
  }

  const content = (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
        <div className="flex items-center gap-3 mb-2">
          {Icon && (
            <Icon className="w-8 h-8 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
          )}
          <div>
            <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">{title}</h1>
            {subtitle && (
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{subtitle}</p>
            )}
          </div>
        </div>

        {banner}

        {children}

        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-6 border border-lsc-border dark:border-earth-700 space-y-4">
          {footer}
          <button
            type="button"
            onClick={() => void onSave()}
            disabled={saving || disabled}
            className={clsx(
              'w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg font-medium transition-colors',
              'bg-lsc-rose hover:bg-lsc-rose/90 text-white disabled:opacity-50',
            )}
          >
            {saving ? (
              <RefreshCw className="w-5 h-5 motion-safe:animate-spin" aria-hidden="true" />
            ) : (
              <Save className="w-5 h-5" aria-hidden="true" />
            )}
            {saving ? 'Saving\u2026' : saveLabel || `Save ${title}`}
          </button>
        </div>
      </div>
    )

  return bare ? content : <StaffLayout title={title}>{content}</StaffLayout>
}
