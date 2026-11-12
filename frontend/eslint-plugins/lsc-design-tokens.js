/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * ESLint Plugin: lsc-design-tokens
 *
 * Enforces the LSC design token scale across all components and pages.
 * The canonical token definitions live in tailwind.config.js.
 *
 * Rules:
 *   lsc-design-tokens/no-banned-tokens
 *     Flags usage of gray, slate, stone, zinc, neutral color families,
 *     rounded-md/2xl/3xl, shadow-xl/2xl in JSX className strings.
 *
 *   lsc-design-tokens/no-low-contrast-text
 *     Flags text-earth-400 and text-earth-500 which fail or barely pass
 *     WCAG AA contrast requirements on light backgrounds.
 *
 *   lsc-design-tokens/no-unresolvable-color-token
 *     Flags colour classes whose token or shade does not exist, because
 *     Tailwind emits NO CSS for them at all. See the rule's own comment.
 */

// ── Banned patterns with their replacements ───────────────────

// All Tailwind gray families → earth-*
const BANNED_GRAY_FAMILIES = ['gray', 'slate', 'stone', 'zinc', 'neutral'];
const SHADE_STEPS = ['50', '100', '200', '300', '400', '500', '600', '700', '800', '900', '950'];

const BANNED_COLORS = BANNED_GRAY_FAMILIES.flatMap((family) =>
  SHADE_STEPS.map((shade) => ({
    pattern: new RegExp(`\b${family}-${shade}\b`, 'g'),
    replacement: `earth-${shade}`,
  }))
);

const BANNED_RADII = [
  { pattern: /\brounded-md\b/g, replacement: 'rounded-lg' },
  { pattern: /\brounded-2xl\b/g, replacement: 'rounded-xl' },
  { pattern: /\brounded-3xl\b/g, replacement: 'rounded-xl' },
];

const BANNED_SHADOWS = [
  { pattern: /\bshadow-xl\b/g, replacement: 'shadow-lg' },
  { pattern: /\bshadow-2xl\b/g, replacement: 'shadow-lg' },
];

const ALL_BANNED = [...BANNED_COLORS, ...BANNED_RADII, ...BANNED_SHADOWS];

// ── Helper: check a string literal for banned tokens ──────────

function checkStringForBannedTokens(context, node, value) {
  for (const { pattern, replacement } of ALL_BANNED) {
    // Reset regex lastIndex for global patterns
    pattern.lastIndex = 0;
    const match = pattern.exec(value);
    if (match) {
      const token = match[0];
      let category;
      if (token.startsWith('rounded-')) category = 'border-radius';
      else if (token.startsWith('shadow-')) category = 'shadow';
      else category = 'color';

      context.report({
        node,
        message: `Banned design token "{{ token }}" ({{ category }}). Use "{{ replacement }}" instead. See tailwind.config.js.`,
        data: { token, category, replacement },
      });
    }
  }
}

// ── Rule definition ───────────────────────────────────────────

const noBannedTokensRule = {
  meta: {
    type: 'problem',
    docs: {
      description: 'Disallow banned design tokens (gray/slate/stone/zinc/neutral-*, rounded-md/2xl/3xl, shadow-xl/2xl)',
      category: 'Design System',
      recommended: true,
    },
    schema: [],
    messages: {},
  },
  create(context) {
    return {
      // Check className="..." string literals
      JSXAttribute(node) {
        if (node.name.name !== 'className') return;

        // className="literal string"
        if (node.value && node.value.type === 'Literal' && typeof node.value.value === 'string') {
          checkStringForBannedTokens(context, node.value, node.value.value);
        }
      },

      // Check string literals inside template literals and expressions
      // e.g., className={`bg-gray-100 ${...}`} or className={condition ? 'bg-gray-100' : '...'}
      Literal(node) {
        if (typeof node.value !== 'string') return;

        // Only check strings that look like they contain Tailwind classes
        const hasClassLikeContent = /\b(bg-|text-|border-|divide-|ring-|placeholder-|shadow-|rounded-|hover:|dark:|focus:|active:)/.test(node.value);
        if (!hasClassLikeContent) return;

        // Check if we're inside a className context
        const ancestors = context.getAncestors ? context.getAncestors() : context.sourceCode.getAncestors(node);
        const isInClassName = ancestors.some(
          (ancestor) =>
            ancestor.type === 'JSXAttribute' && ancestor.name && ancestor.name.name === 'className'
        );
        const isInClassnameCall = ancestors.some(
          (ancestor) =>
            ancestor.type === 'CallExpression' &&
            ancestor.callee &&
            (ancestor.callee.name === 'clsx' || ancestor.callee.name === 'cn' || ancestor.callee.name === 'twMerge')
        );

        if (isInClassName || isInClassnameCall) {
          checkStringForBannedTokens(context, node, node.value);
        }
      },

      // Check template literal parts: className={`bg-gray-100 ...`}
      TemplateLiteral(node) {
        const ancestors = context.getAncestors ? context.getAncestors() : context.sourceCode.getAncestors(node);
        const isInClassName = ancestors.some(
          (ancestor) =>
            ancestor.type === 'JSXAttribute' && ancestor.name && ancestor.name.name === 'className'
        );
        const isInClassnameCall = ancestors.some(
          (ancestor) =>
            ancestor.type === 'CallExpression' &&
            ancestor.callee &&
            (ancestor.callee.name === 'clsx' || ancestor.callee.name === 'cn' || ancestor.callee.name === 'twMerge')
        );

        if (!isInClassName && !isInClassnameCall) return;

        for (const quasi of node.quasis) {
          if (quasi.value && quasi.value.raw) {
            checkStringForBannedTokens(context, quasi, quasi.value.raw);
          }
        }
      },
    };
  },
};

