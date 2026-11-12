/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/Button';
import { Textarea } from '@/components/ui/textarea';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Progress } from '@/components/ui/progress';
import {
  CheckCircle2,
  Circle,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Sparkles,
  Heart,
  Zap,
  Moon,
  Trophy,
} from 'lucide-react';
import { useTranslation } from '@/i18n'
import { fetchApi } from '@/api/fetchApi'

interface ChecklistItem {
  id: number;
  category: string;
  title: string;
  description?: string;
  status: 'pending' | 'completed' | 'skipped';
  order: number;
  required: boolean;
  notes?: string;
}

interface ShiftSession {
  id: number;
  items_completed: number;
  total_items: number;
  is_completed: boolean;
  checklist_items: ChecklistItem[];
  notes?: string;
}

const CATEGORY_CONFIG = {
  wrap_up: {
    icon: Zap,
    color: 'bg-earth-100 dark:bg-earth-800/30 text-earth-900 dark:text-lsc-rose-light/80',
    label: 'Wrap Up',
    emoji: '✅',
  },
  handoff: {
    icon: Heart,
    color: 'bg-category-100 dark:bg-category-900/30 text-category-900 dark:text-category-200',
    label: 'Hand Off',
    emoji: '🤝',
  },
  tomorrow: {
    icon: Zap,
    color: 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-900 dark:text-status-warning-200',
    label: "Tomorrow's Priorities",
    emoji: '📅',
  },
  mental: {
    icon: Moon,
    color: 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-900 dark:text-status-success-200',
    label: 'Mental Transition',
    emoji: '🧘',
  },
  celebration: {
    icon: Trophy,
    color: 'bg-pink-100 dark:bg-pink-900/30 text-pink-900 dark:text-pink-200',
    label: 'Celebrate Wins',
    emoji: '🎉',
  },
};

