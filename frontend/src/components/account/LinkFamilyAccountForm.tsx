/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * LinkFamilyAccountForm Component
 *
 * Allows child accounts to request linking to a parent account.
 * Sends a link request to the parent email address.
 */

import React, { useState } from 'react';
import { CheckCircle, XCircle, Loader } from 'lucide-react'
import { useTranslation} from '@/i18n'
import { fetchApi } from '@/api/fetchApi'

interface LinkFamilyAccountFormProps {
  onSuccess?: () => void;
  onCancel?: () => void;
}

export const LinkFamilyAccountForm: React.FC<LinkFamilyAccountFormProps> = ({
  onSuccess,
  onCancel,
}) => {
  const { t } = useTranslation()
  const [parentEmail, setParentEmail] = useState('');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(false);

    try {
      await fetchApi('/households/link-request', {
        method: 'POST',
        body: JSON.stringify({
          parent_email: parentEmail,
          message: message || null,
        }),
      });

      setSuccess(true);
      setParentEmail('');
      setMessage('');

      if (onSuccess) {
        setTimeout(() => onSuccess(), 1500);
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : (err as { message?: string })?.message;
      setError(msg || "We couldn't link that account. Please check the details and try again.");
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="p-6 bg-status-success-50 dark:bg-status-success-900/20 border border-status-success-200 dark:border-status-success-800 rounded-lg">
        <div className="flex items-start gap-3">
          <CheckCircle className="w-6 h-6 text-status-success-600 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-serif font-semibold text-status-success-900 dark:text-status-success-200">Link Request Sent</h3>
            <p className="text-sm text-status-success-800 dark:text-status-success-300 mt-1">
              Your parent will receive a request to approve linking your accounts.
              Once approved, you'll be able to share family features.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label htmlFor="parentEmail" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">
          Parent Email Address
        </label>
        <input
          type="email"
          id="parentEmail"
          value={parentEmail}
          onChange={(e) => setParentEmail(e.target.value)}
          placeholder={t('placeholder.account.parentexamplecom')}
          required
          disabled={loading}
          className="mt-1 w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg shadow-sm focus:outline-none focus:ring-lsc-rose dark:focus:ring-lsc-rose-light focus:border-lsc-rose dark:focus:border-lsc-rose-light disabled:bg-earth-50 dark:disabled:bg-earth-900 dark:bg-earth-800 dark:text-earth-50"
        />
        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
          Enter the email address of the parent account you want to link to.
        </p>
      </div>

      <div>
        <label htmlFor="message" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">
          Message (Optional)
        </label>
        <textarea
          id="message"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder={t('components.account.linkFamilyAccountForm.addAMessageToYour')}
          disabled={loading}
          maxLength={500}
          rows={3}
          className="mt-1 w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg shadow-sm focus:outline-none focus:ring-lsc-rose dark:focus:ring-lsc-rose-light focus:border-lsc-rose dark:focus:border-lsc-rose-light disabled:bg-earth-50 dark:disabled:bg-earth-900 dark:bg-earth-800 dark:text-earth-50"
        />
        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
          {message.length}/500 characters
        </p>
      </div>

      {error && (
        <div className="flex items-start gap-3 p-3 bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-lg">
          <XCircle className="w-5 h-5 text-status-danger-600 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-status-danger-800 dark:text-status-danger-300">{error}</div>
        </div>
      )}

      <div className="flex gap-3 justify-end pt-4">
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            disabled={loading}
            className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg hover:bg-earth-50 dark:hover:bg-earth-800 disabled:bg-earth-50 dark:disabled:bg-earth-900 disabled:opacity-50"
          >
            Cancel
          </button>
        )}
        <button
          type="submit"
          disabled={loading || !parentEmail}
          className="px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 disabled:bg-earth-400 flex items-center gap-2"
        >
          {loading && <Loader className="w-4 h-4 motion-safe:animate-spin" />}
          {loading ? 'Sending...' : 'Send Link Request'}
        </button>
      </div>
    </form>
  );
};
