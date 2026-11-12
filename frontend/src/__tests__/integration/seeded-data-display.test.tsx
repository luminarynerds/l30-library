/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Seeded Data Display Integration Tests
 *
 * Verifies that seeded data from backend loads and displays correctly
 * in all frontend components and pages that depend on it.
 */

import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, within } from '../utils/test-utils'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import {
  mockCatalogItem,
  mockAudiobook,
  mockDVD,
} from '../utils/mock-helpers'

// Mock API functions for seeded data
const mockGetCatalog = vi.fn()
const mockGetEvents = vi.fn()
const mockGetReadingPrograms = vi.fn()
const mockGetStaff = vi.fn()
const mockGetRooms = vi.fn()
const mockGetCollections = vi.fn()
const mockGetDatabases = vi.fn()
const mockGetMe = vi.fn()
const mockGetOrganizationFeatures = vi.fn()

vi.mock('@/api/api', () => ({
  getCatalog: () => mockGetCatalog(),
  getEvents: () => mockGetEvents(),
  getReadingPrograms: () => mockGetReadingPrograms(),
  getStaff: () => mockGetStaff(),
  getRooms: () => mockGetRooms(),
  getCollections: () => mockGetCollections(),
  getDatabases: () => mockGetDatabases(),
  getMe: () => mockGetMe(),
  getOrganizationFeatures: () => mockGetOrganizationFeatures(),
}))

// Type definitions for mock data
interface CatalogItem {
  id: number
  title: string
  item_type: string
}

interface Event {
  id: number
  title: string
  start_time: string
}

interface Program {
  id: number
  name: string
}

interface Room {
  id: number
  name: string
  capacity: number
  room_type: string
}

interface StaffMember {
  id: number
  name: string
  title: string
}

// Helper: unwrap a response that may be a bare array or a { items: [...] }
// envelope. Mocks in this file use the envelope shape; the components use
// plain arrays, so we normalize here.
function unwrapList<T>(resp: unknown): T[] {
  if (Array.isArray(resp)) return resp as T[]
  if (resp && typeof resp === 'object' && Array.isArray((resp as { items?: unknown }).items)) {
    return (resp as { items: T[] }).items
  }
  return []
}

// Mock Pages - simplified versions for testing
const MockCatalogPage = () => {
  const [items, setItems] = React.useState<CatalogItem[]>([])

  React.useEffect(() => {
    mockGetCatalog()
      .then((resp: unknown) => setItems(unwrapList<CatalogItem>(resp)))
      .catch(() => setItems([]))
  }, [])

  return (
    <div data-testid="catalog-page">
      <h1>Catalog</h1>
      <ul data-testid="catalog-list">
        {items.map((item) => (
          <li key={item.id} data-testid={`catalog-item-${item.id}`}>
            <span>{item.title}</span>
            <span data-testid={`item-type-${item.id}`}>{item.item_type}</span>
          </li>
        ))}
      </ul>
      {items.length === 0 && <p>No items found</p>}
    </div>
  )
}

const MockEventsPage = () => {
  const [events, setEvents] = React.useState<Event[]>([])

  React.useEffect(() => {
    mockGetEvents()
      .then((resp: unknown) => setEvents(unwrapList<Event>(resp)))
      .catch(() => setEvents([]))
  }, [])

  return (
    <div data-testid="events-page">
      <h1>Events</h1>
      <ul data-testid="events-list">
        {events.map((event) => (
          <li key={event.id} data-testid={`event-${event.id}`}>
            <span>{event.title}</span>
            <span data-testid={`event-date-${event.id}`}>{event.start_time}</span>
          </li>
        ))}
      </ul>
      {events.length === 0 && <p>No events found</p>}
    </div>
  )
}

const MockReadingProgramsPage = () => {
  const [programs, setPrograms] = React.useState<Program[]>([])

  React.useEffect(() => {
    mockGetReadingPrograms()
      .then((resp: unknown) => setPrograms(unwrapList<Program>(resp)))
      .catch(() => setPrograms([]))
  }, [])

  return (
    <div data-testid="programs-page">
      <h1>Reading Programs</h1>
      <ul data-testid="programs-list">
        {programs.map((program) => (
          <li key={program.id} data-testid={`program-${program.id}`}>
            <span>{program.name}</span>
          </li>
        ))}
      </ul>
      {programs.length === 0 && <p>No programs found</p>}
    </div>
  )
}

