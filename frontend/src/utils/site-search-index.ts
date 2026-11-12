/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
export interface StaticSiteSearchEntry {
  id: string
  title: string
  snippet: string
  url: string
  keywords: string[]
  audience?: 'public' | 'staff'
}

export interface StaticSiteSearchResult {
  id: string
  entity_type: 'page'
  title: string
  snippet: string
  url: string
  score: number
  source: 'site-index'
}

export const STATIC_SITE_SEARCH_INDEX: StaticSiteSearchEntry[] = [
  { id: 'home', title: 'Home', snippet: 'Library homepage and quick links.', url: '/', keywords: ['home', 'library'] },
  { id: 'catalog', title: 'Catalog', snippet: 'Search books, eBooks, audiobooks, and more.', url: '/catalog', keywords: ['catalog', 'books', 'ebooks', 'audiobooks', 'search'] },
  { id: 'events', title: 'Events', snippet: 'Community events, classes, and workshops.', url: '/events', keywords: ['events', 'classes', 'workshops', 'calendar'] },
  { id: 'programs', title: 'Reading Programs', snippet: 'Reading challenges and literacy programs.', url: '/programs', keywords: ['reading', 'challenge', 'literacy', 'programs'] },
  { id: 'digital', title: 'Digital Resources', snippet: 'eBooks, streaming, and online learning tools.', url: '/digital', keywords: ['digital', 'ebooks', 'streaming', 'resources'] },
  { id: 'ai-tools', title: 'AI Tools', snippet: 'Library AI tools that run on our server, plus how to try them.', url: '/ai', keywords: ['ai', 'tools', 'assistant'] },
  { id: 'ai-how-it-works', title: 'How AI works at L30', snippet: 'Policy, the eight-criteria rubric, hardware, system prompts, and the wrongness log.', url: '/ai/how-it-works', keywords: ['ai', 'policy', 'rubric', 'transparency', 'receipts', 'hardware', 'philosophy', 'wrongness'] },
  { id: 'databases', title: 'Research Databases', snippet: 'Academic and research database access.', url: '/databases', keywords: ['databases', 'research', 'journals'] },
  { id: 'genealogy', title: 'Genealogy', snippet: 'Family history and genealogy research resources.', url: '/genealogy', keywords: ['genealogy', 'family history', 'archives'] },
  { id: 'makerspace', title: 'Makerspace', snippet: 'Create, build, and learn with makerspace tools.', url: '/makerspace', keywords: ['makerspace', '3d printing', 'creation'] },
  { id: 'branches', title: 'Branches & Locations', snippet: 'Find library branches, hours, and directions.', url: '/branches', keywords: ['branches', 'locations', 'hours', 'directions'] },
  { id: 'rooms', title: 'Room Booking', snippet: 'Reserve meeting and study rooms.', url: '/rooms', keywords: ['rooms', 'booking', 'study rooms'] },
  { id: 'contact', title: 'Contact', snippet: 'Contact the library team.', url: '/contact', keywords: ['contact', 'phone', 'email'] },
  { id: 'faq', title: 'FAQ', snippet: 'Frequently asked questions and answers.', url: '/faq', keywords: ['faq', 'help', 'questions'] },
  { id: 'help', title: 'Knowledge Base', snippet: 'Self-service help and support articles.', url: '/help', keywords: ['knowledge base', 'help', 'support', 'guides'] },
  { id: 'tech-support', title: 'Tech Support Hub', snippet: 'Digital and device help resources.', url: '/tech', keywords: ['tech support', 'devices', 'digital help'] },
  { id: 'about', title: 'About Us', snippet: 'Library mission, story, and impact.', url: '/about', keywords: ['about', 'mission', 'story'] },
  { id: 'transparency', title: 'Transparency', snippet: 'Material costs, public records requests, board meetings, book challenges, AI use, and patron stats.', url: '/transparency', keywords: ['transparency', 'public records', 'records request', 'open records', 'material costs', 'board meetings', 'book challenges', 'banned books', 'ai', 'stats'] },
  { id: 'our-story', title: 'Our Story', snippet: 'Learn the story behind the library.', url: '/our-story', keywords: ['story', 'history', 'about'] },
  { id: 'careers', title: 'Careers', snippet: 'Open positions and hiring information.', url: '/careers', keywords: ['careers', 'jobs', 'hiring'] },
  { id: 'donate', title: 'Donate', snippet: 'Support the library with donations.', url: '/donate', keywords: ['donate', 'support', 'giving'] },
  { id: 'privacy', title: 'Privacy', snippet: 'Privacy policy and data handling.', url: '/privacy', keywords: ['privacy', 'policy', 'data'] },
  { id: 'terms', title: 'Terms of Service', snippet: 'Terms and conditions for using the site.', url: '/terms', keywords: ['terms', 'service', 'policy'] },
  { id: 'announcements', title: 'Announcements', snippet: 'Latest service and community announcements.', url: '/announcements', keywords: ['announcements', 'updates', 'news'] },
  { id: 'ask-librarian', title: 'Ask a Librarian', snippet: 'Get personalized help from library staff.', url: '/ask-librarian', keywords: ['ask librarian', 'reference help', 'research help'] },
  { id: 'card', title: 'Library Card Application', snippet: 'Apply for a library card online.', url: '/card-application', keywords: ['card', 'library card', 'application'] },
  { id: 'youth', title: 'Youth Services', snippet: 'Programs and learning resources for youth.', url: '/youth', keywords: ['youth', 'teens', 'kids'] },
  { id: 'learning-paths', title: 'Learning Paths', snippet: 'Guided learning journeys and courses.', url: '/learning-paths', keywords: ['learning', 'courses', 'paths'] },
  { id: 'read-to-reduce', title: 'Read to Reduce', snippet: 'Reading challenge to reduce stress.', url: '/read-to-reduce', keywords: ['read to reduce', 'reading challenge'] },
  { id: 'public-reading-lists', title: 'Public Reading Lists', snippet: 'Curated reading lists from library staff.', url: '/public-reading-lists', keywords: ['reading lists', 'book lists', 'recommendations'] },
  { id: 'status', title: 'Service Status', snippet: 'Current service and system status.', url: '/status', keywords: ['status', 'uptime', 'outages'] },
]

