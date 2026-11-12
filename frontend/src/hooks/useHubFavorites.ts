/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { apiClient } from "@/lib/api-client";
import { useAuth } from "@/contexts/AuthContext";
import { STAFF_FAVORITES_CHANGED_EVENT } from "@/hooks/useAllHubFavorites";

interface HubFavoriteResponse {
  id: string;
  hub_slug: string;
  item_path: string;
  created_at: string;
}

interface UseHubFavoritesResult {
  favorites: Set<string>;
  isLoading: boolean;
  toggle: (itemPath: string) => Promise<void>;
  isFavorite: (itemPath: string) => boolean;
}

export function useHubFavorites(hubSlug: string): UseHubFavoritesResult {
  const { isAuthenticated } = useAuth();
  const [favorites, setFavorites] = useState<Set<string>>(() => new Set());
  const [isLoading, setIsLoading] = useState<boolean>(isAuthenticated);
  // Tracks in-flight toggles for a given itemPath to dedup rapid double-clicks.
  const inFlightRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    let cancelled = false;
    // No fetch when unauthenticated OR when no slug has been provided (e.g.
    // a NavigationHub mount without `favorites` prop calls this hook with an
    // empty slug to keep hook order stable). Backend would otherwise return
    // ALL favorites for this user since empty hub_slug bypasses the filter.
    if (!isAuthenticated || !hubSlug) {
      setFavorites(new Set());
      setIsLoading(false);
      return () => {
        cancelled = true;
      };
    }
    setIsLoading(true);
    apiClient<HubFavoriteResponse[]>("/hub-favorites", {
      method: "GET",
      params: { hub_slug: hubSlug },
    })
      .then((rows) => {
        if (cancelled) return;
        setFavorites(new Set((rows ?? []).map((r) => r.item_path)));
      })
      .catch(() => {
        if (cancelled) return;
        // Swallow load errors: the star UI just stays empty.
        setFavorites(new Set());
      })
      .finally(() => {
        if (cancelled) return;
        setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [hubSlug, isAuthenticated]);

  const isFavorite = useCallback(
    (itemPath: string) => favorites.has(itemPath),
    [favorites],
  );

  const toggle = useCallback(
    async (itemPath: string) => {
      if (!isAuthenticated) return;
      if (inFlightRef.current.has(itemPath)) return;
      inFlightRef.current.add(itemPath);

      const wasFavorite = favorites.has(itemPath);
      // Optimistic update
      setFavorites((prev) => {
        const next = new Set(prev);
        if (wasFavorite) next.delete(itemPath);
        else next.add(itemPath);
        return next;
      });

      try {
        if (wasFavorite) {
          await apiClient<null>("/hub-favorites", {
            method: "DELETE",
            body: JSON.stringify({ hub_slug: hubSlug, item_path: itemPath }),
          });
        } else {
          await apiClient<HubFavoriteResponse>("/hub-favorites", {
            method: "POST",
            body: JSON.stringify({ hub_slug: hubSlug, item_path: itemPath }),
          });
        }
        // Notify the staff sidebar's all-favorites view to refetch immediately
        // (it otherwise only refreshes on navigation). See useAllHubFavorites.
        window.dispatchEvent(new Event(STAFF_FAVORITES_CHANGED_EVENT));
      } catch {
        // Roll back
        setFavorites((prev) => {
          const next = new Set(prev);
          if (wasFavorite) next.add(itemPath);
          else next.delete(itemPath);
          return next;
        });
      } finally {
        inFlightRef.current.delete(itemPath);
      }
    },
    [favorites, hubSlug, isAuthenticated],
  );

  return useMemo(
    () => ({ favorites, isLoading, toggle, isFavorite }),
    [favorites, isLoading, toggle, isFavorite],
  );
}

export default useHubFavorites;
