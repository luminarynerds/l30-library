/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * FamilyOverview Component
 *
 * Displays comprehensive household information including linked accounts,
 * pending link requests, and aggregated household data (holds, checkouts, fines).
 */

import React, { useEffect, useState } from 'react';
import { Users, AlertCircle, Loader, Plus } from 'lucide-react';
import { LinkFamilyAccountForm } from './LinkFamilyAccountForm';
import { PendingLinksList } from './PendingLinksList';
import { useTranslation } from '@/i18n'
import { fetchApi } from '@/api/fetchApi'

interface LinkedAccountInfo {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
  relationship: string;
  link_status: string;
  linked_at?: string;
}

interface HouseholdData {
  viewing_as_user_id: number;
  viewing_as_name: string;
  relationship: string;
  household_id?: number;
  household_members: LinkedAccountInfo[];
  pending_requests: unknown[];
  holds: unknown[];
  checkouts: unknown[];
  fines: unknown[];
  total_holds: number;
  total_checkouts: number;
  total_fines_amount: number;
}

interface FamilyOverviewProps {
  onClose?: () => void;
}

export const FamilyOverview: React.FC<FamilyOverviewProps> = ({ onClose }) => {
  const { t } = useTranslation()
  const [householdData, setHouseholdData] = useState<HouseholdData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showLinkForm, setShowLinkForm] = useState(false);

  const fetchHouseholdData = async () => {
    setLoading(true);
    setError(null);

    try {
      const data = await fetchApi('/households/me');
      setHouseholdData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load household data');
    } finally {
      setLoading(false);
    }
  };


  useEffect(() => {
    fetchHouseholdData();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12 gap-2 text-lsc-dark/70 dark:text-lsc-cream/70">
        <Loader className="w-5 h-5 motion-safe:animate-spin" />
        <span>Loading family information...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-lg">
        <div className="flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-status-danger-600 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-status-danger-800 dark:text-status-danger-300">{error}</div>
        </div>
      </div>
    );
  }

  if (!householdData) {
    return (
      <div className="text-center text-lsc-dark/70 dark:text-lsc-cream/70 py-8">
        <p>{t('components.account.familyOverview.unableToLoadHouseholdInformation')}</p>
      </div>
    );
  }

  const isParent = householdData.relationship === 'parent';
  const hasLinkedAccounts = householdData.household_members.length > 1;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
            <Users className="w-6 h-6" />
            Family Account
          </h2>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
            {isParent ? 'Manage your family accounts' : 'View linked family account'}
          </p>
        </div>
      </div>

      {/* Family account reassurance for parents */}
      {isParent && (
        <div className="p-4 bg-status-success-50 dark:bg-status-success-900/10 border border-status-success-200 dark:border-status-success-800 rounded-lg">
          <p className="text-sm text-status-success-800 dark:text-status-success-200">
            <span className="font-medium">{t('components.account.familyOverview.yourChildrenSAccountsAre')}</span>{' '}
            As a parent, you can view their checkouts, holds, and fines all from here.
            Children's reading history is protected and never shared outside your family.
            Kids can browse and place holds freely - you'll see everything in one place.
          </p>
        </div>
      )}

      {/* Linked Accounts */}
      {hasLinkedAccounts && (
        <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg p-6">
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">Linked Accounts</h3>
          <div className="space-y-3">
            {householdData.household_members.map((member) => (
              <div key={member.id} className="flex items-center justify-between p-3 bg-earth-50 dark:bg-earth-900 rounded">
                <div>
                  <p className="font-medium text-lsc-dark dark:text-lsc-cream">
                    {member.first_name} {member.last_name}
                  </p>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{member.email}</p>
                </div>
                <span className="text-xs font-medium bg-earth-100 dark:bg-earth-800/30 text-earth-800 dark:text-lsc-rose-light px-2.5 py-1 rounded">
                  {member.relationship === 'parent' ? 'Parent' : 'Child'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Pending Link Requests (for parents) */}
      {isParent && householdData.pending_requests.length > 0 && (
        <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg p-6">
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
            Pending Link Requests ({householdData.pending_requests.length})
          </h3>
          <PendingLinksList onLinkApproved={fetchHouseholdData} onLinkDeclined={fetchHouseholdData} />
        </div>
      )}

      {/* Request Link (for children) */}
      {householdData.relationship !== 'parent' && !hasLinkedAccounts && (
        <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg p-6">
          <div className="flex items-start justify-between mb-4">
            <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">{t('components.account.familyOverview.linkToParentAccount')}</h3>
            {!showLinkForm && (
              <button
                onClick={() => setShowLinkForm(true)}
                className="flex items-center gap-2 px-3 py-1.5 text-sm bg-lsc-rose text-white rounded hover:bg-lsc-rose/90"
              >
                <Plus className="w-4 h-4" />
                New Link Request
              </button>
            )}
          </div>

          {showLinkForm ? (
            <LinkFamilyAccountForm
              onSuccess={() => {
                setShowLinkForm(false);
                fetchHouseholdData();
              }}
              onCancel={() => setShowLinkForm(false)}
            />
          ) : (
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
              Request to link your account to your parent's account to access shared family
              features.
            </p>
          )}
        </div>
      )}

      {/* Aggregated Household Data */}
      {hasLinkedAccounts && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Holds Summary */}
          <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg p-4">
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Total Holds</p>
            <p className="text-3xl font-bold text-lsc-dark dark:text-lsc-cream mt-2">
              {householdData.total_holds}
            </p>
            {householdData.holds.length > 0 && (
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">
                {householdData.holds.length} items on hold across family
              </p>
            )}
          </div>

          {/* Checkouts Summary */}
          <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg p-4">
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Total Checkouts</p>
            <p className="text-3xl font-bold text-lsc-dark dark:text-lsc-cream mt-2">
              {householdData.total_checkouts}
            </p>
            {householdData.checkouts.length > 0 && (
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">
                {householdData.checkouts.length} items checked out
              </p>
            )}
          </div>

          {/* Fines Summary */}
          <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg p-4">
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Total Fines</p>
            <p className="text-3xl font-bold text-lsc-dark dark:text-lsc-cream mt-2">
              ${householdData.total_fines_amount.toFixed(2)}
            </p>
            {householdData.total_fines_amount > 0 ? (
              <p className="text-xs text-status-warning-700 dark:text-status-warning-400 mt-2">
                Combined family balance - pay at any branch or online
              </p>
            ) : (
              <p className="text-xs text-status-success-600 dark:text-status-success-400 mt-2">
                No fines across the family!
              </p>
            )}
          </div>
        </div>
      )}

      {/* Empty State */}
      {!hasLinkedAccounts && householdData.relationship === 'self' && (
        <div className="bg-earth-50 dark:bg-earth-800/20 border border-lsc-border dark:border-earth-700 rounded-lg p-6">
          <div className="flex items-start gap-3">
            <Users className="w-6 h-6 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0 mt-0.5" />
            <div>
              <h4 className="font-serif font-semibold text-earth-900 dark:text-lsc-rose-light/80">{t('components.account.familyOverview.getStartedWithFamilyLinking')}</h4>
              <p className="text-sm text-earth-800 dark:text-lsc-rose-light mt-1">
                Link your account with family members to share holds, checkouts, and manage fines
                together. Request to link to a parent's account or wait for link requests from
                children.
              </p>
              <button
                onClick={() => setShowLinkForm(true)}
                className="mt-3 px-4 py-2 bg-lsc-rose text-white rounded hover:bg-lsc-rose/90 text-sm font-medium"
              >
                Request Family Link
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Close Button */}
      {onClose && (
        <div className="flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded hover:bg-earth-50 dark:hover:bg-earth-800"
          >
            Close
          </button>
        </div>
      )}
    </div>
  );
};
