/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Link } from 'react-router-dom'
import {
  FileText,
  CreditCard,
  BookOpen,
  BookHeadphones,
  Monitor,
  Users,
  UserX,
  Scale,
  AlertTriangle,
  Shield,
  RefreshCw,
  HelpCircle,
  Mail,
  Flag,
  Trash2,
  PenTool,
} from 'lucide-react'
import { useBranding } from '@/contexts/BrandingContext'
import { useTranslation } from '@/i18n'

export default function TermsOfServicePage(): React.ReactElement {
  const branding = useBranding()
  const { t } = useTranslation()
  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="bg-gradient-to-r from-lsc-rose to-lsc-rose rounded-xl p-8 text-white">
        <div className="flex items-center gap-4 mb-4">
          <div className="w-16 h-16 bg-lsc-white dark:bg-earth-800/10 rounded-xl flex items-center justify-center">
            <FileText aria-hidden="true" className="w-8 h-8" color="#7C6545" />
          </div>
          <div>
            <h1 className="text-3xl font-serif font-bold">{t('termsPage.pageTitle', 'Terms of Service')}</h1>
            <p className="text-lsc-border">{t('termsPage.lastUpdated', 'Last updated: March 17, 2026')}</p>
          </div>
        </div>
        <p className="text-lg text-sage-100 max-w-3xl">
          {t('termsPage.headerIntro', { libraryName: branding.library_name })}
        </p>
      </div>

      {/* Introduction */}
      <section className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
        <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
          {t('termsPage.agreementToTerms', 'Agreement to Terms')}
        </h2>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
          {t('termsPage.agreementText1', { libraryName: branding.library_name })}
        </p>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
          {t('termsPage.agreementText2', 'If you do not agree with any part of these terms, please contact us to discuss your concerns or refrain from using our services.')}
        </p>
      </section>

      {/* Main Content Grid */}
      <div className="grid md:grid-cols-2 gap-6">
        {/* Library Card Usage */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-lsc-cream dark:bg-lsc-brown rounded-xl flex items-center justify-center">
              <CreditCard aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
            </div>
            <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
              {t('termsPage.libraryCardUsage', 'Library Card Usage')}
            </h3>
          </div>
          <ul className="space-y-2 text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('termsPage.card1', 'Library cards are free and open to all community members')}
            </li>
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('termsPage.card2', 'Your library card is for your personal use only and may not be shared with others')}
            </li>
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('termsPage.card3', 'You are responsible for all materials checked out using your card')}
            </li>
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('termsPage.card4', 'Report lost or stolen cards immediately to prevent unauthorized use')}
            </li>
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('termsPage.card5', 'Keep your contact information current to receive important notifications')}
            </li>
          </ul>
        </div>

        {/* Borrowing Policies */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-lsc-cream dark:bg-lsc-brown rounded-xl flex items-center justify-center">
              <BookOpen aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
            </div>
            <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
              {t('termsPage.borrowingPolicies', 'Borrowing Policies')}
            </h3>
          </div>
          <ul className="space-y-2 text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('termsPage.borrow1', 'Standard loan period is 21 days for books and 7 days for high-demand items')}
            </li>
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('termsPage.borrow2', 'Items may be renewed up to 3 times if no holds are pending')}
            </li>
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('termsPage.borrow3', 'Overdue fines are $0.25 per day with a maximum of $5.00 per item')}
            </li>
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('termsPage.borrow4', 'You are responsible for replacement costs for lost or damaged materials')}
            </li>
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('termsPage.borrow5', 'Accounts with fines over $10.00 will have borrowing privileges suspended until resolved')}
            </li>
          </ul>
        </div>

        {/* Digital Resources and eBooks */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-lsc-cream dark:bg-lsc-brown rounded-xl flex items-center justify-center">
              <BookHeadphones aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
            </div>
            <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
              {t('termsPage.digitalResourcesEbooks', 'Digital Resources and eBooks')}
            </h3>
          </div>
          <ul className="space-y-2 text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('termsPage.digital1', 'eBooks and audiobooks are available for borrowing with a valid library card')}
            </li>
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('termsPage.digital2', 'Digital loans have set borrowing periods; items are automatically returned when the loan expires')}
            </li>
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('termsPage.digital3', 'Downloaded files are for personal use only and may not be redistributed or shared')}
            </li>
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('termsPage.digital4', 'Open access titles from Standard Ebooks and similar sources are governed by their respective open licenses')}
            </li>
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('termsPage.digital5', 'Circumventing digital rights management (DRM) or copy protections is prohibited')}
            </li>
          </ul>
        </div>

        {/* Computer and Internet Usage */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-lsc-cream dark:bg-lsc-brown rounded-xl flex items-center justify-center">
              <Monitor aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
            </div>
            <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
              {t('termsPage.computerInternetUsage', 'Computer and Internet Usage')}
            </h3>
          </div>
          <ul className="space-y-2 text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('termsPage.computer1', 'Public computers are available on a first-come, first-served basis with a valid library card')}
            </li>
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('termsPage.computer2', 'Session time limits apply during busy periods (typically 60 minutes)')}
            </li>
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('termsPage.computer3', "Internet access is filtered in accordance with the Children's Internet Protection Act (CIPA)")}
            </li>
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('termsPage.computer4', 'Illegal activities, harassment, or accessing inappropriate content is prohibited')}
            </li>
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('termsPage.computer5', 'The library is not responsible for damage to personal devices connected to our network')}
            </li>
          </ul>
        </div>

        {/* User Conduct */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-lsc-cream dark:bg-lsc-brown rounded-xl flex items-center justify-center">
              <Users aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
            </div>
            <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
              {t('termsPage.userConductExpectations', 'User Conduct Expectations')}
            </h3>
          </div>
          <ul className="space-y-2 text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('termsPage.conduct1', 'Treat all staff, volunteers, and fellow patrons with respect and courtesy')}
            </li>
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('termsPage.conduct2', 'Maintain a quiet and respectful atmosphere in designated quiet areas')}
            </li>
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('termsPage.conduct3', 'Children under 10 must be accompanied by a responsible adult or guardian')}
            </li>
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('termsPage.conduct4', 'Handle library materials and property with care')}
            </li>
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('termsPage.conduct5', 'Food and covered beverages are permitted; please clean up after yourself')}
            </li>
          </ul>
        </div>

        {/* Indie Author Content */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-lsc-cream dark:bg-lsc-brown rounded-xl flex items-center justify-center">
              <PenTool aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
            </div>
            <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
              {t('termsPage.indieAuthorPlatform', 'Indie Author Platform')}
            </h3>
          </div>
          <ul className="space-y-2 text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('termsPage.indie1', 'Authors retain full copyright of all submitted works')}
            </li>
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('termsPage.indie2', 'By submitting content, authors grant the library a non-exclusive license to distribute it through our lending platform')}
            </li>
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('termsPage.indie3', 'All submissions must be original work; plagiarized or infringing content will be removed')}
            </li>
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('termsPage.indie4', 'Content must comply with our content rating and community guidelines')}
            </li>
            <li className="flex items-start gap-2">
              <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
              {t('termsPage.indie5', 'Authors may request removal of their works at any time by contacting library staff')}
            </li>
          </ul>
        </div>
      </div>

      {/* Account Termination */}
      <section className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 bg-lsc-cream dark:bg-lsc-brown rounded-xl flex items-center justify-center">
            <UserX aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
          </div>
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
            {t('termsPage.accountTermination', 'Account Termination')}
          </h3>
        </div>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
          {t('termsPage.terminationIntro', 'The library reserves the right to suspend or terminate library privileges for the following reasons:')}
        </p>
        <ul className="space-y-2 text-lsc-dark/70 dark:text-lsc-cream/70 text-sm mb-4">
          <li className="flex items-start gap-2">
            <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
            {t('termsPage.termination1', 'Repeated violation of library policies or these Terms of Service')}
          </li>
          <li className="flex items-start gap-2">
            <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
            {t('termsPage.termination2', 'Harassment, threats, or disruptive behavior toward staff or other patrons')}
          </li>
          <li className="flex items-start gap-2">
            <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
            {t('termsPage.termination3', 'Theft, vandalism, or intentional damage to library property')}
          </li>
          <li className="flex items-start gap-2">
            <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
            {t('termsPage.termination4', 'Failure to pay outstanding fines or fees exceeding $25.00 for more than 90 days')}
          </li>
          <li className="flex items-start gap-2">
            <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
            {t('termsPage.termination5', 'Fraudulent use of library cards or services')}
          </li>
        </ul>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
          {t('termsPage.terminationAppeal', 'Patrons may appeal suspension decisions by submitting a written request to the Library Director within 30 days.')}
        </p>
      </section>

      {/* DMCA and Copyright */}
      <section className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 bg-lsc-cream dark:bg-lsc-brown rounded-xl flex items-center justify-center">
            <Flag aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
          </div>
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
            {t('termsPage.dmcaHeading', 'DMCA and Copyright Notices')}
          </h3>
        </div>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
          {t('termsPage.dmcaIntro', { libraryName: branding.library_name })}
        </p>
        <ul className="space-y-2 text-lsc-dark/70 dark:text-lsc-cream/70 text-sm mb-4">
          <li className="flex items-start gap-2">
            <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
            {t('termsPage.dmcaAgentContact', 'Our designated DMCA agent can be reached at ')}{branding.contact_email}
          </li>
          <li className="flex items-start gap-2">
            <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
            {t('termsPage.dmcaRespondPromptly', 'We will respond to valid notices promptly and remove infringing content as required by law')}
          </li>
          <li className="flex items-start gap-2">
            <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
            {t('termsPage.dmcaRepeatInfringers', 'Repeat infringers will have their accounts terminated')}
          </li>
        </ul>
      </section>

      {/* Intellectual Property */}
      <section className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 bg-lsc-cream dark:bg-lsc-brown rounded-xl flex items-center justify-center">
            <Scale aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
          </div>
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
            {t('termsPage.intellectualProperty', 'Intellectual Property')}
          </h3>
        </div>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
          {t('termsPage.ipIntro', "The library's website content, logos, and original materials are protected by copyright and trademark laws. You may:")}
        </p>
        <ul className="space-y-2 text-lsc-dark/70 dark:text-lsc-cream/70 text-sm mb-4">
          <li className="flex items-start gap-2">
            <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
            {t('termsPage.ip1', 'Use materials for personal, non-commercial purposes')}
          </li>
          <li className="flex items-start gap-2">
            <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
            {t('termsPage.ip2', 'Share links to our website and resources')}
          </li>
          <li className="flex items-start gap-2">
            <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
            {t('termsPage.ip3', 'Print or download materials for educational use with proper attribution')}
          </li>
        </ul>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
          {t('termsPage.ipRestriction', 'You may not reproduce, distribute, or create derivative works from our content without written permission. Digital resources accessed through the library are subject to their respective licensing agreements.')}
        </p>
      </section>

      {/* Limitation of Liability */}
      <section className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 bg-lsc-cream dark:bg-lsc-brown rounded-xl flex items-center justify-center">
            <AlertTriangle aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
          </div>
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
            {t('termsPage.limitationOfLiability', 'Limitation of Liability')}
          </h3>
        </div>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
          {t('termsPage.liabilityIntro', { libraryName: branding.library_name })}
        </p>
        <ul className="space-y-2 text-lsc-dark/70 dark:text-lsc-cream/70 text-sm mb-4">
          <li className="flex items-start gap-2">
            <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
            {t('termsPage.liability1', 'Uninterrupted access to digital resources or website availability')}
          </li>
          <li className="flex items-start gap-2">
            <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
            {t('termsPage.liability2', 'The accuracy, completeness, or currency of information in our collection')}
          </li>
          <li className="flex items-start gap-2">
            <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
            {t('termsPage.liability3', 'Security of personal property left unattended on library premises')}
          </li>
          <li className="flex items-start gap-2">
            <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
            {t('termsPage.liability4', 'Content accessed through external links or third-party databases')}
          </li>
        </ul>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
          {t('termsPage.liabilityLimit', 'The library shall not be liable for any indirect, incidental, or consequential damages arising from your use of our services. Our total liability is limited to the amount of any fees you have paid to the library.')}
        </p>
      </section>

      {/* Privacy and Data */}
      <section className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 bg-lsc-cream dark:bg-lsc-brown rounded-xl flex items-center justify-center">
            <Shield aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
          </div>
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
            {t('termsPage.privacyAndYourData', 'Privacy and Your Data')}
          </h3>
        </div>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
          {t('termsPage.privacyIntroPrefix', 'Your privacy is important to us. We collect and use your personal information in accordance with our')}{' '}
          <Link
            to="/privacy"
            className="text-lsc-rose dark:text-lsc-rose-light underline decoration-2 underline-offset-2 hover:decoration-lsc-rose/50"
          >
            {t('termsPage.privacyPolicyLinkText', 'Privacy Policy')}
          </Link>
          {t('termsPage.privacyIntroSuffix', ', which explains how we protect your data, what information we collect, and how we use it.')}
        </p>
        <ul className="space-y-2 text-lsc-dark/70 dark:text-lsc-cream/70 text-sm mb-4">
          <li className="flex items-start gap-2">
            <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
            {t('termsPage.privacy1', 'Personal information is encrypted at rest and protected by industry-standard security measures')}
          </li>
          <li className="flex items-start gap-2">
            <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
            {t('termsPage.privacy2', 'Borrowing history and reading activity are private and will not be disclosed except as required by law')}
          </li>
          <li className="flex items-start gap-2">
            <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
            {t('termsPage.privacy3', 'We do not sell or share your data with third parties for marketing purposes')}
          </li>
        </ul>
      </section>

      {/* Data Retention and Deletion */}
      <section className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 bg-lsc-cream dark:bg-lsc-brown rounded-xl flex items-center justify-center">
            <Trash2 aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
          </div>
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
            {t('termsPage.dataRetentionAccountDeletion', 'Data Retention and Account Deletion')}
          </h3>
        </div>
        <ul className="space-y-2 text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">
          <li className="flex items-start gap-2">
            <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
            {t('termsPage.retention1', 'You may request a full export of your personal data at any time through your account settings')}
          </li>
          <li className="flex items-start gap-2">
            <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
            {t('termsPage.retention2', 'You may request deletion of your account and associated personal data by contacting library staff')}
          </li>
          <li className="flex items-start gap-2">
            <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
            {t('termsPage.retention3', 'Account deletion is permanent and cannot be reversed; outstanding fines must be resolved first')}
          </li>
          <li className="flex items-start gap-2">
            <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
            {t('termsPage.retention4', 'Certain records may be retained as required by law or for legitimate library operational needs')}
          </li>
        </ul>
      </section>

      {/* Changes to Terms */}
      <section className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 bg-lsc-cream dark:bg-lsc-brown rounded-xl flex items-center justify-center">
            <RefreshCw aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
          </div>
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
            {t('termsPage.changesToTerms', 'Changes to Terms')}
          </h3>
        </div>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
          {t('termsPage.changesIntro', 'We may update these Terms of Service from time to time to reflect changes in our practices, technology, legal requirements, or other factors. When we make changes:')}
        </p>
        <ul className="space-y-2 text-lsc-dark/70 dark:text-lsc-cream/70 text-sm mb-4">
          <li className="flex items-start gap-2">
            <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
            {t('termsPage.changes1', 'We will update the "Last updated" date at the top of this page')}
          </li>
          <li className="flex items-start gap-2">
            <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
            {t('termsPage.changes2', 'Significant changes will be announced on our website and at library locations')}
          </li>
          <li className="flex items-start gap-2">
            <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">•</span>
            {t('termsPage.changes3', 'Your continued use of library services constitutes acceptance of the updated terms')}
          </li>
        </ul>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
          {t('termsPage.changesReview', 'We encourage you to review these terms periodically. If you have concerns about any changes, please contact us before continuing to use our services.')}
        </p>
      </section>

      {/* Contact Section */}
      <section className="bg-lsc-cream dark:bg-lsc-brown/20 rounded-xl p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 bg-lsc-cream dark:bg-earth-800 rounded-xl flex items-center justify-center">
            <HelpCircle aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
          </div>
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
            {t('termsPage.questionsAboutTerms', 'Questions About These Terms?')}
          </h3>
        </div>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
          {t('termsPage.questionsIntro', 'If you have questions about these Terms of Service or need clarification on any policies, please contact us:')}
        </p>
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex items-center gap-2 text-lsc-dark dark:text-lsc-cream/80">
            <Mail aria-hidden="true" className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light" />
            <span>{branding.contact_email}</span>
          </div>
        </div>
      </section>
    </div>
  )
}
