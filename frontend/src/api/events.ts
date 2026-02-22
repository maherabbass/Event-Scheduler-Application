import { apiFetch } from './client'
import type {
  Attendee,
  Event,
  EventListResponse,
  EventStatus,
  Invitation,
  RSVPStatus,
  SuggestInviteesResponse,
} from '../types'

export interface ListEventsParams {
  query?: string
  location?: string
  tags?: string[]
  status?: EventStatus
  date_from?: string
  date_to?: string
  page?: number
  page_size?: number
}

export const eventsApi = {
  list(params: ListEventsParams = {}): Promise<EventListResponse> {
    const qs = new URLSearchParams()
    if (params.query) qs.set('query', params.query)
    if (params.location) qs.set('location', params.location)
    if (params.tags) params.tags.forEach(t => qs.append('tags', t))
    if (params.status) qs.set('status', params.status)
    if (params.date_from) qs.set('date_from', params.date_from)
    if (params.date_to) qs.set('date_to', params.date_to)
    if (params.page) qs.set('page', String(params.page))
    if (params.page_size) qs.set('page_size', String(params.page_size))
    const query = qs.toString()
    return apiFetch<EventListResponse>(`/api/v1/events${query ? '?' + query : ''}`)
  },

  get(id: string): Promise<Event> {
    return apiFetch<Event>(`/api/v1/events/${id}`)
  },

  create(data: Partial<Event>): Promise<Event> {
    return apiFetch<Event>('/api/v1/events', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  update(id: string, data: Partial<Event>): Promise<Event> {
    return apiFetch<Event>(`/api/v1/events/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  },

  delete(id: string): Promise<void> {
    return apiFetch<void>(`/api/v1/events/${id}`, { method: 'DELETE' })
  },

  rsvp(eventId: string, rsvp_status: RSVPStatus): Promise<Attendee> {
    return apiFetch<Attendee>(`/api/v1/events/${eventId}/rsvp`, {
      method: 'POST',
      body: JSON.stringify({ rsvp_status }),
    })
  },

  getAttendees(eventId: string): Promise<Attendee[]> {
    return apiFetch<Attendee[]>(`/api/v1/events/${eventId}/attendees`)
  },

  invite(eventId: string, invited_email: string): Promise<Invitation> {
    return apiFetch<Invitation>(`/api/v1/events/${eventId}/invite`, {
      method: 'POST',
      body: JSON.stringify({ invited_email }),
    })
  },

  suggestInvitees(eventId: string, top_n = 10): Promise<SuggestInviteesResponse> {
    return apiFetch<SuggestInviteesResponse>(
      `/api/v1/events/${eventId}/ai/suggest-invitees?top_n=${top_n}`,
      { method: 'POST' },
    )
  },
}