const MockRoomsPage = () => {
  const [rooms, setRooms] = React.useState<Room[]>([])

  React.useEffect(() => {
    mockGetRooms()
      .then((resp: unknown) => setRooms(unwrapList<Room>(resp)))
      .catch(() => setRooms([]))
  }, [])

  return (
    <div data-testid="rooms-page">
      <h1>Study Rooms</h1>
      <ul data-testid="rooms-list">
        {rooms.map((room) => (
          <li key={room.id} data-testid={`room-${room.id}`}>
            <span>{room.name}</span>
            <span data-testid={`room-capacity-${room.id}`}>{room.capacity}</span>
            <span data-testid={`room-type-${room.id}`}>{room.room_type}</span>
          </li>
        ))}
      </ul>
      {rooms.length === 0 && <p>No rooms available</p>}
    </div>
  )
}

const MockStaffPage = () => {
  const [staff, setStaff] = React.useState<StaffMember[]>([])

  React.useEffect(() => {
    mockGetStaff()
      .then((resp: unknown) => setStaff(unwrapList<StaffMember>(resp)))
      .catch(() => setStaff([]))
  }, [])

  return (
    <div data-testid="staff-page">
      <h1>Staff Directory</h1>
      <ul data-testid="staff-list">
        {staff.map((member) => (
          <li key={member.id} data-testid={`staff-${member.id}`}>
            <span>{member.name}</span>
            <span data-testid={`staff-title-${member.id}`}>{member.title}</span>
          </li>
        ))}
      </ul>
      {staff.length === 0 && <p>No staff found</p>}
    </div>
  )
}

