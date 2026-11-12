/**
 * ts-morph scan of `@/lib/api-client` fetchApi calls.
 * Returns one record per call: { file, line, method, path (normalized),
 *   bodyFields: {name, optional}[], status }.
 * status: 'resolved' | 'unresolved-path' | 'unresolved-body'.
 */
import { SyntaxKind, SymbolFlags } from 'ts-morph'
import { normalizePath } from './openapi-oracle.mjs'

const API_CLIENT_MODULE = '@/lib/api-client'
// `fetchApi` is the only `@/lib/api-client` export with the (path, { body }) object-body
// shape this checker understands. The apiHelpers wrappers (fetchApiSafe / -WithErrorHandling)
// have a callback signature and a different module, so they are deliberately not matched.
const FETCH_NAMES = new Set(['fetchApi'])
const METHODS_WITH_BODY = new Set(['POST', 'PUT', 'PATCH'])

/** Local identifiers in this file that are the api-client fetchApi family. */
function apiClientLocalNames(sourceFile) {
  const names = new Set()
  for (const imp of sourceFile.getImportDeclarations()) {
    if (imp.getModuleSpecifierValue() !== API_CLIENT_MODULE) continue
    for (const named of imp.getNamedImports()) {
      const imported = named.getName()
      if (FETCH_NAMES.has(imported)) names.add(named.getAliasNode()?.getText() ?? imported)
    }
  }
  return names
}

/** Resolve the path arg to a normalized spec-relative path, or null if dynamic-prefix. */
function resolvePath(arg) {
  if (!arg) return null
  if (arg.getKind() === SyntaxKind.StringLiteral) {
    return normalizePath(arg.getLiteralText())
  }
  if (arg.getKind() === SyntaxKind.TemplateExpression || arg.getKind() === SyntaxKind.NoSubstitutionTemplateLiteral) {
    // Reconstruct raw text without backticks; only resolvable if it begins with a literal '/'.
    const text = arg.getText().slice(1, -1)
    if (!text.startsWith('/')) return null
    return normalizePath(text)
  }
  return null
}

function readMethod(optionsObj) {
  const prop = optionsObj?.getProperty?.('method')
  const init = prop?.getInitializer?.()
  if (init && init.getKind() === SyntaxKind.StringLiteral) return init.getLiteralText().toUpperCase()
  return 'GET'
}

/** Resolve the body value's type into a field set, or null if not enumerable. */
function readBodyFields(optionsObj) {
  const prop = optionsObj?.getProperty?.('body')
  if (!prop) return [] // no body property → empty body
  let type
  if (prop.getKind() === SyntaxKind.PropertyAssignment) {
    type = prop.getInitializer()?.getType()
  } else if (prop.getKind() === SyntaxKind.ShorthandPropertyAssignment) {
    type = prop.getSymbol()?.getTypeAtLocation(prop)
  }
  if (!type) return null
  if (type.isString() || type.isAny() || type.isUnknown()) return null // string/FormData/any → not field-checkable
  const props = type.getProperties()
  if (props.length === 0 && !type.isObject()) return null
  return props.map((sym) => ({
    name: sym.getName(),
    optional: sym.hasFlags(SymbolFlags.Optional),
  }))
}

export function scanWrappers(project) {
  const out = []
  for (const sourceFile of project.getSourceFiles()) {
    const locals = apiClientLocalNames(sourceFile)
    if (locals.size === 0) continue
    for (const call of sourceFile.getDescendantsOfKind(SyntaxKind.CallExpression)) {
      const callee = call.getExpression()
      const calleeName = callee.getKind() === SyntaxKind.Identifier ? callee.getText() : null
      if (!calleeName || !locals.has(calleeName)) continue

      const args = call.getArguments()
      const optionsObj = args[1]?.asKind(SyntaxKind.ObjectLiteralExpression)
      const method = readMethod(optionsObj)
      if (!METHODS_WITH_BODY.has(method)) continue

      const file = sourceFile.getFilePath()
      const line = call.getStartLineNumber()
      const path = resolvePath(args[0])
      if (path === null) {
        out.push({ file, line, method, path: null, bodyFields: [], status: 'unresolved-path' })
        continue
      }
      const bodyFields = readBodyFields(optionsObj)
      if (bodyFields === null) {
        out.push({ file, line, method, path, bodyFields: [], status: 'unresolved-body' })
        continue
      }
      out.push({ file, line, method, path, bodyFields, status: 'resolved' })
    }
  }
  return out
}