// ── Rule: no-low-contrast-text ────────────────────────────────
// Flags text-earth-400 (2.6:1) and text-earth-500 (4.2:1) which fail or
// barely pass WCAG AA on light backgrounds.  Suggests earth-600 (6.0:1).

const LOW_CONTRAST_TEXT = [
  { pattern: /(?<!dark:|placeholder:)\btext-earth-400\b/g, ratio: '2.6:1', replacement: 'text-earth-600' },
  { pattern: /(?<!dark:|placeholder:)\btext-earth-500\b/g, ratio: '4.2:1', replacement: 'text-earth-600' },
];

function checkStringForLowContrastText(context, node, value) {
  for (const { pattern, ratio, replacement } of LOW_CONTRAST_TEXT) {
    pattern.lastIndex = 0;
    const match = pattern.exec(value);
    if (match) {
      context.report({
        node,
        message: `Low-contrast text token "{{ token }}" ({{ ratio }} on white). Use "{{ replacement }}" (6.0:1) or darker for WCAG AA compliance.`,
        data: { token: match[0], ratio, replacement },
      });
    }
  }
}

const noLowContrastTextRule = {
  meta: {
    type: 'suggestion',
    docs: {
      description: 'Warn on text color tokens that fail WCAG AA contrast on light backgrounds',
      category: 'Accessibility',
      recommended: true,
    },
    schema: [],
    messages: {},
  },
  create(context) {
    return {
      JSXAttribute(node) {
        if (node.name.name !== 'className') return;
        if (node.value && node.value.type === 'Literal' && typeof node.value.value === 'string') {
          checkStringForLowContrastText(context, node.value, node.value.value);
        }
      },

      Literal(node) {
        if (typeof node.value !== 'string') return;
        if (!/\btext-earth-[45]00\b/.test(node.value)) return;

        const ancestors = context.getAncestors ? context.getAncestors() : context.sourceCode.getAncestors(node);
        const isInClassName = ancestors.some(
          (a) => a.type === 'JSXAttribute' && a.name && a.name.name === 'className'
        );
        const isInClassnameCall = ancestors.some(
          (a) =>
            a.type === 'CallExpression' &&
            a.callee &&
            (a.callee.name === 'clsx' || a.callee.name === 'cn' || a.callee.name === 'twMerge')
        );

        if (isInClassName || isInClassnameCall) {
          checkStringForLowContrastText(context, node, node.value);
        }
      },

      TemplateLiteral(node) {
        const ancestors = context.getAncestors ? context.getAncestors() : context.sourceCode.getAncestors(node);
        const isInClassName = ancestors.some(
          (a) => a.type === 'JSXAttribute' && a.name && a.name.name === 'className'
        );
        const isInClassnameCall = ancestors.some(
          (a) =>
            a.type === 'CallExpression' &&
            a.callee &&
            (a.callee.name === 'clsx' || a.callee.name === 'cn' || a.callee.name === 'twMerge')
        );

        if (!isInClassName && !isInClassnameCall) return;

        for (const quasi of node.quasis) {
          if (quasi.value && quasi.value.raw) {
            checkStringForLowContrastText(context, quasi, quasi.value.raw);
          }
        }
      },
    };
  },
};

