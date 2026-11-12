/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/* eslint-disable react-refresh/only-export-components */
import {
  Smartphone,
  Trophy,
  PenTool,
  Calendar,
  GraduationCap,
  Wrench,
  CloudSun,
  Laugh,
  Heart,
  Flame,
  Sparkles,
  HandHeart,
} from 'lucide-react'

// ---------------------------------------------------------------------------
// Shelf configuration for landing page
// ---------------------------------------------------------------------------

const EXPLORE_ICONS = { Smartphone, Trophy, PenTool, Calendar, GraduationCap, Wrench } as const

export function ExploreIcon({ name }: { name: string }) {
  const Icon = EXPLORE_ICONS[name as keyof typeof EXPLORE_ICONS]
  if (!Icon) return null
  return <Icon className="w-5 h-5 text-lsc-rose flex-shrink-0 mt-0.5" aria-hidden="true" />
}

export const EXPLORE_CARDS = [
  { titleKey: 'catalog.landing.ebooksAndAudiobooks', descKey: 'catalog.landing.ebooksDesc', link: '/digital', icon: 'Smartphone' },
  { titleKey: 'catalog.landing.readingPrograms', descKey: 'catalog.landing.readingProgramsDesc', link: '/programs', icon: 'Trophy' },
  { titleKey: 'catalog.landing.localAuthors', descKey: 'catalog.landing.localAuthorsDesc', link: '/indie/author/browse', icon: 'PenTool' },
  { titleKey: 'catalog.landing.eventsAndPrograms', descKey: 'catalog.landing.eventsDesc', link: '/events', icon: 'Calendar' },
  { titleKey: 'catalog.landing.learningAndClasses', descKey: 'catalog.landing.learningDesc', link: '/learn', icon: 'GraduationCap' },
  { titleKey: 'catalog.landing.makerspace', descKey: 'catalog.landing.makerspaceDesc', link: '/makerspace', icon: 'Wrench' },
] as const

// ---------------------------------------------------------------------------
// Mood browse configuration
// ---------------------------------------------------------------------------

export interface MoodConfig {
  label: string
  slug: string
  tags: string[]
  keywords: string[]
  icon: string
}

const MOOD_ICONS = { CloudSun, Laugh, Heart, Flame, Sparkles, HandHeart } as const

export function MoodIcon({ name, className }: { name: string; className?: string }) {
  const Icon = MOOD_ICONS[name as keyof typeof MOOD_ICONS]
  if (!Icon) return null
  return <Icon className={className ?? 'w-5 h-5'} aria-hidden="true" />
}

export const MOOD_CONFIG: MoodConfig[] = [
  {
    label: 'I want something quiet',
    slug: 'quiet',
    tags: ['Calm', 'Gentle'],
    keywords: ['poetry', 'nature', 'wellness', 'mindfulness', 'cooking', 'self-help', 'gardening', 'crafts', 'watercolor', 'relaxation', 'birds', 'herbs', 'sewing'],
    icon: 'CloudSun',
  },
  {
    label: 'I want to laugh',
    slug: 'funny',
    tags: ['Funny'],
    keywords: ['humor', 'comedy', 'satire', 'funny', 'party'],
    icon: 'Laugh',
  },
  {
    label: 'I want to feel good',
    slug: 'hopeful',
    tags: ['Hopeful'],
    keywords: ['inspirational', 'hope', 'uplifting', 'coming-of-age', 'romance', 'community', 'friendship', 'family', 'recovery'],
    icon: 'Heart',
  },
  {
    label: 'I want something gripping',
    slug: 'gripping',
    tags: ['Intense', 'Dark'],
    keywords: ['thriller', 'suspense', 'mystery', 'dystopian', 'horror', 'noir', 'psychological', 'crime', 'police', 'courtroom', 'cyberattack'],
    icon: 'Flame',
  },
  {
    label: 'I want to be surprised',
    slug: 'surprising',
    tags: ['Mind-bending'],
    keywords: ['science fiction', 'time travel', 'fantasy', 'magical realism', 'cyberpunk', 'solarpunk', 'space', 'genetics', 'climate fiction', 'post-apocalyptic'],
    icon: 'Sparkles',
  },
  {
    label: 'I want to feel understood',
    slug: 'understood',
    tags: ['Personal'],
    keywords: ['memoir', 'autobiography', 'LGBTQ+', 'neurodiversity', 'identity', 'immigration', 'mental health', 'autism', 'ADHD', 'disability', 'introversion'],
    icon: 'HandHeart',
  },
]
