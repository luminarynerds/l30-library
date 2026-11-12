/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Achievements Page - Personal badges & progress
 * No leaderboards, no pressure - just celebrating progress
 */
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { Award, Lock, Star, Trophy, Flame, Beaker, Sparkles, ArrowLeft, Target, BookOpen, Heart, Zap, Share2, Clock } from 'lucide-react';
import { learningApi } from '../components/training';
import { useAuth } from '../contexts/AuthContext';
import clsx from 'clsx';
import toast from 'react-hot-toast';
import { t } from '@/i18n'

// Achievement type definition
interface Achievement {
  id: number;
  slug?: string;
  icon?: string;
  name: string;
  description: string;
  category?: string;
  xp_value: number;
  earned_at?: string;
}

// Icon mapping for achievement categories
const CATEGORY_ICONS: Record<string, typeof Award> = {
  course: Trophy,
  exploration: Star,
  streak: Flame,
  lab: Beaker,
  secret: Sparkles,
  milestone: Target,
  mastery: Zap,
  community: Heart,
  completionist: BookOpen,
};

const CATEGORY_COLORS: Record<string, string> = {
  course: 'text-lsc-rose bg-lsc-cream dark:bg-lsc-dark/30',
  exploration: 'text-earth-600 bg-earth-100 dark:bg-earth-800/30',
  streak: 'text-status-warning-500 bg-status-warning-100 dark:bg-status-warning-900/30',
  lab: 'text-lsc-rose bg-lsc-cream dark:bg-earth-800/30',
  secret: 'text-category-500 bg-category-100 dark:bg-category-900/30',
  milestone: 'text-status-success-500 bg-status-success-100 dark:bg-status-success-900/30',
  mastery: 'text-status-warning-500 bg-status-warning-100 dark:bg-status-warning-900/30',
  community: 'text-pink-500 bg-pink-100 dark:bg-pink-900/30',
  completionist: 'text-lsc-rose bg-lsc-rose/10 dark:bg-lsc-rose/20',
};

const CATEGORY_DESCRIPTIONS: Record<string, string> = {
  course: 'Complete courses to earn these badges',
  exploration: 'Discover new content and features',
  streak: 'Maintain learning consistency',
  lab: 'Develop AI literacy skills in interactive labs',
  secret: 'Hidden achievements for special accomplishments',
  milestone: 'Reach important learning milestones',
  mastery: 'Develop deep expertise and skill proficiency',
  community: 'Engage with fellow learners',
  completionist: 'Complete everything in a category',
};

