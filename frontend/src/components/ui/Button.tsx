/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Button component with clear visual hierarchy and accessibility
 * Implements button variants (primary, secondary, tertiary) with proper touch targets
 *
 * Features friendly, branded loading text that matches the library's warm voice.
 */

import React from 'react'
import { clsx } from '@/utils/helpers'
import { Loader2 } from 'lucide-react'
import { BUTTON_LOADING_MESSAGE_KEYS, getButtonLoadingTextKey } from '@/constants/brandMessages'
import { useTranslation } from '@/i18n/I18nContext'

export type ButtonVariant = 'primary' | 'secondary' | 'tertiary' | 'danger' | 'default' | 'outline' | 'ghost'
export type ButtonSize = 'sm' | 'md' | 'lg'

export type ButtonLoadingAction = keyof typeof BUTTON_LOADING_MESSAGE_KEYS

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
  isLoading?: boolean
  /** Custom loading text (overrides loadingAction) */
  loadingText?: string
  /** Action type for contextual loading text (e.g., 'save', 'submit', 'register') */
  loadingAction?: ButtonLoadingAction
  leftIcon?: React.ReactNode
  rightIcon?: React.ReactNode
  fullWidth?: boolean
}

const variantStyles = {
  // WCAG AA: Disabled states use solid colors for readability (4.5:1+ contrast)
  primary: 'bg-lsc-rose hover:bg-lsc-rose/90 text-white shadow-md hover:shadow-lg active:shadow-sm rounded-xl font-semibold border-2 border-transparent focus:ring-offset-2 disabled:bg-earth-500 disabled:opacity-100 disabled:cursor-not-allowed disabled:shadow-none',
  secondary: 'bg-lsc-cream dark:bg-lsc-brown hover:bg-lsc-border dark:hover:bg-lsc-brown/80 text-lsc-dark dark:text-lsc-cream border-2 border-lsc-border dark:border-lsc-brown rounded-xl font-medium shadow-sm hover:shadow disabled:opacity-50 disabled:cursor-not-allowed',
  tertiary: 'bg-transparent hover:bg-lsc-cream dark:hover:bg-lsc-brown/50 text-lsc-dark dark:text-lsc-cream border-2 border-transparent rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed',
  danger: 'bg-status-danger-600 hover:bg-status-danger-700 text-white shadow-md hover:shadow-lg active:shadow-sm rounded-xl font-semibold border-2 border-transparent focus:ring-offset-2 disabled:bg-earth-500 disabled:opacity-100 disabled:cursor-not-allowed disabled:shadow-none',
  // Additional variants for compatibility
  default: 'bg-lsc-cream dark:bg-lsc-brown hover:bg-lsc-border dark:hover:bg-lsc-brown/80 text-lsc-dark dark:text-lsc-cream border-2 border-lsc-border dark:border-lsc-brown rounded-xl font-medium shadow-sm hover:shadow disabled:opacity-50 disabled:cursor-not-allowed',
  outline: 'bg-transparent border-2 border-lsc-border dark:border-lsc-brown text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-lsc-brown/50 rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed',
  ghost: 'bg-transparent text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream/50 dark:hover:bg-lsc-brown/30 border-none rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed',
}

const sizeStyles = {
  sm: 'px-3 py-2 text-sm min-h-[44px]', // Touch target compliant
  md: 'px-4 py-3 text-base min-h-[48px]',
  lg: 'px-6 py-4 text-lg min-h-[56px]',
}

export function Button({
  variant = 'primary',
  size = 'md',
  isLoading = false,
  loadingText,
  loadingAction = 'default',
  leftIcon,
  rightIcon,
  fullWidth = false,
  children,
  className,
  disabled,
  ...props
}: ButtonProps): React.ReactElement {
  const { t } = useTranslation()
  // Get the appropriate loading text
  const displayLoadingText = loadingText ?? t(getButtonLoadingTextKey(loadingAction))

  return (
    <button
      className={clsx(
        'inline-flex items-center justify-center gap-2 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-lsc-rose touch-manipulation interactive-press',
        variantStyles[variant],
        sizeStyles[size],
        fullWidth && 'w-full',
        className
      )}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? (
        <>
          <Loader2 className="w-5 h-5 motion-safe:animate-spin" aria-hidden="true" />
          <span>{displayLoadingText}</span>
        </>
      ) : (
        <>
          {leftIcon && <span className="flex-shrink-0" aria-hidden="true">{leftIcon}</span>}
          {children}
          {rightIcon && <span className="flex-shrink-0" aria-hidden="true">{rightIcon}</span>}
        </>
      )}
    </button>
  )
}

export default Button
