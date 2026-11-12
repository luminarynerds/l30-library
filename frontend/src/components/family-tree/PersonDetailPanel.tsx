/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react';
import { Plus, X, Edit3, Trash2, Clock, ChevronDown, ChevronUp, Loader } from 'lucide-react';
import type { Person, TimelineEvent } from '@/api/genealogy-research-api';

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[10px] font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wide">{label}</p>
      <p className="text-sm text-earth-800 dark:text-earth-200 capitalize">{value}</p>
    </div>
  );
}

interface PersonDetailPanelProps {
  person: Person;
  timeline: TimelineEvent[];
  timelineLoading: boolean;
  projectId: number;
  onEdit: () => void;
  onDelete: () => void;
  onClose: () => void;
  onAddEvent: () => void;
  onTimelineRefresh: () => void;
}

export function PersonDetailPanel({
  person,
  timeline,
  timelineLoading,
  onEdit,
  onDelete,
  onClose,
  onAddEvent,
}: PersonDetailPanelProps) {
  const [showTimeline, setShowTimeline] = useState(true);

  const eventColors: Record<string, string> = {
    birth: 'bg-status-success-500',
    death: 'bg-earth-500',
    marriage: 'bg-sky-500',
    immigration: 'bg-earth-500',
    military_service: 'bg-status-danger-500',
    education: 'bg-category-500',
    occupation: 'bg-status-warning-500',
    residence: 'bg-teal-500',
    other: 'bg-earth-400',
  };

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden">
      <div className="px-4 py-3 border-b border-lsc-border dark:border-earth-700 flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
            {person.given_names} {person.surname || ''}
          </h3>
          {person.maiden_name && (
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">née {person.maiden_name}</p>
          )}
        </div>
        <div className="flex gap-1 flex-shrink-0">
          <button onClick={onEdit} className="p-1.5 text-earth-600 hover:bg-earth-50 dark:bg-earth-800/20 dark:hover:bg-earth-800/20 rounded" title="Edit">
            <Edit3 className="w-4 h-4" />
          </button>
          <button onClick={onDelete} className="p-1.5 text-status-danger-500 hover:bg-status-danger-50 dark:bg-status-danger-900/20 dark:hover:bg-status-danger-900/20 rounded" title="Delete">
            <Trash2 className="w-4 h-4" />
          </button>
          <button onClick={onClose} className="p-1.5 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-700 rounded" title="Close">
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="p-4 space-y-3">
        <div className="grid grid-cols-2 gap-3 text-sm">
          {(() => {
            const genderMap: Record<string, string> = {
              male: 'Male',
              female: 'Female',
              nonbinary: 'Nonbinary',
              other: 'Another gender / not listed',
              unknown: 'Not recorded',
              '': 'Not recorded',
            };
            const display = genderMap[person.gender ?? ''] ?? person.gender;
            return display ? <DetailRow label="Gender" value={display} /> : null;
          })()}
          {person.birth_date && (
            <DetailRow label="Born" value={`${person.birth_date}${person.birth_place ? `, ${person.birth_place}` : ''}`} />
          )}
          {!person.is_living && person.death_date && (
            <DetailRow label="Died" value={`${person.death_date}${person.death_place ? `, ${person.death_place}` : ''}`} />
          )}
          {person.is_living && (
            <DetailRow label="Status" value="Living" />
          )}
          {person.occupation && (
            <DetailRow label="Occupation" value={person.occupation} />
          )}
          {person.nationality && (
            <DetailRow label="Nationality" value={person.nationality} />
          )}
        </div>

        {person.biography && (
          <div className="mt-2">
            <p className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Biography</p>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 leading-relaxed">{person.biography}</p>
          </div>
        )}

        <div>
          <p className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Data Confidence</p>
          <div className="flex items-center gap-2">
            <div className="flex-1 h-1.5 bg-earth-200 dark:bg-earth-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-status-warning-500 rounded-full"
                style={{ width: `${(person.confidence_level / 5) * 100}%` }}
              />
            </div>
            <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{person.confidence_level}/5</span>
          </div>
        </div>
      </div>

      <div className="border-t border-lsc-border dark:border-earth-700">
        <button
          onClick={() => setShowTimeline(!showTimeline)}
          className="w-full px-4 py-3 flex items-center justify-between text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-700/50"
        >
          <span className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-status-warning-500" />
            Timeline Events ({timeline.length})
          </span>
          {showTimeline ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>

        {showTimeline && (
          <div className="px-4 pb-4">
            {timelineLoading ? (
              <Loader className="w-4 h-4 motion-safe:animate-spin text-lsc-dark/70 dark:text-lsc-cream/70 mx-auto my-4" />
            ) : timeline.length === 0 ? (
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 italic text-center py-2">No events yet</p>
            ) : (
              <div className="space-y-2 mb-3">
                {timeline.map(event => (
                  <div key={event.id} className="flex gap-2.5 items-start">
                    <div className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${eventColors[event.event_type] || eventColors.other}`} />
                    <div>
                      <p className="text-xs font-medium text-earth-800 dark:text-earth-200">{event.title}</p>
                      <p className="text-[10px] text-lsc-dark/70 dark:text-lsc-cream/70">
                        {event.event_date || 'Unknown date'}
                        {event.location ? ` · ${event.location}` : ''}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
            <button
              onClick={onAddEvent}
              className="flex items-center gap-1.5 text-xs text-status-warning-600 hover:text-status-warning-700 dark:text-status-warning-300 font-medium"
            >
              <Plus className="w-3 h-3" />
              Add Event
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
