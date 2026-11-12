/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useMemo } from 'react'
import {
  Code2,
  BookOpen,
  Zap,
  Clock,
  Info,
  BarChart3,
} from 'lucide-react'
import { useTranslation } from '@/i18n'
import YouthSubNav from '@/pages/youth/YouthSubNav'
import PageContainer from '@/components/layout/PageContainer'

interface Track {
  id: string
  name: string
  description: string
  difficulty: 'beginner' | 'intermediate' | 'advanced'
  duration: string
  lessons: number
  icon: React.ReactNode
}

function getDifficultyColor(difficulty: Track['difficulty']): string {
  switch (difficulty) {
    case 'beginner':
      return 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-800 dark:text-status-success-300'
    case 'intermediate':
      return 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-800 dark:text-status-warning-300'
    case 'advanced':
      return 'bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-800 dark:text-status-danger-300'
  }
}

export default function YouthCodingTracksPage(): React.ReactElement {
  const { t } = useTranslation()
  const tracks: Track[] = useMemo(() => [
    {
      id: 'scratch-basics',
      name: 'Scratch Basics',
      description: t('youthCodingTracks.learnProgrammingFundamentalsWithVisual'),
      difficulty: 'beginner',
      duration: '4 weeks',
      lessons: 12,
      icon: <Zap aria-hidden="true" className="w-8 h-8" />,
    },
    {
      id: 'web-dev-intro',
      name: 'Web Development Intro',
      description: t('youthCodingTracks.masterHtmlCssAndJavascript'),
      difficulty: 'intermediate',
      duration: '6 weeks',
      lessons: 18,
      icon: <Code2 aria-hidden="true" className="w-8 h-8" />,
    },
    {
      id: 'python-fundamentals',
      name: 'Python Fundamentals',
      description: t('youthCodingTracks.startYourJourneyWithPython'),
      difficulty: 'beginner',
      duration: '5 weeks',
      lessons: 15,
      icon: <Code2 aria-hidden="true" className="w-8 h-8" />,
    },
    {
      id: 'game-dev',
      name: 'Game Development',
      description: t('youthCodingTracks.createDGamesUsingPython'),
      difficulty: 'intermediate',
      duration: '7 weeks',
      lessons: 20,
      icon: <Zap aria-hidden="true" className="w-8 h-8" />,
    },
    {
      id: 'web-advanced',
      name: 'Advanced Web Development',
      description: t('youthCodingTracks.buildModernWebAppsWith'),
      difficulty: 'advanced',
      duration: '8 weeks',
      lessons: 24,
      icon: <Code2 aria-hidden="true" className="w-8 h-8" />,
    },
    {
      id: 'data-science',
      name: 'Data Science with Python',
      description: t('youthCodingTracks.exploreDataAnalysisAndVisualization'),
      difficulty: 'advanced',
      duration: '8 weeks',
      lessons: 22,
      icon: <BarChart3 aria-hidden="true" className="w-8 h-8" />,
    },
  ], [t])
  const [difficultyFilter, setDifficultyFilter] = useState<'all' | 'beginner' | 'intermediate' | 'advanced'>('all')

  const filteredTracks = tracks.filter(
    (track) => difficultyFilter === 'all' || track.difficulty === difficultyFilter
  )

  return (
    <div className="min-h-screen bg-lsc-cream dark:bg-lsc-dark">
      <YouthSubNav />
      {/* Header */}
      <div className="bg-lsc-white dark:bg-earth-800 border-b border-lsc-border dark:border-earth-700">
        <PageContainer className="py-8">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-lsc-cream dark:bg-earth-800/30 rounded-xl">
              <Code2 aria-hidden="true" className="w-8 h-8 text-lsc-rose dark:text-lsc-rose-light" />
            </div>
            <div>
              <h1 className="text-3xl font-serif font-bold text-lsc-dark dark:text-earth-50">
                Coding Tracks
              </h1>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                Learn to code with guided learning paths from beginner to advanced
              </p>
            </div>
          </div>
        </PageContainer>
      </div>

      <PageContainer className="py-8">
        {/* Coming Soon Banner */}
        <div className="bg-earth-50 dark:bg-earth-800/20 border border-lsc-border dark:border-earth-700 rounded-xl p-6 mb-8">
          <div className="flex gap-3">
            <Info aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-serif font-semibold text-earth-900 dark:text-earth-200 mb-1">Coming Soon</h3>
              <p className="text-earth-800 dark:text-lsc-rose-light text-sm">
                Coding tracks are being developed. Browse our learning paths in the meantime.
              </p>
            </div>
          </div>
        </div>

        {/* Difficulty Filter */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700 mb-8">
          <h2 className="font-serif font-semibold text-lsc-dark dark:text-earth-50 mb-4">Filter by Difficulty</h2>
          <div className="flex flex-wrap gap-3">
            {(['all', 'beginner', 'intermediate', 'advanced'] as const).map((level) => (
              <button
                key={level}
                onClick={() => setDifficultyFilter(level)}
                className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
                  difficultyFilter === level
                    ? 'bg-lsc-rose text-white'
                    : 'bg-lsc-cream dark:bg-earth-800/50 text-lsc-dark dark:text-lsc-cream/80 border border-lsc-border dark:border-earth-700 hover:border-earth-400'
                }`}
              >
                {level.charAt(0).toUpperCase() + level.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Tracks Grid */}
        {filteredTracks.length === 0 ? (
          <div className="text-center py-16">
            <Code2 aria-hidden="true" className="w-16 h-16 mx-auto text-lsc-border dark:text-lsc-cream/70 mb-4" />
            <h3 className="text-lg font-medium text-lsc-dark dark:text-earth-50 mb-2">
              No tracks match this difficulty level
            </h3>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
              Try selecting a different difficulty or browse all tracks
            </p>
            <button
              onClick={() => setDifficultyFilter('all')}
              className="px-4 py-2 rounded-xl text-sm font-medium bg-lsc-rose hover:bg-lsc-rose/90 text-white transition-colors"
            >
              Show all tracks
            </button>
          </div>
        ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredTracks.map((track) => (
            <div
              key={track.id}
              className="rounded-xl border-2 transition-all bg-lsc-white dark:bg-earth-800 border-lsc-border dark:border-earth-700 hover:shadow-md"
            >
              <div className="p-6">
                <div className="flex items-start justify-between mb-4">
                  <div className="p-3 rounded-lg bg-lsc-cream dark:bg-earth-800/50 text-lsc-rose dark:text-lsc-rose-light">
                    {track.icon}
                  </div>
                  <span className={`px-3 py-1 rounded-full text-xs font-medium ${getDifficultyColor(track.difficulty)}`}>
                    {track.difficulty.charAt(0).toUpperCase() + track.difficulty.slice(1)}
                  </span>
                </div>

                <h3 className="font-semibold text-lg mb-2 text-lsc-dark dark:text-earth-50">
                  {track.name}
                </h3>
                <p className="text-sm mb-4 text-lsc-dark/70 dark:text-lsc-cream/70">
                  {track.description}
                </p>

                <div className="flex flex-wrap gap-4 text-sm mb-4 text-lsc-dark/70 dark:text-lsc-cream/70">
                  <div className="flex items-center gap-1">
                    <Clock aria-hidden="true" className="w-4 h-4" />
                    <span>{track.duration}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <BookOpen aria-hidden="true" className="w-4 h-4" />
                    <span>{track.lessons} lessons</span>
                  </div>
                </div>

                <a
                  href="/learning-paths"
                  className="w-full py-2 rounded-lg font-medium transition-colors flex items-center justify-center gap-2 bg-lsc-rose text-white hover:bg-lsc-rose/90"
                >
                  <span>Browse Learning Paths</span>
                </a>
              </div>
            </div>
          ))}
        </div>
        )}
      </PageContainer>
    </div>
  )
}
