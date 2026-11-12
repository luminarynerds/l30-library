/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { AlertTriangle } from 'lucide-react';
import AccessibleFormField, {
  inputClasses,
  selectClasses,
  textareaClasses,
} from '../admin/AccessibleFormField';
import { useTranslation } from '@/i18n';
import { CourseFormData } from './training-types';
import MediaUploadField from './MediaUploadField';
import { API_BASE } from '@/api/types';
import type { AuthoringIssue } from '@/lib/authoring-checks';

interface Props {
  formData: CourseFormData;
  errors: Record<string, string>;
  onUpdate: (field: keyof CourseFormData, value: unknown) => void;
  courseId?: string;
  issues?: AuthoringIssue[];
}

export default function CourseDetailsSection({ formData, errors, onUpdate, courseId, issues }: Props) {
  const { t } = useTranslation();

  return (
    <section
      className="
        bg-lsc-white dark:bg-earth-800
        shadow-md rounded-xl p-6 md:p-8
        border border-lsc-border dark:border-earth-700
        mb-8
      "
      aria-labelledby="course-details-heading"
    >
      <h2
        id="course-details-heading"
        className="font-serif text-xl font-semibold text-lsc-dark dark:text-lsc-cream mb-6"
      >
        Course Details
      </h2>

      {issues && issues.length > 0 && (
        <ul
          className="mb-5 space-y-1.5"
          aria-label="Course-level items to finish"
        >
          {issues.map((issue) => (
            <li
              key={issue.code}
              className="flex items-start gap-2 text-sm text-status-warning-800 dark:text-status-warning-200"
            >
              <AlertTriangle
                className="w-4 h-4 shrink-0 mt-0.5 text-status-warning-600 dark:text-status-warning-400"
                aria-hidden="true"
              />
              <span>{issue.message}</span>
            </li>
          ))}
        </ul>
      )}

      <div className="space-y-6">
        <AccessibleFormField
          id="title"
          label="Course Title"
          required
          {...(errors.title && { error: errors.title })}
        >
          <input
            type="text"
            value={formData.title}
            onChange={(e) => onUpdate('title', e.target.value)}
            className={`${inputClasses} ${errors.title ? 'border-status-danger-500 dark:border-status-danger-400' : ''}`}
            placeholder={t('placeholder.adminCourseForm.egIntroductionToDigital')}
            maxLength={200}
          />
        </AccessibleFormField>

        <AccessibleFormField
          id="description"
          label="Description"
          helpText="Describe what learners will gain from this course."
        >
          <textarea
            value={formData.description}
            onChange={(e) => onUpdate('description', e.target.value)}
            className={textareaClasses}
            rows={4}
            placeholder={t('admin.adminCourseForm.aBriefOverviewOfThe')}
          />
        </AccessibleFormField>

        <MediaUploadField
          label="Thumbnail"
          value={formData.thumbnail_url}
          onChange={(url) => onUpdate('thumbnail_url', url)}
          getUploadUrl={() =>
            courseId
              ? `${API_BASE}/learning/courses/${courseId}/media?media_type=thumbnail`
              : null
          }
          accept="image/*"
          helpText="Upload an image or paste a URL."
          disabledHint="Save the course first to enable upload"
        />

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <AccessibleFormField
            id="access_level"
            label="Access Level"
            helpText="Who can view this course?"
          >
            <select
              value={formData.access_level}
              onChange={(e) => onUpdate('access_level', e.target.value)}
              className={selectClasses}
            >
              <option value="patron">Patron (Everyone)</option>
              <option value="staff">Staff Only</option>
              <option value="admin">Admin Only</option>
            </select>
          </AccessibleFormField>

          <AccessibleFormField
            id="difficulty"
            label="Difficulty Level"
          >
            <select
              value={formData.difficulty}
              onChange={(e) => onUpdate('difficulty', e.target.value)}
              className={selectClasses}
            >
              <option value="beginner">Beginner</option>
              <option value="intermediate">Intermediate</option>
              <option value="advanced">Advanced</option>
            </select>
          </AccessibleFormField>

          <AccessibleFormField
            id="estimated_minutes"
            label="Estimated Duration (minutes)"
            {...(errors.estimated_minutes && { error: errors.estimated_minutes })}
          >
            <input
              type="number"
              value={formData.estimated_minutes}
              onChange={(e) => onUpdate('estimated_minutes', e.target.value)}
              className={`${inputClasses} ${errors.estimated_minutes ? 'border-status-danger-500 dark:border-status-danger-400' : ''}`}
              placeholder={t('placeholder.adminCourseForm.60')}
              min="0"
            />
          </AccessibleFormField>

          <AccessibleFormField
            id="quiz_passing_threshold"
            label="Quiz Passing Score (%)"
            helpText="Minimum percentage to pass quizzes."
            {...(errors.quiz_passing_threshold && { error: errors.quiz_passing_threshold })}
          >
            <input
              type="number"
              value={formData.quiz_passing_threshold}
              onChange={(e) => onUpdate('quiz_passing_threshold', e.target.value)}
              className={`${inputClasses} ${errors.quiz_passing_threshold ? 'border-status-danger-500 dark:border-status-danger-400' : ''}`}
              min="0"
              max="100"
            />
          </AccessibleFormField>

          <AccessibleFormField
            id="xp_reward"
            label="XP reward"
            helpText="Experience points awarded on course completion."
          >
            <input
              type="number"
              value={formData.xp_reward}
              onChange={(e) => onUpdate('xp_reward', e.target.value)}
              className={inputClasses}
              placeholder="100"
              min="0"
            />
          </AccessibleFormField>

          <AccessibleFormField
            id="duration_days"
            label="Duration (days)"
            helpText="Number of days to complete the course."
          >
            <input
              type="number"
              value={formData.duration_days}
              onChange={(e) => onUpdate('duration_days', e.target.value)}
              className={inputClasses}
              placeholder="e.g. 30"
              min="1"
            />
          </AccessibleFormField>
        </div>

        <AccessibleFormField
          id="sensory_warning"
          label="Sensory Warning"
          helpText="Alert learners about content that may be challenging (flashing images, loud sounds, etc.)"
        >
          <div className="relative">
            <AlertTriangle
              className="absolute left-3 top-3.5 w-5 h-5 text-status-warning-500"
              aria-hidden="true"
            />
            <textarea
              value={formData.sensory_warning}
              onChange={(e) => onUpdate('sensory_warning', e.target.value)}
              className={`${textareaClasses} pl-11`}
              rows={2}
              placeholder={t('placeholder.adminCourseForm.egThisCourseContains')}
            />
          </div>
        </AccessibleFormField>
      </div>
    </section>
  );
}
