/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Plus } from "lucide-react"
import { useTranslation } from "@/i18n"
import type { RFIDTag } from "./staff-rfid-types"

interface Props {
  tags: RFIDTag[]
  onProgramNew: () => void
  onToggleSecurity: (tagId: string, currentBit: boolean) => void
}

export function StaffTagsTab({ tags, onProgramNew, onToggleSecurity }: Props) {
  const { t } = useTranslation()
  void t

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">RFID Tags</h2>
        <button onClick={onProgramNew} className="flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium">
          <Plus className="w-4 h-4" />Program New Tag
        </button>
      </div>

      {tags.length === 0 ? (
        <p className="text-center py-8 text-lsc-dark/70 dark:text-lsc-cream/70">No tags registered</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-lsc-cream dark:bg-lsc-brown/50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Tag ID</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Item</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Security</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Last Read</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
              {tags.map((tag) => (
                <tr key={tag.id} className="hover:bg-lsc-cream/50 dark:hover:bg-lsc-brown/50">
                  <td className="px-4 py-3 font-mono text-sm text-lsc-dark dark:text-lsc-cream">{tag.tag_id.substring(0, 16)}...</td>
                  <td className="px-4 py-3">
                    <p className="font-medium text-lsc-dark dark:text-lsc-cream">{tag.item_title || tag.item_barcode}</p>
                    {tag.item_author && <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{tag.item_author}</p>}
                  </td>
                  <td className="px-4 py-3">
                    <span className={"px-2 py-1 text-xs font-medium rounded " + (tag.security_bit ? "bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300" : "bg-status-warning-100 text-status-warning-700")}>
                      {tag.security_bit ? "Secured" : "Desensitized"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    {tag.last_read_at ? new Date(tag.last_read_at).toLocaleDateString() : "Never"}
                    <span className="ml-2 text-xs">({tag.read_count} reads)</span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => onToggleSecurity(tag.tag_id, tag.security_bit)}
                      className={"px-3 py-1 text-xs font-medium rounded-xl " + (tag.security_bit ? "bg-status-warning-100 text-status-warning-700 hover:bg-status-warning-200" : "bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300 hover:bg-status-success-200")}
                    >
                      {tag.security_bit ? "Desensitize" : "Secure"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
