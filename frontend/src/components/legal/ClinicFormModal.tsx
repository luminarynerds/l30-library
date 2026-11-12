/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { XCircle, Loader2, MapPin } from 'lucide-react'
import { useTranslation } from '@/i18n'
import type { LegalTopic, LegalClinic } from '@/api/legal-api'
import { geocodePreview } from '@/api/legal-api'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface ClinicFormModalProps {
  onClose: () => void
  onSave: (data: Record<string, unknown>) => void
  topics: LegalTopic[]
  saving: boolean
  initial?: LegalClinic
}

export function ClinicFormModal({ onClose, onSave, topics, saving, initial }: ClinicFormModalProps) {
  const { t } = useTranslation()
  const isEdit = Boolean(initial)
  const [form, setForm] = useState({
    title: initial?.title ?? '',
    topic_id: initial?.topic_id ? String(initial.topic_id) : '',
    description: initial?.description ?? '',
    date: initial?.date ?? '',
    start_time: initial?.start_time ?? '',
    end_time: initial?.end_time ?? '',
    is_virtual: initial?.is_virtual ?? false,
    location_name: initial?.location_name ?? '',
    location_address: initial?.location_address ?? '',
    capacity: initial?.capacity ?? 20,
    registration_required: true,
    eligibility_notes: initial?.eligibility_notes ?? '',
    public_notes: '',
  })
  const [coords, setCoords] = useState<{ lat: number; lng: number } | null>(null)
  const [geocodeStatus, setGeocodeStatus] = useState<'idle' | 'loading' | 'success' | 'failed'>('idle')
  const [manualCoords, setManualCoords] = useState(false)

  const handleGeocode = async () => {
    const address = form.location_address || form.location_name
    if (!address) return
    setGeocodeStatus('loading')
    try {
      const result = await geocodePreview(address)
      if (result.status === 'success' && result.latitude && result.longitude) {
        setCoords({ lat: result.latitude, lng: result.longitude })
        setGeocodeStatus('success')
      } else {
        setGeocodeStatus('failed')
      }
    } catch {
      setGeocodeStatus('failed')
    }
  }

  const titleText = isEdit
    ? t('admin.adminLegal.editClinic')
    : t('admin.adminLegal.scheduleClinic')

  return (
    <ModalBackdrop onClose={onClose} title={titleText}>
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-6 border-b border-lsc-border dark:border-earth-700">
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-earth-50">{titleText}</h2>
          <button
            onClick={onClose}
            aria-label={t('aria.adminLegal.closeClinicModal')}
            className="p-2 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg"
          >
            <XCircle className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
          </button>
        </div>
        <div className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-earth-50 mb-1">{t('clinicFormModal.title', 'Title')} *</label>
            <input
              type="text" aria-label={t('clinicFormModal.clinicTitle', 'Clinic title')}
              value={form.title}
              onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50"
              placeholder={t('placeholder.adminLegal.egFamilyLawFree')}
            />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-earth-50 mb-1">{t('clinicFormModal.topic', 'Topic')}</label>
              <select aria-label={t('clinicFormModal.topic', 'Topic')}
                value={form.topic_id}
                onChange={e => setForm(f => ({ ...f, topic_id: e.target.value }))}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50"
              >
                <option value="">{t('clinicFormModal.selectTopic', 'Select topic...')}</option>
                {topics.map(t => (
                  <option key={t.id} value={t.id}>{t.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-earth-50 mb-1">{t('clinicFormModal.capacity', 'Capacity')}</label>
              <input
                type="number" aria-label={t('clinicFormModal.capacity', 'Capacity')}
                value={form.capacity}
                onChange={e => setForm(f => ({ ...f, capacity: Number(e.target.value) }))}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50"
                min={1}
              />
            </div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-earth-50 mb-1">{t('clinicFormModal.date', 'Date')} *</label>
              <input
                type="date" aria-label={t('clinicFormModal.clinicDate', 'Clinic date')}
                value={form.date}
                onChange={e => setForm(f => ({ ...f, date: e.target.value }))}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-earth-50 mb-1">{t('clinicFormModal.startTime', 'Start Time')} *</label>
              <input
                type="time" aria-label={t('clinicFormModal.startTimeLower', 'Start time')}
                value={form.start_time}
                onChange={e => setForm(f => ({ ...f, start_time: e.target.value }))}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-earth-50 mb-1">{t('clinicFormModal.endTime', 'End Time')} *</label>
              <input
                type="time" aria-label={t('clinicFormModal.endTimeLower', 'End time')}
                value={form.end_time}
                onChange={e => setForm(f => ({ ...f, end_time: e.target.value }))}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50"
              />
            </div>
          </div>
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="is_virtual"
              checked={form.is_virtual}
              onChange={e => setForm(f => ({ ...f, is_virtual: e.target.checked }))}
              className="w-4 h-4 accent-lsc-rose"
            />
            <label htmlFor="is_virtual" className="text-sm text-lsc-dark dark:text-earth-50">{t('clinicFormModal.virtualClinic', 'Virtual Clinic')}</label>
          </div>
          {!form.is_virtual && (
            <>
              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-earth-50 mb-1">{t('clinicFormModal.locationName', 'Location Name')}</label>
                <input
                  type="text" aria-label={t('clinicFormModal.locationNameLower', 'Location name')}
                  value={form.location_name}
                  onChange={e => setForm(f => ({ ...f, location_name: e.target.value }))}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50"
                  placeholder={t('placeholder.adminLegal.egMainLibraryMeeting')}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-earth-50 mb-1">{t('clinicFormModal.locationAddress', 'Location Address')}</label>
                <input
                  type="text" aria-label={t('clinicFormModal.locationAddressLower', 'Location address')}
                  value={form.location_address}
                  onChange={e => setForm(f => ({ ...f, location_address: e.target.value }))}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50"
                />
              </div>
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={handleGeocode}
                    disabled={geocodeStatus === 'loading' || (!form.location_address && !form.location_name)}
                    className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-earth-50 rounded-lg hover:bg-lsc-cream/80 dark:hover:bg-earth-600 disabled:opacity-50 transition-colors"
                  >
                    {geocodeStatus === 'loading' ? (
                      <Loader2 className="w-3 h-3 motion-safe:animate-spin" />
                    ) : (
                      <MapPin className="w-3 h-3" />
                    )}
                    {geocodeStatus === 'loading' ? t('clinicFormModal.geocoding', 'Geocoding...') : t('clinicFormModal.previewOnMap', 'Preview on map')}
                  </button>
                  {geocodeStatus === 'success' && coords && (
                    <span className="text-xs text-status-success-600 dark:text-status-success-400">
                      {t('clinicFormModal.locationFoundX', { lat: coords.lat.toFixed(4), lng: coords.lng.toFixed(4) })}
                    </span>
                  )}
                  {geocodeStatus === 'failed' && (
                    <span className="text-xs text-status-danger-600 dark:text-status-danger-400">
                      {t('clinicFormModal.geocodingFailedEnterCoordinates', 'Geocoding failed -- enter coordinates manually')}
                    </span>
                  )}
                </div>

                {geocodeStatus === 'success' && coords && (
                  <div className="rounded-lg overflow-hidden border border-lsc-border dark:border-earth-700 h-48">
                    <iframe
                      title={t('clinicFormModal.clinicLocationPreview', 'Clinic location preview')}
                      width="100%"
                      height="100%"
                      style={{ border: 0 }}
                      loading="lazy"
                      src={`https://www.openstreetmap.org/export/embed.html?bbox=${coords.lng - 0.01},${coords.lat - 0.005},${coords.lng + 0.01},${coords.lat + 0.005}&layer=mapnik&marker=${coords.lat},${coords.lng}`}
                    />
                  </div>
                )}

                {(geocodeStatus === 'failed' || manualCoords) && (
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-medium text-lsc-dark dark:text-earth-50 mb-1">{t('clinicFormModal.latitude', 'Latitude')}</label>
                      <input
                        type="number"
                        step="any"
                        aria-label={t('clinicFormModal.latitude', 'Latitude')}
                        value={coords?.lat || ''}
                        onChange={e => setCoords(c => ({ lat: Number(e.target.value), lng: c?.lng || 0 }))}
                        className="w-full px-3 py-1.5 text-sm border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50"
                        placeholder="39.9403"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-lsc-dark dark:text-earth-50 mb-1">{t('clinicFormModal.longitude', 'Longitude')}</label>
                      <input
                        type="number"
                        step="any"
                        aria-label={t('clinicFormModal.longitude', 'Longitude')}
                        value={coords?.lng || ''}
                        onChange={e => setCoords(c => ({ lat: c?.lat || 0, lng: Number(e.target.value) }))}
                        className="w-full px-3 py-1.5 text-sm border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50"
                        placeholder="-82.0132"
                      />
                    </div>
                  </div>
                )}

                {geocodeStatus === 'success' && !manualCoords && (
                  <button
                    type="button"
                    onClick={() => setManualCoords(true)}
                    className="text-xs text-lsc-dark/50 dark:text-lsc-cream/50 hover:text-lsc-dark dark:hover:text-lsc-cream transition-colors"
                  >
                    {t('clinicFormModal.wrongLocationEnterCoordinates', 'Wrong location? Enter coordinates manually')}
                  </button>
                )}
              </div>
            </>
          )}
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-earth-50 mb-1">{t('clinicFormModal.description', 'Description')}</label>
            <textarea aria-label={t('clinicFormModal.description', 'Description')}
              value={form.description}
              onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
              rows={3}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50"
              placeholder={t('admin.adminLegal.whatWillBeCoveredAt')}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-earth-50 mb-1">{t('clinicFormModal.eligibilityNotes', 'Eligibility Notes')}</label>
            <textarea aria-label={t('clinicFormModal.eligibilityNotes', 'Eligibility Notes')}
              value={form.eligibility_notes}
              onChange={e => setForm(f => ({ ...f, eligibility_notes: e.target.value }))}
              rows={2}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50"
              placeholder={t('admin.adminLegal.whoIsEligibleToAttend')}
            />
          </div>
        </div>
        <div className="flex justify-end gap-3 p-6 border-t border-lsc-border dark:border-earth-700">
          <button onClick={onClose} className="px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg text-lsc-dark dark:text-earth-50 hover:bg-lsc-cream dark:hover:bg-earth-700 text-sm">
            {t('common.cancel')}
          </button>
          <button
            onClick={() => onSave({
              ...form,
              topic_id: form.topic_id ? Number(form.topic_id) : null,
              ...(coords ? { latitude: coords.lat, longitude: coords.lng } : {}),
            })}
            disabled={saving || !form.title || !form.date || !form.start_time || !form.end_time}
            className="px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 text-sm font-medium disabled:opacity-50 flex items-center gap-2"
          >
            {saving && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
            {isEdit ? t('admin.adminLegal.saveChanges') : t('admin.adminLegal.scheduleClinic')}
          </button>
        </div>
      </div>
    </ModalBackdrop>
  )
}
