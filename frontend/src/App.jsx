import { useEffect, useRef, useState } from 'react'
import Sidebar from './components/Sidebar'
import ChatWindow from './components/ChatWindow'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:3001'

export default function App() {
  const [connected, setConnected] = useState(false)
  const chatRef = useRef(null)

  useEffect(() => {
    if (window.location.search.includes('connected=true')) {
      setConnected(true)
      window.history.replaceState({}, '', '/')
      return
    }

    fetch(`${API_BASE}/api/auth/status`)
      .then(r => r.json())
      .then(data => { if (data.connected) setConnected(true) })
      .catch(() => {})
  }, [])

  function handleNav(prompt) {
    chatRef.current?.sendPrompt(prompt)
  }

  return (
    <div style={{
      display: 'flex',
      height: '100vh',
      fontFamily: 'system-ui, -apple-system, sans-serif',
      background: '#0a0a0f',
      overflow: 'hidden'
    }}>
      <Sidebar connected={connected} onNav={handleNav} />
      <ChatWindow ref={chatRef} />
    </div>
  )
}
