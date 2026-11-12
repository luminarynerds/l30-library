/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Global Bionic Reading Effect
 *
 * When bionic reading is enabled, this component processes visible text nodes
 * in the main content area, wrapping the first portion of each word in
 * bionic-bold spans. Uses MutationObserver to handle dynamic content.
 *
 * Only processes text inside <main> to avoid breaking UI elements.
 */

import { useEffect, useRef } from "react";
import { useUnifiedAccessibility } from "../hooks/useUnifiedAccessibility";

const COMMON_SHORT_WORDS = new Set([
  "a", "an", "the", "is", "it", "to", "of", "in", "on", "at",
  "by", "or", "and", "but", "if", "as", "be", "we", "he", "she",
]);

const MIN_WORD_LENGTH = 3;
const FIXATION_STRENGTH = 0.4;
const PROCESSED_ATTR = "data-bionic";

function calculateFixation(len: number): number {
  if (len <= 1) return 1;
  if (len <= 3) return 1;
  if (len <= 6) return Math.ceil(len * FIXATION_STRENGTH);
  if (len <= 9) return Math.ceil(len * FIXATION_STRENGTH * 0.9);
  return Math.ceil(len * FIXATION_STRENGTH * 0.8);
}

function processTextNode(node: Text): DocumentFragment | null {
  const text = node.textContent;
  if (!text || !text.trim()) return null;

  const frag = document.createDocumentFragment();
  const words = text.split(/(\s+)/);
  let changed = false;

  for (const word of words) {
    if (/^\s+$/.test(word)) {
      frag.appendChild(document.createTextNode(word));
      continue;
    }

    const match = word.match(/^([^a-zA-Z]*)([a-zA-Z]+)([^a-zA-Z]*)$/);
    if (!match || match[2]!.length < MIN_WORD_LENGTH || COMMON_SHORT_WORDS.has(match[2]!.toLowerCase())) {
      frag.appendChild(document.createTextNode(word));
      continue;
    }

    const [, lead = "", letters = "", trail = ""] = match;
    const fix = calculateFixation(letters.length);
    const boldPart = lead + letters.slice(0, fix);
    const lightPart = letters.slice(fix) + trail;

    const boldSpan = document.createElement("span");
    boldSpan.className = "bionic-bold";
    boldSpan.textContent = boldPart;

    const lightSpan = document.createElement("span");
    lightSpan.className = "bionic-light";
    lightSpan.textContent = lightPart;

    frag.appendChild(boldSpan);
    frag.appendChild(lightSpan);
    changed = true;
  }

  return changed ? frag : null;
}

function processElement(el: Element): void {
  if (el.getAttribute(PROCESSED_ATTR)) return;

  // Skip interactive/structural elements
  const tag = el.tagName.toLowerCase();
  if (["script", "style", "code", "pre", "input", "textarea", "select", "button", "a", "svg"].includes(tag)) return;

  const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, {
    acceptNode: (node) => {
      const parent = node.parentElement;
      if (!parent) return NodeFilter.FILTER_REJECT;
      const ptag = parent.tagName.toLowerCase();
      if (["script", "style", "code", "pre", "input", "textarea", "select", "button", "svg"].includes(ptag)) {
        return NodeFilter.FILTER_REJECT;
      }
      if (parent.getAttribute(PROCESSED_ATTR)) return NodeFilter.FILTER_REJECT;
      return node.textContent && node.textContent.trim() ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
    },
  });

  const textNodes: Text[] = [];
  let current = walker.nextNode();
  while (current) {
    textNodes.push(current as Text);
    current = walker.nextNode();
  }

  for (const textNode of textNodes) {
    const frag = processTextNode(textNode);
    if (frag && textNode.parentNode) {
      const wrapper = document.createElement("span");
      wrapper.setAttribute(PROCESSED_ATTR, "1");
      wrapper.appendChild(frag);
      textNode.parentNode.replaceChild(wrapper, textNode);
    }
  }

  el.setAttribute(PROCESSED_ATTR, "1");
}

function cleanBionic(el: Element): void {
  const processed = el.querySelectorAll(`[${PROCESSED_ATTR}]`);
  processed.forEach((node) => {
    const text = node.textContent || "";
    const textNode = document.createTextNode(text);
    node.parentNode?.replaceChild(textNode, node);
  });
  el.removeAttribute(PROCESSED_ATTR);
}

export function BionicReadingGlobal() {
  const { settings } = useUnifiedAccessibility();
  const observerRef = useRef<MutationObserver | null>(null);

  useEffect(() => {
    if (!settings.bionicReading) {
      // Clean up
      const main = document.querySelector("main");
      if (main) cleanBionic(main);
      observerRef.current?.disconnect();
      return;
    }

    const applyToMain = () => {
      const main = document.querySelector("main");
      if (!main) return;

      // Process existing content
      const contentEls = main.querySelectorAll("p, li, td, dd, blockquote, h1, h2, h3, h4, h5, h6, figcaption, .prose");
      contentEls.forEach(processElement);
    };

    // Initial application (slight delay for React renders)
    const timer = setTimeout(applyToMain, 100);

    // Watch for new content
    observerRef.current = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        for (const node of mutation.addedNodes) {
          if (node instanceof Element && !node.getAttribute(PROCESSED_ATTR)) {
            const contentEls = node.querySelectorAll("p, li, td, dd, blockquote, h1, h2, h3, h4, h5, h6, figcaption, .prose");
            contentEls.forEach(processElement);
            if (["P", "LI", "TD", "DD", "BLOCKQUOTE", "H1", "H2", "H3", "H4", "H5", "H6", "FIGCAPTION"].includes(node.tagName)) {
              processElement(node);
            }
          }
        }
      }
    });

    const main = document.querySelector("main");
    if (main) {
      observerRef.current.observe(main, { childList: true, subtree: true });
    }

    return () => {
      clearTimeout(timer);
      observerRef.current?.disconnect();
    };
  }, [settings.bionicReading]);

  return null;
}

export default BionicReadingGlobal;
