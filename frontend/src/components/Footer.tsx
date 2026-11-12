/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { ChevronUp } from 'lucide-react'
import { FooterCarbonBadge } from './FooterCarbonBadge'
import LanguageSwitcher from './LanguageSwitcher'
import { FooterAddress } from './footer/FooterAddress'
import { FooterSocialLinks } from './footer/FooterSocialLinks'
import { FooterNewsletterForm } from './footer/FooterNewsletterForm'
import { FooterDemoNotice } from './footer/FooterDemoNotice'
import { JsonLdLibrary } from './footer/JsonLdLibrary'
import { useTranslation } from '../i18n/I18nContext'
import { useAccessibility } from '../features/accessibility/hooks/useAccessibility'
import { useOrganizationFeatures } from '../contexts/OrganizationFeaturesContext'

export default function Footer() {
  const { t } = useTranslation()
  const { isFeatureEnabled } = useOrganizationFeatures()
  const { settings: a11ySettings, updateSetting: updateA11ySetting } = useAccessibility()
  const [showBackToTop, setShowBackToTop] = useState(false)

  useEffect(() => {
    const handleScroll = () => setShowBackToTop(window.scrollY > 400)
    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  const scrollToTop = useCallback(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }, [])

  const mainLinks = [
    ...(isFeatureEnabled('collection_management_enabled') ? [{ to: '/catalog', label: t('navigation.catalog') }] : []),
    ...(isFeatureEnabled('events_enabled') ? [{ to: '/events', label: t('navigation.events') }] : []),
    ...(isFeatureEnabled('collection_management_enabled') ? [{ to: '/digital', label: t('navigation.digitalResources') }] : []),
    ...(isFeatureEnabled('meeting_rooms_enabled') ? [{ to: '/rooms', label: t('navigation.rooms') }] : []),
    { to: '/ask-librarian', label: t('navigation.askALibrarian') },
    ...(isFeatureEnabled('community_features_enabled') ? [{ to: '/blog', label: t('navigation.blog', 'Blog') }] : []),
  ]

  const aboutLinks = [
    { to: '/about', label: t('common.about') },
    { to: '/branches', label: t('navigation.hoursAndLocations') },
    { to: '/help', label: t('footer.helpCenter') },
    { to: '/careers', label: t('footer.careers') },
    ...(isFeatureEnabled('board_features_enabled') ? [{ to: '/board/meetings', label: t('footer.boardMeetings') }] : []),
    { to: '/transparency', label: t('footer.transparency', 'Transparency') },
  ]

  const legalLinks = [
    { to: '/legal', label: 'Legal Help' },
    { to: '/privacy', label: t('footer.privacy') },
    { to: '/terms', label: t('footer.terms') },
    { to: '/accessibility', label: t('footer.accessibility') },
    { to: '/security', label: t('footer.security', 'Report a Vulnerability') },
    { to: '/status', label: t('footer.status') },
  ]

  return (
    <>
      <footer
        id="footer"
        className="bg-earth-950 text-earth-300 border-t border-earth-100 dark:border-earth-700"
        role="contentinfo"
        aria-label={t('footer.footerNavigation')}
      >
        <JsonLdLibrary />
        <div className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex flex-wrap items-start justify-between gap-4 sm:gap-6 mb-6">
            <FooterAddress />
            <FooterSocialLinks />
          </div>

          <nav aria-label={t('footer.footerNavigation')} className="mb-6 space-y-5">
            {[
              { title: t('libraryExperience.footerTasks', 'Use the library'), links: mainLinks },
              { title: t('libraryExperience.footerAbout', 'Your library'), links: [...aboutLinks, { to: '/donate', label: t('footer.donate') }] },
              { title: t('libraryExperience.footerPolicies', 'Policies and access'), links: legalLinks },
            ].map((group) => (
              <div key={group.title}>
                <h2 className="text-sm font-semibold text-earth-100 mb-1">{group.title}</h2>
                <ul className="flex flex-wrap gap-x-6 gap-y-1">
                  {group.links.map(({ to, label }) => (
                    <li key={to}>
                      <Link to={to} className="text-sm text-earth-300 hover:text-earth-100 transition-colors min-h-[44px] inline-flex items-center rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose">
                        {label}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </nav>

          {/* Inline display toggles for screen-reader users navigating by landmark.
               These write to the same UnifiedAccessibilityContext as the FAB widget. */}
          <div className="border-t border-earth-800 pt-5 pb-1 mb-1" aria-label={t('a11y.footerToggles.label', 'Quick display settings')}>
            <p className="text-xs text-earth-300 mb-3 font-medium uppercase tracking-wide">
              {t('a11y.footerToggles.label', 'Quick display settings')}
            </p>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => updateA11ySetting('dyslexiaFont', !a11ySettings.dyslexiaFont)}
                aria-pressed={a11ySettings.dyslexiaFont}
                className={[
                  'px-3 py-1.5 rounded-lg text-sm border transition-colors',
                  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-1 focus-visible:ring-offset-earth-950',
                  a11ySettings.dyslexiaFont
                    ? 'bg-lsc-rose/20 border-lsc-rose text-white'
                    : 'bg-transparent border-earth-700 text-earth-300 hover:border-earth-500',
                ].join(' ')}
              >
                {t('a11y.footerToggles.dyslexiaFont', 'Dyslexia font')}
              </button>
              <button
                type="button"
                onClick={() => updateA11ySetting('reduceMotion', !a11ySettings.reduceMotion)}
                aria-pressed={a11ySettings.reduceMotion}
                className={[
                  'px-3 py-1.5 rounded-lg text-sm border transition-colors',
                  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-1 focus-visible:ring-offset-earth-950',
                  a11ySettings.reduceMotion
                    ? 'bg-lsc-rose/20 border-lsc-rose text-white'
                    : 'bg-transparent border-earth-700 text-earth-300 hover:border-earth-500',
                ].join(' ')}
              >
                {t('a11y.footerToggles.reduceMotion', 'Reduce motion')}
              </button>
              <button
                type="button"
                onClick={() => updateA11ySetting('highContrast', !a11ySettings.highContrast)}
                aria-pressed={a11ySettings.highContrast}
                className={[
                  'px-3 py-1.5 rounded-lg text-sm border transition-colors',
                  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-1 focus-visible:ring-offset-earth-950',
                  a11ySettings.highContrast
                    ? 'bg-lsc-rose/20 border-lsc-rose text-white'
                    : 'bg-transparent border-earth-700 text-earth-300 hover:border-earth-500',
                ].join(' ')}
              >
                {t('a11y.footerToggles.highContrast', 'High contrast')}
              </button>
            </div>
          </div>
          <FooterNewsletterForm />

          <FooterDemoNotice />

          <div className="border-t border-earth-800 pt-6 flex flex-wrap items-center justify-between gap-2">
            <p className="text-xs text-earth-300 font-mono">{t('footer.copyright')}</p>
            <div className="dark flex items-center gap-3">
              <LanguageSwitcher />
              <FooterCarbonBadge />
            </div>
          </div>
        </div>
      </footer>

      <button
        onClick={scrollToTop}
        className={`fixed bottom-20 right-4 p-2.5 min-w-[44px] min-h-[44px] rounded-lg bg-lsc-white dark:bg-earth-950 text-lsc-dark dark:text-lsc-cream border border-lsc-border dark:border-earth-700 hover:border-lsc-rose dark:hover:border-lsc-rose-light shadow-md z-30 transition-all duration-200 ${
          showBackToTop ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4 pointer-events-none'
        }`}
        aria-label={t('footer.backToTop')}
      >
        <ChevronUp aria-hidden="true" className="w-4 h-4" />
      </button>
    </>
  )
}
