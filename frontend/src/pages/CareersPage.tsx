/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from "react";
import {
  Briefcase,
  Sparkles,
  BookOpen,
  Users,
  Heart,
  ArrowRight,
  CheckCircle2,
  Mail,
  Building2,
  GraduationCap,
  Library,
  Lightbulb,
  BarChart3,
  Globe,
  Clock,
  MapPin,
  DollarSign,
} from 'lucide-react';
import StandardPageLayout from '@/components/StandardPageLayout'
import { useTranslation } from '@/i18n'
import { useBranding } from '@/contexts/BrandingContext'

const benefits = [
  { key: 'careers.benefitHealthInsurance', fallback: 'Comprehensive health, dental, and vision insurance' },
  { key: 'careers.benefitPto', fallback: 'Generous paid time off and sick leave' },
  { key: 'careers.benefitPension', fallback: 'State pension/retirement plan participation' },
  { key: 'careers.benefitProfDev', fallback: 'Professional development budget for conferences, certifications, and courses (you choose)' },
  { key: 'careers.benefitTuition', fallback: 'Tuition reimbursement for library science, IT, social work, or related degrees' },
  { key: 'careers.benefitFlexible', fallback: 'Flexible and hybrid scheduling where the role allows' },
  { key: 'careers.benefitLibraryCard', fallback: 'Free library card with extended borrowing privileges' },
  { key: 'careers.benefitMakerspace', fallback: 'Full access to Makerspace equipment and creative tools' },
  { key: 'careers.benefitLearningTime', fallback: 'Dedicated learning time, 4 hours a month for professional growth on the clock' },
  { key: 'careers.benefitBookClub', fallback: 'Staff book club, wellness programs, and quiet reading time (really!)' },
];

// Demo content: this instance has no jobs backend. These are sample role
// profiles so applicants can see the kind of information a real posting
// would include (pay band, schedule, location). Replace with live postings
// when a careers/jobs data source exists.
const sampleRoles = [
  {
    title: 'Youth Services Librarian',
    pay: '$52,000 - $64,000 / year',
    schedule: 'Full time, 40 hours/week (includes some evenings and Saturdays)',
    location: 'Onsite at the main branch',
  },
  {
    title: 'Community Engagement Librarian',
    pay: '$50,000 - $61,000 / year',
    schedule: 'Full time, 40 hours/week',
    location: 'Hybrid, onsite plus community outreach',
  },
  {
    title: 'Digital Services Librarian',
    pay: '$55,000 - $68,000 / year',
    schedule: 'Full time, 40 hours/week',
    location: 'Hybrid, 2 days remote',
  },
  {
    title: 'Bilingual Reference Librarian',
    pay: '$50,000 - $63,000 / year',
    schedule: 'Part time, 20-25 hours/week',
    location: 'Onsite at the main branch',
  },
  {
    title: 'Makerspace & Programs Librarian',
    pay: '$48,000 - $59,000 / year',
    schedule: 'Full time, 40 hours/week (includes weekend programs)',
    location: 'Onsite at the main branch',
  },
];

const interviewSteps = [
  {
    titleKey: 'careers.interviewStep1Title', title: 'Application review',
    descriptionKey: 'careers.interviewStep1Desc', description: 'We read every application. You will hear back from a real person, usually within two weeks, whether or not we move forward.',
  },
  {
    titleKey: 'careers.interviewStep2Title', title: 'Phone or video chat',
    descriptionKey: 'careers.interviewStep2Desc', description: 'A 30 minute conversation with the hiring manager about your experience and the role. No trick questions.',
  },
  {
    titleKey: 'careers.interviewStep3Title', title: 'Onsite interview',
    descriptionKey: 'careers.interviewStep3Desc', description: 'About 90 minutes with two or three team members. We will share the questions ahead of time so you can prepare.',
  },
  {
    titleKey: 'careers.interviewStep4Title', title: 'Reference check and offer',
    descriptionKey: 'careers.interviewStep4Desc', description: 'We check references, then make an offer that includes the pay range and benefits up front.',
  },
];

