/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Regression tests for theme CSS load failure handling.
 *
 * What this guards against: loadTheme resolving silently when the stylesheet
 * 404s (stale hashed asset in a tab that predates a deploy). The patron
 * enables dyslexia font or colorblind mode, the class lands on <html>, and
 * nothing visibly changes. Policy mirrors lazyWithRetry: retry once, then a
 * loop-guarded hard reload to pick up the new asset manifest.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { RELOAD_LOOP_WINDOW_MS } from '../lazyWithRetry';

type LinkStub = HTMLLinkElement & {
  onload: (() => void) | null;
  onerror: (() => void) | null;
};

// themeLoader keeps module-level loaded/loading singletons, so each test
// imports a fresh copy to avoid cross-test short-circuits.
let loadTheme: (theme: string) => Promise<void>;

let createdLinks: LinkStub[] = [];
function createdLink(index: number): LinkStub {
  const link = createdLinks[index];
  if (!link) throw new Error(`Expected theme stylesheet link ${index} to exist`);
  return link;
}

let reloadSpy: ReturnType<typeof vi.fn>;
const realCreateElement = document.createElement.bind(document);

function createdLink(index: number): LinkStub {
  const link = createdLinks[index];
  if (!link) {
    throw new Error(`Expected stylesheet link at index ${index}`);
  }
  return link;
}

beforeEach(async () => {
  vi.resetModules();
  ({ loadTheme } = await import('../themeLoader'));
  createdLinks = [];
  // Drive link events explicitly without happy-dom starting real stylesheet requests.
  vi.spyOn(document.head, 'appendChild').mockImplementation(<T extends Node>(node: T) => node);
  vi.spyOn(document, 'createElement').mockImplementation((tag: string) => {
    const el = realCreateElement(tag) as LinkStub;
    if (tag === 'link') {
      createdLinks.push(el);
    }
    return el;
  });
  reloadSpy = vi.fn();
  vi.stubGlobal('location', { ...window.location, reload: reloadSpy });
  window.sessionStorage.clear();
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  document
    .querySelectorAll('link[data-theme]')
    .forEach((link) => link.remove());
  window.sessionStorage.clear();
});

describe('loadTheme failure handling', () => {
  it('retries once when the stylesheet fails to load', async () => {
    const promise = loadTheme('colorblind');
    expect(createdLinks.length).toBe(1);

    createdLink(0).onerror?.();
    await Promise.resolve();
    expect(createdLinks.length).toBe(2);

    createdLink(1).onload?.();
    await promise;
  });

  it('reloads the page (loop-guarded) when the retry also fails', async () => {
    const promise = loadTheme('neuro-inclusive');
    createdLink(0).onerror?.();
    await Promise.resolve();
    createdLink(1).onerror?.();
    await promise;

    expect(reloadSpy).toHaveBeenCalledTimes(1);
  });

  it('does not reload again inside the loop window', async () => {
    const first = loadTheme('neuro-inclusive');
    createdLink(0).onerror?.();
    await Promise.resolve();
    createdLink(1).onerror?.();
    await first;
    expect(reloadSpy).toHaveBeenCalledTimes(1);

    // Second failing load right away: within RELOAD_LOOP_WINDOW_MS the
    // asset is genuinely gone; reloading again would loop.
    const second = loadTheme('colorblind');
    createdLink(2).onerror?.();
    await Promise.resolve();
    createdLink(3).onerror?.();
    await second;
    expect(reloadSpy).toHaveBeenCalledTimes(1);
    expect(RELOAD_LOOP_WINDOW_MS).toBeGreaterThan(0);
  });

  it('control: a successful load creates one link and never reloads', async () => {
    const promise = loadTheme('colorblind');
    expect(createdLinks.length).toBe(1);
    createdLink(0).onload?.();
    await promise;

    expect(createdLinks.length).toBe(1);
    expect(reloadSpy).not.toHaveBeenCalled();
  });
});
