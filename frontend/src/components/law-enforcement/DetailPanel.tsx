/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import {
  X,
  FileText,
  CheckSquare,
  Activity,
  Gavel,
  Shield,
  Clock,
  Users,
  AlertCircle,
  Send,
  Loader2,
} from 'lucide-react'
import { useTranslation, getCurrentLocale } from '@/i18n'
import type {
  LawEnforcementRequestDetail,
  ChecklistItem,
  AuditLogEntry,
  WorkflowActionType,
} from './types'
import FocusTrap from 'focus-trap-react'

interface DetailPanelProps {
  request: LawEnforcementRequestDetail
  detailLoading: boolean
  detailTab: 'overview' | 'checklist' | 'audit'
  checklist: ChecklistItem[]
  auditLog: AuditLogEntry[]
  noteText: string
  onNoteChange: (text: string) => void
  onClose: () => void
  onTabChange: (tab: 'overview' | 'checklist' | 'audit') => void
  onChecklistToggle: (itemId: number, completed: boolean) => void
  onAddNote: () => void
  onWorkflowAction: (action: WorkflowActionType, data: Record<string, unknown>) => void
  getStatusColor: (status: string) => string
  formatDate: (dateStr: string) => string
}

function DetailField({
  label,
  value,
  icon,
}: {
  label: string
  value?: string | null
  icon?: React.ReactNode
}): React.ReactElement {
  return (
    <div className="py-3 border-b border-lsc-border dark:border-earth-700 last:border-0">
      <div className="flex items-start gap-3">
        {icon && <div className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{icon}</div>}
        <div className="flex-1">
          <p className="text-xs uppercase text-lsc-dark/70 dark:text-lsc-cream/70 font-medium">
            {label}
          </p>
          <p className="text-lsc-dark dark:text-lsc-cream mt-1">
            {value || <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Not set</span>}
          </p>
        </div>
      </div>
    </div>
  )
}

