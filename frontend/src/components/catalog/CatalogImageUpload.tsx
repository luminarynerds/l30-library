/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useRef, useCallback } from 'react'
import { Upload, Star, Loader2, Trash2 } from 'lucide-react'
import type { CatalogImage } from '@/api/catalog-api'
import {
  uploadCatalogImage,
  deleteCatalogImage,
  updateCatalogImage,
} from '@/api/catalog-api'
import { t } from '@/i18n'

interface CatalogImageUploadProps {
  itemId: number
  images: CatalogImage[]
  token: string
  onImagesChanged: () => void
}

const ACCEPTED_TYPES = ['image/png', 'image/jpeg', 'image/gif', 'image/webp']
const MAX_SIZE_MB = 10
const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024

export default function CatalogImageUpload({
  itemId,
  images,
  token,
  onImagesChanged,
}: CatalogImageUploadProps): React.ReactElement {
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<number | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileSelect = useCallback(
    async (files: FileList | null) => {
      if (!files || files.length === 0) return
      setError(null)

      const file = files[0]!
      if (!file) return

      if (!ACCEPTED_TYPES.includes(file.type)) {
        setError('File must be an image (PNG, JPEG, GIF, or WebP)')
        return
      }

      if (file.size > MAX_SIZE_BYTES) {
        setError(`File too large (max ${MAX_SIZE_MB}MB)`)
        return
      }

      setUploading(true)
      try {
        const isPrimary = images.length === 0
        await uploadCatalogImage(token, itemId, file, { is_primary: isPrimary })
        onImagesChanged()
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Upload failed')
      } finally {
        setUploading(false)
        if (fileInputRef.current) fileInputRef.current.value = ''
      }
    },
    [token, itemId, images.length, onImagesChanged]
  )

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      handleFileSelect(e.dataTransfer.files)
    },
    [handleFileSelect]
  )

  const handleDelete = useCallback(
    async (imageId: number) => {
      setDeletingId(imageId)
      try {
        await deleteCatalogImage(token, itemId, imageId)
        onImagesChanged()
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Delete failed')
      } finally {
        setDeletingId(null)
      }
    },
    [token, itemId, onImagesChanged]
  )

  const handleSetPrimary = useCallback(
    async (imageId: number) => {
      try {
        await updateCatalogImage(token, itemId, imageId, { is_primary: true })
        onImagesChanged()
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Update failed')
      }
    },
    [token, itemId, onImagesChanged]
  )

  return (
    <div className="space-y-3">
      <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80">
        Images
      </label>

      {/* Existing images grid */}
      {images.length > 0 && (
        <div className="grid grid-cols-3 sm:grid-cols-4 gap-3">
          {images.map((img) => (
            <div
              key={img.id}
              className="relative group rounded-lg overflow-hidden border border-lsc-border dark:border-earth-700 bg-lsc-cream dark:bg-lsc-brown aspect-square"
            >
              <img
                src={img.image_url}
                alt={img.caption || 'Catalog image'}
                className="w-full h-full object-cover"
                loading="lazy"
              />
              {img.is_primary && (
                <span className="absolute top-1 left-1 bg-lsc-rose text-white text-xs px-1.5 py-0.5 rounded-full flex items-center gap-0.5">
                  <Star className="w-3 h-3" aria-hidden="true" />
                  Primary
                </span>
              )}
              <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 group-focus-within:bg-black/40 transition-colors flex items-center justify-center gap-2 opacity-0 group-hover:opacity-100 group-focus-within:opacity-100">
                {!img.is_primary && (
                  <button
                    type="button"
                    onClick={() => handleSetPrimary(img.id)}
                    className="p-1.5 bg-lsc-white/90 rounded-full text-lsc-rose hover:bg-lsc-white transition-colors"
                    title="Set as primary"
                    aria-label={t('aria.catalog.setAsPrimaryImage')}
                  >
                    <Star className="w-4 h-4" />
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => handleDelete(img.id)}
                  disabled={deletingId === img.id}
                  className="p-1.5 bg-lsc-white/90 rounded-full text-status-danger-600 hover:bg-lsc-white transition-colors disabled:opacity-50"
                  title="Delete image"
                  aria-label={t('aria.catalog.deleteImage')}
                >
                  {deletingId === img.id ? (
                    <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                  ) : (
                    <Trash2 className="w-4 h-4" />
                  )}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Upload area */}
      <div
        onDrop={handleDrop}
        onDragOver={(e) => e.preventDefault()}
        className="border-2 border-dashed border-lsc-border dark:border-earth-700 rounded-xl p-4 text-center hover:border-lsc-rose dark:hover:border-lsc-rose transition-colors cursor-pointer"
        onClick={() => fileInputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            fileInputRef.current?.click()
          }
        }}
        aria-label={t('aria.catalog.uploadImageClickOrDrag')}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="image/png,image/jpeg,image/gif,image/webp"
          className="hidden"
          onChange={(e) => handleFileSelect(e.target.files)}
          disabled={uploading}
        />
        {uploading ? (
          <div className="flex items-center justify-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70">
            <Loader2 className="w-5 h-5 motion-safe:animate-spin" aria-hidden="true" />
            <span className="text-sm">Uploading...</span>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-1 text-lsc-dark/70 dark:text-lsc-cream/60">
            <Upload className="w-6 h-6" aria-hidden="true" />
            <span className="text-sm font-medium">
              Drop image here or click to browse
            </span>
            <span className="text-xs">
              PNG, JPEG, GIF, WebP up to {MAX_SIZE_MB}MB
            </span>
          </div>
        )}
      </div>

      {error && (
        <p className="text-sm text-status-danger-600 dark:text-status-danger-400" role="alert">
          {error}
        </p>
      )}
    </div>
  )
}
