/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import {
  Server, Accessibility, BookOpen,
} from 'lucide-react'
import { usePageTitle } from '@/hooks/usePageTitle'
import PageContainer from '@/components/layout/PageContainer'

export default function DemoLandingPage(): React.ReactElement {
  usePageTitle('L30 — Library Management System')

  return (
    <div className="min-h-screen">
      {/* Hero */}
      <section className="relative overflow-hidden py-20 lg:py-32">
        <div className="absolute inset-0 bg-gradient-to-br from-earth-900 via-earth-800 to-earth-900" />
        <div className="absolute inset-0 opacity-20">
          <div className="absolute top-20 left-10 w-72 h-72 bg-lsc-rose rounded-full blur-[128px]" />
          <div className="absolute bottom-20 right-10 w-96 h-96 bg-lsc-green rounded-full blur-[128px]" />
        </div>

        <PageContainer className="relative text-center">
          <div className="flex items-center justify-center gap-2 mb-6">
            <BookOpen className="w-8 h-8 text-brand-300" aria-hidden="true" />
            <span className="text-brand-300 font-semibold text-lg tracking-wide uppercase">L30</span>
          </div>

          <h1 className="font-serif text-4xl md:text-5xl lg:text-6xl text-lsc-cream mb-6 motion-safe:animate-hero-fade-up-0">
            Your library, running in 60 seconds.
          </h1>
          <p className="text-xl md:text-2xl text-earth-600 max-w-2xl mx-auto mb-12 motion-safe:animate-hero-fade-up-1">
            No sales calls. No contracts. See it for yourself.
          </p>

          {/* CTA */}
          <div className="max-w-lg mx-auto motion-safe:animate-hero-fade-up-2">
            <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm border border-lsc-border dark:border-earth-700 p-8 text-center">
              <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-3">
                See it for yourself
              </h2>
              <p className="text-earth-600 dark:text-earth-400 text-sm mb-6">
                Browse the live catalog, explore staff tools, or schedule a walkthrough with our team.
              </p>
              <div className="space-y-3">
                <a
                  href="/catalog"
                  className="w-full flex items-center justify-center gap-2 bg-lsc-rose hover:bg-brand-600 text-white font-semibold py-3 px-6 rounded-lg transition-colors duration-200 focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2 min-h-[44px]"
                >
                  <BookOpen className="w-5 h-5" aria-hidden="true" />
                  Explore the Library
                </a>
                <a
                  href="mailto:hello@l30.org?subject=L30 Demo Request"
                  className="w-full flex items-center justify-center gap-2 bg-lsc-white dark:bg-earth-700 hover:bg-earth-50 dark:hover:bg-earth-600 text-lsc-dark dark:text-lsc-cream font-semibold py-3 px-6 rounded-lg border-2 border-lsc-border dark:border-earth-600 transition-colors duration-200 focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2 min-h-[44px]"
                >
                  Schedule a Walkthrough
                </a>
              </div>
            </div>
          </div>
        </PageContainer>
      </section>

      {/* Stackable spine */}
      <section className="py-20 bg-earth-50 dark:bg-earth-900">
        <PageContainer>
          <h2 className="font-serif text-3xl text-center text-lsc-dark dark:text-lsc-cream mb-4">
            Start with two things. Stack the rest at your pace.
          </h2>
          <p className="text-earth-600 dark:text-earth-400 text-center max-w-2xl mx-auto mb-12">
            A catalog and a checkout desk is a working library. That&rsquo;s day one. Everything
            else is a switch you flip when it&rsquo;s useful, at your pace.
          </p>

          {/* Sub-block A — always on */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm border border-lsc-border dark:border-earth-700 p-6 mb-8">
            <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-3">
              Always on. No switch to flip.
            </h3>
            <ul className="flex flex-wrap gap-x-2 gap-y-1 text-earth-600 dark:text-earth-400 text-sm leading-relaxed mb-3">
              <li>Catalog</li>
              <li aria-hidden="true">·</li>
              <li>Cataloging</li>
              <li aria-hidden="true">·</li>
              <li>Checkout</li>
              <li aria-hidden="true">·</li>
              <li>Holds</li>
              <li aria-hidden="true">·</li>
              <li>Patron accounts</li>
              <li aria-hidden="true">·</li>
              <li>Reports</li>
            </ul>
            <p className="text-earth-600 dark:text-earth-400 text-sm italic">
              This is the library. It doesn&rsquo;t toggle off.
            </p>
          </div>

          {/* Sub-block B — toggle on when ready */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm border border-lsc-border dark:border-earth-700 p-6">
            <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
              Toggle on when you&rsquo;re ready.
            </h3>
            <ul className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-3 text-earth-600 dark:text-earth-400 text-sm leading-relaxed">
              <li>
                <span className="font-semibold text-lsc-dark dark:text-lsc-cream">Patron Experience</span> — self-checkout, patron portal, reading shelves &amp; goals, family onboarding
              </li>
              <li>
                <span className="font-semibold text-lsc-dark dark:text-lsc-cream">Programs &amp; Spaces</span> — events, meeting rooms, makerspace, storytime, book clubs
              </li>
              <li>
                <span className="font-semibold text-lsc-dark dark:text-lsc-cream">Collections &amp; Digital</span> — acquisitions, serials, streaming, indie ebooks via MetisLib
              </li>
              <li>
                <span className="font-semibold text-lsc-dark dark:text-lsc-cream">Community Services</span> — home delivery, interlibrary loan, outreach, volunteers, teacher &amp; literacy tools
              </li>
              <li>
                <span className="font-semibold text-lsc-dark dark:text-lsc-cream">Staff Operations</span> — scheduling, training, processing queue, SIP2/RFID
              </li>
              <li>
                <span className="font-semibold text-lsc-dark dark:text-lsc-cream">Governance &amp; Reporting</span> — board tools, strategic planning, financial &amp; annual reports, intellectual-freedom tracking
              </li>
            </ul>
          </div>

          <p className="text-earth-600 dark:text-earth-400 text-center max-w-2xl mx-auto mt-8">
            Toggle on what you need. Leave the rest off. Add more as you grow comfortable.
            No migration, no re-implementation, no upsell call.
          </p>
        </PageContainer>
      </section>

      {/* Help-agent beat */}
      <section className="py-20 bg-lsc-white dark:bg-earth-800/50">
        <PageContainer>
          <h2 className="font-serif text-3xl text-center text-lsc-dark dark:text-lsc-cream mb-6">
            Ask it the silly questions. Nobody&rsquo;s keeping score.
          </h2>
          <p className="text-earth-600 dark:text-earth-400 max-w-3xl mx-auto leading-relaxed">
            Every screen has a help chat. Ask it anything, as often as you need — how to renew,
            what an ISBN is, where the bathroom is. It answers only from the help articles your
            staff wrote and approved (no generative model, nothing invented) and hands back the
            answer with a citation. It runs on a model on your own server, so questions never
            leave the building — and it strips emails, phone numbers, and card numbers before
            anything&rsquo;s saved. When it can&rsquo;t help, a librarian picks up with your
            summarized conversation already in hand. No starting over.
          </p>
        </PageContainer>
      </section>

      {/* Constants — two things never toggle off */}
      <section className="py-20 bg-earth-50 dark:bg-earth-900">
        <PageContainer>
          <h2 className="font-serif text-3xl text-center text-lsc-dark dark:text-lsc-cream mb-12">
            Two things never toggle off.
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm border border-lsc-border dark:border-earth-700 p-6 motion-safe:hover:-translate-y-1 motion-safe:transition-transform motion-safe:duration-300">
              <div className="w-12 h-12 rounded-lg bg-lsc-green/10 flex items-center justify-center mb-4">
                <Server className="w-6 h-6 text-lsc-green" aria-hidden="true" />
              </div>
              <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
                Your server, your data.
              </h3>
              <p className="text-earth-600 dark:text-earth-400 text-sm leading-relaxed">
                Runs on your own server. Patron data never leaves your building. Unplug anytime.
              </p>
            </div>

            <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm border border-lsc-border dark:border-earth-700 p-6 motion-safe:hover:-translate-y-1 motion-safe:transition-transform motion-safe:duration-300">
              <div className="w-12 h-12 rounded-lg bg-lsc-rose/10 flex items-center justify-center mb-4">
                <Accessibility className="w-6 h-6 text-lsc-rose" aria-hidden="true" />
              </div>
              <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
                Accessibility, always on.
              </h3>
              <p className="text-earth-600 dark:text-earth-400 text-sm leading-relaxed">
                WCAG AA. Dyslexia fonts, high-contrast, reduced-motion. Not a module you switch
                on. Built into every screen.
              </p>
            </div>
          </div>
        </PageContainer>
      </section>

      {/* Live-demo proof */}
      <section className="py-20 bg-lsc-white dark:bg-earth-800/50">
        <PageContainer className="text-center">
          <h2 className="font-serif text-3xl text-lsc-dark dark:text-lsc-cream mb-4">
            Not a slideshow. It&rsquo;s running.
          </h2>
          <p className="text-earth-600 dark:text-earth-400 max-w-2xl mx-auto mb-8">
            Every link here is the live system, not a screenshot.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-8">
            <a
              href="/catalog"
              className="inline-flex items-center justify-center gap-2 bg-lsc-rose hover:bg-brand-600 text-white font-semibold py-3 px-6 rounded-lg transition-colors duration-200 focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2 min-h-[44px]"
            >
              Browse the live catalog →
            </a>
            <a
              href="/catalog"
              className="inline-flex items-center justify-center gap-2 bg-lsc-white dark:bg-earth-700 hover:bg-earth-50 dark:hover:bg-earth-600 text-lsc-dark dark:text-lsc-cream font-semibold py-3 px-6 rounded-lg border-2 border-lsc-border dark:border-earth-600 transition-colors duration-200 focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2 min-h-[44px]"
            >
              Place a real hold →
            </a>
          </div>
          <p className="text-earth-600 dark:text-earth-400">
            Running live at Little Schitt Creek Library today.
          </p>
        </PageContainer>
      </section>

      {/* Attribute strip */}
      <section className="py-12 bg-earth-50 dark:bg-earth-900">
        <PageContainer>
          <p className="text-center text-sm text-earth-600 dark:text-earth-400">
            Open-source · Self-hosted · Multi-language · WCAG AA
          </p>
        </PageContainer>
      </section>
    </div>
  )
}
