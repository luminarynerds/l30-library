/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/* eslint-disable react-refresh/only-export-components */
import * as Sentry from "@/lib/sentry-lazy"
/**
 * PrintableBarcode Component
 *
 * Renders scannable barcodes for printing using SVG.
 * Supports Code 39, Code 128, and Codabar formats commonly used in libraries.
 *
 * For browser printing, this uses SVG rendering which:
 * - Scales without pixelation
 * - Prints at any DPI without quality loss
 * - Works reliably across all browsers
 */

import { useMemo } from 'react'

// ==================== Types ====================

export type BarcodeFormat = 'code39' | 'code128' | 'codabar'

interface PrintableBarcodeProps {
  value: string
  format?: BarcodeFormat
  width?: number // Total width in pixels (default: 200)
  height?: number // Bar height in pixels (default: 50)
  showText?: boolean // Show value text below barcode
  className?: string
  'aria-label'?: string
}

// ==================== Encoding Tables ====================

// Code 39 character patterns (narrow=1, wide=3)
const CODE39_PATTERNS: Record<string, string> = {
  '0': 'nnnwwnwnn',
  '1': 'wnnwnnnnw',
  '2': 'nnwwnnnnw',
  '3': 'wnwwnnnnn',
  '4': 'nnnwwnnnw',
  '5': 'wnnwwnnnn',
  '6': 'nnwwwnnnn',
  '7': 'nnnwnnwnw',
  '8': 'wnnwnnwnn',
  '9': 'nnwwnnwnn',
  'A': 'wnnnnwnnw',
  'B': 'nnwnnwnnw',
  'C': 'wnwnnwnnn',
  'D': 'nnnnwwnnw',
  'E': 'wnnnwwnnn',
  'F': 'nnwnwwnnn',
  'G': 'nnnnnwwnw',
  'H': 'wnnnnwwnn',
  'I': 'nnwnnwwnn',
  'J': 'nnnnwwwnn',
  'K': 'wnnnnnnww',
  'L': 'nnwnnnnww',
  'M': 'wnwnnnnwn',
  'N': 'nnnnwnnww',
  'O': 'wnnnwnnwn',
  'P': 'nnwnwnnwn',
  'Q': 'nnnnnnwww',
  'R': 'wnnnnnwwn',
  'S': 'nnwnnnwwn',
  'T': 'nnnnwnwwn',
  'U': 'wwnnnnnnw',
  'V': 'nwwnnnnnw',
  'W': 'wwwnnnnnn',
  'X': 'nwnnwnnnw',
  'Y': 'wwnnwnnnn',
  'Z': 'nwwnwnnnn',
  '-': 'nwnnnnwnw',
  '.': 'wwnnnnwnn',
  ' ': 'nwwnnnwnn',
  '$': 'nwnwnwnnn',
  '/': 'nwnwnnnwn',
  '+': 'nwnnnwnwn',
  '%': 'nnnwnwnwn',
  '*': 'nwnnwnwnn', // Start/stop character
}

