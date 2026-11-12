/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import {
  Book, MessageCircle, Upload, Search, ChevronRight, Loader,
  Clock, Users, BookOpen, ArrowRight, CheckCircle2,
} from 'lucide-react'
import { genealogyDashboardApi, type GenealogyDashboard } from '@/api/genealogy-api'
import { useTranslation } from '@/i18n'
import { usePageTitle } from '@/hooks/usePageTitle'
import { useBranding } from '@/contexts/BrandingContext'

// ============================================================================
// Stat Card
// ============================================================================

function StatCard({ value, label, icon }: { value: number; label: string; icon: React.ReactNode }) {
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-5 text-center">
      <div className="flex justify-center mb-2 text-lsc-rose dark:text-lsc-rose-light">
        {icon}
      </div>
      <p className="text-3xl font-bold font-serif text-lsc-dark dark:text-lsc-cream">
        {value}
      </p>
      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-0.5">
        {label}
      </p>
    </div>
  )
}

// ============================================================================
// Service Card
// ============================================================================

interface ServiceCardProps {
  title: string
  description: string
  icon: React.ReactNode
  href: string
  cta: string
  highlights: string[]
  color: string
}

function ServiceCard({ title, description, icon, href, cta, highlights, color }: ServiceCardProps) {
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden hover:shadow-lg transition-shadow group">
      {/* Header */}
      <div className={`${color} p-6`}>
        <div className="w-12 h-12 rounded-xl bg-lsc-white dark:bg-earth-800/20 flex items-center justify-center mb-3">
          {icon}
        </div>
        <h3 className="text-xl font-serif font-bold text-white">
          {title}
        </h3>
        <p className="text-white/80 text-sm mt-1">
          {description}
        </p>
      </div>

      {/* Body */}
      <div className="p-6 space-y-4">
        <ul className="space-y-2">
          {highlights.map((item, idx) => (
            <li key={idx} className="flex items-start gap-2 text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
              <CheckCircle2 className="w-4 h-4 text-status-success-500 flex-shrink-0 mt-0.5" />
              {item}
            </li>
          ))}
        </ul>
        <a
          href={href}
          className="flex items-center justify-between w-full px-4 py-3 bg-lsc-cream dark:bg-earth-700 hover:bg-lsc-border dark:hover:bg-earth-600 rounded-lg font-medium text-lsc-dark dark:text-lsc-cream transition-colors group-hover:bg-lsc-rose group-hover:text-white dark:group-hover:bg-lsc-rose"
        >
          <span>{cta}</span>
          <ArrowRight className="w-4 h-4" />
        </a>
      </div>
    </div>
  )
}

// ============================================================================
// Latest Courses Widget
// ============================================================================

