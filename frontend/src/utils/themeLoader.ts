/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { shouldReloadAfterChunkError } from './lazyWithRetry'
/**
 * Theme Loader
 *
 * Dynamically loads theme CSS files to reduce initial bundle size.
 * Uses a singleton pattern to prevent duplicate loading.
 *
 * Load failures follow the lazyWithRetry policy: retry once (transient
 * network), then a loop-guarded hard reload (stale hashed asset in a tab
 * that predates a deploy — the old URL 404s forever and only a reload gets
 * the new manifest). Without this, enabling e.g. dyslexia font in a stale
 * tab put the class on <html> with no stylesheet behind it: a silent no-op.
 */

const RELOAD_STORAGE_KEY = 'lazy-retry:theme-css';

// Track loaded themes to prevent duplicate loading
const loadedThemes = new Set<string>();
const loadingThemes = new Map<string, Promise<void>>();

// Theme file mappings
const THEME_FILES: Record<string, string> = {
  'neuro-inclusive': new URL('../styles/neuro-inclusive.css', import.meta.url).href,
  'colorblind': new URL('../styles/colorblind.css', import.meta.url).href,
};

export async function loadTheme(theme: string): Promise<void> {
  // Already loaded
  if (loadedThemes.has(theme)) {
    return Promise.resolve();
  }

  // Currently loading - return existing promise
  if (loadingThemes.has(theme)) {
    return loadingThemes.get(theme)!;
  }

  const themePath = THEME_FILES[theme];
  if (!themePath) {
    Sentry.captureMessage(`Unknown theme: ${theme}`, 'warning');
    return Promise.resolve();
  }

  // Create loading promise
  const loadPromise = new Promise<void>((resolve, _reject) => {
    // Check if already loaded via link tag
    const existingLink = document.querySelector(`link[data-theme="${theme}"]`);
    if (existingLink) {
      loadedThemes.add(theme);
      resolve();
      return;
    }

    const attach = (attempt: number): void => {
      const link = document.createElement('link');
      link.rel = 'stylesheet';
      link.href = themePath;
      link.dataset.theme = theme;

      link.onload = () => {
        loadedThemes.add(theme);
        loadingThemes.delete(theme);
        resolve();
      };

      link.onerror = () => {
        link.remove();
        if (attempt === 0) {
          // quick retry for transient network hiccups
          attach(1);
          return;
        }

        loadingThemes.delete(theme);
        Sentry.captureMessage(`Failed to load theme: ${theme}`, 'warning');
        if (
          typeof window !== 'undefined' &&
          shouldReloadAfterChunkError(window.sessionStorage, RELOAD_STORAGE_KEY)
        ) {
          window.location.reload();
        }
        // Don't reject - theme CSS is optional, and after a reload-guard
        // hit there is nothing more to do this page-life.
        resolve();
      };

      document.head.appendChild(link);
    };

    attach(0);
  });

  loadingThemes.set(theme, loadPromise);
  return loadPromise;
}

export async function applyTheme(theme: string): Promise<void> {
  await loadTheme(theme);

  // Remove existing theme classes
  const themeClasses = Object.keys(THEME_FILES).map((t) => `theme-${t}`);
  document.documentElement.classList.remove(...themeClasses);

  // Add new theme class
  if (theme !== 'default') {
    document.documentElement.classList.add(`theme-${theme}`);
  }
}

export function preloadThemes(themes: string[]): void {
  themes.forEach((theme) => {
    // Use requestIdleCallback for non-critical loading
    if ('requestIdleCallback' in window) {
      (window as unknown as { requestIdleCallback: (callback: () => void) => void }).requestIdleCallback(() => loadTheme(theme));
    } else {
      setTimeout(() => loadTheme(theme), 100);
    }
  });
}

export function unloadTheme(theme: string): void {
  const link = document.querySelector(`link[data-theme="${theme}"]`);
  if (link) {
    link.remove();
    loadedThemes.delete(theme);
  }
}

export function isThemeLoaded(theme: string): boolean {
  return loadedThemes.has(theme);
}

export function getLoadedThemes(): string[] {
  return Array.from(loadedThemes);
}
