/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { BookOpen, Monitor, Map, Printer, Wrench, Users, Headphones, Search, Award, Baby, Palette, Shield, Boxes, Laptop, Library, Cpu } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

interface CourseThumbnailProps {
  title: string;
  thumbnailUrl?: string | null;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

interface ThemeMatch {
  icon: LucideIcon;
  from: string;
  to: string;
}

const THEME_KEYWORDS: [string[], ThemeMatch][] = [
  [['digital', 'internet', 'email', 'online'], { icon: Monitor, from: 'from-sky-400', to: 'to-blue-600' }],
  [['makerspace', 'maker'], { icon: Wrench, from: 'from-status-warning-400', to: 'to-orange-600' }],
  [['3d print', 'printer'], { icon: Printer, from: 'from-violet-400', to: 'to-category-600' }],
  [['laser', 'cnc', 'router'], { icon: Cpu, from: 'from-red-400', to: 'to-rose-600' }],
  [['tour', 'getting started', 'essentials', 'orientation'], { icon: Map, from: 'from-emerald-400', to: 'to-green-600' }],
  [['customer service', 'patron service', 'staff training'], { icon: Users, from: 'from-lsc-rose', to: 'to-blue-700' }],
  [['accessibility', 'a11y'], { icon: Headphones, from: 'from-teal-400', to: 'to-cyan-600' }],
  [['reference', 'research'], { icon: Search, from: 'from-slate-400', to: 'to-slate-700' }],
  [['catalog', 'classification'], { icon: Library, from: 'from-status-warning-500', to: 'to-yellow-700' }],
  [['children', 'youth'], { icon: Baby, from: 'from-pink-400', to: 'to-rose-500' }],
  [['reader', 'advisory', 'book'], { icon: BookOpen, from: 'from-orange-400', to: 'to-status-warning-600' }],
  [['visual', 'learning'], { icon: Palette, from: 'from-fuchsia-400', to: 'to-pink-600' }],
  [['assessment', 'quiz', 'interactive'], { icon: Award, from: 'from-lime-400', to: 'to-green-600' }],
  [['productivity', 'office'], { icon: Laptop, from: 'from-cyan-400', to: 'to-blue-500' }],
  [['advanced', 'marketing'], { icon: Shield, from: 'from-gray-500', to: 'to-gray-700' }],
];

function getTheme(title: string): ThemeMatch {
  const lower = title.toLowerCase();
  for (const [keywords, theme] of THEME_KEYWORDS) {
    if (keywords.some(k => lower.includes(k))) return theme;
  }
  // Fallback: deterministic color based on title hash
  const hash = [...title].reduce((h, c) => ((h << 5) - h + c.charCodeAt(0)) | 0, 0);
  const fallbacks: ThemeMatch[] = [
    { icon: BookOpen, from: 'from-orange-400', to: 'to-status-warning-600' },
    { icon: Boxes, from: 'from-lsc-rose', to: 'to-violet-600' },
    { icon: Monitor, from: 'from-teal-400', to: 'to-emerald-600' },
  ];
  return fallbacks[Math.abs(hash) % fallbacks.length]!;
}

const SIZES = {
  sm: { container: 'h-20', icon: 'w-8 h-8' },
  md: { container: 'h-36', icon: 'w-12 h-12' },
  lg: { container: 'h-48', icon: 'w-16 h-16' },
};

export default function CourseThumbnail({ title, thumbnailUrl, className = '', size = 'md' }: CourseThumbnailProps) {
  const s = SIZES[size];

  if (thumbnailUrl) {
    return (
      <div className={`${s.container} ${className} overflow-hidden`}>
        <img
          src={thumbnailUrl}
          alt={title}
          className="w-full h-full object-cover"
          loading="lazy"
        />
      </div>
    );
  }

  const theme = getTheme(title);
  const Icon = theme.icon;

  return (
    <div className={`${s.container} ${className} bg-gradient-to-br ${theme.from} ${theme.to} flex items-center justify-center relative overflow-hidden`}>
      {/* Subtle pattern overlay */}
      <div className="absolute inset-0 opacity-10" style={{
        backgroundImage: 'radial-gradient(circle at 20% 80%, white 1px, transparent 1px), radial-gradient(circle at 80% 20%, white 1px, transparent 1px)',
        backgroundSize: '30px 30px',
      }} />
      <Icon aria-hidden="true" className={`${s.icon} text-white/90 relative z-10 drop-shadow-sm`} />
    </div>
  );
}
