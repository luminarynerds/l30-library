/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useCallback, useEffect, useMemo, useState } from "react"
import {
  ChevronDown,
  ChevronRight,
  Download,
  FilePlus,
  FolderTree,
  Loader2,
  Plus,
  Trash2,
} from "lucide-react"
import { AdminShell } from "../../components/shells/AdminShell"
import { Modal } from "../../components/ui/Modal"
import {
  type ArchivalCollection,
  type ArchivalCollectionCreate,
  type ArchivalCollectionItem,
  type ArchivalCollectionTreeNode,
  type ArchivalCollectionUpdate,
  type ArchivalLevel,
  addCollectionItem,
  createCollection,
  deleteCollection,
  eadExportUrl,
  getCollection,
  getCollectionTree,
  listCollectionItems,
  listRootCollections,
  removeCollectionItem,
  updateCollection,
} from "../../api/archival-collections-api"

const LEVELS: ArchivalLevel[] = [
  "collection",
  "fonds",
  "recordgrp",
  "subgrp",
  "series",
  "subseries",
  "file",
  "item",
]

const EMPTY_DRAFT: ArchivalCollectionCreate = {
  name: "",
  description: null,
  parent_id: null,
  position: 0,
  level: null,
  reference_code: null,
  title: null,
  date_creation: null,
  date_accumulation: null,
  extent: null,
  creator: null,
  biographical_history: null,
  archival_history: null,
  acquisition_source: null,
  scope_content: null,
  appraisal: null,
  accruals: null,
  arrangement: null,
  access_conditions: null,
  reproduction_conditions: null,
  languages: null,
  physical_access: null,
  technical_access: null,
  finding_aids: null,
  originals_location: null,
  copies_location: null,
  related_materials: null,
  publication_note: null,
  notes: null,
  description_rules: null,
  description_status: null,
  described_by: null,
}

function levelLabel(level: ArchivalLevel | null | undefined): string {
  if (!level) return "—"
  return level.replace(/_/g, " ")
}

function TreeNode({
  node,
  selectedId,
  onSelect,
  depth,
}: {
  node: ArchivalCollectionTreeNode
  selectedId: number | null
  onSelect: (id: number) => void
  depth: number
}) {
  const [open, setOpen] = useState(true)
  const isSelected = selectedId === node.id
  const hasChildren = node.children.length > 0
  return (
    <div>
      <div
        className={`w-full flex items-center gap-1 py-1 pr-2 rounded-lg ${
          isSelected
            ? "bg-lsc-rose/10 text-lsc-dark dark:text-lsc-cream"
            : "hover:bg-lsc-cream dark:hover:bg-earth-700"
        }`}
        style={{ paddingLeft: `${depth * 14 + 6}px` }}
      >
        {hasChildren ? (
          <button
            type="button"
            className="p-0.5 text-lsc-dark/70 dark:text-lsc-cream/70"
            onClick={(e) => {
              e.stopPropagation()
              setOpen((v) => !v)
            }}
            aria-label={open ? "Collapse" : "Expand"}
          >
            {open ? (
              <ChevronDown className="w-4 h-4" />
            ) : (
              <ChevronRight className="w-4 h-4" />
            )}
          </button>
        ) : (
          <span className="w-5" />
        )}
        <button
          type="button"
          className="flex-1 min-w-0 text-left flex items-center gap-1"
          onClick={() => onSelect(node.id)}
        >
          <FolderTree className="w-4 h-4 text-lsc-rose" />
          <span className="text-sm text-lsc-dark dark:text-lsc-cream truncate">
            {node.title || node.name}
          </span>
          <span className="ml-auto text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
            {levelLabel(node.level)}
            {node.item_count > 0 ? ` · ${node.item_count}` : ""}
          </span>
        </button>
      </div>
      {open &&
        node.children.map((child) => (
          <TreeNode
            key={child.id}
            node={child}
            selectedId={selectedId}
            onSelect={onSelect}
            depth={depth + 1}
          />
        ))}
    </div>
  )
}

