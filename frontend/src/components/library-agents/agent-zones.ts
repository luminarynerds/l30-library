/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import {
  Building2, Cpu, BookOpen, Heart, Gamepad2, ArrowLeftRight, MapPin,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import type { LibraryAgent } from '../../api/library-agents-api'

export interface LibraryZone {
  id: string
  name: string
  icon: LucideIcon
  description: string
  colors: {
    accent: string
    bg: string
    iconBg: string
    iconText: string
    text: string
  }
  gridClass: string
  matchAgent: (agent: LibraryAgent) => boolean
}

export const LIBRARY_ZONES: LibraryZone[] = [
  {
    id: 'directors-office',
    name: "Director's Office",
    icon: Building2,
    description: 'Leadership, strategy & community partnerships',
    colors: {
      accent: 'border-status-warning-500 dark:border-status-warning-400',
      bg: 'bg-status-warning-50/50 dark:bg-status-warning-900/10',
      iconBg: 'bg-status-warning-100 dark:bg-status-warning-900/30',
      iconText: 'text-status-warning-600 dark:text-status-warning-400',
      text: 'text-status-warning-700 dark:text-status-warning-300',
    },
    gridClass: '',
    matchAgent: (a) => {
      const r = a.role.toLowerCase()
      return r.includes('director') && !r.includes('assistant') && !r.includes('branch')
    },
  },
  {
    id: 'tech-hub',
    name: 'Tech Hub & Makerspace',
    icon: Cpu,
    description: '3D printing, digital tools & innovation',
    colors: {
      accent: 'border-lsc-rose/50 dark:border-earth-400',
      bg: 'bg-earth-50/50 dark:bg-earth-800/10',
      iconBg: 'bg-earth-100 dark:bg-earth-800/30',
      iconText: 'text-lsc-rose dark:text-lsc-rose-light',
      text: 'text-lsc-rose dark:text-lsc-rose-light',
    },
    gridClass: 'md:col-span-2',
    matchAgent: (a) => a.department === 'Technology',
  },
  {
    id: 'reference-desk',
    name: 'Reference Desk',
    icon: BookOpen,
    description: 'Research, local history & genealogy',
    colors: {
      accent: 'border-lsc-rose',
      bg: 'bg-lsc-cream/50 dark:bg-lsc-brown/10',
      iconBg: 'bg-lsc-rose/10 dark:bg-lsc-rose/20',
      iconText: 'text-lsc-rose dark:text-lsc-rose-light',
      text: 'text-lsc-rose dark:text-lsc-rose-light',
    },
    gridClass: '',
    matchAgent: (a) => a.department === 'Adult Services' || a.role.toLowerCase().includes('reference'),
  },
  {
    id: 'childrens-room',
    name: "Children's Room",
    icon: Heart,
    description: 'Story time, reading programs & bilingual fun',
    colors: {
      accent: 'border-pink-500 dark:border-pink-400',
      bg: 'bg-pink-50/50 dark:bg-pink-900/10',
      iconBg: 'bg-pink-100 dark:bg-pink-900/30',
      iconText: 'text-pink-600 dark:text-pink-400',
      text: 'text-pink-700 dark:text-pink-300',
    },
    gridClass: '',
    matchAgent: (a) => a.role.toLowerCase().includes('children'),
  },
  {
    id: 'youth-lounge',
    name: 'Youth Lounge',
    icon: Gamepad2,
    description: 'Teen programs, book clubs & gaming',
    colors: {
      accent: 'border-category-500 dark:border-category-400',
      bg: 'bg-category-50/50 dark:bg-category-900/10',
      iconBg: 'bg-category-100 dark:bg-category-900/30',
      iconText: 'text-category-600 dark:text-category-400',
      text: 'text-category-700 dark:text-category-300',
    },
    gridClass: '',
    matchAgent: (a) => {
      const r = a.role.toLowerCase()
      return r.includes('youth') || r.includes('teen')
    },
  },
  {
    id: 'circulation',
    name: 'Circulation Desk',
    icon: ArrowLeftRight,
    description: 'Checkouts, holds, accounts & library cards',
    colors: {
      accent: 'border-rose-500 dark:border-rose-400',
      bg: 'bg-rose-50/50 dark:bg-rose-900/10',
      iconBg: 'bg-rose-100 dark:bg-rose-900/30',
      iconText: 'text-rose-700 dark:text-rose-400',
      text: 'text-rose-700 dark:text-rose-300',
    },
    gridClass: '',
    matchAgent: (a) => a.department === 'Circulation',
  },
  {
    id: 'elmdale',
    name: 'Elmdale Branch',
    icon: MapPin,
    description: 'Our community branch — small but mighty',
    colors: {
      accent: 'border-status-success-500 dark:border-status-success-400',
      bg: 'bg-status-success-50/50 dark:bg-status-success-900/10',
      iconBg: 'bg-status-success-100 dark:bg-status-success-900/30',
      iconText: 'text-status-success-600 dark:text-status-success-400',
      text: 'text-status-success-700 dark:text-status-success-300',
    },
    gridClass: 'md:col-span-2',
    matchAgent: (a) => a.role.toLowerCase().includes('branch'),
  },
]

export function getAgentIcon(agent: LibraryAgent): LucideIcon {
  for (const zone of LIBRARY_ZONES) {
    if (zone.matchAgent(agent)) return zone.icon
  }
  return LIBRARY_ZONES[2]!.icon // reference-desk fallback
}
