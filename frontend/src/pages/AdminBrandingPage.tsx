/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import { Building2, Save, RefreshCw, Mail, MapPin, Palette, Globe, Accessibility, BookOpen, Plus, Trash2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { AdminShell } from '../components/shells/AdminShell'
import { useBrandingContext, type Branding, type AboutStoryEvent } from '../contexts/BrandingContext'
import api from '@/lib/api-client'

type EditableKey =
  | 'library_name' | 'library_short_name' | 'tagline' | 'domain'
  | 'contact_email' | 'privacy_email' | 'indie_email' | 'giving_email'
  | 'events_email' | 'print_email' | 'makerspace_email'
  | 'phone' | 'address_line1' | 'address_line2' | 'city' | 'state' | 'zip_code'
  | 'primary_color' | 'accent_color'
  | 'hero_title' | 'hero_subtitle'
  | 'bluesky_url' | 'mastodon_url'
  | 'quiet_hours' | 'sensory_friendly_times' | 'low_stim_seating'

const EDITABLE_KEYS: EditableKey[] = [
  'library_name', 'library_short_name', 'tagline', 'domain',
  'contact_email', 'privacy_email', 'indie_email', 'giving_email',
  'events_email', 'print_email', 'makerspace_email',
  'phone', 'address_line1', 'address_line2', 'city', 'state', 'zip_code',
  'primary_color', 'accent_color',
  'hero_title', 'hero_subtitle',
  'bluesky_url', 'mastodon_url',
  'quiet_hours', 'sensory_friendly_times', 'low_stim_seating',
]

type FormState = Pick<Branding, EditableKey>

function pickEditable(b: Branding): FormState {
  const out = {} as FormState
  for (const k of EDITABLE_KEYS) out[k] = b[k] ?? ''
  return out
}

function Field({
  label, value, onChange, type = 'text', placeholder, helper,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  type?: string
  placeholder?: string
  helper?: string
}) {
  return (
    <label className="block">
      <span className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">{label}</span>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose/50"
      />
      {helper && (
        <span className="block mt-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/60">{helper}</span>
      )}
    </label>
  )
}

function Section({
  title, icon: Icon, children,
}: { title: string; icon: React.ElementType; children: React.ReactNode }) {
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm p-6 space-y-4 border border-lsc-border dark:border-earth-700">
      <div className="flex items-center gap-2 mb-2">
        <Icon className="w-5 h-5 text-lsc-rose" />
        <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">{title}</h2>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">{children}</div>
    </div>
  )
}