export function EndOfShiftChecklist() {
  const { t } = useTranslation()
  const [session, setSession] = useState<ShiftSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(
    new Set(['wrap_up', 'handoff'])
  );
  const [dailyWin, setDailyWin] = useState('');
  const [showWinForm, setShowWinForm] = useState(false);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [loggedWins, setLoggedWins] = useState<any[]>([]);

  const loadWins = async () => {
    try {
      const data = await fetchApi('/staff/daily-wins');
      setLoggedWins(data.wins || []);
    } catch (error) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)));
    }
  };


  const createNewSession = async () => {
    try {
      const data = await fetchApi('/staff/shift-sessions', {
        method: 'POST',
      });
      setSession(data);
    } catch (error) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)));
    }
  };

  const loadSession = async () => {
    try {
      const data = await fetchApi('/staff/shift-sessions/current');
      setSession(data);
    } catch (error) {
      const status = (error as { status?: number })?.status;
      if (status === 404) {
        // Create new session if none exists
        createNewSession();
      } else {
        Sentry.captureException(error instanceof Error ? error : new Error(String(error)));
      }
    } finally {
      setLoading(false);
    }
  };


  useEffect(() => {
    loadSession();
    loadWins();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleItemUpdate = async (itemId: number, newStatus: 'pending' | 'completed' | 'skipped', notes?: string) => {
    if (!session) return;

    try {
      await fetchApi(`/staff/checklist-items/${itemId}`, {
        method: 'PATCH',
        body: JSON.stringify({ status: newStatus, notes }),
      });

      // Update local state
      setSession({
        ...session,
        checklist_items: session.checklist_items.map((item) =>
          item.id === itemId ? { ...item, status: newStatus, ...(notes !== undefined ? { notes } : {}) } : item
        ),
        items_completed: session.checklist_items.filter(
          (i) => (i.id === itemId ? newStatus === 'completed' : i.status === 'completed')
        ).length,
      });
    } catch (error) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)));
    }
  };

  const handleLogWin = async () => {
    if (!dailyWin.trim()) return;

    try {
      await fetchApi('/staff/daily-wins', {
        method: 'POST',
        body: JSON.stringify({
          description: dailyWin,
          is_public: false,
          emoji: '🎉',
        }),
      });

      setDailyWin('');
      setShowWinForm(false);
      loadWins();
    } catch (error) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)));
    }
  };

  const handleCompleteShift = async () => {
    if (!session) return;

    try {
      await fetchApi(`/staff/shift-sessions/${session.id}/complete`, {
        method: 'POST',
      });
      setSession({ ...session, is_completed: true });
    } catch (error) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)));
    }
  };

  if (loading) {
    return <div className="text-center py-8">Loading checklist...</div>;
  }

  if (!session) {
    return <div className="text-center py-8">{t('components.staff.endOfShiftChecklist.failedToLoadShiftSession')}</div>;
  }

  const groupedItems: Record<string, ChecklistItem[]> = session.checklist_items.reduce((acc: Record<string, ChecklistItem[]>, item: ChecklistItem) => {
    const key = item.category;
    if (!acc[key]) acc[key] = [];
    acc[key].push(item);
    return acc;
  }, {});
  const completionPercentage = (session.items_completed / session.total_items) * 100;
  const requiredIncomplete = session.checklist_items.filter(
    (i) => i.required && i.status !== 'completed'
  );

  const toggleCategory = (category: string) => {
    const newExpanded = new Set(expandedCategories);
    if (newExpanded.has(category)) {
      newExpanded.delete(category);
    } else {
      newExpanded.add(category);
    }
    setExpandedCategories(newExpanded);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Sparkles className="w-6 h-6 text-status-warning-500" />
                End-of-Shift Wrap-Up
              </CardTitle>
              <CardDescription>
                Complete your shift wrap-up to leave on time and transition smoothly
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {/* Progress bar */}
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="font-medium">Progress</span>
                <span className="text-earth-600 dark:text-earth-400">
                  {session.items_completed} of {session.total_items} items
                </span>
              </div>
              <Progress value={completionPercentage} className="h-2" />
            </div>

            {/* Required items alert */}
            {requiredIncomplete.length > 0 && (
              <Alert className="bg-status-warning-50 dark:bg-status-warning-900/20 border-status-warning-200 dark:border-status-warning-800">
                <AlertCircle className="h-4 w-4 text-status-warning-600" />
                <AlertDescription className="text-status-warning-800 dark:text-status-warning-200">
                  You have {requiredIncomplete.length} required item{requiredIncomplete.length > 1 ? 's' : ''} to complete
                  before leaving.
                </AlertDescription>
              </Alert>
            )}

            {/* Completion message */}
            {session.is_completed && (
              <Alert className="bg-status-success-50 dark:bg-status-success-900/20 border-status-success-200 dark:border-status-success-800">
                <CheckCircle2 className="h-4 w-4 text-status-success-600" />
                <AlertDescription className="text-status-success-800 dark:text-status-success-200">
                  ✨ All done! Permission to leave on time granted. Great work today! 👋
                </AlertDescription>
              </Alert>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Checklist sections */}
      <div className="space-y-4">
        {Object.entries(groupedItems).map(([category, items]) => {
          const config = CATEGORY_CONFIG[category as keyof typeof CATEGORY_CONFIG];
          const categoryComplete = items?.every((i: ChecklistItem) => i.status !== 'pending') || false;

          return (


            <Card key={category} className={categoryComplete ? 'bg-earth-50 dark:bg-earth-900' : ''}>
              <button
                type="button"
                className="flex w-full items-center justify-between p-6 text-left cursor-pointer hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-800"
                onClick={() => toggleCategory(category)}
                aria-expanded={expandedCategories.has(category)}
              >
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg ${config.color}`}>
                    <span className="text-lg">{config.emoji}</span>
                  </div>
                  <div>
                    <h3 className="font-serif font-semibold">{config.label}</h3>
                    <p className="text-sm text-earth-600 dark:text-earth-400">
                      {items?.filter((i: ChecklistItem) => i.status === 'completed').length}/{items?.length} done
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {categoryComplete && <CheckCircle2 className="w-5 h-5 text-status-success-600" />}
                  {expandedCategories.has(category) ? (
                    <ChevronUp className="w-5 h-5" />
                  ) : (
                    <ChevronDown className="w-5 h-5" />
                  )}
                </div>
              </button>

              {expandedCategories.has(category) && (
                <CardContent className="border-t space-y-4">
                  {items?.map((item: ChecklistItem) => (
                    <div
                      key={item.id}
                      className={`flex gap-3 p-3 rounded-lg transition-colors ${
                        item.status === 'completed' ? 'bg-status-success-50 dark:bg-status-success-900/20' : 'bg-earth-50 dark:bg-earth-900 hover:bg-earth-100 dark:hover:bg-earth-700'
                      }`}
                    >
                      <div className="pt-1">
                        <button
                          onClick={() =>
                            handleItemUpdate(
                              item.id,
                              item.status === 'completed' ? 'pending' : 'completed'
                            )
                          }
                          aria-label={item.title}
                          aria-pressed={item.status === 'completed'}
                          className="flex-shrink-0"
                        >
                          {item.status === 'completed' ? (
                            <CheckCircle2 className="w-6 h-6 text-status-success-600" />
                          ) : (
                            <Circle className="w-6 h-6 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-earth-600 dark:hover:text-earth-300" />
                          )}
                        </button>
                      </div>

                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <p
                              className={`font-medium ${
                                item.status === 'completed'
                                  ? 'line-through text-earth-600 dark:text-earth-400'
                                  : ''
                              }`}
                            >
                              {item.title}
                              {item.required && (
                                <span className="ml-1 text-status-danger-500" title="Required">
                                  *
                                </span>
                              )}
                            </p>
                            {item.description && (
                              <p className="text-sm text-earth-600 dark:text-earth-400 mt-1">
                                {item.description}
                              </p>
                            )}
                          </div>
                        </div>

                        {item.notes && (
                          <div className="mt-2 p-2 bg-earth-50 dark:bg-earth-800/20 rounded text-sm text-earth-900 dark:text-lsc-rose-light/80">
                            {item.notes}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </CardContent>
              )}
            </Card>
          );
        })}
      </div>

      {/* Daily wins section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Trophy className="w-5 h-5 text-status-warning-500" />
            Celebrate Your Wins
          </CardTitle>
          <CardDescription>
            Log your accomplishments and celebrate what you achieved today
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {loggedWins.length > 0 && (
            <div className="space-y-2">
              <p className="text-sm font-medium">Today's wins:</p>
              {loggedWins.slice(0, 3).map((win) => (
                <div
                  key={win.id}
                  className="p-3 bg-status-warning-50 dark:bg-status-warning-900/20 rounded-lg border border-status-warning-200 dark:border-status-warning-800 flex items-start gap-2"
                >
                  <span className="text-xl mt-1">{win.emoji}</span>
                  <span className="text-sm">{win.description}</span>
                </div>
              ))}
            </div>
          )}

          {showWinForm ? (
            <div className="space-y-3 p-4 bg-pink-50 dark:bg-pink-900/20 rounded-lg border border-pink-200 dark:border-pink-800">
              <Textarea
                placeholder={t('components.staff.endOfShiftChecklist.whatDidYouAccomplishToday')}
                value={dailyWin}
                onChange={(e) => setDailyWin(e.target.value)}
                className="min-h-20"
              />
              <div className="flex gap-2">
                <Button
                  onClick={handleLogWin}
                  disabled={!dailyWin.trim()}
                  className="flex-1"
                  variant="default"
                >
                  Log Win 🎉
                </Button>
                <Button
                  onClick={() => setShowWinForm(false)}
                  variant="outline"
                  className="flex-1"
                >
                  Cancel
                </Button>
              </div>
            </div>
          ) : (
            <Button
              onClick={() => setShowWinForm(true)}
              variant="outline"
              className="w-full"
            >
              + Add a win to celebrate
            </Button>
          )}
        </CardContent>
      </Card>

      {/* Action buttons */}
      <div className="flex gap-2">
        {!session.is_completed ? (
          <>
            <Button
              onClick={handleCompleteShift}
              disabled={requiredIncomplete.length > 0}
              className="flex-1 bg-status-success-600 hover:bg-status-success-700"
            >
              <CheckCircle2 className="w-4 h-4 mr-2" />
              Complete Shift & Leave
            </Button>
          </>
        ) : (
          <Button disabled className="flex-1 bg-status-success-200 dark:bg-status-success-900/40 text-status-success-900 dark:text-status-success-200">
            <CheckCircle2 className="w-4 h-4 mr-2" />
            Shift Complete - You're done!
          </Button>
        )}
      </div>

      {/* Permission to leave */}
      {session.is_completed && (
        <Alert className="bg-earth-50 dark:bg-earth-800/20 border-lsc-border dark:border-earth-700">
          <Heart className="h-4 w-4 text-lsc-rose dark:text-lsc-rose-light" />
          <AlertDescription className="text-earth-900 dark:text-lsc-rose-light/80">
            <strong>{t('components.staff.endOfShiftChecklist.permissionToLeaveOnTime')}</strong> You've completed your end-of-shift
            wrap-up. Leave work at work and enjoy your time off! 👋
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
}
