/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from "react"

export function SectionCard({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`bg-lsc-white dark:bg-earth-800 rounded-xl shadow p-6 ${className}`}>
      {children}
    </div>
  );
}

export function Label({ children, htmlFor }: { children: React.ReactNode; htmlFor?: string }) {
  return (
    <label htmlFor={htmlFor} className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
      {children}
    </label>
  );
}

export function InputField({ value, onChange, type = "text", placeholder, className = "", ...rest }: React.InputHTMLAttributes<HTMLInputElement> & { onChange: (e: React.ChangeEvent<HTMLInputElement>) => void }) {
  return (
    <input
      type={type}
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      className={`w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-100 focus:ring-2 focus:ring-lsc-rose focus:border-transparent ${className}`}
      {...rest}
    />
  );
}

export function TextArea({ value, onChange, rows = 3, placeholder, className = "" }: { value: string; onChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void; rows?: number; placeholder?: string; className?: string }) {
  return (
    <textarea
      value={value}
      onChange={onChange}
      rows={rows}
      placeholder={placeholder}
      className={`w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-100 focus:ring-2 focus:ring-lsc-rose focus:border-transparent ${className}`}
    />
  );
}

export function PrimaryButton({ children, onClick, disabled, className = "" }: { children: React.ReactNode; onClick: () => void; disabled?: boolean; className?: string }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 disabled:opacity-50 flex items-center gap-2 ${className}`}
    >
      {children}
    </button>
  );
}

export function SecondaryButton({ children, onClick, disabled, className = "" }: { children: React.ReactNode; onClick: () => void; disabled?: boolean; className?: string }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`px-4 py-2 bg-lsc-brown text-white rounded-lg hover:bg-lsc-brown/90 disabled:opacity-50 flex items-center gap-2 ${className}`}
    >
      {children}
    </button>
  );
}

export function DangerButton({ children, onClick, disabled }: { children: React.ReactNode; onClick: () => void; disabled?: boolean }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="px-3 py-1.5 text-status-danger-600 hover:bg-status-danger-50 dark:hover:bg-status-danger-900/20 rounded-lg text-sm flex items-center gap-1 disabled:opacity-50"
    >
      {children}
    </button>
  );
}

export function AIStatCard({ value, label, color }: { value: string | number; label: string; color: string }) {
  const colorClasses: Record<string, string> = {
    default: "bg-lsc-cream dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream",
    success: "bg-status-success-50 dark:bg-status-success-900/20 text-status-success-700 dark:text-status-success-300",
    danger: "bg-status-danger-50 dark:bg-status-danger-900/20 text-status-danger-700 dark:text-status-danger-300",
    accent: "bg-earth-50 dark:bg-earth-800/20 text-lsc-rose dark:text-lsc-rose-light",
    warning: "bg-status-warning-50 dark:bg-status-warning-900/20 text-status-warning-700 dark:text-status-warning-300",
  };
  return (
    <div className={`rounded-xl p-4 text-center ${colorClasses[color] || colorClasses.default}`}>
      <p className="text-2xl font-bold">{value}</p>
      <p className="text-sm opacity-80">{label}</p>
    </div>
  );
}
