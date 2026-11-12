/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * MSW Handlers for Seeded Data Endpoints
 *
 * Provides mock handlers matching seeded data structure from backend.
 * These handlers return data that matches what seed scripts create.
 *
 * Usage:
 *  import { seedDataHandlers } from './handlers-seeded-data'
 *  const server = setupServer(...seedDataHandlers)
 */

import { http, HttpResponse, PathParams } from 'msw'
import { API_BASE } from '@/api/types';
import {
  mockCatalogItem,
  mockAudiobook,
  mockDVD,
  mockUser,
} from '../utils/mock-helpers'

const API_URL = `http://localhost:8000${API_BASE}`

// ==================== Seeded Data Handlers ====================

export const seedDataHandlers = [
  // ===== CATALOG ENDPOINTS =====
  http.get(`${API_URL}/catalog`, () => {
    return HttpResponse.json({
      items: [
        mockCatalogItem,
        mockAudiobook,
        mockDVD,
        ...Array.from({ length: 20 }, (_, i) => ({
          ...mockCatalogItem,
          id: i + 4,
          title: `Seeded Book ${i + 1}`,
          isbn: `978-0-${String(i).padStart(8, '0')}-0`,
        })),
      ],
      total: 23,
      page: 1,
      page_size: 50,
    })
  }),

  http.get(`${API_URL}/catalog/:id`, ({ params }: { params: PathParams }) => {
    return HttpResponse.json({
      ...mockCatalogItem,
      id: Number(params.id),
    })
  }),

  // ===== EVENTS ENDPOINTS =====
  http.get(`${API_URL}/events`, () => {
    const now = new Date()
    return HttpResponse.json({
      items: [
        {
          id: 1,
          title: 'Summer Reading Kickoff',
          description: 'Start your summer reading adventure',
          start_time: new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000).toISOString(),
          end_time: new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000 + 3600000).toISOString(),
          location: 'Main Library',
        },
        {
          id: 2,
          title: 'Book Club Meeting',
          description: 'Monthly book discussion',
          start_time: new Date(now.getTime() + 14 * 24 * 60 * 60 * 1000).toISOString(),
          end_time: new Date(now.getTime() + 14 * 24 * 60 * 60 * 1000 + 5400000).toISOString(),
          location: 'Community Room',
        },
        {
          id: 3,
          title: 'Author Lecture',
          description: 'Meet bestselling author',
          start_time: new Date(now.getTime() + 21 * 24 * 60 * 60 * 1000).toISOString(),
          end_time: new Date(now.getTime() + 21 * 24 * 60 * 60 * 1000 + 3600000).toISOString(),
          location: 'Auditorium',
        },
        {
          id: 4,
          title: 'Children\'s Story Time',
          description: 'Interactive stories for kids',
          start_time: new Date(now.getTime() + 28 * 24 * 60 * 60 * 1000).toISOString(),
          end_time: new Date(now.getTime() + 28 * 24 * 60 * 60 * 1000 + 1800000).toISOString(),
          location: 'Children\'s Area',
        },
        {
          id: 5,
          title: 'Tech Workshop',
          description: 'Learn digital skills',
          start_time: new Date(now.getTime() + 35 * 24 * 60 * 60 * 1000).toISOString(),
          end_time: new Date(now.getTime() + 35 * 24 * 60 * 60 * 1000 + 7200000).toISOString(),
          location: 'Computer Lab',
        },
      ],
      total: 5,
      page: 1,
      page_size: 50,
    })
  }),

  http.get(`${API_URL}/events/:id`, ({ params }: { params: PathParams }) => {
    return HttpResponse.json({
      id: Number(params.id),
      title: `Event ${params.id}`,
      description: 'Event description',
      start_time: new Date().toISOString(),
      end_time: new Date(Date.now() + 3600000).toISOString(),
      location: 'Library',
    })
  }),

  // ===== READING PROGRAMS ENDPOINTS =====
  http.get(`${API_URL}/reading-programs`, () => {
    return HttpResponse.json({
      items: [
        {
          id: 1,
          name: 'Summer Reading 2024',
          description: 'Read books this summer and earn badges',
          start_date: new Date().toISOString().split('T')[0],
          end_date: new Date(Date.now() + 90 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
          is_active: true,
        },
        {
          id: 2,
          name: 'Winter Reading Challenge',
          description: 'Challenge yourself with 12 books in winter',
          start_date: new Date(Date.now() + 180 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
          end_date: new Date(Date.now() + 270 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
          is_active: false,
        },
        {
          id: 3,
          name: 'Classic Book Club',
          description: 'Explore classic literature with fellow readers',
          start_date: new Date().toISOString().split('T')[0],
          end_date: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
          is_active: true,
        },
      ],
      total: 3,
      page: 1,
      page_size: 50,
    })
  }),

  http.get(`${API_URL}/reading-programs/:id`, ({ params }: { params: PathParams }) => {
    return HttpResponse.json({
      id: Number(params.id),
      name: `Reading Program ${params.id}`,
      description: 'Program description',
      is_active: true,
    })
  }),

  // ===== ROOMS ENDPOINTS =====
  http.get(`${API_URL}/rooms`, () => {
    return HttpResponse.json({
      items: [
        {
          id: 1,
          name: 'Study Room A',
          room_type: 'study',
          capacity: 2,
          amenities: ['WiFi', 'Whiteboard'],
          operating_hours: {
            monday: { open: '09:00', close: '21:00' },
            tuesday: { open: '09:00', close: '21:00' },
            wednesday: { open: '09:00', close: '21:00' },
            thursday: { open: '09:00', close: '21:00' },
            friday: { open: '09:00', close: '21:00' },
            saturday: { open: '10:00', close: '18:00' },
            sunday: { open: 'Closed', close: 'Closed' },
          },
        },
        {
          id: 2,
          name: 'Study Room B',
          room_type: 'study',
          capacity: 4,
          amenities: ['WiFi', 'Whiteboard', 'Monitor'],
          operating_hours: {
            monday: { open: '09:00', close: '21:00' },
            tuesday: { open: '09:00', close: '21:00' },
            wednesday: { open: '09:00', close: '21:00' },
            thursday: { open: '09:00', close: '21:00' },
            friday: { open: '09:00', close: '21:00' },
            saturday: { open: '10:00', close: '18:00' },
            sunday: { open: 'Closed', close: 'Closed' },
          },
        },
        {
          id: 3,
          name: 'Meeting Room',
          room_type: 'meeting',
          capacity: 12,
          amenities: ['WiFi', 'Projector', 'Conference Phone', 'Whiteboard'],
          operating_hours: {
            monday: { open: '08:00', close: '22:00' },
            tuesday: { open: '08:00', close: '22:00' },
            wednesday: { open: '08:00', close: '22:00' },
            thursday: { open: '08:00', close: '22:00' },
            friday: { open: '08:00', close: '22:00' },
            saturday: { open: '10:00', close: '18:00' },
            sunday: { open: '12:00', close: '18:00' },
          },
        },
        {
          id: 4,
          name: 'Computer Lab',
          room_type: 'lab',
          capacity: 10,
          amenities: ['Computers', 'WiFi', 'Printer', 'Software'],
          operating_hours: {
            monday: { open: '09:00', close: '21:00' },
            tuesday: { open: '09:00', close: '21:00' },
            wednesday: { open: '09:00', close: '21:00' },
            thursday: { open: '09:00', close: '21:00' },
            friday: { open: '09:00', close: '21:00' },
            saturday: { open: '10:00', close: '18:00' },
            sunday: { open: 'Closed', close: 'Closed' },
          },
        },
        {
          id: 5,
          name: 'Event Space',
          room_type: 'event',
          capacity: 100,
          amenities: ['Projector', 'Sound System', 'Stage', 'Seating'],
          operating_hours: {
            monday: { open: '08:00', close: '23:00' },
            tuesday: { open: '08:00', close: '23:00' },
            wednesday: { open: '08:00', close: '23:00' },
            thursday: { open: '08:00', close: '23:00' },
            friday: { open: '08:00', close: '23:00' },
            saturday: { open: '09:00', close: '23:00' },
            sunday: { open: '10:00', close: '22:00' },
          },
        },
      ],
      total: 5,
      page: 1,
      page_size: 50,
    })
  }),

  http.get(`${API_URL}/rooms/:id`, ({ params }: { params: PathParams }) => {
    return HttpResponse.json({
      id: Number(params.id),
      name: `Room ${params.id}`,
      room_type: 'study',
      capacity: 2,
      amenities: [],
    })
  }),

  // ===== STAFF ENDPOINTS =====
  http.get(`${API_URL}/staff`, () => {
    return HttpResponse.json({
      items: [
        {
          id: 1,
          name: 'Jane Smith',
          title: 'Head Librarian',
          bio: 'Jane is the head librarian with 15+ years of experience',
          email: 'jane.smith@library.org',
          phone: '555-0001',
        },
        {
          id: 2,
          name: 'John Johnson',
          title: 'Circulation Manager',
          bio: 'John manages our circulation desk and patron services',
          email: 'john.johnson@library.org',
          phone: '555-0002',
        },
        {
          id: 3,
          name: 'Sarah Davis',
          title: 'Children\'s Librarian',
          bio: 'Sarah specializes in children\'s programming and literacy',
          email: 'sarah.davis@library.org',
          phone: '555-0003',
        },
        {
          id: 4,
          name: 'Michael Brown',
          title: 'Technology Coordinator',
          bio: 'Michael oversees our technology infrastructure and systems',
          email: 'michael.brown@library.org',
          phone: '555-0004',
        },
      ],
      total: 4,
      page: 1,
      page_size: 50,
    })
  }),

  http.get(`${API_URL}/staff/:id`, ({ params }: { params: PathParams }) => {
    return HttpResponse.json({
      id: Number(params.id),
      name: `Staff Member ${params.id}`,
      title: 'Librarian',
      bio: 'Staff bio',
      email: `staff${params.id}@library.org`,
    })
  }),

  // ===== DATABASE SUBSCRIPTIONS ENDPOINTS =====
  http.get(`${API_URL}/databases`, () => {
    return HttpResponse.json({
      items: [
        {
          id: 1,
          name: 'JSTOR',
          description: 'Digital library of academic journals, books, and primary sources',
          url: 'https://www.jstor.org',
          access_level: 'patron',
        },
        {
          id: 2,
          name: 'ProQuest Dissertations',
          description: 'Comprehensive dissertation and thesis database',
          url: 'https://www.proquest.com',
          access_level: 'patron',
        },
        {
          id: 3,
          name: 'EBSCO Research Databases',
          description: 'Business, education, and general reference databases',
          url: 'https://www.ebsco.com',
          access_level: 'patron',
        },
        {
          id: 4,
          name: 'Academic Search Complete',
          description: 'Multidisciplinary academic research database',
          url: 'https://www.ebscohost.com',
          access_level: 'patron',
        },
        {
          id: 5,
          name: 'Library of Congress Catalog',
          description: 'Browse the Library of Congress collection',
          url: 'https://catalog.loc.gov',
          access_level: 'public',
        },
        {
          id: 6,
          name: 'WorldCat',
          description: 'Search library catalogs worldwide',
          url: 'https://www.worldcat.org',
          access_level: 'public',
        },
      ],
      total: 6,
      page: 1,
      page_size: 50,
    })
  }),

  http.get(`${API_URL}/databases/:id`, ({ params }: { params: PathParams }) => {
    return HttpResponse.json({
      id: Number(params.id),
      name: `Database ${params.id}`,
      description: 'Database description',
      url: 'https://example.com',
      access_level: 'patron',
    })
  }),

  // ===== COLLECTIONS ENDPOINTS =====
  http.get(`${API_URL}/collections`, () => {
    return HttpResponse.json({
      items: [
        {
          id: 1,
          name: 'Staff Picks',
          description: 'Hand-picked recommendations from our librarians',
          item_count: 42,
        },
        {
          id: 2,
          name: 'Best of 2024',
          description: 'Award-winning and popular books from 2024',
          item_count: 58,
        },
        {
          id: 3,
          name: 'Bestsellers',
          description: 'Current bestselling books across all genres',
          item_count: 73,
        },
        {
          id: 4,
          name: 'New Arrivals',
          description: 'Recently added to our collection',
          item_count: 120,
        },
      ],
      total: 4,
      page: 1,
      page_size: 50,
    })
  }),

  http.get(`${API_URL}/collections/:id`, ({ params }: { params: PathParams }) => {
    return HttpResponse.json({
      id: Number(params.id),
      name: `Collection ${params.id}`,
      description: 'Collection description',
      items: [mockCatalogItem],
    })
  }),

  // ===== ANNOUNCEMENTS ENDPOINTS =====
  http.get(`${API_URL}/announcements`, () => {
    return HttpResponse.json({
      items: [
        {
          id: 1,
          title: 'Library Hours Updated',
          message: 'Starting next week, we\'re extending hours on Thursdays',
          type: 'info',
          is_active: true,
          created_at: new Date().toISOString(),
        },
        {
          id: 2,
          title: 'Summer Programming',
          message: 'Register now for our summer reading programs!',
          type: 'announcement',
          is_active: true,
          created_at: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
        },
      ],
      total: 2,
      page: 1,
      page_size: 50,
    })
  }),

  // ===== USER ENDPOINTS =====
  http.get(`${API_URL}/users/me`, () => {
    return HttpResponse.json(mockUser)
  }),

  http.get(`${API_URL}/users/:id`, ({ params }: { params: PathParams }) => {
    return HttpResponse.json({
      ...mockUser,
      id: Number(params.id),
    })
  }),

  // ===== AUTHENTICATION ENDPOINTS =====
  http.post(`${API_URL}/login`, () => {
    return HttpResponse.json({
      access_token: 'mock-jwt-token-' + Math.random().toString(36).substr(2, 9),
      token_type: 'bearer',
      user: mockUser,
    })
  }),

  http.post(`${API_URL}/logout`, () => {
    return HttpResponse.json({ message: 'Logged out successfully' })
  }),

  http.post(`${API_URL}/refresh`, () => {
    return HttpResponse.json({
      access_token: 'mock-refreshed-token-' + Math.random().toString(36).substr(2, 9),
      token_type: 'bearer',
    })
  }),

  // ===== HEALTH CHECK =====
  http.get(`${API_URL}/health`, () => {
    return HttpResponse.json({
      status: 'ok',
      database: 'connected',
      timestamp: new Date().toISOString(),
    })
  }),
]

export default seedDataHandlers