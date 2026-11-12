/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useId, useState } from 'react'
import { HelpCircle, X } from 'lucide-react'
import { useTranslation } from '@/i18n/I18nContext'

// ---------------------------------------------------------------------------
// MoodLegend
//
// A small "What do these mean?" disclosure that explains the mood tags in
// plain language. Mood tags are a low-cognitive-load entry point for ND
// patrons, but only if the words are unambiguous -- this is where we say what
// "Intense" means and disambiguate it on audio (content vs. narration).
//
// Keyboard + screen-reader accessible: a real <button> toggles an expandable
// region (aria-expanded / aria-controls). No portal, no focus trap -- it's an
// inline panel, not a modal, so Escape-to-close + outside-click are nice-to-
// have, not required for a non-trapping disclosure.
// ---------------------------------------------------------------------------

interface MoodMeaning {
  tag: string
  meaning: string
}

export default function MoodLegend() {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const panelId = useId()

  // Plain-language meanings. Kept here (not in the data layer) because they are
  // patron-facing explanatory copy, not catalog data.
  const meanings: MoodMeaning[] = [
    { tag: 'Calm', meaning: t('catalog.mood.legend.calm', 'Quiet, low-stakes, easy to put down and pick back up.') },
    { tag: 'Gentle', meaning: t('catalog.mood.legend.gentle', 'Soft and reassuring, nothing jarring.') },
    { tag: 'Hopeful', meaning: t('catalog.mood.legend.hopeful', 'Ends in a better place than it starts; leaves you lifted.') },
    { tag: 'Funny', meaning: t('catalog.mood.legend.funny', 'Meant to make you laugh.') },
    { tag: 'Intense', meaning: t('catalog.mood.legend.intense', 'High-stakes and gripping. On audiobooks this describes the story’s content (tension, violence, distress), not a loud or fast narration.') },
    { tag: 'Dark', meaning: t('catalog.mood.legend.dark', 'Heavy themes — grief, dread, the worst of people. Not necessarily sad, but not light.') },
    { tag: 'Mind-bending', meaning: t('catalog.mood.legend.mindBending', 'Plays with ideas, reality, or structure; expect to think.') },
    { tag: 'Personal', meaning: t('catalog.mood.legend.personal', 'Intimate, first-person, identity-forward. Often memoir or own-voices.') },
  ]

  return (
    <div className="mt-3">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-controls={panelId}
        className="inline-flex items-center gap-1.5 text-xs font-semibold text-lsc-rose hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose rounded-sm px-1 py-1 min-h-[32px]"
      >
        <HelpCircle className="w-4 h-4" aria-hidden="true" />
        {t('catalog.mood.legend.trigger', 'What do the mood tags mean?')}
      </button>

      {open && (
        <div
          id={panelId}
          role="region"
          aria-label={t('catalog.mood.legend.title', 'Mood tags explained')}
          className="mt-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 p-4 max-w-prose"
        >
          <div className="flex items-start justify-between gap-3 mb-2">
            <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
              {t('catalog.mood.legend.intro', 'Mood tags describe how a title feels, so you can pick by what you’re in the mood for. Tap any tag to browse more like it.')}
            </p>
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="flex-shrink-0 p-1.5 text-lsc-dark/60 dark:text-lsc-cream/50 hover:text-lsc-rose focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose rounded-lg min-w-[32px] min-h-[32px] flex items-center justify-center"
              aria-label={t('catalog.mood.legend.close', 'Close mood tag explainer')}
            >
              <X className="w-4 h-4" aria-hidden="true" />
            </button>
          </div>
          <dl className="space-y-1.5">
            {meanings.map(({ tag, meaning }) => (
              <div key={tag} className="text-sm">
                <dt className="inline font-semibold text-lsc-dark dark:text-lsc-cream">{tag}: </dt>
                <dd className="inline text-lsc-dark/75 dark:text-lsc-cream/70">{meaning}</dd>
              </div>
            ))}
          </dl>
        </div>
      )}
    </div>
  )
}
