/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useMemo, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchApi } from '@/api/fetchApi'
import { capitalizeFirst } from '@/utils/helpers';
import {
  BookOpen,
  Search,
  ExternalLink,
  Clock,
  AlertCircle,
  Loader2,
} from 'lucide-react'
import { useTranslation} from '@/i18n'
import YouthSubNav from '@/pages/youth/YouthSubNav'
import PageContainer from '@/components/layout/PageContainer'

interface ExternalResource {
  id: number
  title: string
  description: string
  source_url: string
  thumbnail_url?: string
  provider: string
  resource_type: string
  difficulty: 'beginner' | 'intermediate' | 'advanced'
  topics: string[]
  estimated_minutes?: number
  source_organization?: string
  is_featured: boolean
}

interface Subject {
  id: string
  name: string
  description: string
  icon: React.ReactNode
  topicKeyword: string
}

function getDifficultyColor(difficulty: string): string {
  switch (difficulty) {
    case 'beginner':
      return 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-800 dark:text-status-success-300'
    case 'intermediate':
      return 'bg-earth-100 dark:bg-earth-800/30 text-earth-800 dark:text-lsc-rose-light'
    case 'advanced':
      return 'bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-800 dark:text-status-danger-300'
    default:
      return 'bg-earth-100 dark:bg-earth-900/30 text-earth-800 dark:text-earth-300'
  }
}

function getResourceTypeIcon(type: string): React.ReactNode {
  switch (type) {
    case 'article':
      return <BookOpen aria-hidden="true" className="w-4 h-4" />
    case 'video':
      return <ExternalLink aria-hidden="true" className="w-4 h-4" />
    case 'course':
      return <BookOpen aria-hidden="true" className="w-4 h-4" />
    case 'toolkit':
      return <BookOpen aria-hidden="true" className="w-4 h-4" />
    default:
      return <BookOpen aria-hidden="true" className="w-4 h-4" />
  }
}

