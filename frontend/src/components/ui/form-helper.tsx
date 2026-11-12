/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * FormHelper - Reusable helper text component for form fields
 * Provides contextual hints and guidance to users
 */

import React from 'react'
import { HelpCircle } from 'lucide-react'

interface FormHelperProps {
  id?: string
  text: string
  showIcon?: boolean
  className?: string
}

export function FormHelper({
  id,
  text,
  showIcon = false,
  className = ''
}: FormHelperProps): React.ReactElement {
  return (
    <div
      id={id}
      className={`mt-2 flex items-start gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 ${className}`}
    >
      {showIcon && (
        <HelpCircle
          className="w-4 h-4 flex-shrink-0 mt-0.5"
          aria-hidden="true"
        />
      )}
      <span>{text}</span>
    </div>
  )
}

export default FormHelper
