/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/* eslint-disable react-refresh/only-export-components */
import React from 'react';
import { AlertCircle } from 'lucide-react';

interface AccessibleFormFieldProps {
  /** Unique ID for the form field - used for label association */
  id: string;
  /** Label text for the field */
  label: string;
  /** Whether the field is required */
  required?: boolean;
  /** Optional help text displayed below the input */
  helpText?: string;
  /** Error message to display */
  error?: string;
  /** Children elements (the actual input, select, textarea, etc.) */
  children: React.ReactNode;
  /** Additional classes for the wrapper */
  className?: string;
}

export default function AccessibleFormField({
  id,
  label,
  required = false,
  helpText,
  error,
  children,
  className = '',
}: AccessibleFormFieldProps): React.ReactElement {
  const helpTextId = helpText ? `${id}-help` : undefined;
  const errorId = error ? `${id}-error` : undefined;

  // Clone children to inject aria attributes
  const enhancedChildren = React.Children.map(children, (child) => {
    if (React.isValidElement(child)) {
      const describedBy = [helpTextId, errorId].filter(Boolean).join(' ') || undefined;
      return React.cloneElement(child as React.ReactElement<Record<string, unknown>>, {
        id,
        'aria-describedby': describedBy,
        'aria-invalid': error ? true : undefined,
        'aria-required': required ? true : undefined,
      });
    }
    return child;
  });

  return (
    <div className={`space-y-2 ${className}`}>
      {/* Label with required indicator */}
      <label
        htmlFor={id}
        className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream"
      >
        {label}
        {required && (
          <span
            className="text-status-danger-600 dark:text-status-danger-400 ml-1"
            aria-hidden="true"
          >
            *
          </span>
        )}
        {required && <span className="sr-only">(required)</span>}
      </label>

      {/* Help text - displayed above input for better discoverability */}
      {helpText && (
        <p
          id={helpTextId}
          className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70"
        >
          {helpText}
        </p>
      )}

      {/* The form control */}
      {enhancedChildren}

      {/* Error message with live region for screen readers */}
      {error && (
        <div
          id={errorId}
          role="alert"
          aria-live="polite"
          className="flex items-center gap-2 text-sm text-status-danger-600 dark:text-status-danger-400"
        >
          <AlertCircle className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
}

interface AccessibleToggleProps {
  id: string;
  label: string;
  description?: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
}

export function AccessibleToggle({
  id,
  label,
  description,
  checked,
  onChange,
  disabled = false,
}: AccessibleToggleProps): React.ReactElement {
  return (
    <div className="flex items-start justify-between gap-4">
      <div className="flex-1">
        <label
          htmlFor={id}
          className="font-medium text-lsc-dark dark:text-lsc-cream cursor-pointer"
        >
          {label}
        </label>
        {description && (
          <p
            id={`${id}-description`}
            className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1"
          >
            {description}
          </p>
        )}
      </div>
      <button
        type="button"
        id={id}
        role="switch"
        aria-checked={checked}
        aria-describedby={description ? `${id}-description` : undefined}
        onClick={() => !disabled && onChange(!checked)}
        disabled={disabled}
        className={`
          relative w-12 h-7 rounded-full motion-safe:transition-colors
          min-w-[48px] min-h-[44px] flex items-center
          focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2
          dark:focus:ring-offset-earth-800
          disabled:opacity-50 disabled:cursor-not-allowed
          ${checked ? 'bg-lsc-rose' : 'bg-lsc-border dark:bg-earth-600'}
        `}
      >
        <span
          aria-hidden="true"
          className={`
            absolute w-5 h-5 bg-lsc-white dark:bg-earth-800 rounded-full shadow
            motion-safe:transition-transform
            ${checked ? 'left-6' : 'left-1'}
          `}
        />
      </button>
    </div>
  );
}

/**
 * Consistent input styling classes
 */
export const inputClasses = `
  w-full border border-lsc-border dark:border-earth-700 rounded-lg px-4 py-3
  bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream
  focus:ring-2 focus:ring-lsc-rose focus:border-transparent focus:outline-none
  disabled:opacity-50 disabled:cursor-not-allowed
  min-h-[44px]
`.trim().replace(/\s+/g, ' ');

/**
 * Consistent select styling classes
 */
export const selectClasses = `
  w-full border border-lsc-border dark:border-earth-700 rounded-lg px-4 py-3
  bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream
  focus:ring-2 focus:ring-lsc-rose focus:border-transparent focus:outline-none
  disabled:opacity-50 disabled:cursor-not-allowed
  min-h-[44px] cursor-pointer
`.trim().replace(/\s+/g, ' ');

/**
 * Consistent textarea styling classes
 */
export const textareaClasses = `
  w-full border border-lsc-border dark:border-earth-700 rounded-lg px-4 py-3
  bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream
  focus:ring-2 focus:ring-lsc-rose focus:border-transparent focus:outline-none
  disabled:opacity-50 disabled:cursor-not-allowed
  resize-y min-h-[100px]
`.trim().replace(/\s+/g, ' ');
