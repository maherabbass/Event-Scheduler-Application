import { useEffect, useState } from 'react'
import { apiFetch } from '../api/client'
import { useAuth } from '../AuthContext'
import type { User, UserRole } from '../types'

const ROLES: UserRole[] = ['ADMIN', 'ORGANIZER', 'MEMBER']

export default function Admin() {
  const { isAdmin } = useAuth()
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [updating, setUpdating] = useState<string | null>(null)

  useEffect(() => {
    apiFetch<User[]>('/api/v1/admin/users')
      .then(setUsers)
      .catch(e => setError(e instanceof Error ? e.message : 'Failed to load users'))
      .finally(() => setLoading(false))
  }, [])

  const handleRoleChange = async (userId: string, role: UserRole) => {
    setUpdating(userId)
    try {
      const updated = await apiFetch<User>(`/api/v1/admin/users/${userId}/role`, {
        method: 'PATCH',
        body: JSON.stringify({ role }),
      })
      setUsers(users => users.map(u => u.id === userId ? updated : u))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to update role')
    } finally {
      setUpdating(null)
    }
  }

  if (!isAdmin) return <div className="alert alert-error">Admin access required.</div>
  if (loading) return <div className="loading-center"><div className="spinner" /></div>

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">User Management</h1>
        <span className="text-muted">{users.length} users</span>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      <div className="card">
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Provider</th>
                <th>Role</th>
                <th>Joined</th>
              </tr>
            </thead>
            <tbody>
              {users.map(user => (
                <tr key={user.id}>
                  <td>{user.name}</td>
                  <td>{user.email}</td>
                  <td>{user.oauth_provider ?? '—'}</td>
                  <td>
                    <select
                      className="form-control"
                      style={{ width: 'auto', padding: '0.25rem 0.5rem' }}
                      value={user.role}
                      disabled={updating === user.id}
                      onChange={e => handleRoleChange(user.id, e.target.value as UserRole)}
                    >
                      {ROLES.map(r => (
                        <option key={r} value={r}>{r}</option>
                      ))}
                    </select>
                  </td>
                  <td className="text-muted" style={{ fontSize: '0.8rem' }}>
                    {new Date(user.created_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