interface CollectionFormProps {
  draft: ArchivalCollectionCreate
  onChange: (next: ArchivalCollectionCreate) => void
}

function field<K extends keyof ArchivalCollectionCreate>(
  draft: ArchivalCollectionCreate,
  onChange: (next: ArchivalCollectionCreate) => void,
  key: K,
  value: ArchivalCollectionCreate[K],
) {
  onChange({ ...draft, [key]: value })
}

const inputClass =
  "w-full rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"

function CollectionForm({ draft, onChange }: CollectionFormProps) {
  const text = (
    key: keyof ArchivalCollectionCreate,
    label: string,
    longform = false,
  ) => (
    <label className="block">
      <span className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
        {label}
      </span>
      {longform ? (
        <textarea
          className={`${inputClass} min-h-[80px]`}
          value={(draft[key] as string) ?? ""}
          onChange={(e) =>
            field(draft, onChange, key, (e.target.value || null) as never)
          }
        />
      ) : (
        <input
          type="text"
          className={inputClass}
          value={(draft[key] as string) ?? ""}
          onChange={(e) =>
            field(draft, onChange, key, (e.target.value || null) as never)
          }
        />
      )}
    </label>
  )

  return (
    <div className="space-y-6">
      <section className="space-y-3">
        <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
          Identity
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <label className="block md:col-span-2">
            <span className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
              Name (internal label) *
            </span>
            <input
              type="text"
              required
              className={inputClass}
              value={draft.name}
              onChange={(e) =>
                field(draft, onChange, "name", e.target.value as never)
              }
            />
          </label>
          {text("title", "Title (DACS 2.3)")}
          {text("reference_code", "Reference code (DACS 2.1)")}
          {text("date_creation", "Date of creation (DACS 2.4)")}
          {text("date_accumulation", "Date of accumulation")}
          {text("extent", "Extent (DACS 2.5)")}
          {text("creator", "Creator (DACS 2.6)")}
          <label className="block">
            <span className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
              Level
            </span>
            <select
              className={inputClass}
              value={draft.level ?? ""}
              onChange={(e) =>
                field(
                  draft,
                  onChange,
                  "level",
                  (e.target.value || null) as never,
                )
              }
            >
              <option value="">—</option>
              {LEVELS.map((l) => (
                <option key={l} value={l}>
                  {levelLabel(l)}
                </option>
              ))}
            </select>
          </label>
          {text("languages", "Language(s) of material")}
        </div>
      </section>

      <section className="space-y-3">
        <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
          Context
        </h3>
        {text("biographical_history", "Biographical / administrative history", true)}
        {text("archival_history", "Archival history (custodial)", true)}
        {text("acquisition_source", "Immediate source of acquisition", true)}
      </section>

      <section className="space-y-3">
        <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
          Content & structure
        </h3>
        {text("scope_content", "Scope and content (DACS 3.1)", true)}
        {text("appraisal", "Appraisal, destruction, scheduling", true)}
        {text("accruals", "Accruals", true)}
        {text("arrangement", "System of arrangement", true)}
      </section>

      <section className="space-y-3">
        <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
          Conditions of access &amp; use
        </h3>
        {text("access_conditions", "Conditions governing access (DACS 4.1)", true)}
        {text("reproduction_conditions", "Conditions governing reproduction", true)}
        {text("physical_access", "Physical access", true)}
        {text("technical_access", "Technical access", true)}
        {text("finding_aids", "Finding aids", true)}
      </section>

      <section className="space-y-3">
        <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
          Allied materials
        </h3>
        {text("originals_location", "Existence/location of originals", true)}
        {text("copies_location", "Existence/location of copies", true)}
        {text("related_materials", "Related archival materials", true)}
        {text("publication_note", "Publication note", true)}
      </section>

      <section className="space-y-3">
        <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
          Notes &amp; description control
        </h3>
        {text("notes", "Notes", true)}
        {text("description_rules", "Description rules (e.g. DACS, RAD)")}
        {text("description_status", "Description status (draft/final)")}
        {text("described_by", "Described by")}
      </section>
    </div>
  )
}

