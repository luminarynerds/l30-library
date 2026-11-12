/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useEffect } from 'react';
import { Zap, Filter, X } from 'lucide-react';
import api from '../../api/api';
import ExternalResourceCard from './ExternalResourceCard';
import { API_BASE } from '@/api/types'

interface ExternalResource {
  id: number;
  title: string;
  description: string;
  source_url: string;
  thumbnail_url?: string;
  provider: string;
  resource_type: string;
  difficulty: 'beginner' | 'intermediate' | 'advanced';
  topics: string[];
  estimated_minutes?: number;
  source_organization?: string;
  is_featured?: boolean;
}

interface ExternalResourcesSectionProps {
  showFilters?: boolean;
  featuredOnly?: boolean;
  maxResources?: number;
  showTitle?: boolean;
}

const DIFFICULTY_OPTIONS = ['all', 'beginner', 'intermediate', 'advanced'] as const;
const TOPIC_OPTIONS = [
  'AI',
  'Ethics',
  'Data Management',
  'Governance',
  'Leadership',
  'Data Visualization',
  'Privacy',
  'Application',
  'Partnerships',
  'Talent',
  'Quality',
];

export default function ExternalResourcesSection({
  showFilters = true,
  featuredOnly = false,
  maxResources = 20,
  showTitle = true,
}: ExternalResourcesSectionProps) {
  const [resources, setResources] = useState<ExternalResource[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showFilterPanel, setShowFilterPanel] = useState(false);

  // Filters
  const [difficultyFilter, setDifficultyFilter] = useState<string>('all');
  const [topicFilter, setTopicFilter] = useState<string | null>(null);

  // Load resources
  useEffect(() => {
    const loadResources = async () => {
      try {
        setLoading(true);
        setError(null);

        const params = new URLSearchParams();
        if (difficultyFilter && difficultyFilter !== 'all') {
          params.append('difficulty', difficultyFilter);
        }
        if (topicFilter) {
          params.append('topic', topicFilter);
        }
        if (featuredOnly) {
          params.append('featured_only', 'true');
        }
        params.append('limit', maxResources.toString());

        const response = await api.get(`${API_BASE}/learning/external-resources?${params}`);
        setResources(Array.isArray(response) ? response : []);
      } catch (_err) {
        Sentry.captureException(_err instanceof Error ? _err : new Error(String(_err)));
        setError('Unable to load external resources. Please try again later.');
      } finally {
        setLoading(false);
      }
    };

    loadResources();
  }, [difficultyFilter, topicFilter, featuredOnly, maxResources]);

  const handleResourceClick = async (resourceId: number) => {
    try {
      await api.post(`${API_BASE}/learning/external-resources/${resourceId}/click`);
    } catch (_err) {
      Sentry.captureException(_err instanceof Error ? _err : new Error(String(_err)));
    }
  };

  const handleClearFilters = () => {
    setDifficultyFilter('all');
    setTopicFilter(null);
    setShowFilterPanel(false);
  };

  if (loading) {
    return (
      <div className="w-full">
        {showTitle && (
          <div className="mb-6">
            <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
              Curated External Resources
            </h2>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
              Learn from industry-leading providers like data.org
            </p>
          </div>
        )}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(6)].map((_, i) => (
            <div
              key={i}
              className="bg-earth-200 dark:bg-earth-700 rounded-lg h-96 motion-safe:animate-pulse motion-reduce:animate-none"
            />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-lg p-4">
        <p className="text-status-danger-700 dark:text-status-danger-300">{error}</p>
      </div>
    );
  }

  if (resources.length === 0 && difficultyFilter === "all" && !topicFilter) {
    return null;
  }

  if (resources.length === 0) {
    return (
      <div className="bg-earth-50 dark:bg-earth-800/20 border border-lsc-border dark:border-earth-700 rounded-lg p-6 text-center">
        <Zap className="w-12 h-12 text-lsc-rose dark:text-lsc-rose-light mx-auto mb-3" />
        <p className="text-lsc-rose dark:text-lsc-rose-light">
          No resources found matching your filters.
        </p>
      </div>
    );
  }

  return (
    <div className="w-full">
      {/* Header */}
      {showTitle && (
        <div className="mb-6">
          <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
            Curated External Resources
          </h2>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            Learn from industry-leading providers like data.org
          </p>
        </div>
      )}

      {/* Filter Controls */}
      {showFilters && (
        <div className="mb-6">
          <button
            onClick={() => setShowFilterPanel(!showFilterPanel)}
            className="flex items-center gap-2 px-4 py-2 bg-earth-100 hover:bg-earth-200 dark:bg-earth-800 dark:hover:bg-earth-700 rounded-lg text-lsc-dark/70 dark:text-lsc-cream/70 font-medium transition-colors"
          >
            <Filter className="w-4 h-4" />
            Filters
          </button>

          {/* Filter Panel */}
          {showFilterPanel && (
            <div className="mt-4 p-4 bg-earth-50 dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg">
              <div className="flex justify-between items-center mb-4">
                <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Filter Resources</h3>
                <button
                  onClick={() => setShowFilterPanel(false)}
                  className="text-earth-600 hover:text-lsc-dark/70 dark:text-lsc-cream/70 dark:hover:text-earth-200"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Difficulty Filter */}
              <div className="mb-6">
                <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                  Difficulty Level
                </label>
                <div className="space-y-2">
                  {DIFFICULTY_OPTIONS.map((opt) => (
                    <label key={opt} className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        name="difficulty"
                        value={opt}
                        checked={difficultyFilter === opt}
                        onChange={(e) => setDifficultyFilter(e.target.value)}
                        className="w-4 h-4"
                      />
                      <span className="text-lsc-dark/70 dark:text-lsc-cream/70">
                        {opt === 'all' ? 'All Levels' : opt.charAt(0).toUpperCase() + opt.slice(1)}
                      </span>
                    </label>
                  ))}
                </div>
              </div>

              {/* Topic Filter */}
              <div className="mb-6">
                <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                  Topics
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={() => setTopicFilter(null)}
                    className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                      topicFilter === null
                        ? 'bg-lsc-rose text-white dark:bg-earth-500'
                        : 'bg-earth-200 text-earth-700 dark:bg-earth-700 dark:text-earth-300 hover:bg-earth-300 dark:hover:bg-earth-600'
                    }`}
                  >
                    All Topics
                  </button>
                  {TOPIC_OPTIONS.map((topic) => (
                    <button
                      key={topic}
                      onClick={() => setTopicFilter(topicFilter === topic ? null : topic)}
                      className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                        topicFilter === topic
                          ? 'bg-lsc-rose text-white dark:bg-earth-500'
                          : 'bg-earth-200 text-earth-700 dark:bg-earth-700 dark:text-earth-300 hover:bg-earth-300 dark:hover:bg-earth-600'
                      }`}
                    >
                      {topic}
                    </button>
                  ))}
                </div>
              </div>

              {/* Clear Filters Button */}
              <button
                onClick={handleClearFilters}
                className="w-full px-4 py-2 bg-earth-200 hover:bg-earth-300 dark:bg-earth-700 dark:hover:bg-earth-600 text-lsc-dark/70 dark:text-lsc-cream/70 rounded-lg font-medium transition-colors"
              >
                Clear Filters
              </button>
            </div>
          )}
        </div>
      )}

      {/* Resource Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {resources.map((resource) => (
          <ExternalResourceCard
            key={resource.id}
            {...resource}
            onResourceClick={handleResourceClick}
          />
        ))}
      </div>

      {/* Results Count */}
      <div className="mt-6 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
        Showing {resources.length} resource{resources.length !== 1 ? 's' : ''}
      </div>
    </div>
  );
}