// Code 128B patterns (bar widths 1-4)
const CODE128_PATTERNS: number[][] = [
  [2, 1, 2, 2, 2, 2], // 0: space
  [2, 2, 2, 1, 2, 2], // 1: !
  [2, 2, 2, 2, 2, 1], // 2: "
  [1, 2, 1, 2, 2, 3], // 3: #
  [1, 2, 1, 3, 2, 2], // 4: $
  [1, 3, 1, 2, 2, 2], // 5: %
  [1, 2, 2, 2, 1, 3], // 6: &
  [1, 2, 2, 3, 1, 2], // 7: '
  [1, 3, 2, 2, 1, 2], // 8: (
  [2, 2, 1, 2, 1, 3], // 9: )
  [2, 2, 1, 3, 1, 2], // 10: *
  [2, 3, 1, 2, 1, 2], // 11: +
  [1, 1, 2, 2, 3, 2], // 12: ,
  [1, 2, 2, 1, 3, 2], // 13: -
  [1, 2, 2, 2, 3, 1], // 14: .
  [1, 1, 3, 2, 2, 2], // 15: /
  [1, 2, 3, 1, 2, 2], // 16: 0
  [1, 2, 3, 2, 2, 1], // 17: 1
  [2, 2, 3, 2, 1, 1], // 18: 2
  [2, 2, 1, 1, 3, 2], // 19: 3
  [2, 2, 1, 2, 3, 1], // 20: 4
  [2, 1, 3, 2, 1, 2], // 21: 5
  [2, 2, 3, 1, 1, 2], // 22: 6
  [3, 1, 2, 1, 3, 1], // 23: 7
  [3, 1, 1, 2, 2, 2], // 24: 8
  [3, 2, 1, 1, 2, 2], // 25: 9
  [3, 2, 1, 2, 2, 1], // 26: :
  [3, 1, 2, 2, 1, 2], // 27: ;
  [3, 2, 2, 1, 1, 2], // 28: <
  [3, 2, 2, 2, 1, 1], // 29: =
  [2, 1, 2, 1, 2, 3], // 30: >
  [2, 1, 2, 3, 2, 1], // 31: ?
  [2, 3, 2, 1, 2, 1], // 32: @
  [1, 1, 1, 3, 2, 3], // 33: A
  [1, 3, 1, 1, 2, 3], // 34: B
  [1, 3, 1, 3, 2, 1], // 35: C
  [1, 1, 2, 3, 1, 3], // 36: D
  [1, 3, 2, 1, 1, 3], // 37: E
  [1, 3, 2, 3, 1, 1], // 38: F
  [2, 1, 1, 3, 1, 3], // 39: G
  [2, 3, 1, 1, 1, 3], // 40: H
  [2, 3, 1, 3, 1, 1], // 41: I
  [1, 1, 2, 1, 3, 3], // 42: J
  [1, 1, 2, 3, 3, 1], // 43: K
  [1, 3, 2, 1, 3, 1], // 44: L
  [1, 1, 3, 1, 2, 3], // 45: M
  [1, 1, 3, 3, 2, 1], // 46: N
  [1, 3, 3, 1, 2, 1], // 47: O
  [3, 1, 3, 1, 2, 1], // 48: P
  [2, 1, 1, 3, 3, 1], // 49: Q
  [2, 3, 1, 1, 3, 1], // 50: R
  [2, 1, 3, 1, 1, 3], // 51: S
  [2, 1, 3, 3, 1, 1], // 52: T
  [2, 1, 3, 1, 3, 1], // 53: U
  [3, 1, 1, 1, 2, 3], // 54: V
  [3, 1, 1, 3, 2, 1], // 55: W
  [3, 3, 1, 1, 2, 1], // 56: X
  [3, 1, 2, 1, 1, 3], // 57: Y
  [3, 1, 2, 3, 1, 1], // 58: Z
  [3, 3, 2, 1, 1, 1], // 59: [
  [3, 1, 4, 1, 1, 1], // 60: \
  [2, 2, 1, 4, 1, 1], // 61: ]
  [4, 3, 1, 1, 1, 1], // 62: ^
  [1, 1, 1, 2, 2, 4], // 63: _
  [1, 1, 1, 4, 2, 2], // 64: `
  [1, 2, 1, 1, 2, 4], // 65: a
  [1, 2, 1, 4, 2, 1], // 66: b
  [1, 4, 1, 1, 2, 2], // 67: c
  [1, 4, 1, 2, 2, 1], // 68: d
  [1, 1, 2, 2, 1, 4], // 69: e
  [1, 1, 2, 4, 1, 2], // 70: f
  [1, 2, 2, 1, 1, 4], // 71: g
  [1, 2, 2, 4, 1, 1], // 72: h
  [1, 4, 2, 1, 1, 2], // 73: i
  [1, 4, 2, 2, 1, 1], // 74: j
  [2, 4, 1, 2, 1, 1], // 75: k
  [2, 2, 1, 1, 1, 4], // 76: l
  [4, 1, 3, 1, 1, 1], // 77: m
  [2, 4, 1, 1, 1, 2], // 78: n
  [1, 3, 4, 1, 1, 1], // 79: o
  [1, 1, 1, 2, 4, 2], // 80: p
  [1, 2, 1, 1, 4, 2], // 81: q
  [1, 2, 1, 2, 4, 1], // 82: r
  [1, 1, 4, 2, 1, 2], // 83: s
  [1, 2, 4, 1, 1, 2], // 84: t
  [1, 2, 4, 2, 1, 1], // 85: u
  [4, 1, 1, 2, 1, 2], // 86: v
  [4, 2, 1, 1, 1, 2], // 87: w
  [4, 2, 1, 2, 1, 1], // 88: x
  [2, 1, 2, 1, 4, 1], // 89: y
  [2, 1, 4, 1, 2, 1], // 90: z
  [4, 1, 2, 1, 2, 1], // 91: {
  [1, 1, 1, 1, 4, 3], // 92: |
  [1, 1, 1, 3, 4, 1], // 93: }
  [1, 3, 1, 1, 4, 1], // 94: ~
  [1, 1, 4, 1, 1, 3], // 95: DEL
  [1, 1, 4, 3, 1, 1], // 96: FNC3
  [4, 1, 1, 1, 1, 3], // 97: FNC2
  [4, 1, 1, 3, 1, 1], // 98: SHIFT
  [1, 1, 3, 1, 4, 1], // 99: Code C
  [1, 1, 4, 1, 3, 1], // 100: Code B
  [3, 1, 1, 1, 4, 1], // 101: Code A
  [4, 1, 1, 1, 3, 1], // 102: FNC1
  [2, 1, 1, 4, 1, 2], // 103: Start A
  [2, 1, 1, 2, 1, 4], // 104: Start B
  [2, 1, 1, 2, 3, 2], // 105: Start C
]

const CODE128_STOP: number[] = [2, 3, 3, 1, 1, 1, 2]

// ==================== Encoding Functions ====================

