import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import { captureTokenFromUrl } from './api/auth'

// Before anything renders: if the portal redirected here with a token in the
// URL fragment, store it and strip it from the address bar. Runs once, and is
// a no-op when the dashboard is opened directly.
captureTokenFromUrl()

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
