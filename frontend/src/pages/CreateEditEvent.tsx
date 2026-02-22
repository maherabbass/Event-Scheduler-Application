import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { eventsApi } from '../api/events'
import { useAuth } from '../AuthContext'
import type { EventStatus } from '../types'

interface FormState {
  title: string
  description: string
  location: string
  start_datetime: string
  end_datetime: string
  tags: string
  status: EventStatus
}

const DEFAULT_FORM: FormState = {
  title: '',
  description: '',
  location: '',
  start_datetime: '',
  end_datetime: '',
  tags: '',
  status: 'DRAFT',
}

function toLocalDatetime(iso: string) {
  if (!iso) return ''
  return iso.slice(0, 16)
}

function toISOString(local: string) {
  if (!local) return ''
  return new Date(local).toISOString()
}

export default function CreateEditEvent() {
  const { id } = useParams<{ id?: string }>()
  const isEdit = !!id
  const navigate = useNavigate()
  const { canManageEvents, isAdmin } = useAuth()

  const [form, setForm] = useState<FormState>(DEFAULT_FORM)
  const [loading, setLoading] = useState(false)
  const [fetchLoading, setFetchLoading] = useState(isEdit)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!isEdit || !id) return
    eventsApi.get(id).then(ev => {
      setForm({
        title: ev.title,
        description: ev.description ?? '',
        location: ev.location ?? '',
        start_datetime: toLocalDatetime(ev.start_datetime),
        end_datetime: toLocalDatetime(ev.end_datetime ?? ''),
        tags: ev.tags.join(', '),
        status: ev.status,
      })
    }).catch(e => {
      setError(e instanceof Error ? e.message : 'Failed to load event')
    }).finally(() => setFetchLoading(false))
  }, [id, isEdit])

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) => {
    setForm(f => ({ ...f, [e.target.name]: e.target.value }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    const data = {
      title: form.title,
      description: form.description || undefined,
      location: form.location || undefined,
      start_datetime: toISOString(form.start_datetime),
      end_datetime: form.end_datetime ? toISOString(form.end_datetime) : undefined,
      tags: form.tags.split(',').map(t => t.trim()).filter(Boolean),
      status: form.status,
    }

    try {
      if (isEdit && id) {
        const ev = await eventsApi.update(id, data)
        navigate(`/events/${ev.id}`)
      } else {
        const ev = await eventsApi.create(data)
        navigate(`/events/${ev.id}`)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save event')
    } finally {
      setLoading(false)
    }
  }

  if (!canManageEvents && !isAdmin) {
    return <div className="alert alert-error">Access denied.</div>
  }

  if (fetchLoading) return <div className="loading-center"><div className="spinner" /></div>

  return (
    <div style={{ maxWidth: 640, margin: '0 auto' }}>
      <div className="page-header">
        <h1 className="page-title">{isEdit ? 'Edit Event' : 'Create Event'}</h1>
        <button className="btn btn-secondary" onClick={() => navigate(isEdit ? `/events/${id}` : '/events')}>
          Cancel
        </button>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      <div className="card">
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Title *</label>
            <input
              name="title"
              className="form-control"
              value={form.title}
              onChange={handleChange}
              required
              placeholder="Event title"
            />
          </div>

          <div className="form-group">
            <label className="form-label">Description</label>
            <textarea
              name="description"
              className="form-control"
              value={form.description}
              onChange={handleChange}
              placeholder="Event description..."
              rows={4}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Location</label>
            <input
              name="location"
              className="form-control"
              value={form.location}
              onChange={handleChange}
              placeholder="City, venue, or Online"
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <div className="form-group">
              <label className="form-label">Start Date & Time *</label>
              <input
                type="datetime-local"
                name="start_datetime"
                className="form-control"
                value={form.start_datetime}
                onChange={handleChange}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">End Date & Time</label>
              <input
                type="datetime-local"
                name="end_datetime"
                className="form-control"
                value={form.end_datetime}
                onChange={handleChange}
              />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Tags (comma-separated)</label>
            <input
              name="tags"
              className="form-control"
              value={form.tags}
              onChange={handleChange}
              placeholder="technology, python, networking"
            />
          </div>

          <div className="form-group">
            <label className="form-label">Status</label>
            <select
              name="status"
              className="form-control"
              value={form.status}
              onChange={handleChange}
            >
              <option value="DRAFT">Draft</option>
              <option value="PUBLISHED">Published</option>
              <option value="CANCELLED">Cancelled</option>
            </select>
          </div>

          <button type="submit" className="btn btn-primary" disabled={loading} style={{ width: '100%' }}>
            {loading ? 'Saving...' : isEdit ? 'Update Event' : 'Create Event'}
          </button>
        </form>
      </div>
    </div>
  )
}
