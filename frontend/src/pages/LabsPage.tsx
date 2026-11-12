/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * AI Labs Hub - Fun, interactive AI literacy games
 * "Learn by playing, not by reading"
 */
import { Link } from 'react-router-dom';
import {
  Camera, MessageSquareWarning, Wand2, PenTool,
  Clock, ArrowRight, Zap, GraduationCap
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useTranslation } from '@/i18n'

const LABS = [
  {
    slug: 'real-or-fake',
    titleKey: 'labs.realOrFakeTitle',
    title: 'Real or Fake?',
    subtitleKey: 'labs.realOrFakeSubtitle',
    subtitle: 'Deepfake Detective',
    descriptionKey: 'labs.canYouSpotAiGenerated',
    description: 'Can you spot AI-generated images? Test your eye against the machines.',
    icon: Camera,
    color: 'from-pink-500 to-rose-500',
    bgColor: 'bg-pink-50 dark:bg-pink-900/20',
    timeKey: 'labs.time5Min',
    time: '5 min',
    difficulty: 'Easy',
  },
  {
    slug: 'ai-said-what',
    titleKey: 'labs.aiSaidWhatTitle',
    title: 'AI Said What?',
    subtitleKey: 'labs.aiSaidWhatSubtitle',
    subtitle: 'Hallucination Spotter',
    descriptionKey: 'labs.aiMakesStuffUpCan',
    description: 'AI makes stuff up. Can you tell fact from fiction?',
    icon: MessageSquareWarning,
    color: 'from-lsc-rose to-orange-500',
    bgColor: 'bg-lsc-cream dark:bg-lsc-dark/20',
    timeKey: 'labs.time5Min',
    time: '5 min',
    difficulty: 'Medium',
  },
  {
    slug: 'fix-this-prompt',
    titleKey: 'labs.fixThisPromptTitle',
    title: 'Fix This Prompt',
    subtitleKey: 'labs.fixThisPromptSubtitle',
    subtitle: 'Prompt Makeover',
    descriptionKey: 'labs.badPromptsConfusedAiLearn',
    description: 'Bad prompts = confused AI. Learn to ask better questions.',
    icon: Wand2,
    color: 'from-category-500 to-violet-500',
    bgColor: 'bg-category-50 dark:bg-category-900/20',
    timeKey: 'labs.time5Min',
    time: '5 min',
    difficulty: 'Easy',
  },
  {
    slug: 'who-wrote-this',
    titleKey: 'labs.whoWroteThisTitle',
    title: 'Who Wrote This?',
    subtitleKey: 'labs.whoWroteThisSubtitle',
    subtitle: 'Human vs AI',
    descriptionKey: 'labs.threeWritersOneIsAi',
    description: 'Three writers, one is AI. Can you tell which?',
    icon: PenTool,
    color: 'from-teal-500 to-cyan-500',
    bgColor: 'bg-teal-50 dark:bg-teal-900/20',
    timeKey: 'labs.time5Min',
    time: '5 min',
    difficulty: 'Hard',
  },
];

export default function LabsPage() {
  const { t } = useTranslation()
  const { isAuthenticated } = useAuth();

  return (
    <div className="min-h-screen bg-lsc-cream dark:bg-lsc-dark py-8 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-cream dark:bg-lsc-dark/30 text-lsc-rose dark:text-lsc-rose-light rounded-full text-sm font-medium mb-4">
            <Zap aria-hidden="true" className="w-4 h-4" />
            {t('labs.interactiveLearning', 'Interactive Learning')}
          </div>
          <h1 className="text-4xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4">
            {t('labs.aiLearningLabsHeading', 'AI Learning Labs')}
          </h1>
          <p className="text-lg text-lsc-dark/70 dark:text-lsc-cream/70 max-w-2xl mx-auto">
            {t('labs.aiLearningLabsBlurb', 'Quick, fun games that teach you how AI really works. No lectures, no quizzes-just play and learn.')}
          </p>
        </div>

        {/* Registration prompt for unauthenticated users */}
        {!isAuthenticated && (
          <div className="bg-lsc-rose/10 dark:bg-lsc-rose/20 border border-lsc-rose/30 rounded-xl p-4 mb-8 flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <GraduationCap aria-hidden="true" className="w-8 h-8 text-lsc-rose flex-shrink-0" />
              <p className="text-lsc-dark dark:text-lsc-cream">
                <span className="font-medium">{t('labs.earnBadgesAsYouPlay')}</span>{' '}
                <span className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('labs.createAFreeAccountTo')}</span>
              </p>
            </div>
            <Link
              to="/account"
              className="inline-flex items-center gap-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white px-5 py-2 rounded-xl font-medium whitespace-nowrap"
            >
              {t('labs.signUpFree', 'Sign Up Free')}
            </Link>
          </div>
        )}

        {/* Labs Grid */}
        <div className="grid md:grid-cols-2 gap-6">
          {LABS.map((lab) => {
            const Icon = lab.icon;
            return (
              <Link
                key={lab.slug}
                to={`/learn/labs/${lab.slug}`}
                className="group relative bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 overflow-hidden hover:shadow-lg transition-all hover:-translate-y-1"
              >
                {/* Gradient Header */}
                <div className={`h-24 bg-gradient-to-r ${lab.color} flex items-center justify-center`}>
                  <Icon aria-hidden="true" className="w-12 h-12 text-white/90" />
                </div>

                {/* Content */}
                <div className="p-6">
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <h2 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream group-hover:text-lsc-rose dark:group-hover:text-lsc-rose transition-colors">
                        {t(lab.titleKey, lab.title)}
                      </h2>
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                        {t(lab.subtitleKey, lab.subtitle)}
                      </p>
                    </div>
                    <ArrowRight aria-hidden="true" className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70 group-hover:text-lsc-rose group-hover:translate-x-1 transition-all" />
                  </div>

                  <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
                    {t(lab.descriptionKey, lab.description)}
                  </p>

                  <div className="flex items-center gap-4 text-sm">
                    <span className="flex items-center gap-1 text-lsc-dark/70 dark:text-lsc-cream/70">
                      <Clock aria-hidden="true" className="w-4 h-4" />
                      {t(lab.timeKey, lab.time)}
                    </span>
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${lab.bgColor} ${
                      lab.difficulty === 'Easy' ? 'text-status-success-700 dark:text-status-success-300' :
                      lab.difficulty === 'Medium' ? 'text-lsc-rose dark:text-lsc-rose-light' :
                      'text-status-danger-700 dark:text-status-danger-300'
                    }`}>
                      {lab.difficulty === 'Easy' ? t('labs.difficultyEasy', 'Easy') : lab.difficulty === 'Medium' ? t('labs.difficultyMedium', 'Medium') : t('labs.difficultyHard', 'Hard')}
                    </span>
                  </div>
                </div>
              </Link>
            );
          })}
        </div>

        {/* Bottom Message */}
        <div className="mt-12 text-center">
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            {t('labs.bottomBlurb', 'Each lab takes about 5 minutes. Play one, play all-no pressure.')}
          </p>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">
            {t('labs.earnLabRatPrefix', 'Earn the')} <span className="font-medium">{t('labs.labRatBadgeName', 'Lab Rat')}</span> {t('labs.earnLabRatSuffix', 'badge when you complete your first lab!')}
          </p>
        </div>
      </div>
    </div>
  );
}
