import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import { captureTokenFromUrl, requireSession } from './api/auth'

// Before anything renders: if the portal redirected here with a token in the
// URL fragment, store it and strip it from the address bar. Runs once, and is
// a no-op when the dashboard is opened directly.
captureTokenFromUrl()

// Then, if there is no usable session and a portal is configured, leave for it
// without rendering. Mounting the app first would flash a dashboard at someone
// who has just signed out, which reads as the sign-out having failed.
if (!requireSession()) {
  createRoot(document.getElementById('root')).render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
}
