/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Heart,
  Gift,
  BookOpen,
  Users,
  Laptop,
  Baby,
  Building2,
  HandHeart,
  Mail,
  Banknote,
  CircleDollarSign,
  CheckCircle2,
  Feather,
  Calendar,
  Shield
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import StandardPageLayout from '@/components/StandardPageLayout'
import { useTranslation } from '@/i18n'
import { useBranding } from '@/contexts/BrandingContext'
import { usePageTitle } from '@/hooks/usePageTitle'

// Allowlist of lucide icons the donate config may reference by name. Unknown or
// missing names fall back to Gift so a typo never breaks the page.
const ICON_MAP: Record<string, LucideIcon> = {
  Heart,
  Gift,
  BookOpen,
  Users,
  Laptop,
  Baby,
  Building2,
  HandHeart,
  Banknote,
  Feather,
  Calendar,
}

function ConfigIcon({ name, className }: { name?: string; className?: string }): React.ReactElement {
  const Cmp = (name && ICON_MAP[name]) || Gift
  return <Cmp aria-hidden="true" className={className} />
}

// Plain-language equivalents so each amount means something concrete.
const AMOUNT_BUYS: Record<number, string> = {
  25: "one new hardcover",
  50: "a week of free wifi for a family",
  100: "a child's summer reading kit",
  250: "books for a whole class visit",
}

