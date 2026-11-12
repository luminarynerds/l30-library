/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'
import { BoardDecisionLinkCreateData, BoardDecisionType } from '@/api/domains/admin/strategic-api'

interface Props {
  data: Partial<BoardDecisionLinkCreateData> & { meeting_date: string; decision_type: BoardDecisionType }
  setData: (v: Props['data']) => void
  onSave: () => void
  onClose: () => void
}

const decisionTypes: { value: BoardDecisionType; label: string }[] = [
  { value: 'approval', label: 'Approval' },
  { value: 'funding', label: 'Funding' },
  { value: 'amendment', label: 'Amendment' },
  { value: 'closure', label: 'Closure' },
]

export default function BoardDecisionModal({ data, setData, onSave, onClose }: Props) {
  return (
    <ModalBackdrop onClose={onClose} title="Link Board Decision">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg w-full max-w-xl max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
            Link Board Decision
          </h3>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Meeting Date *</label>
                <input
                  type="date"
                  value={data.meeting_date?.split('T')[0] || ''}
                  onChange={(e) => setData({ ...data, meeting_date: e.target.value })}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
                />
              </div>
              <div>
                <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Decision Type *</label>
                <select
                  value={data.decision_type}
                  onChange={(e) => setData({ ...data, decision_type: e.target.value as BoardDecisionType })}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
                >
                  {decisionTypes.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </div>
            </div>
            <div>
              <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Meeting Reference</label>
              <input
                type="text"
                value={data.meeting_reference || ''}
                onChange={(e) => setData({ ...data, meeting_reference: e.target.value })}
                placeholder="e.g. Board Meeting 2026-01"
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
              />
            </div>
            <div>
              <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Decision Summary</label>
              <textarea
                value={data.decision_summary || ''}
                onChange={(e) => setData({ ...data, decision_summary: e.target.value })}
                rows={3}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream resize-none"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Vote Result</label>
                <input
                  type="text"
                  value={data.vote_result || ''}
                  onChange={(e) => setData({ ...data, vote_result: e.target.value })}
                  placeholder="e.g. 5-0"
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
                />
              </div>
              <div>
                <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Resolution Number</label>
                <input
                  type="text"
                  value={data.resolution_number || ''}
                  onChange={(e) => setData({ ...data, resolution_number: e.target.value })}
                  placeholder="e.g. 2026-003"
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Minutes URL</label>
              <input
                type="text"
                value={data.minutes_url || ''}
                onChange={(e) => setData({ ...data, minutes_url: e.target.value })}
                placeholder="https://"
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
              />
            </div>
          </div>
          <div className="flex justify-end gap-2 mt-6">
            <button
              onClick={onClose}
              className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-xl"
            >
              Cancel
            </button>
            <button
              onClick={onSave}
              disabled={!data.meeting_date}
              className="px-4 py-2 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose disabled:opacity-50"
            >
              Link Decision
            </button>
          </div>
        </div>
      </div>
    </ModalBackdrop>
  )
}
