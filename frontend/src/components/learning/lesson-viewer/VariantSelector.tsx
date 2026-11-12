/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { FileText } from 'lucide-react'
import { VARIANT_ICONS, type LessonVariant } from '../lesson-types'

interface Props {
  variants: LessonVariant[]
  activeVariant: string
  onChange: (variant: string) => void
}

export function VariantSelector({ variants, activeVariant, onChange }: Props) {
  if (variants.length === 0) return null

  const buttonClass = (active: boolean) =>
    `inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
      active
        ? 'bg-lsc-rose text-white'
        : 'bg-lsc-cream dark:bg-lsc-brown text-lsc-dark dark:text-earth-300 hover:bg-lsc-cream dark:hover:bg-lsc-brown/90'
    }`

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 mb-6 shadow-sm">
      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
        Choose your preferred format:
      </p>
      <div className="flex flex-wrap gap-2">
        <button onClick={() => onChange('default')} className={buttonClass(activeVariant === 'default')}>
          <FileText aria-hidden="true" className="w-4 h-4" />
          Default
        </button>
        {variants.map(variant => {
          const Icon = VARIANT_ICONS[variant.variant_type] || FileText
          return (
            <button
              key={variant.id}
              onClick={() => onChange(variant.variant_type)}
              className={buttonClass(activeVariant === variant.variant_type)}
            >
              <Icon aria-hidden="true" className="w-4 h-4" />
              {variant.variant_type.replace('_', ' ')}
            </button>
          )
        })}
      </div>
    </div>
  )
}
