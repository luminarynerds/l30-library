/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useEffect, useState } from "react";
import { API_BASE } from '@/api/types';
import {
  Heart, Target, Users, Sparkles, Calendar, Award,
  BookOpen, ArrowRight, Clock,
  Laptop, Building2, GraduationCap,
  Scale, Feather, Handshake, Coins, Accessibility
} from "lucide-react";
import api from "../api/api";
import { RichTextDisplay } from "../components/RichTextEditor";
import { getCurrentLocale } from '@/i18n'

interface TimelineEvent {
  year: number;
  title: string;
  description?: string;
  image_url?: string;
}

interface PublicGoal {
  id: number;
  title: string;
  description?: string;
  category?: string;
  progress: number;
  status: string;
}

interface PublicMilestone {
  id: number;
  title: string;
  celebration_text?: string;
  impact_story?: string;
  photo_url?: string;
  achieved_date?: string;
  milestone_type: string;
}

interface OurStoryData {
  has_plan: boolean;
  library_name: string;
  mission?: string;
  vision?: string;
  values: string[];
  story_intro?: string;
  hero_image_url?: string;
  history_timeline: TimelineEvent[];
  goals: PublicGoal[];
  milestones: PublicMilestone[];
  plan_period?: string;
}

// Matched by keyword *contained in* the value phrase (values are free text
// like "Equity of access"), so each card gets a fitting icon instead of all
// sharing the Heart fallback. Order matters: earlier keys win on a tie.
const valueIcons: Record<string, typeof Heart> = {
  equity: Scale,
  inclusion: Users,
  access: Accessibility,
  freedom: Feather,
  intellectual: Feather,
  privacy: Feather,
  community: Handshake,
  partnership: Handshake,
  collaboration: Handshake,
  learning: GraduationCap,
  education: GraduationCap,
  literacy: BookOpen,
  innovation: Sparkles,
  fiscal: Coins,
  stewardship: Coins,
  responsibility: Coins,
  excellence: Award,
  default: Heart,
};

function iconForValue(value: string): typeof Heart {
  const v = value.toLowerCase();
  const key = Object.keys(valueIcons).find((k) => k !== "default" && v.includes(k));
  return key ? valueIcons[key] ?? Heart : Heart;
}

const categoryColors: Record<string, string> = {
  "Community": "from-rose-500 to-pink-500",
  "Technology": "from-blue-500 to-cyan-500",
  "Collections": "from-lsc-rose to-orange-500",
  "Programs": "from-green-500 to-emerald-500",
  "Facilities": "from-category-500 to-violet-500",
  default: "from-earth-500 to-earth-600",
};

// Keyed by lowercase category so a goal shows an icon that fits its theme
// instead of every card sharing the same target. Falls back to Target.
const categoryIcons: Record<string, typeof Target> = {
  technology: Laptop,
  community: Users,
  programs: Calendar,
  facilities: Building2,
  staff: GraduationCap,
  collections: BookOpen,
  default: Target,
};

