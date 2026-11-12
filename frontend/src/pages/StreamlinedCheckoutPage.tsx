/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertCircle, Volume2, RotateCcw, LogOut, Printer, Search, Loader2 } from 'lucide-react';
import { format } from 'date-fns';
import toast from 'react-hot-toast';
import { useAuth } from '../contexts/AuthContext';
import { searchPatrons, getPatronCheckouts, type Patron } from '../api/staff-api/patrons';
import { staffCheckoutItem, staffCheckinItem } from '../api/staff-api/circulation';
import { getPatronFineHistory } from '../api/staff-api/fines';
import { useTranslation} from '@/i18n'
import { AdminShell } from '../components/shells/AdminShell'

interface CheckoutItem {
  id: string;
  barcode: string;
  title: string;
  author: string;
  dueDate: string;
  timestamp: number;
}

interface CheckoutError {
  barcode: string;
  message: string;
  type: 'invalid' | 'already_checked_out' | 'not_found' | 'patron_blocked';
  timestamp: number;
}

export const StreamlinedCheckoutPage: React.FC = () => {
  const { t } = useTranslation()
  const navigate = useNavigate();
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { user: _user, token } = useAuth();
  const barcodeInputRef = useRef<HTMLInputElement>(null);

  // State management
  const [mode, setMode] = useState<'patron' | 'items' | 'done'>('patron');
  const [patronLookupMode, setPatronLookupMode] = useState<'scan' | 'search'>('scan');
  const [nameQuery, setNameQuery] = useState('');
  const [nameResults, setNameResults] = useState<Patron[]>([]);
  const [isSearchingByName, setIsSearchingByName] = useState(false);
  const [patronCard, setPatronCard] = useState('');
  const [patronInfo, setPatronInfo] = useState<{ id: number; name: string; email: string; checkoutCount: number; fineBalance: number; cardExpiry: string | null } | null>(null);
  const [checkedOutItems, setCheckedOutItems] = useState<CheckoutItem[]>([]);
  const [errors, setErrors] = useState<CheckoutError[]>([]);
  const [currentBarcode, setCurrentBarcode] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [totalFines, setTotalFines] = useState(0);
  const [receipt, setReceipt] = useState<string | null>(null);
  const [printInProgress, setPrintInProgress] = useState(false);

  // Warn before leaving with scanned items
  useEffect(() => {
    const handler = (e: BeforeUnloadEvent) => {
      if (checkedOutItems.length > 0) {
        e.preventDefault()
      }
    }
    window.addEventListener('beforeunload', handler)
    return () => window.removeEventListener('beforeunload', handler)
  }, [checkedOutItems])

  useEffect(() => {
    // Focus barcode input
    if (barcodeInputRef.current) {
      barcodeInputRef.current.focus();
    }
  }, [mode]);

  // Play beep sound
  const playSound = (type: 'success' | 'error') => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();

    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);

    if (type === 'success') {
      oscillator.frequency.value = 800; // Higher pitch for success
      gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.1);
      oscillator.start(audioContext.currentTime);
      oscillator.stop(audioContext.currentTime + 0.1);
    } else {
      oscillator.frequency.value = 400; // Lower pitch for error
      gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.2);
      oscillator.start(audioContext.currentTime);
      oscillator.stop(audioContext.currentTime + 0.2);
    }
  };

  // Handle patron card scan
  const handlePatronCardScan = async (barcode: string) => {
    if (!barcode.trim()) return;

    setIsProcessing(true);
    try {
      if (!token) throw new Error('Authentication required');

      // Search for patron by card barcode
      const result = await searchPatrons(token, barcode);

      if (result.patrons.length === 0) {
        playSound('error');
        setErrors([...errors, {
          barcode,
          message: t('streamlinedCheckout.patronCardNotFound'),
          type: 'not_found',
          timestamp: Date.now()
        }]);
        setPatronCard('');
        return;
      }

      const patron = result.patrons[0];
      if (!patron) return;

      // Check patron status
      if (patron.patron_status === 'blocked') {
        playSound('error');
        setErrors([...errors, {
          barcode,
          message: `Patron account blocked: ${patron.suspension_reason || 'No reason specified'}`,
          type: 'patron_blocked',
          timestamp: Date.now()
        }]);
        setPatronCard('');
        return;
      }

      if (patron.patron_status === 'suspended') {
        playSound('error');
        setErrors([...errors, {
          barcode,
          message: `Patron account suspended until ${patron.suspended_until}`,
          type: 'patron_blocked',
          timestamp: Date.now()
        }]);
        setPatronCard('');
        return;
      }

      // Get patron details including fines
      const checkouts = await getPatronCheckouts(token, patron.id);
      const fineHistory = await getPatronFineHistory(token, patron.id);

      const totalUnpaidFines = fineHistory.fines
        .filter((f) => f.status === 'unpaid')
        .reduce((sum, f) => sum + (parseFloat(String(f.amount)) - parseFloat(String(f.amount_paid))), 0);

      playSound('success');
      setPatronInfo({
        id: patron.id,
        name: [patron.first_name, patron.last_name].filter(Boolean).join(' ') || 'Unknown Patron',
        email: patron.email ?? "",
        checkoutCount: checkouts.length,
        fineBalance: totalUnpaidFines,
        cardExpiry: patron.card_expires_at || null
      });
      setPatronCard(barcode);
      setMode('items');
      setTotalFines(totalUnpaidFines);
      setErrors([]); // Clear errors when patron successfully scanned
      setCurrentBarcode('');
    } catch (_error: unknown) {
      playSound('error');
      setErrors([...errors, {
        barcode,
        message: t('streamlinedCheckout.errorScanningPatronCardTry'),
        type: 'invalid',
        timestamp: Date.now()
      }]);
      setPatronCard('');
    } finally {
      setIsProcessing(false);
    }
  };

  // Handle patron name search
  const handleNameSearch = async () => {
    if (!nameQuery.trim()) return;
    if (!token) {
      toast.error(t('toast.authenticationRequired'));
      return;
    }
    setIsSearchingByName(true);
    setNameResults([]);
    try {
      const result = await searchPatrons(token, nameQuery.trim());
      setNameResults(result.patrons);
      if (result.patrons.length === 0) {
        playSound('error');
      }
    } catch {
      playSound('error');
      setNameResults([]);
    } finally {
      setIsSearchingByName(false);
    }
  };

  // Handle selecting a patron from name search results
  const handleSelectPatron = async (patron: Patron) => {
    setIsProcessing(true);
    try {
      if (!token) throw new Error('Authentication required');

      if (patron.patron_status === 'blocked' || patron.patron_status === 'suspended') {
        playSound('error');
        setErrors([...errors, {
          barcode: [patron.first_name, patron.last_name].filter(Boolean).join(' ') || 'Unknown Patron',
          message: `Patron account ${patron.patron_status}: ${patron.suspension_reason || patron.suspended_until || 'No reason specified'}`,
          type: 'patron_blocked',
          timestamp: Date.now()
        }]);
        return;
      }

      const checkouts = await getPatronCheckouts(token, patron.id);
      const fineHistory = await getPatronFineHistory(token, patron.id);
      const totalUnpaidFines = fineHistory.fines
        .filter((f) => f.status === 'unpaid')
        .reduce((sum, f) => sum + (parseFloat(String(f.amount)) - parseFloat(String(f.amount_paid))), 0);

      playSound('success');
      setPatronInfo({
        id: patron.id,
        name: [patron.first_name, patron.last_name].filter(Boolean).join(' ') || 'Unknown Patron',
        email: patron.email ?? "",
        checkoutCount: checkouts.length,
        fineBalance: totalUnpaidFines,
        cardExpiry: patron.card_expires_at || null
      });
      setPatronCard('');
      setMode('items');
      setTotalFines(totalUnpaidFines);
      setErrors([]);
      setCurrentBarcode('');
      setNameQuery('');
      setNameResults([]);
    } catch {
      playSound('error');
      setErrors([...errors, {
        barcode: [patron.first_name, patron.last_name].filter(Boolean).join(' ') || 'Unknown Patron',
        message: t('streamlinedCheckout.errorLoadingPatronDetailsTry'),
        type: 'invalid',
        timestamp: Date.now()
      }]);
    } finally {
      setIsProcessing(false);
    }
  };

  // Handle item barcode scan
  const handleItemScan = async (barcode: string) => {
    if (!barcode.trim() || mode !== 'items') return;

    // Check if patron card scanned again (signals done)
    if (barcode === patronCard) {
      playSound('success');
      handleCheckoutComplete();
      return;
    }

    // Check for duplicate
    if (checkedOutItems.some(item => item.barcode === barcode)) {
      playSound('error');
      setErrors([...errors, {
        barcode,
        message: t('streamlinedCheckout.itemAlreadyCheckedOutIn'),
        type: 'already_checked_out',
        timestamp: Date.now()
      }]);
      setCurrentBarcode('');
      return;
    }

    setIsProcessing(true);
    try {
      if (!token) throw new Error('Authentication required');

      const response = await staffCheckoutItem(
        token,
        patronInfo!.id,
        barcode
      );

      // Guard against 200 with success: false
      if ('success' in response && response.success === false) {
        playSound('error');
        setErrors(prev => [...prev, {
          barcode,
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          message: (response as any).message || 'Checkout failed',
          type: 'invalid' as const,
          timestamp: Date.now()
        }]);
        setCurrentBarcode('');
        return;
      }

      // Successful checkout
      playSound('success');
      setCheckedOutItems([...checkedOutItems, {
        id: String(response.id),
        barcode,
        title: response.item_title || 'Unknown Title',
        author: response.item_author || 'Unknown Author',
        dueDate: response.due_date,
        timestamp: Date.now()
      }]);
      setCurrentBarcode('');
      setErrors([]); // Clear errors on successful scan
    } catch (error: unknown) {
      playSound('error');
      setErrors([...errors, {
        barcode,
        message: (error instanceof Error ? error.message : null) || 'Error processing item. Try again.',
        type: 'invalid',
        timestamp: Date.now()
      }]);
      setCurrentBarcode('');
    } finally {
      setIsProcessing(false);
    }
  };

  // Handle checkout complete
  const handleCheckoutComplete = async () => {
    if (checkedOutItems.length === 0) {
      setMode('patron');
      setPatronInfo(null);
      setPatronCard('');
      return;
    }

    setMode('done');

    // Generate receipt
    const receiptContent = generateReceipt();
    setReceipt(receiptContent);

    // Auto-print receipt
    setTimeout(() => {
      printReceipt();
    }, 500);
  };

  // Generate receipt
  const generateReceipt = (): string => {
    const now = new Date();
    const itemsHTML = checkedOutItems.map(item => `
      <tr>
        <td style="padding: 8px; border-bottom: 1px solid #ddd;">${(item.title || '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c] || c))}</td>
        <td style="padding: 8px; border-bottom: 1px solid #ddd; text-align: right;">
          ${format(new Date(item.dueDate), 'MMM dd, yyyy')}
        </td>
      </tr>
    `).join('');

    return `
      <!DOCTYPE html>
      <html>
      <head>
        <title>Checkout Receipt</title>
        <style>
          body { font-family: 'Courier New', monospace; margin: 0; padding: 20px; }
          .receipt { max-width: 400px; margin: 0 auto; }
          .header { text-align: center; margin-bottom: 20px; }
          .patron-info { margin-bottom: 15px; }
          .items-table { width: 100%; margin: 15px 0; border-collapse: collapse; }
          .items-table th { text-align: left; padding: 8px; border-bottom: 2px solid #000; }
          .footer { text-align: center; margin-top: 20px; font-size: 12px; color: #666; }
          .total { font-weight: bold; font-size: 16px; margin: 15px 0; }
          .due-date { color: #d32f2f; font-weight: bold; }
        </style>
      </head>
      <body>
        <div class="receipt">
          <div class="header">
            <h2>CHECKOUT RECEIPT</h2>
            <p>${format(now, 'PPp')}</p>
          </div>

          <div class="patron-info">
            <strong>${patronInfo!.name}</strong><br>
            Items Checked Out: <strong>${checkedOutItems.length}</strong>
          </div>

          <table class="items-table">
            <thead>
              <tr>
                <th>ITEM</th>
                <th style="text-align: right;">DUE DATE</th>
              </tr>
            </thead>
            <tbody>
              ${itemsHTML}
            </tbody>
          </table>

          <div class="total">
            Total: ${checkedOutItems.length} item${checkedOutItems.length !== 1 ? 's' : ''}
          </div>

          ${totalFines > 0 ? `
            <div style="background: #fff3cd; padding: 10px; border: 1px solid #ffc107; border-radius: 4px; margin: 15px 0;">
              <strong>Outstanding Fines: $${totalFines.toFixed(2)}</strong>
            </div>
          ` : ''}

          <div class="footer">
            <p>${t('streamlinedCheckout.thankYouForUsingOur')}</p>
            <p>Questions? Contact staff.</p>
          </div>
        </div>
      </body>
      </html>
    `;
  };

  // Print receipt using hidden iframe (avoids popup blockers)
  const printReceipt = () => {
    if (!receipt) return;

    setPrintInProgress(true);

    // Remove any previous print iframe
    const existingFrame = document.getElementById('receipt-print-frame');
    if (existingFrame) existingFrame.remove();

    const iframe = document.createElement('iframe');
    iframe.id = 'receipt-print-frame';
    iframe.style.position = 'fixed';
    iframe.style.right = '0';
    iframe.style.bottom = '0';
    iframe.style.width = '0';
    iframe.style.height = '0';
    iframe.style.border = 'none';
    document.body.appendChild(iframe);

    const iframeDoc = iframe.contentDocument || iframe.contentWindow?.document;
    if (iframeDoc) {
      iframeDoc.open();
      iframeDoc.write(receipt);
      iframeDoc.close();

      // Wait for content to render before printing
      iframe.onload = () => {
        try {
          iframe.contentWindow?.print();
        } catch {
          // Fallback: try window.print() if iframe print fails
          window.print();
        }
        setTimeout(() => {
          iframe.remove();
          setPrintInProgress(false);
        }, 1000);
      };

      // Trigger onload for inline content
      setTimeout(() => {
        if (document.getElementById('receipt-print-frame')) {
          try {
            iframe.contentWindow?.print();
          } catch {
            // Silent fallback
          }
          setTimeout(() => {
            iframe.remove();
            setPrintInProgress(false);
          }, 1000);
        }
      }, 500);
    } else {
      setPrintInProgress(false);
    }
  };

  // Handle undo last scan
  const handleUndoLastScan = async () => {
    if (checkedOutItems.length === 0) return;

    const lastItem = checkedOutItems[checkedOutItems.length - 1]!;

    try {
      if (!token) throw new Error('Authentication required');
      // Call API to return the checkout
      await staffCheckinItem(token, lastItem.barcode);

      // Remove from list
      setCheckedOutItems(checkedOutItems.slice(0, -1));
      playSound('success');
    } catch (error: unknown) {
      playSound('error');
      setErrors([...errors, {
        barcode: lastItem.barcode,
        message: t('streamlinedCheckout.failedToUndoScan') + (error instanceof Error ? error.message : 'an unexpected issue'),
        type: 'invalid',
        timestamp: Date.now()
      }]);
    }
  };

  // Handle barcode input
  const handleBarcodeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setCurrentBarcode(e.target.value);
  };

  const handleBarcodeKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      if (mode === 'patron') {
        handlePatronCardScan(currentBarcode);
      } else if (mode === 'items') {
        handleItemScan(currentBarcode);
      }
    }
  };

  // Reset for next patron
  const handleReset = () => {
    setMode('patron');
    setPatronCard('');
    setPatronInfo(null);
    setCheckedOutItems([]);
    setErrors([]);
    setCurrentBarcode('');
    setTotalFines(0);
    setReceipt(null);
  };

  // Remove specific error
  const removeError = (timestamp: number) => {
    setErrors(errors.filter(e => e.timestamp !== timestamp));
  };

  // Render patron mode
  if (mode === 'patron') {
    return (
      <div className="min-h-screen bg-lsc-cream dark:bg-earth-900 p-4">
        <div className="max-w-2xl mx-auto">
          <button
            onClick={() => navigate('/staff')}
            className="mb-4 inline-flex items-center gap-2 px-4 py-2 bg-lsc-white dark:bg-earth-800 rounded-lg shadow hover:shadow-md dark:hover:shadow-lg transition-shadow text-lsc-dark/70 dark:text-lsc-cream/70"
          >
            <LogOut size={20} />
            Exit
          </button>

          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-lg p-8">
            <h1 className="font-serif text-4xl font-bold text-center mb-2 text-earth-800 dark:text-earth-100">
              Fast Checkout
            </h1>
            <p className="text-center text-lsc-dark/70 dark:text-lsc-cream/70 mb-8">
              {patronLookupMode === 'scan' ? 'Scan patron card to begin' : 'Search for patron by name'}
            </p>

            {patronLookupMode === 'scan' ? (
              <>
                <div className="mb-4">
                  <input
                    ref={barcodeInputRef}
                    type="text"
                    value={currentBarcode}
                    onChange={handleBarcodeChange}
                    onKeyDown={handleBarcodeKeyDown}
                    placeholder={t('placeholder.streamlinedCheckout.scanPatronCard')}
                    aria-label={t('placeholder.streamlinedCheckout.scanPatronCard')}
                    disabled={isProcessing}
                    className="w-full px-6 py-4 text-xl border-2 border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream rounded-lg focus:border-lsc-rose focus:outline-none focus:ring-2 focus:ring-status-warning-200 dark:focus:ring-status-warning-900 disabled:bg-earth-100 dark:disabled:bg-earth-900"
                    autoFocus
                  />
                </div>
                <button
                  onClick={() => setPatronLookupMode('search')}
                  className="mb-6 w-full flex items-center justify-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose transition-colors"
                >
                  <Search size={16} />
                  No card? Search by name
                </button>
              </>
            ) : (
              <>
                <div className="mb-4">
                  <form
                    onSubmit={(e) => { e.preventDefault(); handleNameSearch(); }}
                    className="flex gap-2"
                  >
                    <input
                      type="text"
                      value={nameQuery}
                      onChange={(e) => setNameQuery(e.target.value)}
                      placeholder={t('streamlinedCheckout.enterPatronNameOrEmail')}
                      disabled={isSearchingByName}
                      className="flex-1 px-6 py-4 text-xl border-2 border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream rounded-lg focus:border-lsc-rose focus:outline-none focus:ring-2 focus:ring-status-warning-200 dark:focus:ring-status-warning-900 disabled:bg-earth-100 dark:disabled:bg-earth-900"
                      autoFocus
                    />
                    <button
                      type="submit"
                      disabled={isSearchingByName || !nameQuery.trim()}
                      className="px-6 py-4 bg-lsc-rose hover:bg-status-warning-600 text-white rounded-lg font-semibold disabled:bg-earth-400 dark:disabled:bg-earth-600 disabled:cursor-not-allowed transition-colors"
                    >
                      {isSearchingByName ? <Loader2 size={24} className="motion-safe:animate-spin" /> : <Search size={24} />}
                    </button>
                  </form>
                </div>

                {/* Name search results */}
                {nameResults.length > 0 && (
                  <div className="mb-6 space-y-2">
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                      {nameResults.length} patron{nameResults.length !== 1 ? 's' : ''} found — select one:
                    </p>
                    {nameResults.map((patron) => (
                      <button
                        key={patron.id}
                        onClick={() => handleSelectPatron(patron)}
                        disabled={isProcessing}
                        className="w-full text-left p-4 bg-earth-50 dark:bg-earth-700 border-2 border-lsc-border dark:border-earth-700 rounded-lg hover:border-lsc-rose transition-colors disabled:opacity-50"
                      >
                        <p className="font-bold text-earth-800 dark:text-earth-100">{[patron.first_name, patron.last_name].filter(Boolean).join(' ') || 'Unknown Patron'}</p>
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{patron.email ?? patron.email_masked ?? ""}</p>
                      </button>
                    ))}
                  </div>
                )}

                {nameResults.length === 0 && nameQuery && !isSearchingByName && (
                  <p className="mb-6 text-center text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">
                    No patrons found. Try a different name or email.
                  </p>
                )}

                <button
                  onClick={() => { setPatronLookupMode('scan'); setNameQuery(''); setNameResults([]); }}
                  className="mb-6 w-full flex items-center justify-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose transition-colors"
                >
                  Back to card scan
                </button>
              </>
            )}

            {/* Error Messages */}
            {errors.length > 0 && (
              <div className="mb-6 space-y-2">
                {errors.map((error) => (
                  <div
                    key={error.timestamp}
                    className="bg-status-danger-50 dark:bg-status-danger-900/20 border-l-4 border-status-danger-500 p-4 flex justify-between items-start"
                  >
                    <div className="flex gap-3">
                      <AlertCircle className="text-status-danger-500 dark:text-status-danger-400 flex-shrink-0 mt-0.5" size={20} />
                      <div>
                        <p className="font-semibold text-status-danger-800 dark:text-status-danger-300">{error.message}</p>
                        <p className="text-sm text-status-danger-700 dark:text-status-danger-400">Barcode: {error.barcode}</p>
                      </div>
                    </div>
                    <button
                      onClick={() => removeError(error.timestamp)}
                      className="text-status-danger-500 dark:text-status-danger-400 hover:text-status-danger-700 dark:hover:text-status-danger-300 text-sm"
                    >
                      Dismiss
                    </button>
                  </div>
                ))}
              </div>
            )}

            {patronLookupMode === 'scan' && (
              <div className="bg-earth-50 dark:bg-earth-700 border border-lsc-border dark:border-earth-700 rounded-lg p-4 text-center">
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
                  Position scanner or barcode reader to receive scan
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Render items mode
  if (mode === 'items' && patronInfo) {
    const earliestDueDate = checkedOutItems.length > 0
      ? new Date(Math.min(...checkedOutItems.map(i => new Date(i.dueDate).getTime())))
      : null;

    return (
      <div className="min-h-screen bg-lsc-cream dark:bg-earth-900 p-4">
        <div className="max-w-4xl mx-auto">
          {/* Header */}
          <div className="flex justify-between items-center mb-6">
            <div>
              <h1 className="font-serif text-4xl font-bold text-earth-800 dark:text-earth-100">Fast Checkout</h1>
              <p className="text-lg text-lsc-dark/70 dark:text-lsc-cream/70">{patronInfo!.name}</p>
            </div>
            <div className="flex gap-3">
              <button
                onClick={handleUndoLastScan}
                disabled={checkedOutItems.length === 0}
                className="flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-status-warning-600 text-white rounded-lg disabled:bg-earth-400 dark:disabled:bg-earth-600 disabled:cursor-not-allowed transition-colors"
              >
                <RotateCcw size={20} />
                Undo Last
              </button>
              <button
                onClick={handleCheckoutComplete}
                className="flex items-center gap-2 px-4 py-2 bg-earth-700 hover:bg-earth-800 dark:bg-earth-600 dark:hover:bg-earth-500 text-white rounded-lg transition-colors"
              >
                <LogOut size={20} />
                Done & Print
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Main scanning area */}
            <div className="lg:col-span-2">
              <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-lg p-8">
                <p className="text-center text-lsc-dark/70 dark:text-lsc-cream/70 mb-6 text-lg">
                  Scan items or patron card again to finish
                </p>

                <input
                  ref={barcodeInputRef}
                  type="text"
                  value={currentBarcode}
                  onChange={handleBarcodeChange}
                  onKeyDown={handleBarcodeKeyDown}
                  placeholder={t('placeholder.streamlinedCheckout.scanItemBarcode')}
                  aria-label={t('placeholder.streamlinedCheckout.scanItemBarcode')}
                  disabled={isProcessing}
                  className="w-full px-6 py-6 text-2xl font-bold text-center border-2 border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream rounded-lg focus:border-lsc-rose focus:outline-none focus:ring-2 focus:ring-status-warning-200 dark:focus:ring-status-warning-900 disabled:bg-earth-100 dark:disabled:bg-earth-900"
                  autoFocus
                />

                {/* Items list */}
                <div className="mt-8">
                  {checkedOutItems.length === 0 ? (
                    <p className="text-center text-lsc-dark/70 dark:text-lsc-cream/70 py-8">{t('streamlinedCheckout.noItemsScannedYet')}</p>
                  ) : (
                    <div className="space-y-2">
                      {checkedOutItems.map((item, idx) => (
                        <div
                          key={item.id}
                          className="bg-earth-50 dark:bg-earth-700 border border-lsc-border dark:border-earth-700 rounded-lg p-4 flex justify-between items-start"
                        >
                          <div>
                            <p className="font-bold text-earth-800 dark:text-earth-100">
                              {idx + 1}. {item.title}
                            </p>
                            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{item.author}</p>
                          </div>
                          <div className="text-right">
                            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Due:</p>
                            <p className="font-bold text-lsc-rose">
                              {format(new Date(item.dueDate), 'MMM dd')}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Error messages */}
                {errors.length > 0 && (
                  <div className="mt-6 space-y-2">
                    {errors.slice(-3).map((error) => (
                      <div
                        key={error.timestamp}
                        className="bg-status-danger-50 dark:bg-status-danger-900/20 border-l-4 border-status-danger-500 p-4 flex justify-between items-start"
                      >
                        <div className="flex gap-3">
                          <AlertCircle className="text-status-danger-500 dark:text-status-danger-400 flex-shrink-0 mt-0.5" size={20} />
                          <div>
                            <p className="font-semibold text-status-danger-800 dark:text-status-danger-300">{error.message}</p>
                            <p className="text-xs text-status-danger-700 dark:text-status-danger-400">{error.barcode}</p>
                          </div>
                        </div>
                        <button
                          onClick={() => removeError(error.timestamp)}
                          className="text-status-danger-500 dark:text-status-danger-400 hover:text-status-danger-700 dark:hover:text-status-danger-300 text-xs font-bold"
                        >
                          ×
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Sidebar stats */}
            <div className="space-y-4">
              <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-lg p-6">
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm mb-2">ITEMS CHECKED OUT</p>
                <p className="text-5xl font-bold text-lsc-rose">
                  {checkedOutItems.length}
                </p>
              </div>

              {earliestDueDate && (
                <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-lg p-6">
                  <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm mb-2">EARLIEST DUE DATE</p>
                  <p className="text-2xl font-bold text-lsc-rose">
                    {format(earliestDueDate, 'MMM dd')}
                  </p>
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                    {Math.ceil((earliestDueDate.getTime() - new Date().getTime()) / (1000 * 60 * 60 * 24))} days away
                  </p>
                </div>
              )}

              {totalFines > 0 && (
                <div className="bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 rounded-lg p-6">
                  <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm mb-2">OUTSTANDING FINES</p>
                  <p className="text-3xl font-bold text-status-warning-600 dark:text-status-warning-400">
                    ${totalFines.toFixed(2)}
                  </p>
                </div>
              )}

              <div className="bg-earth-100 dark:bg-earth-700 border border-lsc-border dark:border-earth-700 rounded-lg p-4 text-center">
                <Volume2 className="mx-auto mb-2 text-lsc-dark/70 dark:text-lsc-cream/70" size={24} />
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Audio feedback enabled</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Render done mode
  if (mode === 'done') {
    return (

    <AdminShell title="Fast Checkout">      <div className="min-h-screen bg-lsc-cream dark:bg-earth-900 p-4 flex items-center">
        <div className="max-w-2xl mx-auto w-full">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-lg p-8 text-center">
            <div className="mb-6">
              <div className="inline-flex items-center justify-center w-16 h-16 bg-lsc-rose/10 dark:bg-lsc-rose/20 rounded-full mb-4">
                <span className="text-4xl text-lsc-rose">✓</span>
              </div>
            </div>

            <h1 className="font-serif text-4xl font-bold mb-2 text-earth-800 dark:text-earth-100">
              Checkout Complete
            </h1>
            <p className="text-xl text-lsc-dark/70 dark:text-lsc-cream/70 mb-8">
              {checkedOutItems.length} item{checkedOutItems.length !== 1 ? 's' : ''} checked out for {patronInfo?.name}
            </p>

            <div className="bg-earth-50 dark:bg-earth-700 rounded-lg p-6 mb-6 text-left">
              <h2 className="font-serif font-bold text-lg text-earth-800 dark:text-earth-100 mb-4">Checked Out Items:</h2>
              <div className="space-y-2">
                {checkedOutItems.map((item, idx) => (
                  <div key={item.id} className="border-b border-lsc-border dark:border-earth-700 pb-3 last:border-b-0">
                    <p className="font-semibold text-earth-800 dark:text-earth-100">{idx + 1}. {item.title}</p>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{item.author}</p>
                    <p className="text-sm font-bold text-lsc-rose">
                      Due: {format(new Date(item.dueDate), 'EEEE, MMMM d, yyyy')}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            {totalFines > 0 && (
              <div className="bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 rounded-lg p-4 mb-6">
                <p className="font-bold text-status-warning-800 dark:text-status-warning-200">
                  Outstanding Fines: ${totalFines.toFixed(2)}
                </p>
              </div>
            )}

            <div className="flex gap-4">
              <button
                onClick={() => printReceipt()}
                disabled={printInProgress}
                className="flex-1 flex items-center justify-center gap-2 px-6 py-3 bg-lsc-rose hover:bg-status-warning-600 text-white font-bold rounded-lg disabled:bg-earth-400 dark:disabled:bg-earth-600 transition-colors"
              >
                <Printer size={20} />
                Print Receipt
              </button>
              <button
                onClick={handleReset}
                className="flex-1 px-6 py-3 bg-earth-600 hover:bg-earth-700 dark:bg-earth-700 dark:hover:bg-earth-600 text-white font-bold rounded-lg transition-colors"
              >
                Next Patron
              </button>
              <button
                onClick={() => navigate('/staff')}
                className="flex-1 px-6 py-3 bg-earth-400 hover:bg-earth-500 dark:bg-earth-700 dark:hover:bg-earth-600 text-white font-bold rounded-lg transition-colors"
              >
                Exit
              </button>
            </div>
          </div>
        </div>
      </div>
    </AdminShell>
  );
  }

  return null;
};

export default StreamlinedCheckoutPage;
