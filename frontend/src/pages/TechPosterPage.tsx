/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * TechPosterPage
 *
 * Staff-only tool for generating physical QR-code posters/stickers that
 * point patrons at /tech triage flows or directly at a specific guide.
 *
 * Two QR target patterns (decided up-front):
 *  1. Per-context QR — sticker tied to a physical location (e.g. by the
 *     printer). Encodes a direct guide URL like
 *     `https://l30.org/guides/wireless-printing`. Bypasses /tech because
 *     the sticker's location already scopes the problem.
 *  2. Generic QR — service desk, card sleeve, anywhere the patron's
 *     problem isn't yet known. Encodes the triage launchpad
 *     `https://l30.org/tech` or `https://l30.org/tech?p=<password|login|printer|wifi>`
 *     for pre-scoping.
 *
 * Staff page; English-only copy is intentional.
 */
import { useMemo, useState } from 'react'
import { QRCodeSVG } from 'qrcode.react'
import { Printer, QrCode } from 'lucide-react'
import { useTranslation } from '@/i18n'

import StandardPageLayout from '@/components/StandardPageLayout'
import { GUIDES } from '@/pages/guides/_data'
import { QR_PARAM_TO_GUIDE_ID, type QrParam } from '@/pages/TechSupportPage'
import { buildQrTargetUrl, type QrDestinationKind } from '@/pages/_qrSlug'

type DestinationKind = QrDestinationKind

interface Destination {
  key: string
  kind: DestinationKind
  /** Path appended to window.location.origin to form the QR target URL. */
  path: string
  label: string
  caption: string
}

const TRIAGE_LABELS: Record<QrParam, string> = {
  password: 'Password help',
  login: 'Library card / login help',
  printer: 'Printing help',
  wifi: 'WiFi help',
}

const TRIAGE_CAPTIONS: Record<QrParam, string> = {
  password: 'Tech help: password',
  login: 'Tech help: library card',
  printer: 'Tech help: printing',
  wifi: 'Tech help: WiFi',
}

/**
 * Legal-help destinations.
 *
 * /legal/wizard is intentionally omitted — it's auth-gated, so a QR-scanning
 * patron would land on a login redirect, which is worse UX than not surfacing
 * the destination.
 */
const LEGAL_DESTINATIONS: ReadonlyArray<Omit<Destination, 'kind'>> = [
  {
    key: 'legal-main',
    path: '/legal',
    label: 'Legal Help (main page)',
    caption: 'Free legal info, forms, and clinics.',
  },
  {
    key: 'legal-calculators',
    path: '/legal/calculators',
    label: 'Legal calculators',
    caption: 'Self-help calculators for fees, deadlines, and filings.',
  },
]

function buildDestinations(guideLabels: Record<string, string>): Destination[] {
  const launchpad: Destination = {
    key: 'launchpad',
    kind: 'launchpad',
    path: '/tech',
    label: 'Tech Help (general triage)',
    caption: 'Tech help',
  }

  const triage: Destination[] = (Object.keys(QR_PARAM_TO_GUIDE_ID) as QrParam[]).map((p) => ({
    key: `triage-${p}`,
    kind: 'triage',
    path: `/tech?p=${p}`,
    label: TRIAGE_LABELS[p],
    caption: TRIAGE_CAPTIONS[p],
  }))

  const guideDests: Destination[] = GUIDES.map((g) => ({
    key: `guide-${g.id}`,
    kind: 'guide',
    path: g.href,
    label: guideLabels[g.id] ?? g.id,
    caption: guideLabels[g.id] ?? g.id,
  }))

  const legal: Destination[] = LEGAL_DESTINATIONS.map((d) => ({
    ...d,
    kind: 'legal',
  }))

  return [launchpad, ...triage, ...guideDests, ...legal]
}

function DestinationCard({
  dest,
  selected,
  onClick,
}: {
  dest: Destination
  selected: boolean
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={selected}
      className={[
        'w-full min-h-[44px] text-left rounded-lg border px-4 py-3',
        'transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose',
        selected
          ? 'border-lsc-rose bg-lsc-rose/10 text-lsc-dark dark:text-lsc-cream'
          : 'border-earth-300 bg-lsc-cream hover:bg-earth-100 text-lsc-dark dark:border-earth-700 dark:bg-lsc-dark dark:text-lsc-cream dark:hover:bg-earth-900',
      ].join(' ')}
    >
      <span className="block font-medium">{dest.label}</span>
      <span className="block text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-0.5 break-all">
        {dest.path}
      </span>
    </button>
  )
}

