/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Shield, Lock, Eye, FileText, UserCheck, Database, Bell, HelpCircle, Cookie, BarChart3 } from 'lucide-react'
import { useBranding } from '@/contexts/BrandingContext'
import { useTranslation } from '@/i18n'

export default function PrivacyPage(): React.ReactElement {
  const branding = useBranding()
  const { t } = useTranslation()
  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="bg-gradient-to-r from-lsc-rose to-lsc-rose rounded-xl p-8 text-white">
        <div className="flex items-center gap-4 mb-4">
          <div className="w-16 h-16 bg-lsc-white dark:bg-earth-800/10 rounded-xl flex items-center justify-center">
            <Shield aria-hidden="true" className="w-8 h-8" color="#7C6545" />
          </div>
          <div>
            <h1 className="text-3xl font-serif font-bold">{t('privacyPage.pageTitle', 'Privacy Policy')}</h1>
            <p className="text-lsc-border">{t('privacyPage.lastUpdated', 'Last updated May 26, 2026')}</p>
          </div>
        </div>
        <p className="text-lg text-sage-100 max-w-3xl">
          {t('privacyPage.committedToProtecting', { libraryName: branding.library_name })}
        </p>
      </div>

      {/* Introduction */}
      <section className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
        <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
          {t('privacyPage.ourCommitmentToPrivacy', 'Our Commitment to Privacy')}
        </h2>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
          {t(
            'privacyPage.weBelieveThatPrivacy',
            'We believe that privacy is a fundamental right. This policy explains how we collect, use, and protect your personal information when you use our library services, website, and digital resources.',
          )}
        </p>
      </section>

      {/* Main Content Grid */}
      <div className="grid md:grid-cols-2 gap-6">
        {/* Information We Collect */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-lsc-cream dark:bg-lsc-brown rounded-xl flex items-center justify-center">
              <Database aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
            </div>
            <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
              {t('privacyPage.informationWeCollect', 'Information We Collect')}
            </h3>
          </div>
          <ul className="space-y-2 text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('privacyPage.collectRegistration', 'Name, address, and contact information for library card registration')}
            </li>
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t(
                'privacyPage.collectBorrowingHistory',
                'Borrowing history (you control this — opt in to keep your reading history, or leave it off and records are cleared after items are returned)',
              )}
            </li>
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('privacyPage.collectEventRegistrations', 'Event registrations and program participation')}
            </li>
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t(
                'privacyPage.collectUsageStats',
                'Computer and Wi-Fi usage statistics (anonymized means we track how often and when people use these services, but we do not track who uses them or what websites are visited)',
              )}
            </li>
          </ul>
        </div>

        {/* How We Use Information */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-lsc-cream dark:bg-lsc-brown rounded-xl flex items-center justify-center">
              <FileText aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
            </div>
            <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
              {t('privacyPage.howWeUseYourInformation', 'How We Use Your Information')}
            </h3>
          </div>
          <ul className="space-y-2 text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('privacyPage.useProvideServices', 'To provide library services and manage your account')}
            </li>
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('privacyPage.useSendNotifications', 'To send notifications about holds, due dates, and events')}
            </li>
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('privacyPage.useImproveServices', 'To improve our services and programs')}
            </li>
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('privacyPage.useComplyLegal', 'To comply with legal requirements')}
            </li>
          </ul>
        </div>

        {/* Data Protection */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-lsc-cream dark:bg-lsc-brown rounded-xl flex items-center justify-center">
              <Lock aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
            </div>
            <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
              {t('privacyPage.dataProtection', 'Data Protection')}
            </h3>
          </div>
          <ul className="space-y-2 text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t(
                'privacyPage.protectionEncryption',
                'Encrypted data transmission and storage (your information is scrambled when sent to our servers and locked in secure storage, so others cannot read it)',
              )}
            </li>
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('privacyPage.protectionSecurityAudits', 'Regular security audits and updates')}
            </li>
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('privacyPage.protectionStaffTraining', 'Staff training on privacy and confidentiality')}
            </li>
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t(
                'privacyPage.protectionLimitedAccess',
                'Limited access to personal information (only a small number of authorized staff members can view your personal details, and only when needed to help you)',
              )}
            </li>
          </ul>
        </div>

        {/* Your Rights */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-lsc-cream dark:bg-lsc-brown rounded-xl flex items-center justify-center">
              <UserCheck aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
            </div>
            <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
              {t('privacyPage.yourRights', 'Your Rights')}
            </h3>
          </div>
          <ul className="space-y-2 text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('privacyPage.rightAccessInfo', 'Access your personal information upon request')}
            </li>
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('privacyPage.rightRequestCorrections', 'Request corrections to inaccurate data')}
            </li>
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('privacyPage.rightOptOut', 'Opt out of non-essential communications')}
            </li>
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('privacyPage.rightRequestDeletion', 'Request deletion of your account')}
            </li>
          </ul>
        </div>
      </div>

      {/* Children's Privacy (COPPA) */}
      <section className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 bg-lsc-cream dark:bg-lsc-brown rounded-xl flex items-center justify-center">
            <UserCheck aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
          </div>
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
            {t('privacyPage.childrensPrivacy', "Children's Privacy")}
          </h3>
        </div>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
          {t(
            'privacyPage.weTakeExtraCare',
            "We take extra care with information about children under 13, in accordance with the Children's Online Privacy Protection Act (COPPA).",
          )}
        </p>
        <ul className="space-y-2 text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">
          <li className="flex items-start gap-2">
            <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
            {t('privacyPage.coppaConsent', 'A parent or guardian must provide consent before a child under 13 can create an account')}
          </li>
          <li className="flex items-start gap-2">
            <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
            {t('privacyPage.coppaParentsReview', "Parents can review, update, or request deletion of their child's information at any time")}
          </li>
          <li className="flex items-start gap-2">
            <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
            {t('privacyPage.coppaMinimumInfo', 'We collect only the minimum information needed to provide library services to children')}
          </li>
          <li className="flex items-start gap-2">
            <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
            {t(
              'privacyPage.coppaNoSharing',
              "Children's browsing and reading history is never shared or used for recommendations without parental consent",
            )}
          </li>
        </ul>
      </section>

      {/* FERPA — for K-12 and higher-ed deployments */}
      <section className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 bg-lsc-cream dark:bg-lsc-brown rounded-xl flex items-center justify-center">
            <UserCheck aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
          </div>
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
            {t('privacyPage.ferpaHeading', 'FERPA (School & Education Records)')}
          </h3>
        </div>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
          {t(
            'privacyPage.ferpaIntro',
            'When Librar is deployed at a K-12 school, district, or higher-education institution, patron records may be considered "education records" under the Family Educational Rights and Privacy Act (FERPA, 20 U.S.C. § 1232g). In that context:',
          )}
        </p>
        <ul className="space-y-2 text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">
          <li className="flex items-start gap-2">
            <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
            <span>
              {t('privacyPage.ferpaWeActAsAPrefix', 'We act as a ')}
              <strong>{t('privacyPage.ferpaSchoolOfficialStrong', 'school official with a legitimate educational interest')}</strong>
              {t('privacyPage.ferpaWhenProcessingSuffix', ' when processing student records on behalf of the operating institution.')}
            </span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
            {t(
              'privacyPage.ferpaStudentRecordsReleased',
              'Student records are released only to the institution, to the student or parent exercising FERPA rights, or under valid legal process (subpoena, court order, judicial warrant).',
            )}
          </li>
          <li className="flex items-start gap-2">
            <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
            {t(
              'privacyPage.ferpaNoAdvertising',
              'We do not use student data for advertising, marketing to students, or any purpose other than delivering library services.',
            )}
          </li>
          <li className="flex items-start gap-2">
            <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
            <span>
              {t('privacyPage.ferpaBorrowingHistoryPrefix', 'Borrowing history, reading recommendations, and search queries are ')}
              <strong>{t('privacyPage.ferpaNotUsedToTrainStrong', 'not used to train AI models')}</strong>
              {t('privacyPage.ferpaNeitherOursSuffix', " — neither ours nor any third party's.")}
            </span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
            <span>
              {t('privacyPage.ferpaDataSharingAgreementPrefix', 'A FERPA-compliant Data Sharing Agreement is available for K-12 and higher-ed customers on request — email ')}
              <a href={`mailto:${branding.privacy_email}`} aria-label="Contact privacy team by email" className="underline">{branding.privacy_email}</a>.
            </span>
          </li>
        </ul>
      </section>

      {/* AI chat assistant */}
      <section className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 bg-lsc-cream dark:bg-lsc-brown rounded-xl flex items-center justify-center">
            <HelpCircle aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
          </div>
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
            {t('privacyPage.ourChatAssistant', 'Our Chat Assistant')}
          </h3>
        </div>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
          {t(
            'privacyPage.chatAssistantIntro',
            'When you use the library’s chat assistant (for example, “Ask a Librarian”), here’s what happens to what you type:',
          )}
        </p>
        <ul className="space-y-2 text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">
          <li className="flex items-start gap-2">
            <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
            <span>
              {t('privacyPage.chatStaysOnServersPrefix', "What you type and the assistant's replies stay on the library's ")}
              <strong>{t('privacyPage.chatOwnServersStrong', 'own servers')}</strong>
              {t('privacyPage.chatOwnServersSuffix', '. They are not sent to OpenAI, Anthropic, Google, or any outside AI company.')}
            </span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
            {t(
              'privacyPage.chatKeepConversation',
              'We keep the conversation so a staff member can follow up if you ask, and so we can fix problems. If you leave an email for follow-up, it is stored with that conversation and used only to reply to you.',
            )}
          </li>
          <li className="flex items-start gap-2">
            <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
            <span>
              {t('privacyPage.chatQuestionsPrefix', 'Your questions are ')}
              <strong>{t('privacyPage.chatNeverTrainStrong', 'never used to train an AI model')}</strong>
              {t('privacyPage.chatNeverTrainSuffix', " — ours or anyone else's.")}
            </span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
            <span>
              {t('privacyPage.chatDeletePrefix', 'We delete chat conversations within ')}
              <strong>{t('privacyPage.chatNinetyDaysStrong', '90 days')}</strong>.
            </span>
          </li>
        </ul>
      </section>

      {/* Sub-Processors */}
      <section className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 bg-lsc-cream dark:bg-lsc-brown rounded-xl flex items-center justify-center">
            <Eye aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
          </div>
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
            {t('privacyPage.subProcessors', 'Sub-Processors')}
          </h3>
        </div>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
          {t('privacyPage.subProcessorsIntroPrefix', "To deliver Librar's services, we use a small set of trusted sub-processors. Each is listed below with its purpose, the data in scope, and where it operates. A Data Processing Addendum (DPA) is available on request — email ")}
          <a href={`mailto:${branding.privacy_email}`} aria-label="Contact privacy team by email" className="underline">{branding.privacy_email}</a>.
        </p>

        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-lsc-cream dark:border-lsc-brown text-left">
                <th className="py-2 pr-4 font-semibold text-lsc-dark dark:text-lsc-cream">{t('privacyPage.processorColumn', 'Processor')}</th>
                <th className="py-2 pr-4 font-semibold text-lsc-dark dark:text-lsc-cream">{t('privacyPage.purposeColumn', 'Purpose')}</th>
                <th className="py-2 pr-4 font-semibold text-lsc-dark dark:text-lsc-cream">{t('privacyPage.dataInScopeColumn', 'Data in scope')}</th>
                <th className="py-2 font-semibold text-lsc-dark dark:text-lsc-cream">{t('privacyPage.jurisdictionColumn', 'Jurisdiction')}</th>
              </tr>
            </thead>
            <tbody className="text-lsc-dark/80 dark:text-lsc-cream/80">
              <tr className="border-b border-lsc-cream/50 dark:border-lsc-brown/50">
                <td className="py-3 pr-4 font-semibold align-top">Cloudflare</td>
                <td className="py-3 pr-4 align-top">{t('privacyPage.cloudflarePurpose', 'DNS, CDN, WAF, bot verification (Turnstile)')}</td>
                <td className="py-3 pr-4 align-top">{t('privacyPage.cloudflareDataScope', 'IP addresses, HTTP request headers, TLS termination')}</td>
                <td className="py-3 align-top">{t('privacyPage.usGlobalEdge', 'US / global edge')}</td>
              </tr>
              <tr className="border-b border-lsc-cream/50 dark:border-lsc-brown/50">
                <td className="py-3 pr-4 font-semibold align-top">Resend</td>
                <td className="py-3 pr-4 align-top">{t('privacyPage.resendPurpose', 'Transactional email delivery (holds, due-date notices, account notifications)')}</td>
                <td className="py-3 pr-4 align-top">{t('privacyPage.resendDataScope', 'Recipient email address, notification message body')}</td>
                <td className="py-3 align-top">{t('privacyPage.usSanFrancisco', 'US (San Francisco)')}</td>
              </tr>
              <tr className="border-b border-lsc-cream/50 dark:border-lsc-brown/50">
                <td className="py-3 pr-4 font-semibold align-top">PrivateEmail (Namecheap)</td>
                <td className="py-3 pr-4 align-top">{t('privacyPage.privateEmailPurpose', 'Staff inbox hosting (info@, security@, privacy@, accessibility@)')}</td>
                <td className="py-3 pr-4 align-top">{t('privacyPage.privateEmailDataScope', 'Contents of staff email correspondence')}</td>
                <td className="py-3 align-top">{t('privacyPage.usPhoenix', 'US (Phoenix, AZ)')}</td>
              </tr>
              <tr className="border-b border-lsc-cream/50 dark:border-lsc-brown/50">
                <td className="py-3 pr-4 font-semibold align-top">Sentry <span className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60">({t('privacyPage.conditionalLabel', 'conditional')})</span></td>
                <td className="py-3 pr-4 align-top">{t('privacyPage.sentryPurpose', 'Error monitoring (frontend + backend)')}</td>
                <td className="py-3 pr-4 align-top">{t('privacyPage.sentryDataScope', 'Stack traces, request paths; no patron PII in scrubbed payload')}</td>
                <td className="py-3 align-top">{t('privacyPage.usSanFrancisco', 'US (San Francisco)')}</td>
              </tr>
              <tr className="border-b border-lsc-cream/50 dark:border-lsc-brown/50">
                <td className="py-3 pr-4 font-semibold align-top">OpenAI <span className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60">({t('privacyPage.conditionalLabel', 'conditional')})</span></td>
                <td className="py-3 pr-4 align-top">{t('privacyPage.openaiPurpose', 'Embeddings API for catalog semantic search — catalog text only, never patron data')}</td>
                <td className="py-3 pr-4 align-top">{t('privacyPage.openaiDataScope', 'Catalog item titles, descriptions, subject headings')}</td>
                <td className="py-3 align-top">{t('privacyPage.usOnly', 'US')}</td>
              </tr>
              <tr className="border-b border-lsc-cream/50 dark:border-lsc-brown/50">
                <td className="py-3 pr-4 font-semibold align-top">Stripe <span className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60">({t('privacyPage.conditionalLabel', 'conditional')})</span></td>
                <td className="py-3 pr-4 align-top">{t('privacyPage.stripePurpose', 'Payment processing — card data handled by Stripe via PCI-compliant iframe; L30 never sees card numbers')}</td>
                <td className="py-3 pr-4 align-top">{t('privacyPage.stripeDataScope', 'Email, transaction metadata')}</td>
                <td className="py-3 align-top">{t('privacyPage.usSanFrancisco', 'US (San Francisco)')}</td>
              </tr>
              <tr>
                <td className="py-3 pr-4 font-semibold align-top">GitHub Container Registry</td>
                <td className="py-3 pr-4 align-top">{t('privacyPage.githubPurpose', 'Build-time container image storage (no patron data ever)')}</td>
                <td className="py-3 pr-4 align-top">{t('privacyPage.githubDataScope', 'None (container images only)')}</td>
                <td className="py-3 align-top">{t('privacyPage.usOnly', 'US')}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-4">
          <strong>({t('privacyPage.conditionalLabel', 'conditional')})</strong>{' '}
          {t(
            'privacyPage.conditionalMeansSuffix',
            'means the sub-processor is used only when the corresponding feature is enabled in your deployment. Self-hosted customers control which are active.',
          )}
        </p>

        <h4 className="font-serif text-base font-semibold text-lsc-dark dark:text-lsc-cream mt-6 mb-2">{t('privacyPage.dataResidencyHeading', 'Data residency & cross-border transfers')}</h4>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          {t(
            'privacyPage.dataResidencyText',
            'Primary patron data is stored on self-hosted infrastructure. Cloudflare edge nodes terminate TLS globally; no patron-identifying data is cached at edge. US-based sub-processors handle data under the EU-US Data Privacy Framework or Standard Contractual Clauses where applicable.',
          )}
        </p>

        <h4 className="font-serif text-base font-semibold text-lsc-dark dark:text-lsc-cream mt-6 mb-2">{t('privacyPage.retentionHeading', 'Retention')}</h4>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          {t(
            'privacyPage.retentionText',
            'Borrowing history retention is patron-controlled (opt-in). Request/IP metadata is retained for 30 days for security investigation, then purged. Backup snapshots roll off within 90 days. On account deletion, personally-identifying records are removed from the primary database within 7 days; remaining backup snapshots roll off within the standard backup window.',
          )}
        </p>

        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-4">
          {t(
            'privacyPage.chatRetentionText',
            'Chat assistant conversations are deleted within 90 days. For staff-only AI tools, the text you type is removed after 30 days and the log is deleted within 90.',
          )}
        </p>

        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-4">
          {t(
            'privacyPage.changesNoticeText',
            'Changes to this sub-processor list are communicated at least 30 days in advance to operating institutions via email and a dated changelog at this URL.',
          )}
        </p>
      </section>

      {/* Confidentiality of Library Records — Ohio Revised Code 149.432 */}
      <section
        id="records-confidentiality"
        className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm"
        aria-labelledby="records-confidentiality-heading"
      >
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 bg-lsc-cream dark:bg-lsc-brown rounded-xl flex items-center justify-center">
            <FileText aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
          </div>
          <h3 id="records-confidentiality-heading" className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
            {t('privacyPage.recordsConfidentialityHeading', 'Confidentiality of Library Records (Ohio Revised Code § 149.432)')}
          </h3>
        </div>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
          {t(
            'privacyPage.ohioLawIntro',
            'Ohio law protects the privacy of library users. Under Ohio Revised Code § 149.432, any library record that identifies you as having requested, used, or borrowed library materials or services is confidential. We will not disclose it except:',
          )}
        </p>
        <ul className="space-y-2 text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">
          <li className="flex items-start gap-2">
            <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
            {t('privacyPage.disclosureToYou', 'To you, or to a person you authorize in writing')}
          </li>
          <li className="flex items-start gap-2">
            <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
            {t('privacyPage.disclosureToStaff', 'To library staff acting within the scope of their duties to operate the library')}
          </li>
          <li className="flex items-start gap-2">
            <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
            {t('privacyPage.disclosureLegalProcess', 'In response to a valid court order, subpoena, or other legal process, as required by law')}
          </li>
          <li className="flex items-start gap-2">
            <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
            {t('privacyPage.disclosureOtherwisePermitted', 'As otherwise required or permitted by Ohio Revised Code § 149.432')}
          </li>
        </ul>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-3">
          {t(
            'privacyPage.confidentialityCoverage',
            'This protection covers your borrowing history, holds, search and browsing activity, computer and Wi-Fi use, program registrations, and any personally identifying information in your library account.',
          )}
        </p>
      </section>

      {/* Law Enforcement & Government Requests */}
      <section className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 bg-lsc-cream dark:bg-lsc-brown rounded-xl flex items-center justify-center">
            <Shield aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
          </div>
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
            {t('privacyPage.lawEnforcementHeading', 'Law Enforcement & Government Requests')}
          </h3>
        </div>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
          {t(
            'privacyPage.alaGuidelinesIntro',
            "We follow the American Library Association's guidelines on patron confidentiality. Your reading records and library usage are private.",
          )}
        </p>
        <ul className="space-y-2 text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">
          <li className="flex items-start gap-2">
            <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
            {t('privacyPage.leNoVoluntarySharing', 'We do not voluntarily share patron records with law enforcement or government agencies')}
          </li>
          <li className="flex items-start gap-2">
            <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
            {t('privacyPage.leRequireCourtOrder', 'We require a valid court order, subpoena, or warrant before releasing any patron information')}
          </li>
          <li className="flex items-start gap-2">
            <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
            {t('privacyPage.leRequestsReviewed', 'All law enforcement requests are reviewed by library administration and logged')}
          </li>
          <li className="flex items-start gap-2">
            <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
            {t('privacyPage.leNotifyPatrons', 'We will notify affected patrons of requests for their records unless legally prohibited from doing so')}
          </li>
        </ul>
      </section>

      {/* Cookies & Analytics */}
      <div className="grid md:grid-cols-2 gap-6">
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-lsc-cream dark:bg-lsc-brown rounded-xl flex items-center justify-center">
              <Cookie aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
            </div>
            <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
              {t('privacyPage.cookiesHeading', 'Cookies')}
            </h3>
          </div>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm mb-3">
            {t('privacyPage.cookiesEssentialOnly', 'We use only essential cookies required for the site to function. We do not use advertising, tracking, or third-party cookies.')}
          </p>
          <ul className="space-y-2 text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              <span>
                <strong className="text-lsc-dark dark:text-lsc-cream">{t('privacyPage.cookieAuthStrong', 'Authentication cookie')}</strong>
                {t('privacyPage.cookieAuthSuffix', ' — keeps you logged in between visits. This is a secure, encrypted cookie that cannot be read by other websites. It is deleted when you log out.')}
              </span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              <span>
                <strong className="text-lsc-dark dark:text-lsc-cream">{t('privacyPage.cookieLocalPrefsStrong', 'Local preferences')}</strong>
                {t('privacyPage.cookieLocalPrefsSuffix', ' — your accessibility settings, theme choice, and reading preferences are stored in your browser (not on our servers) and never shared.')}
              </span>
            </li>
          </ul>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm mt-3">
            {t('privacyPage.noConsentBannerNeeded', 'No consent banner is needed because we only use strictly necessary cookies.')}
          </p>
        </div>

        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-lsc-cream dark:bg-lsc-brown rounded-xl flex items-center justify-center">
              <BarChart3 aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
            </div>
            <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
              {t('privacyPage.analyticsHeading', 'Analytics')}
            </h3>
          </div>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm mb-3">
            {t('privacyPage.analyticsUmamiIntro', 'We use Umami, a privacy-respecting analytics tool, to understand how people use our website. This helps us improve our services.')}
          </p>
          <ul className="space-y-2 text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('privacyPage.analyticsNoCookies', 'No cookies are set by our analytics')}
            </li>
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('privacyPage.analyticsNoPersonalInfo', 'No personal information is collected')}
            </li>
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('privacyPage.analyticsCannotIdentify', 'We cannot identify individual visitors')}
            </li>
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('privacyPage.analyticsSelfHosted', 'All data is self-hosted on our own servers — never shared with third parties')}
            </li>
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('privacyPage.analyticsAggregateOnly', 'We only see aggregate information like which pages are most visited and what devices people use')}
            </li>
          </ul>
        </div>
      </div>

      {/* Contact Section */}
      <section className="bg-lsc-cream dark:bg-lsc-brown/20 rounded-xl p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 bg-lsc-cream dark:bg-earth-800 rounded-xl flex items-center justify-center">
            <HelpCircle aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
          </div>
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
            {t('privacyPage.questionsOrConcerns', 'Questions or Concerns?')}
          </h3>
        </div>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
          {t('privacyPage.questionsIntro', 'If you have questions about this privacy policy or how we handle your information, please contact us:')}
        </p>
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex items-center gap-2 text-lsc-dark dark:text-lsc-cream/80">
            <Bell aria-hidden="true" className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light" />
            <span>{branding.privacy_email}</span>
          </div>
        </div>
      </section>
    </div>
  )
}
