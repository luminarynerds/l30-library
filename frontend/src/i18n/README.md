# i18n (Internationalization) System

This directory contains the complete internationalization system for the L30 Library application.

## Overview

The i18n system provides:
- Multi-language support (EN, ES, FR, DE, ZH, AR, RU)
- Right-to-left (RTL) layout support for Arabic
- ICU message format for plurals and variables
- Date and number localization
- Translation management

## Quick Start

### 1. Wrap your app with I18nProvider

```tsx
import { I18nProvider } from './i18n'

function App() {
  return (
    <I18nProvider>
      {/* Your app */}
    </I18nProvider>
  )
}
```

### 2. Use translations in components

```tsx
import { useTranslation } from './i18n'

function MyComponent() {
  const { t, language, setLanguage, isRTL } = useTranslation()

  return (
    <div>
      <h1>{t('navigation.home')}</h1>
      <p>{t('common.loading')}</p>
      <button onClick={() => setLanguage('es')}>
        Espa�ol
      </button>
    </div>
  )
}
```

### 3. Use with parameters and plurals

```tsx
// Simple variable
t('catalog.dueDate', { date: '2026-01-15' })
// Output: "Due: 2026-01-15"

// Plurals (ICU format)
t('catalog.resultsCount', { count: 0 })  // "No items found"
t('catalog.resultsCount', { count: 1 })  // "1 item found"
t('catalog.resultsCount', { count: 5 })  // "5 items found"
```

### 4. Format dates and numbers

```tsx
import { formatDate, formatCurrency, formatRelativeTime } from './i18n'

// Dates
formatDate(new Date(), 'es')  // "15/1/2026"
formatLongDate(new Date(), 'es')  // "15 de enero de 2026"
formatRelativeTime(someDate, 'es')  // "Hace 2 horas"

// Numbers
formatCurrency(19.99, 'es', 'CAD')  // "19,99 CA$"
formatNumber(1234.56, 'es')  // "1.234,56"
```

## File Structure

```
i18n/
 translations/          # Translation files
�    en.json           # English (comprehensive)
�    es.json           # Spanish (comprehensive)
�    fr.json           # French (basic)
�    de.json           # German (basic)
�    zh.json           # Chinese (basic)
�    ar.json           # Arabic (basic, RTL)
�    ru.json           # Russian (basic)
 I18nContext.tsx       # React context and hooks
 translations.ts       # Translation lookup and ICU parser
 localization.ts       # Date/number formatting
 config.ts             # Configuration
 index.ts              # Exports
 README.md            # This file
```

## Translation Keys

Translation keys use dot notation to organize strings:

```
common.*          - Common UI elements (save, cancel, delete, etc.)
navigation.*      - Navigation labels and aria-labels
header.*          - Header/footer content
catalog.*         - Catalog and search functionality
circulation.*     - Checkout, holds, renewals
account.*         - User account pages
auth.*            - Authentication (login, register)
forms.*           - Form validation and messages
accessibility.*   - Accessibility settings
errors.*          - Error messages
notifications.*   - System notifications
dates.*           - Relative time strings
events.*          - Events and programs
```

## Adding Translations

### 1. Add to English (en.json)

```json
{
  "mySection": {
    "greeting": "Hello, {name}!",
    "itemCount": "{count, plural, =0 {No items} =1 {1 item} other {# items}}"
  }
}
```

### 2. Add to other languages

```json
// es.json
{
  "mySection": {
    "greeting": "�Hola, {name}!",
    "itemCount": "{count, plural, =0 {Sin art�culos} =1 {1 art�culo} other {# art�culos}}"
  }
}
```

### 3. Use in components

```tsx
t('mySection.greeting', { name: 'Ana' })
t('mySection.itemCount', { count: 5 })
```

## ICU Message Format

The system supports ICU MessageFormat for complex translations:

### Variables

```json
{
  "greeting": "Hello, {name}!"
}
```

Usage: `t('greeting', { name: 'John' })`

