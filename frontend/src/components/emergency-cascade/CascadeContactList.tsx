/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Phone, Mail, MessageSquare, Clock } from "lucide-react"
import { useTranslation } from "@/i18n"
import type { CascadeContact, CascadeData } from "./types"

interface Props {
  cascade: CascadeData
  contacts: CascadeContact[]
}

export function CascadeContactList({ cascade, contacts }: Props): React.ReactElement {
  const { t } = useTranslation()

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border-2 border-lsc-border dark:border-earth-700 p-6">
      <h2 className="text-2xl font-serif font-bold mb-6 flex items-center gap-2">
        <Phone className="w-6 h-6 text-category-600" />
        {cascade.cascade_name} - Contact Hierarchy
      </h2>

      {contacts.length > 0 ? (
        <div className="space-y-4">
          {contacts.map((contact, index) => (
            <div key={contact.id} className="p-4 bg-earth-50 dark:bg-earth-900 rounded-lg border-l-4 border-category-400">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <div className="flex items-center gap-3 mb-2">
                    <span className="inline-flex items-center justify-center w-8 h-8 bg-category-600 text-white rounded-full font-bold text-sm">
                      {contact.level}
                    </span>
                    <div>
                      <h4 className="font-serif font-bold text-lsc-dark dark:text-lsc-cream">{contact.contact_name}</h4>
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{contact.contact_role}</p>
                    </div>
                  </div>
                </div>

                <div
                  className={`px-3 py-1 rounded-full text-xs font-bold ${
                    contact.is_active
                      ? "bg-status-success-100 dark:bg-status-success-900/30 text-status-success-800 dark:text-status-success-300"
                      : "bg-earth-100 dark:bg-earth-700 text-earth-800 dark:text-earth-100"
                  }`}
                >
                  {contact.is_active ? "ACTIVE" : "INACTIVE"}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4 text-sm">
                {contact.contact_email && (
                  <div className="flex items-center gap-2">
                    <Mail className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
                    <span className="text-lsc-dark/70 dark:text-lsc-cream/70 break-all">{contact.contact_email}</span>
                  </div>
                )}

                {contact.contact_phone && (
                  <div className="flex items-center gap-2">
                    <Phone className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
                    <span className="text-lsc-dark/70 dark:text-lsc-cream/70">{contact.contact_phone}</span>
                  </div>
                )}

                <div className="flex items-center gap-2">
                  <MessageSquare className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
                  <span className="text-lsc-dark/70 dark:text-lsc-cream/70 capitalize">{contact.contact_method}</span>
                </div>

                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
                  <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Wait: varies</span>
                </div>
              </div>

              {index < contacts.length - 1 && (
                <div className="mt-4 flex justify-center">
                  <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">
                    <Phone className="w-4 h-4 rotate-90" />
                    <span>escalate if no response</span>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-center py-8">{t('emergencyOperationsCascade.noContactsAddedToThis')}</p>
      )}
    </div>
  )
}
