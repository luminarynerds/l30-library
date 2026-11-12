/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Modal } from '@/components/ui/Modal'
import { clsx } from '@/utils/helpers'
import type { CatalogItem } from '@/api/api'

interface WayfindingModalProps {
  isOpen: boolean
  onClose: () => void
  item: CatalogItem
  reduceMotion: boolean
}

// Map Dewey hundreds to section names and grid positions
const DEWEY_SECTIONS: { range: [number, number]; name: string; code: string }[] = [
  { range: [0, 99], name: 'Reference & General', code: '000' },
  { range: [100, 199], name: 'Philosophy & Psychology', code: '100' },
  { range: [200, 299], name: 'Religion & Spirituality', code: '200' },
  { range: [300, 399], name: 'Social Sciences', code: '300' },
  { range: [400, 499], name: 'Languages', code: '400' },
  { range: [500, 599], name: 'Science & Math', code: '500' },
  { range: [600, 699], name: 'Technology', code: '600' },
  { range: [700, 799], name: 'Arts & Recreation', code: '700' },
  { range: [800, 899], name: 'Literature', code: '800' },
  { range: [900, 999], name: 'History & Geography', code: '900' },
]

const SPECIAL_SECTIONS: Record<string, string> = {
  FIC: 'Fiction',
  JUV: 'Juvenile',
  YA: 'Young Adult',
  REF: 'Reference',
  LP: 'Large Print',
  AV: 'Audio/Visual',
  PER: 'Periodicals',
}

function getSection(item: CatalogItem): { name: string; code: string } {
  // Check call number for special sections
  const callNum = item.call_number?.toUpperCase().trim() ?? ''
  for (const [prefix, name] of Object.entries(SPECIAL_SECTIONS)) {
    if (callNum.startsWith(prefix)) return { name, code: prefix }
  }

  // Try Dewey decimal
  const dewey = item.dewey_decimal ?? callNum
  const deweyNum = parseInt(dewey, 10)
  if (!isNaN(deweyNum)) {
    const section = DEWEY_SECTIONS.find(
      (s) => deweyNum >= s.range[0] && deweyNum <= s.range[1]
    )
    if (section) return { name: section.name, code: section.code }
  }

  // Fallback by item type
  if (['dvd', 'bluray', 'cd', 'vinyl'].includes(item.item_type)) return { name: 'Audio/Visual', code: 'AV' }
  if (['game'].includes(item.item_type)) return { name: 'Gaming', code: 'GAME' }
  if (['magazine'].includes(item.item_type)) return { name: 'Periodicals', code: 'PER' }

  return { name: 'General Collection', code: 'GEN' }
}

function getBranchName(item: CatalogItem): string {
  const rawLocation = item.location?.trim() || ''
  const tokens = rawLocation.split(' - ').map((t) => t.trim()).filter(Boolean)
  return tokens[0] || 'Main Branch'
}

function getAuthorSort(item: CatalogItem): string {
  if (!item.author) return ''
  const parts = item.author.split(/[,\s]+/).filter(Boolean)
  return parts[0]?.toUpperCase() ?? ''
}

// Floor map sections in grid layout
const MAP_AREAS = [
  { code: 'ENTRANCE', label: 'Entrance', row: 4, col: 2 },
  { code: '000', label: 'Reference', row: 1, col: 1 },
  { code: 'FIC', label: 'Fiction', row: 1, col: 3 },
  { code: '100', label: 'Philosophy', row: 2, col: 1 },
  { code: '200', label: 'Religion', row: 2, col: 2 },
  { code: '300', label: 'Social Sci', row: 2, col: 3 },
  { code: '400', label: 'Languages', row: 3, col: 1 },
  { code: '500', label: 'Science', row: 1, col: 2 },
  { code: '600', label: 'Technology', row: 3, col: 2 },
  { code: '700', label: 'Arts', row: 3, col: 3 },
  { code: '800', label: 'Literature', row: 1, col: 4 },
  { code: '900', label: 'History', row: 2, col: 4 },
  { code: 'JUV', label: 'Juvenile', row: 3, col: 4 },
  { code: 'YA', label: 'Young Adult', row: 4, col: 4 },
  { code: 'AV', label: 'Audio/Visual', row: 4, col: 1 },
  { code: 'PER', label: 'Periodicals', row: 4, col: 3 },
  { code: 'LP', label: 'Large Print', row: 4, col: 4 },
  { code: 'REF', label: 'Reference', row: 1, col: 1 },
  { code: 'GEN', label: 'General', row: 2, col: 2 },
  { code: 'GAME', label: 'Gaming', row: 3, col: 4 },
]

export function WayfindingModal({ isOpen, onClose, item, reduceMotion }: WayfindingModalProps): React.ReactElement {
  const section = getSection(item)
  const branchName = getBranchName(item)
  const authorSort = getAuthorSort(item)

  const directions = [
    `Enter through the main entrance at ${branchName}.`,
    `Head to the ${section.name} area.`,
    item.call_number ? `Look for the shelf labeled ${item.call_number}.` : `Browse the ${section.name} shelves.`,
    authorSort ? `Your item is filed under ${authorSort}.` : 'Ask staff for help locating this item.',
  ]

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={`Find "${item.title}"`} size="xl">
      <div className="flex flex-col md:flex-row gap-6">
        {/* Floor map */}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-3">{branchName} Floor Map</p>
          <div className="grid grid-cols-4 grid-rows-4 gap-1.5 aspect-square max-w-[320px]">
            {MAP_AREAS.filter((a, i, arr) => arr.findIndex((b) => `${b.row}-${b.col}` === `${a.row}-${a.col}`) === i).map((area) => {
              const isTarget = MAP_AREAS.some((b) => b.row === area.row && b.col === area.col && b.code === section.code)
              return (
                <div
                  key={`${area.row}-${area.col}`}
                  className={clsx(
                    'rounded-lg flex items-center justify-center text-center p-1 text-[10px] font-medium leading-tight border transition-colors',
                    area.code === 'ENTRANCE'
                      ? 'bg-earth-200 dark:bg-earth-600 text-earth-800 dark:text-earth-100 border-lsc-border dark:border-earth-700'
                      : isTarget
                        ? [
                            'bg-lsc-rose/20 dark:bg-lsc-rose/30 border-lsc-rose text-lsc-rose dark:text-lsc-rose-light font-bold ring-2 ring-lsc-rose/40',
                            !reduceMotion && 'motion-safe:animate-pulse',
                          ]
                        : 'bg-lsc-cream/60 dark:bg-earth-700/60 text-lsc-dark/70 dark:text-lsc-cream/70 border-lsc-border/30 dark:border-earth-700/30'
                  )}
                  style={{ gridRow: area.row, gridColumn: area.col }}
                  aria-label={`${area.label}${isTarget ? ' (your item is here)' : ''}`}
                >
                  {area.label}
                </div>
              )
            })}
          </div>
        </div>

        {/* Directions */}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-3">Step-by-step directions</p>
          <ol className="space-y-3">
            {directions.map((step, idx) => (
              <li key={idx} className="flex gap-3 text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-lsc-rose text-white flex items-center justify-center text-xs font-bold">
                  {idx + 1}
                </span>
                <span className="pt-0.5">{step}</span>
              </li>
            ))}
          </ol>

          {item.call_number && (
            <div className="mt-4 p-3 bg-lsc-cream/50 dark:bg-lsc-dark/50 rounded-lg">
              <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80">Call Number</p>
              <p className="text-lg font-mono font-bold text-lsc-dark dark:text-lsc-cream">{item.call_number}</p>
            </div>
          )}
        </div>
      </div>
    </Modal>
  )
}
