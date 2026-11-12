/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import {
  PenTool, BookOpen, MapPin, Palette, Headphones,
} from 'lucide-react'

export interface AITool {
  name: string
  tagline: string
  summary?: string
  description: string
  icon: React.ElementType
  status: 'available' | 'in-library' | 'coming-soon'
  iconColor?: string
  link?: string
}

export const aiTools: AITool[] = [
  {
    name: 'AI Writing Assistant',
    tagline: 'Your words stay yours.',
    summary: 'Get help drafting emails, cover letters, and essays. In-library only.',
    description: 'Get help brainstorming, editing, drafting cover letters, or getting unstuck. Runs entirely on library computers.',
    icon: PenTool,
    status: 'in-library',
    iconColor: 'text-status-success-600 dark:text-status-success-400',
  },
  {
    name: 'What Should I Read Next?',
    tagline: 'Better than "customers also bought."',
    summary: 'Tell us what you liked and get personalized book recommendations. Works from home.',
    description: 'Tell us what you liked (or didn\'t), and we\'ll suggest your next read. No tracking, no ads, just books.',
    icon: BookOpen,
    status: 'available',
    iconColor: 'text-lsc-rose',
  },
  {
    name: 'AR Local History Tours',
    tagline: 'See the past come alive.',
    summary: 'Point your phone at local landmarks to see how they looked decades ago.',
    description: 'Augmented reality walking tours of our town. Point your device at buildings and landmarks to see how they looked in the past.',
    icon: MapPin,
    status: 'available',
    iconColor: 'text-category-500 dark:text-category-400',
  },
  {
    name: 'Immersive Content Creation',
    tagline: 'Create in virtual space.',
    summary: 'Use VR/AR tools to create art, music, and stories in immersive environments.',
    description: 'Use VR/AR tools to create art, music, and stories in immersive environments. Build virtual worlds or enhance real spaces with digital elements.',
    icon: Palette,
    status: 'coming-soon',
    iconColor: 'text-category-500 dark:text-category-400',
  },
  {
    name: 'AI Podcasting Assistant',
    tagline: 'From idea to episode.',
    summary: 'AI-powered script writing and audio editing for local creators and storytellers.',
    description: 'Create professional podcasts with AI-powered script writing, voice cloning, and audio editing. Perfect for local creators, businesses, and storytellers.',
    icon: Headphones,
    status: 'available',
    iconColor: 'text-lsc-rose dark:text-lsc-rose-light',
  },
]

export interface ReadingMood {
  emoji: string
  label: string
  prompt: string
}

export const readingMoods: ReadingMood[] = [
  { emoji: '☕', label: 'Something cozy', prompt: 'Recommend a cozy book for me - something warm and comforting' },
  { emoji: '😱', label: "Can't put it down", prompt: "I need a page-turner - a book I can't put down. What would you recommend?" },
  { emoji: '😂', label: 'Make me laugh', prompt: 'I want to laugh - give me a funny book recommendation' },
]
