/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * FormError - Reusable error message component with brand-aligned styling
 * Displays validation errors with proper accessibility attributes
 */

import React from 'react'
import { AlertCircle } from 'lucide-react'

interface FormErrorProps {
  id?: string
  error: string
  className?: string
}

export function FormError({ id, error, className = '' }: FormErrorProps): React.ReactElement {
  return (
    <div
      id={id}
      role="alert"
      aria-live="polite"
      className={`mt-2 flex items-start gap-2 text-sm text-status-danger-600 dark:text-status-danger-400 ${className}`}
    >
      <AlertCircle
        className="w-4 h-4 flex-shrink-0 mt-0.5"
        aria-hidden="true"
      />
      <span>{error}</span>
    </div>
  )
}

export default FormError