const values = [
  {
    icon: Heart,
    titleKey: 'careers.values.communityFirst', title: 'Community First',
    descriptionKey: 'careers.values.communityFirstDesc', description: 'A library card should be the great equalizer. Every service we build, from search to legal aid to home delivery, exists to serve people who need it most.',
  },
  {
    icon: BookOpen,
    titleKey: 'careers.values.radicalLearningTitle', title: 'Radical Learning',
    descriptionKey: 'careers.values.radicalLearningDesc', description: 'We do not just help patrons learn. We learn constantly ourselves. Our staff are expected to grow, experiment, and stay curious about new tools and community needs.',
  },
  {
    icon: Users,
    titleKey: 'careers.values.dignityPrivacyTitle', title: 'Dignity & Privacy',
    descriptionKey: 'careers.values.dignityPrivacyDesc', description: 'What a patron reads, researches, or asks for help with is their business. We guard intellectual freedom and data privacy as core professional values.',
  },
  {
    icon: Sparkles,
    titleKey: 'careers.values.techAsCareTitle', title: 'Technology as Care',
    descriptionKey: 'careers.values.techAsCareDesc', description: 'We do not adopt technology to be impressive. We adopt it because it helps a homebound patron get books, a family find legal resources, or a kid discover a love of making.',
  },
];

