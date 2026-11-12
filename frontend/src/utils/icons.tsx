/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Icon utility module for consistent icon rendering
 * Replaces emoji characters with SVG icons from lucide-react
 */

import {
  Package,
  PackageCheck,
  FileText,
  CheckCircle,
  PlusCircle,
  BookOpen,
  ArrowUpFromLine,
  RefreshCw,
  Bookmark,
  Wrench,
  AlertTriangle,
  Settings,
  Clipboard,
  HelpCircle,
  Search,
  Tag,
  Check,
  X,
  Recycle,
  Trash2,
  MapPin,
  ArrowLeftRight,
  Pin,
  FileQuestion,
  Sun,
  Moon,
  Circle,
  Lightbulb,
  Coffee,
  Laugh,
  BookHeart,
  Trophy,
  Star,
  Snowflake,
  PartyPopper,
  Pause,
  Lock,
  Target,
  Laptop,
  Leaf,
  Gamepad2,
  type LucideIcon,
} from 'lucide-react'
import { createElement } from 'react'

/**
 * Lifecycle event type to icon mapping
 */
export const lifecycleEventIcons: Record<string, LucideIcon> = {
  ordered: Package,
  received: PackageCheck,
  cataloging_started: FileText,
  cataloged: CheckCircle,
  copy_created: PlusCircle,
  shelved: BookOpen,
  checked_out: ArrowUpFromLine,
  returned: PackageCheck,
  renewed: RefreshCw,
  hold_placed: Bookmark,
  hold_filled: CheckCircle,
  condition_changed: Wrench,
  damaged: AlertTriangle,
  repaired: Settings,
  inventoried: Clipboard,
  missing: HelpCircle,
  found: Search,
  marked_for_weeding: Tag,
  weeding_approved: Check,
  weeding_rejected: X,
  weeded: Recycle,
  disposed: Trash2,
  location_changed: MapPin,
  transferred: ArrowLeftRight,
  note_added: Pin,
  other: FileQuestion,
}

/**
 * Theme option icons
 */
export const themeIcons = {
  light: Sun,
  dark: Moon,
  'high-contrast': Circle,
}

/**
 * Program type icons
 */
export const programTypeIcons = {
  summer: Sun,
  winter: Snowflake,
  year_round: BookOpen,
  special: PartyPopper,
}

/**
 * Miscellaneous icons
 */
export const miscIcons = {
  funFact: Lightbulb,
  favoriteBook: BookOpen,
  cozy: Coffee,
  exciting: BookHeart,
  funny: Laugh,
  trophy: Trophy,
  star: Star,
  pause: Pause,
  lock: Lock,
  books: BookOpen,
}

/**
 * Agent emoji to icon mapping
 * Maps emoji characters used by library agents to lucide-react icons
 */
export const agentEmojiIcons: Record<string, LucideIcon> = {
  '🎯': Target,      // Marlene - Library Director
  '💻': Laptop,      // Stevie - Assistant Director
  '📖': BookOpen,    // Pat - Reference Librarian
  '📚': BookOpen,    // Sophie - Children's Librarian
  '🌿': Leaf,        // Donna Fay - Elmdale Branch Manager
  '🎮': Gamepad2,    // Twyla - Youth Services Librarian
  '🔧': Wrench,      // Jordan - Technology Specialist
  '📋': Clipboard,   // Thel - Circulation Manager
}

export function getLifecycleIcon(eventType: string, className?: string): React.ReactNode {
  const IconComponent = lifecycleEventIcons[eventType] || FileQuestion
  return createElement(IconComponent, { className: className || 'w-4 h-4', 'aria-hidden': true })
}

export function getThemeIcon(theme: 'light' | 'dark' | 'high-contrast', className?: string): React.ReactNode {
  const IconComponent = themeIcons[theme]
  return createElement(IconComponent, { className: className || 'w-4 h-4', 'aria-hidden': true })
}

export function getProgramTypeIcon(programType: string, className?: string): React.ReactNode {
  const IconComponent = programTypeIcons[programType as keyof typeof programTypeIcons] || BookOpen
  return createElement(IconComponent, { className: className || 'w-4 h-4', 'aria-hidden': true })
}

export function renderStars(count: number, className?: string): React.ReactNode {
  return Array.from({ length: count }, (_, i) =>
    createElement(Star, {
      key: i,
      className: `${className || 'w-4 h-4'} fill-current text-status-warning-400`,
      'aria-hidden': true
    })
  )
}

/**
 * Emoji-to-specialty label mapping for agent icons
 */
export const agentEmojiLabels: Record<string, string> = {
  '\u{1F3AF}': 'Leadership',       // Marlene - Library Director
  '\u{1F4BB}': 'Technology',       // Stevie - Assistant Director
  '\u{1F4D6}': 'Reference',       // Pat - Reference Librarian
  '\u{1F4DA}': "Children's services", // Sophie - Children's Librarian
  '\u{1F33F}': 'Branch services',  // Donna Fay - Elmdale Branch Manager
  '\u{1F3AE}': 'Youth services',   // Twyla - Youth Services Librarian
  '\u{1F527}': 'Tech support',     // Jordan - Technology Specialist
  '\u{1F4CB}': 'Circulation',      // Thel - Circulation Manager
}

export function getAgentIcon(emoji: string, className?: string, accessible?: boolean): React.ReactNode {
  const IconComponent = agentEmojiIcons[emoji] || HelpCircle
  const label = agentEmojiLabels[emoji] || 'Specialty'
  if (accessible) {
    // Wrap in a span with title tooltip; icon gets aria-hidden, span gets aria-label
    return createElement(
      'span',
      { title: label, 'aria-label': label, role: 'img' },
      createElement(IconComponent, { className: className || 'w-5 h-5', 'aria-hidden': true })
    )
  }
  return createElement(IconComponent, { className: className || 'w-5 h-5', 'aria-hidden': true })
}
