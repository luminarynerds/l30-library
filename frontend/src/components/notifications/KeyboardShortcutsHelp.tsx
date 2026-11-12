/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useTranslation } from '@/i18n'

export function KeyboardShortcutsHelp(): React.ReactElement {
  const { t } = useTranslation()

  return (
    <details className="mt-6 bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 overflow-hidden">
      <summary className="px-4 py-3 cursor-pointer text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream/50 dark:hover:bg-earth-700/50 transition-colors list-none flex items-center gap-2">
        Keyboard shortcuts
      </summary>
      <div className="px-4 pb-4 pt-2 border-t border-lsc-border dark:border-earth-700">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
          <div className="space-y-2">
            <h4 className="font-medium text-lsc-dark dark:text-lsc-cream">Navigation</h4>
            <div className="space-y-1 text-lsc-dark/70 dark:text-lsc-cream/70">
              <div className="flex items-center gap-2">
                <kbd className="px-1.5 py-0.5 bg-lsc-cream dark:bg-earth-700 rounded text-xs font-mono">↑</kbd>
                <kbd className="px-1.5 py-0.5 bg-lsc-cream dark:bg-earth-700 rounded text-xs font-mono">k</kbd>
                <span>{t('notifications.previousNotificationFocusMode')}</span>
              </div>
              <div className="flex items-center gap-2">
                <kbd className="px-1.5 py-0.5 bg-lsc-cream dark:bg-earth-700 rounded text-xs font-mono">↓</kbd>
                <kbd className="px-1.5 py-0.5 bg-lsc-cream dark:bg-earth-700 rounded text-xs font-mono">j</kbd>
                <span>{t('notifications.nextNotificationFocusMode')}</span>
              </div>
            </div>
          </div>
          <div className="space-y-2">
            <h4 className="font-medium text-lsc-dark dark:text-lsc-cream">Actions</h4>
            <div className="space-y-1 text-lsc-dark/70 dark:text-lsc-cream/70">
              <div className="flex items-center gap-2">
                <kbd className="px-1.5 py-0.5 bg-lsc-cream dark:bg-earth-700 rounded text-xs font-mono">x</kbd>
                <span>{t('notifications.toggleReadStatusFocusMode')}</span>
              </div>
              <div className="flex items-center gap-2">
                <kbd className="px-1.5 py-0.5 bg-lsc-cream dark:bg-earth-700 rounded text-xs font-mono">Enter</kbd>
                <span>{t('notifications.viewDetailsFocusMode')}</span>
              </div>
              <div className="flex items-center gap-2">
                <kbd className="px-1.5 py-0.5 bg-lsc-cream dark:bg-earth-700 rounded text-xs font-mono">r</kbd>
                <span>Refresh notifications</span>
              </div>
              <div className="flex items-center gap-2">
                <kbd className="px-1.5 py-0.5 bg-lsc-cream dark:bg-earth-700 rounded text-xs font-mono">Ctrl</kbd>
                <span>+</span>
                <kbd className="px-1.5 py-0.5 bg-lsc-cream dark:bg-earth-700 rounded text-xs font-mono">z</kbd>
                <span>Undo delete</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </details>
  )
}
