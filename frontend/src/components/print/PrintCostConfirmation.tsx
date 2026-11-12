/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useRef, useState } from 'react';
import FocusTrap from 'focus-trap-react';
import api from '../../api/api';
import { useTranslation } from '@/i18n'

interface PrintCostConfirmationProps {
  onClose: () => void;
}

export default function PrintCostConfirmation({ onClose }: PrintCostConfirmationProps) {
  const { t } = useTranslation()
  const [paymentMethod, setPaymentMethod] = useState<'card' | 'cash' | 'account_balance'>('card');
  const previousActiveElement = useRef<HTMLElement | null>(null);

  useEffect(() => {
    previousActiveElement.current = document.activeElement as HTMLElement;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = '';
      previousActiveElement.current?.focus();
    };
  }, []);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const pendingJob = JSON.parse(localStorage.getItem('pendingPrintJob') || '{}');
  const totalCost = pendingJob.cost || 0;
  const releaseCode = pendingJob.release_code || 'N/A';

  const handlePayment = async () => {
    setLoading(true);
    setError(null);

    try {
      await api.post('/print/pay', {
        job_id: pendingJob.id,
        payment_method: paymentMethod,
        payment_reference: `PRINT-${pendingJob.id}-${Date.now()}`,
      });

      // Show success and redirect to release station
      alert(`Payment processed! Your release code is: ${releaseCode}\\Please go to the print release station to collect your prints.`);
      localStorage.removeItem('pendingPrintJob');
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Payment failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <FocusTrap focusTrapOptions={{ escapeDeactivates: false, allowOutsideClick: true, returnFocusOnDeactivate: false, fallbackFocus: () => document.body }}>
      <div
        className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
        role="presentation"
        onKeyDown={(e) => { if (e.key === 'Escape') onClose(); }}
      >
      <div
        className="bg-lsc-white dark:bg-earth-800 rounded-lg max-w-md w-full mx-4 p-6"
        role="dialog"
        aria-modal="true"
        aria-labelledby="print-cost-modal-title"
      >
        <h2 id="print-cost-modal-title" className="text-2xl font-serif font-bold mb-4 text-lsc-dark dark:text-lsc-cream">Confirm Print Payment</h2>

        {error && (
          <div className="bg-status-danger-100 dark:bg-status-danger-900/30 border border-status-danger-400 text-status-danger-700 dark:text-status-danger-300 px-4 py-3 rounded mb-4">
            {error}
          </div>
        )}

        <div className="bg-earth-50 dark:bg-earth-900 rounded-lg p-4 mb-6">
          <div className="mb-4">
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Job Name</p>
            <p className="font-semibold text-lsc-dark dark:text-lsc-cream">{pendingJob.job_name}</p>
          </div>
          <div className="mb-4">
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Total Pages</p>
            <p className="font-semibold text-lsc-dark dark:text-lsc-cream">{pendingJob.pages * pendingJob.copies}</p>
          </div>
          <div className="border-t border-lsc-border dark:border-earth-700 pt-4">
            <div className="flex justify-between items-center">
              <span className="font-semibold text-lsc-dark dark:text-lsc-cream">Total Cost:</span>
              <span className="text-2xl font-bold text-lsc-rose dark:text-lsc-rose-light">${totalCost.toFixed(2)}</span>
            </div>
          </div>
        </div>

        <div className="mb-6">
          <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
            Payment Method
          </label>
          <div className="space-y-2">
            <label className="flex items-center">
              <input
                type="radio"
                value="card"
                checked={paymentMethod === 'card'}
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                onChange={(e) => setPaymentMethod(e.target.value as any)}
                className="rounded-full"
              />
              <span className="ml-2 text-lsc-dark dark:text-lsc-cream">Credit/Debit Card</span>
            </label>
            <label className="flex items-center">
              <input
                type="radio"
                value="cash"
                checked={paymentMethod === 'cash'}
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                onChange={(e) => setPaymentMethod(e.target.value as any)}
                className="rounded-full"
              />
              <span className="ml-2 text-lsc-dark dark:text-lsc-cream">{t('components.print.printCostConfirmation.cashAtReleaseStation')}</span>
            </label>
            <label className="flex items-center">
              <input
                type="radio"
                value="account_balance"
                checked={paymentMethod === 'account_balance'}
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                onChange={(e) => setPaymentMethod(e.target.value as any)}
                className="rounded-full"
              />
              <span className="ml-2 text-lsc-dark dark:text-lsc-cream">Account Balance</span>
            </label>
          </div>
        </div>

        <div className="bg-earth-50 dark:bg-earth-800/20 border border-lsc-border dark:border-earth-700 rounded-lg p-3 mb-6">
          <p className="text-sm text-lsc-rose dark:text-lsc-rose-light">
            <strong>Your Release Code:</strong> <span className="font-mono font-bold text-lg">{releaseCode}</span>
          </p>
          <p className="text-sm text-lsc-rose dark:text-lsc-rose-light mt-2">
            Save this code to collect your prints at any print release station.
          </p>
        </div>

        <div className="flex gap-4">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-50 dark:hover:bg-earth-700"
            disabled={loading}
          >
            Cancel
          </button>
          <button
            onClick={handlePayment}
            disabled={loading}
            className="flex-1 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 disabled:bg-earth-400"
          >
            {loading ? 'Processing...' : `Pay $${totalCost.toFixed(2)}`}
          </button>
        </div>
      </div>
      </div>
    </FocusTrap>
  );
}
