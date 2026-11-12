/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Eye, Lock } from 'lucide-react'
import { useTranslation } from '@/i18n'

interface BulletPoint {
  title: string
  body: string
}

function BulletCard({ icon: Icon, heading, lead, items }: {
  icon: React.ElementType
  heading: string
  lead: string
  items: BulletPoint[]
}): React.ReactElement {
  return (
    <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl p-6">
      <div className="flex items-center gap-2 mb-4">
        <Icon aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
        <h3 className="text-lg font-serif font-bold text-lsc-dark dark:text-lsc-cream">
          {heading}
        </h3>
      </div>
      <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4 text-sm">{lead}</p>
      <ul className="space-y-3 text-sm">
        {items.map(item => (
          <li key={item.title} className="flex gap-2">
            <span aria-hidden="true" className="text-lsc-rose font-bold">•</span>
            <span className="text-lsc-dark/70 dark:text-lsc-cream/70">
              <span className="font-semibold text-lsc-dark dark:text-lsc-cream">{item.title}:</span>{' '}
              {item.body}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default function SafetyTransparencySection(): React.ReactElement {
  const { t } = useTranslation()
  const guardrails: BulletPoint[] = [
    {
      title: t('aITools.guardrailMedicalTitle', 'No medical advice'),
      body: t('aITools.willSuggestCallingANurse', 'Will suggest calling a nurse hotline or visiting the health department'),
    },
    {
      title: t('aITools.guardrailLegalTitle', 'No legal advice'),
      body: t('aITools.pointsToLegalAidResources', 'Points to legal aid resources and the law library in Elmdale'),
    },
    {
      title: t('aITools.guardrailFinancialTitle', 'No financial advice'),
      body: t('aITools.suggestsTheFreeTaxPrep', 'Suggests the free tax prep clinic or credit union'),
    },
    {
      title: t('aITools.guardrailFamilyTitle', 'Family-friendly only'),
      body: t('aITools.contentFilterEnabledRedirectsInappropriate', 'Content filter enabled; redirects inappropriate queries'),
    },
    {
      title: t('aITools.guardrailUncertaintyTitle', 'Admits uncertainty'),
      body: t('aITools.trainedToSayIDon', 'Trained to say "I don\'t know" rather than guess'),
    },
    {
      title: t('aITools.guardrailHandoffTitle', 'Human escalation'),
      body: t('aITools.complexQuestionsGetRoutedTo', 'Complex questions get routed to staff'),
    },
    {
      title: t('aITools.guardrailVendorTitle', 'Age-appropriate by design'),
      body: t(
        'aITools.allToolsComplyWithVendor',
        'Age restrictions enforced (COPPA-aligned); staff review tools and prompts before they go live for public programming. The patron-facing tools on this page run locally on library hardware — no patron data flows to a third-party AI vendor. The admin policy-extraction tool that can use OpenAI is listed in the data-flow matrix above; its use complies with OpenAI\'s Terms of Service and COPPA where applicable.',
      ),
    },
    {
      title: t('aITools.guardrailAccuracyTitle', 'Accuracy limits'),
      body: t(
        'aITools.weApplyHumanOversightAnd',
        'We apply human oversight and fact-checking to AI outputs to the best of our ability, but acknowledge that errors (hallucinations) can occur',
      ),
    },
  ]
  const transparency: BulletPoint[] = [
    {
      title: t('aITools.askToSeeTheSystem', 'Ask to see the system prompt'),
      body: t('aITools.askToSeeTheSystemBody', "We'll print it out for you. It's not secret."),
    },
    {
      title: t('aITools.requestTheirInteractionLogs', 'Request their interaction logs'),
      body: t('aITools.requestTheirInteractionLogsBody', "Oh wait, there aren't any. We don't log what you type."),
    },
    {
      title: t('aITools.talkToStevieAboutThe', 'Talk to Stevie about the tech'),
      body: t('aITools.talkToStevieAboutTheBody', 'She loves explaining it. Too much, honestly. Bring coffee.'),
    },
    {
      title: t('aITools.suggestImprovementsTitle', 'Suggest improvements'),
      body: t('aITools.suggestImprovementsBody', 'Several of our best prompts came from patron feedback.'),
    },
  ]

  return (
    <section id="safety" className="scroll-mt-24">
      <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-6">
        {t('aITools.safetyHeading', 'Safety and Transparency')}
      </h2>
      <div className="grid md:grid-cols-2 gap-6 mb-6">
        <BulletCard
          icon={Lock}
          heading={t('aITools.safetyGuardrails', 'Safety Guardrails')}
          lead={t(
            'aITools.safetyGuardrailsLead',
            'Our IT staff configured hard limits. The AI has built-in restrictions that prevent it from doing certain things, no matter how you ask:',
          )}
          items={guardrails}
        />
        <BulletCard
          icon={Eye}
          heading={t('aITools.radicalTransparency', 'Radical Transparency')}
          lead={t(
            'aITools.radicalTransparencyLead',
            "You can see everything. We don't hide how this works. Any patron can:",
          )}
          items={transparency}
        />
      </div>
    </section>
  )
}
