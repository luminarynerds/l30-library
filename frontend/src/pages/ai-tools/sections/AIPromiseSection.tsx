/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { ShieldCheck, Server, EyeOff } from 'lucide-react'
import { useTranslation } from '@/i18n'
import TrustCard from '../components/TrustCard'

export default function AIPromiseSection(): React.ReactElement {
  const { t } = useTranslation()
  const promises = [
    {
      icon: Server,
      title: t('aITools.runsOnOurComputersTitle', 'Runs on our computers'),
      body: t('aITools.runsOnOurComputersBody', 'The AI tools on this page run on Llama 3.2 via Ollama on a Dell PowerEdge R720 in our building. No prompt, no answer, no question leaves our network.'),
    },
    {
      icon: ShieldCheck,
      title: t('aITools.noTrainingTitle', 'No training on your data'),
      body: t('aITools.noTrainingBody', "We don't use your questions to train models. Your conversations aren't product."),
    },
    {
      icon: EyeOff,
      title: t('aITools.noTrackingTitle', 'No tracking, period'),
      body: t('aITools.noTrackingBody', "We don't track what you ask, what you write, or what you read. Stevie insisted."),
    },
  ]

  return (
    <section
      id="promise"
      className="scroll-mt-24 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl p-6"
    >
      <div className="flex items-center gap-2 mb-4">
        <ShieldCheck aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
        <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
          {t('aITools.ourAiPromise', 'Our AI Promise')}
        </h2>
      </div>
      <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-6">
        {t('aITools.ourAiPromiseLead', "The boring legal version is in our privacy policy. Here's the human version.")}
      </p>
      <div className="grid md:grid-cols-3 gap-6">
        {promises.map(p => (
          <TrustCard key={p.title} icon={p.icon} title={p.title} body={p.body} />
        ))}
      </div>
    </section>
  )
}