function textForSearch(entry: StaticSiteSearchEntry): string {
  return `${entry.title} ${entry.snippet} ${entry.keywords.join(' ')} ${entry.url}`.toLowerCase()
}

function calculateScore(query: string, entry: StaticSiteSearchEntry): number {
  const normalizedQuery = query.toLowerCase()
  const haystack = textForSearch(entry)

  if (entry.title.toLowerCase() === normalizedQuery) return 1
  if (entry.title.toLowerCase().startsWith(normalizedQuery)) return 0.9
  if (entry.url.toLowerCase().includes(normalizedQuery)) return 0.85
  if (entry.keywords.some((keyword) => keyword.toLowerCase() === normalizedQuery)) return 0.82
  if (haystack.includes(normalizedQuery)) return 0.75
  return 0
}

export function searchStaticSiteIndex(query: string, limit: number = 25): StaticSiteSearchResult[] {
  const normalizedQuery = query.trim().toLowerCase()
  if (!normalizedQuery) return []

  return STATIC_SITE_SEARCH_INDEX
    .map((entry) => ({ entry, score: calculateScore(normalizedQuery, entry) }))
    .filter((item) => item.score > 0)
    .sort((a, b) => b.score - a.score || a.entry.title.localeCompare(b.entry.title))
    .slice(0, limit)
    .map(({ entry, score }) => ({
      id: `page:${entry.id}`,
      entity_type: 'page' as const,
      title: entry.title,
      snippet: entry.snippet,
      url: entry.url,
      score,
      source: 'site-index' as const,
    }))
}
