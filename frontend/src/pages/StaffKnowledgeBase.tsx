/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useRef, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  BookOpen,
  HelpCircle,
  Video,
  CheckSquare2,
  MessageSquare,
  Bookmark,
  Flag,
  Zap,
} from 'lucide-react';
import KnowledgeBaseSearch from '../components/knowledge-base/KnowledgeBaseSearch';
import ArticleList from '../components/knowledge-base/ArticleList';
import DecisionTreeBrowser from '../components/knowledge-base/DecisionTreeBrowser';
import VideoTutorials from '../components/knowledge-base/VideoTutorials';
import OnboardingChecklist from '../components/knowledge-base/OnboardingChecklist';
import StaffQA from '../components/knowledge-base/StaffQA';
import BookmarkedArticles from '../components/knowledge-base/BookmarkedArticles';
import QuickAnswers from '../components/knowledge-base/QuickAnswers';
import ContentFlagsReview from '../components/knowledge-base/ContentFlagsReview';
import { useAuth } from '../contexts/AuthContext';
import { useEssentialsMode } from '../contexts/EssentialsModeContext';
import api from '../api/api';
import { AdminShell } from '../components/shells/AdminShell'
import { t } from '@/i18n'
import PageContainer from '@/components/layout/PageContainer'

type Tab =
  | 'quick-answers'
  | 'articles'
  | 'decision-trees'
  | 'videos'
  | 'onboarding'
  | 'qa'
  | 'bookmarks'
  | 'flags';

