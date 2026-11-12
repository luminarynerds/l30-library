/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Link, useLocation } from 'react-router-dom'
import { Baby, BookOpen, Code2, Users, Archive } from 'lucide-react'
import clsx from 'clsx'
import PageContainer from '@/components/layout/PageContainer'

const YOUTH_NAV_ITEMS = [
  { href: '/youth', label: 'Hub', icon: Baby },
  { href: '/youth/homework-help', label: 'Homework Help', icon: BookOpen },
  { href: '/youth/coding-tracks', label: 'Coding', icon: Code2 },
  { href: '/youth/teen-mentors', label: 'Mentors', icon: Users },
  { href: '/youth/archives', label: 'Archives', icon: Archive },
]

export default function YouthSubNav() {
  const { pathname } = useLocation()

  return (
    <nav
      className="sticky top-16 z-30 bg-lsc-white/95 dark:bg-earth-800/95 backdrop-blur-sm border-b border-lsc-border dark:border-earth-700"
      aria-label="Youth programs"
    >
      <PageContainer>
        <ul className="flex gap-1 overflow-x-auto scrollbar-hide py-2 -mx-4 px-4">
          {YOUTH_NAV_ITEMS.map(({ href, label, icon: Icon }) => {
            const isActive = pathname === href || (href !== '/youth' && pathname.startsWith(href))
            return (
              <li key={href}>
                <Link
                  to={href}
                  className={clsx(
                    'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium whitespace-nowrap transition-colors',
                    isActive
                      ? 'bg-lsc-rose text-white'
                      : 'text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700/50 hover:text-lsc-dark dark:hover:text-lsc-cream'
                  )}
                >
                  <Icon aria-hidden="true" className="w-4 h-4" />
                  {label}
                </Link>
              </li>
            )
          })}
        </ul>
      </PageContainer>
    </nav>
  )
}
