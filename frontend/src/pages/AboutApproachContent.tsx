/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Link } from 'react-router-dom'
import PageContainer from '@/components/layout/PageContainer'

export default function AboutApproachContent(): React.ReactElement {
  return (
    <PageContainer width="read" className="pb-16">
      {/* Hero */}
      <header className="mb-10">
        <p className="text-xs font-semibold uppercase tracking-widest text-lsc-rose mb-4">
          Fictional library. Real product.
        </p>
        <h1 className="text-4xl sm:text-5xl font-serif font-bold text-lsc-dark dark:text-lsc-cream leading-tight">
          This library doesn&rsquo;t exist.
        </h1>
        <p className="text-2xl sm:text-3xl font-serif text-lsc-dark/60 dark:text-lsc-cream/60 mt-2">
          Everything on this page does.
        </p>
      </header>

      <div className="space-y-5 text-base text-lsc-dark/80 dark:text-lsc-cream/90 leading-relaxed">
        <p>
          There is no Little Schitt Creek. No Marlene in the director&rsquo;s
          office. No Eleanor coming in three times a week. We made them up.
        </p>

        <p className="font-medium text-lsc-dark dark:text-lsc-cream">
          What we didn&rsquo;t make up:
        </p>

        <p>
          The catalog you just searched. The accessibility presets you just
          clicked. The challenge-review workflow, the AI scorecard, the stats
          counter updating daily, the indie ebook collection the library owns
          outright. All of it is <strong>L30</strong>, a complete, open-source
          library management system, running live right now on a server that
          costs less than a year of database subscriptions.
        </p>

        <p className="text-lg font-medium text-lsc-dark dark:text-lsc-cream">
          You weren&rsquo;t browsing a mockup. You were using the product.
        </p>
      </div>

      <hr className="border-lsc-border dark:border-earth-700 my-10" />

      {/* Why we did it this way */}
      <section className="space-y-4">
        <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
          Why we did it this way
        </h2>
        <p className="text-base text-lsc-dark/80 dark:text-lsc-cream/90 leading-relaxed">
          Most ILS demos are a sales call, a sandbox login, and a PDF. We thought
          you should be able to walk into a fully populated library and just look
          around. So we built one. Population: fictional. Software: real.
        </p>
        <p className="text-base text-lsc-dark/80 dark:text-lsc-cream/90 leading-relaxed">
          Every claim Little Schitt Creek makes, a real library could make:
        </p>
        <ul className="space-y-3 text-base text-lsc-dark/80 dark:text-lsc-cream/90">
          <li>
            <strong className="text-lsc-dark dark:text-lsc-cream">Own your digital collection</strong>{' '}
            instead of renting it back at 3-5x consumer price
          </li>
          <li>
            <strong className="text-lsc-dark dark:text-lsc-cream">Cancel the subscription stack.</strong>{' '}
            Scheduling, events, room booking, reading programs, LMS, all included
          </li>
          <li>
            <strong className="text-lsc-dark dark:text-lsc-cream">Keep patron data in the building.</strong>{' '}
            No cloud, no vendor, no tracking
          </li>
          <li>
            <strong className="text-lsc-dark dark:text-lsc-cream">Run it without special infrastructure</strong>,
            on modest hardware
          </li>
        </ul>
      </section>

      <hr className="border-lsc-border dark:border-earth-700 my-10" />

      {/* Who built it */}
      <section className="space-y-4">
        <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
          Who built it
        </h2>
        <p className="text-base text-lsc-dark/80 dark:text-lsc-cream/90 leading-relaxed">
          A librarian. Twenty years in library technology, including years inside
          the vendors libraries depend on. The system is AGPL-licensed and ships
          with full documentation and an AI maintenance agent, so it doesn&rsquo;t
          depend on its builder. Or on you having an IT department.
        </p>
      </section>

      <hr className="border-lsc-border dark:border-earth-700 my-10" />

      {/* What happens next */}
      <section className="space-y-4">
        <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
          What happens next
        </h2>
        <p className="text-base text-lsc-dark/80 dark:text-lsc-cream/90 leading-relaxed">
          L30 is recruiting pilot libraries: small public libraries serving
          50,000 people or fewer, willing to be first.
        </p>
        <p className="text-base text-lsc-dark/80 dark:text-lsc-cream/90 leading-relaxed">
          No platform fee. No contract. Three real costs: staff time, a server you
          can rely on, and your honest feedback.
        </p>
        <p className="text-base font-medium text-lsc-dark dark:text-lsc-cream leading-relaxed">
          The first libraries in make it real for everyone who comes after.
        </p>

        <div className="flex flex-wrap gap-3 pt-2">
          <Link
            to="/contact"
            className="inline-flex items-center px-5 py-2.5 rounded-lg bg-lsc-rose text-white text-sm font-semibold hover:bg-lsc-rose/90 transition-colors"
          >
            Join the pilot
          </Link>
          <Link
            to="/"
            className="inline-flex items-center px-5 py-2.5 rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream text-sm font-semibold hover:bg-earth-100 dark:hover:bg-earth-700 transition-colors"
          >
            Tour Little Schitt Creek again
          </Link>
        </div>
      </section>

      <hr className="border-lsc-border dark:border-earth-700 my-10" />

      <p className="text-xs italic text-lsc-dark/50 dark:text-lsc-cream/50 leading-relaxed">
        Little Schitt Creek is a fictional demonstration library. All patron names,
        quotes, and statistics are illustrative. The software is real, open source,
        and available at l30.org.
      </p>
    </PageContainer>
  )
}