// ── Rule: no-hardcoded-page-width ─────────────────────────────
// Flags hand-rolled page-root width wrappers (max-w-{2..7}xl + mx-auto + px-4).
// Use <PageContainer width="…"> or StandardPageLayout so the content width
// stays in one place (src/components/layout/page-width.ts) and can't drift.

const PAGE_WIDTH_WRAPPER = /max-w-(?:2xl|3xl|4xl|5xl|6xl|7xl)\b/;

function checkStringForPageWidth(context, node, value) {
  if (
    PAGE_WIDTH_WRAPPER.test(value) &&
    /\bmx-auto\b/.test(value) &&
    /\bpx-4\b/.test(value) &&
    !/\bflex\b/.test(value) &&
    !/\bcontainer\b/.test(value)
  ) {
    context.report({
      node,
      message:
        'Hardcoded page width. Use <PageContainer width="…"> or StandardPageLayout instead of max-w-*xl mx-auto on a page root. See src/components/layout/page-width.ts.',
    });
  }
}

const noHardcodedPageWidthRule = {
  meta: {
    type: 'suggestion',
    docs: {
      description: 'Disallow hardcoded page-root content widths; use PageContainer/StandardPageLayout',
      category: 'Design System',
      recommended: true,
    },
    schema: [],
    messages: {},
  },
  create(context) {
    // Page-root widths only live in src/pages/**; chrome components legitimately set widths.
    const fn = context.filename || (context.getFilename && context.getFilename()) || '';
    if (!/[\\/]pages[\\/]/.test(fn)) return {};
    function inClassName(node) {
      const ancestors = context.getAncestors ? context.getAncestors() : context.sourceCode.getAncestors(node);
      return ancestors.some(
        (a) =>
          (a.type === 'JSXAttribute' && a.name && a.name.name === 'className') ||
          (a.type === 'CallExpression' &&
            a.callee &&
            (a.callee.name === 'clsx' || a.callee.name === 'cn' || a.callee.name === 'twMerge'))
      );
    }
    return {
      JSXAttribute(node) {
        if (node.name.name !== 'className') return;
        if (node.value && node.value.type === 'Literal' && typeof node.value.value === 'string') {
          checkStringForPageWidth(context, node.value, node.value.value);
        }
      },
      Literal(node) {
        if (typeof node.value !== 'string') return;
        if (!PAGE_WIDTH_WRAPPER.test(node.value)) return;
        if (inClassName(node)) checkStringForPageWidth(context, node, node.value);
      },
      TemplateLiteral(node) {
        if (!inClassName(node)) return;
        for (const quasi of node.quasis) {
          if (quasi.value && quasi.value.raw) {
            checkStringForPageWidth(context, quasi, quasi.value.raw);
          }
        }
      },
    };
  },
};

// ── Rule: no-unresolvable-color-token ─────────────────────────
//
// Tailwind emits NO CSS AT ALL for a colour class whose token or shade is not
// defined. That failure is silent, and it is worse than it sounds: when the
// dead class is a `dark:` override, the light base class beside it stays
// applied in dark mode. `bg-category-50 dark:bg-category-950/30` rendered a
// near-white panel in dark mode because the `category` scale stopped at 900,
// putting #e9d5ff text on #faf5ff -- 1.27:1 against a 4.5:1 floor.
//
// Neither sibling rule can catch this. Both pattern-match a fixed list of
// banned names and never read tailwind.config.js, so they cannot know which
// scales or shades actually exist. This rule reads the config.
//
// A sweep in 2026-07 found 113 such classes across 436 usages.

import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const TAILWIND_CONFIG = resolve(
  dirname(fileURLToPath(import.meta.url)),
  '../tailwind.config.js',
);

// Stock Tailwind palettes stay available through `extend`, so they are valid
// even though they never appear in our config.
const STOCK_SCALES = [
  'slate', 'gray', 'zinc', 'neutral', 'stone', 'red', 'orange', 'amber',
  'yellow', 'lime', 'green', 'emerald', 'teal', 'cyan', 'sky', 'blue',
  'indigo', 'violet', 'purple', 'fuchsia', 'pink', 'rose',
];
const STOCK_SHADES = new Set([...SHADE_STEPS]);
const BARE_COLORS = new Set(['black', 'white', 'transparent', 'current', 'inherit', 'none']);

