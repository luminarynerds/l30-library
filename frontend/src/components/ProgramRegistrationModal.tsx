/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useId, useRef, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Loader2, CheckCircle, X } from 'lucide-react'
import FocusTrap from 'focus-trap-react'
import { registerForProgram, type ReadingProgram, type ReadingRegistrationCreate } from '@/api/api'
import { useAuth } from '@/contexts/AuthContext'
import { t as translate, useTranslation } from '@/i18n'

interface ProgramRegistrationModalProps {
  program: ReadingProgram
  onClose: () => void
}

export default function ProgramRegistrationModal({
  program,
  onClose,
}: ProgramRegistrationModalProps): React.ReactElement {
  const { t } = useTranslation()
  const { token } = useAuth()
  const queryClient = useQueryClient()
  const titleId = useId()
  const accessibilityHelpId = useId()
  const previousActiveElement = useRef<HTMLElement | null>(null)
  const [success, setSuccess] = useState(false)
  const [goalTarget, setGoalTarget] = useState<string>('')
  const [largePrintMode, setLargePrintMode] = useState(false)
  const [phoneRegistrationRequested, setPhoneRegistrationRequested] = useState(false)
  const [transportationNotes, setTransportationNotes] = useState('')
  const [caregiverName, setCaregiverName] = useState('')
  const [caregiverPhone, setCaregiverPhone] = useState('')
  const [homeDeliverySupportNeeded, setHomeDeliverySupportNeeded] = useState(false)
  const [homeDeliveryNotes, setHomeDeliveryNotes] = useState('')
  const [memoryCareTracking, setMemoryCareTracking] = useState(false)
  const [techHelpRequested, setTechHelpRequested] = useState(false)
  const [seniorCenterPartner, setSeniorCenterPartner] = useState('')
  const [accessibilityNeeds, setAccessibilityNeeds] = useState('')
  const [wellnessCheckIns, setWellnessCheckIns] = useState(false)

  const isSeniorProgram = (() => {
    const ag = program.age_group?.toLowerCase() ?? ''
    return ag.includes('senior') || ag.includes('65') || ag.includes('older adult')
  })()

  // Capture trigger element, lock body scroll, restore focus on close
  useEffect(() => {
    previousActiveElement.current = document.activeElement as HTMLElement
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = ''
      previousActiveElement.current?.focus()
    }
  }, [])

  const mutation = useMutation({
    mutationFn: (data: ReadingRegistrationCreate) =>
      registerForProgram(token!, data),
    onSuccess: () => {
      setSuccess(true)
      queryClient.invalidateQueries({ queryKey: ['reading-programs'] })
      queryClient.invalidateQueries({ queryKey: ['my-registrations'] })
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    const supportPreferences = {
      largePrintMode,
      phoneRegistrationRequested,
      transportationNotes,
      caregiverContact: {
        name: caregiverName,
        phone: caregiverPhone,
      },
      homeDeliverySupportNeeded,
      homeDeliveryNotes,
      memoryCareTracking,
      techHelpRequested,
      seniorCenterPartner,
      accessibilityNeeds,
      wellnessCheckIns,
    }

    localStorage.setItem(`reading-program-support-${program.id}`, JSON.stringify(supportPreferences))

    const data: ReadingRegistrationCreate = {
      program_id: program.id,
    }
    if (goalTarget) {
      data.goal_target = parseInt(goalTarget, 10)
    }
    mutation.mutate(data)
  }

  return (
    <FocusTrap
      focusTrapOptions={{
        escapeDeactivates: false,
        allowOutsideClick: true,
        returnFocusOnDeactivate: false,
        fallbackFocus: () => document.body,
      }}
    >
      <div
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4"
        role="presentation"
        onKeyDown={(e) => {
          if (e.key === 'Escape') {
            e.preventDefault()
            onClose()
          }
        }}
      >
        <div
          className={`relative w-full max-w-md bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-h-[90vh] overflow-y-auto ${largePrintMode ? 'text-lg' : ''}`}
          role="dialog"
          aria-modal="true"
          aria-labelledby={titleId}
        >
          <div className="flex items-center justify-between border-b border-lsc-border dark:border-earth-700 px-6 py-4 sticky top-0 bg-lsc-white dark:bg-earth-800 rounded-t-xl z-10">
            <h2
              id={titleId}
              className="text-lg font-serif font-semibold text-lsc-dark dark:text-lsc-cream"
            >
              {success ? 'Welcome to the Program!' : 'Join Program'}
            </h2>
            <button
              onClick={onClose}
              className="p-2 rounded-full text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700 transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose"
              aria-label={translate('aria.addRoleModal.closeModal')}
            >
              <X aria-hidden="true" className="w-5 h-5" />
            </button>
          </div>

          <div className="p-6">
            {success ? (
              <div className="text-center py-6">
                <CheckCircle aria-hidden="true" className="w-16 h-16 text-lsc-rose dark:text-lsc-rose-light mx-auto mb-4" />
                <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
                  You're all set!
                </h3>
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
                  You've successfully joined <strong>{program.name}</strong>. Start logging your reading to track your
                  progress!
                </p>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
                  Thank you for joining! We're here to support you every step of the way.
                </p>
                <button
                  onClick={onClose}
                  className="px-6 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl transition-colors"
                >
                  Done
                </button>
              </div>
            ) : (
              <>
                {/* Program info */}
                <div className="mb-4 p-3 bg-lsc-cream dark:bg-lsc-brown/30 rounded-xl">
                  <h3 className="font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                    {program.name}
                  </h3>
                  {program.description && (
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                      {program.description}
                    </p>
                  )}
                  <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 space-y-1">
                    {program.target_age_min && program.target_age_max && (
                      <p>Age: {program.target_age_min}–{program.target_age_max} years</p>
                    )}
                    {program.reading_goal_type && program.reading_goal_value && (
                      <p>
                        Program goal: <strong>{program.reading_goal_value} {program.reading_goal_type}</strong>
                      </p>
                    )}
                  </div>
                </div>

                <form onSubmit={handleSubmit} className="space-y-4">
                  <div>
                    <label
                      htmlFor="goal_target"
                      className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-2"
                    >
                      <div>Personal Goal (optional)</div>
                      <div className="text-xs font-normal text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                        Set your own goal or leave blank to use the program default
                      </div>
                    </label>
                    <div className="flex gap-2">
                      <input
                        type="number"
                        id="goal_target"
                        name="goal_target"
                        value={goalTarget}
                        onChange={(e) => setGoalTarget(e.target.value)}
                        className="flex-1 px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                        placeholder={program.reading_goal_value?.toString() || '100'}
                        min="1"
                      />
                      <div className="flex items-center px-3 py-2 bg-lsc-cream dark:bg-lsc-brown rounded-xl text-sm font-medium text-lsc-dark dark:text-lsc-cream/80">
                        {program.reading_goal_type || 'units'}
                      </div>
                    </div>
                  </div>

                  {isSeniorProgram && (
                  <div className="p-4 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-earth-800/60 space-y-3">
                    <div>
                      <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">{t('components.programRegistration.seniorSupportOptionsOptional')}</p>
                      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{t('components.programRegistration.personalizedOptionsToSupportYour')}</p>
                    </div>

                    <label className="flex items-center gap-2 text-sm text-lsc-dark dark:text-lsc-cream/80">
                      <input type="checkbox" checked={largePrintMode} onChange={(e) => setLargePrintMode(e.target.checked)} />
                      Large print interface option
                    </label>

                    <label className="flex items-center gap-2 text-sm text-lsc-dark dark:text-lsc-cream/80">
                      <input type="checkbox" checked={phoneRegistrationRequested} onChange={(e) => setPhoneRegistrationRequested(e.target.checked)} />
                      Phone registration for programs
                    </label>

                    <div>
                      <label htmlFor="transportation_notes" className="block text-xs font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1">Transportation coordination notes</label>
                      <textarea
                        id="transportation_notes"
                        value={transportationNotes}
                        onChange={(e) => setTransportationNotes(e.target.value)}
                        className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
                        rows={2}
                        placeholder={t('components.programRegistration.preferredPickupWindowsDriverNotes')}
                      />
                    </div>

                    <div className="grid sm:grid-cols-2 gap-2">
                      <div>
                        <label htmlFor="caregiver_name" className="block text-xs font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1">Caregiver name</label>
                        <input
                          id="caregiver_name"
                          value={caregiverName}
                          onChange={(e) => setCaregiverName(e.target.value)}
                          className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
                          placeholder={t('placeholder.programRegistrationModal.caregiverContactManagement')}
                        />
                      </div>
                      <div>
                        <label htmlFor="caregiver_phone" className="block text-xs font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1">Caregiver phone</label>
                        <input
                          id="caregiver_phone"
                          value={caregiverPhone}
                          onChange={(e) => setCaregiverPhone(e.target.value)}
                          className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
                        />
                      </div>
                    </div>

                    <label className="flex items-center gap-2 text-sm text-lsc-dark dark:text-lsc-cream/80">
                      <input type="checkbox" checked={homeDeliverySupportNeeded} onChange={(e) => setHomeDeliverySupportNeeded(e.target.checked)} />
                      Home delivery service integration
                    </label>

                    {homeDeliverySupportNeeded && (
                      <textarea
                        value={homeDeliveryNotes}
                        onChange={(e) => setHomeDeliveryNotes(e.target.value)}
                        className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
                        rows={2}
                        placeholder={t('components.programRegistration.deliveryOrPorchDropOff')}
                      />
                    )}

                    <label className="flex items-center gap-2 text-sm text-lsc-dark dark:text-lsc-cream/80">
                      <input type="checkbox" checked={memoryCareTracking} onChange={(e) => setMemoryCareTracking(e.target.checked)} />
                      Memory care program tracking
                    </label>

                    <label className="flex items-center gap-2 text-sm text-lsc-dark dark:text-lsc-cream/80">
                      <input type="checkbox" checked={techHelpRequested} onChange={(e) => setTechHelpRequested(e.target.checked)} />
                      Tech help for seniors scheduling
                    </label>

                    <div>
                      <label htmlFor="senior_center_partner" className="block text-xs font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1">{t('components.programRegistration.seniorCenterPartnershipTools')}</label>
                      <input
                        id="senior_center_partner"
                        value={seniorCenterPartner}
                        onChange={(e) => setSeniorCenterPartner(e.target.value)}
                        className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
                        placeholder={t('components.programRegistration.partnerSiteOrCoordinator')}
                      />
                    </div>

                    <div>
                      <label htmlFor="accessibility_needs" className="block text-xs font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1">Accessibility needs tracking</label>
                      <p id={accessibilityHelpId} className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                        {t('components.programRegistration.hearingVisionMobilityOrCommunication')}
                      </p>
                      <textarea
                        id="accessibility_needs"
                        aria-describedby={accessibilityHelpId}
                        value={accessibilityNeeds}
                        onChange={(e) => setAccessibilityNeeds(e.target.value)}
                        className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
                        rows={2}
                        placeholder={t('components.programRegistration.hearingVisionMobilityOrCommunication')}
                      />
                    </div>

                    <label className="flex items-center gap-2 text-sm text-lsc-dark dark:text-lsc-cream/80">
                      <input type="checkbox" checked={wellnessCheckIns} onChange={(e) => setWellnessCheckIns(e.target.checked)} />
                      Wellness check-in programs
                    </label>
                  </div>
                  )}

                  {mutation.isError && (
                    <div className="p-3 bg-status-danger-50 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-300 rounded-xl text-sm">
                      {mutation.error.message}
                    </div>
                  )}

                  <div className="bg-lsc-cream dark:bg-lsc-brown/30 p-3 rounded-xl text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    <p className="mb-2 font-medium">What happens next:</p>
                    <ul className="space-y-1 text-xs list-disc list-inside">
                      <li>{t('components.programRegistration.youLlJoinTheProgram')}</li>
                      <li>{t('components.programRegistration.logYourReadingEntriesTo')}</li>
                      <li>{t('components.programRegistration.earnBadgesAndAchievementsAs')}</li>
                      <li>{t('components.programRegistration.checkYourProgressAnytimeFrom')}</li>
                    </ul>
                  </div>

                  <div className="flex gap-3 pt-2">
                    <button
                      type="button"
                      onClick={onClose}
                      className="flex-1 px-4 py-2 border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream/80 rounded-xl hover:bg-lsc-cream dark:hover:bg-lsc-brown transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={mutation.isPending}
                      className="flex-1 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 disabled:bg-lsc-rose text-white rounded-xl transition-colors flex items-center justify-center gap-2"
                    >
                      {mutation.isPending ? (
                        <>
                          <Loader2 aria-hidden="true" className="w-4 h-4 motion-safe:animate-spin" />
                          Joining...
                        </>
                      ) : (
                        'Join Program'
                      )}
                    </button>
                  </div>
                </form>
              </>
            )}
          </div>
        </div>
      </div>
    </FocusTrap>
  )
}
