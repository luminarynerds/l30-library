/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import apiClient from '@/lib/api-client';

interface WalkInRoom {
  id: number;
  name: string;
  description?: string;
  room_type: string;
  capacity: number;
  floor?: string;
  room_number?: string;
  amenities: string[];
  walk_in_duration_minutes: number;
  image_url?: string;
}

interface WalkInReservation {
  status: 'confirmed' | 'queued';
  reservation_id?: number;
  queue_position?: number;
  estimated_ready_minutes?: number;
  message: string;
}

interface QueueDisplay {
  room_id: number;
  room_name: string;
  queue_length: number;
  first_in_queue_wait_minutes?: number;
  rooms_available_now: number;
}

export const walkInRoomsApi = {
  // Get available rooms for walk-in booking
  async getAvailableRooms(): Promise<WalkInRoom[]> {
    return apiClient.get<WalkInRoom[]>('/walk-in/rooms/available');
  },

  // Create a walk-in reservation
  async createWalkInReservation(
    roomId: number,
    durationMinutes?: number
  ): Promise<WalkInReservation> {
    return apiClient.post<WalkInReservation>('/walk-in/reservations', {
      room_id: roomId,
      duration_minutes: durationMinutes,
    });
  },

  // Release a room early
  async releaseRoomEarly(reservationId: number): Promise<{ status: string; message: string }> {
    return apiClient.post(
      `/walk-in/reservations/${reservationId}/release-early`,
      {}
    );
  },

  // Extend a reservation
  async extendReservation(
    reservationId: number,
    additionalMinutes: number
  ): Promise<{ status: string; message: string; new_end_time: string }> {
    return apiClient.post(
      `/walk-in/reservations/${reservationId}/extend`,
      {
        additional_minutes: additionalMinutes,
      }
    );
  },

  // Record occupancy sensor reading
  async recordSensorReading(
    roomId: number,
    isOccupied: boolean,
    confidence: number = 100,
    sensorType?: string
  ): Promise<{ status: string; sensor_id: number; message: string }> {
    return apiClient.post('/walk-in/sensor-reading', {
      room_id: roomId,
      is_occupied: isOccupied,
      confidence,
      sensor_type: sensorType,
    });
  },

  // Get queue display for a room
  async getQueueDisplay(roomId: number): Promise<QueueDisplay> {
    return apiClient.get<QueueDisplay>(`/walk-in/queue-display/${roomId}`);
  },

  // Get entrance display (all rooms)
  async getEntranceDisplay(): Promise<QueueDisplay[]> {
    return apiClient.get<QueueDisplay[]>('/walk-in/entrance-display');
  },

  // Auto-release rooms (called by background job)
  async autoReleaseRooms(roomId: number): Promise<{ status: string; released_count: number }> {
    return apiClient.post(`/walk-in/rooms/${roomId}/auto-release`, {});
  },
};
