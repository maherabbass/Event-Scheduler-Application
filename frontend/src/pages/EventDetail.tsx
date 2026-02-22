import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { eventsApi } from '../api/events'
import { useAuth } from '../AuthContext'
import InviteForm from '../components/InviteForm'
import RSVPButton from '../components/RSVPButton'
import type { Attendee, Event, RSVPStatus, SuggestedInvitee } from '../types'

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default function EventDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { user, isAuthenticated, canManageEvents, isAdmin } = useAuth()

  const [event, setEvent] = useState<Event | null>(null)
  const [attendees, setAttendees] = useState<Attendee[]>([])
  const [myRSVP, setMyRSVP] = useState<RSVPStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [suggestions, setSuggestions] = useState<SuggestedInvitee[]>([])
  const [loadingSuggestions, setLoadingSuggestions] = useState(false)
  const [deleteLoading, setDeleteLoading] = useState(false)

  useEffect(() => {
    if (!id) return
    const load = async () => {
      try {
        const ev = await eventsApi.get(id)
        setEvent(ev)
        if (isAuthenticated) {
          const att = await eventsApi.getAttendees(id)
          setAttendees(att)
          if (user) {
            const mine = att.find(a => a.user_id === user.id)
            setMyRSVP(mine?.rsvp_status ?? null)
          }
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Failed to load event')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [id, isAuthenticated, user])

  const handleDelete = async () => {
    if (!event || !window.confirm('Delete this event?')) return
    setDeleteLoading(true)
    try {
      await eventsApi.delete(event.id)
      navigate('/events')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to delete event')
      setDeleteLoading(false)
    }
  }

  const handleAISuggest = async () => {
    if (!event) return
    setLoadingSuggestions(true)
    try {
      const res = await eventsApi.suggestInvitees(event.id)
      setSuggestions(res.suggestions)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'AI suggestion failed')
    } finally {
      setLoadingSuggestions(false)
    }
  }

  const canEdit = event && (isAdmin || (canManageEvents && event.created_by === user?.id))

  if (loading) return <div className="loading-center"><div className="spinner" /></div>
  if (error) return <div className="alert alert-error">{error}</div>
  if (!event) return <div className="alert alert-error">Event not found</div>

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem', alignItems: 'center' }}>
        <button className="btn btn-secondary btn-sm" onClick={() => navigate('/events')}>
          ← Back
        </button>
        {canEdit && (
          <>
            <button className="btn btn-secondary btn-sm" onClick={() => navigate(`/events/${event.id}/edit`)}>
              Edit
            </button>
            <button className="btn btn-danger btn-sm" onClick={handleDelete} disabled={deleteLoading}>
              {deleteLoading ? 'Deleting...' : 'Delete'}
            </button>
          </>
        )}
      </div>

      <div className="card mb-2">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700 }}>{event.title}</h1>
          <span className={`status-badge status-${event.status}`}>{event.status}</span>
        </div>

        <div style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap', marginBottom: '1rem', color: '#64748b' }}>
          <span>📅 {formatDate(event.start_datetime)}</span>
          {event.end_datetime && <span>→ {formatDate(event.end_datetime)}</span>}
          {event.location && <span>📍 {event.location}</span>}
        </div>

        {event.description && (
          <p style={{ marginBottom: '1rem', lineHeight: '1.7' }}>{event.description}</p>
        )}

        {event.tags.length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.375rem' }}>
            {event.tags.map(tag => <span key={tag} className="tag">{tag}</span>)}
          </div>
        )}
      </div>

      {isAuthenticated && event.status !== 'CANCELLED' && (
        <div className="card mb-2">
          <h2 className="section-title">Your RSVP</h2>
          <RSVPButton
            eventId={event.id}
            currentStatus={myRSVP}
            onUpdate={status => {
              setMyRSVP(status)
              eventsApi.getAttendees(event.id).then(setAttendees)
            }}
          />
        </div>
      )}

      {isAuthenticated && attendees.length > 0 && (
        <div className="card mb-2">
          <h2 className="section-title">Attendees ({attendees.length})</h2>
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>RSVP</th>
                </tr>
              </thead>
              <tbody>
                {attendees.map(a => (
                  <tr key={String(a.user_id)}>
                    <td>{a.name}</td>
                    <td>{a.email}</td>
                    <td>
                      <span className={`status-badge status-${a.rsvp_status === 'ATTENDING' ? 'PUBLISHED' : a.rsvp_status === 'DECLINED' ? 'CANCELLED' : 'DRAFT'}`}>
                        {a.rsvp_status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {canEdit && (
        <div className="card mb-2">
          <h2 className="section-title">Send Invitation</h2>
          <InviteForm eventId={event.id} />
          <div className="divider" />
          <h3 style={{ fontWeight: 600, marginBottom: '0.75rem' }}>AI Invite Suggestions</h3>
          <button
            className="btn btn-primary"
            onClick={handleAISuggest}
            disabled={loadingSuggestions}
          >
            {loadingSuggestions ? 'Analyzing...' : '🤖 Get AI Suggestions'}
          </button>
          {suggestions.length > 0 && (
            <div className="mt-2">
              {suggestions.map(s => (
                <div key={String(s.user_id)} className="suggestion-card">
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', marginBottom: '0.25rem' }}>
                      <strong>{s.name}</strong>
                      <span className="text-muted" style={{ fontSize: '0.8rem' }}>{s.email}</span>
                      <span className="suggestion-score">{(s.score * 100).toFixed(0)}%</span>
                    </div>
                    <p className="suggestion-message">"{s.invitation_message}"</p>
                  </div>
                  <button
                    className="btn btn-primary btn-sm"
                    onClick={() => eventsApi.invite(event.id, s.email).catch(() => {})}
                  >
                    Invite
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
