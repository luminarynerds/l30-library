/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/* eslint-disable react-refresh/only-export-components */
/**
 * WhatsNewBanner - Training Alerts Component
 *
 * Displays new courses, features, and updates to users.
 * Dismissible with localStorage persistence to remember user preferences.
 */
import { useState, useCallback } from 'react'
import { Link } from 'react-router-dom';
import {
  X,
  Sparkles,
  BookOpen,
  Megaphone,
  Lightbulb,
  RefreshCw,
  ChevronRight,
  Bell,
  ArrowRight,
} from 'lucide-react';
import { useTranslation} from '@/i18n'

export type AnnouncementType = 'new_course' | 'new_feature' | 'content_update' | 'tip' | 'announcement';

export interface TrainingAnnouncement {
  id: string;
  title: string;
  description: string;
  type: AnnouncementType;
  linkUrl?: string;
  linkText?: string;
  courseId?: number;
  priority?: number;
  createdAt: string;
}

interface WhatsNewBannerProps {
  /** Announcements to display */
  announcements?: TrainingAnnouncement[];
  /** Whether to show a compact single-line banner or expandable list */
  variant?: 'banner' | 'list' | 'card';
  /** Maximum number of items to show */
  maxItems?: number;
  /** Custom storage key for dismissed items */
  storageKey?: string;
  /** Callback when announcement is dismissed */
  onDismiss?: (id: string) => void;
  /** Callback when "View All" is clicked */
  onViewAll?: () => void;
}

const STORAGE_KEY_PREFIX = 'lsc_training_dismissed_';

const typeIcons: Record<AnnouncementType, React.ReactNode> = {
  new_course: <BookOpen className="w-5 h-5" aria-hidden="true" />,
  new_feature: <Sparkles className="w-5 h-5" aria-hidden="true" />,
  content_update: <RefreshCw className="w-5 h-5" aria-hidden="true" />,
  tip: <Lightbulb className="w-5 h-5" aria-hidden="true" />,
  announcement: <Megaphone className="w-5 h-5" aria-hidden="true" />,
};

const typeLabels: Record<AnnouncementType, string> = {
  new_course: 'New Course',
  new_feature: 'New Feature',
  content_update: 'Updated',
  tip: 'Quick Tip',
  announcement: 'Announcement',
};

const typeColors: Record<AnnouncementType, string> = {
  new_course: 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-300',
  new_feature: 'bg-category-100 text-category-800 dark:bg-category-900/30 dark:text-category-300',
  content_update: 'bg-earth-100 text-earth-800 dark:bg-earth-800/30 dark:text-lsc-rose-light',
  tip: 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-300',
  announcement: 'bg-lsc-rose/10 text-lsc-rose',
};

function getDismissedIds(storageKey: string): Set<string> {
  try {
    const stored = localStorage.getItem(storageKey);
    if (stored) {
      const parsed = JSON.parse(stored);
      return new Set(parsed.ids || []);
    }
  } catch {
    // Ignore parse errors
  }
  return new Set();
}

function saveDismissedIds(storageKey: string, ids: Set<string>): void {
  try {
    localStorage.setItem(storageKey, JSON.stringify({
      ids: Array.from(ids),
      lastUpdated: new Date().toISOString(),
    }));
  } catch {
    // Ignore storage errors
  }
}