export default function AdminBrandingPage() {
  const { branding, loading: contextLoading, refetch } = useBrandingContext()
  const [form, setForm] = useState<FormState>(() => pickEditable(branding))
  const [timeline, setTimeline] = useState<AboutStoryEvent[]>(
    () => branding.about_story?.timeline ?? []
  )
  const [storyIntro, setStoryIntro] = useState(
    () => (branding.about_story?.intro ?? []).join('\n\n')
  )
  const noteModeOf = (story: typeof branding.about_story): 'stock' | 'custom' | 'hidden' =>
    story?.hide_director_note ? 'hidden' : story?.director_note?.paragraphs?.length ? 'custom' : 'stock'
  const [noteMode, setNoteMode] = useState<'stock' | 'custom' | 'hidden'>(
    () => noteModeOf(branding.about_story)
  )
  const [noteText, setNoteText] = useState(
    () => (branding.about_story?.director_note?.paragraphs ?? []).join('\n\n')
  )
  const [noteSignature, setNoteSignature] = useState(
    () => branding.about_story?.director_note?.signature ?? ''
  )
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!contextLoading) {
      setForm(pickEditable(branding))
      setTimeline(branding.about_story?.timeline ?? [])
      setStoryIntro((branding.about_story?.intro ?? []).join('\n\n'))
      setNoteMode(noteModeOf(branding.about_story))
      setNoteText((branding.about_story?.director_note?.paragraphs ?? []).join('\n\n'))
      setNoteSignature(branding.about_story?.director_note?.signature ?? '')
    }
    // noteModeOf is a pure helper; listing it would re-run the effect for nothing.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [contextLoading, branding])

  const update = (k: EditableKey) => (v: string) => setForm((prev) => ({ ...prev, [k]: v }))

  const updateEvent = (i: number, k: keyof AboutStoryEvent) => (v: string) =>
    setTimeline((prev) => prev.map((e, idx) => (idx === i ? { ...e, [k]: v } : e)))
  const addEvent = () => setTimeline((prev) => [...prev, { year: '', title: '', description: '' }])
  const removeEvent = (i: number) => setTimeline((prev) => prev.filter((_, idx) => idx !== i))

  const handleSave = async () => {
    setSaving(true)
    try {
      const kept = timeline.filter((e) => e.year.trim() || e.title.trim() || e.description.trim())
      const intro = storyIntro.split(/\n\s*\n/).map((p) => p.trim()).filter(Boolean)
      const noteParagraphs = noteText.split(/\n\s*\n/).map((p) => p.trim()).filter(Boolean)
      const customNote = noteMode === 'custom' && noteParagraphs.length > 0
      await api.put('/branding', {
        ...form,
        about_story: kept.length > 0 || intro.length > 0 || noteMode !== 'stock'
          ? {
              intro,
              timeline: kept,
              ...(customNote
                ? { director_note: { paragraphs: noteParagraphs, signature: noteSignature.trim() } }
                : {}),
              ...(noteMode === 'hidden' ? { hide_director_note: true } : {}),
            }
          : null,
      })
      await refetch()
      toast.success('Branding updated')
    } catch (err) {
      const e = err as { message?: string }
      toast.error(e.message || 'Failed to update branding')
    } finally {
      setSaving(false)
    }
  }

  if (contextLoading) {
    return (
      <AdminShell title="Branding & Contact">
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
        </div>
      </AdminShell>
    )
  }

  return (
    <AdminShell title="Branding & Contact">
      <div className="max-w-5xl mx-auto p-6 space-y-6">
        <div className="flex items-center justify-between gap-3 mb-2">
          <div className="flex items-center gap-3">
            <Building2 className="w-8 h-8 text-lsc-rose" />
            <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
              Branding & Contact
            </h1>
          </div>
          <button
            type="button"
            onClick={handleSave}
            disabled={saving}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-lsc-rose text-white font-medium hover:bg-lsc-rose/90 disabled:opacity-60"
          >
            <Save className="w-4 h-4" />
            {saving ? 'Saving…' : 'Save changes'}
          </button>
        </div>

        <Section title="Library identity" icon={Building2}>
          <Field label="Library name" value={form.library_name} onChange={update('library_name')} />
          <Field label="Short name" value={form.library_short_name} onChange={update('library_short_name')} helper="Used in tight spaces (e.g. card prefix labels)" />
          <Field label="Tagline" value={form.tagline} onChange={update('tagline')} />
          <Field label="Primary domain" value={form.domain} onChange={update('domain')} placeholder="l30.org" />
        </Section>

        <Section title="Contact emails" icon={Mail}>
          <Field label="General contact" value={form.contact_email} onChange={update('contact_email')} type="email" helper="Shown as 'Email Us' in the footer" />
          <Field label="Privacy / data requests" value={form.privacy_email} onChange={update('privacy_email')} type="email" />
          <Field label="Indie press / catalog submissions" value={form.indie_email} onChange={update('indie_email')} type="email" />
          <Field label="Giving / donations" value={form.giving_email} onChange={update('giving_email')} type="email" />
          <Field label="Events" value={form.events_email} onChange={update('events_email')} type="email" />
          <Field label="Print services" value={form.print_email} onChange={update('print_email')} type="email" />
          <Field label="Makerspace" value={form.makerspace_email} onChange={update('makerspace_email')} type="email" />
          <Field label="Phone" value={form.phone} onChange={update('phone')} type="tel" />
        </Section>

        <Section title="Mailing address" icon={MapPin}>
          <Field label="Address line 1" value={form.address_line1} onChange={update('address_line1')} />
          <Field label="Address line 2" value={form.address_line2} onChange={update('address_line2')} />
          <Field label="City" value={form.city} onChange={update('city')} />
          <Field label="State" value={form.state} onChange={update('state')} />
          <Field label="ZIP" value={form.zip_code} onChange={update('zip_code')} />
        </Section>

        <Section title="Brand colors" icon={Palette}>
          <Field label="Primary color (hex)" value={form.primary_color} onChange={update('primary_color')} placeholder="#8B5E5E" helper="Used for buttons, accents, focus rings" />
          <Field label="Accent color (hex)" value={form.accent_color} onChange={update('accent_color')} placeholder="#D49898" helper="Derives the warm accent palette" />
        </Section>

        <Section title="Hero & social" icon={Globe}>
          <Field label="Hero title" value={form.hero_title} onChange={update('hero_title')} helper="Leave blank to use the default copy from translations" />
          <Field label="Hero subtitle" value={form.hero_subtitle} onChange={update('hero_subtitle')} helper="Leave blank to use the default copy from translations" />
          <Field label="Bluesky URL" value={form.bluesky_url} onChange={update('bluesky_url')} placeholder="https://bsky.app/profile/..." />
          <Field label="Mastodon URL" value={form.mastodon_url} onChange={update('mastodon_url')} placeholder="https://mastodon.social/@..." />
        </Section>

        <Section title="Sensory access info" icon={Accessibility}>
          <div className="md:col-span-2 space-y-4">
            <Field
              label="Quiet hours"
              value={form.quiet_hours ?? ''}
              onChange={update('quiet_hours')}
              helper="Shown on the homepage to help patrons plan their visit. Example: Weekday mornings, 9–11am"
            />
            <Field
              label="Sensory-friendly times"
              value={form.sensory_friendly_times ?? ''}
              onChange={update('sensory_friendly_times')}
              helper="Times when the library reduces lights, noise, and announcements. Example: First Saturday monthly, 10am–noon"
            />
            <Field
              label="Low-stimulation seating area"
              value={form.low_stim_seating ?? ''}
              onChange={update('low_stim_seating')}
              helper="Where patrons can find a quieter spot. Example: Quiet reading nook, NE corner past the stacks"
            />
          </div>
        </Section>

        <Section title="Our Story timeline (About page)" icon={BookOpen}>
          <div className="md:col-span-2 space-y-4">
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">
              Shown as "How We Got Here" on the About page. Leave empty to keep the
              stock timeline until you write your library's own history.
            </p>
            <label className="block">
              <span className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Story introduction</span>
              <textarea
                value={storyIntro}
                onChange={(e) => setStoryIntro(e.target.value)}
                rows={5}
                placeholder="The paragraphs shown beside the timeline. Separate paragraphs with a blank line."
                className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose/50"
              />
              <span className="block mt-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/60">Separate paragraphs with a blank line.</span>
            </label>
            {timeline.map((event, i) => (
              <div
                key={i}
                className="grid grid-cols-1 md:grid-cols-[7rem_1fr_auto] gap-3 items-start p-3 rounded-lg border border-lsc-border dark:border-earth-700"
              >
                <Field label="Year" value={event.year} onChange={updateEvent(i, 'year')} placeholder="1883" />
                <div className="space-y-3">
                  <Field label="Title" value={event.title} onChange={updateEvent(i, 'title')} placeholder="A library for Orange" />
                  <label className="block">
                    <span className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Description</span>
                    <textarea
                      value={event.description}
                      onChange={(e) => updateEvent(i, 'description')(e.target.value)}
                      rows={2}
                      className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose/50"
                    />
                  </label>
                </div>
                <button
                  type="button"
                  onClick={() => removeEvent(i)}
                  aria-label={`Remove timeline entry ${event.year || i + 1}`}
                  className="mt-7 p-2 rounded-lg text-lsc-dark/60 dark:text-lsc-cream/60 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-900/20"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
            <button
              type="button"
              onClick={addEvent}
              className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-600 text-sm font-medium text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700"
            >
              <Plus className="w-4 h-4" /> Add timeline entry
            </button>

            <fieldset className="pt-4 border-t border-lsc-border dark:border-earth-700">
              <legend className="text-sm font-medium text-lsc-dark dark:text-lsc-cream pt-4 mb-1">
                "A Note From the Director" (About page)
              </legend>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60 mb-3">
                Shown below the timeline. Write your own, or hide the section until
                your director has one ready.
              </p>
              <div className="flex flex-wrap gap-4 mb-3">
                {([
                  ['custom', 'Write our own'],
                  ['hidden', 'Hide the section'],
                  ['stock', 'Sample note'],
                ] as const).map(([mode, label]) => (
                  <label key={mode} className="inline-flex items-center gap-2 text-sm text-lsc-dark dark:text-lsc-cream">
                    <input
                      type="radio"
                      name="director-note-mode"
                      checked={noteMode === mode}
                      onChange={() => setNoteMode(mode)}
                      className="w-4 h-4 accent-[rgb(var(--accent-rose-rgb))]"
                    />
                    {label}
                  </label>
                ))}
              </div>
              {noteMode === 'custom' && (
                <div className="space-y-3">
                  <label className="block">
                    <span className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Note text</span>
                    <textarea
                      value={noteText}
                      onChange={(e) => setNoteText(e.target.value)}
                      rows={4}
                      placeholder="A few short paragraphs from your director. Separate paragraphs with a blank line."
                      className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose/50"
                    />
                  </label>
                  <Field
                    label="Signature"
                    value={noteSignature}
                    onChange={setNoteSignature}
                    placeholder="Jane Doe, Director"
                  />
                </div>
              )}
              {noteMode === 'stock' && (
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">
                  Shows the sample note signed "Marlene W., Director" until you replace or hide it.
                </p>
              )}
            </fieldset>
          </div>
        </Section>

        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">
          Changes save to <code>library_branding</code> and refresh the live site immediately.
          Browser HTTP cache may keep the old value visible for a few minutes for users with
          recently-loaded tabs.
        </p>
      </div>
    </AdminShell>
  )
}