export default function StaffArchivalCollectionsPage() {
  const [roots, setRoots] = useState<ArchivalCollection[]>([])
  const [trees, setTrees] = useState<Record<number, ArchivalCollectionTreeNode>>(
    {},
  )
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [selected, setSelected] = useState<ArchivalCollection | null>(null)
  const [items, setItems] = useState<ArchivalCollectionItem[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [draft, setDraft] = useState<ArchivalCollectionUpdate | null>(null)

  const [createOpen, setCreateOpen] = useState(false)
  const [createParentId, setCreateParentId] = useState<number | null>(null)
  const [createDraft, setCreateDraft] = useState<ArchivalCollectionCreate>(EMPTY_DRAFT)

  const [addItemOpen, setAddItemOpen] = useState(false)
  const [addItemId, setAddItemId] = useState("")
  const [addItemLabel, setAddItemLabel] = useState("")

  const refreshTrees = useCallback(async (rootIds: number[]) => {
    const next: Record<number, ArchivalCollectionTreeNode> = {}
    for (const id of rootIds) {
      try {
        next[id] = await getCollectionTree(id)
      } catch {
        // skip
      }
    }
    setTrees(next)
  }, [])

  const refreshAll = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const list = await listRootCollections()
      setRoots(list)
      await refreshTrees(list.map((c) => c.id))
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load collections")
    } finally {
      setLoading(false)
    }
  }, [refreshTrees])

  useEffect(() => {
    void refreshAll()
  }, [refreshAll])

  const refreshSelected = useCallback(async (id: number) => {
    try {
      const [c, its] = await Promise.all([
        getCollection(id),
        listCollectionItems(id),
      ])
      setSelected(c)
      setItems(its)
      setDraft(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load collection")
    }
  }, [])

  useEffect(() => {
    if (selectedId !== null) {
      void refreshSelected(selectedId)
    } else {
      setSelected(null)
      setItems([])
    }
  }, [selectedId, refreshSelected])

  const onSave = useCallback(async () => {
    if (selectedId === null || draft === null) return
    setSaving(true)
    try {
      const updated = await updateCollection(selectedId, draft)
      setSelected(updated)
      setDraft(null)
      await refreshAll()
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save")
    } finally {
      setSaving(false)
    }
  }, [selectedId, draft, refreshAll])

  const onDelete = useCallback(async () => {
    if (selectedId === null) return
    if (!confirm("Delete this collection? This cannot be undone.")) return
    setSaving(true)
    try {
      await deleteCollection(selectedId)
      setSelectedId(null)
      await refreshAll()
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete")
    } finally {
      setSaving(false)
    }
  }, [selectedId, refreshAll])

  const openCreate = useCallback((parentId: number | null) => {
    setCreateParentId(parentId)
    setCreateDraft({ ...EMPTY_DRAFT, parent_id: parentId })
    setCreateOpen(true)
  }, [])

  const onCreate = useCallback(async () => {
    setSaving(true)
    try {
      const created = await createCollection({
        ...createDraft,
        parent_id: createParentId,
      })
      setCreateOpen(false)
      setCreateDraft(EMPTY_DRAFT)
      await refreshAll()
      setSelectedId(created.id)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create")
    } finally {
      setSaving(false)
    }
  }, [createDraft, createParentId, refreshAll])

  const onAddItem = useCallback(async () => {
    if (selectedId === null) return
    const id = parseInt(addItemId, 10)
    if (Number.isNaN(id)) {
      setError("Catalog item id must be a number")
      return
    }
    setSaving(true)
    try {
      await addCollectionItem(
        selectedId,
        id,
        items.length,
        addItemLabel || undefined,
      )
      setAddItemOpen(false)
      setAddItemId("")
      setAddItemLabel("")
      await refreshSelected(selectedId)
      await refreshTrees(roots.map((r) => r.id))
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to add item")
    } finally {
      setSaving(false)
    }
  }, [selectedId, addItemId, addItemLabel, items.length, refreshSelected, refreshTrees, roots])

  const onRemoveItem = useCallback(
    async (linkId: number) => {
      if (selectedId === null) return
      setSaving(true)
      try {
        await removeCollectionItem(selectedId, linkId)
        await refreshSelected(selectedId)
        await refreshTrees(roots.map((r) => r.id))
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to remove item")
      } finally {
        setSaving(false)
      }
    },
    [selectedId, refreshSelected, refreshTrees, roots],
  )

  const editingDraft = useMemo<ArchivalCollectionCreate | null>(() => {
    if (!selected) return null
    const merged: ArchivalCollectionCreate = { ...EMPTY_DRAFT }
    for (const k of Object.keys(EMPTY_DRAFT) as (keyof ArchivalCollectionCreate)[]) {
      const v = (draft && k in draft ? draft[k] : selected[k]) as never
      ;(merged as Record<string, unknown>)[k] = v
    }
    return merged
  }, [selected, draft])

  return (
    <AdminShell title="Archival collections" subtitle="Hierarchical, DACS-aligned collection cataloging.">
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <aside className="lg:col-span-4 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-3">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
              Hierarchy
            </h2>
            <button
              type="button"
              onClick={() => openCreate(null)}
              className="inline-flex items-center gap-1 rounded-lg bg-lsc-rose hover:bg-lsc-rose/90 text-white px-3 py-1.5 text-sm"
            >
              <Plus className="w-4 h-4" /> New top-level
            </button>
          </div>
          {loading ? (
            <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 py-6">
              <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> Loading…
            </div>
          ) : roots.length === 0 ? (
            <div className="text-center py-10 text-lsc-dark/70 dark:text-lsc-cream/70">
              <FolderTree className="w-12 h-12 mx-auto opacity-50 mb-2" />
              <div className="font-semibold">No collections yet</div>
              <div className="text-sm">Create a top-level collection to begin.</div>
            </div>
          ) : (
            <div className="space-y-1">
              {roots.map((root) => {
                const tree = trees[root.id]
                if (!tree) return null
                return (
                  <TreeNode
                    key={root.id}
                    node={tree}
                    selectedId={selectedId}
                    onSelect={setSelectedId}
                    depth={0}
                  />
                )
              })}
            </div>
          )}
        </aside>

        <section className="lg:col-span-8 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-4">
          {error && (
            <div className="mb-3 px-3 py-2 rounded-lg bg-status-danger-50 dark:bg-status-danger-900/20 text-status-danger-800 dark:text-status-danger-300 text-sm">
              {error}
            </div>
          )}
          {!selected ? (
            <div className="text-center py-16 text-lsc-dark/70 dark:text-lsc-cream/70">
              <FolderTree className="w-12 h-12 mx-auto opacity-50 mb-2" />
              <div className="font-semibold">Select a collection</div>
              <div className="text-sm">
                Pick a node from the hierarchy or create a new one.
              </div>
            </div>
          ) : (
            <>
              <div className="flex flex-wrap items-center gap-2 mb-4">
                <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream flex-1">
                  {selected.title || selected.name}
                </h2>
                <button
                  type="button"
                  onClick={() => openCreate(selected.id)}
                  className="inline-flex items-center gap-1 rounded-lg bg-lsc-rose hover:bg-lsc-rose/90 text-white px-3 py-1.5 text-sm"
                >
                  <FilePlus className="w-4 h-4" /> Add child
                </button>
                <a
                  href={eadExportUrl(selected.id)}
                  className="inline-flex items-center gap-1 rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 px-3 py-1.5 text-sm"
                >
                  <Download className="w-4 h-4" /> EAD3 XML
                </a>
                <button
                  type="button"
                  disabled={saving}
                  onClick={onDelete}
                  className="inline-flex items-center gap-1 rounded-lg bg-status-danger-600 hover:bg-status-danger-700 text-white px-3 py-1.5 text-sm disabled:opacity-60"
                >
                  <Trash2 className="w-4 h-4" /> Delete
                </button>
              </div>

              {editingDraft && (
                <CollectionForm
                  draft={editingDraft}
                  onChange={(next) => setDraft(next)}
                />
              )}

              <div className="mt-6 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setDraft(null)}
                  disabled={!draft || saving}
                  className="rounded-lg px-4 py-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700 disabled:opacity-60"
                >
                  Discard changes
                </button>
                <button
                  type="button"
                  onClick={onSave}
                  disabled={!draft || saving}
                  className="inline-flex items-center gap-1 rounded-lg bg-lsc-rose hover:bg-lsc-rose/90 text-white px-4 py-2 text-sm disabled:opacity-60"
                >
                  {saving && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
                  Save
                </button>
              </div>

              <div className="mt-8">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
                    Catalog items in this component
                  </h3>
                  <button
                    type="button"
                    onClick={() => setAddItemOpen(true)}
                    className="inline-flex items-center gap-1 rounded-lg bg-lsc-rose hover:bg-lsc-rose/90 text-white px-3 py-1.5 text-sm"
                  >
                    <Plus className="w-4 h-4" /> Assign item
                  </button>
                </div>
                {items.length === 0 ? (
                  <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    No items linked to this component yet.
                  </div>
                ) : (
                  <ul className="divide-y divide-lsc-border dark:divide-earth-700">
                    {items.map((it) => (
                      <li
                        key={it.id}
                        className="py-2 flex items-center gap-2"
                      >
                        <span className="text-sm text-lsc-dark dark:text-lsc-cream flex-1">
                          {it.component_label || it.catalog_item_title || `Item #${it.catalog_item_id}`}
                          {it.catalog_item_author && (
                            <span className="text-lsc-dark/70 dark:text-lsc-cream/70">
                              {" "}— {it.catalog_item_author}
                            </span>
                          )}
                        </span>
                        <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                          #{it.catalog_item_id}
                        </span>
                        <button
                          type="button"
                          disabled={saving}
                          onClick={() => onRemoveItem(it.id)}
                          className="text-status-danger-600 hover:text-status-danger-700 disabled:opacity-60"
                          aria-label="Remove"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </>
          )}
        </section>
      </div>

      <Modal
        isOpen={createOpen}
        onClose={() => setCreateOpen(false)}
        title={createParentId === null ? "New top-level collection" : "New child component"}
        size="2xl"
        footer={
          <div className="flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={() => setCreateOpen(false)}
              className="rounded-lg px-4 py-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={onCreate}
              disabled={saving || !createDraft.name.trim()}
              className="inline-flex items-center gap-1 rounded-lg bg-lsc-rose hover:bg-lsc-rose/90 text-white px-4 py-2 text-sm disabled:opacity-60"
            >
              {saving && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
              Create
            </button>
          </div>
        }
      >
        <CollectionForm draft={createDraft} onChange={setCreateDraft} />
      </Modal>

      <Modal
        isOpen={addItemOpen}
        onClose={() => setAddItemOpen(false)}
        title="Assign catalog item"
        size="md"
        footer={
          <div className="flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={() => setAddItemOpen(false)}
              className="rounded-lg px-4 py-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={onAddItem}
              disabled={saving || !addItemId.trim()}
              className="inline-flex items-center gap-1 rounded-lg bg-lsc-rose hover:bg-lsc-rose/90 text-white px-4 py-2 text-sm disabled:opacity-60"
            >
              {saving && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
              Add
            </button>
          </div>
        }
      >
        <div className="space-y-3">
          <label className="block">
            <span className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
              Catalog item ID
            </span>
            <input
              type="text"
              className={inputClass}
              value={addItemId}
              onChange={(e) => setAddItemId(e.target.value)}
            />
          </label>
          <label className="block">
            <span className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
              Component label (optional)
            </span>
            <input
              type="text"
              className={inputClass}
              value={addItemLabel}
              onChange={(e) => setAddItemLabel(e.target.value)}
              placeholder="e.g. Folder 3, Letter from John Doe, 1923"
            />
          </label>
        </div>
      </Modal>
    </AdminShell>
  )
}
