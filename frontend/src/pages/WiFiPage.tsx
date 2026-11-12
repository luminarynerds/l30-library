/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Wifi, Smartphone, Laptop, Eye, EyeOff, Copy, Check, AlertCircle, HelpCircle } from 'lucide-react'
import { useState } from 'react'
import toast from 'react-hot-toast'
import { COPY_FEEDBACK_DURATION_MS } from '@/constants/timeouts'
import { t } from '@/i18n'
import { usePageTitle } from '@/hooks/usePageTitle'
import { useBranding } from '@/contexts/BrandingContext'
import PageContainer from '@/components/layout/PageContainer'

export default function WiFiPage() {
  const branding = useBranding()
  usePageTitle(
    t('wifiPage.pageTitle', 'Free WiFi'),
    t('wifiPage.pageDescription', { libraryShortName: branding.library_short_name })
  )
  const [showPassword, setShowPassword] = useState(false)
  const [copied, setCopied] = useState<'network' | 'password' | null>(null)

  const networkName = 'L30-Public'
  const password = 'LibraryWifi2026'
  const networkNameLabel = t('wifiPage.networkNameLabel', 'Network Name')
  const passwordLabel = t('wifiPage.passwordLabel', 'Password')

  const copyToClipboard = (text: string, id: 'network' | 'password', label: string) => {
    navigator.clipboard.writeText(text)
    setCopied(id)
    toast.success(t('toast.wiFi.copiedLabel', { label: label }))
    setTimeout(() => setCopied(null), COPY_FEEDBACK_DURATION_MS)
  }

  return (
    <PageContainer width="read" className="py-8">
      {/* Header */}
      <div className="mb-12">
        <div className="inline-flex items-center gap-3 mb-4">
          <div className="p-3 bg-lsc-rose/10 rounded-full">
            <Wifi className="w-8 h-8 text-lsc-rose" />
          </div>
          <h1 className="font-serif text-4xl font-bold text-lsc-dark dark:text-lsc-cream">{t('wifiPage.heading', 'Free High-Speed WiFi')}</h1>
        </div>
        <p className="text-lg text-lsc-dark/70 dark:text-lsc-cream/70">
          {t('wifiPage.intro', 'Connect to our library network and enjoy high-speed internet access from anywhere in the building.')}
        </p>
      </div>

      {/* Connection Info */}
      <div className="grid gap-6 mb-8">
        {/* Network Name */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">{networkNameLabel}</h2>
          <div className="flex items-center justify-between gap-4 p-4 bg-lsc-cream/50 dark:bg-earth-700/50 rounded-lg">
            <code className="font-mono text-lg text-lsc-dark dark:text-lsc-cream">{networkName}</code>
            <button
              onClick={() => copyToClipboard(networkName, 'network', networkNameLabel)}
              aria-label={t('wifiPage.copyNetworkNameAria', 'Copy network name')}
              className="p-2 hover:bg-lsc-border dark:hover:bg-earth-600 rounded-lg transition"
            >
              {copied === 'network' ? (
                <Check className="w-5 h-5 text-status-success-600" />
              ) : (
                <Copy className="w-5 h-5 text-lsc-rose" />
              )}
            </button>
          </div>
        </div>

        {/* Password */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">{passwordLabel}</h2>
          <div className="flex items-center justify-between gap-4 p-4 bg-lsc-cream/50 dark:bg-earth-700/50 rounded-lg">
            <code className="font-mono text-lg text-lsc-dark dark:text-lsc-cream">
              {showPassword ? password : '•'.repeat(password.length)}
            </code>
            <div className="flex gap-2">
              <button
                onClick={() => setShowPassword(!showPassword)}
                aria-label={showPassword ? t('account.hidePassword', 'Hide password') : t('account.showPassword', 'Show password')}
                className="p-2 hover:bg-lsc-border dark:hover:bg-earth-600 rounded-lg transition"
              >
                {showPassword ? (
                  <EyeOff className="w-5 h-5 text-lsc-rose" />
                ) : (
                  <Eye className="w-5 h-5 text-lsc-rose" />
                )}
              </button>
              <button
                onClick={() => copyToClipboard(password, 'password', passwordLabel)}
                aria-label={t('wifiPage.copyPasswordAria', 'Copy password')}
                className="p-2 hover:bg-lsc-border dark:hover:bg-earth-600 rounded-lg transition"
              >
                {copied === 'password' ? (
                  <Check className="w-5 h-5 text-status-success-600" />
                ) : (
                  <Copy className="w-5 h-5 text-lsc-rose" />
                )}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Connection Guide */}
      <div className="bg-lsc-cream/30 dark:bg-lsc-dark/30 rounded-xl p-6 mb-8 border border-lsc-border dark:border-earth-700">
        <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-6">{t('wifiPage.howToConnectHeading', 'How to Connect')}</h2>

        <div className="space-y-6">
          {/* iPhone/iPad */}
          <div className="border-l-4 border-lsc-rose pl-4">
            <div className="flex items-center gap-2 mb-3">
              <Smartphone className="w-5 h-5 text-lsc-rose" />
              <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{t('wifiPage.iphoneIpad', 'iPhone/iPad')}</h3>
            </div>
            <ol className="space-y-2 text-lsc-dark/80 dark:text-lsc-cream/80 text-sm">
              <li>{t('wifiPage.iphoneStep1', '1. Open Settings → WiFi')}</li>
              <li>{t('wifiPage.iphoneStep2', '2. Select "L30-Public" from the network list')}</li>
              <li>{t('wifiPage.iphoneStep3', '3. Enter the password when prompted')}</li>
              <li>{t('wifiPage.iphoneStep4', "4. You're connected! 🎉")}</li>
            </ol>
          </div>

          {/* Android */}
          <div className="border-l-4 border-lsc-rose pl-4">
            <div className="flex items-center gap-2 mb-3">
              <Smartphone className="w-5 h-5 text-lsc-rose" />
              <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{t('wifiPage.android', 'Android Phone/Tablet')}</h3>
            </div>
            <ol className="space-y-2 text-lsc-dark/80 dark:text-lsc-cream/80 text-sm">
              <li>{t('wifiPage.androidStep1', '1. Open Settings → WiFi')}</li>
              <li>{t('wifiPage.androidStep2', '2. Tap "L30-Public" from the available networks')}</li>
              <li>{t('wifiPage.androidStep3', '3. Enter the password')}</li>
              <li>{t('wifiPage.androidStep4', '4. Tap "Connect"')}</li>
            </ol>
          </div>

          {/* Laptop/Computer */}
          <div className="border-l-4 border-lsc-rose pl-4">
            <div className="flex items-center gap-2 mb-3">
              <Laptop className="w-5 h-5 text-lsc-rose" />
              <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{t('wifiPage.desktop', 'Windows/Mac/Linux')}</h3>
            </div>
            <ol className="space-y-2 text-lsc-dark/80 dark:text-lsc-cream/80 text-sm">
              <li>{t('wifiPage.desktopStep1', '1. Click the WiFi icon in your system tray/menu bar')}</li>
              <li>{t('wifiPage.desktopStep2', '2. Select "L30-Public"')}</li>
              <li>{t('wifiPage.desktopStep3', '3. Enter the password')}</li>
              <li>{t('wifiPage.desktopStep4', '4. Open your browser - you may see a login page (optional)')}</li>
            </ol>
          </div>
        </div>
      </div>

      {/* Troubleshooting */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
        <div className="flex items-center gap-2 mb-6">
          <AlertCircle className="w-6 h-6 text-lsc-rose" />
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">{t('wifiPage.troubleshootingHeading', 'Troubleshooting')}</h2>
        </div>

        <div className="space-y-4">
          <details className="border-b border-lsc-border dark:border-earth-700 pb-4">
            <summary className="font-semibold text-lsc-dark dark:text-lsc-cream cursor-pointer hover:text-lsc-rose">
              {t('wifiPage.q1', "Can't see the WiFi network?")}
            </summary>
            <p className="mt-3 text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">
              {t('wifiPage.a1', "Try turning WiFi off and back on, or restart your device. If the network still doesn't appear, ask a staff member at the front desk - we may be experiencing a technical issue.")}
            </p>
          </details>

          <details className="border-b border-lsc-border dark:border-earth-700 pb-4">
            <summary className="font-semibold text-lsc-dark dark:text-lsc-cream cursor-pointer hover:text-lsc-rose">
              {t('wifiPage.q2', 'Wrong password error?')}
            </summary>
            <p className="mt-3 text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">
              {t('wifiPage.a2', "Double-check the password is entered exactly as shown above. Passwords are case-sensitive. If you're still having trouble, visit the front desk or tech support area.")}
            </p>
          </details>

          <details className="border-b border-lsc-border dark:border-earth-700 pb-4">
            <summary className="font-semibold text-lsc-dark dark:text-lsc-cream cursor-pointer hover:text-lsc-rose">
              {t('wifiPage.q3', 'Connected but no internet?')}
            </summary>
            <p className="mt-3 text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">
              {t('wifiPage.a3', 'Try "forgetting" the network and reconnecting. Or restart your device. If the problem persists, speak with our tech support staff - they can help diagnose the issue.')}
            </p>
          </details>

          <details className="border-b border-lsc-border dark:border-earth-700 pb-4">
            <summary className="font-semibold text-lsc-dark dark:text-lsc-cream cursor-pointer hover:text-lsc-rose">
              {t('wifiPage.q4', 'Slow connection speed?')}
            </summary>
            <p className="mt-3 text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">
              {t('wifiPage.a4', 'WiFi speed depends on how many people are connected. Try moving closer to a router or ask staff where the strongest signal is located. For demanding tasks, our public computers offer a wired connection.')}
            </p>
          </details>
        </div>
      </div>

      {/* Need Help */}
      <div className="mt-8 bg-lsc-rose/10 dark:bg-lsc-rose/20 rounded-xl p-6 border border-lsc-rose/30">
        <div className="flex items-center gap-3 mb-3">
          <HelpCircle className="w-6 h-6 text-lsc-rose" />
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{t('wifiPage.stillTroubleHeading', 'Still having trouble?')}</h3>
        </div>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
          {t('wifiPage.stillTroubleBody', 'Our tech support team is here to help! Visit the tech support desk or ask any staff member for assistance.')}
        </p>
        <a href="/tech-support" className="inline-block px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition">
          {t('wifiPage.visitTechSupport', 'Visit Tech Support')}
        </a>
      </div>
    </PageContainer>
  )
}
