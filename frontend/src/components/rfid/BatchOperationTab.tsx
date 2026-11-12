/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { ShoppingCart, RotateCcw, Zap, X, CheckCircle, XCircle } from "lucide-react"
import { useTranslation } from "@/i18n"
import type { StaffRFIDReader, BatchResult } from "./staff-rfid-types"

interface Props {
  activeTab: "checkout" | "checkin"
  readers: StaffRFIDReader[]
  selectedReader: number
  setSelectedReader: (id: number) => void
  patronId: string
  setPatronId: (id: string) => void
  tagInput: string
  setTagInput: (v: string) => void
  scannedTags: string[]
  onAddTag: () => void
  onRemoveTag: (tag: string) => void
  onClearAll: () => void
  onProcess: () => void
  results: BatchResult[]
}

export function BatchOperationTab({
  activeTab,
  readers,
  selectedReader,
  setSelectedReader,
  patronId,
  setPatronId,
  tagInput,
  setTagInput,
  scannedTags,
  onAddTag,
  onRemoveTag,
  onClearAll,
  onProcess,
  results,
}: Props) {
  const { t } = useTranslation()

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
          {activeTab === "checkout" ? <><ShoppingCart className="w-5 h-5" />Batch Checkout</> : <><RotateCcw className="w-5 h-5" />Batch Checkin</>}
        </h2>
        <button onClick={onClearAll} className="text-sm text-lsc-rose hover:underline">Clear All</button>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Select Reader</label>
          <select
            value={selectedReader}
            onChange={(e) => setSelectedReader(parseInt(e.target.value))}
            className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
          >
            <option value={0}>-- Select Reader --</option>
            {readers.filter(r => r.status === "online").map(r => (
              <option key={r.id} value={r.id}>{r.name} ({r.location || "No location"})</option>
            ))}
          </select>
        </div>
        {activeTab === "checkout" && (
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Patron ID</label>
            <input
              type="text"
              value={patronId}
              onChange={(e) => setPatronId(e.target.value)}
              placeholder={t('placeholder.staffRFID.enterPatronId')}
              className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
            />
          </div>
        )}
      </div>

      <div className="border border-lsc-border dark:border-earth-700 rounded-xl p-4">
        <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-3 flex items-center gap-2">
          <Zap className="w-4 h-4" />Scan Tags
        </h3>
        <div className="flex gap-2 mb-4">
          <input
            type="text"
            value={tagInput}
            onChange={(e) => setTagInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && onAddTag()}
            placeholder={t('staffRFID.scanOrEnterTagId')}
            className="flex-1 px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream font-mono"
            autoFocus
          />
          <button onClick={onAddTag} className="px-4 py-2 bg-lsc-cream dark:bg-lsc-brown hover:bg-lsc-cream/80 text-lsc-dark dark:text-lsc-cream rounded-xl font-medium">Add</button>
        </div>

        {scannedTags.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-4">
            {scannedTags.map((tag) => (
              <span key={tag} className="inline-flex items-center gap-1 px-3 py-1 bg-lsc-rose/10 text-lsc-rose rounded-full text-sm font-mono">
                {tag}
                <button onClick={() => onRemoveTag(tag)} className="hover:text-status-danger-600" aria-label={`Remove tag ${tag}`}><X aria-hidden="true" className="w-3 h-3" /></button>
              </span>
            ))}
          </div>
        )}

        <div className="flex justify-between items-center">
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{scannedTags.length} tag(s) scanned</p>
          <button
            onClick={onProcess}
            disabled={scannedTags.length === 0 || !selectedReader || (activeTab === "checkout" && !patronId)}
            className="px-6 py-2 bg-lsc-rose hover:bg-lsc-rose/90 disabled:bg-earth-300 disabled:cursor-not-allowed text-white rounded-xl font-medium flex items-center gap-2"
          >
            {activeTab === "checkout" ? <><ShoppingCart className="w-4 h-4" />Process Checkout</> : <><RotateCcw className="w-4 h-4" />Process Checkin</>}
          </button>
        </div>
      </div>

      {results.length > 0 && (
        <div className="space-y-2">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Results</h3>
          {results.map((result, idx) => (
            <div key={idx} className={"flex items-center justify-between p-3 rounded-lg " + (result.success ? "bg-status-success-50 dark:bg-status-success-900/20" : "bg-status-danger-50 dark:bg-status-danger-900/20")}>
              <div className="flex items-center gap-3">
                {result.success ? <CheckCircle className="w-5 h-5 text-status-success-600" /> : <XCircle className="w-5 h-5 text-status-danger-600" />}
                <div>
                  <p className="font-medium text-sm text-lsc-dark dark:text-lsc-cream">{result.item_title || result.tag_id}</p>
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{result.item_barcode}</p>
                </div>
              </div>
              <div className="text-right">
                <p className={"text-sm " + (result.success ? "text-status-success-600" : "text-status-danger-600")}>{result.message}</p>
                {result.due_date && <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Due: {new Date(result.due_date).toLocaleDateString()}</p>}
                {result.fine_amount && <p className="text-xs text-status-danger-600">Fine: ${result.fine_amount.toFixed(2)}</p>}
                {result.next_hold_patron && <p className="text-xs text-lsc-rose">Hold for: {result.next_hold_patron}</p>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
