/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from "react"
import { Loader2, Trash2, Plus, RefreshCw } from "lucide-react"
import toast from "react-hot-toast"
import { Modal } from "@/components/ui/Modal"
import ConfirmDialog from "@/components/ConfirmDialog"
import ImageAltModal from "./ImageAltModal"
import { listBlogMedia, deleteBlogMedia } from "@/services/blog-api"

const PAGE_SIZE = 50

interface MediaItem {
  filename: string
  url: string
  size: number
  uploaded_at: number
}

export interface MediaLibraryPanelProps {
  isOpen: boolean
  token: string | null
  onClose: () => void
  /** Called when the user picks an image and confirms alt text. */
  onInsert: (args: { url: string; alt: string; decorative: boolean }) => void
}

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / 1024 / 1024).toFixed(1)} MB`
}

export default function MediaLibraryPanel({
  isOpen,
  token,
  onClose,
  onInsert,
}: MediaLibraryPanelProps): React.ReactElement | null {
  const [items, setItems] = useState<MediaItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE)
  const [pendingInsert, setPendingInsert] = useState<MediaItem | null>(null)
  const [pendingDelete, setPendingDelete] = useState<MediaItem | null>(null)
  const [deleting, setDeleting] = useState(false)

  const load = async () => {
    if (!token) return
    setLoading(true)
    setError(null)
    try {
      const data = await listBlogMedia(token)
      // Most-recent first
      const sorted = [...data].sort((a, b) => b.uploaded_at - a.uploaded_at)
      setItems(sorted)
      setVisibleCount(PAGE_SIZE)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load media")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (isOpen && token) {
      load()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, token])

  const handleDelete = async () => {
    if (!token || !pendingDelete) return
    setDeleting(true)
    try {
      await deleteBlogMedia(token, pendingDelete.filename)
      setItems((prev) => prev.filter((i) => i.filename !== pendingDelete.filename))
      toast.success("Image deleted")
      setPendingDelete(null)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Delete failed")
    } finally {
      setDeleting(false)
    }
  }

  const handleAltConfirm = (result: { alt: string; decorative: boolean }) => {
    if (!pendingInsert) return
    onInsert({ url: pendingInsert.url, alt: result.alt, decorative: result.decorative })
    setPendingInsert(null)
    onClose()
  }

  if (!isOpen) return null

  const visibleItems = items.slice(0, visibleCount)
  const hasMore = visibleCount < items.length

  return (
    <>
      <Modal isOpen={isOpen && !pendingInsert && !pendingDelete} onClose={onClose} title="Media library" size="2xl">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">
              {loading
                ? "Loading..."
                : `${items.length} image${items.length === 1 ? "" : "s"} available`}
            </p>
            <button
              type="button"
              onClick={load}
              disabled={loading || !token}
              className="flex items-center gap-1 text-sm px-3 py-1.5 rounded-lg text-lsc-dark/70 dark:text-lsc-cream/60 hover:bg-lsc-cream dark:hover:bg-earth-700 focus:outline-none focus:ring-2 focus:ring-lsc-rose disabled:opacity-50"
              aria-label="Refresh media library"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? "motion-safe:animate-spin" : ""}`} aria-hidden="true" />
              Refresh
            </button>
          </div>

          {error && (
            <div role="alert" className="rounded-lg bg-status-danger-100 text-status-danger-700 px-3 py-2 text-sm">
              {error}
            </div>
          )}

          {loading && items.length === 0 ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" aria-hidden="true" />
              <span className="sr-only">Loading media</span>
            </div>
          ) : items.length === 0 ? (
            <div className="text-center py-12 text-lsc-dark/60 dark:text-lsc-cream/50 text-sm">
              No images uploaded yet. Use the toolbar image button to upload your first one.
            </div>
          ) : (
            <>
              <ul className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3" aria-label="Uploaded images">
                {visibleItems.map((item) => (
                  <li
                    key={item.filename}
                    className="group rounded-lg border border-lsc-border dark:border-earth-700 overflow-hidden bg-lsc-cream/30 dark:bg-earth-900/40 flex flex-col"
                  >
                    <div className="aspect-square bg-white dark:bg-earth-950 flex items-center justify-center overflow-hidden">
                      <img
                        src={item.url}
                        alt=""
                        role="presentation"
                        loading="lazy"
                        className="w-full h-full object-cover"
                      />
                    </div>
                    <div className="p-2 text-xs space-y-1">
                      <div
                        className="truncate font-medium text-lsc-dark dark:text-lsc-cream"
                        title={item.filename}
                      >
                        {item.filename}
                      </div>
                      <div className="text-lsc-dark/60 dark:text-lsc-cream/50">{formatBytes(item.size)}</div>
                      <div className="flex gap-1 pt-1">
                        <button
                          type="button"
                          onClick={() => setPendingInsert(item)}
                          className="flex-1 inline-flex items-center justify-center gap-1 px-2 py-1 text-xs rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                          aria-label={`Insert ${item.filename}`}
                        >
                          <Plus className="w-3 h-3" aria-hidden="true" />
                          Insert
                        </button>
                        <button
                          type="button"
                          onClick={() => setPendingDelete(item)}
                          className="inline-flex items-center justify-center px-2 py-1 text-xs rounded-lg border border-lsc-border dark:border-earth-700 text-status-danger-700 hover:bg-status-danger-100 focus:outline-none focus:ring-2 focus:ring-status-danger-600"
                          aria-label={`Delete ${item.filename}`}
                        >
                          <Trash2 className="w-3 h-3" aria-hidden="true" />
                        </button>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>

              {hasMore && (
                <div className="flex justify-center pt-2">
                  <button
                    type="button"
                    onClick={() => setVisibleCount((c) => c + PAGE_SIZE)}
                    className="px-4 py-2 text-sm rounded-xl border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                  >
                    Load more ({items.length - visibleCount} remaining)
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </Modal>

      {pendingInsert && (
        <ImageAltModal
          isOpen={!!pendingInsert}
          imageUrl={pendingInsert.url}
          initialAlt={pendingInsert.filename.replace(/\.[^.]+$/, "").replace(/[-_]+/g, " ")}
          onConfirm={handleAltConfirm}
          onCancel={() => setPendingInsert(null)}
        />
      )}

      {pendingDelete && (
        <ConfirmDialog
          isOpen={!!pendingDelete}
          title="Delete image?"
          message={
            <span>
              Are you sure you want to delete <strong>{pendingDelete.filename}</strong>? This cannot be undone, and any posts already using it will show a broken image.
            </span>
          }
          confirmText="Delete image"
          cancelText="Keep image"
          confirmVariant="danger"
          loading={deleting}
          onConfirm={handleDelete}
          onCancel={() => setPendingDelete(null)}
        />
      )}
    </>
  )
}
