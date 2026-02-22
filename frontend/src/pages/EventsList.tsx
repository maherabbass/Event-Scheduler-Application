import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { eventsApi } from '../api/events'
import EventCard from '../components/EventCard'
import { useAuth } from '../AuthContext'
import type { Event, EventStatus } from '../types'

export default function EventsList() {
  const { canManageEvents } = useAuth()
  const navigate = useNavigate()
  const [events, setEvents] = useState<Event[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pages, setPages] = useState(1)

  // Filters
  const [query, setQuery] = useState('')
  const [location, setLocation] = useState('')
  const [tagInput, setTagInput] = useState('')
  const [status, setStatus] = useState<EventStatus | ''>('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')

  const fetchEvents = async (p = 1) => {
    setLoading(true)
    setError(null)
    try {
      const tags = tagInput.trim() ? tagInput.split(',').map(t => t.trim()).filter(Boolean) : undefined
      const res = await eventsApi.list({
        query: query || undefined,
        location: location || undefined,
        tags,
        status: (status as EventStatus) || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        page: p,
        page_size: 12,
      })
      setEvents(res.items)
      setTotal(res.total)
      setPages(res.pages)
      setPage(p)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load events')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchEvents(1)
  }, [])

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    fetchEvents(1)
  }

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Events</h1>
        {canManageEvents && (
          <button className="btn btn-primary" onClick={() => navigate('/events/new')}>
            + Create Event
          </button>
        )}
      </div>

      <form className="search-bar" onSubmit={handleSearch}>
        <input
          type="text"
          className="form-control"
          placeholder="Search events..."
          value={query}
          onChange={e => setQuery(e.target.value)}
        />
        <input
          type="text"
          className="form-control"
          placeholder="Location..."
          value={location}
          onChange={e => setLocation(e.target.value)}
          style={{ maxWidth: '160px' }}
        />
        <input
          type="text"
          className="form-control"
          placeholder="Tags (comma-separated)"
          value={tagInput}
          onChange={e => setTagInput(e.target.value)}
          style={{ maxWidth: '200px' }}
        />
        <select
          className="form-control"
          value={status}
          onChange={e => setStatus(e.target.value as EventStatus | '')}
          style={{ maxWidth: '140px' }}
        >
          <option value="">All statuses</option>
          <option value="PUBLISHED">Published</option>
          <option value="DRAFT">Draft</option>
          <option value="CANCELLED">Cancelled</option>
        </select>
        <input
          type="date"
          className="form-control"
          placeholder="From"
          value={dateFrom}
          onChange={e => setDateFrom(e.target.value)}
          style={{ maxWidth: '150px' }}
        />
        <input
          type="date"
          className="form-control"
          placeholder="To"
          value={dateTo}
          onChange={e => setDateTo(e.target.value)}
          style={{ maxWidth: '150px' }}
        />
        <button type="submit" className="btn btn-primary">Search</button>
        <button type="button" className="btn btn-secondary" onClick={() => {
          setQuery(''); setLocation(''); setTagInput(''); setStatus(''); setDateFrom(''); setDateTo('')
          fetchEvents(1)
        }}>Clear</button>
      </form>

      {error && <div className="alert alert-error">{error}</div>}

      {loading ? (
        <div className="loading-center"><div className="spinner" /></div>
      ) : events.length === 0 ? (
        <div className="empty-state">
          <p>No events found.</p>
          {canManageEvents && (
            <button className="btn btn-primary mt-2" onClick={() => navigate('/events/new')}>
              Create the first event
            </button>
          )}
        </div>
      ) : (
        <>
          <p className="text-muted mb-2">{total} event{total !== 1 ? 's' : ''} found</p>
          <div className="events-grid">
            {events.map(event => (
              <EventCard key={event.id} event={event} />
            ))}
          </div>

          {pages > 1 && (
            <div className="pagination">
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => fetchEvents(page - 1)}
                disabled={page === 1}
              >
                ← Prev
              </button>
              <span>Page {page} of {pages}</span>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => fetchEvents(page + 1)}
                disabled={page === pages}
              >
                Next →
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
