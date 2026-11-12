/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from 'react';

interface ProgressProps extends React.HTMLAttributes<HTMLDivElement> {
  value?: number;
  max?: number;
}

export function Progress({ value, max, className, ...props }: ProgressProps) {
  return <div className={className} role="progressbar" aria-valuenow={value} aria-valuemax={max} {...props} />;
}
