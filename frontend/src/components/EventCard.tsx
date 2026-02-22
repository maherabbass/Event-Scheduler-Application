import { useNavigate } from 'react-router-dom'
import type { Event } from '../types'

interface Props {
  event: Event
}

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString('en-US', {
    weekday: 'short',
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default function EventCard({ event }: Props) {
  const navigate = useNavigate()

  return (
    <div className="event-card" onClick={() => navigate(`/events/${event.id}`)}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
        <h3 className="event-card-title">{event.title}</h3>
        <span className={`status-badge status-${event.status}`}>{event.status}</span>
      </div>
      <div className="event-card-meta">
        <span>📅 {formatDate(event.start_datetime)}</span>
        {event.location && <span>📍 {event.location}</span>}
      </div>
      {event.description && (
        <p style={{ fontSize: '0.875rem', color: '#64748b', marginBottom: '0.75rem', overflow: 'hidden', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}>
          {event.description}
        </p>
      )}
      {event.tags.length > 0 && (
        <div className="event-card-tags">
          {event.tags.slice(0, 4).map(tag => (
            <span key={tag} className="tag">{tag}</span>
          ))}
          {event.tags.length > 4 && <span className="tag">+{event.tags.length - 4}</span>}
        </div>
      )}
    </div>
  )
}