export function WhatsNewBanner({
  announcements = [],
  variant = 'banner',
  maxItems = 3,
  storageKey = 'whats_new',
  onDismiss,
  onViewAll,
}: WhatsNewBannerProps) {
  const { t } = useTranslation()
  const fullStorageKey = `${STORAGE_KEY_PREFIX}${storageKey}`;
  const [dismissedIds, setDismissedIds] = useState<Set<string>>(() => getDismissedIds(fullStorageKey));
  const [isExpanded, setIsExpanded] = useState(false);

  // Filter out dismissed announcements
  const visibleAnnouncements = announcements
    .filter(a => !dismissedIds.has(a.id))
    .sort((a, b) => (b.priority || 0) - (a.priority || 0))
    .slice(0, maxItems);

  const handleDismiss = useCallback((id: string) => {
    setDismissedIds(prev => {
      const newSet = new Set(prev);
      newSet.add(id);
      saveDismissedIds(fullStorageKey, newSet);
      return newSet;
    });
    onDismiss?.(id);
  }, [fullStorageKey, onDismiss]);

  const handleDismissAll = () => {
    const allIds = new Set(announcements.map(a => a.id));
    setDismissedIds(allIds);
    saveDismissedIds(fullStorageKey, allIds);
    announcements.forEach(a => onDismiss?.(a.id));
  };

  // Don't render if no visible announcements
  if (visibleAnnouncements.length === 0) {
    return null;
  }

  if (variant === 'banner') {
    const announcement = visibleAnnouncements[0]!;
    return (
      <div
        className="relative bg-gradient-to-r from-lsc-rose/10 to-lsc-cream dark:from-lsc-rose/20 dark:to-earth-800 rounded-xl p-4 border border-lsc-rose/20"
        role="region"
        aria-label={t('components.training.whatsNewBanner.whatSNewInTraining')}
      >
        <div className="flex items-start gap-4">
          <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-lsc-rose/20 flex items-center justify-center text-lsc-rose">
            {typeIcons[announcement.type]}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${typeColors[announcement.type]}`}>
                {typeLabels[announcement.type]}
              </span>
              {visibleAnnouncements.length > 1 && (
                <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                  +{visibleAnnouncements.length - 1} more
                </span>
              )}
            </div>
            <h3 className="font-medium text-lsc-dark dark:text-lsc-cream">
              {announcement.title}
            </h3>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1 line-clamp-2" title={announcement.description}>
              {announcement.description}
            </p>
            {announcement.linkUrl && (
              <Link
                to={announcement.linkUrl}
                className="inline-flex items-center gap-1 mt-2 text-sm text-lsc-rose hover:text-lsc-rose/80 font-medium"
                aria-label={announcement.linkText ? undefined : `Learn more about ${announcement.title}`}
              >
                {announcement.linkText || 'Learn more'}
                <ArrowRight className="w-4 h-4" aria-hidden="true" />
              </Link>
            )}
          </div>
          <button
            onClick={() => handleDismiss(announcement.id)}
            className="flex-shrink-0 p-1.5 rounded-lg text-lsc-dark/70 hover:text-lsc-dark hover:bg-lsc-dark/10 dark:text-lsc-cream/70 dark:hover:text-lsc-cream dark:hover:bg-lsc-cream/10 transition-colors"
            aria-label={t('aria.training.dismissThisAnnouncement')}
          >
            <X className="w-5 h-5" aria-hidden="true" />
          </button>
        </div>
      </div>
    );
  }

  if (variant === 'list') {
    return (
      <div
        className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 overflow-hidden"
        role="region"
        aria-label={t('components.training.whatsNewBanner.whatSNewInTraining2')}
      >
        <div className="p-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Bell className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
            <h2 className="font-serif font-bold text-lsc-dark dark:text-lsc-cream">
              What's New
            </h2>
            <span className="px-2 py-0.5 bg-lsc-rose/10 text-lsc-rose rounded-full text-xs font-medium">
              {visibleAnnouncements.length}
            </span>
          </div>
          <div className="flex items-center gap-2">
            {onViewAll && (
              <button
                onClick={onViewAll}
                className="text-sm text-lsc-rose hover:text-lsc-rose/80"
              >
                View All
              </button>
            )}
            <button
              onClick={handleDismissAll}
              className="text-xs text-lsc-dark/70 hover:text-lsc-dark dark:text-lsc-cream/70 dark:hover:text-lsc-cream"
            >
              Dismiss All
            </button>
          </div>
        </div>
        <ul className="divide-y divide-lsc-border dark:divide-earth-700">
          {visibleAnnouncements.map((announcement) => (
            <li key={announcement.id} className="p-4 hover:bg-lsc-cream/50 dark:hover:bg-lsc-brown/20 transition-colors">
              <div className="flex items-start gap-3">
                <div className={`flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center ${typeColors[announcement.type]}`}>
                  {typeIcons[announcement.type]}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${typeColors[announcement.type]}`}>
                      {typeLabels[announcement.type]}
                    </span>
                  </div>
                  <h3 className="font-medium text-sm text-lsc-dark dark:text-lsc-cream">
                    {announcement.title}
                  </h3>
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-0.5 line-clamp-2" title={announcement.description}>
                    {announcement.description}
                  </p>
                  {announcement.linkUrl && (
                    <Link
                      to={announcement.linkUrl}
                      className="inline-flex items-center gap-1 mt-2 text-xs text-lsc-rose hover:text-lsc-rose/80"
                    >
                      {announcement.linkText || 'View'}
                      <ChevronRight className="w-3 h-3" aria-hidden="true" />
                    </Link>
                  )}
                </div>
                <button
                  onClick={() => handleDismiss(announcement.id)}
                  className="flex-shrink-0 p-1 rounded text-lsc-dark/70 hover:text-lsc-dark dark:text-lsc-cream/70 dark:hover:text-lsc-cream transition-colors"
                  aria-label={`Dismiss ${announcement.title}`}
                >
                  <X className="w-4 h-4" aria-hidden="true" />
                </button>
              </div>
            </li>
          ))}
        </ul>
      </div>
    );
  }

  // Card variant - compact expandable card
  return (
    <div
      className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm border border-lsc-border dark:border-earth-700"
      role="region"
      aria-label={t('components.training.whatsNewBanner.whatSNewInTraining3')}
    >
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between"
        aria-expanded={isExpanded}
      >
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-lsc-rose/10 flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-lsc-rose" aria-hidden="true" />
          </div>
          <div className="text-left">
            <h3 className="font-medium text-sm text-lsc-dark dark:text-lsc-cream">
              What's New
            </h3>
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
              {visibleAnnouncements.length} update{visibleAnnouncements.length !== 1 ? 's' : ''}
            </p>
          </div>
        </div>
        <ChevronRight
          className={`w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70 transition-transform ${isExpanded ? 'rotate-90' : ''}`}
          aria-hidden="true"
        />
      </button>

      {isExpanded && (
        <div className="mt-4 space-y-3">
          {visibleAnnouncements.map((announcement) => (
            <div
              key={announcement.id}
              className="flex items-start gap-3 p-3 bg-lsc-cream/50 dark:bg-lsc-brown/20 rounded-lg"
            >
              <div className={`flex-shrink-0 w-6 h-6 rounded flex items-center justify-center ${typeColors[announcement.type]}`}>
                {typeIcons[announcement.type]}
              </div>
              <div className="flex-1 min-w-0">
                <h4 className="font-medium text-sm text-lsc-dark dark:text-lsc-cream">
                  {announcement.title}
                </h4>
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-0.5">
                  {announcement.description}
                </p>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleDismiss(announcement.id);
                }}
                className="flex-shrink-0 p-1 rounded text-lsc-dark/70 hover:text-lsc-dark dark:text-lsc-cream/70 dark:hover:text-lsc-cream"
                aria-label={`Dismiss ${announcement.title}`}
              >
                <X className="w-4 h-4" aria-hidden="true" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function useWhatsNewAnnouncements(storageKey = 'whats_new') {
  const fullStorageKey = `${STORAGE_KEY_PREFIX}${storageKey}`;
  const [dismissedIds, setDismissedIds] = useState<Set<string>>(() => getDismissedIds(fullStorageKey));

  const dismiss = useCallback((id: string) => {
    setDismissedIds(prev => {
      const newSet = new Set(prev);
      newSet.add(id);
      saveDismissedIds(fullStorageKey, newSet);
      return newSet;
    });
  }, [fullStorageKey]);

  const clearDismissed = useCallback(() => {
    setDismissedIds(new Set());
    localStorage.removeItem(fullStorageKey);
  }, [fullStorageKey]);

  const isDismissed = useCallback((id: string) => dismissedIds.has(id), [dismissedIds]);

  return {
    dismissedIds,
    dismiss,
    clearDismissed,
    isDismissed,
  };
}

export default WhatsNewBanner;
