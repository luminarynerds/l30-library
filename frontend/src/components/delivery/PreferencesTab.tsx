/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Loader2 } from 'lucide-react';
import { useTranslation } from '@/i18n';
import type { HomeDeliveryEnrollment, ReadingPreferenceProfile } from '../../api/homeDeliveryApi';

interface PreferencesTabProps {
  enrollments: HomeDeliveryEnrollment[];
  selectedEnrollment: HomeDeliveryEnrollment | null;
  readingPrefs: ReadingPreferenceProfile | null;
  prefsLoading: boolean;
  editingContactInfo: boolean;
  editPhone: string;
  editInstructions: string;
  onSelectEnrollment: (enrollment: HomeDeliveryEnrollment) => void;
  onEditContactInfo: () => void;
  onCancelEdit: () => void;
  onSaveContactInfo: () => void;
  onEditPhoneChange: (val: string) => void;
  onEditInstructionsChange: (val: string) => void;
}

export function PreferencesTab({
  enrollments,
  selectedEnrollment,
  readingPrefs,
  prefsLoading,
  editingContactInfo,
  editPhone,
  editInstructions,
  onSelectEnrollment,
  onEditContactInfo,
  onCancelEdit,
  onSaveContactInfo,
  onEditPhoneChange,
  onEditInstructionsChange,
}: PreferencesTabProps) {
  const { t } = useTranslation();
  return (
    <div className="space-y-4">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-4">
        <h3 className="font-serif text-lg font-semibold mb-2">{t('homeDeliveryManagement.patronReadingPreferencesAmpContact')}</h3>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
          Select an enrolled patron to view and manage their reading preferences and delivery contact information.
        </p>
        <div className="flex items-center gap-4">
          <label className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Select Patron:</label>
          <select
            onChange={(e) => {
              const id = Number(e.target.value);
              const enrollment = enrollments.find((en) => en.id === id);
              if (enrollment) onSelectEnrollment(enrollment);
            }}
            className="px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-status-warning-500"
          >
            <option value="">-- Select patron --</option>
            {enrollments.filter((en) => en.status === 'active').map((en) => (
              <option key={en.id} value={en.id}>{en.patron_name}</option>
            ))}
          </select>
        </div>
      </div>

      {selectedEnrollment && (
        <div className="grid md:grid-cols-2 gap-4">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-4">
              <h4 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{t('homeDeliveryManagement.contactAmpDeliveryInfo')}</h4>
              {!editingContactInfo ? (
                <button
                  onClick={onEditContactInfo}
                  className="text-sm text-status-warning-600 hover:text-status-warning-800 dark:text-status-warning-300"
                >
                  Edit
                </button>
              ) : (
                <div className="flex gap-2">
                  <button
                    onClick={onSaveContactInfo}
                    className="text-sm text-status-success-600 hover:text-status-success-800 dark:text-status-success-300 font-medium"
                  >
                    Save
                  </button>
                  <button
                    onClick={onCancelEdit}
                    className="text-sm text-earth-600 hover:text-lsc-dark/70 dark:text-lsc-cream/70 dark:hover:text-earth-200"
                  >
                    Cancel
                  </button>
                </div>
              )}
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Phone Number</label>
                {editingContactInfo ? (
                  <input
                    type="tel"
                    value={editPhone}
                    onChange={(e) => onEditPhoneChange(e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-status-warning-500"
                  />
                ) : (
                  <p className="text-lsc-dark dark:text-lsc-cream">{selectedEnrollment.contact_phone || '—'}</p>
                )}
              </div>
              <div>
                <label className="block text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Delivery Instructions</label>
                {editingContactInfo ? (
                  <textarea
                    value={editInstructions}
                    onChange={(e) => onEditInstructionsChange(e.target.value)}
                    rows={3}
                    className="w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-status-warning-500"
                    placeholder={t('placeholder.homeDeliveryManagement.egLeaveAtBack')}
                  />
                ) : (
                  <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">{selectedEnrollment.delivery_instructions || 'None specified'}</p>
                )}
              </div>
              <div>
                <label className="block text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Delivery Frequency</label>
                <p className="text-lsc-dark dark:text-lsc-cream capitalize">{selectedEnrollment.delivery_frequency.replace('_', ' ')}</p>
              </div>
              {selectedEnrollment.alternate_contact_name && (
                <div>
                  <label className="block text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Emergency / Alternate Contact</label>
                  <p className="text-lsc-dark dark:text-lsc-cream">{selectedEnrollment.alternate_contact_name}</p>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{selectedEnrollment.alternate_contact_phone}</p>
                </div>
              )}
            </div>
          </div>

          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-6">
            <h4 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">Reading Preferences</h4>
            {prefsLoading ? (
              <div className="flex items-center justify-center py-4">
                <Loader2 className="w-5 h-5 motion-safe:animate-spin text-status-warning-600" />
              </div>
            ) : readingPrefs ? (
              <div className="space-y-3 text-sm">
                {readingPrefs.preferred_genres.length > 0 && (
                  <div>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Preferred Genres</p>
                    <div className="flex flex-wrap gap-1">
                      {readingPrefs.preferred_genres.map((g) => (
                        <span key={g} className="px-2 py-0.5 bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-800 dark:text-status-warning-300 rounded text-xs">{g}</span>
                      ))}
                    </div>
                  </div>
                )}
                {readingPrefs.excluded_genres.length > 0 && (
                  <div>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Excluded Genres</p>
                    <div className="flex flex-wrap gap-1">
                      {readingPrefs.excluded_genres.map((g) => (
                        <span key={g} className="px-2 py-0.5 bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-800 dark:text-status-danger-300 rounded text-xs">{g}</span>
                      ))}
                    </div>
                  </div>
                )}
                {readingPrefs.favorite_authors.length > 0 && (
                  <div>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Favorite Authors</p>
                    <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{readingPrefs.favorite_authors.join(', ')}</p>
                  </div>
                )}
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Format Preferences</p>
                    <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{readingPrefs.format_preferences.join(', ') || '—'}</p>
                  </div>
                  <div>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Content Rating</p>
                    <p className="text-lsc-dark/70 dark:text-lsc-cream/70 capitalize">{readingPrefs.content_rating}</p>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  {readingPrefs.prefers_large_print && (
                    <span className="px-2 py-0.5 bg-earth-100 dark:bg-earth-800/30 text-earth-800 dark:text-lsc-rose-light rounded text-xs">Large Print</span>
                  )}
                  {readingPrefs.prefers_audiobooks && (
                    <span className="px-2 py-0.5 bg-earth-100 dark:bg-earth-800/30 text-earth-800 dark:text-lsc-rose-light rounded text-xs">Audiobooks</span>
                  )}
                  {readingPrefs.prefers_short_books && (
                    <span className="px-2 py-0.5 bg-earth-100 dark:bg-earth-800/30 text-earth-800 dark:text-lsc-rose-light rounded text-xs">Short Books</span>
                  )}
                </div>
                {readingPrefs.current_series.length > 0 && (
                  <div>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Current Series</p>
                    {readingPrefs.current_series.map((s, i) => (
                      <div key={i} className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                        <span className="font-medium">{s.series_name}</span>
                        {s.last_read_book && <span className="text-lsc-dark/70 dark:text-lsc-cream/70"> — last read: {s.last_read_book}</span>}
                        {s.next_book && <span className="text-status-success-700 dark:text-status-success-300"> → next: {s.next_book}</span>}
                      </div>
                    ))}
                  </div>
                )}
                {readingPrefs.notes && (
                  <div>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Notes</p>
                    <p className="text-lsc-dark/70 dark:text-lsc-cream/70 italic">{readingPrefs.notes}</p>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('homeDeliveryManagement.noReadingPreferencesSetFor')}</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
