import { useEffect, useRef, useState } from 'react'
import Sidebar from './components/Sidebar'
import ChatWindow from './components/ChatWindow'

export default function App() {
  const [connected, setConnected] = useState(false)
  const chatRef = useRef(null)

  useEffect(() => {
    if (window.location.search.includes('connected=true')) {
      setConnected(true)
      window.history.replaceState({}, '', '/')
    }
  }, [])

  function handleNav(prompt) {
    chatRef.current?.sendPrompt(prompt)
  }

  return (
    <div style={{
      display: 'flex',
      height: '100vh',
      fontFamily: 'system-ui, -apple-system, sans-serif',
      background: '#0d1117',
      overflow: 'hidden'
    }}>
      <Sidebar connected={connected} onNav={handleNav} />
      <ChatWindow ref={chatRef} />
    </div>
  )
}