export default function AboutStoryContent() {
  const [data, setData] = useState<OurStoryData | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchStory = async () => {
    try {
      const res = await api.get(`${API_BASE}/strategic/our-story`);
      setData(res);
    } catch (_err) {
      Sentry.captureException(_err instanceof Error ? _err : new Error(String(_err)));
    } finally {
      setLoading(false);
    }
  };


  useEffect(() => {
    fetchStory();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-lsc-cream dark:bg-lsc-dark">
        <div className="container mx-auto py-16 px-4">
          <div className="motion-safe:animate-pulse space-y-8">
            <div className="h-64 bg-lsc-cream dark:bg-lsc-brown rounded-xl"></div>
            <div className="h-32 bg-lsc-cream dark:bg-lsc-brown rounded-xl"></div>
          </div>
        </div>
      </div>
    );
  }

  if (!data?.has_plan) {
    return (
      <div className="min-h-screen bg-lsc-cream dark:bg-lsc-dark">
        <div className="container mx-auto py-16 px-4 text-center">
          <BookOpen className="h-20 w-20 text-lsc-border mx-auto mb-6" />
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4">
            Our Story
          </h1>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-lg">
            The story of {data?.library_name || "our library"} is being written...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-lsc-cream dark:bg-lsc-dark">
      {/* Hero Section */}
      <div className="relative overflow-hidden">
        <div
          className="absolute inset-0 bg-cover bg-center"
          style={{
            backgroundImage: data.hero_image_url
              ? `url(${data.hero_image_url})`
              : "linear-gradient(135deg, #8B7B6A 0%, #5C4F3D 100%)"
          }}
        />
        <div className="absolute inset-0 bg-gradient-to-b from-black/60 via-black/40 to-black/70" />

        <div className="relative container mx-auto px-4 py-24 md:py-32">
          <div className="max-w-3xl">
            <h1 className="font-serif text-4xl md:text-5xl lg:text-6xl font-bold text-white mb-6">
              Our Story
            </h1>
            {data.story_intro && (
              <p className="text-xl md:text-2xl text-lsc-cream leading-relaxed">
                {data.story_intro}
              </p>
            )}
            {data.plan_period && (
              <div className="mt-8 inline-flex items-center gap-2 px-4 py-2 bg-lsc-white dark:bg-earth-800/10 backdrop-blur rounded-full text-lsc-dark dark:text-lsc-cream">
                <Calendar className="h-5 w-5" />
                <span>Strategic Plan {data.plan_period}</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Mission Section */}
      {data.mission && (
        <section className="py-16 bg-lsc-white dark:bg-earth-800">
          <div className="container mx-auto px-4">
            <div className="max-w-4xl mx-auto text-center">
              <div className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-cream dark:bg-lsc-dark/30 text-lsc-dark dark:text-lsc-rose rounded-full mb-6">
                <Target className="h-5 w-5" />
                <span className="font-medium">Our Mission</span>
              </div>
              <p className="text-2xl md:text-3xl text-lsc-dark dark:text-lsc-cream leading-relaxed font-serif italic">
                "{data.mission}"
              </p>
            </div>
          </div>
        </section>
      )}

      {/* Values Section */}
      {data.values && data.values.length > 0 && (
        <section className="py-16 bg-lsc-white dark:bg-earth-900">
          <div className="container mx-auto px-4">
            <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream text-center mb-12">
              Our Core Values
            </h2>
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-5xl mx-auto">
              {data.values.map((value, i) => {
                const IconComponent = iconForValue(value);
                return (
                  <div
                    key={i}
                    className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm hover:shadow-md transition-shadow"
                  >
                    <div className="w-12 h-12 bg-lsc-cream dark:bg-lsc-dark/30 rounded-xl flex items-center justify-center mb-4">
                      <IconComponent className="h-6 w-6 text-lsc-rose dark:text-lsc-rose" aria-hidden="true" />
                    </div>
                    <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
                      {value}
                    </h3>
                  </div>
                );
              })}
            </div>
          </div>
        </section>
      )}

      {/* Timeline Section */}
      {data.history_timeline && data.history_timeline.length > 0 && (
        <section className="py-16 bg-lsc-white dark:bg-earth-800">
          <div className="container mx-auto px-4">
            <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream text-center mb-4">
              Our Journey
            </h2>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-center mb-12 max-w-2xl mx-auto">
              From humble beginnings to a community cornerstone, explore the moments that shaped our library.
            </p>

            <div className="max-w-4xl mx-auto">
              <div className="relative">
                {/* Timeline line */}
                <div className="absolute left-8 md:left-1/2 top-0 bottom-0 w-0.5 bg-lsc-cream dark:bg-lsc-dark/50 transform md:-translate-x-1/2" />

                {data.history_timeline.map((event, i) => (
                  <div
                    key={i}
                    className={`relative flex items-start gap-6 mb-12 ${
                      i % 2 === 0 ? "md:flex-row" : "md:flex-row-reverse"
                    }`}
                  >
                    {/* Timeline dot */}
                    <div className="absolute left-8 md:left-1/2 w-4 h-4 bg-lsc-rose rounded-full border-4 border-white dark:border-earth-800 transform -translate-x-1/2 z-10" />

                    {/* Year badge */}
                    <div className={`hidden md:block w-1/2 ${i % 2 === 0 ? "text-right pr-12" : "text-left pl-12"}`}>
                      <span className="text-3xl font-bold text-lsc-rose dark:text-lsc-rose">
                        {event.year}
                      </span>
                    </div>

                    {/* Content card */}
                    <div className={`ml-16 md:ml-0 md:w-1/2 ${i % 2 === 0 ? "md:pl-12" : "md:pr-12"}`}>
                      <div className="bg-lsc-cream dark:bg-lsc-brown rounded-xl p-6 shadow-sm">
                        <span className="md:hidden text-2xl font-bold text-lsc-rose dark:text-lsc-rose block mb-2">
                          {event.year}
                        </span>
                        <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
                          {event.title}
                        </h3>
                        {event.description && (
                          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
                            {event.description}
                          </p>
                        )}
                        {event.image_url && (
                          <img
                            src={event.image_url}
                            alt={event.title}
                            className="mt-4 rounded-xl w-full h-48 object-cover"
                          />
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Goals Progress Section */}
      {data.goals && data.goals.length > 0 && (
        <section className="py-16 bg-lsc-white dark:bg-earth-900">
          <div className="container mx-auto px-4">
            <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream text-center mb-4">
              What We're Working On
            </h2>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-center mb-12 max-w-2xl mx-auto">
              Our strategic goals guide everything we do. Here's our progress toward building a better library for you.
            </p>

            <div className="grid md:grid-cols-2 gap-6 max-w-5xl mx-auto">
              {data.goals.map((goal) => {
                const colorClass = categoryColors[goal.category || ""] || categoryColors.default;
                const GoalIcon = categoryIcons[(goal.category || "").toLowerCase()] ?? Target;
                return (
                  <div
                    key={goal.id}
                    className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm hover:shadow-md transition-all"
                  >
                    <div className="flex items-start gap-4">
                      <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${colorClass} flex items-center justify-center shrink-0`}>
                        <GoalIcon className="h-6 w-6 text-white" aria-hidden="true" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-1">
                          {goal.title}
                        </h3>
                        {goal.description && (
                          <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3 line-clamp-2">
                            <RichTextDisplay content={goal.description} />
                          </div>
                        )}

                        {/* Progress bar */}
                        <div className="relative">
                          <div className="h-3 bg-lsc-cream dark:bg-lsc-brown rounded-full overflow-hidden">
                            <div
                              className={`h-full bg-gradient-to-r ${colorClass} transition-all duration-500`}
                              style={{ width: `${goal.progress}%` }}
                            />
                          </div>
                          <div className="flex justify-between mt-1">
                            <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                              {goal.status === "completed" ? "Complete!" : `${goal.progress}% progress`}
                            </span>
                            {goal.category && (
                              <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                                {goal.category}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </section>
      )}

      {/* Milestones/Achievements Section */}
      {data.milestones && data.milestones.length > 0 && (
        <section className="py-16 bg-lsc-white dark:bg-earth-800">
          <div className="container mx-auto px-4">
            <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream text-center mb-4">
              Celebrating Our Achievements
            </h2>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-center mb-12 max-w-2xl mx-auto">
              Every milestone is made possible by our community. Here are some moments we're proud of.
            </p>

            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto">
              {data.milestones.map((milestone) => (
                <div
                  key={milestone.id}
                  className="bg-gradient-to-br from-status-warning-50 to-cream-100 dark:from-lsc-dark/20 dark:to-earth-700 rounded-xl p-6 shadow-sm hover:shadow-md transition-all border border-earth-100 dark:border-earth-900/30"
                >
                  {milestone.photo_url && (
                    <img
                      src={milestone.photo_url}
                      alt={milestone.title}
                      className="w-full h-40 object-cover rounded-xl mb-4"
                    />
                  )}

                  <div className="flex items-center gap-2 mb-3">
                    <Award className="h-5 w-5 text-lsc-rose dark:text-lsc-rose" />
                    <span className="text-xs uppercase tracking-wider text-lsc-rose dark:text-lsc-rose font-medium">
                      {milestone.milestone_type}
                    </span>
                  </div>

                  <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
                    {milestone.title}
                  </h3>

                  {milestone.celebration_text && (
                    <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
                      {milestone.celebration_text}
                    </p>
                  )}

                  {milestone.impact_story && (
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 italic">
                      {milestone.impact_story}
                    </p>
                  )}

                  {milestone.achieved_date && (
                    <div className="mt-4 pt-4 border-t border-lsc-border dark:border-earth-900/30 flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      <Clock className="h-4 w-4" />
                      {new Date(milestone.achieved_date).toLocaleDateString(getCurrentLocale(), {
                        month: "long",
                        year: "numeric"
                      })}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* Vision Section */}
      {data.vision && (
        <section className="py-20 bg-gradient-to-br from-earth-800 to-lsc-dark">
          <div className="container mx-auto px-4">
            <div className="max-w-4xl mx-auto text-center">
              <div className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-white dark:bg-earth-800/10 text-lsc-dark/70 dark:text-lsc-cream/70 rounded-full mb-6">
                <Sparkles className="h-5 w-5" />
                <span className="font-medium">Our Vision</span>
              </div>
              <h2 className="font-serif text-3xl md:text-4xl font-bold text-white mb-6">
                Where We're Going
              </h2>
              <p className="text-xl md:text-2xl text-lsc-cream/70 leading-relaxed font-serif italic">
                {(() => {
                  const v = data.vision ?? "";
                  const parts = v.split(" -- ");
                  return parts.length === 2 ? (
                    <>"{parts[0]} --<br />{parts[1]}"</>
                  ) : (
                    <>"{v}"</>
                  );
                })()}
              </p>
              <div className="mt-10">
                <a
                  href="/contact"
                  className="inline-flex items-center gap-2 px-8 py-4 bg-lsc-rose hover:bg-lsc-rose text-white rounded-xl font-semibold transition-colors"
                >
                  Join Our Journey
                  <ArrowRight className="h-5 w-5" />
                </a>
              </div>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}