export default function AchievementsPage() {
  const { isAuthenticated } = useAuth();
  
  const { data: myAchievements, isLoading: loadingMine } = useQuery({
    queryKey: ['my-achievements'],
    queryFn: learningApi.getAchievements,
    enabled: isAuthenticated,
  });

  const { data: allAchievements, isLoading: loadingAll } = useQuery({
    queryKey: ['all-achievements'],
    queryFn: learningApi.getAllAchievements,
    enabled: isAuthenticated,
  });

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-lsc-cream dark:bg-lsc-dark py-12 px-4">
        <div className="max-w-2xl mx-auto text-center">
          <Award aria-hidden="true" className="w-16 h-16 mx-auto text-lsc-rose mb-4" />
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4">
            Sign in to see your achievements
          </h1>
          <Link to="/account" className="inline-flex items-center gap-2 bg-lsc-rose text-white px-6 py-3 rounded-xl">
            Sign In
          </Link>
        </div>
      </div>
    );
  }

  const loading = loadingMine || loadingAll;
  const earnedIds = new Set(myAchievements?.map(a => a.id) || []);
  const earnedCount = myAchievements?.length || 0;
  const totalCount = allAchievements?.length || 0;

  // Group achievements by category
  const byCategory: Record<string, Achievement[]> = {};
  (allAchievements as Achievement[] | undefined)?.forEach((a) => {
    const cat = a.category || 'other';
    if (!byCategory[cat]) byCategory[cat] = [];
    byCategory[cat].push(a);
  });

  // Get recently earned (last 7 days)
  const recentlyEarned = myAchievements?.filter(a => {
    if (!a.earned_at) return false;
    const earnedDate = new Date(a.earned_at);
    const weekAgo = new Date();
    weekAgo.setDate(weekAgo.getDate() - 7);
    return earnedDate > weekAgo;
  }) || [];

  // Total XP from achievements
  const totalXP = myAchievements?.reduce((sum, a) => sum + (a.xp_value || 0), 0) || 0;

  const handleShare = async (achievement: Achievement) => {
    const shareText = `I just earned the "${achievement.name}" badge on the Library Learning Center!`;
    if (navigator.share) {
      try {
        await navigator.share({ title: achievement.name, text: shareText, url: window.location.href });
      } catch { /* User cancelled */ }
    } else {
      navigator.clipboard.writeText(shareText);
      toast.success(t('toast.achievements.copiedToClipboard'));
    }
  };

  return (
    <div className="min-h-screen bg-lsc-cream dark:bg-lsc-dark py-8 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <Link 
          to="/learn"
          className="inline-flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose dark:hover:text-lsc-rose mb-6"
        >
          <ArrowLeft aria-hidden="true" className="w-4 h-4" />
          Back to Learning
        </Link>

        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
          <div>
            <h1 className="text-3xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
              Your Achievements
            </h1>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
              Celebrating your learning journey
            </p>
          </div>
          
          {!loading && (
            <div className="flex gap-4">
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl px-6 py-4 shadow-sm border border-lsc-border dark:border-earth-700">
                <div className="text-center">
                  <p className="text-3xl font-bold text-lsc-rose dark:text-lsc-rose-light">
                    {earnedCount}
                  </p>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    of {totalCount} badges
                  </p>
                </div>
              </div>
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl px-6 py-4 shadow-sm border border-lsc-border dark:border-earth-700">
                <div className="text-center">
                  <p className="text-3xl font-bold text-lsc-rose dark:text-lsc-rose-light">
                    {totalXP}
                  </p>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    XP earned
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        {loading ? (
          <div className="space-y-4">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-32 bg-lsc-cream dark:bg-earth-800 rounded-xl motion-safe:animate-pulse" />
            ))}
          </div>
        ) : (
          <div className="space-y-8">
            {/* Recently Earned Section */}
            {recentlyEarned.length > 0 && (
              <section className="bg-gradient-to-r from-lsc-rose/10 to-yellow-500/10 dark:from-lsc-rose/5 dark:to-yellow-500/5 rounded-xl p-6">
                <h2 className="flex items-center gap-2 text-lg font-medium text-lsc-dark dark:text-lsc-cream mb-4">
                  <Clock className="w-5 h-5 text-lsc-rose" />
                  Recently Earned
                </h2>
                <div className="flex gap-4 overflow-x-auto pb-2">
                  {recentlyEarned.map((achievement) => {
                    const Icon = CATEGORY_ICONS[achievement.category ?? 'other'] || Award;
                    const colorClass = CATEGORY_COLORS[achievement.category ?? 'other'] || 'text-lsc-dark/70 dark:text-lsc-cream/70 bg-lsc-cream dark:bg-lsc-brown';
                    return (
                      <div
                        key={achievement.id}
                        className="flex-shrink-0 bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700 w-64"
                      >
                        <div className="flex items-center gap-3">
                          <div className={clsx('w-10 h-10 rounded-full flex items-center justify-center', colorClass)}>
                            <Icon className="w-5 h-5" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <h3 className="font-medium text-lsc-dark dark:text-lsc-cream truncate" title={achievement.name}>{achievement.name}</h3>
                            <p className="text-xs text-lsc-rose">+{achievement.xp_value} XP</p>
                          </div>
                          <button
                            onClick={() => handleShare(achievement)}
                            className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose"
                            title="Share achievement"
                          >
                            <Share2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </section>
            )}
            {Object.entries(byCategory).map(([category, achievements]) => {
              const Icon = CATEGORY_ICONS[category] || Award;
              const colorClass = CATEGORY_COLORS[category] || 'text-lsc-dark/70 dark:text-lsc-cream/70 bg-lsc-cream dark:bg-lsc-brown';
              const earnedInCategory = achievements.filter(a => earnedIds.has(a.id)).length;

              return (
                <section key={category}>
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h2 className="flex items-center gap-2 text-lg font-medium text-lsc-dark dark:text-lsc-cream capitalize">
                        <Icon aria-hidden="true" className="w-5 h-5" />
                        {category} Badges
                      </h2>
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                        {CATEGORY_DESCRIPTIONS[category] || ''}
                      </p>
                    </div>
                    <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      {earnedInCategory}/{achievements.length}
                    </span>
                  </div>
                  
                  <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
                    {achievements.map((achievement) => {
                      const earned = earnedIds.has(achievement.id);
                      const earnedData = myAchievements?.find(a => a.id === achievement.id);
                      
                      return (
                        <div
                          key={achievement.id}
                          className={clsx(
                            'relative rounded-xl p-4 border-2 transition-all',
                            earned
                              ? 'bg-lsc-white dark:bg-earth-800 border-lsc-border dark:border-earth-700 shadow-sm'
                              : 'bg-lsc-cream dark:bg-earth-800/50 border-lsc-border dark:border-earth-700 opacity-60'
                          )}
                        >
                          <div className="flex items-start gap-4">
                            <div className={clsx(
                              'w-12 h-12 rounded-full flex items-center justify-center flex-shrink-0',
                              earned ? colorClass : 'bg-lsc-cream dark:bg-lsc-brown text-lsc-dark/70 dark:text-lsc-cream/70'
                            )}>
                              {earned ? <Icon aria-hidden="true" className="w-6 h-6" /> : <Lock aria-hidden="true" className="w-5 h-5" />}
                            </div>
                            
                            <div className="flex-1 min-w-0">
                              <h3 className={clsx(
                                'font-medium truncate',
                                earned ? 'text-lsc-dark dark:text-lsc-cream' : 'text-lsc-dark/70 dark:text-lsc-cream/70'
                              )} title={achievement.name}>
                                {achievement.name}
                              </h3>
                              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 line-clamp-2" title={achievement.description}>
                                {achievement.description}
                              </p>
                              
                              <div className="mt-2 flex items-center gap-3 text-xs">
                                <span className={clsx(
                                  'font-medium',
                                  earned ? 'text-lsc-rose dark:text-lsc-rose-light' : 'text-lsc-dark/70'
                                )}>
                                  +{achievement.xp_value} XP
                                </span>
                                
                                {earned && earnedData?.earned_at && (
                                  <span className="text-lsc-dark/70 dark:text-lsc-cream/70">
                                    {new Date(earnedData.earned_at).toLocaleDateString()}
                                  </span>
                                )}
                                {earned && (
                                  <button
                                    onClick={(e) => { e.stopPropagation(); handleShare(achievement); }}
                                    className="ml-auto p-1 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose"
                                    title="Share"
                                  >
                                    <Share2 className="w-3 h-3" />
                                  </button>
                                )}
                              </div>
                            </div>
                          </div>
                          
                          {earned && (
                            <div className="absolute -top-2 -right-2">
                              <span className="flex items-center justify-center w-6 h-6 bg-lsc-rose text-white rounded-full">
                                <Star aria-hidden="true" className="w-3 h-3" />
                              </span>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </section>
              );
            })}
          </div>
        )}

        {/* Encouragement */}
        {!loading && earnedCount < totalCount && (
          <div className="mt-12 text-center py-8 bg-lsc-cream dark:bg-lsc-brown/20 rounded-xl">
            <p className="text-lsc-rose dark:text-lsc-cream/70">
              Keep learning at your own pace. Every lesson brings you closer to new achievements!
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
