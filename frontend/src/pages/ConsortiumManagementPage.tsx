/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useState } from 'react'
import { useAuth } from '../contexts/AuthContext'
import {
  Shield,
  Building2,
  Users,
  Share2,
  DollarSign,
  Palette,
} from 'lucide-react'
import {
  ConsortiumsTab,
  MembersTab,
  SharedResourcesTab,
  BillingTab,
  WhiteLabelTab,
} from '../components/admin/consortium'
import type { ConsortiumDetail } from '../api/consortium-api'
import { AdminShell } from '../components/shells/AdminShell'

type TabType = 'consortiums' | 'members' | 'resources' | 'billing' | 'whitelabel'

// ==================== Main Page Component ====================

export default function ConsortiumManagementPage(): React.ReactElement {
  const { user, token } = useAuth()
  const [activeTab, setActiveTab] = useState<TabType>('consortiums')
  const [selectedConsortium, setSelectedConsortium] = useState<ConsortiumDetail | null>(null)

  const handleSelectConsortium = (consortium: ConsortiumDetail) => {
    setSelectedConsortium(consortium)
    setActiveTab('members')
  }

  // Check admin access
  if (!user || !['admin', 'super_admin'].includes(user.role)) {
    return (
      <AdminShell title="Consortium Management">
        <div className="text-center py-20">
          <Shield className="w-16 h-16 text-lsc-dark/70 dark:text-lsc-cream/70 mx-auto mb-4" />
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">Staff-Only Area</h1>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">
            Admin access required to manage consortiums
          </p>
        </div>
      </AdminShell>
    )
  }

  const tabs: Array<{
    id: TabType
    label: string
    icon: React.ComponentType<React.SVGProps<SVGSVGElement>>
  }> = [
    { id: 'consortiums', label: 'Consortiums', icon: Building2 },
    { id: 'members', label: 'Members', icon: Users },
    { id: 'resources', label: 'Shared Resources', icon: Share2 },
    { id: 'billing', label: 'Billing', icon: DollarSign },
    { id: 'whitelabel', label: 'White Label', icon: Palette },
  ]

  return (
    <AdminShell
      title="Consortium Management"
      subtitle={selectedConsortium ? undefined : 'Manage library consortiums, members, and shared resources'}
      icon={<Building2 className="w-7 h-7 text-lsc-rose" />}
    >
      {/* Selected consortium indicator */}
      {selectedConsortium && (
        <div className="text-lsc-dark/70 dark:text-lsc-cream/70 -mt-4 mb-4">
          Managing:{' '}
          <span className="font-medium text-lsc-dark dark:text-lsc-cream">
            {selectedConsortium.name}
          </span>
          <button
            onClick={() => setSelectedConsortium(null)}
            className="ml-2 text-lsc-rose hover:underline text-sm"
          >
            (change)
          </button>
        </div>
      )}

      {/* Tabs */}
      <div className="flex flex-wrap gap-2 bg-lsc-white dark:bg-earth-800 rounded-lg p-1 shadow-sm border border-lsc-border dark:border-earth-700">
        {tabs.map((tab) => {
          const Icon = tab.icon
          const isActive = activeTab === tab.id
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
                isActive
                  ? 'bg-lsc-rose text-white'
                  : 'text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span className="hidden sm:inline">{tab.label}</span>
            </button>
          )
        })}
      </div>

      {/* Content */}
      <div className="mt-6">
        {activeTab === 'consortiums' && (
          <ConsortiumsTab token={token} onSelectConsortium={handleSelectConsortium} />
        )}
        {activeTab === 'members' && (
          <MembersTab token={token} selectedConsortium={selectedConsortium} />
        )}
        {activeTab === 'resources' && (
          <SharedResourcesTab token={token} selectedConsortium={selectedConsortium} />
        )}
        {activeTab === 'billing' && (
          <BillingTab token={token} selectedConsortium={selectedConsortium} />
        )}
        {activeTab === 'whitelabel' && (
          <WhiteLabelTab token={token} selectedConsortium={selectedConsortium} />
        )}
      </div>
    </AdminShell>
  )
}
