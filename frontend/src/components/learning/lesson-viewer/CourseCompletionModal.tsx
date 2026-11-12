/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Link } from 'react-router-dom'
import { Modal } from '@/components/ui/Modal'
import { useTranslation } from '@/i18n'

interface CourseCompletionModalProps {
  isOpen: boolean
  onClose: () => void
  courseId: string | number | undefined
  courseTitle: string
}

export function CourseCompletionModal({
  isOpen,
  onClose,
  courseId,
  courseTitle,
}: CourseCompletionModalProps) {
  const { t } = useTranslation()

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="md" dismissible>
      <div className="text-center py-2">
        <h2 className="font-serif text-2xl font-semibold text-lsc-dark dark:text-lsc-cream mb-3">
          {t('courseCompletion.headline', { courseTitle })}
        </h2>
        <p className="text-lsc-dark/80 dark:text-lsc-cream/80 mb-6">
          {t(
            'courseCompletion.body',
            'You finished every lesson in this course. Take a moment to notice that. Your certificate is ready when you want it, and there is no rush to pick another course.',
          )}
        </p>
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          {courseId !== undefined && (
            <Link
              to={`/learn/certificate/${courseId}`}
              onClick={onClose}
              className="inline-flex items-center justify-center px-5 py-2.5 bg-lsc-rose text-white rounded-xl font-medium hover:bg-lsc-rose/90 focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2 transition-colors"
            >
              {t('courseCompletion.viewCertificate', 'View certificate')}
            </Link>
          )}
          <Link
            to="/learn/catalog"
            onClick={onClose}
            className="inline-flex items-center justify-center px-5 py-2.5 bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream rounded-xl font-medium hover:bg-lsc-cream/80 dark:hover:bg-earth-600 border border-lsc-border dark:border-earth-600 focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2 transition-colors"
          >
            {t('courseCompletion.browseMore', 'Browse more courses')}
          </Link>
        </div>
      </div>
    </Modal>
  )
}

export default CourseCompletionModal
