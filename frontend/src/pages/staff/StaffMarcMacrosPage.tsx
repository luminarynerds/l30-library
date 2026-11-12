/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useEffect, useState } from "react"
import { Plus, Trash2, Pencil, X, Wand2 } from "lucide-react"
import toast from "react-hot-toast"
import { AdminShell } from "../../components/shells/AdminShell"
import { Modal } from "../../components/ui/Modal"
import {
  createMarcMacro,
  deleteMarcMacro,
  getMarcMacroTargets,
  listMarcMacros,
  type MarcMacro,
  type MarcMacroOp,
  type MarcMacroStep,
  type MarcMacroVisibility,
  updateMarcMacro,
} from "../../api/marc-macros-api"

const OP_LABELS: Record<MarcMacroOp, string> = {
  set: "Set",
  clear: "Clear",
  find_replace: "Find / replace",
  append: "Append",
}

interface EditorState {
  open: boolean
  macro: MarcMacro | null
  draft: {
    name: string
    description: string
    visibility: MarcMacroVisibility
    steps: MarcMacroStep[]
  }
}

const EMPTY_STEP: MarcMacroStep = { op: "set", tag: "245", subfield: "a", value: "" }

const EMPTY_DRAFT: EditorState["draft"] = {
  name: "",
  description: "",
  visibility: "private",
  steps: [{ ...EMPTY_STEP }],
}

