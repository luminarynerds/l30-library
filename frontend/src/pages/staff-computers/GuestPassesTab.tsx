/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Loader2, Ticket } from 'lucide-react'
import { t } from '@/i18n'
import type { GuestPass } from '@/types/computer'
import { GuestPassForm, type GuestPassFormData } from '@/features/computers/GuestPassForm'

interface GuestPassesTabProps {
  passes: GuestPass[]
  loading: boolean
  creating: boolean
  onCreate: (data: GuestPassFormData) => Promise<void>
}

export function GuestPassesTab({ passes, loading, creating, onCreate }: GuestPassesTabProps) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div>
        <GuestPassForm onSubmit={onCreate} isLoading={creating} />
      </div>
      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-6">
        <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
          <Ticket aria-hidden="true" className="w-5 h-5" />
          Recent guest passes
        </h2>
        {loading && passes.length === 0 ? (
          <div className="flex justify-center py-8">
            <Loader2 className="w-5 h-5 motion-safe:animate-spin text-lsc-rose" />
          </div>
        ) : passes.length === 0 ? (
          <div className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/60">
            <Ticket className="w-10 h-10 mx-auto mb-3 opacity-50" />
            <p>No active guest passes</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="text-xs uppercase text-lsc-dark/60 dark:text-lsc-cream/60 border-b border-lsc-border dark:border-earth-700">
                <tr>
                  <th className="text-left py-2 pr-3 font-medium">{t('computers.recentPasses.passCode')}</th>
                  <th className="text-left py-2 pr-3 font-medium">{t('computers.recentPasses.guestName')}</th>
                  <th className="text-left py-2 pr-3 font-medium">{t('computers.recentPasses.sessions')}</th>
                  <th className="text-left py-2 font-medium">{t('computers.recentPasses.issued')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-lsc-border/60 dark:divide-earth-700/60">
                {passes.map(pass => {
                  const remaining = Math.max(pass.max_sessions - pass.sessions_used, 0)
                  return (
                    <tr key={pass.id} className="hover:bg-lsc-cream/30 dark:hover:bg-earth-700/30">
                      <td className="py-2 pr-3 font-mono text-lsc-dark dark:text-lsc-cream">{pass.pass_code}</td>
                      <td className="py-2 pr-3 text-lsc-dark dark:text-lsc-cream">{pass.guest_name}</td>
                      <td className="py-2 pr-3 text-lsc-dark/70 dark:text-lsc-cream/70">{remaining} / {pass.max_sessions}</td>
                      <td className="py-2 text-lsc-dark/70 dark:text-lsc-cream/70 text-xs">
                        {new Date(pass.issued_at).toLocaleDateString()}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
