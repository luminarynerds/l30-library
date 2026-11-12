/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from "react"
import { CheckCircle2, SkipForward, Loader2, RotateCcw, Circle } from "lucide-react"
import toast from "react-hot-toast"
import { useAuth } from "../../../../contexts/AuthContext"
import { fetchApi } from "../../../../api/fetchApi"

interface OnboardingStatusDetail {
  patron_id: number
  status: "not_started" | "in_progress" | "completed" | "skipped"
  current_step: number
  total_steps: number
  steps: Record<string, boolean>
  skipped: boolean
  completed_at: string | null
  started_at: string | null
}

interface PatronOnboardingStatusProps {
  patronId: number
  onboardingCompletedAt?: string | null
  onboardingSkipped?: boolean
  onReset?: () => void
}

const STEP_LABELS: Record<string, string> = {
  welcome: "Welcome",
  preferences: "Preferences",
  branch: "Home Branch",
  tour: "Tour",
  complete: "Complete",
}

export function PatronOnboardingStatus({
  patronId,
  onboardingCompletedAt,
  onboardingSkipped,
  onReset,
}: PatronOnboardingStatusProps) {
  const { token } = useAuth()
  const [detail, setDetail] = useState<OnboardingStatusDetail | null>(null)
  const [isLoadingDetail, setIsLoadingDetail] = useState(false)
  const [isResetting, setIsResetting] = useState(false)
  const [showConfirmReset, setShowConfirmReset] = useState(false)
  const [localCompleted, setLocalCompleted] = useState(onboardingCompletedAt)
  const [localSkipped, setLocalSkipped] = useState(onboardingSkipped)

  const completedAt = localCompleted
  const skipped = localSkipped

  const loadDetail = async () => {
    if (!token) return
    setIsLoadingDetail(true)
    try {
      const data = await fetchApi(`/staff/patrons/${patronId}/onboarding-status`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      setDetail(data)
    } catch {
      toast.error("Failed to load onboarding details")
    } finally {
      setIsLoadingDetail(false)
    }
  }

  const handleReset = async () => {
    if (!token) return
    setIsResetting(true)
    try {
      await fetchApi(`/staff/patrons/${patronId}/onboarding/reset`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
      })
      toast.success("Onboarding reset successfully")
      setLocalCompleted(null)
      setLocalSkipped(false)
      setDetail(null)
      setShowConfirmReset(false)
      onReset?.()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to reset onboarding")
    } finally {
      setIsResetting(false)
    }
  }

  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleDateString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
      })
    } catch {
      return dateStr
    }
  }

  // Status indicator
  let statusIcon: React.ReactNode
  let statusText: string
  let statusColor: string

  if (completedAt && !skipped) {
    statusIcon = <CheckCircle2 className="w-4 h-4 text-status-success-600" />
    statusText = `Completed ${formatDate(completedAt)}`
    statusColor = "text-status-success-700 dark:text-status-success-400"
  } else if (skipped) {
    statusIcon = <SkipForward className="w-4 h-4 text-status-warning-500" />
    statusText = "Skipped"
    statusColor = "text-status-warning-800 dark:text-status-warning-400"
  } else {
    statusIcon = <Circle className="w-4 h-4 text-status-info-500" />
    statusText = "Not Started"
    statusColor = "text-status-info-600 dark:text-status-info-400"
  }

  return (
    <div className="bg-lsc-cream dark:bg-lsc-brown/50 rounded-xl p-6">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
          Onboarding
        </h3>
        <div className="flex items-center gap-2">
          {!detail && (
            <button
              onClick={loadDetail}
              disabled={isLoadingDetail}
              className="text-sm text-lsc-rose hover:text-lsc-rose/80 font-medium"
            >
              {isLoadingDetail ? (
                <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
              ) : (
                "Details"
              )}
            </button>
          )}
          {(completedAt || skipped) && !showConfirmReset && (
            <button
              onClick={() => setShowConfirmReset(true)}
              className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-lsc-dark/60 dark:text-lsc-cream/50 hover:text-lsc-rose border border-lsc-dark/10 dark:border-lsc-cream/10 rounded-lg hover:border-lsc-rose/30 transition-colors"
            >
              <RotateCcw className="w-3 h-3" />
              Reset
            </button>
          )}
        </div>
      </div>

      {/* Status line */}
      <div className={`flex items-center gap-2 text-sm ${statusColor}`}>
        {statusIcon}
        <span className="font-medium">{statusText}</span>
      </div>

      {/* Confirm reset */}
      {showConfirmReset && (
        <div className="mt-3 p-3 bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800/30 rounded-lg">
          <p className="text-sm text-status-warning-800 dark:text-status-warning-200 mb-2">
            Reset onboarding? The patron will see the setup wizard on next login.
          </p>
          <div className="flex gap-2">
            <button
              onClick={handleReset}
              disabled={isResetting}
              className="px-3 py-1.5 text-xs font-medium text-white bg-status-warning-600 rounded-lg hover:bg-status-warning-700 disabled:opacity-50"
            >
              {isResetting ? (
                <Loader2 className="w-3 h-3 inline motion-safe:animate-spin mr-1" />
              ) : null}
              Confirm Reset
            </button>
            <button
              onClick={() => setShowConfirmReset(false)}
              className="px-3 py-1.5 text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/60 hover:bg-lsc-dark/5 rounded-lg"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Step details (loaded on demand) */}
      {detail && (
        <div className="mt-3 space-y-2">
          {detail.status !== "not_started" && Object.keys(detail.steps).length > 0 && (
            <div className="grid grid-cols-5 gap-1">
              {Object.entries(detail.steps).map(([step, completed]) => (
                <div
                  key={step}
                  className={`text-center p-2 rounded-lg ${
                    completed
                      ? "bg-status-success-100 dark:bg-status-success-900/30"
                      : "bg-lsc-white/50 dark:bg-earth-800/50"
                  }`}
                >
                  <div className="mb-1">
                    {completed ? (
                      <CheckCircle2 className="w-3.5 h-3.5 text-status-success-600 mx-auto" />
                    ) : (
                      <Circle className="w-3.5 h-3.5 text-lsc-dark/30 dark:text-lsc-cream/30 mx-auto" />
                    )}
                  </div>
                  <div className="text-[10px] text-lsc-dark/70 dark:text-lsc-cream/50 leading-tight">
                    {STEP_LABELS[step] || step}
                  </div>
                </div>
              ))}
            </div>
          )}
          {detail.started_at && (
            <p className="text-xs text-lsc-dark/50 dark:text-lsc-cream/40">
              Started {formatDate(detail.started_at)}
            </p>
          )}
        </div>
      )}
    </div>
  )
}
