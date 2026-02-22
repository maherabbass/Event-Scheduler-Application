import { useState } from 'react'
import { eventsApi } from '../api/events'
import type { RSVPStatus } from '../types'

interface Props {
  eventId: string
  currentStatus: RSVPStatus | null
  onUpdate?: (status: RSVPStatus) => void
}

const RSVP_OPTIONS: { value: RSVPStatus; label: string }[] = [
  { value: 'ATTENDING', label: '✅ Attending' },
  { value: 'MAYBE', label: '🤔 Maybe' },
  { value: 'DECLINED', label: '❌ Declined' },
]

export default function RSVPButton({ eventId, currentStatus, onUpdate }: Props) {
  const [status, setStatus] = useState<RSVPStatus | null>(currentStatus)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleRSVP = async (newStatus: RSVPStatus) => {
    if (loading) return
    setLoading(true)
    setError(null)
    try {
      await eventsApi.rsvp(eventId, newStatus)
      setStatus(newStatus)
      onUpdate?.(newStatus)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to update RSVP')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <div className="rsvp-group">
        {RSVP_OPTIONS.map(opt => (
          <button
            key={opt.value}
            className={`rsvp-btn ${status === opt.value ? `active-${opt.value}` : ''}`}
            onClick={() => handleRSVP(opt.value)}
            disabled={loading}
          >
            {opt.label}
          </button>
        ))}
      </div>
      {error && <p className="alert alert-error mt-1">{error}</p>}
    </div>
  )
}
