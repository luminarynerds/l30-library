/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Check, Clock, AlertCircle } from 'lucide-react';
import api from '../../api/api';
import { useAuth } from '../../contexts/AuthContext';
import { useTranslation } from '@/i18n'
import { useUnifiedAccessibility } from '@/features/accessibility/hooks/useUnifiedAccessibility'

interface ChecklistItem {
  id: string;
  title: string;
  description: string;
  due_days: number;
  completed: boolean;
  completed_at: string | null;
}

interface Checklist {
  id: number;
  user_id: number;
  title: string;
  description: string;
  checklist_items: ChecklistItem[];
  is_completed: boolean;
  start_date: string;
  completed_date: string | null;
  created_at: string;
  updated_at: string;
}

export default function OnboardingChecklist() {
  const { t } = useTranslation()
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const { announceToScreenReader } = useUnifiedAccessibility();
  const userId = user?.id;

  const { data: checklists, isLoading } = useQuery({
    queryKey: ['onboarding-checklists', userId],
    queryFn: async () => {
      if (!userId) return [];
      return await api.get<Checklist[]>(`/staff-knowledge/onboarding-checklists/user/${userId}`);
    },
    enabled: !!userId,
  });

  const updateMutation = useMutation({
    mutationFn: async (data: { checklist_id: number; items: ChecklistItem[] }) => {
      await api.put(`/staff-knowledge/onboarding-checklists/${data.checklist_id}`, {
        checklist_items: data.items,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['onboarding-checklists', userId] });
    },
  });

  const toggleItem = (checklist: Checklist, itemId: string) => {
    const newItems = checklist.checklist_items.map(item =>
      item.id === itemId
        ? {
            ...item,
            completed: !item.completed,
            completed_at: !item.completed ? new Date().toISOString() : null,
          }
        : item
    );
    updateMutation.mutate({ checklist_id: checklist.id, items: newItems });
    // Announce the new progress optimistically; the query invalidation that
    // refreshes the bar is async, so derive the count from newItems, not state.
    const completed = newItems.filter(item => item.completed).length;
    announceToScreenReader(
      `${completed} ${t('components.knowledgeBase.onboardingChecklist.of', 'of')} ${newItems.length} ${t('components.knowledgeBase.onboardingChecklist.complete', 'complete')}`
    );
  };

  if (isLoading) {
    return (
      <div className="text-center py-12" role="status">
        <div className="inline-block motion-safe:animate-spin rounded-full h-8 w-8 border-b-2 border-lsc-rose"></div>
        <span className="sr-only">{t('components.knowledgeBase.onboardingChecklist.loading', 'Loading checklists...')}</span>
      </div>
    );
  }

  if (!checklists || checklists.length === 0) {
    return (
      <div className="text-center py-12 bg-earth-50 dark:bg-earth-900 rounded-lg border border-lsc-border dark:border-earth-700">
        <p className="text-earth-600 dark:text-earth-400">{t('components.knowledgeBase.onboardingChecklist.noOnboardingChecklistsAssignedYet')}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {checklists.map(checklist => {
        const completedItems = checklist.checklist_items.filter(item => item.completed).length;
        const totalItems = checklist.checklist_items.length;
        const progressPercent = (completedItems / totalItems) * 100;
        const progressLabel = `${checklist.title}: ${completedItems} ${t('components.knowledgeBase.onboardingChecklist.of', 'of')} ${totalItems} ${t('components.knowledgeBase.onboardingChecklist.complete', 'complete')}`;
        return (
          <div
            key={checklist.id}
            className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg p-6"
          >
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-1">
                  {checklist.title}
                </h3>
                {checklist.description && (
                  <p className="text-earth-600 dark:text-earth-400 text-sm">{checklist.description}</p>
                )}
              </div>
              {checklist.is_completed && (
                <div className="bg-status-success-100 dark:bg-status-success-900/30 border border-status-success-300 dark:border-status-success-700 rounded-full p-3">
                  <Check className="w-6 h-6 text-status-success-600" aria-hidden="true" />
                </div>
              )}
            </div>

            {/* Progress Bar */}
            <div className="mb-6">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-earth-600 dark:text-earth-400">
                  {`${t('components.knowledgeBase.onboardingChecklist.progress', 'Progress')}: ${completedItems}/${totalItems}`}
                </span>
                <span className="text-sm text-earth-600 dark:text-earth-400">
                  {Math.round(progressPercent)}%
                </span>
              </div>
              <div
                className="w-full bg-earth-200 dark:bg-earth-600 rounded-full h-2"
                role="progressbar"
                aria-valuenow={completedItems}
                aria-valuemin={0}
                aria-valuemax={totalItems}
                aria-label={progressLabel}
              >
                <div
                  className={`h-2 rounded-full transition-all ${
                    progressPercent === 100 ? 'bg-status-success-600' : 'bg-lsc-rose'
                  }`}
                  style={{ width: `${progressPercent}%` }}
                ></div>
              </div>
            </div>

            {/* Checklist Items */}
            <div className="space-y-3">
              {checklist.checklist_items.map(item => {
                const itemDueDate = new Date(checklist.start_date);
                itemDueDate.setDate(itemDueDate.getDate() + item.due_days);
                const isOverdue =
                  !item.completed && new Date() > itemDueDate;

                return (
                  <div
                    key={item.id}
                    className={`flex items-start gap-3 p-3 rounded-lg border ${
                      item.completed
                        ? 'bg-status-success-50 dark:bg-status-success-900/20 border-status-success-200 dark:border-status-success-800'
                        : isOverdue
                          ? 'bg-status-danger-50 dark:bg-status-danger-900/20 border-status-danger-200 dark:border-status-danger-800'
                          : 'bg-earth-50 dark:bg-earth-900 border-lsc-border dark:border-earth-700'
                    }`}
                  >
                    <button
                      type="button"
                      role="checkbox"
                      aria-checked={item.completed}
                      aria-label={item.title}
                      onClick={() => toggleItem(checklist, item.id)}
                      className={`mt-1 flex-shrink-0 w-5 h-5 rounded border-2 flex items-center justify-center transition focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose ${
                        item.completed
                          ? 'bg-status-success-600 border-status-success-600'
                          : isOverdue
                            ? 'border-status-danger-400 hover:border-status-danger-600'
                            : 'border-lsc-border dark:border-earth-700 hover:border-lsc-rose/50'
                      }`}
                    >
                      {item.completed && (
                        <Check className="w-3 h-3 text-white" aria-hidden="true" />
                      )}
                    </button>
                    <div className="flex-1 min-w-0">
                      <p
                        className={`font-medium ${
                          item.completed
                            ? 'text-earth-600 dark:text-earth-400 line-through'
                            : 'text-lsc-dark dark:text-lsc-cream'
                        }`}
                      >
                        {item.title}
                      </p>
                      {item.description && (
                        <p className="text-sm text-earth-600 dark:text-earth-400 mt-1">
                          {item.description}
                        </p>
                      )}
                      <div className="flex items-center gap-2 mt-2 text-xs text-earth-600 dark:text-earth-400">
                        <Clock className="w-3 h-3" aria-hidden="true" />
                        {`${t('components.knowledgeBase.onboardingChecklist.dueIn', 'Due in')} ${item.due_days} ${t('components.knowledgeBase.onboardingChecklist.days', 'days')}`}
                        {item.completed && (
                          <span className="ml-2 text-status-success-700 dark:text-status-success-300 font-medium">
                            {t('components.knowledgeBase.onboardingChecklist.completed', 'Completed')}
                          </span>
                        )}
                        {isOverdue && (
                          <span className="ml-2 text-status-danger-700 dark:text-status-danger-300 font-medium flex items-center gap-1">
                            <AlertCircle className="w-3 h-3" aria-hidden="true" />
                            {t('components.knowledgeBase.onboardingChecklist.overdue', 'Overdue')}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
