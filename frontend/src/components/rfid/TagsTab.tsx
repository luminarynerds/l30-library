/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Tag, List, Plus, Zap } from "lucide-react"
import { useTranslation } from "@/i18n"
import type { RFIDReader, RFIDSession } from "./types"

interface TagsTabProps {
  readers: RFIDReader[]
  sessions: RFIDSession[]
  selectedSession: number
  onSelectSession: (id: number) => void
  tagSimForm: { tag_id: string; signal_strength: number; found_at_location: string }
  onSetTagSimForm: (form: { tag_id: string; signal_strength: number; found_at_location: string }) => void
  batchForm: { count: number; include_registered: boolean; include_unregistered: boolean; delay_ms: number }
  onSetBatchForm: (form: { count: number; include_registered: boolean; include_unregistered: boolean; delay_ms: number }) => void
  testTagsForm: { reader_id: number; count: number }
  onSetTestTagsForm: (form: { reader_id: number; count: number }) => void
  onSimulateScan: () => void
  onSimulateBatchScan: () => void
  onCreateTestTags: () => void
}

export function TagsTab({
  readers,
  sessions,
  selectedSession,
  onSelectSession,
  tagSimForm,
  onSetTagSimForm,
  batchForm,
  onSetBatchForm,
  testTagsForm,
  onSetTestTagsForm,
  onSimulateScan,
  onSimulateBatchScan,
  onCreateTestTags,
}: TagsTabProps) {
  const { t } = useTranslation()

  return (
    <div className="space-y-6">
      <div className="border border-lsc-border dark:border-earth-700 rounded-xl p-4">
        <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-3 flex items-center gap-2">
          <Tag className="w-4 h-4" />Single Tag Scan
        </h3>
        <div className="grid md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Active Session *</label>
            <select
              value={selectedSession}
              onChange={(e) => onSelectSession(parseInt(e.target.value))}
              className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
            >
              <option value={0}>-- Select Session --</option>
              {sessions.map(s => (
                <option key={s.id} value={s.id}>Session #{s.id} - {s.session_type.replace(/_/g, " ")} ({s.reader_name || `Reader ${s.reader_id}`})</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">{t('rFIDSimulator.tagIdOptionalRandomIf')}</label>
            <input
              type="text"
              value={tagSimForm.tag_id}
              onChange={(e) => onSetTagSimForm({ ...tagSimForm, tag_id: e.target.value })}
              placeholder={t('placeholder.rFIDSimulator.e200123456789012')}
              className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream font-mono"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Signal Strength (dBm)</label>
            <input
              type="number"
              value={tagSimForm.signal_strength}
              onChange={(e) => onSetTagSimForm({ ...tagSimForm, signal_strength: parseInt(e.target.value) })}
              min={-100}
              max={0}
              className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">{t('rFIDSimulator.foundAtLocationOptional')}</label>
            <input
              type="text"
              value={tagSimForm.found_at_location}
              onChange={(e) => onSetTagSimForm({ ...tagSimForm, found_at_location: e.target.value })}
              placeholder={t('placeholder.rFIDSimulator.fictionSectionA3')}
              className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
            />
          </div>
        </div>
        <div className="mt-4 flex justify-end">
          <button
            onClick={onSimulateScan}
            disabled={!selectedSession}
            className="px-6 py-2 bg-lsc-rose hover:bg-lsc-rose/90 disabled:bg-earth-300 disabled:cursor-not-allowed text-white rounded-xl font-medium flex items-center gap-2"
          >
            <Zap className="w-4 h-4" />Simulate Scan
          </button>
        </div>
      </div>

      <div className="border border-lsc-border dark:border-earth-700 rounded-xl p-4">
        <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-3 flex items-center gap-2">
          <List className="w-4 h-4" />Batch Tag Scan
        </h3>
        <div className="grid md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Number of Tags (1-50)</label>
            <input
              type="number"
              value={batchForm.count}
              onChange={(e) => onSetBatchForm({ ...batchForm, count: parseInt(e.target.value) || 1 })}
              min={1}
              max={50}
              className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">{t('rFIDSimulator.delayBetweenScansMs')}</label>
            <input
              type="number"
              value={batchForm.delay_ms}
              onChange={(e) => onSetBatchForm({ ...batchForm, delay_ms: parseInt(e.target.value) || 0 })}
              min={0}
              max={5000}
              className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
            />
          </div>
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={batchForm.include_registered}
                onChange={(e) => onSetBatchForm({ ...batchForm, include_registered: e.target.checked })}
                className="w-4 h-4 rounded border-lsc-border"
              />
              <span className="text-sm text-lsc-dark dark:text-lsc-cream">Include Registered Tags</span>
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={batchForm.include_unregistered}
                onChange={(e) => onSetBatchForm({ ...batchForm, include_unregistered: e.target.checked })}
                className="w-4 h-4 rounded border-lsc-border"
              />
              <span className="text-sm text-lsc-dark dark:text-lsc-cream">Include Unregistered Tags</span>
            </label>
          </div>
        </div>
        <div className="mt-4 flex justify-end">
          <button
            onClick={onSimulateBatchScan}
            disabled={!selectedSession}
            className="px-6 py-2 bg-lsc-rose hover:bg-lsc-rose/90 disabled:bg-earth-300 disabled:cursor-not-allowed text-white rounded-xl font-medium flex items-center gap-2"
          >
            <List className="w-4 h-4" />Simulate Batch ({batchForm.count} tags)
          </button>
        </div>
      </div>

      <div className="border border-lsc-border dark:border-earth-700 rounded-xl p-4">
        <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-3 flex items-center gap-2">
          <Plus className="w-4 h-4" />Create Test Tags
        </h3>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">{t('rFIDSimulator.createTestRfidTagsLinked')}</p>
        <div className="grid md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Reader</label>
            <select
              value={testTagsForm.reader_id}
              onChange={(e) => onSetTestTagsForm({ ...testTagsForm, reader_id: parseInt(e.target.value) })}
              className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
            >
              <option value={0}>-- Select Reader --</option>
              {readers.map(r => (
                <option key={r.id} value={r.id}>{r.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Number of Tags (1-100)</label>
            <input
              type="number"
              value={testTagsForm.count}
              onChange={(e) => onSetTestTagsForm({ ...testTagsForm, count: parseInt(e.target.value) || 1 })}
              min={1}
              max={100}
              className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
            />
          </div>
        </div>
        <div className="mt-4 flex justify-end">
          <button
            onClick={onCreateTestTags}
            disabled={!testTagsForm.reader_id}
            className="px-6 py-2 bg-status-success-600 hover:bg-status-success-700 disabled:bg-earth-300 disabled:cursor-not-allowed text-white rounded-xl font-medium flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />Create {testTagsForm.count} Test Tags
          </button>
        </div>
      </div>
    </div>
  )
}
