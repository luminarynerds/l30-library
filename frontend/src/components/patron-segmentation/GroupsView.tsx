/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Users, Plus, Edit3, Trash2, Mail, Download, Eye, ChevronRight } from "lucide-react"
import type { PatronGroup, GroupDetail, GroupStats } from "../../api/patron-segmentation-api"

interface Props {
  groups: PatronGroup[]
  selectedGroup: GroupDetail | null
  groupStats: GroupStats | null
  onCreateGroup: () => void
  onViewGroup: (groupId: number) => void
  onEditGroup: (group: PatronGroup) => void
  onSendMessage: () => void
  onExportGroup: (groupId: number) => void
  onDeleteGroup: (group: PatronGroup) => void
}

export function GroupsView({
  groups,
  selectedGroup,
  groupStats,
  onCreateGroup,
  onViewGroup,
  onEditGroup,
  onSendMessage,
  onExportGroup,
  onDeleteGroup,
}: Props) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm overflow-hidden">
        <div className="p-4 border-b border-lsc-border dark:border-earth-700">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
            Patron Groups ({groups.length})
          </h3>
        </div>
        {groups.length === 0 ? (
          <div className="p-8 text-center">
            <Users className="w-12 h-12 mx-auto text-lsc-dark/30 dark:text-lsc-cream/60 mb-4" />
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
              No groups found
            </p>
            <button
              onClick={onCreateGroup}
              className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose/90 transition-colors"
            >
              <Plus className="w-4 h-4" />
              Create Group
            </button>
          </div>
        ) : (
          <div className="divide-y divide-lsc-border dark:divide-earth-700 max-h-[600px] overflow-auto">
            {groups.map((group) => (
              <button
                key={group.id}
                onClick={() => onViewGroup(group.id)}
                className={`w-full p-4 text-left hover:bg-lsc-cream/50 dark:hover:bg-lsc-brown/20 transition-colors ${
                  selectedGroup?.id === group.id ? "bg-lsc-cream dark:bg-lsc-brown/30" : ""
                }`}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-lsc-dark dark:text-lsc-cream">
                        {group.name}
                      </span>
                      {!group.is_active && (
                        <span className="px-2 py-0.5 bg-earth-100 dark:bg-earth-700 rounded text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                          Inactive
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                      {group.member_count} members
                    </p>
                  </div>
                  <ChevronRight className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm overflow-hidden">
        {selectedGroup ? (
          <>
            <div className="p-4 border-b border-lsc-border dark:border-earth-700">
              <div className="flex items-center justify-between">
                <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
                  {selectedGroup.name}
                </h3>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => onEditGroup(selectedGroup)}
                    className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose dark:hover:text-lsc-rose-light hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 rounded-lg transition-colors"
                    title="Edit group"
                  >
                    <Edit3 className="w-4 h-4" />
                  </button>
                  <button
                    onClick={onSendMessage}
                    className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose dark:hover:text-lsc-rose-light hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 rounded-lg transition-colors"
                    title="Send message"
                  >
                    <Mail className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => onExportGroup(selectedGroup.id)}
                    className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose dark:hover:text-lsc-rose-light hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 rounded-lg transition-colors"
                    title="Export members"
                  >
                    <Download className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => onDeleteGroup(selectedGroup)}
                    className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-status-danger-600 dark:hover:text-status-danger-400 hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 rounded-lg transition-colors"
                    title="Delete group"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
              {selectedGroup.description && (
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">
                  {selectedGroup.description}
                </p>
              )}
            </div>

            {groupStats && (
              <div className="grid grid-cols-2 gap-4 p-4 bg-lsc-cream/50 dark:bg-lsc-brown/20">
                <div>
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Members</p>
                  <p className="text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
                    {groupStats.member_count}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Active Checkouts</p>
                  <p className="text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
                    {groupStats.active_checkouts}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Total Checkouts</p>
                  <p className="text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
                    {groupStats.total_checkouts}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Unpaid Fines</p>
                  <p className="text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
                    ${groupStats.unpaid_fines}
                  </p>
                </div>
              </div>
            )}

            <div className="p-4">
              <h4 className="font-medium text-lsc-dark dark:text-lsc-cream mb-3">
                Members ({selectedGroup.members.length})
              </h4>
              <div className="space-y-2 max-h-[300px] overflow-auto">
                {selectedGroup.members.map((member) => (
                  <div
                    key={member.id}
                    className="flex items-center justify-between p-2 rounded-lg bg-lsc-cream/50 dark:bg-lsc-brown/20"
                  >
                    <div>
                      <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                        {member.patron_name}
                      </p>
                      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                        {member.patron_email}
                      </p>
                    </div>
                    {member.role && (
                      <span className="text-xs px-2 py-0.5 bg-earth-100 dark:bg-earth-800/30 text-lsc-rose dark:text-lsc-rose-light rounded">
                        {member.role}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </>
        ) : (
          <div className="p-8 text-center">
            <Eye className="w-12 h-12 mx-auto text-lsc-dark/30 dark:text-lsc-cream/60 mb-4" />
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
              Select a group to view details
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
