/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Link } from 'react-router-dom'
import {
  AlertCircle,
  CheckCircle,
  ExternalLink,
  Globe,
  Scale,
  Shield,
  Trash2,
  Users,
} from 'lucide-react'
import { useTranslation } from '@/i18n'
import {
  DATA_BROKER_OPT_OUTS,
  GOOGLE_REMOVAL_RESOURCES,
  OTHER_REMOVAL_RESOURCES,
  REMOVAL_STEPS,
} from '../data/privacyResources'

export default function PrivacyTab(): React.ReactElement {
  const { t } = useTranslation()

  return (
    <div className="space-y-8">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
        <div className="flex items-start gap-4">
          <div className="p-3 bg-lsc-cream dark:bg-lsc-brown/30 rounded-xl">
            <Globe aria-hidden="true" className="w-6 h-6 text-lsc-rose" />
          </div>
          <div>
            <h3 className="font-serif font-semibold text-lg text-lsc-dark dark:text-earth-50 mb-2">
              {t('components.legal.privacyTab.removingYourInformationFrom', 'Removing Your Information from Google Search')}
            </h3>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
              {t(
                'components.legal.privacyTab.concernedAboutPersonalInformation',
                'Concerned about personal information appearing in search results? You have options. Google provides tools to request removal of certain types of personal information, and there are steps you can take to reduce your online footprint.',
              )}
            </p>
          </div>
        </div>
      </div>

      <div>
        <div className="flex items-center gap-2 mb-4">
          <CheckCircle aria-hidden="true" className="w-5 h-5 text-lsc-rose" />
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-earth-50">
            {t('components.legal.privacyTab.stepByStepRemovalGuide', 'Step-by-Step Removal Guide')}
          </h3>
        </div>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {REMOVAL_STEPS.map((item) => (
            <div
              key={item.step}
              className="bg-lsc-white dark:bg-earth-800 rounded-xl p-5 border border-lsc-border dark:border-earth-700"
            >
              <div className="flex items-center gap-3 mb-3">
                <span className="w-8 h-8 bg-lsc-rose text-white rounded-full flex items-center justify-center font-semibold text-sm">
                  {item.step}
                </span>
                <h4 className="font-medium text-lsc-dark dark:text-earth-50">{t(item.titleKey, item.title)}</h4>
              </div>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t(item.descriptionKey, item.description)}</p>
            </div>
          ))}
        </div>
      </div>

      <div>
        <div className="flex items-center gap-2 mb-4">
          <Shield aria-hidden="true" className="w-5 h-5 text-lsc-rose" />
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-earth-50">
            {t('components.legal.privacyTab.googleSOfficialRemoval', "Google's Official Removal Tools")}
          </h3>
        </div>
        <div className="grid md:grid-cols-2 gap-4">
          {GOOGLE_REMOVAL_RESOURCES.map((resource) => (
            <div
              key={resource.name}
              className="bg-lsc-white dark:bg-earth-800 rounded-xl p-5 border border-lsc-border dark:border-earth-700"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <h4 className="font-medium text-lsc-dark dark:text-earth-50">{resource.name}</h4>
                    <span className="px-2 py-0.5 bg-earth-100 dark:bg-earth-800/30 text-lsc-rose dark:text-lsc-rose-light rounded text-xs font-medium">
                      {t('components.legal.privacyTab.official', 'Official')}
                    </span>
                  </div>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">{t(resource.descriptionKey, resource.description)}</p>
                  <a
                    href={resource.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    aria-label={`${t('components.legal.privacyTab.visit', 'Visit')} ${resource.name} (${t('aria.legalResources.opensInNewTab', 'opens in a new tab')})`}
                    className="inline-flex items-center gap-1 min-h-[44px] text-sm text-lsc-rose hover:text-lsc-rose/80 font-medium"
                  >
                    {t('components.legal.privacyTab.visitResource', 'Visit Resource')}
                    <ExternalLink aria-hidden="true" className="w-3 h-3" />
                  </a>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div>
        <div className="flex items-center gap-2 mb-4">
          <Trash2 aria-hidden="true" className="w-5 h-5 text-lsc-rose" />
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-earth-50">
            {t('components.legal.privacyTab.dataBrokerOptOutLinks', 'Data Broker Opt-Out Links')}
          </h3>
        </div>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
          {t(
            'components.legal.privacyTab.peopleSearchWebsitesCollect',
            'People-search websites collect and display personal information. You can request removal from these sites directly.',
          )}
        </p>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {DATA_BROKER_OPT_OUTS.map((resource) => (
            <a
              key={resource.name}
              href={resource.url}
              target="_blank"
              rel="noopener noreferrer"
              aria-label={`${t('components.legal.privacyTab.optOutFrom', 'Opt out from')} ${resource.name} (${t('aria.legalResources.opensInNewTab', 'opens in a new tab')})`}
              className="block bg-lsc-white dark:bg-earth-800 rounded-xl p-4 min-h-[44px] border border-lsc-border dark:border-earth-700 hover:border-lsc-rose dark:hover:border-lsc-rose transition-colors group"
            >
              <h4 className="font-medium text-lsc-dark dark:text-earth-50 mb-1 group-hover:text-lsc-rose transition-colors">
                {resource.name}
              </h4>
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{t(resource.descriptionKey, resource.description)}</p>
              <span className="inline-flex items-center gap-1 text-xs text-lsc-rose mt-2">
                {t('components.legal.privacyTab.optOut', 'Opt Out')} <ExternalLink aria-hidden="true" className="w-3 h-3" />
              </span>
            </a>
          ))}
        </div>
      </div>

      <div>
        <div className="flex items-center gap-2 mb-4">
          <Scale aria-hidden="true" className="w-5 h-5 text-lsc-rose" />
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-earth-50">
            {t('components.legal.privacyTab.privacyRightsAdditionalResources', 'Privacy Rights & Additional Resources')}
          </h3>
        </div>
        <div className="grid md:grid-cols-2 gap-4">
          {OTHER_REMOVAL_RESOURCES.map((resource) => (
            <div
              key={resource.name}
              className="bg-lsc-white dark:bg-earth-800 rounded-xl p-5 border border-lsc-border dark:border-earth-700"
            >
              <div className="flex items-start gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <h4 className="font-medium text-lsc-dark dark:text-earth-50">{resource.name}</h4>
                    <span
                      className={`px-2 py-0.5 rounded text-xs font-medium ${
                        resource.type === 'official'
                          ? 'bg-earth-100 dark:bg-earth-800/30 text-lsc-rose dark:text-lsc-rose-light'
                          : 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300'
                      }`}
                    >
                      {resource.type === 'official'
                        ? t('components.legal.privacyTab.official', 'Official')
                        : t('components.legal.privacyTab.tool', 'Tool')}
                    </span>
                  </div>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">{t(resource.descriptionKey, resource.description)}</p>
                  <a
                    href={resource.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    aria-label={`${t('components.legal.privacyTab.visit', 'Visit')} ${resource.name} (${t('aria.legalResources.opensInNewTab', 'opens in a new tab')})`}
                    className="inline-flex items-center gap-1 min-h-[44px] text-sm text-lsc-rose hover:text-lsc-rose/80 font-medium"
                  >
                    {t('components.legal.privacyTab.visitResource', 'Visit Resource')}
                    <ExternalLink aria-hidden="true" className="w-3 h-3" />
                  </a>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 rounded-xl p-6">
        <div className="flex items-start gap-4">
          <AlertCircle aria-hidden="true" className="w-6 h-6 text-status-warning-600 dark:text-status-warning-400 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-serif font-semibold text-status-warning-800 dark:text-status-warning-200 mb-2">
              {t('components.legal.privacyTab.importantInformation', 'Important Information')}
            </h3>
            <ul className="text-sm text-status-warning-700 dark:text-status-warning-300 space-y-2">
              <li>
                <strong>{t('legalResources.removalIsNotGuaranteed')}</strong>{' '}
                {t(
                  'components.legal.privacyTab.googleReviewsRequestsAnd',
                  "Google reviews requests and may decline if the content doesn't meet their criteria.",
                )}
              </li>
              <li>
                <strong>{t('legalResources.removalFromGoogleDoesnT')}</strong>{' '}
                {t('components.legal.privacyTab.contentMustBeRemoved', 'Content must be removed from the original website to be fully deleted.')}
              </li>
              <li>
                <strong>{t('legalResources.dataBrokerOptOutsMay')}</strong>{' '}
                {t('components.legal.privacyTab.someSitesReAdd', 'Some sites re-add information from public records over time.')}
              </li>
              <li>
                <strong>{t('components.legal.privacyTab.considerYourSafety', 'Consider your safety.')}</strong>{' '}
                {t(
                  'components.legal.privacyTab.ifYoureInDanger',
                  "If you're in danger, contact local authorities. Domestic violence organizations can help with privacy planning.",
                )}
              </li>
            </ul>
          </div>
        </div>
      </div>

      <div className="bg-lsc-cream dark:bg-lsc-brown/20 rounded-xl p-6">
        <div className="flex items-start gap-4">
          <Users aria-hidden="true" className="w-6 h-6 text-lsc-rose flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-serif font-semibold text-lsc-dark dark:text-earth-50 mb-2">
              {t('legalResources.needHelpVisitTheLibrary')}
            </h3>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
              {t('legalResources.needHelpNavigatingRemoval', "Need help navigating the legal resource removal process? Contact us and we'll do our best to guide you through it.")}
            </p>
            <Link
              to="/contact"
              aria-label={t('legalResources.contactUsAria', 'Contact the library for help with legal resources')}
              className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2"
            >
              {t('legalResources.contactUs', 'Contact us')}
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
