/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { PersonStanding, Eye, Ear, Hand, Monitor, MessageCircle, Phone, Mail, Settings } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useTranslation } from '@/i18n'
import { useBranding } from '@/contexts/BrandingContext'

export default function AccessibilityPage(): JSX.Element {
  const branding = useBranding()
  const { t } = useTranslation()
  return (
    <div className="space-y-8 max-w-6xl mx-auto">
      {/* CTA to accessibility settings */}
      <div className="bg-lsc-cream dark:bg-earth-800 rounded-xl p-4 flex items-center justify-between gap-4 border border-lsc-border dark:border-earth-700">
        <p className="text-lsc-dark dark:text-lsc-cream text-sm">
          {t('accessibilityPage.changeSiteLooksPrompt', 'Looking to change how this site looks and feels?')}
        </p>
        <Link
          to="/accessibility/settings"
          className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors text-sm font-medium whitespace-nowrap focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2"
        >
          <Settings className="w-4 h-4" aria-hidden="true" />
          {t('accessibilityPage.adjustAccessibilitySettingsLink', 'Adjust your accessibility settings')}
        </Link>
      </div>

      {/* Software Accessibility Conformance — for procurement, school IT, and a11y reviewers */}
      <section
        id="software-conformance"
        className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm border border-lsc-cream dark:border-lsc-brown"
        aria-labelledby="software-conformance-heading"
      >
        <h2 id="software-conformance-heading" className="font-serif text-xl font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
          {t('accessibilityPage.conformanceStatementHeading', 'Software Accessibility Conformance Statement')}
        </h2>

        <dl className="space-y-3 text-lsc-dark/80 dark:text-lsc-cream/80">
          <div>
            <dt className="font-semibold inline">{t('accessibilityPage.targetStandardLabel', 'Target standard: ')}</dt>
            <dd className="inline">{t('accessibilityPage.targetStandardValue', 'Web Content Accessibility Guidelines (WCAG) 2.1, Level AA')}</dd>
          </div>
          <div>
            <dt className="font-semibold inline">{t('accessibilityPage.conformanceStatusLabel', 'Conformance status: ')}</dt>
            <dd className="inline">
              {t(
                'accessibilityPage.conformanceStatusValue',
                'Partially conformant — the L30 platform substantially meets WCAG 2.1 AA. Known gaps are documented below and tracked in our public issue queue.',
              )}
            </dd>
          </div>
          <div>
            <dt className="font-semibold inline">{t('accessibilityPage.selfEvalDateLabel', 'Self-evaluation date: ')}</dt>
            <dd className="inline"><time dateTime="2026-05-26">{t('accessibilityPage.selfEvalDateValue', 'May 26, 2026')}</time></dd>
          </div>
          <div>
            <dt className="font-semibold inline">{t('accessibilityPage.evaluationMethodLabel', 'Evaluation method: ')}</dt>
            <dd className="inline">
              {t(
                'accessibilityPage.evaluationMethodValue',
                'Automated axe-core scans on every public page in our test suite, plus manual keyboard, screen-reader (NVDA, VoiceOver), and color-contrast review. Third-party audit not yet commissioned; available on request.',
              )}
            </dd>
          </div>
          <div>
            <dt className="font-semibold inline">{t('accessibilityPage.vpatAcrLabel', 'VPAT / ACR: ')}</dt>
            <dd className="inline">
              {t('accessibilityPage.vpatAcrPrefix', 'Available on request — email ')}
              <a href="mailto:accessibility@l30.org" className="underline">accessibility@l30.org</a>.
            </dd>
          </div>
        </dl>

        <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mt-6 mb-2">{t('accessibilityPage.knownGapsHeading', 'Known gaps')}</h3>
        <ul className="list-disc pl-6 space-y-1 text-lsc-dark/80 dark:text-lsc-cream/80 text-sm">
          <li>{t('accessibilityPage.knownGap1', 'Some legacy admin views ship without complete keyboard-only flows — replacements in progress.')}</li>
          <li>{t('accessibilityPage.knownGap2', 'Color contrast in a few branded-theme combinations needs re-checking after recent BrandingContext changes.')}</li>
          <li>{t('accessibilityPage.knownGap3', 'Alt-text coverage on user-uploaded images depends on staff entry; admin tooling for review is being added.')}</li>
        </ul>

        <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mt-6 mb-2">{t('accessibilityPage.howWeWorkHeading', 'How we work on accessibility')}</h3>
        <ul className="list-disc pl-6 space-y-1 text-lsc-dark/80 dark:text-lsc-cream/80 text-sm">
          <li>{t('accessibilityPage.howWeWork1', 'Every public-facing page has an automated accessibility test in our test suite.')}</li>
          <li>{t('accessibilityPage.howWeWork2', 'Calm-mode, focus-mode, high-contrast theme, and customizable text density ship as core features, not add-ons.')}</li>
          <li>{t('accessibilityPage.howWeWork3', 'We treat keyboard navigation as a primary input, not a fallback.')}</li>
          <li>{t('accessibilityPage.howWeWork4', 'Patron-facing accessibility services are listed below; the rest of this page is for end-user accommodations.')}</li>
        </ul>

        <p className="mt-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          {t('accessibilityPage.foundProblemPrefix', 'Found a problem? Email ')}
          <a href="mailto:accessibility@l30.org" className="underline">accessibility@l30.org</a>.
          {' '}
          {t('accessibilityPage.forSecurityIssuesPrefix', 'For security-relevant accessibility issues, please use our ')}
          <a href="/security" className="underline">{t('accessibilityPage.responsibleDisclosureLinkText', 'responsible-disclosure policy')}</a>.
        </p>
      </section>

      {/* Header */}
      <div className="bg-gradient-to-r from-lsc-rose to-lsc-rose dark:from-lsc-brown dark:to-earth-800 rounded-xl p-8 text-white">
        <div className="flex items-center gap-4 mb-4">
          <div className="w-16 h-16 bg-lsc-white rounded-xl flex items-center justify-center">
            <PersonStanding aria-hidden="true" className="w-8 h-8" color="#7C6545" />
          </div>
          <div>
            <h1 className="text-3xl font-serif font-bold">{t('accessibilityPage.pageTitle', 'Accessibility')}</h1>
            <p className="text-white">{t('accessibility.ourCommitmentToInclusiveAccess')}</p>
          </div>
        </div>
        <p className="text-lg text-white dark:text-white/90 max-w-3xl">
          {t('accessibilityPage.committedToEnsuring', { libraryName: branding.library_name })}
        </p>
      </div>

      {/* Statement */}
      <section className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
        <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
          {t('accessibilityPage.accessibilityStatementHeading', 'Accessibility Statement')}
        </h2>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
          {t(
            'accessibilityPage.wcagComplianceIntro',
            'We strive to comply with the Web Content Accessibility Guidelines (WCAG) 2.1 Level AA and applicable accessibility standards. We are continuously working to improve the accessibility of our website and services.',
          )}
        </p>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
          {t('accessibilityPage.equitableGoalText', 'Our goal is to provide an equitable experience for all patrons, regardless of ability.')}
        </p>
      </section>

      {/* Services Grid */}
      <div className="grid md:grid-cols-2 gap-6">
        {/* Visual Accessibility */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-lsc-cream dark:bg-lsc-brown rounded-xl flex items-center justify-center">
              <Eye aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
            </div>
            <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
              {t('accessibilityPage.visualAccessibilityHeading', 'Visual Accessibility')}
            </h3>
          </div>
          <ul className="space-y-2 text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('accessibilityPage.visual1', 'Large print books and materials')}
            </li>
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('accessibilityPage.visual2', 'Screen magnification software on public computers')}
            </li>
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('accessibilityPage.visual3', 'JAWS and NVDA screen readers available')}
            </li>
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('accessibilityPage.visual4', 'High contrast website option')}
            </li>
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t(
                'accessibilityPage.visual5',
                'Braille materials and BARD access (BARD is a free audiobook library from the Library of Congress for people with reading disabilities)',
              )}
            </li>
          </ul>
        </div>

        {/* Hearing Accessibility */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-lsc-cream dark:bg-lsc-brown rounded-xl flex items-center justify-center">
              <Ear aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
            </div>
            <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
              {t('accessibilityPage.hearingAccessibilityHeading', 'Hearing Accessibility')}
            </h3>
          </div>
          <ul className="space-y-2 text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('accessibilityPage.hearing1', 'Hearing loop system at service desks')}
            </li>
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('accessibilityPage.hearing2', 'Video relay service (VRS) available')}
            </li>
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('accessibilityPage.hearing3', 'Captioned videos and programs')}
            </li>
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('accessibilityPage.hearing4', 'ASL interpretation upon request for events')}
            </li>
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('accessibilityPage.hearing5', 'Visual alerts and notifications')}
            </li>
          </ul>
        </div>

        {/* Physical Accessibility */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-lsc-cream dark:bg-lsc-brown rounded-xl flex items-center justify-center">
              <Hand aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
            </div>
            <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
              {t('accessibilityPage.physicalAccessibilityHeading', 'Physical Accessibility')}
            </h3>
          </div>
          <ul className="space-y-2 text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('accessibilityPage.physical1', 'Wheelchair accessible entrance and aisles')}
            </li>
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('accessibilityPage.physical2', 'Accessible parking spaces near entrance')}
            </li>
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('accessibilityPage.physical3', 'Elevator access to all floors')}
            </li>
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('accessibilityPage.physical4', 'Adjustable height computer workstations')}
            </li>
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('accessibilityPage.physical5', 'Home delivery service for patrons who cannot visit')}
            </li>
          </ul>
        </div>

        {/* Digital Accessibility */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-lsc-cream dark:bg-lsc-brown rounded-xl flex items-center justify-center">
              <Monitor aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
            </div>
            <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
              {t('accessibilityPage.digitalAccessibilityHeading', 'Digital Accessibility')}
            </h3>
          </div>
          <ul className="space-y-2 text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('accessibilityPage.digital1', 'WCAG 2.1 Level AA compliant website')}
            </li>
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('accessibilityPage.digital2', 'Keyboard navigation support')}
            </li>
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('accessibilityPage.digital3', 'Screen reader compatible catalog')}
            </li>
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('accessibilityPage.digital4', 'Text resizing without loss of functionality')}
            </li>
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('accessibilityPage.digital5', 'Alternative text for images')}
            </li>
          </ul>
        </div>
      </div>

      {/* Assistive Technology */}
      <section className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
        <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
          {t('accessibilityPage.assistiveTechHeading', 'Assistive Technology Available')}
        </h2>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-lsc-cream dark:bg-lsc-brown/20 rounded-xl p-4 text-center">
            <p className="font-medium text-lsc-dark dark:text-lsc-cream">{t('accessibilityPage.screenReadersLabel', 'Screen Readers')}</p>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">JAWS, NVDA</p>
          </div>
          <div className="bg-lsc-cream dark:bg-lsc-brown/20 rounded-xl p-4 text-center">
            <p className="font-medium text-lsc-dark dark:text-lsc-cream">{t('accessibilityPage.magnificationLabel', 'Magnification')}</p>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">ZoomText, Built-in</p>
          </div>
          <div className="bg-lsc-cream dark:bg-lsc-brown/20 rounded-xl p-4 text-center">
            <p className="font-medium text-lsc-dark dark:text-lsc-cream">{t('accessibilityPage.voiceControlLabel', 'Voice Control')}</p>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Dragon, Voice Access</p>
          </div>
          <div className="bg-lsc-cream dark:bg-lsc-brown/20 rounded-xl p-4 text-center">
            <p className="font-medium text-lsc-dark dark:text-lsc-cream">{t('accessibilityPage.alternativeInputLabel', 'Alternative Input')}</p>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('accessibility.switchAccessEyeTracking')}</p>
          </div>
        </div>
      </section>

      {/* Feedback Section */}
      <section className="bg-lsc-cream dark:bg-lsc-brown/20 rounded-xl p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 bg-lsc-cream dark:bg-earth-800 rounded-xl flex items-center justify-center">
            <MessageCircle aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
          </div>
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
            {t('accessibilityPage.accessibilityFeedbackHeading', 'Accessibility Feedback')}
          </h3>
        </div>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
          {t(
            'accessibilityPage.feedbackIntro',
            'We want to hear from you about accessibility. Please tell us if you encounter barriers such as: website difficult to read, confusing instructions, missing video captions, buttons too small to click, or staff not understanding your accessibility needs. Contact us:',
          )}
        </p>
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex items-center gap-2 text-lsc-dark dark:text-lsc-cream/80">
            <Phone aria-hidden="true" className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light" />
            <span>{branding.phone}</span>
          </div>
          <div className="flex items-center gap-2 text-lsc-dark dark:text-lsc-cream/80">
            <Mail aria-hidden="true" className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light" />
            <span>{branding.contact_email}</span>
          </div>
        </div>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-4">
          {t(
            'accessibilityPage.feedbackResponseTime',
            'We respond to accessibility feedback within 2 business days (Monday through Friday). If we cannot fix the issue immediately, we will explain what we are doing and when you can expect a solution.',
          )}
        </p>
      </section>

      {/* ADA Title II Grievance Procedure */}
      <section
        id="grievance"
        className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm border border-lsc-cream dark:border-lsc-brown"
        aria-labelledby="grievance-heading"
      >
        <h2 id="grievance-heading" className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
          {t('accessibilityPage.grievanceHeading', 'Accessibility Grievance Procedure (ADA Title II)')}
        </h2>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
          {t('accessibilityPage.grievanceIntro', { libraryName: branding.library_name })}
        </p>
        <dl className="space-y-3 text-lsc-dark/80 dark:text-lsc-cream/80 text-sm">
          <div>
            <dt className="font-semibold">{t('accessibilityPage.howToFileLabel', 'How to file')}</dt>
            <dd>
              {t('accessibilityPage.howToFilePrefix', 'Submit your grievance in writing, or in another accessible format on request, to the ADA Coordinator at')}{" "}
              <a href="mailto:accessibility@l30.org" className="underline">accessibility@l30.org</a>
              {t('accessibilityPage.howToFileSuffix', '. Please include your name, how to reach you, a description of what happened, the date it occurred, and the resolution you are seeking.')}
            </dd>
          </div>
          <div>
            <dt className="font-semibold">{t('accessibilityPage.whenToFileLabel', 'When to file')}</dt>
            <dd>{t('accessibilityPage.whenToFileValue', 'As soon as possible, and ideally within 60 calendar days of the alleged barrier or discrimination.')}</dd>
          </div>
          <div>
            <dt className="font-semibold">{t('accessibilityPage.acknowledgmentLabel', 'Acknowledgment')}</dt>
            <dd>{t('accessibilityPage.acknowledgmentValue', 'We will acknowledge your grievance within 2 business days of receiving it.')}</dd>
          </div>
          <div>
            <dt className="font-semibold">{t('accessibilityPage.responseLabel', 'Response')}</dt>
            <dd>{t('accessibilityPage.responseValue', 'The ADA Coordinator will respond in writing within 15 business days, in a format accessible to you, and will work with you to resolve the issue.')}</dd>
          </div>
          <div>
            <dt className="font-semibold">{t('accessibilityPage.appealsLabel', 'Appeals')}</dt>
            <dd>
              {t(
                'accessibilityPage.appealsValue',
                "If the Coordinator's response does not resolve the matter, you may appeal in writing to the Library Director within 15 business days. If the Director's decision still does not resolve it, you may appeal to the Library Board, which meets the third Tuesday of each month at 6:30 p.m.",
              )}
            </dd>
          </div>
          <div>
            <dt className="font-semibold">{t('accessibilityPage.recordRetentionLabel', 'Record retention')}</dt>
            <dd>{t('accessibilityPage.recordRetentionValue', "Grievances and the library's responses are retained for 3 years.")}</dd>
          </div>
          <div>
            <dt className="font-semibold">{t('accessibilityPage.alternativeFormatsLabel', 'Alternative formats')}</dt>
            <dd>{t('accessibilityPage.alternativeFormatsValue', 'This procedure, and any library information, is available in large print or other accessible formats on request.')}</dd>
          </div>
        </dl>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-4">
          {t('accessibilityPage.noRetaliationText', 'The library will not retaliate against anyone for filing a grievance or for participating in the resolution of one.')}
        </p>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">
          {t(
            'accessibilityPage.filingGrievanceRightsText',
            'Filing a grievance with the library does not affect your right to file a complaint with the U.S. Department of Justice or to pursue other remedies available under the ADA.',
          )}
        </p>
      </section>
    </div>
  )
}