export default function StaffKnowledgeBase() {
  const [searchParams, setSearchParams] = useSearchParams();
  const SECTION_IDS: Tab[] = ['quick-answers','articles','decision-trees','videos','onboarding','qa','bookmarks','flags'];
  const rawSection = searchParams.get('section') as Tab | null;
  const activeTab: Tab = rawSection && SECTION_IDS.includes(rawSection) ? rawSection : 'quick-answers';
  const [searchQuery, setSearchQuery] = useState('');
  const { user } = useAuth();
  const { isEssentialsMode } = useEssentialsMode();
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);

  const isStaff =
    user?.role === 'staff' ||
    user?.role === 'admin' ||
    user?.role === 'super_admin';

  const { data: stats } = useQuery({
    queryKey: ['kb-stats'],
    queryFn: async () => {
      try {
        const [_articlesRes, flagsRes, qaRes] = await Promise.all([
          api.get('/staff-knowledge/articles', { params: { limit: 1 } }),
          api.get('/staff-knowledge/flags', { params: { status: 'pending' } }).catch(() => ({ data: [] })),
          api.get('/staff-knowledge/qa', { params: { answered_only: false, limit: 100 } }).catch(() => ({ data: [] })),
        ]);
        const unanswered = Array.isArray(qaRes.data)
          ? qaRes.data.filter((q: { is_answered: boolean }) => !q.is_answered).length
          : 0;
        return {
          pendingFlags: Array.isArray(flagsRes.data) ? flagsRes.data.length : 0,
          unansweredQuestions: unanswered,
        };
      } catch {
        return { pendingFlags: 0, unansweredQuestions: 0 };
      }
    },
  });

  // `lowPriority` tabs are de-emphasized (not removed) in EssentialsMode so the
  // high-value path (How Do I / Articles) leads while every panel stays reachable.
  const tabs = useMemo(() => {
    const all = [
      { id: 'quick-answers' as const, label: t('components.knowledgeBase.staffKnowledgeBase.tabs.howDoI', 'How Do I...?'), icon: Zap, lowPriority: false },
      { id: 'articles' as const, label: t('components.knowledgeBase.staffKnowledgeBase.tabs.articles', 'Articles & Policies'), icon: BookOpen, lowPriority: false },
      { id: 'decision-trees' as const, label: t('components.knowledgeBase.staffKnowledgeBase.tabs.decisionTrees', 'Decision Trees'), icon: HelpCircle, lowPriority: true },
      { id: 'videos' as const, label: t('components.knowledgeBase.staffKnowledgeBase.tabs.videos', 'Videos'), icon: Video, lowPriority: true },
      { id: 'onboarding' as const, label: t('components.knowledgeBase.staffKnowledgeBase.tabs.onboarding', 'Onboarding'), icon: CheckSquare2, lowPriority: true },
      { id: 'qa' as const, label: t('components.knowledgeBase.staffKnowledgeBase.tabs.askColleague', 'Ask a Colleague'), icon: MessageSquare, badge: stats?.unansweredQuestions, lowPriority: false },
      { id: 'bookmarks' as const, label: t('components.knowledgeBase.staffKnowledgeBase.tabs.bookmarks', 'Bookmarks'), icon: Bookmark, lowPriority: true },
      ...(isStaff
        ? [{ id: 'flags' as const, label: t('components.knowledgeBase.staffKnowledgeBase.tabs.flaggedContent', 'Flagged Content'), icon: Flag, badge: stats?.pendingFlags, lowPriority: true }]
        : []),
    ];
    // In EssentialsMode, surface the high-value tabs first (stable order otherwise).
    return isEssentialsMode
      ? [...all].sort((a, b) => Number(a.lowPriority) - Number(b.lowPriority))
      : all;
  }, [stats?.unansweredQuestions, stats?.pendingFlags, isStaff, isEssentialsMode]);

  const activeIndex = Math.max(0, tabs.findIndex(tab => tab.id === activeTab));

  const selectTab = (id: Tab) => {
    setSearchParams({ section: id }, { replace: false });
    setSearchQuery('');
  };

  // Roving tabindex with automatic activation: arrow/Home/End move focus and
  // switch the panel in one step (panels are react-query backed and cheap).
  const handleTabKeyDown = (e: React.KeyboardEvent<HTMLButtonElement>) => {
    let next = activeIndex;
    switch (e.key) {
      case 'ArrowRight':
      case 'ArrowDown':
        next = (activeIndex + 1) % tabs.length;
        break;
      case 'ArrowLeft':
      case 'ArrowUp':
        next = (activeIndex - 1 + tabs.length) % tabs.length;
        break;
      case 'Home':
        next = 0;
        break;
      case 'End':
        next = tabs.length - 1;
        break;
      default:
        return;
    }
    e.preventDefault();
    const nextTab = tabs[next];
    if (nextTab) {
      selectTab(nextTab.id);
      tabRefs.current[next]?.focus();
    }
  };

  const panelId = 'staff-kb-panel';
  const tabId = (id: Tab) => `staff-kb-tab-${id}`;

  return (
    <AdminShell title="Staff Knowledge Base">
    <div className="min-h-screen bg-lsc-cream dark:bg-earth-900">
      {/* Header */}
      <div className="bg-lsc-white dark:bg-earth-800 border-b border-lsc-border dark:border-earth-700">
        <PageContainer width="wide" className="py-6">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-3">
              <BookOpen className="w-8 h-8 text-lsc-rose dark:text-lsc-rose-light" />
              <div>
                {/* StaffLayout (via AdminShell title) already emits the page <h1>; this is a styled visual title only, demoted to avoid a duplicate h1. */}
                <p className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
                  {t('components.knowledgeBase.staffKnowledgeBase.title', 'Staff Knowledge Base')}
                </p>
                <p className="text-earth-600 dark:text-earth-400 text-sm mt-1">
                  {t('components.knowledgeBase.staffKnowledgeBase.subtitle', 'Policies, procedures, how-tos, and answers all in one place')}
                </p>
              </div>
            </div>

            {/* Quick Stats — hidden in EssentialsMode to reduce density (the badges and tabs still convey the same counts). */}
            {!isEssentialsMode && stats && (stats.pendingFlags > 0 || stats.unansweredQuestions > 0) && (
              <div className="hidden md:flex items-center gap-4">
                {stats.unansweredQuestions > 0 && (
                  <button
                    onClick={() => selectTab('qa')}
                    className="flex items-center gap-2 px-3 py-1.5 bg-earth-50 dark:bg-earth-800/20 border border-lsc-border dark:border-earth-700 rounded-lg text-sm text-lsc-rose dark:text-lsc-rose-light hover:bg-earth-100 dark:hover:bg-earth-800/30 transition"
                  >
                    <MessageSquare className="w-4 h-4" />
                    {`${stats.unansweredQuestions} ${t('components.knowledgeBase.staffKnowledgeBase.unanswered', 'unanswered')}`}
                  </button>
                )}
                {stats.pendingFlags > 0 && isStaff && (
                  <button
                    onClick={() => selectTab('flags')}
                    className="flex items-center gap-2 px-3 py-1.5 bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 rounded-lg text-sm text-status-warning-700 dark:text-status-warning-300 hover:bg-status-warning-100 dark:hover:bg-status-warning-900/30 transition"
                  >
                    <Flag className="w-4 h-4" />
                    {`${stats.pendingFlags} ${t('components.knowledgeBase.staffKnowledgeBase.flagsPending', 'flags pending')}`}
                  </button>
                )}
              </div>
            )}
          </div>

        </PageContainer>
      </div>

      {/* Persistent global search — hidden on quick-answers (which has its own search form) */}
      {activeTab !== 'quick-answers' && (
        <PageContainer width="wide" className="pt-4 pb-2">
          <KnowledgeBaseSearch
            query={searchQuery}
            onQueryChange={setSearchQuery}
            onSubmit={() => selectTab('articles')}
          />
        </PageContainer>
      )}

      {/* Navigation Tabs */}
      <div className="bg-lsc-white dark:bg-earth-800 border-b border-lsc-border dark:border-earth-700 sticky top-0 z-10">
        <PageContainer width="wide">
          <div
            role="tablist"
            aria-label={t('aria.staffKnowledgeBase.knowledgeBaseSections')}
            aria-orientation="horizontal"
            className="flex flex-wrap gap-2 py-2"
          >
            {tabs.map((tab, index) => {
              const Icon = tab.icon;
              const badge = 'badge' in tab ? tab.badge : undefined;
              const isActive = activeTab === tab.id;
              // De-emphasize low-priority tabs in EssentialsMode (still rendered + reachable).
              const deemphasized = isEssentialsMode && tab.lowPriority && !isActive;
              return (
                <button
                  key={tab.id}
                  ref={el => { tabRefs.current[index] = el; }}
                  id={tabId(tab.id)}
                  role="tab"
                  type="button"
                  aria-selected={isActive}
                  aria-controls={panelId}
                  tabIndex={isActive ? 0 : -1}
                  onClick={() => selectTab(tab.id)}
                  onKeyDown={handleTabKeyDown}
                  className={`flex items-center gap-2 px-3.5 py-2 rounded-full font-medium text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2 dark:focus-visible:ring-offset-earth-800 ${
                    isActive
                      ? 'bg-lsc-rose text-white'
                      : 'bg-earth-100 text-earth-700 hover:bg-earth-200 dark:bg-earth-700 dark:text-earth-200 dark:hover:bg-earth-600'
                  } ${deemphasized ? 'opacity-60' : ''}`}
                >
                  <Icon className="w-4 h-4" aria-hidden />
                  {tab.label}
                  {/* Badge counts are decluttered in EssentialsMode. */}
                  {!isEssentialsMode && badge !== undefined && badge > 0 && (
                    <span className="ml-1 px-1.5 py-0.5 bg-status-danger-500 text-white text-xs font-bold rounded-full min-w-[20px] text-center">
                      {badge}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </PageContainer>
      </div>

      {/* Content */}
      <PageContainer width="wide" className="py-8 outline-none" id={panelId} role="tabpanel" aria-labelledby={tabId(activeTab)} tabIndex={0}>
        {activeTab === 'quick-answers' && <QuickAnswers />}
        {activeTab === 'articles' && <ArticleList searchQuery={searchQuery} />}
        {activeTab === 'decision-trees' && <DecisionTreeBrowser />}
        {activeTab === 'videos' && <VideoTutorials />}
        {activeTab === 'onboarding' && <OnboardingChecklist />}
        {activeTab === 'qa' && <StaffQA />}
        {activeTab === 'bookmarks' && <BookmarkedArticles />}
        {activeTab === 'flags' && isStaff && <ContentFlagsReview />}
      </PageContainer>
    </div>
    </AdminShell>
  );
}
