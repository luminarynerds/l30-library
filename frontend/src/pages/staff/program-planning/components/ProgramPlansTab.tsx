/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getPlanByProgram } from '@/api/program-planning-api'
import {
  FileText, DollarSign, Users, Search, ClipboardCheck, Loader2,
} from 'lucide-react'
import InfoCard from './InfoCard'
import FormSection from './FormSection'
import StatusBadge from './StatusBadge'

function ProgramPlansTab() {
  const [programIdInput, setProgramIdInput] = useState('')
  const [lookupId, setLookupId] = useState<number | null>(null)

  const { data: plan, isLoading, isError, error } = useQuery({
    queryKey: ['program-plan-by-program', lookupId],
    queryFn: () => getPlanByProgram(lookupId!),
    enabled: lookupId !== null,
    retry: false,
  })

  const handleLookup = (e: React.FormEvent) => {
    e.preventDefault()
    const id = parseInt(programIdInput)
    if (id > 0) setLookupId(id)
  }

  const remaining = plan ? plan.total_budget - plan.total_spent : 0

  return (
    <div>
      {/* Lookup Bar */}
      <form onSubmit={handleLookup} className="flex items-end gap-3 mb-6">
        <div className="flex-1 max-w-xs">
          <label htmlFor="plan-lookup-program" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
            Program ID
          </label>
          <input
            id="plan-lookup-program"
            type="number"
            min={1}
            value={programIdInput}
            onChange={e => setProgramIdInput(e.target.value)}
            placeholder="Enter program ID"
            className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
          />
        </div>
        <button
          type="submit"
          disabled={!programIdInput || isLoading}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-earth-600 text-white hover:bg-earth-700 disabled:opacity-50 transition-colors"
        >
          {isLoading ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <Search className="w-4 h-4" />}
          Look Up
        </button>
      </form>

      <div aria-live="polite">
      {/* Loading */}
      {isLoading && (
        <div className="flex justify-center py-12">
          <Loader2 className="w-8 h-8 motion-safe:animate-spin text-earth-600 dark:text-earth-200" />
        </div>
      )}

      {/* Error */}
      {isError && (
        <div className="text-center py-12 bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700">
          <FileText className="w-12 h-12 text-lsc-dark/30 dark:text-lsc-cream/60 mx-auto mb-3" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            {(error as Error)?.message?.includes('404') || (error as Error)?.message?.includes('not found')
              ? `No plan found for program #${lookupId}`
              : 'Failed to load plan. Check the program ID and try again.'}
          </p>
        </div>
      )}

      {/* No lookup yet */}
      {!lookupId && !isLoading && (
        <div className="text-center py-12 bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700">
          <FileText className="w-12 h-12 text-lsc-dark/30 dark:text-lsc-cream/60 mx-auto mb-3" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">Enter a program ID to view its plan details.</p>
        </div>
      )}
      </div>

      {/* Plan Data */}
      {plan && !isLoading && (
        <div className="space-y-6">
          {/* Plan Header Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <InfoCard icon={DollarSign} label="Total Budget" value={`$${plan.total_budget.toFixed(2)}`} />
            <InfoCard icon={DollarSign} label="Total Spent" value={`$${plan.total_spent.toFixed(2)}`} />
            <InfoCard icon={DollarSign} label="Remaining" value={`$${remaining.toFixed(2)}`} />
            <div className="bg-earth-50 dark:bg-earth-700 rounded-lg p-3">
              <div className="flex items-center gap-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                <ClipboardCheck className="w-3 h-3" />
                Planning Status
              </div>
              <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                plan.planning_complete
                  ? 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900 dark:text-status-success-200'
                  : 'bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900 dark:text-status-warning-200'
              }`}>
                {plan.planning_complete ? 'Complete' : 'In Progress'}
              </span>
            </div>
          </div>

          {/* Planning Notes */}
          {plan.planning_notes && (
            <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-4">
              <h3 className="text-sm font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase mb-1">Planning Notes</h3>
              <p className="text-sm text-lsc-dark dark:text-lsc-cream whitespace-pre-wrap">{plan.planning_notes}</p>
            </div>
          )}

          {/* Budget Items */}
          <FormSection title={`Budget Items (${plan.budget_items.length})`} defaultOpen={plan.budget_items.length > 0}>
            {plan.budget_items.length === 0 ? (
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">No budget items.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-lsc-border dark:border-earth-700">
                      <th className="text-left p-2 text-lsc-dark/70 dark:text-lsc-cream/70 font-medium">Description</th>
                      <th className="text-left p-2 text-lsc-dark/70 dark:text-lsc-cream/70 font-medium">Category</th>
                      <th className="text-right p-2 text-lsc-dark/70 dark:text-lsc-cream/70 font-medium">Estimated</th>
                      <th className="text-right p-2 text-lsc-dark/70 dark:text-lsc-cream/70 font-medium">Actual</th>
                      <th className="text-center p-2 text-lsc-dark/70 dark:text-lsc-cream/70 font-medium">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {plan.budget_items.map(item => (
                      <tr key={item.id} className="border-b border-earth-100 dark:border-earth-700 last:border-0">
                        <td className="p-2 text-lsc-dark dark:text-lsc-cream">{item.description}</td>
                        <td className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70">{item.category}</td>
                        <td className="p-2 text-right text-lsc-dark dark:text-lsc-cream">${item.estimated_amount.toFixed(2)}</td>
                        <td className="p-2 text-right text-lsc-dark/70 dark:text-lsc-cream/70">
                          {item.actual_amount != null ? `$${item.actual_amount.toFixed(2)}` : '---'}
                        </td>
                        <td className="p-2 text-center">
                          {item.is_paid
                            ? <StatusBadge status="paid" />
                            : <StatusBadge status="pending" />}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </FormSection>

          {/* Supply Checklist */}
          <FormSection title={`Supply Checklist (${plan.supply_items.length})`} defaultOpen={plan.supply_items.length > 0}>
            {plan.supply_items.length === 0 ? (
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">No supply items.</p>
            ) : (
              <div className="space-y-2">
                {plan.supply_items.map(item => (
                  <div key={item.id} className="flex items-center justify-between py-2 px-3 bg-earth-50 dark:bg-earth-700 rounded">
                    <div className="flex-1 min-w-0">
                      <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">{item.item_name}</span>
                      <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 ml-2">
                        {item.quantity_on_hand}/{item.quantity_needed} {item.unit ?? 'units'}
                      </span>
                      {item.vendor && (
                        <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 ml-2">
                          ({item.vendor})
                        </span>
                      )}
                    </div>
                    <StatusBadge status={item.status} />
                  </div>
                ))}
              </div>
            )}
          </FormSection>

          {/* Volunteers */}
          <FormSection title={`Volunteers (${plan.volunteer_assignments.length})`} defaultOpen={plan.volunteer_assignments.length > 0}>
            {plan.volunteer_assignments.length === 0 ? (
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">No volunteer assignments.</p>
            ) : (
              <div className="space-y-2">
                {plan.volunteer_assignments.map(v => (
                  <div key={v.id} className="flex items-center justify-between py-2 px-3 bg-earth-50 dark:bg-earth-700 rounded">
                    <div className="flex-1 min-w-0">
                      <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">{v.role}</span>
                      {v.hours_worked != null && (
                        <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 ml-2">
                          {v.hours_worked}h worked
                        </span>
                      )}
                    </div>
                    <StatusBadge status={v.status} />
                  </div>
                ))}
              </div>
            )}
          </FormSection>

          {/* Room & Equipment */}
          <FormSection
            title={`Room & Equipment (${plan.room_bookings.length + plan.equipment_bookings.length})`}
            defaultOpen={plan.room_bookings.length + plan.equipment_bookings.length > 0}
          >
            {plan.room_bookings.length === 0 && plan.equipment_bookings.length === 0 ? (
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">No room or equipment bookings.</p>
            ) : (
              <div className="space-y-3">
                {plan.room_bookings.length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/60 uppercase mb-2">Rooms</h4>
                    <div className="space-y-2">
                      {plan.room_bookings.map(r => (
                        <div key={r.id} className="flex items-center justify-between py-2 px-3 bg-earth-50 dark:bg-earth-700 rounded">
                          <div className="flex-1 min-w-0">
                            <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                              Room {r.room_id ?? 'TBD'}
                            </span>
                            {(r.setup_time_minutes || r.teardown_time_minutes) && (
                              <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 ml-2">
                                {r.setup_time_minutes ? `${r.setup_time_minutes}m setup` : ''}
                                {r.setup_time_minutes && r.teardown_time_minutes ? ' / ' : ''}
                                {r.teardown_time_minutes ? `${r.teardown_time_minutes}m teardown` : ''}
                              </span>
                            )}
                          </div>
                          <StatusBadge status={r.status} />
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {plan.equipment_bookings.length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/60 uppercase mb-2">Equipment</h4>
                    <div className="space-y-2">
                      {plan.equipment_bookings.map(eq => (
                        <div key={eq.id} className="flex items-center justify-between py-2 px-3 bg-earth-50 dark:bg-earth-700 rounded">
                          <div className="flex-1 min-w-0">
                            <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                              {eq.equipment_type_requested}
                            </span>
                            <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 ml-2">
                              x{eq.quantity}
                            </span>
                          </div>
                          <StatusBadge status={eq.status} />
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </FormSection>

          {/* Marketing Milestones */}
          <FormSection title={`Marketing Milestones (${plan.marketing_milestones.length})`} defaultOpen={plan.marketing_milestones.length > 0}>
            {plan.marketing_milestones.length === 0 ? (
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">No marketing milestones.</p>
            ) : (
              <div className="space-y-2">
                {plan.marketing_milestones.map(m => (
                  <div key={m.id} className="flex items-center justify-between py-2 px-3 bg-earth-50 dark:bg-earth-700 rounded">
                    <div className="flex-1 min-w-0">
                      <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">{m.description}</span>
                      <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 ml-2">
                        {m.milestone_type.replace(/_/g, ' ')}
                      </span>
                      <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 ml-2">
                        Due: {new Date(m.due_date).toLocaleDateString()}
                      </span>
                    </div>
                    {m.completed
                      ? <StatusBadge status="completed" />
                      : new Date(m.due_date) <= new Date()
                        ? <StatusBadge status="overdue" />
                        : <StatusBadge status="pending" />}
                  </div>
                ))}
              </div>
            )}
          </FormSection>

          {/* Evaluation */}
          <FormSection title="Evaluation" defaultOpen={plan.evaluation !== null}>
            {!plan.evaluation ? (
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">No evaluation yet.</p>
            ) : (
              <div className="space-y-4">
                {/* Ratings */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {[
                    { label: 'Overall', value: plan.evaluation.overall_rating },
                    { label: 'Content', value: plan.evaluation.content_quality_rating },
                    { label: 'Logistics', value: plan.evaluation.logistics_rating },
                    { label: 'Engagement', value: plan.evaluation.engagement_rating },
                  ].map(r => (
                    <div key={r.label} className="bg-earth-50 dark:bg-earth-700 rounded-lg p-3">
                      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">{r.label}</p>
                      {r.value ? (
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                          r.value === 'excellent' ? 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900 dark:text-status-success-200' :
                          r.value === 'good' ? 'bg-earth-100 text-lsc-rose dark:bg-earth-800 dark:text-lsc-rose-light/80' :
                          r.value === 'fair' ? 'bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900 dark:text-status-warning-200' :
                          'bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900 dark:text-status-danger-200'
                        }`}>{r.value}</span>
                      ) : (
                        <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">---</span>
                      )}
                    </div>
                  ))}
                </div>

                {/* Attendance */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <InfoCard icon={Users} label="Expected" value={plan.evaluation.expected_attendance?.toString() ?? '---'} />
                  <InfoCard icon={Users} label="Actual" value={plan.evaluation.actual_attendance?.toString() ?? '---'} />
                  <InfoCard icon={Users} label="New Patrons" value={plan.evaluation.new_patron_count?.toString() ?? '---'} />
                  <InfoCard icon={Users} label="Repeats" value={plan.evaluation.repeat_attendee_count?.toString() ?? '---'} />
                </div>

                {/* Budget Variance */}
                {plan.evaluation.budget_variance != null && (
                  <div className="bg-earth-50 dark:bg-earth-700 rounded-lg p-3">
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Budget Variance</p>
                    <p className={`text-sm font-medium ${
                      plan.evaluation.budget_variance > 0 ? 'text-status-danger-700 dark:text-status-danger-300' :
                      plan.evaluation.budget_variance < 0 ? 'text-status-success-700 dark:text-status-success-300' :
                      'text-lsc-dark dark:text-lsc-cream'
                    }`}>
                      {plan.evaluation.budget_variance > 0 ? '+' : ''}${plan.evaluation.budget_variance.toFixed(2)}
                      {plan.evaluation.budget_variance > 0 ? ' over budget' : plan.evaluation.budget_variance < 0 ? ' under budget' : ' on budget'}
                    </p>
                  </div>
                )}

                {/* Qualitative Notes */}
                <div className="space-y-3">
                  {plan.evaluation.what_went_well && (
                    <div>
                      <h4 className="text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/60 uppercase mb-1">What Went Well</h4>
                      <p className="text-sm text-lsc-dark dark:text-lsc-cream whitespace-pre-wrap">{plan.evaluation.what_went_well}</p>
                    </div>
                  )}
                  {plan.evaluation.what_to_improve && (
                    <div>
                      <h4 className="text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/60 uppercase mb-1">What to Improve</h4>
                      <p className="text-sm text-lsc-dark dark:text-lsc-cream whitespace-pre-wrap">{plan.evaluation.what_to_improve}</p>
                    </div>
                  )}
                  {plan.evaluation.staff_notes && (
                    <div>
                      <h4 className="text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/60 uppercase mb-1">Staff Notes</h4>
                      <p className="text-sm text-lsc-dark dark:text-lsc-cream whitespace-pre-wrap">{plan.evaluation.staff_notes}</p>
                    </div>
                  )}
                  {plan.evaluation.attendee_feedback_summary && (
                    <div>
                      <h4 className="text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/60 uppercase mb-1">Attendee Feedback</h4>
                      <p className="text-sm text-lsc-dark dark:text-lsc-cream whitespace-pre-wrap">{plan.evaluation.attendee_feedback_summary}</p>
                    </div>
                  )}
                </div>

                {/* Repeat Recommendation */}
                {plan.evaluation.recommend_repeat != null && (
                  <div className="flex items-center gap-2 bg-earth-50 dark:bg-earth-700 rounded-lg p-3">
                    <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Recommend Repeat:</span>
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                      plan.evaluation.recommend_repeat
                        ? 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900 dark:text-status-success-200'
                        : 'bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900 dark:text-status-danger-200'
                    }`}>
                      {plan.evaluation.recommend_repeat ? 'Yes' : 'No'}
                    </span>
                    {plan.evaluation.recommended_changes && (
                      <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 ml-2">
                        -- {plan.evaluation.recommended_changes}
                      </span>
                    )}
                  </div>
                )}
              </div>
            )}
          </FormSection>
        </div>
      )}
    </div>
  )
}

export default ProgramPlansTab