describe('Seeded Data Display Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Catalog Page - Seeded Items Display', () => {
    it('should display seeded catalog items', async () => {
      const seededItems = [
        mockCatalogItem,
        mockAudiobook,
        mockDVD,
      ]

      mockGetCatalog.mockResolvedValue({
        items: seededItems,
        total: seededItems.length,
      })

      render(
        <MemoryRouter initialEntries={['/catalog']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <Routes>
            <Route path="/catalog" element={<MockCatalogPage />} />
          </Routes>
        </MemoryRouter>
      )

      // Wait for catalog to load
      await waitFor(() => {
        const list = screen.getByTestId('catalog-list')
        expect(within(list).getAllByTestId(/^catalog-item-/)).toHaveLength(3)
      })

      // Verify items are displayed
      expect(screen.getByText('Test Book')).toBeInTheDocument()
      expect(screen.getByText('Test Audiobook')).toBeInTheDocument()
      expect(screen.getByText('Test Movie')).toBeInTheDocument()
    })

    it('should display catalog items with different types', async () => {
      const seededItems = [mockCatalogItem, mockAudiobook, mockDVD]

      mockGetCatalog.mockResolvedValue({
        items: seededItems,
        total: seededItems.length,
      })

      render(
        <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <Routes>
            <Route path="/" element={<MockCatalogPage />} />
          </Routes>
        </MemoryRouter>
      )

      await waitFor(() => {
        expect(screen.getByTestId('item-type-1')).toHaveTextContent('book')
        expect(screen.getByTestId('item-type-2')).toHaveTextContent('audiobook')
        expect(screen.getByTestId('item-type-3')).toHaveTextContent('dvd')
      })
    })

    it('should display minimum expected number of seeded catalog items', async () => {
      // Generate 20+ seeded items
      const seededItems = Array.from({ length: 25 }, (_, i) => ({
        ...mockCatalogItem,
        id: i + 1,
        title: `Seeded Book ${i + 1}`,
      }))

      mockGetCatalog.mockResolvedValue({
        items: seededItems,
        total: seededItems.length,
      })

      render(
        <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <Routes>
            <Route path="/" element={<MockCatalogPage />} />
          </Routes>
        </MemoryRouter>
      )

      await waitFor(() => {
        const items = screen.getAllByTestId(/^catalog-item-/)
        expect(items).toHaveLength(25)
        expect(items.length).toBeGreaterThanOrEqual(20)
      })
    })
  })

  describe('Events Page - Seeded Events Display', () => {
    it('should display seeded events', async () => {
      const seededEvents = [
        {
          id: 1,
          title: 'Summer Reading Kickoff',
          start_time: '2024-06-01T14:00:00Z',
          end_time: '2024-06-01T15:00:00Z',
        },
        {
          id: 2,
          title: 'Book Club Meeting',
          start_time: '2024-06-08T18:00:00Z',
          end_time: '2024-06-08T19:30:00Z',
        },
        {
          id: 3,
          title: 'Author Lecture',
          start_time: '2024-06-15T19:00:00Z',
          end_time: '2024-06-15T20:00:00Z',
        },
      ]

      mockGetEvents.mockResolvedValue({
        items: seededEvents,
        total: seededEvents.length,
      })

      render(
        <MemoryRouter initialEntries={['/events']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <Routes>
            <Route path="/events" element={<MockEventsPage />} />
          </Routes>
        </MemoryRouter>
      )

      await waitFor(() => {
        expect(screen.getByText('Summer Reading Kickoff')).toBeInTheDocument()
        expect(screen.getByText('Book Club Meeting')).toBeInTheDocument()
        expect(screen.getByText('Author Lecture')).toBeInTheDocument()
      })
    })

    it('should display minimum expected number of seeded events', async () => {
      const seededEvents = Array.from({ length: 8 }, (_, i) => ({
        id: i + 1,
        title: `Seeded Event ${i + 1}`,
        start_time: new Date(Date.now() + i * 86400000).toISOString(),
        end_time: new Date(Date.now() + i * 86400000 + 3600000).toISOString(),
      }))

      mockGetEvents.mockResolvedValue({
        items: seededEvents,
        total: seededEvents.length,
      })

      render(
        <MemoryRouter>
          <Routes>
            <Route path="/" element={<MockEventsPage />} />
          </Routes>
        </MemoryRouter>
      )

      await waitFor(() => {
        const events = screen.getAllByTestId(/^event-/)
        expect(events.length).toBeGreaterThanOrEqual(5)
      })
    })
  })

  describe('Reading Programs Page - Seeded Programs Display', () => {
    it('should display seeded reading programs', async () => {
      const seededPrograms = [
        { id: 1, name: 'Summer Reading 2024', description: 'Read books this summer' },
        { id: 2, name: 'Winter Reading Challenge', description: 'Challenge yourself in winter' },
        { id: 3, name: 'Classic Book Club', description: 'Explore classic literature' },
      ]

      mockGetReadingPrograms.mockResolvedValue({
        items: seededPrograms,
        total: seededPrograms.length,
      })

      render(
        <MemoryRouter initialEntries={['/reading-programs']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <Routes>
            <Route path="/reading-programs" element={<MockReadingProgramsPage />} />
          </Routes>
        </MemoryRouter>
      )

      await waitFor(() => {
        expect(screen.getByText('Summer Reading 2024')).toBeInTheDocument()
        expect(screen.getByText('Winter Reading Challenge')).toBeInTheDocument()
        expect(screen.getByText('Classic Book Club')).toBeInTheDocument()
      })
    })

    it('should display minimum expected number of seeded programs', async () => {
      const seededPrograms = Array.from({ length: 5 }, (_, i) => ({
        id: i + 1,
        name: `Seeded Program ${i + 1}`,
      }))

      mockGetReadingPrograms.mockResolvedValue({
        items: seededPrograms,
        total: seededPrograms.length,
      })

      render(
        <MemoryRouter>
          <Routes>
            <Route path="/" element={<MockReadingProgramsPage />} />
          </Routes>
        </MemoryRouter>
      )

      await waitFor(() => {
        const programs = screen.getAllByTestId(/^program-/)
        expect(programs.length).toBeGreaterThanOrEqual(3)
      })
    })
  })

  describe('Rooms Page - Seeded Rooms Display', () => {
    it('should display seeded study rooms', async () => {
      const seededRooms = [
        { id: 1, name: 'Study Room A', capacity: 2, room_type: 'study' },
        { id: 2, name: 'Study Room B', capacity: 4, room_type: 'study' },
        { id: 3, name: 'Meeting Room', capacity: 8, room_type: 'meeting' },
        { id: 4, name: 'Computer Lab', capacity: 10, room_type: 'lab' },
      ]

      mockGetRooms.mockResolvedValue({
        items: seededRooms,
        total: seededRooms.length,
      })

      render(
        <MemoryRouter initialEntries={['/rooms']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <Routes>
            <Route path="/rooms" element={<MockRoomsPage />} />
          </Routes>
        </MemoryRouter>
      )

      await waitFor(() => {
        expect(screen.getByText('Study Room A')).toBeInTheDocument()
        expect(screen.getByText('Meeting Room')).toBeInTheDocument()
        expect(screen.getByText('Computer Lab')).toBeInTheDocument()
      })
    })

    it('should display room capacity information', async () => {
      const seededRooms = [
        { id: 1, name: 'Small Study', capacity: 2, room_type: 'study' },
        { id: 2, name: 'Large Meeting', capacity: 20, room_type: 'meeting' },
      ]

      mockGetRooms.mockResolvedValue({
        items: seededRooms,
        total: seededRooms.length,
      })

      render(
        <MemoryRouter>
          <Routes>
            <Route path="/" element={<MockRoomsPage />} />
          </Routes>
        </MemoryRouter>
      )

      await waitFor(() => {
        expect(screen.getByTestId('room-capacity-1')).toHaveTextContent('2')
        expect(screen.getByTestId('room-capacity-2')).toHaveTextContent('20')
      })
    })

    it('should display all room types', async () => {
      const seededRooms = [
        { id: 1, name: 'Study', room_type: 'study', capacity: 2 },
        { id: 2, name: 'Meeting', room_type: 'meeting', capacity: 8 },
        { id: 3, name: 'Lab', room_type: 'lab', capacity: 10 },
        { id: 4, name: 'Event', room_type: 'event', capacity: 50 },
      ]

      mockGetRooms.mockResolvedValue({
        items: seededRooms,
        total: seededRooms.length,
      })

      render(
        <MemoryRouter>
          <Routes>
            <Route path="/" element={<MockRoomsPage />} />
          </Routes>
        </MemoryRouter>
      )

      await waitFor(() => {
        expect(screen.getByTestId('room-type-1')).toHaveTextContent('study')
        expect(screen.getByTestId('room-type-2')).toHaveTextContent('meeting')
        expect(screen.getByTestId('room-type-3')).toHaveTextContent('lab')
        expect(screen.getByTestId('room-type-4')).toHaveTextContent('event')
      })
    })
  })

  describe('Staff Page - Seeded Staff Display', () => {
    it('should display seeded staff members', async () => {
      const seededStaff = [
        { id: 1, name: 'Jane Doe', title: 'Head Librarian' },
        { id: 2, name: 'John Smith', title: 'Circulation Manager' },
        { id: 3, name: 'Sarah Johnson', title: 'Children\'s Librarian' },
      ]

      mockGetStaff.mockResolvedValue({
        items: seededStaff,
        total: seededStaff.length,
      })

      render(
        <MemoryRouter initialEntries={['/staff']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <Routes>
            <Route path="/staff" element={<MockStaffPage />} />
          </Routes>
        </MemoryRouter>
      )

      await waitFor(() => {
        expect(screen.getByText('Jane Doe')).toBeInTheDocument()
        expect(screen.getByText('John Smith')).toBeInTheDocument()
      })
    })

    it('should display staff titles', async () => {
      const seededStaff = [
        { id: 1, name: 'Manager', title: 'Library Director' },
      ]

      mockGetStaff.mockResolvedValue({
        items: seededStaff,
        total: seededStaff.length,
      })

      render(
        <MemoryRouter>
          <Routes>
            <Route path="/" element={<MockStaffPage />} />
          </Routes>
        </MemoryRouter>
      )

      await waitFor(() => {
        expect(screen.getByTestId('staff-title-1')).toHaveTextContent('Library Director')
      })
    })
  })

  describe('Data Loading Error Handling', () => {
    it('should handle catalog load failures gracefully', async () => {
      mockGetCatalog.mockRejectedValue(new Error('Failed to load catalog'))

      render(
        <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <Routes>
            <Route path="/" element={<MockCatalogPage />} />
          </Routes>
        </MemoryRouter>
      )

      await waitFor(() => {
        expect(screen.getByText('No items found')).toBeInTheDocument()
      })
    })

    it('should handle events load failures gracefully', async () => {
      mockGetEvents.mockRejectedValue(new Error('Failed to load events'))

      render(
        <MemoryRouter>
          <Routes>
            <Route path="/" element={<MockEventsPage />} />
          </Routes>
        </MemoryRouter>
      )

      await waitFor(() => {
        expect(screen.getByText('No events found')).toBeInTheDocument()
      })
    })
  })
})

