/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useRef } from 'react';
import FocusTrap from 'focus-trap-react';
import { Loader2 } from 'lucide-react';

// Duplicate-course modal: focus-trapped, ESC closes (handled by FocusTrap
// + onKeyDown), submits the clone via the parent-provided handler. Client-
// side validation mirrors the backend (3-200 chars); the parent surfaces
// 422 duplicate-title errors by returning { ok: false, error }.
export function DuplicateCourseModal({
  sourceTitle,
  sourceId,
  onCancel,
  onSubmit,
  t,
}: {
  sourceTitle: string;
  sourceId: number;
  onCancel: () => void;
  onSubmit: (newTitle: string) => Promise<{ ok: true } | { ok: false; error: string }>;
  t: (key: string, paramsOrFallback?: Record<string, unknown> | string) => string;
}) {
  const [value, setValue] = useState(`${sourceTitle}${t('admin.adminCourses.duplicateNewTitleSuffix')}`);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const titleId = `duplicate-course-title-${sourceId}`;
  const descId = `duplicate-course-desc-${sourceId}`;
  const inputId = `duplicate-course-input-${sourceId}`;
  const errorId = `duplicate-course-error-${sourceId}`;
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = value.trim();
    if (trimmed.length < 3 || trimmed.length > 200) {
      setError(t('admin.adminCourses.duplicateTitleLengthError'));
      inputRef.current?.focus();
      return;
    }
    setSubmitting(true);
    const result = await onSubmit(trimmed);
    setSubmitting(false);
    if (!result.ok) {
      setError(result.error);
      inputRef.current?.focus();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape' && !submitting) onCancel();
  };

  return (
    <FocusTrap
      active
      focusTrapOptions={{
        initialFocus: () => inputRef.current,
        allowOutsideClick: false,
        escapeDeactivates: false,
        returnFocusOnDeactivate: true,
      }}
    >
      <div className="fixed inset-0 z-40" role="presentation" onKeyDown={handleKeyDown}>
        <div
          className="fixed inset-0 bg-black/50"
          aria-hidden="true"
          onClick={() => !submitting && onCancel()}
        />
        <div className="fixed inset-0 flex items-center justify-center z-50 p-4">
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            aria-describedby={descId}
            className="bg-lsc-white dark:bg-earth-800 rounded-xl max-w-[calc(100vw-2rem)] sm:max-w-md w-full shadow-lg"
          >
            <form onSubmit={handleSubmit} noValidate>
              <div className="p-4 sm:p-6 space-y-4">
                <h2
                  id={titleId}
                  className="font-serif text-lg font-bold text-lsc-dark dark:text-lsc-cream"
                >
                  {t('admin.adminCourses.duplicateModalTitle')}
                </h2>
                <p id={descId} className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  {t('admin.adminCourses.duplicateModalBody', { title: sourceTitle })}
                </p>
                <div>
                  <label
                    htmlFor={inputId}
                    className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1"
                  >
                    {t('admin.adminCourses.duplicateNewTitleLabel')}
                  </label>
                  <input
                    ref={inputRef}
                    id={inputId}
                    type="text"
                    value={value}
                    onChange={(e) => {
                      setValue(e.target.value);
                      if (error) setError(null);
                    }}
                    minLength={3}
                    maxLength={200}
                    aria-invalid={!!error}
                    aria-describedby={error ? errorId : undefined}
                    aria-label={t('aria.adminCourses.duplicateNewTitleField')}
                    className={`
                      w-full px-3 py-2 rounded-lg
                      bg-lsc-cream/50 dark:bg-earth-900
                      border text-sm text-lsc-dark dark:text-lsc-cream
                      focus:outline-none focus:ring-2 focus:ring-lsc-rose
                      ${error ? 'border-status-danger-500' : 'border-lsc-border dark:border-earth-700'}
                    `}
                  />
                  {error && (
                    <p
                      id={errorId}
                      role="alert"
                      className="mt-1 text-xs text-status-danger-600 dark:text-status-danger-400"
                    >
                      {error}
                    </p>
                  )}
                </div>
              </div>
              <div className="flex flex-col-reverse sm:flex-row gap-3 p-4 sm:p-6 border-t border-lsc-border dark:border-earth-700">
                <button
                  type="button"
                  onClick={onCancel}
                  disabled={submitting}
                  className="
                    flex-1 px-4 py-2.5 sm:py-2 rounded-lg
                    border border-lsc-border dark:border-earth-700
                    text-lsc-dark dark:text-lsc-cream
                    hover:bg-lsc-cream/50 dark:hover:bg-earth-700
                    motion-safe:transition-colors
                    disabled:opacity-50 disabled:cursor-not-allowed font-medium
                  "
                >
                  {t('admin.adminCourses.duplicateCancel')}
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="
                    flex-1 px-4 py-2.5 sm:py-2 rounded-lg
                    bg-lsc-rose text-white hover:bg-lsc-rose/90
                    motion-safe:transition-colors
                    disabled:opacity-50 disabled:cursor-not-allowed font-medium
                  "
                >
                  {submitting ? (
                    <Loader2 className="w-5 h-5 motion-safe:animate-spin mx-auto" aria-hidden="true" />
                  ) : (
                    t('admin.adminCourses.duplicateSubmit')
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </FocusTrap>
  );
}
