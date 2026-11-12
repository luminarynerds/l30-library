/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from 'react';
import { clsx as cn } from '@/utils/helpers';

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  error?: boolean;
  success?: boolean;
}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, error, success, ...props }, ref) => {
    return (
      <textarea
        className={cn(
          'w-full px-4 py-3 text-base border-2 rounded-lg',
          'bg-lsc-white dark:bg-lsc-dark text-lsc-dark dark:text-lsc-cream',
          'focus:ring-2 focus:ring-lsc-rose focus:border-transparent',
          'transition-all duration-200',
          'disabled:opacity-50 disabled:cursor-not-allowed',
          error && 'border-status-danger-500 dark:border-status-danger-500 focus:ring-status-danger-500',
          success && 'border-status-success-500 dark:border-status-success-500 focus:ring-status-success-500',
          !error && !success && 'border-lsc-border dark:border-earth-700',
          className
        )}
        ref={ref}
        aria-invalid={error}
        {...props}
      />
    );
  }
);
Textarea.displayName = 'Textarea';
