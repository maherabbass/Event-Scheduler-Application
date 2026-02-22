# Event Scheduler — Frontend

React 18 + Vite + TypeScript frontend for the Event Scheduler Application.

**Live URL**: Deployed to Netlify via GitHub Actions on every push to `main`.

---

## Tech Stack

- React 18
- React Router v6
- Vite 5
- TypeScript 5

---

## Local Development

### Prerequisites
- Node 20+
- Backend running at `http://localhost:8000` (see root `README.md`)

### Setup

```bash
npm install
npm run dev
# App at http://localhost:5173
```

The Vite dev server proxies `/api/*` and `/health` to `http://localhost:8000` — no CORS config needed locally.

### Build

```bash
npm run build   # TypeScript check + Vite bundle → dist/
npm run preview # Serve the production build locally
```

---

## Environment Variables

For local dev, no `.env` file is needed — the proxy handles API routing.

For production builds (Netlify), set as a build-time environment variable in the Netlify dashboard:

| Variable | Description |
|---|---|
| `VITE_API_URL` | Backend base URL, e.g. `https://event-scheduler-api-ew.a.run.app` |

See `frontend/.env.example` for reference.

---

## Project Structure

```
frontend/src/
  main.tsx              Entry point
  App.tsx               Route definitions
  AuthContext.tsx       JWT auth state (login, logout, role checks)
  types.ts              Shared TypeScript interfaces
  index.css             Global styles and CSS variables
  api/
    client.ts           fetch wrapper with JWT header injection
    auth.ts             /auth/me, OAuth login URL builder
    events.ts           All event, RSVP, invitation, AI API calls
  components/
    Navbar.tsx          Top navigation bar
    EventCard.tsx       Event summary card (grid)
    RSVPButton.tsx      Attending / Maybe / Declined toggle buttons
    InviteForm.tsx      Email invitation form
    Pagination.tsx      Page number navigation
  pages/
    Login.tsx           Google + GitHub OAuth buttons
    AuthCallback.tsx    Capture ?token= from OAuth redirect
    EventsList.tsx      Filterable event grid
    EventDetail.tsx     Full event view, RSVP, attendees, invitations, AI
    CreateEditEvent.tsx Create / edit event form (Organizer / Admin)
    Admin.tsx           User role management (Admin only)
```

---

## OAuth Flow

1. User clicks "Continue with Google/GitHub" on the Login page
2. Browser redirects to `GET /api/v1/auth/login/{provider}`
3. Backend redirects to the OAuth provider
4. Provider redirects back to `GET /api/v1/auth/callback/{provider}`
5. Backend issues a JWT and redirects to `/auth/callback?token=<jwt>`
6. `AuthCallback.tsx` stores the token in `localStorage` and redirects to `/events`

---

## Deployment (Netlify)

Triggered automatically by `.github/workflows/deploy-frontend.yml` on push to `main`.

Manual deploy:
```bash
npm run build
# Upload dist/ to Netlify, or use Netlify CLI:
netlify deploy --prod --dir=dist
```

The `netlify.toml` and `public/_redirects` both configure SPA fallback routing so deep links work on refresh.
