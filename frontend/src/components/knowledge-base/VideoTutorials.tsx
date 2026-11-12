/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query';
import { Play, FileText } from 'lucide-react'
import api from '../../api/api';
import { useTranslation } from '@/i18n'

interface Video {
  id: number;
  title: string;
  description: string;
  category: string;
  video_url: string;
  thumbnail_url: string;
  duration_seconds: number;
  transcript?: string | null;
  view_count: number;
  created_at: string;
}

export default function VideoTutorials() {
  const { t } = useTranslation()
  const { data: videos, isLoading } = useQuery({
    queryKey: ['video-tutorials'],
    queryFn: async () => {
      return await api.get<Video[]>('/staff-knowledge/video-tutorials');
    },
  });

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  if (isLoading) {
    return (
      <div className="text-center py-12" role="status">
        <div className="inline-block motion-safe:animate-spin rounded-full h-8 w-8 border-b-2 border-lsc-rose"></div>
        <span className="sr-only">{t('components.knowledgeBase.videoTutorials.loading', 'Loading video tutorials...')}</span>
      </div>
    );
  }

  if (!videos || videos.length === 0) {
    return (
      <div className="text-center py-12 bg-earth-50 dark:bg-earth-900 rounded-lg border border-lsc-border dark:border-earth-700">
        <p className="text-earth-600 dark:text-earth-400">{t('components.knowledgeBase.videoTutorials.noVideoTutorialsAvailableYet')}</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {videos.map(video => (
        <VideoCard key={video.id} video={video} t={t} formatDuration={formatDuration} />
      ))}
    </div>
  );
}

interface VideoCardProps {
  video: {
    id: number
    title: string
    description: string
    category: string
    video_url: string
    thumbnail_url: string
    duration_seconds: number
    transcript?: string | null
    view_count: number
    created_at: string
  }
  t: (key: string, fallback?: string) => string
  formatDuration: (seconds: number) => string
}

function VideoCard({ video, t, formatDuration }: VideoCardProps): React.ReactElement {
  const [thumbError, setThumbError] = useState(false)
  const hasTranscript = !!video.transcript?.trim()

  const ytIdMatch = video.video_url?.match(
    /(?:youtube\.com\/(?:watch\?v=|embed\/|shorts\/)|youtu\.be\/)([A-Za-z0-9_-]{11})/
  )
  const ytId = ytIdMatch?.[1]
  const src = !thumbError && (
    video.thumbnail_url?.startsWith('http')
      ? video.thumbnail_url
      : ytId
      ? `https://img.youtube.com/vi/${ytId}/hqdefault.jpg`
      : null
  )

  return (
    <div
      className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg overflow-hidden hover:shadow-lg transition"
    >
      <a
        href={video.video_url}
        target="_blank"
        rel="noopener noreferrer"
        aria-label={`${video.title} (${t('components.knowledgeBase.videoTutorials.opensInNewTab', 'opens in new tab')})`}
        className="block focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose"
      >
        <div className="relative bg-earth-800 aspect-video flex items-center justify-center group">
          {src && (
            <img
              src={src}
              alt={video.title}
              className="absolute inset-0 w-full h-full object-cover group-hover:opacity-75 transition"
              onError={() => setThumbError(true)}
            />
          )}
          <div className="absolute inset-0 flex items-center justify-center group-hover:bg-black group-hover:bg-opacity-30 transition">
            <Play className="w-12 h-12 text-white opacity-80 group-hover:opacity-100 transition" aria-hidden="true" />
          </div>
          {video.duration_seconds && (
            <div className="absolute bottom-2 right-2 bg-black bg-opacity-75 text-white text-xs px-2 py-1 rounded">
              {formatDuration(video.duration_seconds)}
            </div>
          )}
        </div>
      </a>

      <div className="p-4">
        <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-1 line-clamp-2" title={video.title}>
          {video.title}
        </h3>
        {video.description && (
          <p className="text-earth-600 dark:text-earth-400 text-sm mb-3 line-clamp-2" title={video.description}>
            {video.description}
          </p>
        )}
        {hasTranscript && (
          <details className="mb-3">
            <summary className="inline-flex items-center gap-1.5 text-sm text-earth-600 dark:text-earth-400 cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose rounded">
              <FileText className="w-4 h-4" aria-hidden="true" />
              {t('components.knowledgeBase.videoTutorials.transcriptAvailable', 'Transcript available')}
            </summary>
            <p className="mt-2 text-sm text-lsc-dark dark:text-lsc-cream whitespace-pre-line">
              {video.transcript}
            </p>
          </details>
        )}
        <div className="flex items-center justify-between text-sm text-earth-600 dark:text-earth-400">
          <span className="bg-earth-100 dark:bg-earth-700 px-2 py-1 rounded">
            {video.category}
          </span>
          <span className="text-xs">{`${video.view_count} ${t('components.knowledgeBase.videoTutorials.views', 'views')}`}</span>
        </div>
      </div>
    </div>
  )
}
