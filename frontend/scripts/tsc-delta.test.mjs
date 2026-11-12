import { test } from 'node:test'
import assert from 'node:assert/strict'
import { main, runTsc } from './tsc-delta.mjs'

test('compiler crash with empty output fails closed', () => {
  assert.throws(() => runTsc(() => ({ status: null, signal: 'SIGABRT', stdout: '', stderr: 'heap out of memory' })), /memory/)
})
test('configuration failure is not an empty success', () => {
  assert.throws(() => runTsc(() => ({ status: 1, stdout: "error TS5058: Missing config", stderr: '' })), /Unrecognized/)
})
test('launch failure is not an empty success', () => {
  assert.throws(() => runTsc(() => ({ error: new Error('Cannot launch compiler'), status: null, stdout: '', stderr: '' })), /launch/)
})
test('ordinary TypeScript diagnostics are valid checker output', () => {
  const stdout = 'src/example.ts(1,2): error TS2322: Bad assignment.\n'
  assert.equal(runTsc(() => ({ status: 2, stdout, stderr: '' })), stdout)
})
test('clean successful check is accepted', () => {
  assert.equal(runTsc(() => ({ status: 0, stdout: '', stderr: '' })), '')
})
test('partial output cannot hide an unrecognized error', () => {
  assert.throws(() => runTsc(() => ({ status: 2, stdout: 'src/example.ts(1,2): error TS2322: Bad assignment.\nerror TS5058: Missing config', stderr: '' })), /Unrecognized/)
})

import { mkdtempSync, readFileSync, writeFileSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

test('checker failure stays fatal in warning and rebaseline modes', () => {
  const directory = mkdtempSync(join(tmpdir(), 'tsc-ratchet-'))
  const baselineFile = join(directory, 'baseline.json')
  const original = '["src/example.ts::TS2322"]\n'
  writeFileSync(baselineFile, original)
  try {
    for (const options of [{}, { warn: true }, { rebaseline: true }]) {
      assert.equal(main(() => { throw new Error('compiler crashed') }, { ...options, baselineFile }), 2)
      assert.equal(readFileSync(baselineFile, 'utf8'), original)
    }
    assert.equal(main(() => 'src/example.ts(8,3): error TS2322: Existing.\n', { baselineFile }), 0)
    assert.equal(main(() => 'src/new.ts(1,1): error TS2322: New.\n', { baselineFile }), 1)
    assert.equal(readFileSync(baselineFile, 'utf8'), original)
  } finally {
    rmSync(directory, { recursive: true, force: true })
  }
})
