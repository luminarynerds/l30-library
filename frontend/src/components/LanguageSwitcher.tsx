/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as DropdownMenu from '@radix-ui/react-dropdown-menu'
import { Globe } from 'lucide-react'
import { languages, type Language } from '../i18n/translations'
import { useTranslation } from '../i18n/I18nContext'
import { clsx } from '../utils/helpers'
import { t } from '@/i18n'

const LANGUAGE_LIST = Object.entries(languages) as [Language, (typeof languages)[Language]][]

interface LanguageSwitcherProps {
  inline?: boolean
}

export default function LanguageSwitcher({ inline = false }: LanguageSwitcherProps): React.ReactElement {
  const { language, setLanguage } = useTranslation()

  if (inline) {
    return (
      <div className="flex flex-wrap gap-2">
        {LANGUAGE_LIST.map(([code, info]) => (
          <button
            key={code}
            onClick={() => setLanguage(code)}
            className={clsx(
              'px-3 py-2 min-h-[44px] rounded-lg text-sm font-medium transition-colors touch-manipulation',
              code === language
                ? 'bg-lsc-rose/10 text-lsc-rose border border-lsc-rose/30'
                : 'text-lsc-dark dark:text-lsc-cream hover:bg-lsc-rose/5 dark:hover:bg-lsc-rose/10',
            )}
            aria-pressed={code === language}
          >
            {info.flag && <span className="mr-1.5">{info.flag}</span>}
            {info.nativeName}
          </button>
        ))}
      </div>
    )
  }

  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <button
          type="button"
          className="flex items-center justify-center gap-1.5 px-2 py-2 min-w-[44px] min-h-[44px] rounded-lg text-sm text-earth-700 dark:text-earth-300 hover:bg-earth-50 dark:hover:bg-earth-800/15 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose"
          aria-label={t('aria.languageSwitcher.changeLanguage')}
        >
          <Globe className="w-4 h-4" aria-hidden="true" />
          <span className="hidden md:inline uppercase font-medium" aria-hidden="true">{language}</span>
        </button>
      </DropdownMenu.Trigger>

      <DropdownMenu.Portal>
        <DropdownMenu.Content
          align="end"
          sideOffset={4}
          collisionPadding={16}
          aria-label={t('aria.languageSwitcher.selectLanguage')}
          className={clsx(
            'bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg border border-lsc-border dark:border-earth-700',
            'py-1 min-w-[160px] z-[60] motion-safe:animate-menu-enter',
          )}
        >
          <DropdownMenu.RadioGroup
            value={language}
            onValueChange={(v) => setLanguage(v as Language)}
          >
            {LANGUAGE_LIST.map(([code, info]) => (
              <DropdownMenu.RadioItem
                key={code}
                value={code}
                className={clsx(
                  'w-full flex items-center gap-2.5 px-3 py-2.5 text-sm text-left outline-none cursor-pointer transition-colors',
                  'data-[highlighted]:bg-earth-50 dark:data-[highlighted]:bg-earth-700/50',
                  'data-[state=checked]:bg-lsc-rose/10 data-[state=checked]:text-lsc-rose data-[state=checked]:font-medium',
                  'text-lsc-dark/70 dark:text-lsc-cream/70',
                )}
              >
                {info.flag && <span>{info.flag}</span>}
                <span>{info.nativeName}</span>
              </DropdownMenu.RadioItem>
            ))}
          </DropdownMenu.RadioGroup>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  )
}
