/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import {
  Palette,
  Edit2,
  Loader2,
  Check,
  ExternalLink,
} from 'lucide-react'
import toast from 'react-hot-toast'
import {
  getWhiteLabel,
  updateWhiteLabel,
  type ConsortiumDetail,
  type ConsortiumMember,
  type ConsortiumWhiteLabel,
} from '../../../api/consortium-api'
import { useTranslation} from '@/i18n'

function WhiteLabelTab({
  token,
  selectedConsortium,
}: {
  token: string | null
  selectedConsortium: ConsortiumDetail | null
}) {
  const { t } = useTranslation()
  const [members, setMembers] = useState<ConsortiumMember[]>([])
  const [selectedMemberId, setSelectedMemberId] = useState<number | null>(null)
  const [whiteLabel, setWhiteLabel] = useState<ConsortiumWhiteLabel | null>(null)
  const [loading, setLoading] = useState(false)
  const [isEditing, setIsEditing] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [formData, setFormData] = useState<Partial<ConsortiumWhiteLabel>>({})

  useEffect(() => {
    if (selectedConsortium) {
      setMembers(selectedConsortium.members || [])
    }
  }, [selectedConsortium])

  useEffect(() => {
    const loadWhiteLabel = async () => {
      if (!selectedMemberId) return
      try {
        setLoading(true)
        const data = await getWhiteLabel(selectedMemberId)
        setWhiteLabel(data)
        setFormData(data || {})
      } catch (_err: unknown) {
        // White label might not exist yet, which is fine
        setWhiteLabel(null)
        setFormData({})
      } finally {
        setLoading(false)
      }
    }
    loadWhiteLabel()
  }, [selectedMemberId])

  const handleSave = async () => {
    if (!token || !selectedMemberId) return
    setIsSubmitting(true)
    try {
      const updated = await updateWhiteLabel(token, selectedMemberId, formData)
      setWhiteLabel(updated)
      setIsEditing(false)
      toast.success(t('components.admin.whiteLabelTab.whiteLabelSettingsSaved'))
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('toast.admin.failedToSaveSettings'))
    } finally {
      setIsSubmitting(false)
    }
  }

  if (!selectedConsortium) {
    return (
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-12 text-center">
        <Palette className="w-16 h-16 text-lsc-dark/30 dark:text-lsc-cream/60 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-lsc-dark dark:text-lsc-cream mb-2">
          Select a consortium
        </h3>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
          Go to the Consortiums tab and select a consortium to configure white labeling.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
            White Label Configuration
          </h2>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            Customize branding for member libraries in {selectedConsortium.name}
          </p>
        </div>
      </div>

      {/* Member Selector */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6">
        <label
          htmlFor="member-select"
          className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2"
        >
          Select Member Library
        </label>
        <select
          id="member-select"
          value={selectedMemberId || ''}
          onChange={(e) => setSelectedMemberId(e.target.value ? parseInt(e.target.value) : null)}
          className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
        >
          <option value="">Choose a member...</option>
          {members.map((member) => (
            <option key={member.id} value={member.id}>
              Library System #{member.library_system_id} ({member.member_type})
            </option>
          ))}
        </select>
      </div>

      {selectedMemberId && (
        <>
          {loading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="w-8 h-8 text-lsc-rose motion-safe:animate-spin" />
            </div>
          ) : (
            <div className="grid gap-6 md:grid-cols-2">
              {/* Branding Colors */}
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6">
                <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
                  Branding Colors
                </h3>
                <div className="space-y-4">
                  {[
                    { key: 'primary_color', label: 'Primary Color' },
                    { key: 'secondary_color', label: 'Secondary Color' },
                    { key: 'accent_color', label: 'Accent Color' },
                  ].map(({ key, label }) => (
                    <div key={key} className="flex items-center gap-4">
                      <label className="flex-1 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                        {label}
                      </label>
                      {isEditing ? (
                        <input
                          type="color"
                          value={
                            (formData[key as keyof ConsortiumWhiteLabel] as string) || '#000000'
                          }
                          onChange={(e) => setFormData({ ...formData, [key]: e.target.value })}
                          className="w-10 h-10 rounded cursor-pointer"
                        />
                      ) : (
                        <div
                          className="w-10 h-10 rounded border border-lsc-border dark:border-earth-700"
                          style={{
                            backgroundColor:
                              (whiteLabel?.[key as keyof ConsortiumWhiteLabel] as string) ||
                              '#cccccc',
                          }}
                        />
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Domain & URLs */}
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6">
                <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
                  Domain Settings
                </h3>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                      Custom Domain
                    </label>
                    {isEditing ? (
                      <input
                        type="text"
                        value={formData.custom_domain || ''}
                        onChange={(e) =>
                          setFormData({ ...formData, custom_domain: e.target.value || null })
                        }
                        placeholder={t('placeholder.admin.libraryexamplecom')}
                        className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                      />
                    ) : (
                      <p className="text-lsc-dark dark:text-lsc-cream">
                        {whiteLabel?.custom_domain || 'Not configured'}
                      </p>
                    )}
                  </div>
                  <div>
                    <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                      Subdomain
                    </label>
                    {isEditing ? (
                      <input
                        type="text"
                        value={formData.subdomain || ''}
                        onChange={(e) =>
                          setFormData({ ...formData, subdomain: e.target.value || null })
                        }
                        placeholder={t('placeholder.admin.mylibrary')}
                        className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                      />
                    ) : (
                      <p className="text-lsc-dark dark:text-lsc-cream">
                        {whiteLabel?.subdomain || 'Not configured'}
                      </p>
                    )}
                  </div>
                </div>
              </div>

              {/* Logos & Images */}
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6">
                <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
                  Logos & Images
                </h3>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                      Logo URL
                    </label>
                    {isEditing ? (
                      <input
                        type="url"
                        value={formData.logo_url || ''}
                        onChange={(e) =>
                          setFormData({ ...formData, logo_url: e.target.value || null })
                        }
                        placeholder={t('placeholder.admin.https1')}
                        className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                      />
                    ) : whiteLabel?.logo_url ? (
                      <a
                        href={whiteLabel.logo_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-lsc-rose hover:underline flex items-center gap-1"
                      >
                        View Logo <ExternalLink className="w-3 h-3" />
                      </a>
                    ) : (
                      <p className="text-lsc-dark/70 dark:text-lsc-cream/70">Not configured</p>
                    )}
                  </div>
                  <div>
                    <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                      Banner URL
                    </label>
                    {isEditing ? (
                      <input
                        type="url"
                        value={formData.banner_url || ''}
                        onChange={(e) =>
                          setFormData({ ...formData, banner_url: e.target.value || null })
                        }
                        placeholder={t('placeholder.admin.https1')}
                        className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                      />
                    ) : whiteLabel?.banner_url ? (
                      <a
                        href={whiteLabel.banner_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-lsc-rose hover:underline flex items-center gap-1"
                      >
                        View Banner <ExternalLink className="w-3 h-3" />
                      </a>
                    ) : (
                      <p className="text-lsc-dark/70 dark:text-lsc-cream/70">Not configured</p>
                    )}
                  </div>
                </div>
              </div>

              {/* Display Options */}
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6">
                <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
                  Display Options
                </h3>
                <div className="space-y-3">
                  {[
                    { key: 'show_consortium_branding', label: 'Show Consortium Branding' },
                    { key: 'show_member_list', label: 'Show Member List' },
                    { key: 'show_consortium_events', label: 'Show Consortium Events' },
                  ].map(({ key, label }) => (
                    <div key={key} className="flex items-center justify-between">
                      <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                        {label}
                      </span>
                      {isEditing ? (
                        <label className="relative inline-flex items-center cursor-pointer">
                          <input
                            type="checkbox"
                            checked={
                              (formData[key as keyof ConsortiumWhiteLabel] as boolean) ?? true
                            }
                            onChange={(e) =>
                              setFormData({ ...formData, [key]: e.target.checked })
                            }
                            className="sr-only peer"
                          />
                          <div className="w-11 h-6 bg-earth-200 peer-focus:ring-2 peer-focus:ring-lsc-rose rounded-full peer dark:bg-earth-700 peer-checked:bg-lsc-rose"></div>
                        </label>
                      ) : (
                        <span
                          className={`text-sm font-medium ${(whiteLabel?.[key as keyof ConsortiumWhiteLabel] as boolean) !== false ? 'text-status-success-600' : 'text-lsc-dark/70 dark:text-lsc-cream/70'}`}
                        >
                          {(whiteLabel?.[key as keyof ConsortiumWhiteLabel] as boolean) !== false
                            ? 'Yes'
                            : 'No'}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex justify-end gap-3">
            {isEditing ? (
              <>
                <button
                  onClick={() => {
                    setIsEditing(false)
                    setFormData(whiteLabel || {})
                  }}
                  disabled={isSubmitting}
                  className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-xl font-medium disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSave}
                  disabled={isSubmitting}
                  className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium flex items-center gap-2 disabled:opacity-50"
                >
                  {isSubmitting ? (
                    <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                  ) : (
                    <Check className="w-4 h-4" />
                  )}
                  Save Changes
                </button>
              </>
            ) : (
              <button
                onClick={() => setIsEditing(true)}
                className="flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium transition-colors"
              >
                <Edit2 className="w-4 h-4" />
                Edit Settings
              </button>
            )}
          </div>
        </>
      )}
    </div>
  )
}

export default WhiteLabelTab