// Utilities whose value is a colour. Each also has non-colour forms that must
// not be treated as tokens (text-lg, border-2, from-50%, divide-y...).
// Longest first: `ring-offset-earth-950` must match `ring-offset`, not `ring`,
// or the remainder parses as scale "offset-earth" and looks unresolvable.
const COLOR_PREFIXES = [
  'bg', 'text', 'border', 'ring', 'ring-offset', 'divide', 'placeholder',
  'outline', 'decoration', 'fill', 'stroke', 'accent', 'caret', 'shadow',
  'from', 'to', 'via',
  // border-{side}-{colour} is a real utility: border-l-green-500
  'border-t', 'border-r', 'border-b', 'border-l', 'border-x', 'border-y',
  'border-s', 'border-e',
].sort((a, b) => b.length - a.length);
const NON_COLOR_VALUES = new Set([
  'xs', 'sm', 'base', 'md', 'lg', 'xl', '2xl', '3xl', '4xl', '5xl', '6xl',
  '7xl', '8xl', '9xl', 'left', 'center', 'right', 'justify', 'start', 'end',
  'wrap', 'nowrap', 'balance', 'pretty', 'ellipsis', 'clip', 'solid', 'dashed',
  'dotted', 'double', 'hidden', 'inner', 'x', 'y', 'auto', 't', 'r', 'b', 'l',
]);

let paletteCache = null;

/** Parse tailwind.config.js text for scale names, their shades, and flat tokens.
 *  `values` additionally records literal hex values where a scale has them, so
 *  the contrast rule below can actually resolve a colour. Scales defined as
 *  rgb(var(--x) / <alpha-value>) are theme-dependent and deliberately absent
 *  from `values` -- they cannot be resolved without a running browser. */
