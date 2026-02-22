import { useState } from 'react'
import { eventsApi } from '../api/events'

interface Props {
  eventId: string
}

export default function InviteForm({ eventId }: Props) {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email.trim()) return
    setLoading(true)
    setError(null)
    setSuccess(null)
    try {
      await eventsApi.invite(eventId, email.trim())
      setSuccess(`Invitation sent to ${email}`)
      setEmail('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send invitation')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} style={{ display: 'flex', gap: '0.5rem', alignItems: 'flex-end', flexWrap: 'wrap' }}>
      <div className="form-group" style={{ margin: 0, flex: 1, minWidth: '200px' }}>
        <input
          type="email"
          className="form-control"
          placeholder="Email to invite..."
          value={email}
          onChange={e => setEmail(e.target.value)}
          required
        />
      </div>
      <button type="submit" className="btn btn-primary" disabled={loading}>
        {loading ? 'Sending...' : 'Send Invite'}
      </button>
      {success && <p className="alert alert-success" style={{ width: '100%', margin: 0 }}>{success}</p>}
      {error && <p className="alert alert-error" style={{ width: '100%', margin: 0 }}>{error}</p>}
    </form>
  )
}
