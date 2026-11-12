/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useState } from 'react'
import { Check, ChevronDown, ChevronUp } from 'lucide-react'

interface SettingToggleProps {
  label: string
  description: string
  checked: boolean
  onChange: (checked: boolean) => void
  icon?: React.ReactNode
  disabled?: boolean
}

export function SettingToggle({ label, description, checked, onChange, icon, disabled }: SettingToggleProps) {
  const toggle = () => {
    if (!disabled) onChange(!checked)
  }
  return (
    <div
      role="switch"
      aria-checked={checked}
      aria-label={label}
      aria-disabled={disabled || undefined}
      tabIndex={disabled ? -1 : 0}
      onClick={toggle}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          toggle()
        }
      }}
      className={`flex items-start gap-4 p-4 rounded-xl bg-lsc-white dark:bg-lsc-brown border-2 border-transparent hover:border-lsc-rose/30 transition-colors group focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2 ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
    >
      <div className="flex-shrink-0 mt-0.5">
        <div
          aria-hidden="true"
          className={`relative w-12 h-7 rounded-full transition-colors ${checked ? 'bg-status-success-500' : 'bg-earth-300 dark:bg-earth-600'}`}
        >
          <div
            className={`absolute top-1 w-5 h-5 rounded-full bg-lsc-white dark:bg-earth-800 shadow-md transition-transform ${checked ? 'translate-x-6' : 'translate-x-1'}`}
          />
        </div>
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          {icon && <span className="text-lsc-dark/70 dark:text-lsc-cream/70">{icon}</span>}
          <span className="font-medium text-lsc-dark dark:text-lsc-cream">{label}</span>
        </div>
        <p className="mt-1 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 leading-relaxed">
          {description}
        </p>
      </div>
      {checked && (
        <div className="flex-shrink-0">
          <Check className="w-5 h-5 text-status-success-500" aria-hidden="true" />
        </div>
      )}
    </div>
  )
}

interface CollapsibleSectionProps {
  title: string
  description: string
  icon: React.ReactNode
  children: React.ReactNode
  defaultOpen?: boolean
}

export function CollapsibleSection({ title, description, icon, children, defaultOpen = false }: CollapsibleSectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen)

  return (
    <div className="border-2 border-sage/20 dark:border-earth-700 rounded-xl overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center gap-4 p-4 bg-cream dark:bg-earth-800 hover:bg-sage/10 dark:hover:bg-earth-700 transition-colors text-left"
        aria-expanded={isOpen}
      >
        <div className="flex-shrink-0 w-10 h-10 rounded-xl bg-lsc-rose/10 flex items-center justify-center text-lsc-rose">
          {icon}
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{title}</h3>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{description}</p>
        </div>
        <div className="flex-shrink-0 text-lsc-dark/70 dark:text-lsc-cream/70">
          {isOpen ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
        </div>
      </button>
      {isOpen && (
        <div className="p-4 bg-lsc-white dark:bg-earth-800 border-t border-sage/20 dark:border-earth-700 space-y-3">
          {children}
        </div>
      )}
    </div>
  )
}

interface SegmentedControlProps<T extends string> {
  label: string
  description: string
  icon: React.ReactNode
  options: readonly T[]
  value: T
  onChange: (value: T) => void
  disabled?: boolean
  renderLabel?: (option: T) => React.ReactNode
}

const capitalize = (s: string) => s.charAt(0).toUpperCase() + s.slice(1)

export function SegmentedControl<T extends string>({
  label,
  description,
  icon,
  options,
  value,
  onChange,
  disabled = false,
  renderLabel,
}: SegmentedControlProps<T>) {
  return (
    <div className="p-4 rounded-xl bg-lsc-white dark:bg-lsc-brown">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-lsc-dark/70 dark:text-lsc-cream/70">{icon}</span>
        <span className="font-medium text-lsc-dark dark:text-lsc-cream">{label}</span>
      </div>
      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">{description}</p>
      <div className="flex flex-wrap gap-2">
        {options.map((option) => (
          <button
            key={option}
            onClick={() => onChange(option)}
            disabled={disabled}
            className={`
              flex-1 min-w-[80px] py-3 px-4 rounded-xl font-medium transition-colors whitespace-nowrap
              ${value === option
                ? 'bg-lsc-rose text-white'
                : 'bg-cream dark:bg-lsc-dark text-lsc-dark dark:text-lsc-cream hover:bg-sage/20'
              }
              ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
            `}
            aria-pressed={value === option}
          >
            {renderLabel ? renderLabel(option) : capitalize(option)}
          </button>
        ))}
      </div>
    </div>
  )
}
