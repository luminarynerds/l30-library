/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { BookOpen, Users, DollarSign, Clock, Shield, Mail, TrendingUp, Code2, Library, Accessibility } from 'lucide-react'
import { useBranding } from '@/contexts/BrandingContext'
import { fetchApi } from '@/api/fetchApi'
import { useTranslation } from '@/i18n'

export default function LibrarianConnectPage() {
  const { t } = useTranslation()
  const branding = useBranding()
  const [searchParams] = useSearchParams();
  const libId = searchParams.get('lib');
  const [libStats, setLibStats] = useState<{ library_name: string; total_requests: number; unique_titles_requested: number } | null>(null);

  useEffect(() => {
    if (!libId) return;
    fetchApi(`/patron-requests/stats/${libId}`)
      .then((data: { library_name: string; total_requests: number; unique_titles_requested: number } | null) => {
        if (data) setLibStats(data);
      })
      .catch(() => {});
  }, [libId]);

  return (
    <div className="min-h-screen bg-cream-50 dark:bg-earth-950">
      {/* Hero */}
      <section className="py-20 px-4">
        <div className="max-w-3xl mx-auto text-center">
          <h1 className="text-4xl md:text-5xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-6">
            {t('librarianConnect.yourPatronsWantIndieEbooks', 'Your Patrons Want Indie eBooks')}
          </h1>
          <p className="text-xl text-lsc-dark/70 dark:text-lsc-cream/70 mb-8 leading-relaxed">
            {t('librarianConnect.patronsAreRequestingIndieTitles', 'Patrons are requesting indie titles at your library. Connect to our shared lending platform and start fulfilling those requests today.')}
          </p>
          <a
            href={`mailto:${branding.contact_email}?subject=Library%20Connection%20Inquiry`}
            className="inline-flex items-center gap-2 px-8 py-4 bg-status-warning-600 hover:bg-status-warning-700
              text-white font-medium rounded-lg text-lg motion-safe:transition-colors"
          >
            <Mail className="w-5 h-5" />
            {t('librarianConnect.getConnected', 'Get Connected')}
          </a>
        </div>
      </section>

      {/* Request stats banner */}
      {libStats && libStats.total_requests > 0 && (
        <section className="px-4 -mt-8 mb-8">
          <div className="max-w-3xl mx-auto bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 rounded-xl p-6 text-center">
            <TrendingUp className="w-8 h-8 mx-auto mb-3 text-status-warning-600" />
            <p className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-1">
              {t('librarianConnect.patronRequestCount', { count: libStats.total_requests })}
            </p>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
              {t('librarianConnect.forTitleCount', { count: libStats.unique_titles_requested })} {t('librarianConnect.atLibrary', { library: libStats.library_name })}
            </p>
          </div>
        </section>
      )}

      {/* How it works */}
      <section className="py-16 px-4 bg-lsc-white dark:bg-earth-900">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-12 text-center">
            {t('librarianConnect.howItWorks', 'How It Works')}
          </h2>
          <div className="grid md:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="w-14 h-14 mx-auto mb-4 bg-status-warning-100 dark:bg-status-warning-900/30 rounded-xl
                flex items-center justify-center">
                <BookOpen className="w-7 h-7 text-status-warning-600" />
              </div>
              <h3 className="font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">{t('librarianConnect.browseAndBuyCopies', 'Browse & Buy Copies')}</h3>
              <p className="text-earth-600 dark:text-earth-400 text-sm">
                {t('librarianConnect.browseTheIndieCatalogBuy', 'Browse the indie catalog. Buy copies at $10 each — the full amount goes directly to the author. One copy = one concurrent user.')}
              </p>
            </div>
            <div className="text-center">
              <div className="w-14 h-14 mx-auto mb-4 bg-sage-100 dark:bg-sage-900/30 rounded-xl
                flex items-center justify-center">
                <Users className="w-7 h-7 text-sage-600" />
              </div>
              <h3 className="font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">{t('librarianConnect.patronsBorrow', 'Patrons Borrow')}</h3>
              <p className="text-earth-600 dark:text-earth-400 text-sm">
                {t('librarianConnect.patronsBorrowThroughYourLibrarys', "Patrons borrow through your library's website. They see your brand, never ours. Ebook cards can be funded by your Friends group or Foundation.")}
              </p>
            </div>
            <div className="text-center">
              <div className="w-14 h-14 mx-auto mb-4 bg-earth-100 dark:bg-earth-800 rounded-xl
                flex items-center justify-center">
                <Shield className="w-7 h-7 text-earth-600" />
              </div>
              <h3 className="font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">{t('librarianConnect.ownItForever', 'Own It Forever')}</h3>
              <p className="text-earth-600 dark:text-earth-400 text-sm">
                {t('librarianConnect.licensesArePerpetualNoExpirations', 'Licenses are perpetual. No expirations, no re-purchasing. Your copies are yours forever.')}
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section className="py-16 px-4">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-3xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-8 text-center">
            {t('librarianConnect.simpleTransparentPricing', 'Simple, Transparent Pricing')}
          </h2>
          <div className="bg-lsc-white dark:bg-earth-900 rounded-xl shadow-soft-md p-8">
            <div className="space-y-6">
              <div className="flex items-start gap-4">
                <DollarSign className="w-6 h-6 text-status-warning-600 mt-1 shrink-0" />
                <div>
                  <h3 className="font-serif font-bold text-lsc-dark dark:text-lsc-cream">{t('librarianConnect.tenDollarsPerCopy', '$10 per copy')}</h3>
                  <p className="text-earth-600 dark:text-earth-400 text-sm">
                    {t('librarianConnect.flatRateGoesDirectlyToThe', 'Flat rate. Goes directly to the author (minus payment processing). Buy as many copies as you need for concurrent lending.')}
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-4">
                <Clock className="w-6 h-6 text-sage-600 mt-1 shrink-0" />
                <div>
                  <h3 className="font-serif font-bold text-lsc-dark dark:text-lsc-cream">{t('librarianConnect.freeToConnect', 'Free to connect')}</h3>
                  <p className="text-earth-600 dark:text-earth-400 text-sm">
                    {t('librarianConnect.openAccessTitlesProjectGutenberg', 'Open access titles (Project Gutenberg, Standard Ebooks) are free immediately. No platform fees to get started — browse the full catalog at no cost.')}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Platform stats */}
      <section className="py-16 px-4 bg-lsc-white dark:bg-earth-900">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-3xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-8 text-center">
            {t('librarianConnect.byTheNumbers', 'By the Numbers')}
          </h2>
          <div className="grid grid-cols-3 gap-6 text-center">
            <div>
              <p className="text-3xl font-bold text-status-warning-600">77+</p>
              <p className="text-sm text-earth-600 dark:text-earth-400 mt-1">{t('librarianConnect.titlesAvailable', 'Titles Available')}</p>
            </div>
            <div>
              <p className="text-3xl font-bold text-sage-600">3</p>
              <p className="text-sm text-earth-600 dark:text-earth-400 mt-1">{t('librarianConnect.librariesConnected', 'Libraries Connected')}</p>
            </div>
            <div>
              <p className="text-3xl font-bold text-lsc-dark/70 dark:text-lsc-cream/70">$10</p>
              <p className="text-sm text-earth-600 dark:text-earth-400 mt-1">{t('librarianConnect.perCopyAlways', 'Per Copy, Always')}</p>
            </div>
          </div>
        </div>
      </section>

      {/* Beyond ebooks: the full ILS */}
      <section className="py-16 px-4">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4 text-center">
            {t('librarianConnect.moreThanEbooksACompleteLibrary', 'More than ebooks. A complete library system.')}
          </h2>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-center max-w-2xl mx-auto mb-12 leading-relaxed">
            {t('librarianConnect.theIndieEbookLendingHereRuns', "The indie ebook lending here runs on L30, a complete, open-source library system. Catalog, circulation, holds, staff tools, the whole thing. The site you're on is a real library running on it. If you're rethinking your ILS, not just your ebooks, there's a lot more here.")}
          </p>
          <div className="grid md:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="w-14 h-14 mx-auto mb-4 bg-lsc-rose/10 rounded-xl flex items-center justify-center">
                <Code2 className="w-7 h-7 text-lsc-rose" />
              </div>
              <h3 className="font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">{t('librarianConnect.openSourceYoursToOwn', 'Open source, yours to own')}</h3>
              <p className="text-earth-600 dark:text-earth-400 text-sm">
                {t('librarianConnect.agplLicensedNoPerseatFees', 'AGPL-licensed. No per-seat fees, no vendor lock-in. Self-host it or let us run it. Your data stays yours.')}
              </p>
            </div>
            <div className="text-center">
              <div className="w-14 h-14 mx-auto mb-4 bg-sage-100 dark:bg-sage-900/30 rounded-xl flex items-center justify-center">
                <Library className="w-7 h-7 text-sage-600" />
              </div>
              <h3 className="font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">{t('librarianConnect.theWholeCatalogStack', 'The whole catalog stack')}</h3>
              <p className="text-earth-600 dark:text-earth-400 text-sm">
                {t('librarianConnect.catalogingCirculationHoldsAcquisitions', 'Cataloging, circulation, holds, acquisitions, reports, staff tools. Everything a small library runs on, in one system.')}
              </p>
            </div>
            <div className="text-center">
              <div className="w-14 h-14 mx-auto mb-4 bg-status-warning-100 dark:bg-status-warning-900/30 rounded-xl flex items-center justify-center">
                <Accessibility className="w-7 h-7 text-status-warning-600" />
              </div>
              <h3 className="font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">{t('librarianConnect.accessibleByDefault', 'Accessible by default')}</h3>
              <p className="text-earth-600 dark:text-earth-400 text-sm">
                {t('librarianConnect.builtOnAtkinsonHyperlegibleWith', 'Built on Atkinson Hyperlegible with a neurodivergent-aware toolkit. WCAG is the floor, not an upsell.')}
              </p>
            </div>
          </div>
          <div className="text-center mt-12">
            <Link to="/for-libraries" className="inline-flex items-center gap-2 px-6 py-3 border border-lsc-dark dark:border-lsc-cream text-lsc-dark dark:text-lsc-cream font-medium rounded-lg motion-safe:transition-colors hover:bg-lsc-dark hover:text-lsc-cream dark:hover:bg-lsc-cream dark:hover:text-lsc-dark">
              {t('librarianConnect.seeL30ForLibraries', 'See L30 for libraries →')}
            </Link>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-16 px-4 bg-earth-900 dark:bg-earth-950">
        <div className="max-w-2xl mx-auto text-center">
          <h2 className="text-3xl font-serif font-bold text-white mb-4">
            {t('librarianConnect.readyToConnect', 'Ready to Connect?')}
          </h2>
          <p className="text-earth-300 mb-8">
            {t('librarianConnect.setupTakesAbout15Minutes', "Setup takes about 15 minutes. We'll walk you through everything.")}
          </p>
          <a
            href={`mailto:${branding.contact_email}?subject=Library%20Connection%20Inquiry`}
            className="inline-flex items-center gap-2 px-8 py-4 bg-status-warning-600 hover:bg-status-warning-700
              text-white font-medium rounded-lg text-lg motion-safe:transition-colors"
          >
            <Mail className="w-5 h-5" />
            {t('librarianConnect.emailUsToGetStarted', 'Email Us to Get Started')}
          </a>
        </div>
      </section>
    </div>
  );
}
