/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Heart,
  ClipboardList,
  Users,
  Coffee,
  ChevronDown,
  ArrowRight,
} from 'lucide-react'
import StandardPageLayout from '@/components/StandardPageLayout'
import { usePageTitle } from '@/hooks/usePageTitle'

const steps = [
  {
    icon: ClipboardList,
    title: 'Tell Us About You',
    description:
      'Answer a few quick questions. No judgment. Just: Are you new here? Do you have a baby? What do you need most?',
  },
  {
    icon: Users,
    title: 'We Make the Match',
    description:
      "We connect you with someone from our community who's been in your shoes. Someone who remembers. Someone who gets it.",
  },
  {
    icon: Coffee,
    title: 'Real Connection',
    description:
      "Coffee, texts, park days, venting\u2014whatever you need. A real friendship. Someone who thinks you matter.",
  },
]

const faqs = [
  {
    question: 'Is this a therapy or counseling service?',
    answer:
      'No. This is peer support\u2014two people who get it talking to each other.',
  },
  {
    question: 'What if I\'m not "bad enough" to need help?',
    answer:
      "You don\u2019t need to be struggling to benefit from connection. Lots of people just want a friend who gets parenthood. That\u2019s enough.",
  },
  {
    question: 'How much time does a mentor relationship take?',
    answer:
      "Whatever works for you. For some people, it\u2019s a text a few times a week. For others, it\u2019s weekly coffee dates. You decide.",
  },
  {
    question: "I want to mentor but I don't have much experience. Can I do it?",
    answer:
      "Absolutely. You don\u2019t need to be perfect. You just need to remember what it felt like.",
  },
  {
    question: 'Is this free?',
    answer:
      "Yes, completely free. We believe connection shouldn\u2019t cost money.",
  },
]

export default function ParentMentorsPage(): React.ReactElement {
  usePageTitle('Parent Mentors')
  const [openFaq, setOpenFaq] = useState<number | null>(null)

  return (
    <StandardPageLayout
      title="Parent Mentors"
      subtitle="Connect with a parent who's been exactly where you are"
      icon={Heart}
    >
      <div className="space-y-16 md:space-y-24">
        {/* Section 1: What Is Parent Mentors? */}
        <section>
          <h2 className="font-serif text-2xl md:text-3xl text-lsc-dark dark:text-lsc-cream mb-6">
            You Get a Real Friend, Not Just Advice
          </h2>
          <div className="max-w-3xl space-y-4 text-lsc-dark/70 dark:text-lsc-cream/70 leading-relaxed">
            <p>
              Becoming a parent is one of life&apos;s biggest changes. Doing it alone in a
              new place? That&apos;s overwhelming. That&apos;s why we created Parent
              Mentors&mdash;we match you with someone from our community who&apos;s been
              where you are.
            </p>
            <p>
              Someone who remembers the fear, the exhaustion, the wondering if
              they&apos;re doing it right. Someone who just <em>knows</em>.
            </p>
          </div>

          {/* Community photo */}
          <div className="mt-8 max-w-2xl">
            <img
              src="/images/families-community.webp"
              alt="Diverse group of parents and children playing together at a community gathering"
              className="rounded-xl shadow-lg w-full"
            />
          </div>
        </section>

        {/* Section 2: How It Works */}
        <section>
          <h2 className="font-serif text-2xl md:text-3xl text-lsc-dark dark:text-lsc-cream mb-8">
            How It Works
          </h2>
          <div className="grid md:grid-cols-3 gap-6">
            {steps.map((step, i) => (
              <div
                key={step.title}
                className="p-6 rounded-xl bg-lsc-white dark:bg-earth-800/40 border border-lsc-border dark:border-earth-700/30"
              >
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 rounded-lg bg-lsc-rose/10 dark:bg-lsc-rose/20 flex items-center justify-center">
                    <step.icon className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
                  </div>
                  <span className="font-mono text-xs tracking-wider text-earth-600 uppercase">
                    Step {i + 1}
                  </span>
                </div>
                <h3 className="font-serif text-lg text-lsc-dark dark:text-lsc-cream mb-2">
                  {step.title}
                </h3>
                <p className="text-sm text-earth-600 dark:text-earth-400 leading-relaxed">
                  {step.description}
                </p>
              </div>
            ))}
          </div>
        </section>

        {/* Section 3: Join the Program */}
        <section className="text-center">
          <h2 className="font-serif text-2xl md:text-3xl text-lsc-dark dark:text-lsc-cream mb-3">
            Join the Program
          </h2>
          <p className="text-earth-600 dark:text-earth-400 mb-8 max-w-lg mx-auto">
            Whether you need support or want to give it, there&apos;s a place for you here.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              to="/parent-mentors/request"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-lsc-rose hover:bg-lsc-rose/90 text-white font-semibold shadow-md hover:shadow-lg transition-all min-h-[48px]"
            >
              <Heart className="w-5 h-5" aria-hidden="true" />
              I Need a Mentor
              <ArrowRight className="w-4 h-4" aria-hidden="true" />
            </Link>
            <Link
              to="/parent-mentors/volunteer"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-lsc-cream dark:bg-lsc-brown hover:bg-lsc-border dark:hover:bg-lsc-brown/80 text-lsc-dark dark:text-lsc-cream font-medium border-2 border-lsc-border dark:border-lsc-brown shadow-sm hover:shadow transition-all min-h-[48px]"
            >
              <Users className="w-5 h-5" aria-hidden="true" />
              Become a Mentor
              <ArrowRight className="w-4 h-4" aria-hidden="true" />
            </Link>
          </div>
          <p className="text-sm text-earth-600 dark:text-earth-400 mt-6 italic">
            Free. Always has been. Someone&apos;s going to check on you.
          </p>
        </section>

        {/* Section 4: FAQs */}
        <section>
          <h2 className="font-serif text-2xl md:text-3xl text-lsc-dark dark:text-lsc-cream mb-8">
            Frequently Asked Questions
          </h2>
          <div className="max-w-2xl space-y-3">
            {faqs.map((faq, i) => (
              <div
                key={i}
                className="rounded-xl border border-lsc-border dark:border-earth-700/50 overflow-hidden"
              >
                <button
                  onClick={() => setOpenFaq(openFaq === i ? null : i)}
                  className="w-full flex items-center justify-between gap-4 p-4 text-left bg-lsc-white dark:bg-earth-800/40 hover:bg-earth-50 dark:hover:bg-earth-800/60 transition-colors"
                  aria-expanded={openFaq === i}
                >
                  <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                    {faq.question}
                  </span>
                  <ChevronDown
                    className={`w-4 h-4 text-earth-600 flex-shrink-0 transition-transform duration-200 ${
                      openFaq === i ? 'rotate-180' : ''
                    }`}
                    aria-hidden="true"
                  />
                </button>
                {openFaq === i && (
                  <div className="px-4 pb-4 bg-lsc-white dark:bg-earth-800/40">
                    <p className="text-sm text-earth-600 dark:text-earth-400 leading-relaxed">
                      {faq.answer}
                    </p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
      </div>
    </StandardPageLayout>
  )
}
