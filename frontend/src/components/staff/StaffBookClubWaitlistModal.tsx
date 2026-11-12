/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Loader2, Trash2, Users } from 'lucide-react'
import toast from 'react-hot-toast'
import { Modal } from '../ui/Modal'
import { getAccessToken } from '@/utils/tokenStore'
import { t } from '@/i18n'
import {
  getBookClubWaitlist,
  removeBookClubWaitlistEntry,
} from '@/api/domains/content/book-clubs-api'

interface Props {
  clubId: number
  clubName: string
  onClose: () => void
}

export function StaffBookClubWaitlistModal({ clubId, clubName, onClose }: Props) {
  const queryClient = useQueryClient()
  const [removingId, setRemovingId] = useState<number | null>(null)

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['staff-book-club-waitlist', clubId],
    queryFn: () => getBookClubWaitlist(clubId, getAccessToken() ?? undefined),
  })

  const entries = data?.entries ?? []

  const handleRemove = async (userId: number, name: string) => {
    setRemovingId(userId)
    try {
      await removeBookClubWaitlistEntry(
        clubId,
        userId,
        getAccessToken() ?? undefined,
      )
      toast.success(t('staffBookClubs.waitlist.removed', { name }))
      await refetch()
      // Member/capacity counts on the list are unaffected by a waitlist
      // removal, but invalidate so a future "X waiting" surface stays fresh.
      queryClient.invalidateQueries({ queryKey: ['staff-book-clubs'] })
    } catch {
      toast.error(t('staffBookClubs.waitlist.removeError'))
    } finally {
      setRemovingId(null)
    }
  }

  return (
    <Modal
      isOpen={true}
      onClose={onClose}
      title={t('staffBookClubs.waitlist.title', { club: clubName })}
      size='2xl'
    >
      <div className='space-y-4'>
        <p className='text-xs text-earth-600 dark:text-earth-400'>
          {t('staffBookClubs.waitlist.fifoNote')}
        </p>

        {isLoading ? (
          <div
            className='flex justify-center py-12'
            role='status'
            aria-label={t('staffBookClubs.waitlist.title', { club: clubName })}
          >
            <Loader2 className='w-7 h-7 motion-safe:animate-spin text-lsc-gold' />
          </div>
        ) : isError ? (
          <div className='py-10 text-center'>
            <p className='text-sm text-status-danger-700 dark:text-status-danger-300'>
              {t('staffBookClubs.waitlist.loadError')}
            </p>
          </div>
        ) : entries.length === 0 ? (
          <div className='py-12 text-center text-earth-600 dark:text-earth-400'>
            <Users className='w-10 h-10 mx-auto mb-2 opacity-40' aria-hidden='true' />
            <p className='text-sm'>{t('staffBookClubs.waitlist.empty')}</p>
          </div>
        ) : (
          <div className='overflow-x-auto rounded-lg border border-lsc-border dark:border-earth-700'>
            <table className='w-full text-left text-sm'>
              <caption className='sr-only'>
                {t('staffBookClubs.waitlist.title', { club: clubName })}
              </caption>
              <thead className='bg-earth-50 dark:bg-earth-900'>
                <tr>
                  <th scope='col' className='px-3 py-2 text-xs font-medium text-earth-600 dark:text-earth-400 uppercase w-12'>
                    {t('staffBookClubs.waitlist.colPosition')}
                  </th>
                  <th scope='col' className='px-3 py-2 text-xs font-medium text-earth-600 dark:text-earth-400 uppercase'>
                    {t('staffBookClubs.waitlist.colName')}
                  </th>
                  <th scope='col' className='px-3 py-2 text-xs font-medium text-earth-600 dark:text-earth-400 uppercase'>
                    {t('staffBookClubs.waitlist.colEmail')}
                  </th>
                  <th scope='col' className='px-3 py-2 text-xs font-medium text-earth-600 dark:text-earth-400 uppercase'>
                    {t('staffBookClubs.waitlist.colJoined')}
                  </th>
                  <th scope='col' className='px-3 py-2 text-xs font-medium text-earth-600 dark:text-earth-400 uppercase text-right'>
                    {t('staffBookClubs.waitlist.colActions')}
                  </th>
                </tr>
              </thead>
              <tbody>
                {entries.map((entry) => (
                  <tr
                    key={entry.id}
                    className='border-t border-earth-100 dark:border-earth-700'
                  >
                    <td className='px-3 py-2 tabular-nums text-earth-600 dark:text-earth-400'>
                      {entry.position}
                    </td>
                    <td className='px-3 py-2 font-medium text-lsc-dark dark:text-lsc-cream'>
                      {entry.display_name}
                    </td>
                    <td className='px-3 py-2 text-earth-600 dark:text-earth-400'>
                      {entry.email ?? '--'}
                    </td>
                    <td className='px-3 py-2 text-earth-600 dark:text-earth-400'>
                      {entry.created_at
                        ? new Date(entry.created_at).toLocaleDateString()
                        : '--'}
                    </td>
                    <td className='px-3 py-2 text-right'>
                      <button
                        type='button'
                        onClick={() =>
                          handleRemove(entry.user_id, entry.display_name)
                        }
                        disabled={removingId === entry.user_id}
                        aria-label={t('staffBookClubs.waitlist.removeLabel', {
                          name: entry.display_name,
                        })}
                        className='inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-status-danger-700 dark:text-status-danger-300 hover:bg-status-danger-50 dark:hover:bg-status-danger-900/20 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose disabled:opacity-50'
                      >
                        {removingId === entry.user_id ? (
                          <Loader2 className='w-3.5 h-3.5 motion-safe:animate-spin' />
                        ) : (
                          <Trash2 className='w-3.5 h-3.5' aria-hidden='true' />
                        )}
                        {t('staffBookClubs.waitlist.remove')}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className='flex justify-end pt-2'>
          <button
            type='button'
            onClick={onClose}
            className='px-4 py-2 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg hover:bg-earth-50 dark:hover:bg-earth-700 transition-colors'
          >
            {t('staffBookClubs.waitlist.close')}
          </button>
        </div>
      </div>
    </Modal>
  )
}
