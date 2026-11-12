/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import React, { useState, useEffect } from 'react';
import { fetchApi } from '@/api/fetchApi';
import {
  Plus,
  Share2,
  Mail,
  Printer,
  Globe,
  CheckCircle,
  XCircle,
  Clock,
  AlertCircle,
  Eye,
  MousePointer,
} from 'lucide-react';
import PageContainer from '@/components/layout/PageContainer'

interface Campaign {
  id: number;
  event_id: number;
  campaign_name: string;
  channels: string[];
  archive_status: string;
  created_at: string;
  updated_at: string;
}

interface Distribution {
  id: number;
  channel: string;
  status: string;
  posted_at: string | null;
  impressions: number;
  clicks: number;
}

const EVENT_MARKETING_API = '/event-marketing';

// Consolidated status icon helper -- used by both CampaignDetail and DistributionStatus
const getStatusIcon = (status: string) => {
  if (status === 'posted') return <CheckCircle className="w-5 h-5 text-status-success-600 dark:text-status-success-400" />;
  if (status === 'failed') return <XCircle className="w-5 h-5 text-status-danger-600 dark:text-status-danger-400" />;
  if (status === 'scheduled') return <Clock className="w-5 h-5 text-status-warning-600 dark:text-status-warning-400" />;
  return <Clock className="w-5 h-5 text-earth-600 dark:text-earth-600" />;
};