export default function DonatePage(): React.ReactElement {
  const branding = useBranding()
  usePageTitle('Support Your Library', `Support ${branding.library_short_name} with a donation. Every gift helps us provide free access to books, programs, and technology.`)
  const { t } = useTranslation()
  const [selectedAmount, setSelectedAmount] = useState<number | null>(25)
  const [customAmount, setCustomAmount] = useState('')

  const cfg = branding.donate_config ?? {}
  const tiers = cfg.tiers ?? []
  const impactAreas = cfg.impact_areas ?? []
  const waysToGive = cfg.ways_to_give ?? []
  const testimonials = cfg.testimonials ?? []
  const highlights = cfg.highlights ?? []
  const monthlyAmounts = cfg.monthly?.amounts ?? []

  return (
    <StandardPageLayout
      title={t('donate.supportYourLibrary', 'Support Your Library')}
      subtitle={t('donate.yourGenerosityHelpsUsServe')}
      icon={Heart}
    >


      {/* Why Donate Banner */}
      {cfg.intro && (
        <section className="bg-gradient-to-r from-lsc-rose/10 to-status-warning-100 dark:from-lsc-rose/20 dark:to-status-warning-900/20 border border-lsc-rose/20 dark:border-lsc-rose/30 rounded-xl p-6">
          <div className="flex items-start gap-4">
            <div className="w-10 h-10 rounded-full bg-lsc-rose/20 dark:bg-lsc-rose/30 flex items-center justify-center flex-shrink-0">
              <CircleDollarSign aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
            </div>
            <div>
              <h2 className="font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">{t('donate.whyYourSupportMatters')}</h2>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
                {cfg.intro}
              </p>
              {highlights.length > 0 && (
                <div className="flex flex-wrap gap-4 text-sm">
                  {highlights.map((highlight) => (
                    <div key={highlight} className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70">
                      <CheckCircle2 aria-hidden="true" className="w-4 h-4 text-status-success-600 dark:text-status-success-400" />
                      <span>{highlight}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </section>
      )}

      {/* Quick Donate */}
      <section className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm text-center">
        <h2 className="font-serif font-bold text-2xl text-lsc-dark dark:text-lsc-cream mb-4">{t('donate.makeAGift', 'Make a Gift')}</h2>
        <div className="flex flex-wrap items-center justify-center gap-3 mb-4">
          {[25, 50, 100, 250].map((amount) => (
            <button
              key={amount}
              onClick={() => { setSelectedAmount(amount); setCustomAmount('')} }
              aria-pressed={selectedAmount === amount}
              aria-label={`Donate $${amount}: ${AMOUNT_BUYS[amount]}`}
              className={`flex flex-col items-center px-6 py-2.5 rounded-xl font-medium transition-colors ${selectedAmount === amount ? 'bg-lsc-rose text-white' : 'bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream border border-lsc-border dark:border-earth-700 hover:border-lsc-rose'}`}
            >
              <span className="text-lg font-bold leading-tight">${amount}</span>
              <span className={`text-xs font-normal leading-tight mt-0.5 ${selectedAmount === amount ? 'text-white/90' : 'text-lsc-dark/60 dark:text-lsc-cream/60'}`}>{AMOUNT_BUYS[amount]}</span>
            </button>
          ))}
          <input
            type="number"
            placeholder="Other amount"
            value={customAmount}
            onChange={(e) => { setCustomAmount(e.target.value); setSelectedAmount(e.target.value ? null : 25) }}
            className="w-32 px-4 py-2.5 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream text-center"
            aria-label="Enter custom donation amount"
            min="1"
          />
        </div>
        <a
          href={`mailto:${branding.giving_email}?subject=Donation%20-%20$${selectedAmount || customAmount || ''}`}
          className={`inline-flex items-center justify-center gap-2 px-6 py-3 bg-lsc-rose text-white font-medium rounded-xl transition-colors ${!selectedAmount && !customAmount ? 'opacity-50 pointer-events-none' : 'hover:bg-lsc-rose/90'}`}
          aria-disabled={!selectedAmount && !customAmount}
          tabIndex={!selectedAmount && !customAmount ? -1 : undefined}
          onClick={(e) => { if (!selectedAmount && !customAmount) e.preventDefault() }}
        >
          <Heart aria-hidden="true" className="w-5 h-5" />
          Donate Now
        </a>
      </section>

      {/* Donation Tiers */}
      {tiers.length > 0 && (
        <section>
          <h2 className="font-serif font-bold text-2xl text-lsc-dark dark:text-lsc-cream mb-6 text-center">
            {t('donate.givingLevels', 'Giving Levels')}
          </h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {tiers.map((tier) => (
              <div
                key={tier.name}
                className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm border border-lsc-border dark:border-earth-700 hover:border-lsc-rose/50 dark:hover:border-lsc-rose/50 transition-colors"
              >
                <div className="w-10 h-10 rounded-xl bg-lsc-cream dark:bg-lsc-brown/30 flex items-center justify-center mb-4 text-lsc-rose dark:text-lsc-rose-light">
                  <ConfigIcon name={tier.icon} className="w-6 h-6" />
                </div>
                <h3 className="font-serif font-bold text-lg text-lsc-dark dark:text-lsc-cream mb-1">
                  {tier.name}
                </h3>
                <p className="text-2xl font-bold text-lsc-rose dark:text-lsc-rose-light mb-2">
                  {tier.amount}
                </p>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
                  {tier.description}
                </p>
                <ul className="space-y-2">
                  {tier.benefits.map((benefit, index) => (
                    <li key={index} className="flex items-start gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      <CheckCircle2 aria-hidden="true" className="w-4 h-4 text-status-success-600 dark:text-status-success-400 flex-shrink-0 mt-0.5" />
                      <span>{benefit}</span>
                    </li>
                  ))}
                </ul>
                <a
                  href={`mailto:${branding.giving_email}?subject=Donation%20-%20${tier.name}%20(${tier.amount})`}
                  className="mt-4 w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-lsc-rose text-white font-medium rounded-xl text-sm hover:bg-lsc-rose/90 transition-colors"
                  aria-label={`Donate ${tier.amount} as a ${tier.name}`}
                >
                  <Mail aria-hidden="true" className="w-4 h-4" />
                  Donate {tier.amount}
                </a>
              </div>
            ))}
          </div>
        </section>
      )}


      {/* Monthly Giving */}
      {(monthlyAmounts.length > 0 || cfg.monthly?.note) && (
        <section className="bg-gradient-to-r from-lsc-rose/10 to-lsc-cream dark:from-lsc-rose/20 dark:to-earth-800 rounded-xl p-6 border border-lsc-rose/20 dark:border-lsc-rose/30">
          <div className="flex items-start gap-4">
            <div className="w-10 h-10 rounded-full bg-lsc-rose/20 dark:bg-lsc-rose/30 flex items-center justify-center flex-shrink-0">
              <Calendar aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
            </div>
            <div>
              <h2 className="font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">Give Monthly, Make It Last</h2>
              {cfg.monthly?.note && (
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">{cfg.monthly.note}</p>
              )}
              {monthlyAmounts.length > 0 && (
                <div className="flex flex-wrap gap-2 mb-4">
                  {monthlyAmounts.map((amount) => (
                    <span key={amount} className="px-3 py-1 bg-lsc-rose/10 dark:bg-lsc-rose/20 text-lsc-rose dark:text-lsc-rose-light rounded-full text-sm font-medium">{amount}</span>
                  ))}
                </div>
              )}
              <a href={`mailto:${branding.giving_email}?subject=Monthly%20Giving%20Inquiry`} className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white font-medium rounded-xl text-sm hover:bg-lsc-rose/90 transition-colors">
                <Mail aria-hidden="true" className="w-4 h-4" />
                Set Up Monthly Giving
              </a>
            </div>
          </div>
        </section>
      )}

      {/* How to Donate */}
      <section className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
        <h2 className="font-serif font-bold text-xl text-lsc-dark dark:text-lsc-cream mb-6">
          {t('donate.howToDonate', 'How to Donate')}
        </h2>
        <div className="grid md:grid-cols-3 gap-6">
          {/* Online */}
          <div className="bg-lsc-cream dark:bg-lsc-brown rounded-xl p-5">
            <div className="w-10 h-10 rounded-full bg-lsc-white dark:bg-earth-800 flex items-center justify-center mb-4">
              <Mail aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
            </div>
            <h3 className="font-medium text-lsc-dark dark:text-lsc-cream mb-2">{t('donate.contactUsToDonate', 'Contact Us to Donate')}</h3>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
              {t('donate.contactUsToDonateDescription', 'Reach out to arrange your donation. We accept checks, bank transfers, and card payments.')}
            </p>
            <a
              href={`mailto:${branding.giving_email}?subject=Donation%20Inquiry`}
              className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white font-medium rounded-xl text-sm hover:bg-lsc-rose/80 transition-colors"
            >
              <Mail aria-hidden="true" className="w-4 h-4" />
              {branding.giving_email}
            </a>
          </div>

          {/* By Mail */}
          <div className="bg-lsc-cream dark:bg-lsc-brown rounded-xl p-5">
            <div className="w-10 h-10 rounded-full bg-lsc-white dark:bg-earth-800 flex items-center justify-center mb-4">
              <Mail aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
            </div>
            <h3 className="font-medium text-lsc-dark dark:text-lsc-cream mb-2">{t('donate.byMail', 'By Mail')}</h3>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
              {t('donate.byMailDescription', 'Mail a check payable to the library. Include a note if you would like to direct your gift to a specific program.')}
            </p>
            <Link
              to="/branches"
              className="text-sm text-lsc-rose hover:text-lsc-rose/80 dark:text-lsc-rose-light dark:hover:text-lsc-rose font-medium"
            >
              Find our mailing address
            </Link>
          </div>

          {/* In Person */}
          <div className="bg-lsc-cream dark:bg-lsc-brown rounded-xl p-5">
            <div className="w-10 h-10 rounded-full bg-lsc-white dark:bg-earth-800 flex items-center justify-center mb-4">
              <Building2 aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
            </div>
            <h3 className="font-medium text-lsc-dark dark:text-lsc-cream mb-2">{t('donate.inPerson', 'In Person')}</h3>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
              {t('donate.inPersonDescription', 'Visit the circulation desk during library hours to make a donation by cash, check, or card.')}
            </p>
            <Link
              to="/contact"
              className="text-sm text-lsc-rose hover:text-lsc-rose/80 dark:text-lsc-rose-light dark:hover:text-lsc-rose font-medium"
            >
              {t('donate.viewHoursAndLocation', 'View hours & location')}
            </Link>
          </div>
        </div>
      </section>


      {/* Tax Notice */}
      {cfg.tax_note && (
        <p className="text-sm text-lsc-dark/60 dark:text-lsc-cream/60 text-center flex items-center justify-center gap-2 py-4">
          <Shield aria-hidden="true" className="w-4 h-4 text-status-success-600 dark:text-status-success-400 flex-shrink-0" />
          {cfg.tax_note}
        </p>
      )}

      {/* Impact Areas */}
      {impactAreas.length > 0 && (
        <section>
          <h2 className="font-serif font-bold text-2xl text-lsc-dark dark:text-lsc-cream mb-2 text-center">
            {t('donate.whereYourDonationGoes', 'Where Your Donation Goes')}
          </h2>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-center mb-6 max-w-2xl mx-auto">
            {t('donate.whereYourDonationGoesSubheading', "Choose to direct your gift to a specific area, or let us use it where it's needed most.")}
          </p>
          <div className="grid md:grid-cols-2 gap-6">
            {impactAreas.map((area, index) => (
              <div
                key={index}
                className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm flex gap-4"
              >
                <div className="w-12 h-12 rounded-xl bg-lsc-cream dark:bg-lsc-brown/30 flex items-center justify-center flex-shrink-0 text-lsc-rose dark:text-lsc-rose-light">
                  <ConfigIcon name={area.icon} className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
                    {area.title}
                  </h3>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    {area.description}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Other Ways to Give */}
      {waysToGive.length > 0 && (
        <section className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
          <h2 className="font-serif font-bold text-xl text-lsc-dark dark:text-lsc-cream mb-6">
            {t('donate.otherWaysToGive', 'Other Ways to Give')}
          </h2>
          <div className="grid md:grid-cols-2 gap-6">
            {waysToGive.map((way, index) => (
              <div key={index} className="border border-lsc-border dark:border-earth-700 rounded-xl p-5">
                <div className="flex items-center gap-3 mb-3">
                  <ConfigIcon name={way.icon} className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
                  <h3 className="font-medium text-lsc-dark dark:text-lsc-cream">{way.title}</h3>
                </div>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  {way.description}
                </p>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Community Supporters */}
      {testimonials.length > 0 && (
        <section>
          <h2 className="font-serif font-bold text-xl text-lsc-dark dark:text-lsc-cream mb-6 text-center">Join Our Community of Supporters</h2>
          <div className="grid md:grid-cols-3 gap-4">
            {testimonials.map((testimonial, index) => (
              <div key={index} className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm border border-lsc-border dark:border-earth-700">
                <div className="flex items-center gap-3 mb-2">
                  <div className="w-10 h-10 rounded-full bg-lsc-cream dark:bg-earth-700 flex items-center justify-center text-sm font-bold text-lsc-rose">{testimonial.initials}</div>
                  <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">{testimonial.name}</span>
                </div>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 italic">&ldquo;{testimonial.quote}&rdquo;</p>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Contact Section */}
      <section className="bg-gradient-to-br from-lsc-cream to-lsc-cream dark:from-earth-800 dark:to-earth-800 rounded-xl p-6">
        <div className="text-center max-w-2xl mx-auto">
          <h2 className="font-serif font-bold text-xl text-lsc-dark dark:text-lsc-cream mb-4">
            {t('donate.questionsAboutGiving', 'Questions About Giving?')}
          </h2>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-6">
            {t('donate.questionsAboutGivingBody', "We're happy to discuss giving options, memorial gifts, matching programs, or any other questions you have.")}
          </p>
          <div className="flex items-center justify-center">
            <a
              href={`mailto:${branding.giving_email}`}
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream font-medium rounded-xl border border-lsc-border dark:border-earth-700 hover:bg-lsc-cream dark:hover:bg-earth-600 transition-colors"
            >
              <Mail aria-hidden="true" className="w-4 h-4" />
              {branding.giving_email}
            </a>
          </div>
        </div>
      </section>

      {/* Thank You */}
      <section className="text-center py-6">
        <Heart aria-hidden="true" className="w-8 h-8 text-lsc-rose dark:text-lsc-rose-light mx-auto mb-4" />
        <h2 className="font-serif font-bold text-xl text-lsc-dark dark:text-lsc-cream mb-2">
          {t('donate.thankYouForYourSupport', 'Thank You for Your Support')}
        </h2>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 max-w-xl mx-auto">
          {t('donate.thankYouBody', 'Every gift, no matter the size, helps us continue serving our community.')}
          <br />
          {t('donate.thankYouBodyGrateful', 'We are grateful for your generosity.')}
        </p>
      </section>
    </StandardPageLayout>
  )
}
