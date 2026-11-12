/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * FormSuccess - Success indicator for valid form fields
 * Shows when a field passes validation
 */

import React from 'react'
import { CheckCircle } from 'lucide-react'

interface FormSuccessProps {
  id?: string
  message?: string
  className?: string
}

export function FormSuccess({
  id,
  message,
  className = ''
}: FormSuccessProps): React.ReactElement {
  return (
    <div
      id={id}
      role="status"
      aria-live="polite"
      className={`mt-2 flex items-start gap-2 text-sm text-status-success-600 dark:text-status-success-400 ${className}`}
    >
      <CheckCircle
        className="w-4 h-4 flex-shrink-0 mt-0.5"
        aria-hidden="true"
      />
      {message && <span>{message}</span>}
      {!message && <span className="sr-only">Valid input</span>}
    </div>
  )
}

export default FormSuccess
