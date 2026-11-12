/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useRef } from "react"
import { X, Printer, BookOpen } from "lucide-react"
import { t } from '@/i18n'
import { useBranding } from '@/contexts/BrandingContext'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface LibraryCardPrintModalProps {
  isOpen: boolean
  onClose: () => void
  patronName: string
  libraryCardNumber?: string | null
  branch?: string
}

export function LibraryCardPrintModal({ isOpen, onClose, patronName, libraryCardNumber, branch }: LibraryCardPrintModalProps) {
  const branding = useBranding()
  const cardRef = useRef<HTMLDivElement>(null)

  if (!isOpen) return null

  const handlePrint = () => {
    if (!cardRef.current) return
    const printWindow = window.open('', '_blank', 'width=450,height=300')
    if (!printWindow) return

    const doc = printWindow.document
    doc.open()

    const style = doc.createElement('style')
    style.textContent = [
      'body { margin: 0; display: flex; justify-content: center; align-items: center; min-height: 100vh; font-family: Georgia, serif; }',
      '.card { width: 3.375in; height: 2.125in; border: 2px solid #333; border-radius: 12px; padding: 16px; box-sizing: border-box; position: relative; }',
      '.header { font-size: 14px; font-weight: bold; color: #92400e; margin-bottom: 12px; }',
      '.name { font-size: 16px; font-weight: bold; margin-bottom: 4px; }',
      '.card-num { font-size: 13px; color: #555; font-family: monospace; letter-spacing: 1px; }',
      '.branch { font-size: 11px; color: #777; position: absolute; bottom: 12px; left: 16px; }',
    ].join('\n')
    doc.head.appendChild(style)
    doc.title = `Library Card - ${patronName}`

    const card = doc.createElement('div')
    card.className = 'card'

    const header = doc.createElement('div')
    header.className = 'header'
    header.textContent = branding.library_short_name
    card.appendChild(header)

    const name = doc.createElement('div')
    name.className = 'name'
    name.textContent = patronName
    card.appendChild(name)

    if (libraryCardNumber) {
      const num = doc.createElement('div')
      num.className = 'card-num'
      num.textContent = libraryCardNumber
      card.appendChild(num)
    }

    if (branch) {
      const br = doc.createElement('div')
      br.className = 'branch'
      br.textContent = branch
      card.appendChild(br)
    }

    doc.body.appendChild(card)
    doc.close()

    printWindow.onload = () => {
      printWindow.print()
      printWindow.close()
    }
  }

  return (
    <ModalBackdrop onClose={onClose} title="Print Library Card">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 max-w-md w-full mx-4">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">Print Library Card</h2>
          <button
            onClick={onClose}
            aria-label={t('aria.authModals.close')}
            className="text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Card Preview */}
        <div ref={cardRef} className="mx-auto max-w-xs border-2 border-lsc-dark/20 dark:border-lsc-cream/20 rounded-xl p-5 bg-gradient-to-br from-lsc-cream to-white dark:from-earth-700 dark:to-earth-800">
          <div className="flex items-center gap-2 mb-4">
            <BookOpen className="w-5 h-5 text-lsc-rose" />
            <span className="font-serif font-bold text-lsc-rose text-sm">{branding.library_short_name}</span>
          </div>
          <div className="text-lg font-bold text-lsc-dark dark:text-lsc-cream mb-1">{patronName}</div>
          {libraryCardNumber && (
            <div className="font-mono text-sm text-lsc-dark/70 dark:text-lsc-cream/60 tracking-wider">{libraryCardNumber}</div>
          )}
          {branch && (
            <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mt-3">{branch}</div>
          )}
        </div>

        <div className="flex justify-end gap-2 mt-6">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream/50 dark:hover:bg-earth-700 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handlePrint}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-lsc-rose rounded-lg hover:bg-lsc-rose/90 transition-colors"
          >
            <Printer className="w-4 h-4" />
            Print Card
          </button>
        </div>
      </div>
    </ModalBackdrop>
  )
}