export default function CareersPage(): React.ReactElement {
    const branding = useBranding()
  const { t } = useTranslation()
  const [notifyEmail, setNotifyEmail] = useState("")
  const [notifySubmitted, setNotifySubmitted] = useState(() => {
    return localStorage.getItem("l30-career-notify-email") !== null
  })

  const handleNotifySubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (notifyEmail) {
      localStorage.setItem("l30-career-notify-email", notifyEmail)
      setNotifySubmitted(true)
    }
  }

  return (
    <StandardPageLayout
      title={t('footer.careers', 'Careers')}
      subtitle={t('careers.pageSubtitle', 'Public library jobs and what it is like to work here. Open to all backgrounds.')}
      icon={Briefcase}
    >

      {/* Open Positions (leads the page) */}
      <section className="py-12 bg-lsc-white dark:bg-earth-800">
        <div className="container mx-auto px-4 max-w-4xl">
          <div className="bg-lsc-cream dark:bg-earth-700 rounded-xl p-8 border border-lsc-border dark:border-earth-700">
            <div className="flex items-start gap-4">
              <div className="flex-shrink-0 w-12 h-12 bg-sage-100 dark:bg-sage-800 rounded-full flex items-center justify-center">
                <Briefcase className="w-6 h-6 text-sage-600 dark:text-sage-400" />
              </div>
              <div className="flex-1">
                <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4">
                  {t('careers.openPositions', 'Open Positions')}
                </h2>
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70 leading-relaxed mb-2">
                  {t('careers.noOpeningsPosted', 'We do not have any openings posted right now.')}
                </p>
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70 leading-relaxed mb-6">
                  {t('careers.noOpeningsBody', 'We are a growing library and we hire a few times a year. Leave your email below and we will reach out when a role opens that fits your interests. You can also introduce yourself any time.')}
                </p>

                {notifySubmitted ? (
                  <div className="flex items-center gap-3 bg-sage-50 dark:bg-sage-900/30 rounded-lg p-4 motion-safe:animate-fade-in mb-4">
                    <CheckCircle2 className="w-5 h-5 text-sage-600 dark:text-sage-400 flex-shrink-0" />
                    <p className="text-lsc-dark/70 dark:text-lsc-cream/70 font-medium">
                      {t('careers.interestListConfirmed', 'You are on the interest list. We will be in touch when something opens.')}
                    </p>
                  </div>
                ) : (
                  <form onSubmit={handleNotifySubmit} className="flex flex-col sm:flex-row gap-3 mb-4">
                    <input
                      type="email"
                      required
                      value={notifyEmail}
                      onChange={(e) => setNotifyEmail(e.target.value)}
                      placeholder="your@email.com"
                      aria-label={t('aria.careersPage.emailInterestList', 'Email address to join the job interest list')}
                      className="flex-1 px-4 py-3 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream placeholder:text-earth-400 dark:placeholder:text-earth-500 focus:outline-none focus:ring-2 focus:ring-lsc-rose/50 motion-safe:transition-shadow"
                    />
                    <button
                      type="submit"
                      className="px-6 py-3 bg-lsc-rose hover:bg-lsc-rose/90 text-white font-medium rounded-lg motion-safe:transition-colors whitespace-nowrap"
                    >
                      {t('careers.joinInterestList', 'Join the interest list')}
                    </button>
                  </form>
                )}

                <a
                  href={`mailto:${branding.contact_email}?subject=Introducing myself`}
                  className="inline-flex items-center justify-center gap-2 text-lsc-rose hover:underline font-medium"
                >
                  <Mail className="w-4 h-4" />
                  {t('careers.introduceYourselfByEmail', 'Introduce yourself by email')}
                </a>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Roles We Hire For */}
      <section className="py-12 bg-lsc-cream dark:bg-lsc-dark">
        <div className="container mx-auto px-4 max-w-4xl">
          <h2 className="text-3xl font-serif font-bold text-lsc-dark dark:text-lsc-cream text-center mb-3">
            {t('careers.rolesWeHireForHeading', 'Roles We Hire For')}
          </h2>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-center mb-3 max-w-2xl mx-auto">
            {t('careers.rolesWeHireForBody', 'These are the kinds of jobs we post when we are hiring, with the pay, schedule, and location you can expect.')}
          </p>
          <p className="text-lsc-dark/50 dark:text-lsc-cream/50 text-center text-sm mb-10 max-w-2xl mx-auto">
            {t('careers.sampleRolesNote', 'Sample roles for reference. Live postings will appear above when positions are open.')}
          </p>

          <div className="space-y-4">
            {sampleRoles.map((role) => (
              <div
                key={role.title}
                className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700"
              >
                <h3 className="font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-3 text-lg">{role.title}</h3>
                <dl className="grid sm:grid-cols-3 gap-4 text-sm">
                  <div className="flex items-start gap-2">
                    <DollarSign className="w-4 h-4 text-sage-500 flex-shrink-0 mt-0.5" />
                    <div>
                      <dt className="font-medium text-lsc-dark dark:text-lsc-cream">{t('careers.payRangeLabel', 'Pay range')}</dt>
                      <dd className="text-lsc-dark/70 dark:text-lsc-cream/70">{role.pay}</dd>
                    </div>
                  </div>
                  <div className="flex items-start gap-2">
                    <Clock className="w-4 h-4 text-sage-500 flex-shrink-0 mt-0.5" />
                    <div>
                      <dt className="font-medium text-lsc-dark dark:text-lsc-cream">{t('careers.scheduleLabel', 'Schedule')}</dt>
                      <dd className="text-lsc-dark/70 dark:text-lsc-cream/70">{role.schedule}</dd>
                    </div>
                  </div>
                  <div className="flex items-start gap-2">
                    <MapPin className="w-4 h-4 text-sage-500 flex-shrink-0 mt-0.5" />
                    <div>
                      <dt className="font-medium text-lsc-dark dark:text-lsc-cream">{t('careers.locationLabel', 'Location')}</dt>
                      <dd className="text-lsc-dark/70 dark:text-lsc-cream/70">{role.location}</dd>
                    </div>
                  </div>
                </dl>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Why Work Here */}
      <section className="py-12 bg-lsc-white dark:bg-earth-800">
        <div className="container mx-auto px-4 max-w-4xl">
          <div className="bg-lsc-cream/50 dark:bg-earth-700 rounded-xl p-8 border border-lsc-border dark:border-earth-700">
            <div className="flex items-start gap-4">
              <div className="flex-shrink-0 w-12 h-12 bg-sage-100 dark:bg-sage-800 rounded-full flex items-center justify-center">
                <Library className="w-6 h-6 text-sage-600 dark:text-sage-400" />
              </div>
              <div>
                <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4">
                  {t('careers.whyWorkHereHeading', { libraryName: branding.library_name })}
                </h2>
                <div className="prose prose-earth dark:prose-invert max-w-none">
                  <p className="text-lsc-dark/70 dark:text-lsc-cream/70 leading-relaxed mb-4">
                    {t('careers.whyWorkHereBody1', 'This is a working public library that takes its staff seriously. We pay fair wages, post our pay ranges up front, and protect time for the learning and rest that make this work sustainable.')}
                  </p>
                  <p className="text-lsc-dark/70 dark:text-lsc-cream/70 leading-relaxed mb-4">
                    {t('careers.whyWorkHereBody2', 'Day to day, our team helps patrons find what they need, runs programs, builds the collection, keeps the technology working, and looks out for the people in our community who get overlooked. We have librarians, technologists, community navigators, makers, and privacy specialists, and we lean on each other.')}
                  </p>
                  <p className="text-lsc-dark/70 dark:text-lsc-cream/70 leading-relaxed">
                    {t('careers.whyWorkHereBody3', 'If you believe a library card is one of the most useful things a person can have, and you want to do that work with people who feel the same way, you would fit in here.')}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Our Values */}
      <section className="py-12 bg-lsc-cream dark:bg-lsc-dark">
        <div className="container mx-auto px-4 max-w-5xl">
          <h2 className="text-3xl font-serif font-bold text-lsc-dark dark:text-lsc-cream text-center mb-3">
            {t('careers.whatWeValue', 'What We Value')}
          </h2>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-center mb-10 max-w-2xl mx-auto">
            {t('careers.valuesIntro', 'Our team is united by these core principles that guide everything we do.')}
          </p>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {values.map((value) => (
              <div
                key={value.title}
                className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 text-center border border-lsc-border dark:border-earth-700"
              >
                <div className="w-12 h-12 bg-sage-100 dark:bg-sage-800 rounded-full flex items-center justify-center mx-auto mb-4">
                  <value.icon className="w-6 h-6 text-sage-600 dark:text-sage-400" />
                </div>
                <h3 className="font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">{t(value.titleKey, value.title)}</h3>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t(value.descriptionKey, value.description)}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Benefits */}
      <section className="py-12 bg-sage-100 dark:bg-sage-900">
        <div className="container mx-auto px-4 max-w-4xl">
          <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream text-center mb-8">
            {t('careers.benefitsHeading', 'Benefits & Perks')}
          </h2>
          <div className="grid md:grid-cols-2 gap-4">
            {benefits.map((benefit) => (
              <div key={benefit.key} className="flex items-start gap-3">
                <div className="flex-shrink-0 w-6 h-6 bg-lsc-white dark:bg-earth-700 rounded-full flex items-center justify-center">
                  <CheckCircle2 className="w-4 h-4 text-sage-600 dark:text-sage-400" />
                </div>
                <span className="text-lsc-dark/70 dark:text-lsc-cream/70">{t(benefit.key, benefit.fallback)}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* What to Expect: Interview Process */}
      <section className="py-12 bg-lsc-white dark:bg-earth-800">
        <div className="container mx-auto px-4 max-w-4xl">
          <h2 className="text-3xl font-serif font-bold text-lsc-dark dark:text-lsc-cream text-center mb-3">
            {t('careers.whatToExpectApplyHeading', 'What to Expect When You Apply')}
          </h2>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-center mb-10 max-w-2xl mx-auto">
            {t('careers.whatToExpectApplyBody', 'We try to make hiring clear and low stress. Here is each step, start to finish.')}
          </p>
          <ol className="space-y-4">
            {interviewSteps.map((step, index) => (
              <li
                key={step.title}
                className="flex items-start gap-4 bg-lsc-cream dark:bg-earth-700 rounded-xl p-6 border border-lsc-border dark:border-earth-700"
              >
                <div className="flex-shrink-0 w-9 h-9 bg-sage-100 dark:bg-sage-800 rounded-full flex items-center justify-center font-serif font-bold text-sage-700 dark:text-sage-300">
                  {index + 1}
                </div>
                <div>
                  <h3 className="font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-1">{t(step.titleKey, step.title)}</h3>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t(step.descriptionKey, step.description)}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* Thinking About Becoming A Librarian */}
      <section className="py-12 bg-lsc-cream dark:bg-lsc-dark">
        <div className="container mx-auto px-4 max-w-4xl">
          <h2 className="text-3xl font-serif font-bold text-lsc-dark dark:text-lsc-cream text-center mb-3">
            {t('careers.newToLibraryWorkHeading', 'New to Library Work?')}
          </h2>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-center mb-10 max-w-2xl mx-auto">
            {t('careers.newToLibraryWorkBody', 'Library work is part educator, part technologist, part community advocate. Here is what the pathway looks like.')}
          </p>

          <div className="grid md:grid-cols-3 gap-6 mb-8">
            {/* Education */}
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
              <div className="w-12 h-12 bg-sage-100 dark:bg-sage-800 rounded-full flex items-center justify-center mb-4">
                <GraduationCap className="w-6 h-6 text-sage-600 dark:text-sage-400" />
              </div>
              <h3 className="font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-3 text-lg">{t('careers.educationHeading', 'Education')}</h3>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
                {t('careers.educationBody', 'An MLS/MLIS opens doors, but we value demonstrated skill and diverse backgrounds. Library science, social work, IT, education, and community health all prepare you for this work.')}
              </p>
              <ul className="space-y-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-sage-500 flex-shrink-0 mt-0.5" />
                  <span>{t('careers.typicallyYearsOfFullTime')}</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-sage-500 flex-shrink-0 mt-0.5" />
                  <span>{t('careers.someProgramsOfferOnlineOptions')}</span>
                </li>
              </ul>
            </div>

            {/* Career Paths */}
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
              <div className="w-12 h-12 bg-sage-100 dark:bg-sage-800 rounded-full flex items-center justify-center mb-4">
                <BarChart3 className="w-6 h-6 text-sage-600 dark:text-sage-400" />
              </div>
              <h3 className="font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-3 text-lg">{t('careers.careerPaths', 'Career Paths')}</h3>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
                {t('careers.careerPathsBody', 'Modern library roles span community services, technology, data privacy, creative programming, and specialized reference, far beyond the traditional desk.')}
              </p>
              <ul className="space-y-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-sage-500 flex-shrink-0 mt-0.5" />
                  <span>{t('careers.publicAcademicOrSpecialLibraries')}</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-sage-500 flex-shrink-0 mt-0.5" />
                  <span>{t('careers.digitalServicesAndTechnologyRoles')}</span>
                </li>
              </ul>
            </div>

            {/* Professional Growth */}
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
              <div className="w-12 h-12 bg-sage-100 dark:bg-sage-800 rounded-full flex items-center justify-center mb-4">
                <Lightbulb className="w-6 h-6 text-sage-600 dark:text-sage-400" />
              </div>
              <h3 className="font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-3 text-lg">{t('careers.professionalGrowth', 'Professional Growth')}</h3>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
                {t('careers.professionalGrowthBody', 'The field keeps changing. We invest in continuous learning with certifications, conferences, and dedicated on-the-clock growth time for every staff member.')}
              </p>
              <ul className="space-y-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-sage-500 flex-shrink-0 mt-0.5" />
                  <span>{t('careers.specializedCertifications', 'Specialized certifications available')}</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-sage-500 flex-shrink-0 mt-0.5" />
                  <span>{t('careers.leadershipAndManagementOpportunities')}</span>
                </li>
              </ul>
            </div>
          </div>

          {/* Resources */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
            <div className="flex items-start gap-4">
              <Globe className="w-6 h-6 text-lsc-rose flex-shrink-0" />
              <div>
                <h3 className="font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-3">{t('careers.learnMore', 'Learn More')}</h3>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
                  {t('careers.learnMoreIntro', 'Want to explore library science further? Here are some resources to get started:')}
                </p>
                <ul className="space-y-2 text-sm">
                  <li className="flex items-start gap-2 text-lsc-dark/70 dark:text-lsc-cream/70">
                    <ArrowRight className="w-4 h-4 text-lsc-rose flex-shrink-0 mt-0.5" />
                    <span>{t('careers.americanLibraryAssociationAla')} <a href="https://www.ala.org" target="_blank" rel="noopener noreferrer" className="text-lsc-rose hover:underline">www.ala.org</a></span>
                  </li>
                  <li className="flex items-start gap-2 text-lsc-dark/70 dark:text-lsc-cream/70">
                    <ArrowRight className="w-4 h-4 text-lsc-rose flex-shrink-0 mt-0.5" />
                    <span>{t('careers.alaAccreditedProgramsSearchFor')}</span>
                  </li>
                  <li className="flex items-start gap-2 text-lsc-dark/70 dark:text-lsc-cream/70">
                    <ArrowRight className="w-4 h-4 text-lsc-rose flex-shrink-0 mt-0.5" />
                    <span>{t('careers.libraryJobBoardsExploreOpportunities')}</span>
                  </li>
                  <li className="flex items-start gap-2 text-lsc-dark/70 dark:text-lsc-cream/70">
                    <ArrowRight className="w-4 h-4 text-lsc-rose flex-shrink-0 mt-0.5" />
                    <span>{t('careers.informationalInterviewsConnectWithLibrarians')}</span>
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* How to Apply */}
      <section className="py-16 bg-lsc-white dark:bg-earth-800">
        <div className="container mx-auto px-4 max-w-4xl">
          <div className="bg-lsc-cream dark:bg-earth-700 rounded-xl p-8 border border-lsc-border dark:border-earth-700">
            <div className="flex items-start gap-4">
              <div className="flex-shrink-0 w-12 h-12 bg-lsc-rose rounded-full flex items-center justify-center">
                <Mail className="w-6 h-6 text-white" />
              </div>
              <div>
                <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4">
                  {t('careers.howToApplyHeading', 'How to Apply')}
                </h2>
                <div className="prose prose-earth dark:prose-invert max-w-none">
                  <p className="text-lsc-dark/70 dark:text-lsc-cream/70 leading-relaxed mb-4">
                    {t('careers.howToApplyIntro', 'When a role is open, here is what we need from you:')}
                  </p>
                  <ul className="space-y-2 mb-6">
                    <li className="flex items-start gap-2 text-lsc-dark/70 dark:text-lsc-cream/70">
                      <CheckCircle2 className="w-5 h-5 text-sage-500 flex-shrink-0 mt-0.5" />
                      <span><strong>{t('careers.resumeCvLead', 'Resume or CV')}</strong> {t('careers.resumeCvRest', 'highlighting relevant experience')}</span>
                    </li>
                    <li className="flex items-start gap-2 text-lsc-dark/70 dark:text-lsc-cream/70">
                      <CheckCircle2 className="w-5 h-5 text-sage-500 flex-shrink-0 mt-0.5" />
                      <span><strong>{t('careers.coverLetterLead', 'Cover letter')}</strong> {t('careers.coverLetterRest', 'telling us why you are excited about this role')}</span>
                    </li>
                    <li className="flex items-start gap-2 text-lsc-dark/70 dark:text-lsc-cream/70">
                      <CheckCircle2 className="w-5 h-5 text-sage-500 flex-shrink-0 mt-0.5" />
                      <span><strong>{t('careers.referencesLead', 'Three professional references')}</strong> {t('careers.referencesRest', '(we promise to be gentle)')}</span>
                    </li>
                  </ul>
                  <p className="text-lsc-dark/70 dark:text-lsc-cream/70 leading-relaxed mb-6">
                    {t('careers.applyEmailPrefix', 'Email your application materials to ')}<a href={`mailto:${branding.contact_email}`} className="text-lsc-rose hover:underline">{branding.contact_email}</a>{t('careers.applyEmailSuffix', ' with the job title in the subject line. We review applications on a rolling basis and will contact qualified candidates for interviews.')}
                  </p>
                  <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">
                    {t('careers.eeoStatement', { libraryName: branding.library_name })}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Contact CTA */}
      <section className="py-16 bg-lsc-cream dark:bg-lsc-dark">
        <div className="container mx-auto px-4 max-w-2xl text-center">
          <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4">
            {t('careers.questionsHeading', 'Questions About Working Here?')}
          </h2>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-8">
            {t('careers.questionsBody', 'We are happy to talk about our roles, work culture, or anything else you would like to know. Reach out any time.')}
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center mb-8">
            <a
              href={`mailto:${branding.contact_email}`}
              className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-lsc-rose hover:bg-lsc-rose/90 text-white font-medium rounded-xl transition-colors"
            >
              <Mail className="w-4 h-4" />
              {branding.contact_email}
            </a>
            <a
              href="/about"
              className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-lsc-white dark:bg-earth-700 hover:bg-sage-50 dark:hover:bg-earth-600 text-lsc-dark dark:text-lsc-cream font-medium rounded-xl border border-lsc-border dark:border-earth-700 transition-colors"
            >
              <Building2 className="w-4 h-4" />
              {t('careers.learnAboutUs', 'Learn About Us')}
            </a>
          </div>
        </div>
      </section>

    </StandardPageLayout>
  );
}
