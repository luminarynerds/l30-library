/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Codemod: migrate hand-rolled page-root width wrappers to <PageContainer>.
 *
 * Transforms the OUTERMOST <div> carrying the page-root width signature
 * (max-w-Nxl + mx-auto + px-*) reachable from each component return, unless it
 * is already inside a StandardPageLayout/PageContainer. Inner cards/sections
 * are never touched. Width/layout classes are dropped (PageContainer owns
 * them); other classes are preserved via className.
 *
 * Usage (from frontend/, with ts-morph resolvable):
 *   node scripts/codemods/migrate-page-width.mjs <wide|content|read|form> <file...> [--dry]
 */
import { Project, SyntaxKind, QuoteKind } from 'ts-morph'

const argv = process.argv.slice(2)
const dry = argv.includes('--dry')
const rest = argv.filter((a) => a !== '--dry')
const tier = rest[0]
const files = rest.slice(1)

if (!['wide', 'content', 'read', 'form'].includes(tier) || files.length === 0) {
  console.error('usage: migrate-page-width.mjs <wide|content|read|form> <file...> [--dry]')
  process.exit(2)
}

const MANAGED = new Set(['StandardPageLayout', 'PageContainer'])
const ROOT_TAGS = new Set(['div', 'main', 'section'])
const SIG_WIDTH = /^max-w-(2xl|3xl|4xl|5xl|6xl|7xl|\[\d+px\])$/
const isGutterPx = (c) => /^(sm:|md:|lg:|xl:)?px-\d/.test(c)
// Strip only width + horizontal gutters (PageContainer re-adds the same px).
// Keep py-* and everything else so vertical spacing is unchanged.
const isLayout = (c) => SIG_WIDTH.test(c) || c === 'mx-auto' || c === 'container' || isGutterPx(c)
const hasSignature = (cs) =>
  cs.some((c) => SIG_WIDTH.test(c)) && cs.includes('mx-auto') && cs.some(isGutterPx)

function signatureClasses(el) {
  const opening = el.getOpeningElement && el.getOpeningElement()
  if (!opening || !ROOT_TAGS.has(opening.getTagNameNode().getText())) return null
  const attr = opening.getAttribute('className')
  if (!attr || attr.getKind() !== SyntaxKind.JsxAttribute) return null
  const init = attr.getInitializer()
  if (!init || init.getKind() !== SyntaxKind.StringLiteral) return null
  const classes = init.getLiteralValue().split(/\s+/).filter(Boolean)
  return hasSignature(classes) ? classes : null
}

function hasManagedAncestor(el, stop) {
  let a = el.getParent()
  const stopParent = stop.getParent()
  while (a && a !== stopParent) {
    if (a.getKind() === SyntaxKind.JsxElement) {
      const t = a.getOpeningElement().getTagNameNode().getText()
      if (MANAGED.has(t)) return true
    }
    a = a.getParent()
  }
  return false
}

function returnRoots(sf) {
  const roots = []
  sf.forEachDescendant((node) => {
    const k = node.getKind()
    const isRoot = (x) =>
      x && (x.getKind() === SyntaxKind.JsxElement || x.getKind() === SyntaxKind.JsxFragment)
    if (k === SyntaxKind.ReturnStatement) {
      let e = node.getExpression()
      while (e && e.getKind() === SyntaxKind.ParenthesizedExpression) e = e.getExpression()
      if (isRoot(e)) roots.push(e)
    } else if (k === SyntaxKind.ArrowFunction) {
      let b = node.getBody()
      while (b && b.getKind() === SyntaxKind.ParenthesizedExpression) b = b.getExpression()
      if (isRoot(b)) roots.push(b)
    }
  })
  return roots
}

// Find one element to transform (fresh query each call -> no stale nodes).
function findNext(sf) {
  for (const root of returnRoots(sf)) {
    const rootOpen = root.getOpeningElement?.()
    if (rootOpen && MANAGED.has(rootOpen.getTagNameNode().getText())) continue
    const candidates = [root, ...root.getDescendantsOfKind(SyntaxKind.JsxElement)]
    for (const el of candidates) {
      const classes = signatureClasses(el)
      if (!classes) continue
      if (hasManagedAncestor(el, root)) continue
      return { el, classes }
    }
  }
  return null
}

function transform(el, classes) {
  const remaining = classes.filter((c) => !isLayout(c))
  const open = el.getOpeningElement()
  const close = el.getClosingElement()
  const tag = open.getTagNameNode().getText()
  const others = open
    .getAttributes()
    .filter((a) => !(a.getKind() === SyntaxKind.JsxAttribute && a.getNameNode().getText() === 'className'))
    .map((a) => a.getText())
  const parts = []
  if (tag !== 'div') parts.push(`as="${tag}"`)
  if (tier !== 'content') parts.push(`width="${tier}"`)
  if (remaining.length) parts.push(`className="${remaining.join(' ')}"`)
  parts.push(...others)
  const newOpen = `<PageContainer${parts.length ? ' ' + parts.join(' ') : ''}>`
  close.replaceWithText('</PageContainer>')
  open.replaceWithText(newOpen)
}

const project = new Project({
  tsConfigFilePath: 'tsconfig.json',
  skipAddingFilesFromTsConfig: true,
  manipulationSettings: { quoteKind: QuoteKind.Single },
})

const IMPORT_LINE = "import PageContainer from '@/components/layout/PageContainer'"

let changedCount = 0
for (const f of files) {
  const sf = project.addSourceFileAtPath(f)
  let n = 0
  while (n < 50) {
    const hit = findNext(sf)
    if (!hit) break
    transform(hit.el, hit.classes)
    n++
  }
  if (n > 0) {
    const hasImport = sf
      .getImportDeclarations()
      .some((d) => d.getModuleSpecifierValue() === '@/components/layout/PageContainer')
    if (!hasImport) {
      sf.addImportDeclaration({ defaultImport: 'PageContainer', moduleSpecifier: '@/components/layout/PageContainer' })
      // match house style: no trailing semicolon
      sf.replaceWithText(sf.getFullText().replace(IMPORT_LINE + ';', IMPORT_LINE))
    }
    changedCount++
    if (dry) console.log(`would change (${n} wrapper(s)):`, f)
    else {
      sf.saveSync()
      console.log(`migrated (${n} wrapper(s)):`, f)
    }
  } else {
    console.log('skip (no unmanaged page-root width div):', f)
  }
}
console.log(dry ? `[dry] ${changedCount} file(s) would change` : `${changedCount} file(s) migrated`)
