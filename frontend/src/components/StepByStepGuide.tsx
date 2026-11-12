/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * StepByStepGuide Component
 * Displays numbered sequential steps with visual progress indicators
 * Designed for neurodivergent accessibility with clear visual hierarchy and progressive disclosure
 */

import React, { useState } from 'react'
import { Check, ExternalLink } from 'lucide-react'
import { clsx } from '../utils/helpers'
import { t } from '@/i18n'

export interface Step {
  id: string
  actionTitle: string // Verb-first action (e.g., "Open Google Search")
  instruction: string // Detailed instruction text
  expectedResult: string // Expected outcome after completing step
  actionUrl?: string // Optional URL to external resource
  actionLabel?: string // Label for the action button
}

interface StepByStepGuideProps {
  steps: Step[]
  currentStep?: number // Currently active step (0-indexed)
  onStepChange?: (stepIndex: number) => void
  markedComplete?: string[] // Array of completed step IDs
  onMarkComplete?: (stepId: string) => void
  hideCompletion?: boolean
}

function StepItem({
  step,
  stepNumber,
  isActive,
  isCompleted,
  isLast,
  onMarkComplete,
  onActivate,
}: {
  step: Step
  stepNumber: number
  isActive: boolean
  isCompleted: boolean
  isLast: boolean
  onMarkComplete: (stepId: string) => void
  onActivate: () => void
}): React.ReactElement {
  return (
    <div className="flex gap-4 pb-4">
      {/* Connector line and step number container */}
      <div className="flex flex-col items-center gap-2 flex-shrink-0">
        {/* Step number circle */}
        <button
          onClick={onActivate}
          className={clsx(
            'w-12 h-12 min-w-[48px] rounded-full flex items-center justify-center font-bold text-base motion-safe:transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-lsc-rose',
            isCompleted
              ? 'bg-status-success-500 text-white shadow-md'
              : isActive
                ? 'bg-lsc-rose text-white shadow-lg scale-110'
                : 'bg-lsc-cream dark:bg-lsc-brown border-2 border-lsc-border dark:border-lsc-brown text-lsc-dark dark:text-lsc-cream hover:bg-lsc-rose/10'
          )}
          aria-label={`Step ${stepNumber}: ${step.actionTitle}`}
          aria-pressed={isActive}
          title={isCompleted ? 'Step completed' : isActive ? 'Current step' : 'Click to focus step'}
        >
          {isCompleted ? (
            <Check className="w-6 h-6" aria-hidden="true" />
          ) : (
            <span>{stepNumber}</span>
          )}
        </button>

        {/* Vertical connector line (hidden on last step) */}
        {!isLast && (
          <div
            className={clsx(
              'w-1 flex-grow min-h-12 motion-safe:transition-colors',
              isCompleted || isActive ? 'bg-lsc-rose' : 'bg-lsc-border dark:bg-lsc-brown/50'
            )}
            aria-hidden="true"
          />
        )}
      </div>

      {/* Step content */}
      <div className="flex-1 pt-2 pb-4">
        {/* Action title - verb-first */}
        <h3 className="font-serif text-base font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
          {step.actionTitle}
        </h3>

        {/* Instruction text */}
        <p className="text-sm text-lsc-dark/75 dark:text-lsc-cream/80 mb-3 leading-relaxed">
          {step.instruction}
        </p>

        {/* Action button and external link */}
        <div className="flex flex-wrap gap-2 mb-3">
          {step.actionUrl && (
            <a
              href={step.actionUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white text-sm font-medium rounded-xl motion-safe:transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-lsc-rose"
              aria-label={`${step.actionLabel || 'Open link'} (opens in new tab)`}
            >
              {step.actionLabel || 'Open'}
              <ExternalLink className="w-4 h-4" aria-hidden="true" />
            </a>
          )}

          {/* Mark complete button */}
          {!isCompleted && (
            <button
              onClick={() => onMarkComplete(step.id)}
              className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-cream dark:bg-lsc-brown hover:bg-lsc-border dark:hover:bg-lsc-brown/80 text-lsc-dark dark:text-lsc-cream text-sm font-medium border-2 border-lsc-border dark:border-lsc-brown rounded-xl motion-safe:transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-lsc-rose"
              aria-label={`Mark step ${stepNumber} as complete`}
            >
              Mark Done
              <Check className="w-4 h-4" aria-hidden="true" />
            </button>
          )}
        </div>

        {/* Expected result section */}
        <div className="p-3 bg-lsc-cream dark:bg-lsc-brown/30 rounded-lg border border-lsc-border dark:border-lsc-brown/50">
          <p className="text-xs font-semibold text-lsc-dark dark:text-lsc-cream/90 mb-1 uppercase tracking-wide">
            Expected Result
          </p>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/75">
            {step.expectedResult}
          </p>
        </div>
      </div>
    </div>
  )
}

export function StepByStepGuide({
  steps,
  currentStep = 0,
  onStepChange,
  markedComplete = [],
  onMarkComplete,
  hideCompletion,
}: StepByStepGuideProps): React.ReactElement {
  const [localCurrentStep, setLocalCurrentStep] = useState(currentStep)
  const [localMarkedComplete, setLocalMarkedComplete] = useState<string[]>(markedComplete)

  const handleStepChange = (stepIndex: number) => {
    setLocalCurrentStep(stepIndex)
    onStepChange?.(stepIndex)
  }

  const handleMarkComplete = (stepId: string) => {
    if (!localMarkedComplete.includes(stepId)) {
      setLocalMarkedComplete([...localMarkedComplete, stepId])
      onMarkComplete?.(stepId)
    }
  }

  const completionPercentage = Math.round(
    (localMarkedComplete.length / steps.length) * 100
  )

  return (
    <section
      className="w-full"
      aria-label={t('aria.stepByStepGuide.stepbystepGuide')}
      role="region"
    >
      {/* Progress indicator */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
            Progress
          </h2>
          <span className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70">
            {localMarkedComplete.length} of {steps.length} complete
          </span>
        </div>
        {/* Progress bar */}
        <div className="w-full h-2 bg-lsc-cream dark:bg-lsc-brown rounded-full overflow-hidden border border-lsc-border dark:border-lsc-brown">
          <div
            className="h-full bg-lsc-rose motion-safe:transition-all duration-300 ease-out"
            style={{ width: `${completionPercentage}%` }}
            role="progressbar"
            aria-valuenow={completionPercentage}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label={`Guide progress: ${completionPercentage}% complete`}
          />
        </div>
      </div>

      {/* Steps list with semantic markup */}
      <ol
        className="space-y-2"
        role="list"
        aria-label={`${steps.length} steps in this guide`}
      >
        {steps.map((step, index) => (
          <li key={step.id} role="listitem">
            <StepItem
              step={step}
              stepNumber={index + 1}
              isActive={localCurrentStep === index}
              isCompleted={localMarkedComplete.includes(step.id)}
              isLast={index === steps.length - 1}
              onMarkComplete={handleMarkComplete}
              onActivate={() => handleStepChange(index)}
            />
          </li>
        ))}
      </ol>

      {/* Completion message */}
      {!hideCompletion && localMarkedComplete.length === steps.length && steps.length > 0 && (
        <div className="mt-6 p-4 bg-status-success-50 dark:bg-status-success-900/20 border-2 border-status-success-300 dark:border-status-success-700 rounded-lg">
          <p className="flex items-center gap-2 text-sm font-semibold text-status-success-700 dark:text-status-success-400">
            <Check className="w-5 h-5" aria-hidden="true" />
            All steps completed! Great job!
          </p>
        </div>
      )}
    </section>
  )
}

export default StepByStepGuide
