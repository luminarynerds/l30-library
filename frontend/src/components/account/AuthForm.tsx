/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { User, LogIn, UserPlus, Loader2, Eye, EyeOff } from 'lucide-react'
import toast from 'react-hot-toast'
import { useAuth } from '../../contexts/AuthContext'
import { useTranslation } from '@/i18n'
import { TurnstileWidget } from '@/components/TurnstileWidget'

type AuthMode = 'login' | 'register'

export function AuthForm(): React.ReactElement {
  const { t } = useTranslation()
  const { login, register } = useAuth()
  const [mode, setMode] = useState<AuthMode>('login')
  const [showPassword, setShowPassword] = useState(false)
  const [formData, setFormData] = useState({ email: '', password: '', first_name: '', last_name: '' })
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [turnstileToken, setTurnstileToken] = useState('')

  const handleAuthSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)
    try {
      if (mode === 'login') {
        await login(formData.email, formData.password, turnstileToken || undefined)
        toast.success(t('account.loggedInSuccess'))
      } else {
        await register({ email: formData.email, password: formData.password, first_name: formData.first_name, last_name: formData.last_name, turnstile_token: turnstileToken || undefined })
        toast.success(t('account.accountCreatedSuccess'))
      }
      setFormData({ email: '', password: '', first_name: '', last_name: '' })
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t('account.authFailed'))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen bg-cream dark:bg-lsc-dark py-12 px-4">
      <div className="max-w-md mx-auto">
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-md p-8">
          <div className="flex items-center justify-center mb-6">
            <User className="w-12 h-12 text-lsc-dark/70 dark:text-lsc-cream/70" />
          </div>
          <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream text-center mb-6">
            {mode === 'login' ? t('account.signIn') : t('account.createAccount')}
          </h2>

          <form onSubmit={handleAuthSubmit} className="space-y-4">
            {mode === 'register' && (
              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">{t('account.firstName')}</label>
                <input
                  type="text"
                  placeholder={t('account.yourFirstName')}
                  value={formData.first_name}
                  onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                  className="w-full px-4 py-2 bg-lsc-white dark:bg-earth-900 border border-lsc-border dark:border-earth-600 rounded-xl text-lsc-dark dark:text-lsc-cream placeholder-lsc-dark/50 dark:placeholder-lsc-cream/50 focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                  required
                />
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">{t('account.email')}</label>
              <input
                type="email"
                placeholder={t('account.yourEmail')}
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                className="w-full px-4 py-2 bg-lsc-white dark:bg-earth-900 border border-lsc-border dark:border-earth-600 rounded-xl text-lsc-dark dark:text-lsc-cream placeholder-lsc-dark/50 dark:placeholder-lsc-cream/50 focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">{t('account.password')}</label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  placeholder={t('placeholder.account.input')}
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  className="w-full px-4 py-2 bg-lsc-white dark:bg-earth-900 border border-lsc-border dark:border-earth-600 rounded-xl text-lsc-dark dark:text-lsc-cream placeholder-lsc-dark/50 dark:placeholder-lsc-cream/50 focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? t('account.hidePassword') : t('account.showPassword')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>

            <TurnstileWidget onVerify={setTurnstileToken} />

            <button
              type="submit"
              disabled={isSubmitting || (mode === 'login' && !turnstileToken)}
              className="w-full bg-lsc-rose text-white py-2 rounded-xl hover:bg-lsc-rose transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {isSubmitting ? (
                <Loader2 className="w-5 h-5 motion-safe:animate-spin" />
              ) : mode === 'login' ? (
                <>
                  <LogIn className="w-5 h-5" />
                  {t('account.signIn')}
                </>
              ) : (
                <>
                  <UserPlus className="w-5 h-5" />
                  {t('account.createAccount')}
                </>
              )}
            </button>
          </form>

          <div className="mt-4 text-center">
            <button
              onClick={() => setMode(mode === 'login' ? 'register' : 'login')}
              className="text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream text-sm"
            >
              {mode === 'login' ? t('account.dontHaveAccount') : t('account.alreadyHaveAccount')}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
