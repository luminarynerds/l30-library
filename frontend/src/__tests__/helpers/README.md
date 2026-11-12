# Test Helpers Documentation

This directory contains global test utilities and factory functions for creating consistent test fixtures across the L30 frontend test suite.

## Purpose

The test helpers solve common problems in testing:
- **Type Safety**: Ensures all mock objects have complete, valid types
- **Consistency**: Provides standard mock data across all tests
- **Maintainability**: Single source of truth for test fixtures
- **Productivity**: Reduces boilerplate in test files

## Usage

### Importing

```typescript
import {
  createMockEvent,
  createMockPatron,
  createMockLostItem,
  createMockToken,
  createMockCallback,
} from '../helpers/testHelpers'
```

### Creating Mock Objects

#### Events

```typescript
// Single event with defaults
const event = createMockEvent()

// Event with custom properties
const customEvent = createMockEvent({
  title: 'My Custom Event',
  max_attendees: 100,
  is_featured: true,
})

// Multiple events
const events = createMockEvents(5) // Creates 5 events with IDs 1-5

// Multiple events with custom base properties
const events = createMockEvents(3, {
  category: 'workshop',
  audience: 'adults',
})
```

#### Patrons

```typescript
// Single patron with defaults
const patron = createMockPatron()

// Patron with custom properties
const blockedPatron = createMockPatron({
  is_active: false,
  block_reason: 'Excessive fines',
  fines_balance: 50.0,
})

// Multiple patrons
const patrons = createMockPatrons(10) // Creates 10 patrons with unique emails
```

#### Items (Lost, Damaged, Mending)

```typescript
// Lost items
const lostItem = createMockLostItem()
const lostItems = createMockLostItems(5, {
  lost_type: 'patron_declared_lost',
  replacement_cost: 29.99,
})

// Damaged items
const damagedItem = createMockDamagedItem()
const damagedItems = createMockDamagedItems(3, {
  severity: 'severe',
  damage_types: ['water_damage', 'torn_cover'],
})

// Mending queue items
const mendingItem = createMockMendingQueueItem()
const mendingItems = createMockMendingQueueItems(4, {
  priority: 1,
  is_in_progress: true,
})
```

### Utilities

```typescript
// Mock auth token
const token = createMockToken() // Returns 'mock-test-token-12345'

// Mock callbacks
const onSuccess = createMockCallback<() => void>()
const onClick = createMockCallback<(id: number) => void>()

// Wait for async operations
await waitForAsync()

// Mock staff members
const staff = createMockStaffMembers(5) // Returns [{id: 1, name: 'Staff Member 1'}, ...]
```

### Type Guards

```typescript
// Check item types
if (isLostItem(item)) {
  console.log(item.lost_type) // TypeScript knows this is a LostItem
}

if (isDamagedItem(item)) {
  console.log(item.severity) // TypeScript knows this is a DamagedItem
}

if (isMendingQueueItem(item)) {
  console.log(item.priority) // TypeScript knows this is a MendingQueueItem
}
```

## Example Test File

```typescript
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import {
  createMockEvents,
  createMockToken,
  createMockCallback,
} from '../../helpers/testHelpers'
import EventList from '../../../components/EventList'

describe('EventList', () => {
  it('renders list of events', () => {
    const events = createMockEvents(3)
    const token = createMockToken()
    const onEventClick = createMockCallback<(id: number) => void>()

    render(
      <EventList
        events={events}
        token={token}
        onEventClick={onEventClick}
      />
    )

    events.forEach(event => {
      expect(screen.getByText(event.title)).toBeInTheDocument()
    })
  })
})
```

## Benefits

### Before Test Helpers

```typescript
// Incomplete mock - missing many required fields!
const mockEvent = {
  id: 1,
  title: 'Test Event',
  description: 'Test description',
  date: '2024-01-15',
  location: 'Library',
  // Missing: start_time, end_time, is_virtual, audience, category,
  // tags, max_attendees, registration_required, registration_count,
  // spots_remaining, image_url, is_featured, series_id, series_name,
  // created_at, average_rating, review_count
}
```

### After Test Helpers

```typescript
// Complete, type-safe mock!
const mockEvent = createMockEvent({
  title: 'Test Event',
  location: 'Library',
})
// All other required fields are automatically filled with sensible defaults
```

## Maintenance

When backend types change:
1. Update the factory function in `testHelpers.ts`
2. All tests automatically get the updated type
3. TypeScript will catch any tests that need updates

## Adding New Factories

To add a new mock factory:

1. Import the type from the appropriate API file
2. Create a factory function following the pattern:

```typescript
export function createMockYourType(overrides: Partial<YourType> = {}): YourType {
  return {
    // All required fields with sensible defaults
    id: 1,
    name: 'Test Name',
    ...overrides, // Allow customization
  }
}
```

3. Optionally add a plural version:

```typescript
export function createMockYourTypes(count: number, overrides: Partial<YourType> = {}): YourType[] {
  return Array.from({ length: count }, (_, index) =>
    createMockYourType({
      id: index + 1,
      name: `Test Name ${index + 1}`,
      ...overrides,
    })
  )
}
```

## Questions or Issues?

If you encounter issues with the test helpers or need additional factory functions, please:
1. Check if the factory exists for your type
2. Verify you're using the latest version of the helpers
3. Create an issue or PR with your proposed changes