export default function TechPosterPage(): React.ReactElement {
  const { t } = useTranslation()
  const [selectedKey, setSelectedKey] = useState<string>('launchpad')

  const guideLabels = useMemo(() => {
    const map: Record<string, string> = {}
    for (const g of GUIDES) {
      map[g.id] = t(g.titleKey, { defaultValue: g.id })
    }
    return map
  }, [t])

  const { launchpad, triageGroup, guideGroup, legalGroup, byKey } = useMemo(() => {
    const all = buildDestinations(guideLabels)
    const lp = all.find((d) => d.kind === 'launchpad')!
    return {
      launchpad: lp,
      triageGroup: all.filter((d) => d.kind === 'triage'),
      guideGroup: all.filter((d) => d.kind === 'guide'),
      legalGroup: all.filter((d) => d.kind === 'legal'),
      byKey: new Map(all.map((d) => [d.key, d])),
    }
  }, [guideLabels])

  const selected: Destination = byKey.get(selectedKey) ?? launchpad

  const origin = typeof window !== 'undefined' ? window.location.origin : ''
  // Encode a stable `qr=<slug>` so Umami can attribute the scan to this
  // specific sticker without us needing a separate beacon endpoint.
  const targetUrl = buildQrTargetUrl(origin, { kind: selected.kind, path: selected.path })

  return (
    <StandardPageLayout
      title="Help QR Poster"
      subtitle="Pick a tech-help or legal-help destination, then print a QR code poster or sticker for it."
      icon={QrCode}
    >
      <style>{`
        @media print {
          body * { visibility: hidden !important; }
          .tech-poster-print-area, .tech-poster-print-area * { visibility: visible !important; }
          .tech-poster-print-area { position: absolute; inset: 0; padding: 1in; }
        }
      `}</style>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6" data-testid="tech-poster-destinations">
          <section aria-labelledby="poster-launchpad-heading">
            <h2 id="poster-launchpad-heading" className="text-lg font-semibold mb-2">
              Quick triage launchpad
            </h2>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
              Generic sticker for service desk or card sleeves — patron scans, picks their issue on /tech.
            </p>
            <div className="grid grid-cols-1 gap-2">
              <DestinationCard
                dest={launchpad}
                selected={selected.key === launchpad.key}
                onClick={() => setSelectedKey(launchpad.key)}
              />
            </div>
          </section>

          <section aria-labelledby="poster-triage-heading">
            <h2 id="poster-triage-heading" className="text-lg font-semibold mb-2">
              Pre-scoped triage
            </h2>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
              Lands on /tech with the relevant topic announced — useful when the sticker location hints at the problem.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {triageGroup.map((d) => (
                <DestinationCard
                  key={d.key}
                  dest={d}
                  selected={selected.key === d.key}
                  onClick={() => setSelectedKey(d.key)}
                />
              ))}
            </div>
          </section>

          <section aria-labelledby="poster-guides-heading">
            <h2 id="poster-guides-heading" className="text-lg font-semibold mb-2">
              Direct to a guide
            </h2>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
              Place the sticker right at the thing it answers (e.g. wireless printing QR by the printer).
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {guideGroup.map((d) => (
                <DestinationCard
                  key={d.key}
                  dest={d}
                  selected={selected.key === d.key}
                  onClick={() => setSelectedKey(d.key)}
                />
              ))}
            </div>
          </section>

          <section aria-labelledby="poster-legal-heading">
            <h2 id="poster-legal-heading" className="text-lg font-semibold mb-2">
              Legal help
            </h2>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
              Stickers for the legal-resources shelf, clinic flyers, or court-forms binders.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {legalGroup.map((d) => (
                <DestinationCard
                  key={d.key}
                  dest={d}
                  selected={selected.key === d.key}
                  onClick={() => setSelectedKey(d.key)}
                />
              ))}
            </div>
          </section>
        </div>

        <aside aria-label="QR code preview" className="lg:col-span-1">
          <div className="sticky top-4">
            <div className="tech-poster-print-area rounded-lg border border-earth-300 dark:border-earth-700 bg-lsc-cream dark:bg-lsc-dark p-6 flex flex-col items-center gap-4">
              <h2 className="text-lg font-semibold text-center">{selected.caption}</h2>
              <div
                data-testid="tech-poster-qr"
                className="bg-white p-4 rounded"
                role="img"
                aria-label={`QR code for ${targetUrl}`}
              >
                <QRCodeSVG value={targetUrl} size={256} level="M" marginSize={2} />
              </div>
              <p
                data-testid="tech-poster-url"
                className="text-sm text-center break-all text-lsc-dark dark:text-lsc-cream"
              >
                {targetUrl}
              </p>
              <p className="text-xs text-center text-lsc-dark/70 dark:text-lsc-cream/70">
                Scan with a phone camera to test before printing.
              </p>
            </div>

            <button
              type="button"
              onClick={() => window.print()}
              className="mt-4 w-full min-h-[44px] inline-flex items-center justify-center gap-2 rounded-lg bg-lsc-rose text-white font-medium px-4 py-2 hover:bg-lsc-rose/90 focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2"
            >
              <Printer aria-hidden="true" className="w-4 h-4" />
              Print this poster
            </button>
          </div>
        </aside>
      </div>
    </StandardPageLayout>
  )
}
