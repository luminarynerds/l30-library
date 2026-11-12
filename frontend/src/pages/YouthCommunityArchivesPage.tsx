/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useMemo } from 'react'
import toast from 'react-hot-toast'
import {
  Archive,
  Mail,
  Phone,
  Search,
  FileText,
  Image,
  Music,
  Video,
  Download,
  Trash2,
  AlertCircle,
  BookOpen,
  Calendar,
  ExternalLink,
} from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { useTranslation} from '@/i18n'
import { useBranding } from '@/contexts/BrandingContext'
import YouthSubNav from '@/pages/youth/YouthSubNav'
import PageContainer from '@/components/layout/PageContainer'

interface Submission {
  id: string
  title: string
  description: string
  type: 'document' | 'photo' | 'audio' | 'video'
  submittedDate: string
  status: 'pending' | 'approved' | 'archived'
  category: string
}

interface ArchiveResource {
  id: string
  title: string
  description: string
  type: string
  url?: string
  link: string
}

function getTypeIcon(type: Submission['type'] | string): React.ReactNode {
  switch (type) {
    case 'document':
      return <FileText aria-hidden="true" className="w-5 h-5" />
    case 'photo':
      return <Image aria-hidden="true" className="w-5 h-5" />
    case 'audio':
      return <Music aria-hidden="true" className="w-5 h-5" />
    case 'video':
      return <Video aria-hidden="true" className="w-5 h-5" />
    default:
      return <Archive aria-hidden="true" className="w-5 h-5" />
  }
}

function getStatusColor(status: Submission['status']): string {
  switch (status) {
    case 'approved':
      return 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-800 dark:text-status-success-300'
    case 'pending':
      return 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-800 dark:text-status-warning-300'
    case 'archived':
      return 'bg-earth-100 dark:bg-earth-800/30 text-earth-800 dark:text-lsc-rose-light'
    default:
      return 'bg-earth-100 dark:bg-earth-900/30 text-earth-800 dark:text-earth-300'
  }
}