function encodeCode39(value: string): string {
  const upperValue = value.toUpperCase()
  let binary = ''

  // Add start character
  binary += patternToBinary(CODE39_PATTERNS['*']!)
  binary += '0' // Inter-character gap

  // Encode each character
  for (const char of upperValue) {
    const pattern = CODE39_PATTERNS[char]
    if (!pattern) {
      Sentry.captureMessage(`PrintableBarcode: Invalid Code 39 character '${char}'`, 'warning')
      continue
    }
    binary += patternToBinary(pattern)
    binary += '0' // Inter-character gap
  }

  // Add stop character
  binary += patternToBinary(CODE39_PATTERNS['*']!)

  return binary
}

function patternToBinary(pattern: string): string {
  let binary = ''
  let isBar = true

  for (const char of pattern) {
    const width = char === 'w' ? 3 : 1
    binary += (isBar ? '1' : '0').repeat(width)
    isBar = !isBar
  }

  return binary
}

function encodeCode128(value: string): number[] {
  const codes: number[] = []

  // Start with Code B (for most ASCII characters)
  codes.push(104)
  let checksum = 104

  // Encode each character
  for (let i = 0; i < value.length; i++) {
    const charCode = value.charCodeAt(i)
    let code: number

    if (charCode >= 32 && charCode <= 126) {
      code = charCode - 32
    } else {
      // Handle control characters or fallback
      code = 0
    }

    codes.push(code)
    checksum += code * (i + 1)
  }

  // Add checksum
  codes.push(checksum % 103)

  return codes
}

function code128ToBinary(codes: number[]): string {
  let binary = ''

  for (const code of codes) {
    const pattern = CODE128_PATTERNS[code]
    if (pattern) {
      let isBar = true
      for (const width of pattern) {
        binary += (isBar ? '1' : '0').repeat(width)
        isBar = !isBar
      }
    }
  }

  // Add stop pattern
  let isBar = true
  for (const width of CODE128_STOP) {
    binary += (isBar ? '1' : '0').repeat(width)
    isBar = !isBar
  }

  return binary
}

// ==================== SVG Rendering ====================

function binaryToSvgBars(
  binary: string,
  width: number,
  _height: number
): { x: number; width: number }[] {
  const bars: { x: number; width: number }[] = []
  const unitWidth = width / binary.length

  let currentBar: { start: number; length: number } | null = null

  for (let i = 0; i < binary.length; i++) {
    if (binary[i] === '1') {
      if (!currentBar) {
        currentBar = { start: i, length: 1 }
      } else {
        currentBar.length++
      }
    } else {
      if (currentBar) {
        bars.push({
          x: currentBar.start * unitWidth,
          width: currentBar.length * unitWidth,
        })
        currentBar = null
      }
    }
  }

  // Don't forget the last bar if it extends to the end
  if (currentBar) {
    bars.push({
      x: currentBar.start * unitWidth,
      width: currentBar.length * unitWidth,
    })
  }

  return bars
}

// ==================== Component ====================

export default function PrintableBarcode({
  value,
  format = 'code39',
  width = 200,
  height = 50,
  showText = true,
  className = '',
  'aria-label': ariaLabel,
}: PrintableBarcodeProps): React.ReactElement {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { binary: _binary, bars, textValue } = useMemo(() => {
    let binaryData: string
    let displayValue = value

    switch (format) {
      case 'code128': {
        const codes = encodeCode128(value)
        binaryData = code128ToBinary(codes)
        break
      }
      case 'codabar': {
        // Codabar uses A-D as start/stop, treat similar to Code 39
        displayValue = `A${value}A`
        binaryData = encodeCode39(displayValue)
        break
      }
      case 'code39':
      default: {
        binaryData = encodeCode39(value)
        displayValue = `*${value.toUpperCase()}*`
        break
      }
    }

    const barData = binaryToSvgBars(binaryData, width, height)

    return {
      binary: binaryData,
      bars: barData,
      textValue: displayValue,
    }
  }, [value, format, width, height])

  const totalHeight = showText ? height + 20 : height
  const label = ariaLabel || `Barcode: ${value}`

  return (
    <div
      className={`barcode-container ${className}`}
      data-barcode
      data-format={format}
      data-value={value}
    >
      <svg
        width={width}
        height={totalHeight}
        viewBox={`0 0 ${width} ${totalHeight}`}
        role="img"
        aria-label={label}
        className="barcode-svg"
        style={{
          display: 'block',
          maxWidth: '100%',
          height: 'auto',
        }}
      >
        {/* White background for reliable scanning */}
        <rect x="0" y="0" width={width} height={totalHeight} fill="white" />

        {/* Barcode bars */}
        {bars.map((bar, index) => (
          <rect
            key={index}
            x={bar.x}
            y={0}
            width={bar.width}
            height={height}
            fill="black"
          />
        ))}

        {/* Text label */}
        {showText && (
          <text
            x={width / 2}
            y={height + 14}
            textAnchor="middle"
            fontSize="12"
            fontFamily="'Courier New', monospace"
            fill="black"
            letterSpacing="2"
          >
            {textValue}
          </text>
        )}
      </svg>
    </div>
  )
}

// ==================== Utility Exports ====================

export { encodeCode39, encodeCode128 }