function loadPalette() {
  if (paletteCache) return paletteCache;
  const scales = new Map();
  const values = new Map();
  const flat = new Set();
  let src = '';
  try {
    src = readFileSync(TAILWIND_CONFIG, 'utf8');
  } catch {
    // Config unreadable -> disable the rule rather than flag everything.
    paletteCache = { scales, values, flat, usable: false };
    return paletteCache;
  }

  // `name: { 50: '#..', ... }` and `'quoted-name': { ... }`
  const blockRe = /(?:'([\w-]+)'|"([\w-]+)"|([A-Za-z][\w-]*))\s*:\s*\{([^{}]*)\}/g;
  for (let m; (m = blockRe.exec(src)); ) {
    const name = m[1] || m[2] || m[3];
    const shades = new Set();
    for (const s of m[4].matchAll(/(?:^|[,{\s])(?:'|")?(\d{2,3}|DEFAULT)(?:'|")?\s*:/g)) {
      shades.add(s[1]);
    }
    if (shades.size) {
      const prev = scales.get(name) || new Set();
      for (const s of shades) prev.add(s);
      scales.set(name, prev);
      // literal hex values only -- var()-based scales stay unresolved
      const hexes = values.get(name) || new Map();
      for (const h of m[4].matchAll(/(?:'|")?(\d{2,3})(?:'|")?\s*:\s*(?:'|")(#[0-9a-fA-F]{6})(?:'|")/g)) {
        hexes.set(h[1], h[2].toLowerCase());
      }
      if (hexes.size) values.set(name, hexes);
    }
  }
  // `'lsc-rose': 'rgb(...)'` -- single-value tokens
  for (const m of src.matchAll(/(?:'([\w-]+)'|"([\w-]+)")\s*:\s*(?:'|")[^'"]*(?:'|")\s*,/g)) {
    flat.add(m[1] || m[2]);
  }
  for (const name of STOCK_SCALES) {
    const prev = scales.get(name) || new Set();
    for (const s of STOCK_SHADES) prev.add(s);
    scales.set(name, prev);
  }
  paletteCache = { scales, values, flat, usable: scales.size > 0 };
  return paletteCache;
}

/**
 * Does this class resolve to a real colour?
 * Returns null when the token is not a colour class at all (so: not our
 * business), true when it resolves, false when it emits nothing.
 */
function resolvesToColor(token, palette) {
  let t = token;
  // strip variants (dark:, hover:, group-hover:, ...) and the ! modifier
  const parts = t.split(':');
  t = parts[parts.length - 1].replace(/^!/, '');
  // arbitrary values are opaque to us
  if (t.includes('[') || t.includes(']')) return null;
  // strip an opacity modifier, remembering that there was one
  const slash = t.indexOf('/');
  const hasOpacity = slash !== -1;
  if (hasOpacity) t = t.slice(0, slash);

  const prefix = COLOR_PREFIXES.find(
    (p) => t.startsWith(`${p}-`) && t.length > p.length + 1,
  );
  if (!prefix) return null;
  let rest = t.slice(prefix.length + 1);
  if (!rest) return null;
  // non-colour forms of the same prefix
  if (NON_COLOR_VALUES.has(rest)) return null;
  if (/^\d+(\.\d+)?$/.test(rest) || /^\d+%$/.test(rest)) return null;
  // legacy opacity/blend utilities share these prefixes: bg-opacity-50
  if (/^(opacity|blend|clip|origin|repeat|size|position)-/.test(rest)) return null;
  // currentColor has no alpha channel, so `bg-current/20` emits nothing even
  // though `bg-current` is perfectly valid.
  if (rest === 'current') return !hasOpacity;
  if (BARE_COLORS.has(rest)) return true;

  const { scales, flat } = palette;
  if (flat.has(rest)) return true;
  if (scales.has(rest)) return scales.get(rest).has('DEFAULT');

  const dash = rest.lastIndexOf('-');
  if (dash === -1) return null; // single unknown word -- probably not a token
  const scale = rest.slice(0, dash);
  const shade = rest.slice(dash + 1);
  if (!/^\d{2,3}$/.test(shade)) {
    // e.g. lsc-rose-light -- only a token if declared flat, else not ours
    return flat.has(rest) ? true : null;
  }
  // A numeric 2-3 digit shade after a colour-utility prefix is unambiguously
  // an attempt at a colour class, so an unknown scale here is a real error
  // (bg-accent-600, text-status-error-700) rather than an unrelated string.
  if (!scales.has(scale)) return false;
  return scales.get(scale).has(shade);
}

/** Only analyse strings that look like class lists (>=2 utility-ish tokens). */
function looksLikeClassList(value) {
  const toks = value.trim().split(/\s+/).filter(Boolean);
  if (toks.length >= 2) return true;
  return false;
}

function checkClassString(context, node, value) {
  const palette = loadPalette();
  if (!palette.usable) return;
  if (!looksLikeClassList(value)) return;
  for (const token of value.split(/\s+/)) {
    if (!token) continue;
    if (resolvesToColor(token, palette) === false) {
      context.report({
        node,
        messageId: 'unresolvable',
        data: { token },
      });
    }
  }
}

const noUnresolvableColorTokenRule = {
  meta: {
    type: 'problem',
    docs: {
      description:
        'Disallow colour classes whose token or shade is not defined in tailwind.config.js, because Tailwind emits no CSS for them',
      category: 'Design System',
      recommended: true,
    },
    schema: [],
    messages: {
      unresolvable:
        '"{{ token }}" resolves to no colour in tailwind.config.js, so Tailwind emits NO CSS for it. If this is a dark: override, the light class beside it will stay applied in dark mode. Add the shade to the config or use an existing token.',
    },
  },
  create(context) {
    return {
      JSXAttribute(node) {
        if (!node.name || (node.name.name !== 'className' && node.name.name !== 'class')) return;
        if (node.value && node.value.type === 'Literal' && typeof node.value.value === 'string') {
          checkClassString(context, node.value, node.value.value);
        }
      },
      Literal(node) {
        if (typeof node.value !== 'string') return;
        // the JSXAttribute visitor already covered className="..."
        if (node.parent && node.parent.type === 'JSXAttribute') return;
        checkClassString(context, node, node.value);
      },
      TemplateLiteral(node) {
        for (const quasi of node.quasis) {
          if (quasi.value && quasi.value.raw) {
            checkClassString(context, quasi, quasi.value.raw);
          }
        }
      },
    };
  },
};

// ── Rule: no-low-contrast-pair ────────────────────────────────
//
// no-low-contrast-text only knows two hardcoded classes and explicitly skips
// anything `dark:`-prefixed, so a dark-mode pair that fails AA sails through.
// That is how `dark:bg-earth-700` beside `dark:text-earth-400` shipped at
// 4.33:1 in eleven places -- both tokens exist, so no-unresolvable-color-token
// cannot see it either; they are simply too close together.
//
// This rule pairs the background and text classes ON THE SAME ELEMENT and
// computes the real ratio. It cannot see a background inherited from an
// ancestor, so it is deliberately silent when an element sets only one half
// of the pair -- it reports what it can prove, and nothing else.
//
// Only literal-hex scales are resolvable. Theme tokens defined as
// rgb(var(--x) / <alpha-value>) shift with the active theme and are skipped.

const AA_NORMAL = 4.5;

function hexToRgb(hex) {
  const h = hex.replace('#', '');
  return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16));
}

function relativeLuminance([r, g, b]) {
  const f = (c) => {
    const s = c / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
}

function contrastRatio(hexA, hexB) {
  const la = relativeLuminance(hexToRgb(hexA));
  const lb = relativeLuminance(hexToRgb(hexB));
  const [hi, lo] = la > lb ? [la, lb] : [lb, la];
  return (hi + 0.05) / (lo + 0.05);
}

/** Resolve a class to a literal hex, or null when it is theme-dependent,
 *  carries an opacity modifier, or is not a colour we can pin down. */
function resolveHex(token, prefix, palette) {
  let t = token.split(':').pop().replace(/^!/, '');
  if (!t.startsWith(`${prefix}-`)) return null;
  if (t.includes('[') || t.includes('/')) return null; // arbitrary or alpha
  const rest = t.slice(prefix.length + 1);
  const dash = rest.lastIndexOf('-');
  if (dash === -1) return null;
  const scale = rest.slice(0, dash);
  const shade = rest.slice(dash + 1);
  const byScale = palette.values.get(scale);
  if (!byScale) return null;
  return byScale.get(shade) || null;
}

/** Pick the class that wins for a given mode: the dark: one if present,
 *  otherwise the bare one (which stays applied in dark mode). */
function pickForMode(tokens, prefix, dark) {
  let bare = null;
  let darkTok = null;
  for (const tok of tokens) {
    const variants = tok.split(':');
    const base = variants.pop();
    if (!base.startsWith(`${prefix}-`)) continue;
    // ignore state variants -- hover/focus pairs are a separate question
    const others = variants.filter((v) => v !== 'dark');
    if (others.length) continue;
    if (variants.includes('dark')) darkTok = tok;
    else bare = tok;
  }
  return dark ? darkTok || bare : bare;
}

function checkContrastPair(context, node, value) {
  const palette = loadPalette();
  if (!palette.usable || !palette.values.size) return;
  const tokens = value.split(/\s+/).filter(Boolean);
  if (tokens.length < 2) return;

  for (const dark of [false, true]) {
    const bgTok = pickForMode(tokens, 'bg', dark);
    const fgTok = pickForMode(tokens, 'text', dark);
    if (!bgTok || !fgTok) continue;
    const bg = resolveHex(bgTok, 'bg', palette);
    const fg = resolveHex(fgTok, 'text', palette);
    if (!bg || !fg) continue;
    const ratio = contrastRatio(bg, fg);
    if (ratio < AA_NORMAL) {
      context.report({
        node,
        messageId: 'lowPair',
        data: {
          mode: dark ? 'dark mode' : 'light mode',
          fg: fgTok,
          bg: bgTok,
          ratio: ratio.toFixed(2),
        },
      });
    }
  }
}

const noLowContrastPairRule = {
  meta: {
    type: 'problem',
    docs: {
      description:
        'Disallow background/text class pairs on the same element whose computed contrast falls below WCAG AA',
      category: 'Accessibility',
      recommended: true,
    },
    schema: [],
    messages: {
      lowPair:
        '{{ fg }} on {{ bg }} is {{ ratio }}:1 in {{ mode }}, below the 4.5:1 WCAG AA floor for normal text. Pick a lighter text shade or a darker surface.',
    },
  },
  create(context) {
    return {
      JSXAttribute(node) {
        if (!node.name || (node.name.name !== 'className' && node.name.name !== 'class')) return;
        if (node.value && node.value.type === 'Literal' && typeof node.value.value === 'string') {
          checkContrastPair(context, node.value, node.value.value);
        }
      },
      Literal(node) {
        if (typeof node.value !== 'string') return;
        if (node.parent && node.parent.type === 'JSXAttribute') return;
        checkContrastPair(context, node, node.value);
      },
      TemplateLiteral(node) {
        for (const quasi of node.quasis) {
          if (quasi.value && quasi.value.raw) {
            checkContrastPair(context, quasi, quasi.value.raw);
          }
        }
      },
    };
  },
};

// ── Plugin export ─────────────────────────────────────────────

const plugin = {
  meta: {
    name: 'eslint-plugin-lsc-design-tokens',
    version: '1.3.0',
  },
  rules: {
    'no-banned-tokens': noBannedTokensRule,
    'no-low-contrast-text': noLowContrastTextRule,
    'no-hardcoded-page-width': noHardcodedPageWidthRule,
    'no-unresolvable-color-token': noUnresolvableColorTokenRule,
    'no-low-contrast-pair': noLowContrastPairRule,
  },
};

export default plugin;
