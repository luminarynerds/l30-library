/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useState } from "react"
import { fetchApi } from '@/lib/api-client'
import {
  AlertTriangle,
  CheckCircle,
  AlertCircle,
  AlertOctagon,
  Info,
  Lock,
  Gift,
  CreditCard,
  ArrowRightLeft,
  RefreshCw,
  IdCard,
  CheckCircle2,
  ShieldCheck,
  Phone,
  Users,
  Bookmark,
  MoreVertical,
  X,
} from "lucide-react"
import { useTranslation } from '@/i18n'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface ResolutionAction {
  action_type: string
  label: string
  description: string
  required_input?: string
  icon: string
}

interface ProblemDetails {
  problem_type: string
  title: string
  description: string
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  context: Record<string, any>
  solutions: string[]
  actions: ResolutionAction[]
  severity: string
}

interface ProblemResolutionModalProps {
  problem: ProblemDetails
  patronId: number
  itemId?: number
  onClose: () => void
  onActionExecuted: (actionType: string) => void
  onRetryCheckout: () => void
  isLoading?: boolean
}

export default function ProblemResolutionModal({
  problem,
  patronId,
  itemId,
  onClose,
  onActionExecuted,
  onRetryCheckout,
  isLoading: _isLoading = false,
}: ProblemResolutionModalProps): React.ReactElement {
  const { t } = useTranslation()
  const [selectedAction, setSelectedAction] = useState<ResolutionAction | null>(null)
  const [inputValue, setInputValue] = useState("")
  const [actionInProgress, setActionInProgress] = useState(false)
  const [expandedSolutions, setExpandedSolutions] = useState(false)

  // Determine severity styling
  const severityColors = {
    info: { bg: "bg-earth-50 dark:bg-earth-800/20", border: "border-lsc-border dark:border-earth-700", text: "text-lsc-rose dark:text-lsc-rose-light" },
    warning: { bg: "bg-status-warning-50 dark:bg-status-warning-900/20", border: "border-status-warning-200 dark:border-status-warning-800", text: "text-status-warning-700 dark:text-status-warning-300" },
    error: { bg: "bg-status-danger-50 dark:bg-status-danger-900/20", border: "border-status-danger-200 dark:border-status-danger-800", text: "text-status-danger-700 dark:text-status-danger-300" },
    critical: { bg: "bg-status-danger-100 dark:bg-status-danger-900/30", border: "border-status-danger-300 dark:border-earth-700", text: "text-status-danger-800 dark:text-status-danger-300" },
  }
  const colors = severityColors[problem.severity as keyof typeof severityColors] || severityColors.warning

  // Severity icon
  const severityIconMap = {
    info: Info,
    warning: AlertTriangle,
    error: AlertCircle,
    critical: AlertOctagon,
  }
  const SeverityIcon = severityIconMap[problem.severity as keyof typeof severityIconMap] || AlertTriangle

  // Action icon mapping
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const ActionIcons: Record<string, React.ComponentType<any>> = {
    check: CheckCircle,
    "lock-open": Lock,
    gift: Gift,
    "credit-card": CreditCard,
    "arrows-h": ArrowRightLeft,
    refresh: RefreshCw,
    "id-card": IdCard,
    "check-circle": CheckCircle2,
    "shield-check": ShieldCheck,
    phone: Phone,
    "user-tie": Users,
    bookmark: Bookmark,
    "exclamation-triangle": AlertTriangle,
    plus: CheckCircle,
  }

  const handleActionClick = (action: ResolutionAction) => {
    setSelectedAction(action)
    setInputValue("")
  }

  const handleExecuteAction = async () => {
    if (!selectedAction) return

    setActionInProgress(true)
    try {
      const result = await fetchApi('/circulation/resolve-problem', {
        method: 'POST',
        body: JSON.stringify({
          problem_type: problem.problem_type,
          action_type: selectedAction.action_type,
          input_data: {
            patron_id: patronId,
            item_id: itemId,
            ...parseInputData(),
          },
        }),
      })

      if (result.success) {
        onActionExecuted(selectedAction.action_type)

        // Show success message
        const message = result.message || `${selectedAction.label} completed`
        alert(message)

        // For override actions, allow retry checkout
        if (selectedAction.action_type === "override") {
          setTimeout(() => {
            setSelectedAction(null)
            setInputValue("")
            onRetryCheckout()
          }, 500)
        } else {
          // Close modal for other actions
          setTimeout(() => {
            setSelectedAction(null)
            setInputValue("")
            onClose()
          }, 500)
        }
      } else {
        alert(`Action failed: ${result.message}`)
      }
    } catch (error) {
      alert(`Error: ${error instanceof Error ? error.message : "an unexpected issue"}`)
    } finally {
      setActionInProgress(false)
    }
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const parseInputData = (): Record<string, any> => {
    if (!selectedAction?.required_input) return {}

    switch (selectedAction.required_input) {
      case "payment_amount":
        return { payment_amount: parseFloat(inputValue) || 0 }
      case "override_reason":
      case "verification_notes":
      case "waive_reason":
        return { [selectedAction.required_input]: inputValue }
      case "item_to_return_id":
        return { item_to_return_id: parseInt(inputValue) || 0 }
      default:
        return { input: inputValue }
    }
  }

  const getInputPlaceholder = (): string => {
    switch (selectedAction?.required_input) {
      case "payment_amount":
        return "Enter payment amount (e.g., 12.50)"
      case "override_reason":
        return "Reason for override (e.g., ID verified, emergency)"
      case "verification_notes":
        return "Staff verification notes"
      case "waive_reason":
        return "Reason for waiving fines"
      case "item_to_return_id":
        return "Select item ID to return"
      default:
        return "Enter required information"
    }
  }

  return (
    <ModalBackdrop onClose={onClose} title="Problem Resolution">
      <div className={`${colors.bg} ${colors.border} border rounded-lg max-w-2xl w-full max-h-96 overflow-y-auto shadow-lg`}>
        {/* Header */}
        <div className="flex items-start justify-between p-6 border-b sticky top-0 bg-lsc-white dark:bg-earth-800">
          <div className="flex items-start gap-4 flex-1">
            <SeverityIcon className={`${colors.text} h-6 w-6 flex-shrink-0 mt-1`} />
            <div className="flex-1">
              <h2 className="font-serif text-lg font-bold text-lsc-dark dark:text-lsc-cream">{problem.title}</h2>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{problem.description}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label={t('aria.addRoleModal.closeModal')}
            className="text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-earth-600 dark:hover:text-earth-300 flex-shrink-0"
            disabled={actionInProgress}
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Context Information */}
          {Object.keys(problem.context).length > 0 && (
            <div className="bg-lsc-white dark:bg-earth-800 rounded-lg p-4 border border-lsc-border dark:border-earth-700">
              <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2">Details</h3>
              <dl className="grid grid-cols-1 gap-2 text-sm">
                {Object.entries(problem.context).map(([key, value]) => {
                  if (Array.isArray(value)) return null // Skip arrays for now
                  return (
                    <div key={key} className="flex justify-between">
                      <dt className="text-lsc-dark/70 dark:text-lsc-cream/70 font-medium">{humanizeKey(key)}:</dt>
                      <dd className="text-lsc-dark dark:text-lsc-cream font-semibold">{formatValue(value)}</dd>
                    </div>
                  )
                })}
              </dl>
            </div>
          )}

          {/* Suggested Solutions */}
          {problem.solutions.length > 0 && (
            <div className="bg-lsc-white dark:bg-earth-800 rounded-lg p-4 border border-lsc-border dark:border-earth-700">
              <button
                onClick={() => setExpandedSolutions(!expandedSolutions)}
                className="flex items-center justify-between w-full"
              >
                <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Suggested Solutions</h3>
                <MoreVertical className={`h-4 w-4 transition-transform ${expandedSolutions ? "rotate-180" : ""}`} />
              </button>
              {expandedSolutions && (
                <ul className="mt-3 space-y-2">
                  {problem.solutions.map((solution, idx) => (
                    <li key={idx} className="flex gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      <span className="text-lsc-dark/70 dark:text-lsc-cream/70">•</span>
                      <span>{solution}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {/* Resolution Actions */}
          {!selectedAction ? (
            <div>
              <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-3">Available Actions</h3>
              <div className="grid grid-cols-1 gap-2">
                {problem.actions.map((action) => {
                  const IconComponent = ActionIcons[action.icon] || CheckCircle
                  return (
                    <button
                      key={action.action_type}
                      onClick={() => handleActionClick(action)}
                      disabled={actionInProgress}
                      className="p-3 rounded-lg border border-lsc-border dark:border-earth-700 hover:border-lsc-rose/50 hover:bg-earth-50 dark:bg-earth-800/20 dark:hover:bg-earth-800/20 text-left transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <div className="flex items-start gap-3">
                        <IconComponent className="h-5 w-5 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0 mt-0.5" />
                        <div className="flex-1">
                          <div className="font-semibold text-lsc-dark dark:text-lsc-cream">{action.label}</div>
                          <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{action.description}</div>
                        </div>
                      </div>
                    </button>
                  )
                })}
              </div>
            </div>
          ) : (
            // Action Input Form
            <div className="bg-lsc-white dark:bg-earth-800 rounded-lg p-4 border border-lsc-border dark:border-earth-700">
              <button
                onClick={() => setSelectedAction(null)}
                className="text-sm text-lsc-rose dark:text-lsc-rose-light hover:text-lsc-rose dark:text-lsc-rose-light mb-3"
              >
                ← Back to actions
              </button>

              <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-3">{selectedAction.label}</h3>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">{selectedAction.description}</p>

              {selectedAction.required_input && (
                <div className="mb-4">
                  {selectedAction.required_input === "item_to_return_id" ? (
                    // Show list of current checkouts
                    <div className="space-y-2">
                      <label htmlFor="return-item-select" className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">{t('components.staff.problemResolution.selectItemToReturn')}</label>
                      {problem.context.items_checked_out?.length > 0 ? (
                        <select
                          id="return-item-select"
                          value={inputValue}
                          onChange={(e) => setInputValue(e.target.value)}
                          className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg text-sm"
                        >
                          <option value="">Choose an item...</option>
                          {problem.context.items_checked_out.map((item: { checkout_id: number; item_title: string; days_until_due: number }) => (
                            <option key={item.checkout_id} value={item.checkout_id}>
                              {item.item_title} (Due: {item.days_until_due} days)
                            </option>
                          ))}
                        </select>
                      ) : (
                        <input
                          type="number"
                          value={inputValue}
                          onChange={(e) => setInputValue(e.target.value)}
                          placeholder={getInputPlaceholder()}
                          className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg text-sm"
                        />
                      )}
                    </div>
                  ) : (
                    <input
                      type={selectedAction.required_input === "payment_amount" ? "number" : "text"}
                      step={selectedAction.required_input === "payment_amount" ? "0.01" : undefined}
                      value={inputValue}
                      onChange={(e) => setInputValue(e.target.value)}
                      placeholder={getInputPlaceholder()}
                      className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg text-sm"
                      autoFocus
                    />
                  )}
                </div>
              )}

              <button
                onClick={handleExecuteAction}
                disabled={
                  actionInProgress ||
                  (!!selectedAction.required_input && !inputValue)
                }
                className="w-full bg-lsc-rose hover:bg-lsc-rose/90 disabled:bg-earth-400 text-white py-2 px-4 rounded-lg font-medium transition-colors"
              >
                {actionInProgress ? "Processing..." : `Confirm ${selectedAction.label}`}
              </button>
            </div>
          )}
        </div>
      </div>
    </ModalBackdrop>
  )
}

function humanizeKey(key: string): string {
  return key
    .replace(/_/g, " ")
    .split(" ")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ")
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "—"
  if (typeof value === "boolean") return value ? "Yes" : "No"
  if (typeof value === "number") {
    if (Number.isInteger(value)) return value.toString()
    return value.toFixed(2)
  }
  if (value instanceof Date) return value.toLocaleDateString()
  return String(value)
}