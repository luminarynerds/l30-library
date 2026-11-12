# MSW Mock Handlers

Mock Service Worker (MSW) handlers for testing frontend components with API mocking.

## Files

### `handlers-seeded-data.ts`

Comprehensive MSW handlers matching all seeded data from backend seed scripts.

**Coverage:**
- Catalog items (20+ diverse items)
- Events (5+ upcoming events)
- Reading programs (3+ programs)
- Rooms (4+ rooms with full amenities)
- Staff directory (4+ staff members)
- Database subscriptions (6+ databases)
- Collections (4+ collections)
- Announcements (2+ banners)
- Authentication (login, logout, refresh)
- User profile endpoints

**Usage:**

```typescript
import { setupServer } from 'msw/node'
import { seedDataHandlers } from '@/__tests__/mocks/handlers-seeded-data'

// Set up server with handlers
const server = setupServer(...seedDataHandlers)

// In beforeAll
beforeAll(() => server.listen())

// In afterEach
afterEach(() => server.resetHandlers())

// In afterAll
afterAll(() => server.close())
```

### `handlers.ts` (Existing)

Original MSW handlers for staff analytics, at-risk patrons, events, reviews, etc.

**Usage:**

```typescript
import { handlers } from '@/__tests__/mocks/handlers'

const server = setupServer(...handlers)
```

## Creating Custom Handlers

To create handlers matching specific seeded data:

```typescript
import { http, HttpResponse } from 'msw'

export const customHandlers = [
  http.get('${API_BASE}/custom', () => {
    return HttpResponse.json({
      items: [
        { id: 1, name: 'Item 1' },
        { id: 2, name: 'Item 2' },
      ],
      total: 2,
    })
  }),
]
```

## Combining Handlers

Use multiple handler sets together:

```typescript
import { setupServer } from 'msw/node'
import { handlers as defaultHandlers } from './handlers'
import { seedDataHandlers } from './handlers-seeded-data'

// Combine handlers (seeded data handlers override defaults)
const server = setupServer(
  ...defaultHandlers,
  ...seedDataHandlers,
)
```

## Testing with Seeded Data

### Example: Testing Catalog Page with Seeded Items

```typescript
import { render, screen, waitFor } from '@testing-library/react'
import { setupServer } from 'msw/node'
import { seedDataHandlers } from '@/__tests__/mocks/handlers-seeded-data'
import CatalogPage from '@/pages/CatalogPage'

const server = setupServer(...seedDataHandlers)

beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

it('displays seeded catalog items', async () => {
  render(<CatalogPage />)

  await waitFor(() => {
    expect(screen.getByText('Seeded Book 1')).toBeInTheDocument()
  })
})
```

### Example: Overriding Handler Response

```typescript
server.use(
  http.get('${API_BASE}/catalog', () => {
    return HttpResponse.json({
      items: [
        { id: 1, title: 'Custom Item' },
      ],
      total: 1,
    })
  })
)
```

## Data Matching

The seeded data handlers return data structures matching:
- `backend/tests/test_seeded_data_loading.py` - Expected minimum counts
- `backend/scripts/seed_*.py` - Actual seeded data structure
- `frontend/src/__tests__/utils/mock-helpers.ts` - Type definitions

## API Endpoints Covered

### Catalog
- `GET ${API_BASE}/catalog` - List all items
- `GET ${API_BASE}/catalog/:id` - Get specific item

### Events
- `GET ${API_BASE}/events` - List events
- `GET ${API_BASE}/events/:id` - Get specific event

### Reading Programs
- `GET ${API_BASE}/reading-programs` - List programs
- `GET ${API_BASE}/reading-programs/:id` - Get specific program

### Rooms
- `GET ${API_BASE}/rooms` - List rooms
- `GET ${API_BASE}/rooms/:id` - Get specific room

### Staff
- `GET ${API_BASE}/staff` - List staff
- `GET ${API_BASE}/staff/:id` - Get specific staff member

### Database Subscriptions
- `GET ${API_BASE}/databases` - List databases
- `GET ${API_BASE}/databases/:id` - Get specific database

### Collections
- `GET ${API_BASE}/collections` - List collections
- `GET ${API_BASE}/collections/:id` - Get specific collection

### Announcements
- `GET ${API_BASE}/announcements` - List announcements

### Authentication
- `POST ${API_BASE}/login` - User login
- `POST ${API_BASE}/logout` - User logout
- `POST ${API_BASE}/refresh` - Refresh token

### Users
- `GET ${API_BASE}/users/me` - Current user profile
- `GET ${API_BASE}/users/:id` - Get specific user

### Health
- `GET ${API_BASE}/health` - API health check

## Debugging

Enable logging to see all MSW requests:

```typescript
// In test setup
server.listen({ onUnhandledRequest: 'warn' })
```

View network calls in your test output when a request doesn't have a matching handler.

## References

- [MSW Documentation](https://mswjs.io/)
- [MSW API Reference](https://mswjs.io/docs/api/)
- Seeded Data: `docs/SEEDED_DATA_LOADING_CHECKLIST.md`
- Test Utilities: `src/__tests__/utils/mock-helpers.ts`
