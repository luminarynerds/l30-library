/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * ExitStrategySection Component
 *
 * A neurodivergent-accessible component for displaying cancellation/unsubscribe
 * information in a neutral, non-anxiety-inducing way. Reduces cognitive load by
 * providing clear steps and timeline information in a collapsible format.
 *
 * Neurodivergent-accessible features:
 * - Neutral language ("Stop using" not "Cancel subscription")
 * - Clear, step-by-step process to reduce overwhelm
 * - Optional promo for alternatives to ease decision-making
 * - Collapsible for progressive disclosure
 * - Visual hierarchy with proper spacing
 * - Screen reader support with semantic HTML
 *
 * @example
 * <ExitStrategySection
 *   service="Grammarly Free Trial"
 *   cancelSteps={[
 *     "Log into your account",
 *     "Click Account Settings",
 *     "Select Subscription > Cancel"
 *   ]}
 *   timeline="Access continues until end of billing period"
 *   alternativePromo={{
 *     title: "Build Your Own Writing Tool",
 *     description: "Learn to create custom ChatGPT assistants",
 *     link: "/events/ai-tools-class"
 *   }}
 * />
 */

import React, { useState } from 'react'
import { ChevronDown, Rocket, ArrowRight, ShieldCheck } from 'lucide-react'


interface AlternativePromo {
  /** Title of the alternative service/class */
  title: string

  /** Brief description of the alternative */
  description: string

  /** Link to the alternative (internal or external) */
  link: string

  /** Optional icon color class */
  colorClass?: string
}

interface ExitStrategySectionProps {
  /** Name of the service or trial */
  service: string

  /** Array of steps to cancel/stop using the service */
  cancelSteps: string[]

  /** Information about what happens and when (e.g., "Access continues until end of billing period") */
  timeline: string

  /** Optional alternative service or class to promote */
  alternativePromo?: AlternativePromo

  /** Whether the section starts expanded (default: false) */
  defaultExpanded?: boolean

  /** Custom CSS classes */
  className?: string

}

/**
 * ExitStrategySection Component
 *
 * Displays cancellation/exit information in a reassuring, accessible manner.
 * Ideal for embedding in resource cards or as a standalone section.
 */
const ExitStrategySection = React.forwardRef<
  HTMLDivElement,
  ExitStrategySectionProps
>(
  (
    {
      service,
      cancelSteps,
      timeline,
      alternativePromo,
      defaultExpanded = false,
      className = '',

    },
    ref
  ) => {
    const [isExpanded, setIsExpanded] = useState(defaultExpanded)
    const sanitizedServiceId = service.replace(/\s+/g, '-').toLowerCase()

    return (
      <div
        ref={ref}
        className={`
          border-2 border-lsc-border dark:border-earth-700
          rounded-xl overflow-hidden
          bg-lsc-cream/50 dark:bg-lsc-brown/20
          transition-all duration-200
          ${className}
        `}
      >
        {/* Toggle Header */}
        <button
          type="button"
          onClick={() => setIsExpanded(!isExpanded)}
          aria-expanded={isExpanded}
          aria-controls={`exit-strategy-content-${sanitizedServiceId}`}
          className={`
            w-full px-5 sm:px-6 py-4 sm:py-5
            flex items-center gap-3 justify-between
            text-left font-semibold
            text-lsc-dark dark:text-lsc-cream
            hover:bg-lsc-cream dark:hover:bg-lsc-brown/40
            active:bg-lsc-cream/70 dark:active:bg-lsc-brown/60
            transition-colors duration-150
            focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-inset
          `}
        >
          <div className="flex items-center gap-3 flex-1 min-w-0">
            <Rocket className="w-5 h-5 flex-shrink-0 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
            <span className="truncate" title={`How to get started with ${service}`}>
              How to get started with{' '}
              <span className="font-bold">{service}</span>
            </span>
          </div>

          <ChevronDown
            className={`
              w-5 h-5 flex-shrink-0
              text-lsc-rose dark:text-lsc-rose-light
              transition-transform duration-300
              ${isExpanded ? 'rotate-180' : ''}
            `}
            aria-hidden="true"
          />
        </button>

        {/* Expanded Content */}
        {isExpanded && (
          <div
            id={`exit-strategy-content-${sanitizedServiceId}`}
            className="border-t-2 border-lsc-border dark:border-earth-700 px-5 sm:px-6 py-4 sm:py-5 space-y-5"
          >
            {/* Steps Section */}
            <div>
              <h4 className="text-sm font-bold uppercase tracking-wider text-lsc-dark dark:text-lsc-cream mb-3">
                Getting Started
              </h4>
              <ol className="space-y-2">
                {cancelSteps.map((step, index) => (
                  <li
                    key={index}
                    className="flex gap-3 text-sm sm:text-base text-lsc-dark dark:text-lsc-cream/90"
                  >
                    <span
                      className={`
                        inline-flex items-center justify-center
                        w-6 h-6 flex-shrink-0
                        rounded-full
                        bg-lsc-rose text-white
                        font-bold text-xs
                      `}
                      aria-label={`Step ${index + 1}`}
                    >
                      {index + 1}
                    </span>
                    <span className="pt-0.5">{step}</span>
                  </li>
                ))}
              </ol>
            </div>

            {/* Timeline Section */}
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
              <h4 className="text-xs font-bold uppercase tracking-wider text-lsc-dark dark:text-lsc-cream mb-2 flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5" aria-hidden="true" />
                Data & Privacy
              </h4>
              <p className="text-sm sm:text-base text-lsc-dark/80 dark:text-lsc-cream/80 leading-relaxed">
                {timeline}
              </p>
            </div>

            {/* Alternative Promo Section (Optional) */}
            {alternativePromo && (
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border-2 border-lsc-rose/30 dark:border-lsc-rose-light/30">
                <h4 className="text-xs font-bold uppercase tracking-wider text-lsc-rose dark:text-lsc-rose-light mb-2">
                  Interested in Alternatives?
                </h4>
                <p className="text-sm text-lsc-dark dark:text-lsc-cream mb-3">
                  {alternativePromo.description}
                </p>
                <a
                  href={alternativePromo.link}
                  className={`
                    inline-flex items-center gap-2
                    text-sm font-bold
                    text-lsc-rose dark:text-lsc-rose-light
                    hover:gap-3 transition-all duration-200
                    focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2 dark:focus-visible:ring-offset-earth-800
                    rounded px-2 py-1
                  `}
                >
                  {alternativePromo.title}
                  <ArrowRight className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
                </a>
              </div>
            )}

            {/* Legal/Informational note */}
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 border-t border-lsc-border dark:border-earth-700 pt-3">
              Need help? Contact the library or visit the service's help center for additional support.
            </p>
          </div>
        )}
      </div>
    )
  }
)

ExitStrategySection.displayName = 'ExitStrategySection'

export default ExitStrategySection
