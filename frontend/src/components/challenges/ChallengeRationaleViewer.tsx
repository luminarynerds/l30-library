/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useTranslation } from '@/i18n'
import type {
  AcquisitionRationale,
  ChallengeReason,
} from '@/types/acquisitionRationale'

export interface ChallengeRationaleViewerProps {
  rationale: AcquisitionRationale | null
  challengeReason: ChallengeReason
}

export function ChallengeRationaleViewer({
  rationale,
  challengeReason,
}: ChallengeRationaleViewerProps) {
  const { t } = useTranslation()

  if (!rationale) {
    return <p>{t('acquisitionRationale.noRationaleOnFile')}</p>
  }

  const anticipated =
    rationale.anticipated_challenge_reasons.includes(challengeReason)

  return (
    <section aria-label={t('acquisitionRationale.title')}>
      <h3>{t('acquisitionRationale.title')}</h3>
      <dl>
        <dt>{t('acquisitionRationale.signalLabel')}</dt>
        <dd>
          {rationale.signal_type}
          {rationale.signal_note ? `: ${rationale.signal_note}` : ''}
        </dd>

        {rationale.policy_clause && (
          <>
            <dt>{t('acquisitionRationale.policyClauseLabel')}</dt>
            <dd>{rationale.policy_clause}</dd>
          </>
        )}

        <dt>{t('acquisitionRationale.primaryUseCaseLabel')}</dt>
        <dd>{rationale.primary_use_case_slug}</dd>

        <dt>{t('acquisitionRationale.weedingConditionLabel')}</dt>
        <dd>
          {rationale.weeding_condition}
          {rationale.weeding_signal_note
            ? `\n${rationale.weeding_signal_note}`
            : ''}
        </dd>

        <dt>{t('acquisitionRationale.challengeAnticipationLabel')}</dt>
        <dd>
          {anticipated
            ? t('acquisitionRationale.anticipatedYes', { reason: challengeReason })
            : t('acquisitionRationale.notAnticipated', { reason: challengeReason })}
        </dd>
      </dl>
    </section>
  )
}
