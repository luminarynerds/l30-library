/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from "react";
import { ExternalLink, Loader2, Video } from "lucide-react";

interface MeetingRecordingPlayerProps {
  recordingUrl: string | null | undefined;
}

function getYouTubeEmbedUrl(url: string): string | null {
  // Match youtube.com/watch?v=VIDEO_ID
  const watchMatch = url.match(/youtube\.com\/watch\?.*v=([a-zA-Z0-9_-]+)/);
  if (watchMatch) {
    return `https://www.youtube.com/embed/${watchMatch[1]}`;
  }
  // Match youtu.be/VIDEO_ID
  const shortMatch = url.match(/youtu\.be\/([a-zA-Z0-9_-]+)/);
  if (shortMatch) {
    return `https://www.youtube.com/embed/${shortMatch[1]}`;
  }
  return null;
}

function getVimeoEmbedUrl(url: string): string | null {
  // Match vimeo.com/VIDEO_ID
  const match = url.match(/vimeo\.com\/(\d+)/);
  if (match) {
    return `https://player.vimeo.com/video/${match[1]}`;
  }
  return null;
}

type VideoSourceType = "youtube" | "vimeo" | "direct" | "external";

function detectSourceType(url: string): VideoSourceType {
  if (url.match(/youtube\.com\/watch/) || url.match(/youtu\.be\//)) {
    return "youtube";
  }
  if (url.match(/vimeo\.com\//)) {
    return "vimeo";
  }
  if (url.match(/\.(mp4|webm|ogg)(\?|$)/i)) {
    return "direct";
  }
  return "external";
}

export default function MeetingRecordingPlayer({ recordingUrl }: MeetingRecordingPlayerProps) {
  const [iframeLoaded, setIframeLoaded] = useState(false);

  if (!recordingUrl) {
    return null;
  }

  const sourceType = detectSourceType(recordingUrl);

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow p-6">
      <div className="flex items-center gap-2 mb-4">
        <Video className="h-5 w-5 text-lsc-rose" />
        <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
          Meeting Recording
        </h2>
      </div>

      {sourceType === "youtube" && (() => {
        const embedUrl = getYouTubeEmbedUrl(recordingUrl);
        if (!embedUrl) return null;
        return (
          <div className="relative w-full" style={{ paddingBottom: "56.25%" }}>
            {!iframeLoaded && (
              <div className="absolute inset-0 flex items-center justify-center bg-earth-100 dark:bg-earth-800 rounded-lg">
                <Loader2 className="w-8 h-8 motion-safe:animate-spin text-earth-600" />
              </div>
            )}
            <iframe
              className="absolute inset-0 w-full h-full rounded-lg"
              src={embedUrl}
              title="Meeting Recording"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
              onLoad={() => setIframeLoaded(true)}
            />
          </div>
        );
      })()}

      {sourceType === "vimeo" && (() => {
        const embedUrl = getVimeoEmbedUrl(recordingUrl);
        if (!embedUrl) return null;
        return (
          <div className="relative w-full" style={{ paddingBottom: "56.25%" }}>
            {!iframeLoaded && (
              <div className="absolute inset-0 flex items-center justify-center bg-earth-100 dark:bg-earth-800 rounded-lg">
                <Loader2 className="w-8 h-8 motion-safe:animate-spin text-earth-600" />
              </div>
            )}
            <iframe
              className="absolute inset-0 w-full h-full rounded-lg"
              src={embedUrl}
              title="Meeting Recording"
              allow="autoplay; fullscreen; picture-in-picture"
              allowFullScreen
              onLoad={() => setIframeLoaded(true)}
            />
          </div>
        );
      })()}

      {sourceType === "direct" && (
        <video
          className="w-full rounded-lg"
          controls
          preload="metadata"
        >
          <source src={recordingUrl} />
          Your browser does not support the video tag.
        </video>
      )}

      {sourceType === "external" && (
        <div className="flex flex-col items-center justify-center py-8 gap-4 bg-lsc-cream dark:bg-earth-700 rounded-lg">
          <Video className="h-12 w-12 text-lsc-dark/70 dark:text-lsc-cream/70" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm text-center">
            This recording is hosted on an external platform.
          </p>
          <a
            href={recordingUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose/90 transition-colors text-sm font-medium"
          >
            <ExternalLink className="h-4 w-4" />
            Open Recording
          </a>
        </div>
      )}
    </div>
  );
}
