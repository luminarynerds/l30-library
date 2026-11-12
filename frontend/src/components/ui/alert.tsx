/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from 'react';

interface AlertProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: string;
}

export function Alert({ children, className, variant: _variant, ...props }: AlertProps) {
  return <div className={className} role="alert" {...props}>{children}</div>;
}

export function AlertTitle({ children, className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return <h5 className={className} {...props}>{children}</h5>;
}

export function AlertDescription({ children, className, ...props }: React.HTMLAttributes<HTMLParagraphElement>) {
  return <p className={className} {...props}>{children}</p>;
}
