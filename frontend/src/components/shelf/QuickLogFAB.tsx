/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Pencil } from 'lucide-react'
import { useReadingStatus } from '@/hooks/useReadingStatus'
import type { ReadingStatusRecord } from '@/api/domains/content/reading-status-api'
import { t } from '@/i18n'

interface QuickLogFABProps {
  onClick: () => void
}

export default function QuickLogFAB({ onClick }: QuickLogFABProps) {
  const { allStatuses } = useReadingStatus()
  const hasCurrentlyReading = allStatuses.some(
    (s: ReadingStatusRecord) => s.status === 'currently_reading',
  )

  if (!hasCurrentlyReading) return null

  return (
    <button
      onClick={onClick}
      aria-label={t('aria.shelf.logYourReading')}
      className="fixed bottom-20 sm:bottom-6 right-6 z-40 w-14 h-14 rounded-full bg-lsc-rose text-white shadow-lg hover:bg-lsc-rose/90 flex items-center justify-center transition-transform hover:scale-105 motion-reduce:transition-none active:scale-95"
    >
      <Pencil className="w-5 h-5" aria-hidden="true" />
    </button>
  )
}