export default function YouthCommunityArchivesPage(): React.ReactElement {
  const { t } = useTranslation()
  const branding = useBranding()
  const initialSubmissions: Submission[] = useMemo(() => [
    {
      id: '1',
      title: t('youthCommunityArchives.localHistoricalPhotosSMain'),
      description: t('youthCommunityArchives.collectionOfVintagePhotographsShowing'),
      type: 'photo',
      submittedDate: '2024-02-10',
      status: 'approved',
      category: 'History',
    },
    {
      id: '2',
      title: t('youthCommunityArchives.interviewWithCommunityFounder'),
      description: t('youthCommunityArchives.recordedOralHistoryInterviewDiscussing'),
      type: 'audio',
      submittedDate: '2024-02-08',
      status: 'approved',
      category: 'Oral History',
    },
    {
      id: '3',
      title: 'Family Tree Documentation',
      description: t('youthCommunityArchives.digitizedFamilyTreeRecordsAnd'),
      type: 'document',
      submittedDate: '2024-02-12',
      status: 'pending',
      category: 'Genealogy',
    },
  ], [t])
  const genealogyResources: ArchiveResource[] = useMemo(() => [
    {
      id: 'ancestory',
      title: t('youthCommunityArchives.ancestryComLibraryAccess'),
      description: t('youthCommunityArchives.freeAccessToGenealogyDatabases'),
      type: 'Database',
      link: 'https://www.ancestry.com',
    },
    {
      id: 'familysearch',
      title: 'FamilySearch.org',
      description: t('youthCommunityArchives.freeGenealogyResearchToolWith'),
      type: 'Online Tool',
      link: 'https://www.familysearch.org',
    },
    {
      id: 'newspapers',
      title: 'Historical Newspapers Collection',
      description: t('youthCommunityArchives.searchDigitizedNewspapersFromLocal'),
      type: 'Collection',
      link: 'https://chroniclingamerica.loc.gov',
    },
    {
      id: 'census',
      title: 'Census Records Archive',
      description: t('youthCommunityArchives.accessToHistoricalUS'),
      type: 'Database',
      link: 'https://www.archives.gov',
    },
    {
      id: 'vital-records',
      title: 'Vital Records Guide',
      description: t('youthCommunityArchives.guideToFindingBirthMarriage'),
      type: 'Guide',
      link: 'https://www.cdc.gov/nchs/w2w/index.htm',
    },
    {
      id: 'local-history',
      title: t('youthCommunityArchives.localHistoryRoomMaterials'),
      description: t('youthCommunityArchives.physicalAndDigitalMaterialsIn'),
      type: 'Collection',
      link: 'https://www.loc.gov',
    },
  ], [t])
  const [activeTab, setActiveTab] = useState<'browse' | 'submit' | 'genealogy'>('browse')
  const [submissions, setSubmissions] = useState(initialSubmissions)
  const [searchQuery, setSearchQuery] = useState('')

  const filteredSubmissions = submissions.filter(
    (submission) =>
      submission.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      submission.description.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const deleteSubmission = (id: string) => {
    toast.success(t('toast.youthCommunityArchives.submissionDeleted'))
    setSubmissions(submissions.filter((s) => s.id !== id))
  }

  return (
    <div className="min-h-screen bg-lsc-cream dark:bg-lsc-dark">
      <YouthSubNav />
      {/* Header */}
      <div className="bg-lsc-white dark:bg-earth-800 border-b border-lsc-border dark:border-earth-700">
        <PageContainer className="py-8">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-lsc-cream dark:bg-earth-800/30 rounded-xl">
              <Archive aria-hidden="true" className="w-8 h-8 text-lsc-rose dark:text-lsc-rose-light" />
            </div>
            <div>
              <h1 className="text-3xl font-serif font-bold text-lsc-dark dark:text-earth-50">
                Community Archives & Genealogy
              </h1>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                Preserve our community's history and explore your family roots
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
              <h3 className="font-serif font-semibold text-earth-900 dark:text-earth-200 mb-1">{t('youthCommunityArchives.helpPreserveOurHistory')}</h3>
              <p className="text-earth-800 dark:text-lsc-rose-light text-sm mb-3">
                Do you have photographs, documents, or recordings that tell the story of our community? We'd love to include them in our digital archives!
              </p>
              <p className="text-earth-800 dark:text-lsc-rose-light text-sm">
                All submissions are reviewed by our archivists and made available to the public with proper attribution.
              </p>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="border-b border-lsc-border dark:border-earth-700 mb-8">
          <nav className="flex gap-6">
            {[
              { id: 'browse', label: 'Browse Archives', icon: <Archive aria-hidden="true" className="w-4 h-4" /> },
              { id: 'submit', label: 'Contribute', icon: <Mail aria-hidden="true" className="w-4 h-4" /> },
              { id: 'genealogy', label: 'Genealogy Resources', icon: <BookOpen aria-hidden="true" className="w-4 h-4" /> },
            ].map((tab) => (
              <Button variant="secondary"
                key={tab.id}
                onClick={() => setActiveTab(tab.id as 'browse' | 'submit' | 'genealogy')}
              >
                {tab.icon}
                <span>{tab.label}</span>
              </Button>
            ))}
          </nav>
        </div>

        {/* Browse Archives Tab */}
        {activeTab === 'browse' && (
          <div>
            {/* Search */}
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700 mb-6">
              <div className="flex gap-4">
                <div className="flex-1 relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
                  <input
                    type="text"
                    placeholder={t('placeholder.youthCommunityArchives.searchArchives')} aria-label={t('aria.youthCommunityArchives.searchArchives')}
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-10 pr-4 py-2.5 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-earth-50 placeholder-earth-500 dark:placeholder-earth-500 focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                  />
                </div>
              </div>
            </div>

            {/* Submissions List */}
            {filteredSubmissions.length > 0 ? (
              <div className="space-y-4">
                {filteredSubmissions.map((submission) => (
                  <div
                    key={submission.id}
                    className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700 hover:shadow-md transition-shadow"
                  >
                    <div className="flex items-start gap-4">
                      <div className="p-3 bg-lsc-cream dark:bg-earth-800/50 rounded-lg text-lsc-rose dark:text-lsc-rose-light flex-shrink-0">
                        {getTypeIcon(submission.type)}
                      </div>

                      <div className="flex-1">
                        <div className="flex items-start justify-between mb-2">
                          <div>
                            <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-earth-50">{submission.title}</h3>
                            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                              {submission.type.charAt(0).toUpperCase() + submission.type.slice(1)} • {submission.category}
                            </p>
                          </div>
                          <span className={`px-3 py-1 rounded-full text-xs font-medium whitespace-nowrap ${getStatusColor(submission.status)}`}>
                            {submission.status.charAt(0).toUpperCase() + submission.status.slice(1)}
                          </span>
                        </div>

                        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">{submission.description}</p>

                        <div className="flex items-center gap-4 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                          <div className="flex items-center gap-1">
                            <Calendar aria-hidden="true" className="w-4 h-4" />
                            <span>{submission.submittedDate}</span>
                          </div>
                        </div>
                      </div>

                      {submission.status === 'approved' && (
                        <Button variant="secondary" size="sm">
                          <Download aria-hidden="true" />
                        </Button>
                      )}
                      {submission.status === 'pending' && (
                        <Button variant="danger" size="sm"
                          onClick={() => deleteSubmission(submission.id)}
                        >
                          <Trash2 aria-hidden="true" />
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-16">
                <Archive aria-hidden="true" className="w-16 h-16 mx-auto text-lsc-border dark:text-lsc-cream/70 mb-4" />
                <h3 className="text-lg font-medium text-lsc-dark dark:text-earth-50 mb-2">
                  No materials found
                </h3>
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
                  Try adjusting your search or browse other sections
                </p>
              </div>
            )}
          </div>
        )}

        {/* Contribute Tab */}
        {activeTab === 'submit' && (
          <div className="flex justify-center">
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-8 border border-lsc-border dark:border-earth-700 max-w-2xl w-full">
              <div className="text-center mb-6">
                <div className="inline-flex p-3 bg-lsc-cream dark:bg-earth-800/50 rounded-xl mb-4">
                  <Archive aria-hidden="true" className="w-10 h-10 text-lsc-rose dark:text-lsc-rose-light" />
                </div>
                <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-earth-50">
                  Contribute to Our Archives
                </h2>
              </div>

              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
                We'd love to include your photographs, documents, recordings, and other materials that tell the story of our community. All submissions are reviewed by our archivists.
              </p>

              <p className="text-lsc-dark dark:text-earth-50 font-medium mb-3">
                To get started, contact our Local History department:
              </p>

              <div className="space-y-3 mb-6 pl-1">
                <div className="flex items-center gap-3">
                  <Mail aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0" />
                  <a href={`mailto:${branding.contact_email}`} className="text-lsc-rose dark:text-lsc-rose-light hover:underline">
                    {branding.contact_email}
                  </a>
                </div>
                {branding.phone && (
                  <div className="flex items-center gap-3">
                    <Phone aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0" />
                    <a
                      href={`tel:${branding.phone.replace(/\D/g, '')}`}
                      className="text-lsc-rose dark:text-lsc-rose-light hover:underline"
                    >
                      {branding.phone}
                    </a>
                  </div>
                )}
                <div className="flex items-center gap-3">
                  <Archive aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0" />
                  <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Main Branch, Local History Room (2nd floor)</span>
                </div>
              </div>

              <div className="bg-lsc-cream dark:bg-earth-800/30 rounded-lg p-4 border border-lsc-border dark:border-earth-700">
                <h3 className="font-serif font-semibold text-lsc-dark dark:text-earth-50 mb-2">What we accept:</h3>
                <ul className="space-y-1.5 text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">
                  <li className="flex items-start gap-2">
                    <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">&#8226;</span>
                    Photographs and postcards (originals or high-quality scans)
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">&#8226;</span>
                    Letters, diaries, and documents
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">&#8226;</span>
                    Audio and video recordings
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-lsc-rose dark:text-lsc-rose-light mt-1">&#8226;</span>
                    Maps, blueprints, and newspapers
                  </li>
                </ul>
              </div>
            </div>
          </div>
        )}

        {/* Genealogy Resources Tab */}
        {activeTab === 'genealogy' && (
          <div>
            <div className="mb-8">
              <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-earth-50 mb-4">
                Research Your Family History
              </h2>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-6">
                Use these resources to discover your family roots and connect with your heritage. Many are available free through your library card!
              </p>
            </div>

            <div className="grid md:grid-cols-2 gap-6">
              {genealogyResources.map((resource) => (
                <div
                  key={resource.id}
                  className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700 hover:shadow-md transition-shadow"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <h3 className="font-serif font-semibold text-lg text-lsc-dark dark:text-earth-50">{resource.title}</h3>
                      <span className="text-xs font-medium text-lsc-rose dark:text-lsc-rose-light bg-lsc-cream dark:bg-earth-800/50 px-2 py-1 rounded inline-block mt-2">
                        {resource.type}
                      </span>
                    </div>
                  </div>

                  <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">{resource.description}</p>

                  <a
                    href={resource.link}
                    className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg font-medium transition-colors"
                  >
                    <span>Access</span>
                    <ExternalLink aria-hidden="true" className="w-4 h-4" />
                  </a>
                </div>
              ))}
            </div>

            {/* Genealogy Tips */}
            <div className="mt-12 bg-lsc-cream dark:bg-earth-800/20 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
              <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-earth-50 mb-4">{t('youthCommunityArchives.gettingStartedWithGenealogy')}</h3>
              <ul className="space-y-3">
                <li className="flex gap-3">
                  <span className="text-lsc-rose dark:text-lsc-rose-light font-bold flex-shrink-0">1.</span>
                  <span className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('youthCommunityArchives.startWithWhatYouKnow')}</span>
                </li>
                <li className="flex gap-3">
                  <span className="text-lsc-rose dark:text-lsc-rose-light font-bold flex-shrink-0">2.</span>
                  <span className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('youthCommunityArchives.organizeYourFindingsInA')}</span>
                </li>
                <li className="flex gap-3">
                  <span className="text-lsc-rose dark:text-lsc-rose-light font-bold flex-shrink-0">3.</span>
                  <span className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('youthCommunityArchives.searchPrimarySourcesLikeCensus')}</span>
                </li>
                <li className="flex gap-3">
                  <span className="text-lsc-rose dark:text-lsc-rose-light font-bold flex-shrink-0">4.</span>
                  <span className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('youthCommunityArchives.connectWithOtherResearchersAnd')}</span>
                </li>
              </ul>
            </div>
          </div>
        )}
      </PageContainer>
    </div>
  )
}
