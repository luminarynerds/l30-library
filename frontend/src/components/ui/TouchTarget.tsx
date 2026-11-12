/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * TouchTarget - Ensures minimum touch target size of 44x44px (WCAG 2.2 Level AAA)
 * Wraps interactive elements that may be smaller than the minimum touch target
 */

import React from 'react'
import { clsx } from '@/utils/helpers'

interface TouchTargetProps {
  children: React.ReactNode
  className?: string
  as?: 'button' | 'a' | 'div'
  [key: string]: unknown
}

export function TouchTarget({
  children,
  className,
  as: Component = 'div',
  ...props
}: TouchTargetProps): React.ReactElement {
  return (
    <Component
      className={clsx(
        'inline-flex items-center justify-center min-w-[44px] min-h-[44px] touch-manipulation',
        className
      )}
      {...props}
    >
      {children}
    </Component>
  )
}

/**
 * Utility class for applying touch target sizing inline
 * Use: className="touch-target"
 */
export const touchTargetClass = 'min-w-[44px] min-h-[44px] touch-manipulation'

export default TouchTarget
