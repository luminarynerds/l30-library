/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Loader2, Settings } from 'lucide-react'
import toast from 'react-hot-toast'
import { useAuth } from '../../contexts/AuthContext'
import { useTranslation } from '@/i18n'
import { CalendarSubscribeCard } from './CalendarSubscribeCard'
import { ProfileEditSection } from './ProfileEditSection'

export function SettingsTab(): React.ReactElement {
  const { t } = useTranslation()
  const { user, updateProfile } = useAuth()
  const [isSavingPrivacy, setIsSavingPrivacy] = useState(false)
  const [isSavingAggregate, setIsSavingAggregate] = useState(false)

  return (
    <div>
      <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-6">{t('account.accountSettings')}</h2>
      <div className="space-y-4">
        <ProfileEditSection />
        <div className="p-4 bg-lsc-cream dark:bg-earth-800 rounded-xl">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2">{t('account.privacy')}</h3>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/80 mb-3">{t('account.controlYourReadingHistoryAnd')}</p>
          <label className={`flex items-center space-x-3 ${isSavingPrivacy ? 'cursor-wait opacity-70' : 'cursor-pointer'}`}>
            <input
              type="checkbox"
              checked={user?.track_reading_history || false}
              disabled={isSavingPrivacy}
              aria-label={t('account.trackMyReadingHistory')}
              onChange={async (e) => {
                setIsSavingPrivacy(true)
                try {
                  await updateProfile({ track_reading_history: e.target.checked })
                  toast.success(e.target.checked ? t('account.readingHistoryEnabled') : t('account.readingHistoryDisabled'))
                } catch (_err) {
                  toast.error(t('account.failedToUpdatePrivacySettings'))
                } finally {
                  setIsSavingPrivacy(false)
                }
              }}
              className="w-5 h-5 text-lsc-rose border-sage/30 rounded focus:ring-lsc-cream disabled:opacity-50"
            />
            <div className="flex items-center gap-2">
              <div>
                <div className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">{t('account.trackMyReadingHistory')}</div>
                <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/80">{t('account.whenEnabledYourCheckoutHistory')}</div>
              </div>
              {isSavingPrivacy && <Loader2 className="w-4 h-4 motion-safe:animate-spin text-lsc-dark/70 dark:text-lsc-cream/60" />}
            </div>
          </label>

          <label className={`flex items-center space-x-3 mt-4 ${isSavingAggregate ? 'cursor-wait opacity-70' : 'cursor-pointer'}`}>
            <input
              type="checkbox"
              checked={user?.aggregate_recommendations_opt_out || false}
              disabled={isSavingAggregate}
              aria-label="Exclude my activity from aggregate recommendations"
              onChange={async (e) => {
                setIsSavingAggregate(true)
                try {
                  await updateProfile({ aggregate_recommendations_opt_out: e.target.checked })
                  toast.success(e.target.checked ? 'Excluded from aggregate recommendations' : 'Included in aggregate recommendations')
                } catch (_err) {
                  toast.error(t('account.failedToUpdatePrivacySettings'))
                } finally {
                  setIsSavingAggregate(false)
                }
              }}
              className="w-5 h-5 text-lsc-rose border-sage/30 rounded focus:ring-lsc-cream disabled:opacity-50"
            />
            <div className="flex items-center gap-2">
              <div>
                <div className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">Exclude my activity from aggregate recommendations</div>
                <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/80">When enabled, your checkouts and returns are not counted in the anonymous &quot;what neighbors are reading&quot; rails on /discover.</div>
              </div>
              {isSavingAggregate && <Loader2 className="w-4 h-4 motion-safe:animate-spin text-lsc-dark/70 dark:text-lsc-cream/60" />}
            </div>
          </label>
        </div>
        <div className="p-4 bg-lsc-cream dark:bg-earth-800 rounded-xl">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2">Accessibility</h3>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/80 mb-3">Customize text size, contrast, motion, and other display preferences.</p>
          <Link
            to="/accessibility/settings"
            className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors text-sm font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2"
          >
            <Settings className="w-4 h-4" aria-hidden="true" />
            Accessibility settings
          </Link>
        </div>
        <CalendarSubscribeCard />
      </div>
    </div>
  )
}
