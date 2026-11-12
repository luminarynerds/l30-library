/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Moon } from 'lucide-react'
import { useEssentialsMode } from '@/contexts/EssentialsModeContext'
import { useTranslation } from '@/i18n'

export default function SensoryQuietEntry(): React.ReactElement | null {
  const { t } = useTranslation()
  const { isEssentialsMode, toggleMode, isLoading } = useEssentialsMode()

  // Already in calm mode — no entry link needed.
  if (isEssentialsMode) return null

  return (
    <div className="mb-6 flex justify-end">
      <button
        type="button"
        onClick={() => { void toggleMode() }}
        disabled={isLoading}
        className="inline-flex items-center gap-2 text-sm text-lsc-dark dark:text-lsc-cream underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2 rounded-lg px-2 py-1 disabled:opacity-50"
      >
        <Moon aria-hidden="true" className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light" />
        <span>
          {t(
            'aITools.sensoryQuietEntry',
            'Looking for the calm version of this page? Switch to Sensory Quiet Mode.',
          )}
        </span>
      </button>
    </div>
  )
}
