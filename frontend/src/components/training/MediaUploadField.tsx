/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy";
import { useRef, useState } from 'react';
import toast from 'react-hot-toast';
import { Upload, Loader2, X } from 'lucide-react';
import { getAccessToken } from '../../utils/tokenStore';

interface Props {
  label: string;
  value: string;
  onChange: (url: string) => void;
  // Caller builds the upload URL; returns null when upload is not yet possible (e.g. unsaved entity)
  getUploadUrl: () => string | null;
  accept: string;
  helpText?: string;
  disabledHint?: string;
}

export default function MediaUploadField({
  label,
  value,
  onChange,
  getUploadUrl,
  accept,
  helpText,
  disabledHint,
}: Props) {
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const uploadUrl = getUploadUrl();
    if (!uploadUrl) return;

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);

      const token = getAccessToken();
      // eslint-disable-next-line no-restricted-syntax -- multipart/form-data upload; fetchApi forces JSON Content-Type
      const res = await fetch(
        uploadUrl,
        {
          method: 'POST',
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          credentials: 'include',
          body: formData,
        },
      );

      if (!res.ok) {
        const errBody = await res.json().catch(() => ({ detail: 'Upload failed' }));
        throw new Error(errBody.detail || 'Upload failed');
      }

      const data = await res.json();
      onChange(data.url);
      toast.success('File uploaded');
    } catch (err) {
      Sentry.captureException(err instanceof Error ? err : new Error(String(err)));
      toast.error(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const canUpload = getUploadUrl() !== null;
  const isImage = accept.startsWith('image/') && value;
  const isAudio = accept.startsWith('audio/') && value;

  return (
    <div>
      <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
        {label}
      </label>

      <div className="flex gap-2">
        <input
          type="url"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="https://... or upload below"
          className="
            flex-1 border border-lsc-border dark:border-earth-700 rounded-lg
            px-4 py-2 bg-lsc-white dark:bg-earth-700
            text-lsc-dark dark:text-lsc-cream
            focus:ring-2 focus:ring-lsc-rose focus:border-transparent
          "
        />
        {value && (
          <button
            type="button"
            onClick={() => onChange('')}
            className="
              p-2 rounded-lg text-status-danger-600 dark:text-status-danger-400
              hover:bg-status-danger-100 dark:bg-status-danger-900/30 dark:hover:bg-status-danger-900/20
              focus:outline-none focus:ring-2 focus:ring-status-danger-500
            "
            aria-label="Clear"
          >
            <X className="w-4 h-4" aria-hidden="true" />
          </button>
        )}
      </div>

      <div className="mt-2 flex items-center gap-3">
        <input
          ref={fileInputRef}
          type="file"
          accept={accept}
          onChange={handleFile}
          disabled={!canUpload || uploading}
          className="hidden"
          id={`upload-${label.toLowerCase().replace(/\s+/g, '-')}`}
        />
        <label
          htmlFor={`upload-${label.toLowerCase().replace(/\s+/g, '-')}`}
          className={`
            inline-flex items-center gap-2
            px-3 py-1.5 rounded-lg text-sm font-medium
            border border-lsc-border dark:border-earth-700
            ${canUpload && !uploading
              ? 'text-lsc-rose hover:bg-lsc-rose/10 cursor-pointer'
              : 'text-lsc-dark/50 dark:text-lsc-cream/50 cursor-not-allowed opacity-60'}
            motion-safe:transition-colors
          `}
        >
          {uploading ? (
            <Loader2 className="w-4 h-4 motion-safe:animate-spin" aria-hidden="true" />
          ) : (
            <Upload className="w-4 h-4" aria-hidden="true" />
          )}
          {uploading ? 'Uploading...' : 'Upload file'}
        </label>
        {!canUpload && disabledHint && (
          <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
            {disabledHint}
          </span>
        )}
        {helpText && canUpload && (
          <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{helpText}</span>
        )}
      </div>

      {isImage && (
        <img
          src={value}
          alt="Visual aid preview"
          className="mt-3 max-h-40 rounded-lg border border-lsc-border dark:border-earth-700"
        />
      )}
      {isAudio && (
        <audio controls src={value} className="mt-3 w-full">
          <track kind="captions" />
        </audio>
      )}
    </div>
  );
}
