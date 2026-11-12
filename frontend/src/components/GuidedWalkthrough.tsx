/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useTranslation } from "@/i18n"
import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ChevronLeft, ChevronRight, HelpCircle, Phone, AlertCircle, CheckCircle, Printer } from 'lucide-react'
import EscalationModal from './EscalationModal'
import RelatedGuides from './RelatedGuides'
import GuideFeedback from './GuideFeedback'
import parseGuideContent from "@/utils/parseGuideContent"
import { useSchemaOrg } from './linked-data/SchemaOrgHead'
import { findGuide } from '@/pages/guides/_data'

export interface WalkthroughStep {
  id: string
  title: string
  content: string | React.ReactNode
  tips?: string[]
  troubleshooting?: string
  hasCheckpoint?: boolean
}

interface GuidedWalkthroughProps {
  guideId: string
  title: string
  description: string
  steps: WalkthroughStep[]
  onComplete?: () => void
}

export default function GuidedWalkthrough({
  guideId,
  title,
  description,
  steps,
  onComplete,
}: GuidedWalkthroughProps): React.ReactElement {
  const [currentStepIndex, setCurrentStepIndex] = useState(0)
  const [completedSteps, setCompletedSteps] = useState<Set<string>>(new Set())
  const [_showEscalation, _setShowEscalation] = useState(false)
  const [needsHelp, setNeedsHelp] = useState(false)
  const [isComplete, setIsComplete] = useState(false)

  const navigate = useNavigate()
  const { language } = useTranslation()

  const currentStep = steps[currentStepIndex]!
  const progress = ((currentStepIndex + 1) / steps.length) * 100
  const isLastStep = currentStepIndex === steps.length - 1

  // Schema.org HowTo JSON-LD — exposes each guide as structured data so search
  // engines can surface step-by-step rich results. Only string-content steps
  // become HowToStep nodes (React-node FAQ steps are skipped intentionally).
  const guideMeta = findGuide(guideId)
  const howToSchema = useMemo(() => {
    const stepNodes = steps
      .filter((step) => typeof step.content === 'string')
      .map((step, index) => ({
        '@type': 'HowToStep',
        position: index + 1,
        name: step.title,
        text: step.content as string,
        url: `https://l30.org/guides/${guideId}#${step.id}`,
      }))
    return {
      '@context': 'https://schema.org',
      '@type': 'HowTo',
      '@id': `https://l30.org/guides/${guideId}`,
      name: title,
      description,
      ...(guideMeta?.estimatedMinutes
        ? { totalTime: `PT${guideMeta.estimatedMinutes}M` }
        : {}),
      step: stepNodes,
    }
  }, [guideId, title, description, steps, guideMeta])
  useSchemaOrg(howToSchema, `guide-${guideId}`)

  const handleMarkComplete = () => {
    const newCompleted = new Set(completedSteps)
    newCompleted.add(currentStep.id)
    setCompletedSteps(newCompleted)

    if (isLastStep) {
      setIsComplete(true)
      onComplete?.()
    } else {
      setCurrentStepIndex(currentStepIndex + 1)
    }
  }

  const handleNext = () => {
    if (currentStepIndex < steps.length - 1) {
      setCurrentStepIndex(currentStepIndex + 1)
    }
  }

  const handlePrevious = () => {
    if (currentStepIndex > 0) {
      setCurrentStepIndex(currentStepIndex - 1)
    }
  }

  const handleRestart = () => {
    setCurrentStepIndex(0)
    setCompletedSteps(new Set())
    setNeedsHelp(false)
    setIsComplete(false)
  }

  if (isComplete) {
    return (
      <div className="min-h-screen bg-lsc-cream dark:bg-lsc-dark">
        <div className="max-w-3xl mx-auto px-4 py-12">
          <div className="bg-status-success-50 dark:bg-status-success-900/20 border border-status-success-200 dark:border-status-success-700 rounded-xl p-8 text-center">
            <h2 className="font-serif text-lg font-semibold text-status-success-800 dark:text-status-success-200 mb-2">Guide Complete</h2>
            <p className="text-sm text-status-success-700 dark:text-status-success-300 mb-6">You've finished all the steps.</p>
            <div className="flex flex-wrap justify-center gap-3">
              <button onClick={() => { setIsComplete(false); setCurrentStepIndex(0); setCompletedSteps(new Set()) }} className="px-4 py-2 text-sm font-medium rounded-lg border border-status-success-300 dark:border-status-success-600 text-status-success-700 dark:text-status-success-300 hover:bg-status-success-100 dark:hover:bg-status-success-800/30 motion-safe:transition-colors">
                Start Over
              </button>
              <a href="/help" className="px-4 py-2 text-sm font-medium rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 motion-safe:transition-colors">
                Back to Help Center
              </a>
            </div>
          </div>

          <div className="mt-8">
            <GuideFeedback
              guideId={guideId}
              guideTitle={title}
              onSubmitFeedback={() => {}}
            />
            <RelatedGuides currentGuideId={guideId} />
          </div>
        </div>
      </div>
    )
  }

  if (needsHelp) {
    return (
      <div className="min-h-screen bg-lsc-cream dark:bg-lsc-dark">
        <div className="max-w-3xl mx-auto px-4 py-12">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-8 border border-lsc-border dark:border-earth-700">
            <div className="text-center">
              <Phone className="w-16 h-16 mx-auto text-lsc-rose mb-4" />
              <h2 className="font-serif text-2xl font-semibold text-lsc-dark dark:text-earth-50 mb-3">
                Need Extra Help?
              </h2>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-6">
                Our tech support team is here to help you through this process.
              </p>

              <EscalationModal
                guideTitle={title}
                stepNumber={currentStepIndex + 1}
                totalSteps={steps.length}
              />

              <button
                onClick={handleRestart}
                className="mt-6 text-lsc-rose dark:text-lsc-rose-light hover:underline"
              >
                Back to Guide
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-lsc-cream dark:bg-lsc-dark">
      <div className="max-w-3xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <button
              onClick={() => navigate(-1)}
              className="flex items-center gap-2 text-lsc-rose dark:text-lsc-rose-light hover:underline"
            >
              <ChevronLeft className="w-4 h-4" />
              Back
            </button>
            <button
              onClick={() => window.print()}
              className="flex items-center gap-2 px-3 py-2 text-sm rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 motion-safe:transition-colors print:hidden"
            >
              <Printer aria-hidden="true" className="w-4 h-4" />
              Print Guide
            </button>
          </div>
          <h1 className="text-3xl font-serif font-bold text-lsc-dark dark:text-earth-50 mb-2">{title}</h1>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{description}</p>
          {language !== "en" && (
            <div className="mt-3 px-3 py-2 rounded-lg bg-earth-50 dark:bg-earth-800 border border-lsc-border dark:border-earth-700 text-sm text-earth-600 dark:text-earth-400">
              This guide is currently available in English only.
            </div>
          )}
        </div>

        {/* Progress Bar */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
              Step {currentStepIndex + 1} of {steps.length}
            </span>
            <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              {Math.round(progress)}%
            </span>
          </div>
          <div className="w-full bg-lsc-border dark:bg-earth-700 rounded-full h-2"
              role="progressbar"
              aria-valuenow={Math.round(progress)}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label="Guide progress"
            >
            <div
              className="bg-lsc-rose h-2 rounded-full motion-safe:transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        {/* Step Indicators */}
        <div className="relative">
        <div className="mb-8 flex gap-2 overflow-x-auto pb-2">
          {steps.map((step, index) => (
            <button
              key={step.id}
              onClick={() => setCurrentStepIndex(index)}
              aria-label={`Step ${index + 1}: ${step.title}`}
              aria-current={index === currentStepIndex ? "step" : undefined}
              className={`flex items-center gap-2 px-3 py-2 rounded-full whitespace-nowrap motion-safe:transition-colors flex-shrink-0 ${
                index === currentStepIndex
                  ? 'bg-lsc-rose text-white'
                  : completedSteps.has(step.id)
                    ? 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-400'
                    : 'bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream border border-lsc-border dark:border-earth-700'
              }`}
            >
              {completedSteps.has(step.id) && <CheckCircle className="w-4 h-4" />}
              <span className="text-sm font-medium">Step {index + 1}</span>
            </button>
          ))}
        </div>
          <div className="absolute right-0 top-0 bottom-2 w-8 bg-gradient-to-l from-lsc-cream dark:from-lsc-dark to-transparent pointer-events-none sm:hidden" aria-hidden="true" />
        </div>

        {/* Main Content */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-8 border border-lsc-border dark:border-earth-700 mb-8">
          <h2 className="font-serif text-2xl font-semibold text-lsc-dark dark:text-earth-50 mb-4">
            {currentStep.title}
          </h2>

          <div className="prose dark:prose-invert max-w-prose mb-6">
            {typeof currentStep.content === 'string' ? (
              <div className="text-lsc-dark dark:text-lsc-cream space-y-3">
                {parseGuideContent(currentStep.content)}
              </div>
            ) : (
              currentStep.content
            )}
          </div>

          {/* Tips */}
          {currentStep.tips && currentStep.tips.length > 0 && (
            <div className="bg-lsc-cream dark:bg-lsc-brown/20 rounded-xl p-4 mb-6">
              <h3 className="font-serif font-semibold text-lsc-dark dark:text-earth-50 mb-3 flex items-center gap-2">
                <HelpCircle className="w-4 h-4 text-lsc-rose" />
                Helpful Tips
              </h3>
              <ul className="space-y-2">
                {currentStep.tips.map((tip, index) => (
                  <li key={index} className="text-sm text-lsc-dark dark:text-lsc-cream flex gap-2">
                    <span className="text-lsc-rose">&bull;</span>
                    <span>{tip}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Troubleshooting */}
          {currentStep.troubleshooting && (
            <div className="bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-900/50 rounded-xl p-4 mb-6">
              <h3 className="font-serif font-semibold text-status-warning-900 dark:text-status-warning-100 mb-2 flex items-center gap-2">
                <AlertCircle className="w-4 h-4" />
                Troubleshooting
              </h3>
              <div className="text-sm text-status-warning-800 dark:text-status-warning-200 space-y-2">
                {parseGuideContent(currentStep.troubleshooting)}
              </div>
            </div>
          )}

          {/* Checkpoint Message */}
          {currentStep.hasCheckpoint && (
            <div className="bg-status-success-50 dark:bg-status-success-900/20 border border-status-success-200 dark:border-status-success-900/50 rounded-xl p-4 mb-6">
              <p className="text-sm text-status-success-800 dark:text-status-success-200">
                When you finish this step, click Next Step to continue.
              </p>
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row gap-4 justify-between">
          <div className="flex gap-3">
            <button
              onClick={handlePrevious}
              disabled={currentStepIndex === 0}
              className="flex items-center gap-2 px-6 py-3 rounded-xl border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 disabled:opacity-50 disabled:cursor-not-allowed motion-safe:transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
              Previous
            </button>
            <button
              onClick={handleNext}
              disabled={isLastStep}
              className="flex items-center gap-2 px-6 py-3 rounded-xl border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 disabled:opacity-50 disabled:cursor-not-allowed motion-safe:transition-colors"
            >
              Skip
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>

          <div className="flex gap-3">
            <button
              onClick={() => setNeedsHelp(true)}
              className="px-6 py-3 rounded-xl border border-lsc-rose dark:border-lsc-rose-light text-lsc-rose dark:text-lsc-rose-light hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 motion-safe:transition-colors font-medium"
            >
              Need Help?
            </button>
            <button
              onClick={handleMarkComplete}
              className="px-6 py-3 rounded-xl bg-lsc-rose hover:bg-lsc-rose/90 text-white font-medium motion-safe:transition-colors"
            >
              {isLastStep ? 'Complete' : 'Next Step'}
            </button>
          </div>
        </div>

        {/* Restart Button */}
        <div className="mt-6 text-center print:hidden">
          <button
            onClick={handleRestart}
            className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream motion-safe:transition-colors"
          >
            Start Over
          </button>
        </div>

        {/* Feedback & Related Guides - Only show on last step */}
        {currentStepIndex === steps.length - 1 && (
          <div className="print:hidden">
            <GuideFeedback
              guideId={guideId}
              guideTitle={title}
              onSubmitFeedback={() => {
                // Feedback submitted
              }}
            />

            <RelatedGuides currentGuideId={guideId} />
          </div>
        )}
      </div>

      {/* Print Styles */}
      <style>{`
        @media print {
          body {
            background: white;
            color: black;
          }
          h1, h2, h3 {
            break-after: avoid;
            page-break-after: avoid;
          }
          .bg-lsc-cream,
          .bg-lsc-white,
          .bg-earth-800,
          .border {
            break-inside: avoid;
            page-break-inside: avoid;
          }
        }
      `}</style>
    </div>
  )
}
