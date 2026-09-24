import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import { receiveSignout } from './context/AuthContext'

// A sign-out relay hop only passes through here to clear this app's token.
// Rendering during it would flash the loading screen at someone who is signing
// out, so skip mounting entirely - the same as Readmissions' main.jsx.
if (!receiveSignout()) {
  createRoot(document.getElementById('root')).render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
}