export default function YouthHomeworkHelpPage(): React.ReactElement {
  const { t } = useTranslation()
  const subjects: Subject[] = useMemo(() => [
    {
      id: 'math',
      name: 'Math',
      description: t('youthHomeworkHelp.algebraGeometryCalculusAndMore'),
      icon: <BookOpen aria-hidden="true" className="w-6 h-6" />,
      topicKeyword: 'Math',
    },
    {
      id: 'english',
      name: 'English',
      description: t('youthHomeworkHelp.literatureWritingGrammarAndComprehension'),
      icon: <BookOpen aria-hidden="true" className="w-6 h-6" />,
      topicKeyword: 'Writing',
    },
    {
      id: 'science',
      name: 'Science',
      description: t('youthHomeworkHelp.biologyChemistryPhysicsAndEarth'),
      icon: <BookOpen aria-hidden="true" className="w-6 h-6" />,
      topicKeyword: 'Science',
    },
    {
      id: 'history',
      name: 'History',
      description: t('youthHomeworkHelp.worldHistoryCivicsAndSocial'),
      icon: <Clock aria-hidden="true" className="w-6 h-6" />,
      topicKeyword: 'History',
    },
    {
      id: 'languages',
      name: 'Languages',
      description: t('youthHomeworkHelp.spanishFrenchChineseAndMore'),
      icon: <BookOpen aria-hidden="true" className="w-6 h-6" />,
      topicKeyword: 'Languages',
    },
    {
      id: 'arts',
      name: 'Arts',
      description: t('youthHomeworkHelp.visualArtsMusicAndCreative'),
      icon: <BookOpen aria-hidden="true" className="w-6 h-6" />,
      topicKeyword: 'Arts',
    },
  ], [t])
  const [selectedSubject, setSelectedSubject] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [sortBy, setSortBy] = useState<'beginner' | 'intermediate' | 'advanced' | ''>('')
  const [debouncedSearch, setDebouncedSearch] = useState('')

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchQuery), 300)
    return () => clearTimeout(timer)
  }, [searchQuery])

  // Build topic filter from selected subject
  const topicFilter = selectedSubject
    ? subjects.find(s => s.id === selectedSubject)?.topicKeyword
    : undefined

  // Fetch external resources from API
  const { data: resources = [], isLoading, error } = useQuery({
    queryKey: ['external-resources', sortBy, topicFilter],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (sortBy) {
        params.append('difficulty', sortBy)
      }
      if (topicFilter) {
        params.append('topic', topicFilter)
      }
      params.append('limit', '50')

      return await fetchApi(`/learning/external-resources?${params.toString()}`)
    },
  })

  // Client-side search filter
  const filteredResources = resources.filter((resource: ExternalResource) => {
    if (debouncedSearch && !resource.title.toLowerCase().includes(debouncedSearch.toLowerCase())) {
      return false
    }
    return true
  })

  // Calculate live resource counts for each subject
  const getSubjectResourceCount = (subjectId: string): number => {
    const keyword = subjects.find(s => s.id === subjectId)?.topicKeyword
    if (!keyword) return 0
    return resources.filter((r: ExternalResource) => r.topics.includes(keyword)).length
  }

  const handleResourceClick = (resource: ExternalResource) => {
    if (resource.source_url?.startsWith('http://') || resource.source_url?.startsWith('https://')) {
      window.open(resource.source_url, '_blank', 'noopener,noreferrer')
    }
  }

  return (
    <div className="min-h-screen bg-lsc-cream dark:bg-lsc-dark">
      <YouthSubNav />
      {/* Header */}
      <div className="bg-lsc-white dark:bg-earth-800 border-b border-lsc-border dark:border-earth-700">
        <PageContainer className="py-8">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-lsc-cream dark:bg-earth-800/30 rounded-xl">
              <BookOpen aria-hidden="true" className="w-8 h-8 text-lsc-rose dark:text-lsc-rose-light" />
            </div>
            <div>
              <h1 className="text-3xl font-serif font-bold text-lsc-dark dark:text-earth-50">
                Homework Help Hub
              </h1>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                Access curated learning resources for all subjects
              </p>
            </div>
          </div>
        </PageContainer>
      </div>

      <PageContainer className="py-8">
        {/* Info Banner */}
        <div className="bg-earth-50 dark:bg-earth-800/20 border border-lsc-border dark:border-earth-700 rounded-xl p-6 mb-8">
          <div className="flex gap-3">
            <AlertCircle aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-serif font-semibold text-earth-900 dark:text-earth-200 mb-1">Need Live Help?</h3>
              <p className="text-earth-800 dark:text-lsc-rose-light text-sm">
                Join our weekly homework help sessions with certified tutors every Tuesday and Thursday from 4-6 PM
              </p>
            </div>
          </div>
        </div>

        {/* Search and Filter */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700 mb-8">
          <div className="flex gap-3 items-center">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
              <input
                type="text"
                placeholder={t('placeholder.youthHomeworkHelp.searchResources')}
                aria-label={t('aria.youthHomeworkHelp.searchHomeworkResources')}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-earth-50 placeholder-earth-500 dark:placeholder-earth-500 focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
              />
            </div>
            <div className="w-48">
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
                aria-label="Difficulty level"
                className="w-full py-2.5 px-3 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-earth-50 focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
              >
                <option value="">All Levels</option>
                <option value="beginner">Beginner</option>
                <option value="intermediate">Intermediate</option>
                <option value="advanced">Advanced</option>
              </select>
            </div>
          </div>
        </div>

        {/* Subjects Grid with Live Resource Counts */}
        <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-earth-50 mb-6">Browse by Subject</h2>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4 mb-12">
          {subjects.map((subject) => (
            <button
              key={subject.id}
              onClick={() => setSelectedSubject(selectedSubject === subject.id ? null : subject.id)}
              className={`text-left p-6 rounded-xl border-2 transition-colors ${
                selectedSubject === subject.id
                  ? 'bg-lsc-rose text-white border-earth-600'
                  : 'bg-lsc-white dark:bg-earth-800 border-lsc-border dark:border-earth-700 hover:border-earth-400 text-lsc-dark dark:text-earth-50'
              }`}
            >
              <div className="flex items-start justify-between mb-3">
                <div className={selectedSubject === subject.id ? 'text-white' : 'text-lsc-rose dark:text-lsc-rose-light'}>
                  {subject.icon}
                </div>
                {isLoading ? (
                  <Loader2 className="w-4 h-4 motion-safe:animate-spin text-lsc-dark/70 dark:text-lsc-cream/70" aria-hidden="true" />
                ) : (
                  <span className={`text-sm font-semibold ${selectedSubject === subject.id ? 'text-white' : 'text-lsc-dark/70 dark:text-lsc-cream/70'}`}>
                    {getSubjectResourceCount(subject.id)}
                  </span>
                )}
              </div>
              <h3 className="font-serif font-semibold text-lg mb-1">{subject.name}</h3>
              <p className={`text-sm ${selectedSubject === subject.id ? 'text-white/80' : 'text-lsc-dark/70 dark:text-lsc-cream/70'}`}>
                {subject.description}
              </p>
            </button>
          ))}
        </div>

        {/* Resources */}
        {error && (
          <div className="bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-xl p-6 mb-8">
            <div className="flex gap-3">
              <AlertCircle aria-hidden="true" className="w-5 h-5 text-status-danger-600 dark:text-status-danger-400 flex-shrink-0 mt-0.5" />
              <div>
                <h3 className="font-serif font-semibold text-status-danger-900 dark:text-status-danger-100 mb-1">Error Loading Resources</h3>
                <p className="text-status-danger-800 dark:text-status-danger-300 text-sm">
                  We encountered an error loading the resources. Please try again.
                </p>
              </div>
            </div>
          </div>
        )}

        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-earth-50">
            {selectedSubject ? `${subjects.find((s) => s.id === selectedSubject)?.name} Resources` : 'All Resources'}
          </h2>
          {isLoading ? (
            <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70" role="status" aria-live="polite">
              <Loader2 className="w-4 h-4 motion-safe:animate-spin" aria-hidden="true" />
              <span className="text-sm">Loading...</span>
            </div>
          ) : (
            <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70" role="status" aria-live="polite" aria-atomic="true">{filteredResources.length} results</span>
          )}
        </div>

        {isLoading ? (
          <div className="space-y-4" aria-busy="true" aria-label="Loading resources">
            {[...Array(5)].map((_, i) => (
              <div
                key={i}
                className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700 motion-safe:animate-pulse"
              >
                <div className="h-6 bg-lsc-border dark:bg-earth-700 rounded w-1/2 mb-4" />
                <div className="h-4 bg-lsc-border dark:bg-earth-700 rounded w-3/4 mb-4" />
                <div className="h-4 bg-lsc-border dark:bg-earth-700 rounded w-full" />
              </div>
            ))}
          </div>
        ) : filteredResources.length > 0 ? (
          <div className="space-y-4">
            {filteredResources.map((resource: ExternalResource) => (
              <div
                key={resource.id}
                className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700 hover:shadow-md transition-shadow"
              >
                <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-start gap-3 mb-3">
                      <div className="p-2 bg-lsc-cream dark:bg-earth-800/50 rounded-lg text-lsc-rose dark:text-lsc-rose-light">
                        {getResourceTypeIcon(resource.resource_type)}
                      </div>
                      <div className="flex-1">
                        <h3 className="font-serif font-semibold text-lg text-lsc-dark dark:text-earth-50">{resource.title}</h3>
                        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                          {resource.source_organization || resource.provider} • {capitalizeFirst(resource.resource_type)}
                        </p>
                      </div>
                    </div>
                    <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">{resource.description}</p>
                    <div className="flex flex-wrap gap-4 text-sm">
                      <span className={`px-3 py-1 rounded-full font-medium ${getDifficultyColor(resource.difficulty)}`}>
                        {capitalizeFirst(resource.difficulty)}
                      </span>
                      {resource.estimated_minutes && (
                        <div className="flex items-center gap-1 text-lsc-dark/70 dark:text-lsc-cream/70">
                          <Clock aria-hidden="true" className="w-4 h-4" />
                          <span>{resource.estimated_minutes} min</span>
                        </div>
                      )}
                      {resource.is_featured && (
                        <span className="px-3 py-1 rounded-full font-medium bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-800 dark:text-status-warning-300">
                          Featured
                        </span>
                      )}
                    </div>
                    {resource.topics && resource.topics.length > 0 && (
                      <div className="flex flex-wrap gap-2 mt-4">
                        {resource.topics.map((topic) => (
                          <span
                            key={topic}
                            className="px-2 py-1 rounded-full text-xs font-medium bg-lsc-cream dark:bg-earth-800/50 text-lsc-dark dark:text-lsc-cream/80"
                          >
                            {topic}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  <button
                    onClick={() => handleResourceClick(resource)}
                    className="flex items-center justify-center gap-2 px-4 py-2 rounded-xl font-medium transition-colors whitespace-nowrap bg-lsc-rose hover:bg-lsc-rose/90 text-white"
                  >
                    <ExternalLink aria-hidden="true" className="w-4 h-4" />
                    <span className="text-sm">Open</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-16">
            <Search aria-hidden="true" className="w-16 h-16 mx-auto text-lsc-border dark:text-lsc-cream/70 mb-4" />
            <h3 className="text-lg font-medium text-lsc-dark dark:text-earth-50 mb-2">No resources found</h3>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">{t('youthHomeworkHelp.tryAdjustingYourSearchOr')}</p>
            {(searchQuery || selectedSubject || sortBy) && (
              <button
                onClick={() => { setSearchQuery(''); setSelectedSubject(null); setSortBy(''); }}
                className="px-4 py-2 rounded-xl text-sm font-medium bg-lsc-rose hover:bg-lsc-rose/90 text-white transition-colors"
              >
                Clear all filters
              </button>
            )}
          </div>
        )}
      </PageContainer>
    </div>
  )
}