function LatestCoursesWidget({ courses }: { courses: GenealogyDashboard['latest_courses'] }) {
  if (courses.length === 0) return null

  const difficultyColors: Record<string, string> = {
    beginner: 'bg-status-success-50 text-status-success-700 dark:bg-status-success-900/20 dark:text-status-success-300',
    intermediate: 'bg-status-warning-50 text-status-warning-700 dark:bg-status-warning-900/20 dark:text-status-warning-300',
    advanced: 'bg-status-danger-50 text-status-danger-700 dark:bg-status-danger-900/20 dark:text-status-danger-300',
  }

  return (
    <div className="space-y-3">
      {courses.map(course => (
        <div key={course.id} className="flex items-start gap-3 p-4 bg-lsc-cream/50 dark:bg-earth-700/50 rounded-lg">
          <Book className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <p className="font-medium text-sm text-lsc-dark dark:text-lsc-cream truncate" title={course.title}>{course.title}</p>
            <div className="flex items-center gap-2 mt-1">
              <span className={`text-xs px-2 py-0.5 rounded-full ${difficultyColors[course.difficulty_level] || difficultyColors.beginner}`}>
                {course.difficulty_level}
              </span>
              <span className="flex items-center gap-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                <Clock className="w-3 h-3" />
                {course.duration_minutes} min
              </span>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

// ============================================================================
// Latest Archives Widget
// ============================================================================

function LatestArchivesWidget({ submissions }: { submissions: GenealogyDashboard['latest_submissions'] }) {
  if (submissions.length === 0) return null

  return (
    <div className="space-y-3">
      {submissions.map(sub => (
        <div key={sub.id} className="flex items-start gap-3 p-4 bg-lsc-cream/50 dark:bg-earth-700/50 rounded-lg">
          <Upload className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <p className="font-medium text-sm text-lsc-dark dark:text-lsc-cream truncate" title={sub.title}>{sub.title}</p>
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-0.5">
              {sub.material_type} &middot; by {sub.submitter_name}
              {sub.date_or_period && ` &middot; ${sub.date_or_period}`}
            </p>
          </div>
        </div>
      ))}
    </div>
  )
}

// ============================================================================
// Main Page
// ============================================================================

export default function GenealogyPage(): React.ReactElement {
  const branding = useBranding()
  usePageTitle('Genealogy Services', `Research your family history with ${branding.library_short_name} genealogy services, databases, and expert guidance.`)
  const { t } = useTranslation()
  const [dashboard, setDashboard] = useState<GenealogyDashboard | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      try {
        const data = await genealogyDashboardApi.get()
        setDashboard(data)
      } catch {
        // Silently fail - page still renders without stats
      } finally {
        setIsLoading(false)
      }
    }
    load()
  }, [])

  const services: ServiceCardProps[] = [
    {
      title: 'Ask a Genealogist',
      description: t('genealogy.submitAResearchQuestionAnd'),
      icon: <MessageCircle className="w-6 h-6 text-white" aria-hidden="true" />,
      href: '/genealogy/inquiry',
      cta: 'Submit an Inquiry',
      color: 'bg-lsc-rose dark:bg-lsc-rose/90',
      highlights: [
        'Get expert answers to your research questions',
        'Track your inquiry status with progress updates',
        'Response within 2 business days',
        'No appointment needed',
      ],
    },
    {
      title: 'Training Courses',
      description: t('genealogy.freeGenealogyCoursesForAll'),
      icon: <Book className="w-6 h-6 text-white" aria-hidden="true" />,
      href: '/genealogy/training',
      cta: 'Browse Courses',
      color: 'bg-earth-700 dark:bg-earth-600',
      highlights: [
        'Beginner to advanced courses available',
        'Free for library cardholders',
        'In-person sessions with hands-on practice',
        'Enroll online in minutes',
      ],
    },
    {
      title: 'Community Archives',
      description: t('genealogy.browseAndContributeToOur'),
      icon: <Upload className="w-6 h-6 text-white" aria-hidden="true" />,
      href: '/genealogy/archives',
      cta: 'Explore Archives',
      color: 'bg-lsc-brown dark:bg-earth-800',
      highlights: [
        'Photographs, documents, maps & more',
        'Submit your own family history materials',
        'Creative Commons licensing options',
        'Public and restricted access options',
      ],
    },
    {
      title: 'Research Platform',
      description: t('genealogy.buildYourFamilyTreeManage'),
      icon: <Search className="w-6 h-6 text-white" aria-hidden="true" />,
      href: '/genealogy/research',
      cta: 'Start a Research Project',
      color: 'bg-lsc-rose/90 dark:bg-earth-800',
      highlights: [
        'Collaborative family tree builder',
        'Document management and OCR',
        'AI-powered research suggestions',
        'DNA profile tracking',
      ],
    },
  ]

  return (
    <div className="space-y-10 max-w-5xl mx-auto">
      {/* Hero */}
      <div className="text-center space-y-4 py-4">
        <div className="flex justify-center mb-4">
          <div className="w-20 h-20 rounded-full bg-lsc-rose/10 dark:bg-lsc-rose/20 flex items-center justify-center">
            <BookOpen className="w-10 h-10 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
          </div>
        </div>
        <h1 className="text-3xl md:text-5xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
          Genealogy Services
        </h1>
        <p className="text-lg md:text-xl text-lsc-dark/70 dark:text-lsc-cream/70 max-w-2xl mx-auto">
          Discover your family history with expert guidance, community resources,
          and free training programs from our local history specialists.
        </p>
      </div>

      {/* Stats */}
      {isLoading ? (
        <div className="flex items-center justify-center py-8">
          <Loader className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" />
          <span className="ml-2 text-lsc-dark/70 dark:text-lsc-cream/70">Loading...</span>
        </div>
      ) : dashboard && (
        <div className="grid grid-cols-2 gap-4">
          <StatCard
            value={dashboard.active_courses}
            label="Active Courses"
            icon={<Book className="w-6 h-6" />}
          />
          <StatCard
            value={dashboard.published_submissions}
            label="Archive Items"
            icon={<Upload className="w-6 h-6" />}
          />
        </div>
      )}

      {/* Services Grid */}
      <div>
        <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-6">
          Genealogy Services
        </h2>
        <div className="grid md:grid-cols-2 gap-6">
          {services.map(service => (
            <ServiceCard key={service.href} {...service} />
          ))}
        </div>
      </div>

      {/* Recent Activity */}
      {dashboard && (dashboard.latest_courses.length > 0 || dashboard.latest_submissions.length > 0) && (
        <div className="grid md:grid-cols-2 gap-6">
          {dashboard.latest_courses.length > 0 && (
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-5">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
                  <Book className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
                  Upcoming Courses
                </h3>
                <a
                  href="/genealogy/training"
                  className="text-xs text-lsc-rose dark:text-lsc-rose-light hover:underline flex items-center gap-1"
                >
                  View all
                  <ChevronRight className="w-3 h-3" />
                </a>
              </div>
              <LatestCoursesWidget courses={dashboard.latest_courses} />
            </div>
          )}

          {dashboard.latest_submissions.length > 0 && (
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-5">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
                  <Upload className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
                  Recently Added Archives
                </h3>
                <a
                  href="/genealogy/archives"
                  className="text-xs text-lsc-rose dark:text-lsc-rose-light hover:underline flex items-center gap-1"
                >
                  View all
                  <ChevronRight className="w-3 h-3" />
                </a>
              </div>
              <LatestArchivesWidget submissions={dashboard.latest_submissions} />
            </div>
          )}
        </div>
      )}

      {/* Getting Started Guide */}
      <div className="bg-lsc-cream dark:bg-earth-700/50 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
        <h2 className="text-xl font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
          New to Genealogy Research?
        </h2>
        <p className="text-lsc-dark/80 dark:text-lsc-cream/80 mb-5">
          Everyone starts somewhere. Here's how to get going:
        </p>
        <ol className="space-y-3">
          {[
            { step: '1', text: t('genealogy.startWithWhatYouKnow') },
            { step: '2', text: 'Attend our free "Getting Started with Genealogy" course' },
            { step: '3', text: t('genealogy.submitAnInquiryToAsk') },
            { step: '4', text: t('genealogy.exploreOurCommunityArchivesAnd') },
            { step: '5', text: t('genealogy.shareWhatYouFindBy') },
          ].map(item => (
            <li key={item.step} className="flex items-start gap-3">
              <span className="w-6 h-6 rounded-full bg-lsc-rose/20 text-lsc-rose dark:text-lsc-rose-light flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5">
                {item.step}
              </span>
              <span className="text-lsc-dark/80 dark:text-lsc-cream/80 text-sm">{item.text}</span>
            </li>
          ))}
        </ol>

        <div className="mt-6 flex flex-col sm:flex-row gap-3">
          <a
            href="/genealogy/inquiry"
            className="inline-flex items-center justify-center gap-2 px-5 py-3 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2 dark:focus:ring-offset-earth-700"
          >
            <MessageCircle className="w-4 h-4" />
            Ask a Genealogist
          </a>
          <a
            href="/genealogy/training"
            className="inline-flex items-center justify-center gap-2 px-5 py-3 bg-lsc-white dark:bg-earth-800 hover:bg-lsc-border dark:hover:bg-earth-700 text-lsc-dark dark:text-lsc-cream rounded-lg font-medium border border-lsc-border dark:border-earth-700 transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2 dark:focus:ring-offset-earth-700"
          >
            <Book className="w-4 h-4" />
            Browse Free Courses
          </a>
        </div>
      </div>

      {/* Local History & Genealogy Desk */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6 flex items-start gap-5">
        <div className="w-16 h-16 rounded-full bg-lsc-rose/20 dark:bg-lsc-rose/30 flex items-center justify-center flex-shrink-0 text-lsc-rose dark:text-lsc-rose-light">
          <Users className="w-8 h-8" />
        </div>
        <div>
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream text-lg">
            Local History & Genealogy Desk
          </h3>
          <p className="text-lsc-dark/80 dark:text-lsc-cream/80 text-sm mt-1">
            Our local history and genealogy staff can help with everything from getting
            started to breaking through the toughest research "brick walls." We teach
            our genealogy courses and respond personally to every inquiry.
          </p>
          <div className="flex flex-wrap gap-2 mt-3">
            {['Vital Records', 'Census Research', 'Immigration Records', 'DNA Genealogy', 'Local Archives'].map(tag => (
              <span key={tag} className="text-xs px-2.5 py-1 bg-lsc-rose/10 text-lsc-rose dark:text-lsc-rose-light rounded-full">
                {tag}
              </span>
            ))}
          </div>
          <a
            href="/genealogy/inquiry"
            className="inline-flex items-center gap-2 mt-4 text-sm text-lsc-rose dark:text-lsc-rose-light hover:underline font-medium"
          >
            Ask a Question
            <ChevronRight className="w-4 h-4" />
          </a>
        </div>
      </div>

      {/* Quick Links */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { href: '/genealogy/inquiry', label: 'Submit Inquiry', icon: <MessageCircle className="w-5 h-5" /> },
          { href: '/genealogy/training', label: 'Training Courses', icon: <Book className="w-5 h-5" /> },
          { href: '/genealogy/archives', label: 'Community Archives', icon: <Upload className="w-5 h-5" /> },
          { href: '/genealogy/archives/submit', label: 'Share Your History', icon: <Users className="w-5 h-5" /> },
        ].map(link => (
          <a
            key={link.href}
            href={link.href}
            className="flex flex-col items-center gap-2 p-4 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 hover:border-lsc-rose dark:hover:border-lsc-rose hover:shadow-md transition-all text-center group"
          >
            <div className="text-lsc-rose dark:text-lsc-rose-light group-hover:scale-110 transition-transform">
              {link.icon}
            </div>
            <span className="text-xs font-medium text-lsc-dark dark:text-lsc-cream">{link.label}</span>
          </a>
        ))}
      </div>
    </div>
  )
}
