/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { BookOpen, Headphones, Film, Gamepad2, Wrench, Package, Smartphone, PenTool } from 'lucide-react'
import { clsx } from '@/utils/helpers'
import { useTranslation } from '@/i18n/I18nContext'

const FORMATS = [
  { type: 'book', subtitleKey: 'books', icon: BookOpen },
  { type: 'ebook', subtitleKey: 'ebooks', icon: Smartphone },
  { type: 'indie_ebook', subtitleKey: 'indieEbooks', icon: PenTool },
  { type: 'audiobook', subtitleKey: 'audiobooks', icon: Headphones },
  { type: 'dvd', subtitleKey: 'movies', icon: Film },
  { type: 'game', subtitleKey: 'games', icon: Gamepad2 },
  { type: 'kit', subtitleKey: 'kits', icon: Package },
  { type: 'equipment', subtitleKey: 'equipment', icon: Wrench },
] as const

interface CatalogFormatChipsProps {
  activeFormat: string | null
  onSelect: (format: string) => void
}

export default function CatalogFormatChips({ activeFormat, onSelect }: CatalogFormatChipsProps) {
  const { t } = useTranslation()

  return (
    <div className="flex flex-wrap gap-2 mb-6" role="group" aria-label={t('catalog.browseByFormat')}>
      {FORMATS.map(({ type, subtitleKey, icon: Icon }) => {
        const isActive = activeFormat === type
        const label = t(`catalog.formatChipLabels.${type}`)
        const subtitle = t(`catalog.formatSubtitles.${subtitleKey}`)
        return (
          <button
            key={type}
            onClick={() => onSelect(isActive ? '' : type)}
            className={clsx(
              'inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold transition-colors',
              'border-2 focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2 dark:focus:ring-offset-lsc-dark',
              isActive
                ? 'bg-lsc-rose text-white border-lsc-rose'
                : 'bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream border-lsc-border dark:border-earth-700 hover:border-lsc-rose/50'
            )}
            aria-pressed={isActive}
          >
            <Icon className="w-4 h-4" aria-hidden="true" />
            <span>{label}</span>
            <span className={clsx(
              'text-xs font-normal',
              isActive ? 'text-white/90' : 'text-lsc-dark/70 dark:text-lsc-cream/70'
            )}>
              {subtitle}
            </span>
          </button>
        )
      })}
    </div>
  )
}
