export type UserRole = 'ADMIN' | 'ORGANIZER' | 'MEMBER'

export interface User {
  id: string
  email: string
  name: string
  role: UserRole
  oauth_provider: string | null
  created_at: string
}

export type EventStatus = 'DRAFT' | 'PUBLISHED' | 'CANCELLED'
export type RSVPStatus = 'UPCOMING' | 'ATTENDING' | 'MAYBE' | 'DECLINED'

export interface Event {
  id: string
  title: string
  description: string | null
  location: string | null
  start_datetime: string
  end_datetime: string | null
  created_by: string
  tags: string[]
  status: EventStatus
  created_at: string
  updated_at: string
}

export interface EventListResponse {
  items: Event[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface Attendee {
  user_id: string
  email: string
  name: string
  rsvp_status: RSVPStatus
  responded_at: string | null
}

export interface Invitation {
  id: string
  event_id: string
  invited_email: string
  accepted: boolean
  created_at: string
}

export interface SuggestedInvitee {
  user_id: string
  name: string
  email: string
  score: number
  invitation_message: string
}

export interface SuggestInviteesResponse {
  suggestions: SuggestedInvitee[]
}