### Plurals

```json
{
  "items": "{count, plural, =0 {No items} =1 {One item} other {# items}}"
}
```

Usage: `t('items', { count: 5 })`

The `#` symbol is replaced with the actual count.

## RTL (Right-to-Left) Support

Arabic is configured as an RTL language. When Arabic is selected:

1. The `dir="rtl"` attribute is set on `<html>`
2. CSS automatically flips the layout
3. Text alignment becomes right-aligned
4. Icons and UI elements flip appropriately

### RTL-specific CSS

The CSS includes RTL overrides for:
- Margins and padding
- Flex direction
- Text alignment
- Positioning (left/right)
- Border radius

### Preserving LTR elements in RTL

Use the `.ltr-preserve` class for elements that should remain left-to-right:

```tsx
<input type="email" className="ltr-preserve" />
```

## Date and Number Localization

### Dates

```tsx
import { formatDate, formatLongDate, formatTime } from './i18n'

// Short date
formatShortDate(date, language)  // "1/15/2026" or "15/1/2026"

// Long date
formatLongDate(date, language)   // "January 15, 2026" or "15 de enero de 2026"

// Time
formatTime(date, language)       // "2:30 PM" or "14:30"

// Relative time
formatRelativeTime(date, language)  // "2 hours ago" or "Hace 2 horas"
```

### Numbers

```tsx
import { formatNumber, formatCurrency, formatPercentage } from './i18n'

formatNumber(1234.56, language)           // "1,234.56" or "1.234,56"
formatCurrency(19.99, language, 'CAD')    // "$19.99" or "19,99 CA$"
formatPercentage(0.85, language, 0)       // "85%" or "85 %"
```

## Language Persistence

The selected language is automatically:
1. Saved to `localStorage` (`lsc-language-preference`)
2. Restored on page load
3. Falls back to browser language
4. Defaults to English if not detected

## Supported Languages

| Code | Language | Native Name | RTL | Coverage |
|------|----------|-------------|-----|----------|
| en   | English  | English     | No  | 100%     |
| es   | Spanish  | Espa�ol     | No  | 100%     |
| fr   | French   | Fran�ais    | No  | 30%      |
| de   | German   | Deutsch     | No  | 30%      |
| zh   | Chinese  | ��        | No  | 30%      |
| ar   | Arabic   | ��ع���ة     | Yes | 30%      |
| ru   | Russian  | �у��к�й     | No  | 30%      |

## Best Practices

### 1. Always use translation keys

```tsx
// Good
<button>{t('common.save')}</button>

// Bad
<button>Save</button>
```

### 2. Use semantic keys

```tsx
// Good
t('auth.loginButton')

// Bad
t('login_btn_text')
```

### 3. Keep translations short and clear

```json
// Good
{
  "delete": "Delete",
  "deleteConfirm": "Are you sure you want to delete this item?"
}

// Avoid
{
  "deleteButtonLabelForUserInterface": "Delete"
}
```

### 4. Use ICU format for dynamic content

```tsx
// Good
t('greeting', { name: user.name })

// Avoid
`Hello, ${user.name}!`  // Not translatable
```

### 5. Provide context in keys

```json
{
  "navigation": {
    "home": "Home",
    "catalog": "Catalog"
  },
  "breadcrumb": {
    "home": "Home",
    "catalog": "Catalog"
  }
}
```

## Future Enhancements

- [ ] Complete translations for FR, DE, ZH, AR, RU
- [ ] Add Hebrew (he) support
- [ ] Implement lazy loading for translation files
- [ ] Add translation management UI for staff
- [ ] Implement crowdsourced translation contributions
- [ ] Add automated translation validation
- [ ] Support for regional variants (es-MX, fr-CA, etc.)

## Contributing Translations

To contribute translations:

1. Copy `en.json` as a template
2. Translate all strings to your language
3. Test with `setLanguage('your-language-code')`
4. Submit via pull request

For questions or issues, contact the development team.
