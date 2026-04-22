import { useEffect, useRef, useState } from 'react'
import Sidebar from './components/Sidebar'
import ChatWindow from './components/ChatWindow'

export default function App() {
  const [connected, setConnected] = useState(false)
  const chatRef = useRef(null)

  useEffect(() => {
    // Check if just returned from OAuth
    if (window.location.search.includes('connected=true')) {
      setConnected(true)
      window.history.replaceState({}, '', '/')
      return
    }

    // Check persisted token status from backend on every load
    fetch('http://localhost:3001/api/auth/status')
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