function VisibilityBadge({ value }: { value: MarcMacroVisibility }) {
  const styles =
    value === "shared"
      ? "bg-status-info-100 text-status-info-800 dark:bg-status-info-900/30 dark:text-status-info-300"
      : "bg-lsc-cream text-lsc-dark dark:bg-earth-700 dark:text-lsc-cream"
  return (
    <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${styles}`}>
      {value === "shared" ? "Shared" : "Private"}
    </span>
  )
}

function StepRow({
  step,
  targets,
  onChange,
  onRemove,
}: {
  step: MarcMacroStep
  targets: Record<string, string>
  onChange: (next: MarcMacroStep) => void
  onRemove: () => void
}) {
  const target = `${step.tag}$${step.subfield}`
  const knownTargets = Object.keys(targets)
  return (
    <div className="grid grid-cols-12 gap-2 items-start bg-lsc-cream/40 dark:bg-earth-900/40 rounded-lg p-3">
      <select
        aria-label="Operation"
        className="col-span-3 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 px-2 py-1.5 focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
        value={step.op}
        onChange={(e) => onChange({ ...step, op: e.target.value as MarcMacroOp })}
      >
        {Object.entries(OP_LABELS).map(([v, l]) => (
          <option key={v} value={v}>
            {l}
          </option>
        ))}
      </select>
      <select
        aria-label="Target field"
        className="col-span-4 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 px-2 py-1.5 focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
        value={knownTargets.includes(target) ? target : ""}
        onChange={(e) => {
          const [tag, subfield] = e.target.value.split("$")
          onChange({ ...step, tag: tag ?? '', subfield: subfield ?? '' })
        }}
      >
        {!knownTargets.includes(target) && <option value="">— pick a field —</option>}
        {knownTargets.map((t) => (
          <option key={t} value={t}>
            {t} → {targets[t]}
          </option>
        ))}
      </select>
      {step.op === "find_replace" ? (
        <>
          <input
            aria-label="Find text"
            className="col-span-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 px-2 py-1.5 focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
            placeholder="find"
            value={step.find ?? ""}
            onChange={(e) => onChange({ ...step, find: e.target.value })}
          />
          <input
            aria-label="Replace with"
            className="col-span-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 px-2 py-1.5 focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
            placeholder="replace"
            value={step.replace ?? ""}
            onChange={(e) => onChange({ ...step, replace: e.target.value })}
          />
        </>
      ) : step.op === "clear" ? (
        <div className="col-span-4 text-sm text-lsc-dark/60 dark:text-lsc-cream/60 self-center">
          (no value)
        </div>
      ) : (
        <input
          aria-label="Value"
          className="col-span-4 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 px-2 py-1.5 focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
          placeholder="value"
          value={step.value ?? ""}
          onChange={(e) => onChange({ ...step, value: e.target.value })}
        />
      )}
      <button
        type="button"
        onClick={onRemove}
        className="col-span-1 justify-self-end p-1.5 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-status-danger-600 dark:hover:text-status-danger-400 rounded-lg"
        aria-label="Remove step"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  )
}

function MacroEditor({
  state,
  targets,
  onClose,
  onSaved,
}: {
  state: EditorState
  targets: Record<string, string>
  onClose: () => void
  onSaved: () => void
}) {
  const [draft, setDraft] = useState(state.draft)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)

  useEffect(() => {
    setDraft(state.draft)
    setSaveError(null)
  }, [state.draft])

  if (!state.open) return null

  const isEdit = state.macro !== null

  const updateStep = (idx: number, next: MarcMacroStep) => {
    setDraft((d) => ({
      ...d,
      steps: d.steps.map((s, i) => (i === idx ? next : s)),
    }))
  }

  const removeStep = (idx: number) => {
    setDraft((d) => ({ ...d, steps: d.steps.filter((_, i) => i !== idx) }))
  }

  const addStep = () => {
    setDraft((d) => ({ ...d, steps: [...d.steps, { ...EMPTY_STEP }] }))
  }

  const onSave = async () => {
    if (!draft.name.trim()) {
      toast.error("Name is required")
      return
    }
    if (draft.steps.length === 0) {
      toast.error("Add at least one step")
      return
    }
    setSaving(true)
    setSaveError(null)
    try {
      const payload = {
        name: draft.name.trim(),
        description: draft.description.trim() || null,
        visibility: draft.visibility,
        steps: draft.steps,
      }
      if (isEdit && state.macro) {
        await updateMarcMacro(state.macro.id, payload)
        toast.success("Macro updated")
      } else {
        await createMarcMacro(payload)
        toast.success("Macro created")
      }
      onSaved()
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Save failed"
      setSaveError(msg)
      toast.error(msg)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      isOpen={state.open}
      onClose={onClose}
      title={isEdit ? "Edit macro" : "New macro"}
      size="2xl"
      footer={
        <div className="flex items-center justify-end gap-2 w-full">
          <button
            type="button"
            onClick={onClose}
            disabled={saving}
            className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onSave}
            disabled={saving}
            className="px-4 py-2 rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 disabled:opacity-50"
          >
            {saving ? "Saving…" : "Save"}
          </button>
        </div>
      }
    >
      <div className="space-y-4">
        {saveError && (
          <div
            role="alert"
            className="rounded-lg bg-status-danger-50 dark:bg-status-danger-900/20 text-status-danger-800 dark:text-status-danger-300 text-sm p-3"
          >
            {saveError}
          </div>
        )}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <label className="block">
              <span className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                Name
              </span>
              <input
                className="w-full rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 px-3 py-2 focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                value={draft.name}
                onChange={(e) => setDraft({ ...draft, name: e.target.value })}
              />
            </label>
            <label className="block">
              <span className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                Visibility
              </span>
              <select
                className="w-full rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 px-3 py-2 focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                value={draft.visibility}
                onChange={(e) =>
                  setDraft({
                    ...draft,
                    visibility: e.target.value as MarcMacroVisibility,
                  })
                }
              >
                <option value="private">Private (only me)</option>
                <option value="shared">Shared (library-wide, admin only)</option>
              </select>
            </label>
          </div>
          <label className="block">
            <span className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Description
            </span>
            <textarea
              className="w-full rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 px-3 py-2 focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
              rows={2}
              value={draft.description}
              onChange={(e) =>
                setDraft({ ...draft, description: e.target.value })
              }
            />
          </label>

          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
                Steps
              </span>
              <button
                type="button"
                onClick={addStep}
                className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 text-sm"
              >
                <Plus className="w-4 h-4" /> Add step
              </button>
            </div>
            <div className="space-y-2">
              {draft.steps.map((step, idx) => (
                <StepRow
                  key={idx}
                  step={step}
                  targets={targets}
                  onChange={(next) => updateStep(idx, next)}
                  onRemove={() => removeStep(idx)}
                />
              ))}
              {draft.steps.length === 0 && (
                <div className="text-sm text-lsc-dark/60 dark:text-lsc-cream/60 italic">
                  No steps yet — click “Add step” to begin.
                </div>
              )}
            </div>
          </div>
        </div>
    </Modal>
  )
}

export default function StaffMarcMacrosPage(): React.ReactElement {
  const [macros, setMacros] = useState<MarcMacro[]>([])
  const [targets, setTargets] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [editor, setEditor] = useState<EditorState>({
    open: false,
    macro: null,
    draft: EMPTY_DRAFT,
  })

  const refresh = async () => {
    setLoading(true)
    setError(null)
    try {
      const [list, t] = await Promise.all([listMarcMacros(), getMarcMacroTargets()])
      setMacros(list.items)
      setTargets(t)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load macros")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void refresh()
  }, [])

  const onCreate = () => {
    setEditor({ open: true, macro: null, draft: { ...EMPTY_DRAFT, steps: [{ ...EMPTY_STEP }] } })
  }

  const onEdit = (macro: MarcMacro) => {
    setEditor({
      open: true,
      macro,
      draft: {
        name: macro.name,
        description: macro.description ?? "",
        visibility: macro.visibility,
        steps: macro.steps.length > 0 ? macro.steps : [{ ...EMPTY_STEP }],
      },
    })
  }

  const onDelete = async (macro: MarcMacro) => {
    if (!window.confirm(`Delete macro "${macro.name}"?`)) return
    try {
      await deleteMarcMacro(macro.id)
      toast.success("Macro deleted")
      void refresh()
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Delete failed")
    }
  }

  return (
    <AdminShell
      title="MARC Macros"
      subtitle="Saved field-edit task lists for cataloging."
      icon={<Wand2 className="w-7 h-7 text-lsc-rose" />}
      loading={loading}
      error={error}
      actions={
        <button
          onClick={onCreate}
          className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90"
        >
          <Plus className="w-4 h-4" /> New macro
        </button>
      }
    >
      {macros.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 gap-3 text-center">
          <Wand2 className="w-12 h-12 opacity-50 text-lsc-rose" />
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
            No macros yet
          </h3>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 max-w-md">
            A macro is a saved sequence of MARC field edits. Run one against a single
            record or a batch from catalog search.
          </p>
        </div>
      ) : (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden">
          <table className="w-full text-left">
            <thead className="bg-lsc-cream dark:bg-earth-900 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              <tr>
                <th scope="col" className="px-4 py-2">Name</th>
                <th scope="col" className="px-4 py-2">Visibility</th>
                <th scope="col" className="px-4 py-2">Steps</th>
                <th scope="col" className="px-4 py-2 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {macros.map((m) => (
                <tr
                  key={m.id}
                  className="border-t border-lsc-border dark:border-earth-700"
                >
                  <td className="px-4 py-3 align-top">
                    <div className="font-medium text-lsc-dark dark:text-lsc-cream">
                      {m.name}
                    </div>
                    {m.description && (
                      <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                        {m.description}
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3 align-top">
                    <VisibilityBadge value={m.visibility} />
                  </td>
                  <td className="px-4 py-3 align-top text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    {m.steps.length}
                  </td>
                  <td className="px-4 py-3 align-top text-right">
                    <button
                      onClick={() => onEdit(m)}
                      className="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700"
                      aria-label={`Edit ${m.name}`}
                    >
                      <Pencil className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => onDelete(m)}
                      className="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-status-danger-600 dark:hover:text-status-danger-400 hover:bg-lsc-cream dark:hover:bg-earth-700"
                      aria-label={`Delete ${m.name}`}
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <MacroEditor
        state={editor}
        targets={targets}
        onClose={() => setEditor((e) => ({ ...e, open: false }))}
        onSaved={() => {
          setEditor((e) => ({ ...e, open: false }))
          void refresh()
        }}
      />
    </AdminShell>
  )
}
