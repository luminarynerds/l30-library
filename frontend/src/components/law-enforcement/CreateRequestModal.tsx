/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { X, Save } from 'lucide-react'
import { useTranslation } from '@/i18n'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface NewRequestState {
  requesting_agency: string
  request_type: string
  date_received: string
  data_requested: string
  patron_name_on_request: string
  requesting_officer_name: string
  requesting_officer_badge: string
  description: string
}

interface CreateRequestModalProps {
  newRequest: NewRequestState
  onFieldChange: (field: keyof NewRequestState, value: string) => void
  onClose: () => void
  onCreate: () => void
}

export function CreateRequestModal({
  newRequest,
  onFieldChange,
  onClose,
  onCreate,
}: CreateRequestModalProps): React.ReactElement {
  const { t } = useTranslation()

  return (
    <ModalBackdrop onClose={onClose} title="Log New Law Enforcement Request">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-lg w-full max-h-[90vh] overflow-auto">
        <div className="p-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
            Log New Law Enforcement Request
          </h3>
          <button
            onClick={onClose}
            className="p-1 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="p-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Requesting Agency <span className="text-status-danger-500">*</span>
            </label>
            <input
              type="text"
              value={newRequest.requesting_agency}
              onChange={(e) => onFieldChange('requesting_agency', e.target.value)}
              placeholder={t('placeholder.adminLawEnforcement.egLocalPoliceDepartment')}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                Date Received <span className="text-status-danger-500">*</span>
              </label>
              <input
                type="date"
                value={newRequest.date_received}
                onChange={(e) => onFieldChange('date_received', e.target.value)}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                Request Type
              </label>
              <select
                value={newRequest.request_type}
                onChange={(e) => onFieldChange('request_type', e.target.value)}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
              >
                <option value="subpoena">Subpoena</option>
                <option value="warrant">Warrant</option>
                <option value="court_order">Court Order</option>
                <option value="informal">Informal Request</option>
                <option value="national_security_letter">National Security Letter</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Data Requested <span className="text-status-danger-500">*</span>
            </label>
            <textarea
              value={newRequest.data_requested}
              onChange={(e) => onFieldChange('data_requested', e.target.value)}
              rows={2}
              placeholder={t('admin.adminLawEnforcement.descriptionOfDataBeingRequested')}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Patron Name on Request
            </label>
            <input
              type="text"
              value={newRequest.patron_name_on_request}
              onChange={(e) => onFieldChange('patron_name_on_request', e.target.value)}
              placeholder={t('admin.adminLawEnforcement.nameAsItAppearsOn')}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                Officer Name
              </label>
              <input
                type="text"
                value={newRequest.requesting_officer_name}
                onChange={(e) => onFieldChange('requesting_officer_name', e.target.value)}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                Badge Number
              </label>
              <input
                type="text"
                value={newRequest.requesting_officer_badge}
                onChange={(e) => onFieldChange('requesting_officer_badge', e.target.value)}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Description
            </label>
            <textarea
              value={newRequest.description}
              onChange={(e) => onFieldChange('description', e.target.value)}
              rows={2}
              placeholder={t('admin.adminLawEnforcement.additionalDescriptionOfTheRequest')}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
            />
          </div>
        </div>
        <div className="p-4 border-t border-lsc-border dark:border-earth-700 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 rounded-lg"
          >
            Cancel
          </button>
          <button
            onClick={onCreate}
            className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90"
          >
            <Save className="w-4 h-4" />
            Create Request
          </button>
        </div>
      </div>
    </ModalBackdrop>
  )
}
