import { NavLink } from 'react-router-dom'
import { useAuth } from '../AuthContext'

export default function Navbar() {
  const { user, logout, isAdmin, canManageEvents } = useAuth()

  return (
    <nav className="navbar">
      <NavLink to="/events" className="navbar-brand">
        Event Scheduler
      </NavLink>
      <div className="navbar-links">
        <NavLink to="/events" className={({ isActive }) => isActive ? 'active' : ''}>
          Events
        </NavLink>
        {canManageEvents && (
          <NavLink to="/events/new" className={({ isActive }) => isActive ? 'active' : ''}>
            Create Event
          </NavLink>
        )}
        {isAdmin && (
          <NavLink to="/admin" className={({ isActive }) => isActive ? 'active' : ''}>
            Admin
          </NavLink>
        )}
      </div>
      <div className="navbar-user">
        {user && (
          <>
            <span>{user.name}</span>
            <span className={`badge ${user.role === 'ADMIN' ? 'admin' : user.role === 'ORGANIZER' ? 'organizer' : ''}`}>
              {user.role}
            </span>
            <button className="btn btn-secondary btn-sm" onClick={logout}>
              Logout
            </button>
          </>
        )}
      </div>
    </nav>
  )
}
