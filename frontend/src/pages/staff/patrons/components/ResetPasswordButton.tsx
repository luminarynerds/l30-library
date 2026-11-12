/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from "react"
import { KeyRound, Loader2, X, Mail, Hash, Copy, Check } from "lucide-react"
import toast from "react-hot-toast"
import { useTranslation } from '@/i18n'
import { useAuth } from "../../../../contexts/AuthContext"
import { resetPatronPassword } from "../../../../api/staff-api/patrons"
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface ResetPasswordButtonProps {
  patronId: number
  patronName: string
  patronEmail: string
}

type Method = "email" | "temp_code"

export function ResetPasswordButton({ patronId, patronName, patronEmail }: ResetPasswordButtonProps) {
  const { t } = useTranslation()
  const { token } = useAuth()
  const [isOpen, setIsOpen] = useState(false)
  const [method, setMethod] = useState<Method>("email")
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [tempCode, setTempCode] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  const close = () => {
    setIsOpen(false)
    setTempCode(null)
    setMethod("email")
    setCopied(false)
  }

  const handleSubmit = async () => {
    if (!token) return
    setIsSubmitting(true)
    try {
      const result = await resetPatronPassword(token, patronId, {
        send_email: method === "email",
        generate_temp_code: method === "temp_code",
      })
      if (method === "email") {
        if (result.email_sent) {
          toast.success(t('resetPatronPassword.emailSent', { email: patronEmail }))
        } else {
          toast.error(t('resetPatronPassword.emailFailed'))
        }
        close()
      } else if (result.temp_code) {
        setTempCode(result.temp_code)
      } else {
        toast.error(t('resetPatronPassword.failed'))
      }
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('resetPatronPassword.failed'))
    } finally {
      setIsSubmitting(false)
    }
  }

  const copyCode = async () => {
    if (!tempCode) return
    try {
      await navigator.clipboard.writeText(tempCode)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      toast.error(t('resetPatronPassword.copyFailed'))
    }
  }

  return (
    <>
      <button
        onClick={() => setIsOpen(true)}
        className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-lsc-rose hover:bg-lsc-rose/10 rounded-lg transition-colors"
      >
        <KeyRound className="w-4 h-4" />
        {t('resetPatronPassword.button')}
      </button>

      {isOpen && (
        <ModalBackdrop onClose={close} labelledBy="reset-password-modal-title">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 max-w-md w-full mx-4">
            <div className="flex items-center justify-between mb-4">
              <h2 id="reset-password-modal-title" className="text-lg font-serif font-bold text-lsc-dark dark:text-lsc-cream">
                {t('resetPatronPassword.title', { name: patronName })}
              </h2>
              <button
                onClick={close}
                aria-label={t('aria.authModals.close')}
                className="text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {tempCode ? (
              <div className="space-y-4">
                <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
                  {t('resetPatronPassword.tempCodeReady')}
                </p>
                <div className="flex items-center gap-2 p-3 bg-lsc-cream/50 dark:bg-earth-900 border border-lsc-border dark:border-earth-700 rounded-lg">
                  <code className="flex-1 font-mono text-2xl tracking-widest text-center text-lsc-dark dark:text-lsc-cream">
                    {tempCode}
                  </code>
                  <button
                    onClick={copyCode}
                    aria-label={t('resetPatronPassword.copyCode')}
                    className="p-2 text-lsc-rose hover:bg-lsc-rose/10 rounded-lg transition-colors"
                  >
                    {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                  </button>
                </div>
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">
                  {t('resetPatronPassword.tempCodeExpiry')}
                </p>
                <div className="flex justify-end pt-2">
                  <button
                    onClick={close}
                    className="px-4 py-2 text-sm font-medium text-white bg-lsc-green rounded-lg hover:bg-lsc-green/90 transition-colors"
                  >
                    {t('resetPatronPassword.done')}
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
                  {t('resetPatronPassword.chooseMethod')}
                </p>

                <label className={`flex items-start gap-3 p-3 border rounded-lg cursor-pointer transition-colors ${
                  method === "email"
                    ? "border-lsc-rose bg-lsc-rose/5"
                    : "border-lsc-border dark:border-earth-700 hover:bg-lsc-cream/30 dark:hover:bg-earth-700"
                }`}>
                  <input
                    type="radio"
                    name="reset-method"
                    value="email"
                    checked={method === "email"}
                    onChange={() => setMethod("email")}
                    className="mt-1 accent-lsc-rose"
                  />
                  <div className="flex-1">
                    <div className="flex items-center gap-2 text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                      <Mail className="w-4 h-4" />
                      {t('resetPatronPassword.emailMethod')}
                    </div>
                    <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mt-1">
                      {t('resetPatronPassword.emailMethodDesc', { email: patronEmail })}
                    </div>
                  </div>
                </label>

                <label className={`flex items-start gap-3 p-3 border rounded-lg cursor-pointer transition-colors ${
                  method === "temp_code"
                    ? "border-lsc-rose bg-lsc-rose/5"
                    : "border-lsc-border dark:border-earth-700 hover:bg-lsc-cream/30 dark:hover:bg-earth-700"
                }`}>
                  <input
                    type="radio"
                    name="reset-method"
                    value="temp_code"
                    checked={method === "temp_code"}
                    onChange={() => setMethod("temp_code")}
                    className="mt-1 accent-lsc-rose"
                  />
                  <div className="flex-1">
                    <div className="flex items-center gap-2 text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                      <Hash className="w-4 h-4" />
                      {t('resetPatronPassword.tempCodeMethod')}
                    </div>
                    <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mt-1">
                      {t('resetPatronPassword.tempCodeMethodDesc')}
                    </div>
                  </div>
                </label>

                <div className="flex justify-end gap-2 pt-2">
                  <button
                    onClick={close}
                    disabled={isSubmitting}
                    className="px-4 py-2 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream/50 dark:hover:bg-earth-700 rounded-lg transition-colors"
                  >
                    {t('resetPatronPassword.cancel')}
                  </button>
                  <button
                    onClick={handleSubmit}
                    disabled={isSubmitting}
                    className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-white bg-lsc-rose rounded-lg hover:bg-lsc-rose/90 disabled:opacity-50 transition-colors"
                  >
                    {isSubmitting ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <KeyRound className="w-4 h-4" />}
                    {t('resetPatronPassword.confirm')}
                  </button>
                </div>
              </div>
            )}
          </div>
        </ModalBackdrop>
      )}
    </>
  )
}
