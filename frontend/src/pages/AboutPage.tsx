/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { lazy, Suspense } from 'react';
import { useSearchParams } from 'react-router-dom';
import { usePageTitle } from '@/hooks/usePageTitle';

const AboutLibraryContent = lazy(() => import('./AboutLibraryContent'));
const AboutStoryContent = lazy(() => import('./AboutStoryContent'));
const AboutApproachContent = lazy(() => import('./AboutApproachContent'));
const AboutStatsContent = lazy(() => import('./AboutStatsContent'));

type TabSlug = 'library' | 'story' | 'approach' | 'stats';

const TABS: { slug: TabSlug; label: string }[] = [
  { slug: 'library', label: 'Our Library' },
  { slug: 'story', label: 'Our Story' },
  { slug: 'approach', label: 'Is This Real?' },
  { slug: 'stats', label: 'By the Numbers' },
];

function LoadingSpinner() {
  return (
    <div className="flex justify-center py-16">
      <div className="w-8 h-8 border-2 border-lsc-rose border-t-transparent rounded-full animate-spin" />
    </div>
  );
}

export default function AboutPage(): React.ReactElement {
  const [searchParams, setSearchParams] = useSearchParams();
  const rawTab = searchParams.get('tab') || 'library';
  const activeTab: TabSlug = TABS.some(t => t.slug === rawTab) ? (rawTab as TabSlug) : 'library';

  const titles: Record<TabSlug, string> = {
    library: 'About Us',
    story: 'Our Story',
    approach: 'Is This Real?',
    stats: 'By the Numbers',
  };
  usePageTitle(titles[activeTab]);

  const handleTabChange = (slug: TabSlug) => {
    if (slug === 'library') {
      setSearchParams({});
    } else {
      setSearchParams({ tab: slug });
    }
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="min-h-screen bg-lsc-cream dark:bg-lsc-dark">
      {/* Tab Bar */}
      <div className="sticky top-0 z-20 bg-lsc-cream/95 dark:bg-lsc-dark/95 backdrop-blur border-b border-lsc-border dark:border-earth-700">
        <div className="container mx-auto px-4">
          <nav className="flex overflow-x-auto gap-1 py-3 -mx-1 px-1" aria-label="About page sections">
            {TABS.map(({ slug, label }) => (
              <button
                key={slug}
                onClick={() => handleTabChange(slug)}
                className={`px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors ${
                  activeTab === slug
                    ? 'bg-lsc-rose text-white'
                    : 'text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-100 dark:hover:bg-earth-700'
                }`}
              >
                {label}
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* Tab Content */}
      <div className="pt-6 md:pt-8">
      <Suspense fallback={<LoadingSpinner />}>
        {activeTab === 'library' && <AboutLibraryContent />}
        {activeTab === 'story' && <AboutStoryContent />}
        {activeTab === 'approach' && <AboutApproachContent />}
        {activeTab === 'stats' && <AboutStatsContent />}
      </Suspense>
      </div>
    </div>
  );
}
