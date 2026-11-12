/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Link } from 'react-router-dom'
import { ShieldCheck, Mail, Clock, CheckCircle2, XCircle, Lock } from 'lucide-react'
import { t } from '@/i18n'

export default function SecurityPage(): JSX.Element {
  return (
    <div className="space-y-8 max-w-3xl">
      <header className="bg-gradient-to-r from-lsc-rose to-lsc-rose dark:from-lsc-brown dark:to-earth-800 rounded-xl p-8 text-white">
        <div className="flex items-center gap-4 mb-4">
          <div className="w-16 h-16 bg-lsc-white rounded-xl flex items-center justify-center">
            <ShieldCheck aria-hidden="true" className="w-8 h-8" color="#7C6545" />
          </div>
          <div>
            <h1 className="text-3xl font-serif font-bold">{t('securityPage.heading', 'Security & Responsible Disclosure')}</h1>
            <p className="text-white">{t('securityPage.subheading', 'How to report a vulnerability in L30')}</p>
          </div>
        </div>
      </header>

      <aside className="bg-lsc-cream dark:bg-lsc-brown/20 border-l-4 border-lsc-rose dark:border-lsc-rose-light rounded-r-xl p-4 flex gap-3">
        <Lock aria-hidden="true" className="w-5 h-5 mt-0.5 shrink-0 text-lsc-rose dark:text-lsc-rose-light" />
        <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
          {t('securityPage.privacyCalloutPre', 'Looking for how we protect your personal information and keep your reading history private? That is on our ')}{' '}
          <Link to="/privacy" className="font-semibold underline text-lsc-dark dark:text-lsc-cream">{t('privacy.pageTitle', 'Privacy Policy')}</Link>.
          {' '}{t('securityPage.privacyCalloutPost', 'This page is for reporting a security vulnerability.')}
        </p>
      </aside>

      <section className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
        <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-3">{t('securityPage.foundIssueHeading', 'If you found a security issue')}</h2>
        <p className="text-lsc-dark/80 dark:text-lsc-cream/80 mb-4">
          {t('securityPage.foundIssueBody', 'We welcome reports from security researchers, library staff, patrons, and anyone else who finds a vulnerability in L30 or any service we operate. Email a description and reproduction steps to:')}
        </p>
        <p className="text-lsc-dark dark:text-lsc-cream font-mono">
          <Mail aria-hidden="true" className="inline w-4 h-4 mr-2 text-lsc-rose dark:text-lsc-rose-light" />
          <a href="mailto:security@l30.org" className="underline">security@l30.org</a>
        </p>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-3">
          {t('securityPage.pgpNote', 'For sensitive disclosures, request our PGP key in your first email and we will reply with it.')}
        </p>
      </section>

      <section className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
        <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-3">{t('securityPage.whatToExpectHeading', 'What to expect')}</h2>
        <ul className="space-y-3 text-lsc-dark/80 dark:text-lsc-cream/80">
          <li className="flex gap-3"><Clock aria-hidden="true" className="w-5 h-5 mt-0.5 text-lsc-rose dark:text-lsc-rose-light" /><span><strong>{t('securityPage.expectAckLead', 'Acknowledgement within 2 business days.')}</strong> {t('securityPage.expectAckRest', 'A real human will reply.')}</span></li>
          <li className="flex gap-3"><CheckCircle2 aria-hidden="true" className="w-5 h-5 mt-0.5 text-lsc-rose dark:text-lsc-rose-light" /><span><strong>{t('securityPage.expectSafeHarborLead', 'Good-faith safe harbor.')}</strong> {t('securityPage.expectSafeHarborRest', 'We will not pursue legal action against researchers acting in good faith under this policy.')}</span></li>
          <li className="flex gap-3"><CheckCircle2 aria-hidden="true" className="w-5 h-5 mt-0.5 text-lsc-rose dark:text-lsc-rose-light" /><span><strong>{t('securityPage.expectCoordinatedLead', 'Coordinated disclosure.')}</strong> {t('securityPage.expectCoordinatedRest', 'Please give us reasonable time (typically 90 days) before public disclosure.')}</span></li>
          <li className="flex gap-3"><CheckCircle2 aria-hidden="true" className="w-5 h-5 mt-0.5 text-lsc-rose dark:text-lsc-rose-light" /><span><strong>{t('securityPage.expectCreditLead', 'Credit when you want it.')}</strong> {t('securityPage.expectCreditRest', "If you’d like attribution after the fix ships, we’ll list you in our acknowledgements.")}</span></li>
        </ul>
      </section>

      <section className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
        <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-3">{t('securityPage.scopeHeading', 'Scope')}</h2>
        <div className="grid md:grid-cols-2 gap-4">
          <div>
            <h3 className="font-semibold text-lsc-dark dark:text-lsc-cream mb-2 flex items-center gap-2"><CheckCircle2 aria-hidden="true" className="w-4 h-4 text-lsc-rose" /> {t('securityPage.inScopeHeading', 'In scope')}</h3>
            <ul className="list-disc pl-5 text-sm text-lsc-dark/80 dark:text-lsc-cream/80 space-y-1">
              <li>{t('securityPage.inScope1', 'l30.org and any subdomain we operate')}</li>
              <li>{t('securityPage.inScope2', 'Authentication, authorization, and session handling')}</li>
              <li>{t('securityPage.inScope3', 'Data exposure (patron records, staff records, catalog data)')}</li>
              <li>{t('securityPage.inScope4', 'Injection (SQL, command, template), SSRF, deserialization')}</li>
              <li>{t('securityPage.inScope5', 'Workflow bypass affecting circulation, holds, or fines')}</li>
              <li>{t('securityPage.inScope6', 'Account takeover or privilege escalation')}</li>
            </ul>
          </div>
          <div>
            <h3 className="font-semibold text-lsc-dark dark:text-lsc-cream mb-2 flex items-center gap-2"><XCircle aria-hidden="true" className="w-4 h-4 text-lsc-brown" /> {t('securityPage.outOfScopeHeading', 'Out of scope')}</h3>
            <ul className="list-disc pl-5 text-sm text-lsc-dark/80 dark:text-lsc-cream/80 space-y-1">
              <li>{t('securityPage.outOfScope1', 'Denial-of-service or volumetric attacks')}</li>
              <li>{t('securityPage.outOfScope2', 'Spam, phishing, or social engineering of staff')}</li>
              <li>{t('securityPage.outOfScope3', 'Issues in third-party services we use (please report directly to them)')}</li>
              <li>{t('securityPage.outOfScope4', 'Self-XSS, clickjacking on non-sensitive pages')}</li>
              <li>{t('securityPage.outOfScope5', 'Outdated software with no proven exploit')}</li>
              <li>{t('securityPage.outOfScope6', 'Physical attacks or attacks requiring local access')}</li>
            </ul>
          </div>
        </div>
      </section>

      <section className="bg-lsc-cream dark:bg-lsc-brown/20 rounded-xl p-6">
        <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-3">{t('securityPage.pleaseDontHeading', "Please don’t")}</h2>
        <ul className="space-y-2 text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
          <li className="flex gap-3"><XCircle aria-hidden="true" className="w-4 h-4 mt-0.5 shrink-0 text-lsc-brown dark:text-lsc-rose-light" /><span>{t('securityPage.dont1', "Access, modify, or destroy data that isn’t yours.")}</span></li>
          <li className="flex gap-3"><XCircle aria-hidden="true" className="w-4 h-4 mt-0.5 shrink-0 text-lsc-brown dark:text-lsc-rose-light" /><span>{t('securityPage.dont2', 'Disrupt service for other users.')}</span></li>
          <li className="flex gap-3"><XCircle aria-hidden="true" className="w-4 h-4 mt-0.5 shrink-0 text-lsc-brown dark:text-lsc-rose-light" /><span>{t('securityPage.dont3', "Publicly disclose the issue before we’ve had a chance to fix it.")}</span></li>
          <li className="flex gap-3"><XCircle aria-hidden="true" className="w-4 h-4 mt-0.5 shrink-0 text-lsc-brown dark:text-lsc-rose-light" /><span>{t('securityPage.dont4', 'Use automated scanners that generate substantial traffic.')}</span></li>
        </ul>
      </section>

      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('securityPage.lastReviewed', 'Last reviewed June 17, 2026.')}</p>
    </div>
  )
}