export function DetailPanel({
  request,
  detailLoading,
  detailTab,
  checklist,
  auditLog,
  noteText,
  onNoteChange,
  onClose,
  onTabChange,
  onChecklistToggle,
  onAddNote,
  onWorkflowAction,
  getStatusColor,
  formatDate,
}: DetailPanelProps): React.ReactElement {
  const { t } = useTranslation()

  return (
    <div
      className="fixed inset-0 z-50 overflow-hidden"
      role="presentation"
      onKeyDown={(e) => { if (e.key === 'Escape') onClose() }}
    >
      <div className="absolute inset-0 bg-black/50" onClick={onClose} aria-hidden="true" />
            <FocusTrap active={true} focusTrapOptions={{ escapeDeactivates: false, allowOutsideClick: true, returnFocusOnDeactivate: true, fallbackFocus: () => document.body }}>
<div
        className="absolute right-0 top-0 h-full w-full max-w-2xl bg-lsc-white dark:bg-earth-800 shadow-lg overflow-y-auto flex flex-col"
        role="dialog"
        aria-modal="true"
        aria-labelledby="detail-panel-title"
      >
        <div className="sticky top-0 border-b border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 p-4 flex items-center justify-between">
          <div className="flex-1">
            <h2 id="detail-panel-title" className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">
              {request.tracking_number}
            </h2>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              {request.requesting_agency}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
            aria-label={t('aria.adminLawEnforcement.closeDetailPanel')}
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        <div className="flex gap-4 px-4 border-b border-lsc-border dark:border-earth-700 bg-lsc-cream/50 dark:bg-earth-700/30">
          {(['overview', 'checklist', 'audit'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => onTabChange(tab)}
              className={`px-4 py-3 font-medium border-b-2 transition-colors ${
                detailTab === tab
                  ? 'border-lsc-rose text-lsc-rose'
                  : 'border-transparent text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream'
              }`}
            >
              {tab === 'overview' && <><FileText className="w-4 h-4 inline mr-2" />Overview</>}
              {tab === 'checklist' && <><CheckSquare className="w-4 h-4 inline mr-2" />Checklist</>}
              {tab === 'audit' && <><Activity className="w-4 h-4 inline mr-2" />Audit Log</>}
            </button>
          ))}
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-6">
          {detailLoading ? (
            <div className="flex items-center justify-center min-h-[300px]">
              <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
            </div>
          ) : detailTab === 'overview' ? (
            <div className="space-y-6">
              <div className="bg-lsc-cream dark:bg-earth-700/30 rounded-xl p-4">
                <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-3 flex items-center gap-2">
                  <Gavel className="w-5 h-5" />
                  Workflow Actions
                </h3>
                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={() => onWorkflowAction('legal_review', { status: request.legal_review_status })}
                    className="px-3 py-2 bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-700 dark:text-status-warning-300 rounded-lg text-sm font-medium hover:bg-status-warning-200 dark:hover:bg-status-warning-900/50"
                  >
                    Legal Review
                  </button>
                  <button
                    onClick={() => onWorkflowAction('workflow_status', { status: request.workflow_status })}
                    className="px-3 py-2 bg-earth-100 dark:bg-earth-800/30 text-lsc-rose dark:text-lsc-rose-light rounded-lg text-sm font-medium hover:bg-earth-200 dark:hover:bg-earth-800/50"
                  >
                    Change Status
                  </button>
                  <button
                    onClick={() => onWorkflowAction('response', { response_date: request.response_date })}
                    className="px-3 py-2 bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300 rounded-lg text-sm font-medium hover:bg-status-success-200 dark:hover:bg-status-success-900/50"
                  >
                    Record Response
                  </button>
                  <button
                    onClick={() => onWorkflowAction('patron_notification', { notification_date: request.patron_notification_date })}
                    className="px-3 py-2 bg-category-100 dark:bg-category-900/30 text-category-700 dark:text-category-300 rounded-lg text-sm font-medium hover:bg-category-200 dark:hover:bg-category-900/50"
                  >
                    Notify Patron
                  </button>
                </div>
              </div>

              <div className="bg-lsc-white dark:bg-earth-700/30 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
                <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">Request Details</h3>
                <div className="space-y-2">
                  <DetailField label="Tracking Number" value={request.tracking_number} icon={<FileText className="w-4 h-4" />} />
                  <DetailField label="Agency" value={request.requesting_agency} icon={<Shield className="w-4 h-4" />} />
                  <DetailField label="Request Type" value={request.request_type.replace(/_/g, ' ')} />
                  <DetailField label="Date Received" value={formatDate(request.date_received)} icon={<Clock className="w-4 h-4" />} />
                  <DetailField label="Data Requested" value={request.data_requested} />
                  {request.patron_name_on_request && (
                    <DetailField label="Patron Name" value={request.patron_name_on_request} icon={<Users className="w-4 h-4" />} />
                  )}
                </div>
              </div>

              <div className="bg-lsc-white dark:bg-earth-700/30 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
                <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
                  <Gavel className="w-5 h-5" />
                  Legal Review
                </h3>
                <div className="space-y-2">
                  <div className="py-3">
                    <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(request.legal_review_status)}`}>
                      {request.legal_review_status.replace(/_/g, ' ')}
                    </span>
                  </div>
                  {request.legal_review_notes && (
                    <DetailField label="Review Notes" value={request.legal_review_notes} />
                  )}
                  {request.denial_reason && (
                    <DetailField label="Denial Reason" value={request.denial_reason} icon={<AlertCircle className="w-4 h-4" />} />
                  )}
                </div>
              </div>

              {request.response_summary && (
                <div className="bg-lsc-white dark:bg-earth-700/30 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
                  <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">Response</h3>
                  <div className="space-y-2">
                    {request.response_date && (
                      <DetailField label="Response Date" value={formatDate(request.response_date)} icon={<Clock className="w-4 h-4" />} />
                    )}
                    <DetailField label="Summary" value={request.response_summary} />
                  </div>
                </div>
              )}

              {request.patron_notification_date && (
                <div className="bg-lsc-white dark:bg-earth-700/30 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
                  <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">Patron Notification</h3>
                  <DetailField label="Notification Date" value={formatDate(request.patron_notification_date)} icon={<Clock className="w-4 h-4" />} />
                </div>
              )}
            </div>
          ) : detailTab === 'checklist' ? (
            <div className="space-y-4">
              {checklist.length === 0 ? (
                <div className="text-center py-8 text-lsc-dark/70 dark:text-lsc-cream/70">
                  <CheckSquare className="w-12 h-12 mx-auto opacity-50 mb-3" />
                  <p>No checklist items</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {checklist.map((item) => (
                    <div key={item.id} className="flex items-start gap-3 p-3 border border-lsc-border dark:border-earth-700 rounded-lg">
                      <input
                        type="checkbox"
                        checked={item.completed}
                        onChange={(e) => onChecklistToggle(item.id, e.target.checked)}
                        className="mt-1 w-5 h-5 text-lsc-rose rounded"
                      />
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <p className={`font-medium ${item.completed ? 'line-through text-lsc-dark/70 dark:text-lsc-cream/70' : 'text-lsc-dark dark:text-lsc-cream'}`}>
                            {item.name}
                          </p>
                          {item.required && (
                            <span className="px-2 py-1 text-xs font-medium bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-300 rounded">
                              Required
                            </span>
                          )}
                        </div>
                        {item.description && (
                          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                            {item.description}
                          </p>
                        )}
                        {item.completed && item.completed_date && (
                          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">
                            Completed {formatDate(item.completed_date)}
                            {item.completed_by && ` by ${item.completed_by}`}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <div className="mt-6 pt-6 border-t border-lsc-border dark:border-earth-700">
                <h4 className="font-medium text-lsc-dark dark:text-lsc-cream mb-3">Add Note</h4>
                <div className="space-y-3">
                  <textarea
                    value={noteText}
                    onChange={(e) => onNoteChange(e.target.value)}
                    rows={3}
                    placeholder={t('admin.adminLawEnforcement.addANoteToThis')}
                    className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                  />
                  <button
                    onClick={onAddNote}
                    className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90"
                  >
                    <Send className="w-4 h-4" />
                    Add Note
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {auditLog.length === 0 ? (
                <div className="text-center py-8 text-lsc-dark/70 dark:text-lsc-cream/70">
                  <Activity className="w-12 h-12 mx-auto opacity-50 mb-3" />
                  <p>{t('admin.adminLawEnforcement.noAuditLogEntries')}</p>
                </div>
              ) : (
                <div className="relative">
                  <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-lsc-border dark:bg-earth-700" />
                  <div className="space-y-6 pl-12">
                    {auditLog.map((entry) => (
                      <div key={entry.id} className="relative">
                        <div className="absolute -left-8 top-2 w-4 h-4 bg-lsc-rose rounded-full border-4 border-lsc-white dark:border-earth-800" />
                        <div className="bg-lsc-cream dark:bg-earth-700/30 rounded-lg p-3">
                          <div className="flex items-start justify-between gap-2">
                            <div className="flex-1">
                              <p className="font-medium text-lsc-dark dark:text-lsc-cream">
                                {entry.action}
                              </p>
                              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                                {entry.actor} ({entry.actor_role})
                              </p>
                              {entry.change_summary && (
                                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">
                                  {entry.change_summary}
                                </p>
                              )}
                            </div>
                            <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 whitespace-nowrap">
                              {new Date(entry.timestamp).toLocaleString(getCurrentLocale(), {
                                year: 'numeric',
                                month: 'short',
                                day: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit',
                              })}
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
      </FocusTrap>
    </div>
  )
}
