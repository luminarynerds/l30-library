/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { Download, Loader2 } from 'lucide-react'
import { downloadPacketPdf } from '@/api/legal-api'
import { useTranslation } from '@/i18n'

interface DownloadPacketButtonProps {
  packetId: number
  packetName: string
  formCount: number
}

export default function DownloadPacketButton({
  packetId,
  packetName,
  formCount,
}: DownloadPacketButtonProps): React.ReactElement {
  const { t } = useTranslation()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleDownload = async () => {
    setLoading(true)
    setError(null)
    try {
      const blob = await downloadPacketPdf(packetId)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${packetName.toLowerCase().replace(/\s+/g, '-')}-forms.pdf`
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      setError(t('components.legal.downloadPacketButton.couldntGeneratePacketTry', "Couldn't generate packet. Try again or download forms individually."))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <button
        onClick={handleDownload}
        disabled={loading}
        className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-xl text-sm font-medium hover:bg-lsc-rose/90 transition-colors disabled:opacity-50"
      >
        {loading ? (
          <>
            <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
            {t('components.legal.downloadPacketButton.generatingPacket', 'Generating packet...')}
          </>
        ) : (
          <>
            <Download aria-hidden="true" className="w-4 h-4" />
            {t('components.legal.downloadPacketButton.downloadPacketForms', { packetName, formCount })}
          </>
        )}
      </button>
      {error && (
        <p className="text-xs text-status-danger-600 dark:text-status-danger-400 mt-2">{error}</p>
      )}
    </div>
  )
}
