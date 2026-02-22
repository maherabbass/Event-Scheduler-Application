import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './AuthContext'
import Navbar from './components/Navbar'
import Admin from './pages/Admin'
import AuthCallback from './pages/AuthCallback'
import CreateEditEvent from './pages/CreateEditEvent'
import EventDetail from './pages/EventDetail'
import EventsList from './pages/EventsList'
import Login from './pages/Login'

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, loading } = useAuth()
  if (loading) return <div className="loading-center"><div className="spinner" /></div>
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return <>{children}</>
}

function RequireOrganizer({ children }: { children: React.ReactNode }) {
  const { canManageEvents, isAdmin, loading } = useAuth()
  if (loading) return <div className="loading-center"><div className="spinner" /></div>
  if (!canManageEvents && !isAdmin) return <Navigate to="/events" replace />
  return <>{children}</>
}

function RequireAdmin({ children }: { children: React.ReactNode }) {
  const { isAdmin, loading } = useAuth()
  if (loading) return <div className="loading-center"><div className="spinner" /></div>
  if (!isAdmin) return <Navigate to="/events" replace />
  return <>{children}</>
}

export default function App() {
  const { isAuthenticated, loading } = useAuth()

  if (loading) {
    return (
      <div className="loading-center" style={{ minHeight: '100vh' }}>
        <div className="spinner" />
      </div>
    )
  }

  return (
    <div className="app-layout">
      {isAuthenticated && <Navbar />}
      <main className="main-content">
        <Routes>
          <Route
            path="/login"
            element={isAuthenticated ? <Navigate to="/events" replace /> : <Login />}
          />
          <Route path="/auth/callback" element={<AuthCallback />} />

          {/* Authenticated: event list and detail */}
          <Route path="/events" element={<RequireAuth><EventsList /></RequireAuth>} />
          <Route path="/events/:id" element={<RequireAuth><EventDetail /></RequireAuth>} />

          {/* Organizer/Admin: create and edit */}
          <Route
            path="/events/new"
            element={
              <RequireOrganizer>
                <CreateEditEvent />
              </RequireOrganizer>
            }
          />
          <Route
            path="/events/:id/edit"
            element={
              <RequireOrganizer>
                <CreateEditEvent />
              </RequireOrganizer>
            }
          />

          {/* Admin only */}
          <Route
            path="/admin"
            element={
              <RequireAdmin>
                <Admin />
              </RequireAdmin>
            }
          />

          <Route path="/" element={<Navigate to={isAuthenticated ? "/events" : "/login"} replace />} />
          <Route path="*" element={<Navigate to={isAuthenticated ? "/events" : "/login"} replace />} />
        </Routes>
      </main>
    </div>
  )
}
