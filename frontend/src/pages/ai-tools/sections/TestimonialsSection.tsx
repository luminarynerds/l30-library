/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useTranslation } from '@/i18n'

interface Testimonial {
  quote: string
  attribution: string
}

export default function TestimonialsSection(): React.ReactElement {
  const { t } = useTranslation()
  const testimonials: Testimonial[] = [
    {
      quote: t(
        'aITools.testimonialEleanorQuote',
        '"I used to be afraid of the computers. Now I come in three times a week to use the book recommender. It helped me find books about my mother\'s village in Taiwan—books I didn\'t even know existed. And it never makes me feel slow."',
      ),
      attribution: t('aITools.testimonialEleanorAttribution', '— Eleanor Chen, 74, retired teacher'),
    },
    {
      quote: t(
        'aITools.testimonialJamieQuote',
        '"I was the biggest skeptic on staff. I thought AI would replace us. Instead, it handles the routine questions so I can actually do reference work. Last month I helped a genealogist trace her family back five generations. That\'s why I became a librarian."',
      ),
      attribution: t('aITools.testimonialJamieAttribution', '— Jamie Torres, Reference Librarian'),
    },
  ]

  return (
    <section className="bg-lsc-cream dark:bg-lsc-dark/20 border border-lsc-border dark:border-earth-700 rounded-xl p-8 mb-8">
      <h2 className="text-lg font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-6">
        {t('aITools.testimonialsHeading', 'What Folks Are Saying')}
      </h2>
      <div className="space-y-6">
        {testimonials.map(testimonial => (
          <div key={testimonial.attribution} className="border-l-4 border-lsc-rose pl-6">
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 italic mb-3">
              {testimonial.quote}
            </p>
            <p className="font-semibold text-lsc-dark dark:text-lsc-cream">
              {testimonial.attribution}
            </p>
          </div>
        ))}
      </div>
      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-6">
        {t(
          'aITools.testimonialsMore',
          'More stories from patrons like Marcus Williams, Sarah Nguyen, and others are available at the library.',
        )}
      </p>
    </section>
  )
}
