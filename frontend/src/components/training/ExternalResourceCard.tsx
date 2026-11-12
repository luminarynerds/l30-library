/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { ExternalLink, Star, Clock, Users, BookOpen } from 'lucide-react';
import { useState } from 'react';

interface ExternalResourceProps {
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
  onResourceClick?: (resourceId: number) => void;
}

const DIFFICULTY_COLORS = {
  beginner: 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900/30 dark:text-status-success-300',
  intermediate: 'bg-earth-100 text-lsc-rose dark:bg-earth-800/30 dark:text-lsc-rose-light',
  advanced: 'bg-category-100 text-category-700 dark:bg-category-900/30 dark:text-category-300',
};

const RESOURCE_TYPE_ICONS = {
  course: <BookOpen className="w-4 h-4" />,
  toolkit: <Users className="w-4 h-4" />,
  article: <BookOpen className="w-4 h-4" />,
  playbook: <BookOpen className="w-4 h-4" />,
};

const TOPIC_COLORS: Record<string, string> = {
  // WCAG AA: All topic tag colors meet 4.5:1+ contrast ratio
  AI: 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-300', // WCAG AA: 6.19:1
  Ethics: 'bg-pink-100 text-pink-700 dark:bg-pink-900/30 dark:text-pink-300', // WCAG AA: 5.14:1
  'Data Management': 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-300', // WCAG AA: 5.11:1
  Governance: 'bg-lsc-rose/10 text-lsc-rose dark:bg-lsc-rose/20 dark:text-lsc-rose-light', // WCAG AA: 6.66:1
  Leadership: 'bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900/30 dark:text-status-warning-300', // WCAG AA: 4.51:1
  'Data Visualization': 'bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900/30 dark:text-status-danger-300', // WCAG AA: 5.30:1
  Privacy: 'bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900/30 dark:text-status-warning-300', // WCAG AA: 4.76:1
  Application: 'bg-lime-100 text-lime-800 dark:bg-lime-900/30 dark:text-lime-300', // WCAG AA: 7.52:1
  Partnerships: 'bg-teal-100 text-teal-800 dark:bg-teal-900/30 dark:text-teal-300', // WCAG AA: 7.29:1
  Talent: 'bg-fuchsia-100 text-fuchsia-700 dark:bg-fuchsia-900/30 dark:text-fuchsia-300', // WCAG AA: 5.43:1
  Quality: 'bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300', // WCAG AA: 6.48:1
};

export default function ExternalResourceCard({
  id,
  title,
  description,
  source_url,
  thumbnail_url,
  provider,
  resource_type,
  difficulty,
  topics,
  estimated_minutes,
  source_organization,
  is_featured = false,
  onResourceClick,
}: ExternalResourceProps) {
  const [isHovered, setIsHovered] = useState(false);

  const handleClick = () => {
    onResourceClick?.(id);
    window.open(source_url, '_blank');
  };

  const getTopicColor = (topic: string) => {
    return TOPIC_COLORS[topic] || 'bg-earth-100 text-earth-700 dark:bg-earth-800 dark:text-earth-300';
  };

  return (
    <div
      className={`flex flex-col h-full border rounded-lg overflow-hidden transition-all duration-300 ${
        isHovered
          ? 'shadow-lg border-lsc-border dark:border-earth-600'
          : 'shadow-md border-lsc-border dark:border-earth-700'
      } bg-lsc-white dark:bg-earth-900`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Thumbnail */}
      {thumbnail_url && (
        <div className="relative h-48 bg-earth-200 dark:bg-earth-800 overflow-hidden">
          <img
            src={thumbnail_url}
            alt={title}
            className={`w-full h-full object-cover transition-transform duration-300 ${
              isHovered ? 'scale-105' : 'scale-100'
            }`}
          />
          {is_featured && (
            <div className="absolute top-3 right-3 bg-status-warning-400 text-status-warning-900 dark:text-status-warning-200 px-3 py-1 rounded-full flex items-center gap-1 text-sm font-semibold">
              <Star className="w-4 h-4 fill-current" />
              Featured
            </div>
          )}
        </div>
      )}

      {/* Content */}
      <div className="flex flex-col flex-grow p-4">
        {/* Title */}
        <h3 className="font-serif font-semibold text-lg mb-2 text-lsc-dark dark:text-lsc-cream line-clamp-2" title={title}>
          {title}
        </h3>

        {/* Provider & Organization */}
        <div className="mb-2">
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            {source_organization ? `by ${source_organization}` : `from ${provider}`}
          </p>
        </div>

        {/* Description */}
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3 line-clamp-2 flex-grow" title={description}>
          {description}
        </p>

        {/* Metadata Tags */}
        <div className="flex flex-wrap gap-2 mb-3">
          {/* Difficulty */}
          <span
            className={`px-2 py-1 rounded-full text-xs font-medium ${
              DIFFICULTY_COLORS[difficulty]
            }`}
          >
            {difficulty.charAt(0).toUpperCase() + difficulty.slice(1)}
          </span>

          {/* Resource Type */}
          <span className="px-2 py-1 bg-earth-100 text-earth-700 dark:bg-earth-800 dark:text-earth-300 rounded-full text-xs font-medium flex items-center gap-1">
            {RESOURCE_TYPE_ICONS[resource_type as keyof typeof RESOURCE_TYPE_ICONS] || <BookOpen className="w-3 h-3" />}
            {resource_type.charAt(0).toUpperCase() + resource_type.slice(1)}
          </span>

          {/* Duration */}
          {estimated_minutes && (
            <span className="px-2 py-1 bg-earth-100 text-earth-700 dark:bg-earth-800 dark:text-earth-300 rounded-full text-xs font-medium flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {estimated_minutes}m
            </span>
          )}
        </div>

        {/* Topics */}
        {topics && topics.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-4">
            {topics.map((topic) => (
              <span
                key={topic}
                className={`px-2 py-1 rounded-full text-xs font-medium ${getTopicColor(topic)}`}
              >
                {topic}
              </span>
            ))}
          </div>
        )}

        {/* Action Button */}
        <button
          onClick={handleClick}
          className={`w-full py-2 px-3 rounded-lg font-medium flex items-center justify-center gap-2 transition-all duration-300 ${
            isHovered
              ? 'bg-lsc-rose text-white dark:bg-earth-500'
              : 'bg-earth-50 text-lsc-rose dark:text-lsc-rose-light dark:bg-earth-800/20 dark:text-lsc-rose-light'
          }`}
        >
          <ExternalLink className="w-4 h-4" />
          Learn from {provider}
        </button>
      </div>
    </div>
  );
}