export const EventMarketingDashboard: React.FC = () => {
  const [tabValue, setTabValue] = useState(0);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedCampaign, setSelectedCampaign] = useState<Campaign | null>(null);

  const loadCampaigns = async () => {
    setLoading(true);
    try {
      const data = await fetchApi(`${EVENT_MARKETING_API}/campaigns`);
      setCampaigns(data.data || []);
    } catch (error) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)));
    } finally {
      setLoading(false);
    }
  };


  useEffect(() => {
    loadCampaigns();
  }, []);

  const activeCampaigns = campaigns.filter(c => c.archive_status === 'active');
  const archivedCampaigns = campaigns.filter(c => c.archive_status !== 'active');

  const tabs = [
    { label: `Active Campaigns (${activeCampaigns.length})` },
    { label: `Archived (${archivedCampaigns.length})` },
  ];

  return (
    <PageContainer className="py-8">
      <div className="flex flex-col gap-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h1 className="font-serif text-2xl font-semibold text-lsc-dark dark:text-lsc-cream">
            Event Marketing Automation
          </h1>
          <a
            href="/staff/admin/events/new?marketing=true"
            className="inline-flex items-center gap-2 rounded-lg bg-lsc-rose px-4 py-2 text-sm font-medium text-white hover:bg-lsc-rose/90 dark:bg-lsc-rose-light dark:text-earth-900 dark:hover:bg-lsc-rose-light/90 transition-colors focus-ring"
          >
            <Plus className="w-4 h-4" />
            Create Campaign
          </a>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 border-b border-lsc-border dark:border-earth-700">
          {tabs.map((tab, idx) => (
            <button
              key={idx}
              onClick={() => setTabValue(idx)}
              className={`px-4 py-2.5 text-sm font-medium transition-colors focus-ring rounded-t-lg ${
                tabValue === idx
                  ? 'border-b-2 border-lsc-rose text-lsc-rose dark:border-lsc-rose-light dark:text-lsc-rose-light'
                  : 'text-earth-600 dark:text-earth-400 hover:text-lsc-dark dark:hover:text-lsc-cream'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        {tabValue === 0 && (
          <CampaignList
            campaigns={activeCampaigns}
            loading={loading}
            onSelectCampaign={setSelectedCampaign}
          />
        )}
        {tabValue === 1 && (
          <CampaignList
            campaigns={archivedCampaigns}
            loading={loading}
            onSelectCampaign={setSelectedCampaign}
          />
        )}

        {/* Campaign Detail */}
        {selectedCampaign && (
          <CampaignDetail
            campaign={selectedCampaign}
            onClose={() => setSelectedCampaign(null)}
            onRefresh={loadCampaigns}
          />
        )}
      </div>
    </PageContainer>
  );
};

interface CampaignListProps {
  campaigns: Campaign[];
  loading: boolean;
  onSelectCampaign: (campaign: Campaign) => void;
}

const CampaignList: React.FC<CampaignListProps> = ({
  campaigns,
  loading,
  onSelectCampaign,
}) => {
  if (loading) {
    return (
      <div className="w-full h-1 bg-earth-200 dark:bg-earth-700 rounded overflow-hidden">
        <div className="h-full w-1/3 bg-lsc-rose dark:bg-lsc-rose-light rounded motion-safe:animate-pulse" />
      </div>
    );
  }

  if (campaigns.length === 0) {
    return (
      <div className="flex items-center gap-3 rounded-lg border border-lsc-border dark:border-earth-700 bg-earth-50 dark:bg-earth-800/20 px-4 py-3 text-sm text-earth-800 dark:text-lsc-rose-light">
        <AlertCircle className="w-5 h-5 shrink-0" />
        No campaigns found. Create a new campaign to get started.
      </div>
    );
  }

  const getChannelIcon = (channel: string) => {
    const icons: { [key: string]: React.ReactNode } = {
      bluesky: <Globe className="w-4 h-4" />,
      mastodon: <Globe className="w-4 h-4" />,
      email: <Mail className="w-4 h-4" />,
      print_flyer: <Printer className="w-4 h-4" />,
    };
    return icons[channel] || <Share2 className="w-4 h-4" />;
  };

  return (
    <div className="rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 overflow-hidden shadow-soft-sm">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-earth-50 dark:bg-earth-900 border-b border-lsc-border dark:border-earth-700">
              <th className="px-4 py-3 text-left font-semibold text-lsc-dark dark:text-lsc-cream">Campaign Name</th>
              <th className="px-4 py-3 text-left font-semibold text-lsc-dark dark:text-lsc-cream">Event ID</th>
              <th className="px-4 py-3 text-left font-semibold text-lsc-dark dark:text-lsc-cream">Channels</th>
              <th className="px-4 py-3 text-left font-semibold text-lsc-dark dark:text-lsc-cream">Created</th>
              <th className="px-4 py-3 text-center font-semibold text-lsc-dark dark:text-lsc-cream">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
            {campaigns.map((campaign) => (
              <tr
                key={campaign.id}
                className="hover:bg-earth-50 dark:hover:bg-earth-700/50 transition-colors"
              >
                <td
                  className="px-4 py-3 font-medium text-lsc-dark dark:text-lsc-cream cursor-pointer hover:text-lsc-rose dark:hover:text-lsc-rose-light transition-colors"
                  onClick={() => onSelectCampaign(campaign)}
                >
                  {campaign.campaign_name}
                </td>
                <td className="px-4 py-3 text-earth-600 dark:text-earth-400">
                  #{campaign.event_id}
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2 flex-wrap text-earth-600 dark:text-earth-400">
                    {campaign.channels.map((ch) => (
                      <span key={ch} title={ch} className="inline-flex items-center">
                        {getChannelIcon(ch)}
                      </span>
                    ))}
                  </div>
                </td>
                <td className="px-4 py-3 text-earth-600 dark:text-earth-400">
                  {new Date(campaign.created_at).toLocaleDateString()}
                </td>
                <td className="px-4 py-3 text-center">
                  <button
                    title="View Details"
                    onClick={() => onSelectCampaign(campaign)}
                    className="inline-flex items-center rounded-lg px-3 py-1.5 text-sm font-medium text-lsc-rose dark:text-lsc-rose-light hover:bg-lsc-rose/10 dark:hover:bg-lsc-rose-light/10 transition-colors focus-ring"
                  >
                    Details
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

interface CampaignDetailProps {
  campaign: Campaign;
  onClose: () => void;
  onRefresh: () => void;
}

const CampaignDetail: React.FC<CampaignDetailProps> = ({
  campaign,
  onClose,
  onRefresh,
}) => {
  const [distributions, setDistributions] = useState<Distribution[]>([]);
  const [loading, setLoading] = useState(false);
  const [tabValue, setTabValue] = useState(0);

  const loadDistributions = async () => {
    setLoading(true);
    try {
      const data = await fetchApi(`${EVENT_MARKETING_API}/campaigns/${campaign.id}/distributions`);
      setDistributions(data.distributions || []);
    } catch (error) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)));
    } finally {
      setLoading(false);
    }
  };


  useEffect(() => {
    loadDistributions();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [campaign.id]);

  const handleDistribute = async () => {
    try {
      await fetchApi(`${EVENT_MARKETING_API}/campaigns/${campaign.id}/distribute`, {
        method: 'POST',
        body: JSON.stringify({ channels: campaign.channels }),
      });
      loadDistributions();
      onRefresh();
    } catch (error) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)));
    }
  };

  const handleGenerateFlyer = async () => {
    try {
      await fetchApi(`${EVENT_MARKETING_API}/campaigns/${campaign.id}/flyers`, {
        method: 'POST',
        body: JSON.stringify({ size: 'letter' }),
      });
      alert('Flyer generated successfully!');
    } catch (error) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)));
    }
  };

  const handleGenerateGraphics = async () => {
    try {
      await fetchApi(`${EVENT_MARKETING_API}/campaigns/${campaign.id}/graphics/generate-all`, {
        method: 'POST',
      });
      alert('All graphics generated successfully!');
    } catch (error) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)));
    }
  };

  const detailTabs = [
    { label: 'Distribution Status' },
    { label: 'Analytics' },
    { label: 'Feedback' },
  ];

  return (
    <div className="mt-6 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 p-6 shadow-soft-sm">
      <div className="flex flex-col gap-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
            {campaign.campaign_name}
          </h2>
          <button
            onClick={onClose}
            className="rounded-lg border border-lsc-border dark:border-earth-600 px-4 py-2 text-sm font-medium text-lsc-dark dark:text-lsc-cream hover:bg-earth-50 dark:hover:bg-earth-700 transition-colors focus-ring"
          >
            Close
          </button>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap gap-3">
          <button
            onClick={handleDistribute}
            className="inline-flex items-center gap-2 rounded-lg bg-lsc-rose px-4 py-2 text-sm font-medium text-white hover:bg-lsc-rose/90 dark:bg-lsc-rose-light dark:text-earth-900 dark:hover:bg-lsc-rose-light/90 transition-colors focus-ring"
          >
            <Share2 className="w-4 h-4" />
            Distribute Now
          </button>
          <button
            onClick={handleGenerateFlyer}
            className="inline-flex items-center gap-2 rounded-lg border border-lsc-border dark:border-earth-600 px-4 py-2 text-sm font-medium text-lsc-dark dark:text-lsc-cream hover:bg-earth-50 dark:hover:bg-earth-700 transition-colors focus-ring"
          >
            <Printer className="w-4 h-4" />
            Generate Flyer
          </button>
          <button
            onClick={handleGenerateGraphics}
            className="inline-flex items-center gap-2 rounded-lg border border-lsc-border dark:border-earth-600 px-4 py-2 text-sm font-medium text-lsc-dark dark:text-lsc-cream hover:bg-earth-50 dark:hover:bg-earth-700 transition-colors focus-ring"
          >
            <Share2 className="w-4 h-4" />
            Generate Graphics
          </button>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 border-b border-lsc-border dark:border-earth-700">
          {detailTabs.map((tab, idx) => (
            <button
              key={idx}
              onClick={() => setTabValue(idx)}
              className={`px-4 py-2.5 text-sm font-medium transition-colors focus-ring rounded-t-lg ${
                tabValue === idx
                  ? 'border-b-2 border-lsc-rose text-lsc-rose dark:border-lsc-rose-light dark:text-lsc-rose-light'
                  : 'text-earth-600 dark:text-earth-400 hover:text-lsc-dark dark:hover:text-lsc-cream'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        {tabValue === 0 && (
          <DistributionStatus
            distributions={distributions}
            loading={loading}
          />
        )}
        {tabValue === 1 && (
          <CampaignAnalytics campaignId={campaign.id} />
        )}
        {tabValue === 2 && (
          <FeedbackSummary campaignId={campaign.id} />
        )}
      </div>
    </div>
  );
};

interface DistributionStatusProps {
  distributions: Distribution[];
  loading: boolean;
}

const DistributionStatus: React.FC<DistributionStatusProps> = ({
  distributions,
  loading,
}) => {
  if (loading) {
    return (
      <div className="w-full h-1 bg-earth-200 dark:bg-earth-700 rounded overflow-hidden">
        <div className="h-full w-1/3 bg-lsc-rose dark:bg-lsc-rose-light rounded motion-safe:animate-pulse" />
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {distributions.map((dist) => (
        <div
          key={dist.id}
          className="rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 p-4 shadow-soft-sm"
        >
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2">
              {getStatusIcon(dist.status)}
              <span className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                {dist.channel}
              </span>
              <span
                className={`ml-auto inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                  dist.status === 'posted'
                    ? 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-800 dark:text-status-success-400'
                    : 'bg-earth-100 dark:bg-earth-700 text-earth-600 dark:text-earth-300'
                }`}
              >
                {dist.status}
              </span>
            </div>
            {dist.posted_at && (
              <span className="text-xs text-earth-600 dark:text-earth-400">
                Posted: {new Date(dist.posted_at).toLocaleString()}
              </span>
            )}
            <div className="flex items-center gap-4 mt-1">
              <span className="inline-flex items-center gap-1 text-xs text-earth-600 dark:text-earth-400">
                <Eye className="w-3.5 h-3.5" />
                {dist.impressions}
              </span>
              <span className="inline-flex items-center gap-1 text-xs text-earth-600 dark:text-earth-400">
                <MousePointer className="w-3.5 h-3.5" />
                {dist.clicks}
              </span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

interface CampaignAnalyticsProps {
  campaignId: number;
}

const CampaignAnalytics: React.FC<CampaignAnalyticsProps> = ({
  campaignId,
}) => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [analytics, setAnalytics] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const loadAnalytics = async () => {
    setLoading(true);
    try {
      const data = await fetchApi(`${EVENT_MARKETING_API}/campaigns/${campaignId}/analytics`);
      setAnalytics(data);
    } catch (error) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)));
    } finally {
      setLoading(false);
    }
  };


  useEffect(() => {
    loadAnalytics();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [campaignId]);

  if (loading || !analytics) {
    return (
      <div className="w-full h-1 bg-earth-200 dark:bg-earth-700 rounded overflow-hidden">
        <div className="h-full w-1/3 bg-lsc-rose dark:bg-lsc-rose-light rounded motion-safe:animate-pulse" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 p-4 text-center shadow-soft-sm">
          <div className="text-xl font-semibold text-lsc-dark dark:text-lsc-cream">
            {analytics.total_impressions}
          </div>
          <div className="text-xs text-earth-600 dark:text-earth-400 mt-1">
            Total Impressions
          </div>
        </div>
        <div className="rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 p-4 text-center shadow-soft-sm">
          <div className="text-xl font-semibold text-lsc-dark dark:text-lsc-cream">
            {analytics.total_clicks}
          </div>
          <div className="text-xs text-earth-600 dark:text-earth-400 mt-1">
            Total Clicks
          </div>
        </div>
        <div className="rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 p-4 text-center shadow-soft-sm">
          <div className="text-xl font-semibold text-lsc-dark dark:text-lsc-cream">
            {analytics.total_registrations}
          </div>
          <div className="text-xs text-earth-600 dark:text-earth-400 mt-1">
            Total Registrations
          </div>
        </div>
        <div className="rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 p-4 text-center shadow-soft-sm">
          <div className="text-xl font-semibold text-lsc-dark dark:text-lsc-cream">
            {analytics.successful_distributions}/{analytics.total_distributions}
          </div>
          <div className="text-xs text-earth-600 dark:text-earth-400 mt-1">
            Channels Posted
          </div>
        </div>
      </div>

      {/* Sources Table */}
      <div className="rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 p-4 shadow-soft-sm">
        <h3 className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-3">
          Registration Sources
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-lsc-border dark:border-earth-700">
                <th className="px-3 py-2 text-left font-semibold text-lsc-dark dark:text-lsc-cream">Source</th>
                <th className="px-3 py-2 text-right font-semibold text-lsc-dark dark:text-lsc-cream">Clicks</th>
                <th className="px-3 py-2 text-right font-semibold text-lsc-dark dark:text-lsc-cream">Conversions</th>
                <th className="px-3 py-2 text-right font-semibold text-lsc-dark dark:text-lsc-cream">Rate</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
              {analytics.sources.map((source: { source: string; total_clicks: number; total_conversions: number; conversion_rate: number }, idx: number) => (
                <tr key={idx} className="hover:bg-earth-50 dark:hover:bg-earth-700/50 transition-colors">
                  <td className="px-3 py-2 text-earth-600 dark:text-earth-400">{source.source}</td>
                  <td className="px-3 py-2 text-right text-earth-600 dark:text-earth-400">{source.total_clicks}</td>
                  <td className="px-3 py-2 text-right text-earth-600 dark:text-earth-400">{source.total_conversions}</td>
                  <td className="px-3 py-2 text-right text-earth-600 dark:text-earth-400">{source.conversion_rate}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

interface FeedbackSummaryProps {
  campaignId: number;
}

const FeedbackSummary: React.FC<FeedbackSummaryProps> = ({ campaignId }) => {
  const [summary, setSummary] = useState<{ total_responses: number; average_rating: number | null; would_attend_again_pct: number; would_recommend_pct: number; top_sources?: Array<{ source: string; count: number }>; recent_comments?: Array<{ rating: number; what_liked?: string; what_improve?: string }> } | null>(null);
  const [loading, setLoading] = useState(false);

  const loadFeedback = async () => {
    setLoading(true);
    try {
      const data = await fetchApi(`${EVENT_MARKETING_API}/campaigns/${campaignId}/feedback/summary`);
      setSummary(data);
    } catch (error) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)));
    } finally {
      setLoading(false);
    }
  };


  useEffect(() => {
    loadFeedback();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [campaignId]);

  if (loading || !summary) {
    return (
      <div className="w-full h-1 bg-earth-200 dark:bg-earth-700 rounded overflow-hidden">
        <div className="h-full w-1/3 bg-lsc-rose dark:bg-lsc-rose-light rounded motion-safe:animate-pulse" />
      </div>
    );
  }

  return (

    <div className="flex flex-col gap-4">
      {/* Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 p-4 text-center shadow-soft-sm">
          <div className="text-xl font-semibold text-lsc-dark dark:text-lsc-cream">
            {summary.total_responses}
          </div>
          <div className="text-xs text-earth-600 dark:text-earth-400 mt-1">
            Total Responses
          </div>
        </div>
        <div className="rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 p-4 text-center shadow-soft-sm">
          <div className="text-xl font-semibold text-lsc-dark dark:text-lsc-cream">
            {summary.average_rating?.toFixed(1) || 'N/A'} / 5
          </div>
          <div className="text-xs text-earth-600 dark:text-earth-400 mt-1">
            Average Rating
          </div>
        </div>
        <div className="rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 p-4 text-center shadow-soft-sm">
          <div className="text-xl font-semibold text-lsc-dark dark:text-lsc-cream">
            {summary.would_attend_again_pct || 0}%
          </div>
          <div className="text-xs text-earth-600 dark:text-earth-400 mt-1">
            Would Attend Again
          </div>
        </div>
        <div className="rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 p-4 text-center shadow-soft-sm">
          <div className="text-xl font-semibold text-lsc-dark dark:text-lsc-cream">
            {summary.would_recommend_pct || 0}%
          </div>
          <div className="text-xs text-earth-600 dark:text-earth-400 mt-1">
            Would Recommend
          </div>
        </div>
      </div>

      {/* Top Sources */}
      {(summary.top_sources?.length ?? 0) > 0 && (
        <div className="rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 p-4 shadow-soft-sm">
          <h3 className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-3">
            How They Heard About Event
          </h3>
          <div className="flex flex-wrap gap-2">
            {summary.top_sources!.map((source: { source: string; count: number }, idx: number) => (
              <span
                key={idx}
                className="inline-flex items-center rounded-full border border-lsc-border dark:border-earth-600 px-3 py-1 text-xs font-medium text-earth-600 dark:text-earth-400"
              >
                {source.source} ({source.count})
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Recent Comments */}
      {(summary.recent_comments?.length ?? 0) > 0 && (
        <div className="rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 p-4 shadow-soft-sm">
          <h3 className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-3">
            Recent Feedback
          </h3>
          <div className="flex flex-col divide-y divide-lsc-border dark:divide-earth-700">
            {summary.recent_comments!.map((comment: { rating: number; what_liked?: string; what_improve?: string }, idx: number) => (
              <div key={idx} className="py-3 first:pt-0 last:pb-0">
                <div className="flex items-center gap-1 mb-1">
                  <span className="text-xs text-status-warning-500">
                    {'★'.repeat(comment.rating)}{'☆'.repeat(5 - comment.rating)}
                  </span>
                </div>
                {comment.what_liked && (
                  <p className="text-xs text-earth-600 dark:text-earth-400">
                    <strong className="text-lsc-dark dark:text-lsc-cream">Liked:</strong> {comment.what_liked}
                  </p>
                )}
                {comment.what_improve && (
                  <p className="text-xs text-earth-600 dark:text-earth-400 mt-0.5">
                    <strong className="text-lsc-dark dark:text-lsc-cream">Improve:</strong> {comment.what_improve}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>

  );
};

export default EventMarketingDashboard;