/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
export interface RemovalResource {
  name: string
  description: string
  descriptionKey: string
  url: string
  type: 'official' | 'guide' | 'tool'
}

export interface RemovalStep {
  step: number
  title: string
  titleKey: string
  description: string
  descriptionKey: string
}

export const GOOGLE_REMOVAL_RESOURCES: RemovalResource[] = [
  {
    name: 'Google Search Content Removal',
    description: 'Request removal of personal info like phone numbers, email addresses, or physical addresses from Google Search results.',
    descriptionKey: 'components.legal.privacyTab.googleSearchContentRemovalDesc',
    url: 'https://support.google.com/websearch/troubleshooter/9685456',
    type: 'official',
  },
  {
    name: 'Google Results About You',
    description: 'Use the "Results about you" tool to find and request removal of results containing your personal contact info.',
    descriptionKey: 'components.legal.privacyTab.googleResultsAboutYouDesc',
    url: 'https://myactivity.google.com/results-about-you',
    type: 'official',
  },
  {
    name: 'Outdated Content Removal',
    description: 'Request removal of outdated cached pages that no longer exist on the original website.',
    descriptionKey: 'components.legal.privacyTab.outdatedContentRemovalDesc',
    url: 'https://search.google.com/search-console/remove-outdated-content',
    type: 'official',
  },
  {
    name: 'Legal Removal Requests',
    description: 'Submit legal requests for removal of content that violates laws (defamation, copyright, court orders).',
    descriptionKey: 'components.legal.privacyTab.legalRemovalRequestsDesc',
    url: 'https://support.google.com/legal/troubleshooter/1114905',
    type: 'official',
  },
]

export const OTHER_REMOVAL_RESOURCES: RemovalResource[] = [
  {
    name: 'FTC Identity Theft Recovery',
    description: 'Official federal resource for identity theft victims with step-by-step recovery plans.',
    descriptionKey: 'components.legal.privacyTab.ftcIdentityTheftRecoveryDesc',
    url: 'https://www.identitytheft.gov/',
    type: 'official',
  },
  {
    name: 'Have I Been Pwned',
    description: 'Check if your email or phone has been exposed in a data breach. Free monitoring available.',
    descriptionKey: 'components.legal.privacyTab.haveIBeenPwnedDesc',
    url: 'https://haveibeenpwned.com/',
    type: 'tool',
  },
  {
    name: 'Privacy Rights Clearinghouse',
    description: 'Comprehensive guides on privacy rights, data broker opt-outs, and consumer privacy protection.',
    descriptionKey: 'components.legal.privacyTab.privacyRightsClearinghouseDesc',
    url: 'https://privacyrights.org/',
    type: 'official',
  },
  {
    name: 'EFF Surveillance Self-Defense',
    description: 'Tips, tools, and how-tos for safer online communications from the Electronic Frontier Foundation.',
    descriptionKey: 'components.legal.privacyTab.effSurveillanceSelfDefenseDesc',
    url: 'https://ssd.eff.org/',
    type: 'tool',
  },
]

export const DATA_BROKER_OPT_OUTS: RemovalResource[] = [
  {
    name: 'Spokeo',
    description: 'People search engine opt-out',
    descriptionKey: 'components.legal.privacyTab.spokeoDesc',
    url: 'https://www.spokeo.com/optout',
    type: 'tool',
  },
  {
    name: 'WhitePages',
    description: 'Directory listing removal',
    descriptionKey: 'components.legal.privacyTab.whitepagesDesc',
    url: 'https://www.whitepages.com/suppression-requests',
    type: 'tool',
  },
  {
    name: 'BeenVerified',
    description: 'Background check opt-out',
    descriptionKey: 'components.legal.privacyTab.beenverifiedDesc',
    url: 'https://www.beenverified.com/faq/opt-out/',
    type: 'tool',
  },
  {
    name: 'Intelius',
    description: 'People search removal',
    descriptionKey: 'components.legal.privacyTab.inteliusDesc',
    url: 'https://www.intelius.com/opt-out',
    type: 'tool',
  },
]

export const REMOVAL_STEPS: RemovalStep[] = [
  {
    step: 1,
    title: 'Search for Yourself',
    titleKey: 'components.legal.privacyTab.searchForYourself',
    description: 'Google your full name, phone number, address, and email to see what information is publicly available.',
    descriptionKey: 'components.legal.privacyTab.searchForYourselfDesc',
  },
  {
    step: 2,
    title: 'Document What You Find',
    titleKey: 'components.legal.privacyTab.documentWhatYouFind',
    description: 'Save URLs and screenshots of pages containing your personal information for your removal requests.',
    descriptionKey: 'components.legal.privacyTab.documentWhatYouFindDesc',
  },
  {
    step: 3,
    title: 'Submit Removal Requests',
    titleKey: 'components.legal.privacyTab.submitRemovalRequests',
    description: "Use Google's official tools above to request removal of results containing your personal information.",
    descriptionKey: 'components.legal.privacyTab.submitRemovalRequestsDesc',
  },
  {
    step: 4,
    title: 'Contact Original Sites',
    titleKey: 'components.legal.privacyTab.contactOriginalSites',
    description: 'Reach out to website owners directly to request content removal at the source.',
    descriptionKey: 'components.legal.privacyTab.contactOriginalSitesDesc',
  },
  {
    step: 5,
    title: 'Opt Out of Data Brokers',
    titleKey: 'components.legal.privacyTab.optOutOfDataBrokers',
    description: 'Use the opt-out links below to remove your info from people-search websites.',
    descriptionKey: 'components.legal.privacyTab.optOutOfDataBrokersDesc',
  },
  {
    step: 6,
    title: 'Monitor Regularly',
    titleKey: 'components.legal.privacyTab.monitorRegularly',
    description: 'Set up Google Alerts for your name and check periodically. Data brokers may re-add your info over time.',
    descriptionKey: 'components.legal.privacyTab.monitorRegularlyDesc',
  },
]
