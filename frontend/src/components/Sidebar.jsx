import { useState } from 'react'

export default function Sidebar({ connected, onNav }) {
  const [active, setActive] = useState('Chat')

  const navItems = [
    { label: 'Chat',     icon: ChatIcon,     prompt: null },
    { label: 'Drive',    icon: FolderIcon,   prompt: 'List my recent files in Google Drive' },
    { label: 'Gmail',    icon: MailIcon,     prompt: 'Show my unread emails' },
    { label: 'Calendar', icon: CalendarIcon, prompt: 'What meetings do I have today?' },
    { label: 'Notion',   icon: NoteIcon,     prompt: 'Search my Notion notes' },
    { label: 'Code',     icon: CodeIcon,     prompt: 'Help me with code' },
  ]

  return (
    <div style={{
      width: '210px',
      background: '#0d1117',
      display: 'flex',
      flexDirection: 'column',
      flexShrink: 0,
      padding: '20px 14px',
      gap: '2px',
      borderRight: '1px solid #21262d'
    }}>

      {/* Logo */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: '10px',
        padding: '4px 8px 18px',
        borderBottom: '1px solid #21262d',
        marginBottom: '14px'
      }}>
        <div style={{
          width: '30px', height: '30px', flexShrink: 0,
          background: 'linear-gradient(135deg, #e6a817, #f5c842)',
          borderRadius: '8px', display: 'flex', alignItems: 'center',
          justifyContent: 'center', fontSize: '14px',
          color: '#0d1117', fontWeight: '900'
        }}>O</div>
        <span style={{ color: '#e6edf3', fontSize: '14px', fontWeight: '700', letterSpacing: '-0.2px' }}>
          Omni Copilot
        </span>
      </div>

      {/* Section label */}
      <div style={{
        fontSize: '10px', color: '#484f58', fontWeight: '600',
        letterSpacing: '0.8px', textTransform: 'uppercase',
        padding: '0 8px', marginBottom: '6px'
      }}>
        Workspace
      </div>

      {/* Nav items */}
      {navItems.map(item => {
        const isActive = active === item.label
        return (
          <div key={item.label}
            onClick={() => {
              setActive(item.label)
              if (item.prompt) onNav(item.prompt)
            }}
            style={{
              display: 'flex', alignItems: 'center', gap: '10px',
              padding: '8px 10px', borderRadius: '8px',
              cursor: 'pointer',
              background: isActive ? '#e6a81718' : 'transparent',
              color: isActive ? '#e6a817' : '#8b949e',
              fontSize: '13px', fontWeight: isActive ? '600' : '400',
              transition: 'all 0.15s',
              userSelect: 'none',
              borderLeft: isActive ? '2px solid #e6a817' : '2px solid transparent'
            }}
            onMouseEnter={e => {
              if (!isActive) {
                e.currentTarget.style.background = '#161b22'
                e.currentTarget.style.color = '#c9d1d9'
              }
            }}
            onMouseLeave={e => {
              if (!isActive) {
                e.currentTarget.style.background = 'transparent'
                e.currentTarget.style.color = '#8b949e'
              }
            }}
          >
            <item.icon size={15} />
            {item.label}
          </div>
        )
      })}

      {/* Divider */}
      <div style={{ borderTop: '1px solid #21262d', margin: '12px 0' }} />

      {/* Google connect */}
      {connected ? (
        <div style={{
          display: 'flex', alignItems: 'center', gap: '10px',
          padding: '8px 10px', borderRadius: '8px',
          background: '#1a2e1a', color: '#3fb950', fontSize: '12px'
        }}>
          <div style={{ width: '7px', height: '7px', borderRadius: '50%',
            background: '#3fb950', flexShrink: 0 }}/>
          Google connected
        </div>
      ) : (
        <a href="http://localhost:3001/auth/google" style={{
          display: 'flex', alignItems: 'center', gap: '10px',
          padding: '8px 10px', borderRadius: '8px',
          background: '#161b22', color: '#8b949e',
          fontSize: '12px', textDecoration: 'none',
          transition: 'all 0.15s', border: '1px solid #21262d'
        }}
          onMouseEnter={e => {
            e.currentTarget.style.borderColor = '#e6a817'
            e.currentTarget.style.color = '#e6a817'
          }}
          onMouseLeave={e => {
            e.currentTarget.style.borderColor = '#21262d'
            e.currentTarget.style.color = '#8b949e'
          }}
        >
          <div style={{ width: '7px', height: '7px', borderRadius: '50%',
            background: '#f85149', flexShrink: 0 }}/>
          Connect Google
        </a>
      )}

      {/* User badge */}
      <div style={{
        marginTop: 'auto', padding: '10px',
        borderRadius: '8px', background: '#161b22',
        border: '1px solid #21262d',
        display: 'flex', alignItems: 'center', gap: '10px'
      }}>
        <div style={{
          width: '28px', height: '28px', borderRadius: '50%',
          background: 'linear-gradient(135deg, #e6a817, #f5c842)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '12px', color: '#0d1117', fontWeight: '800', flexShrink: 0
        }}>G</div>
        <div>
          <div style={{ fontSize: '12px', color: '#e6edf3', fontWeight: '500' }}>You</div>
          <div style={{ fontSize: '10px', color: '#484f58' }}>Active now</div>
        </div>
      </div>
    </div>
  )
}

function ChatIcon({ size = 15 }) {
  return <svg width={size} height={size} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
    <path d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"/>
  </svg>
}
function FolderIcon({ size = 15 }) {
  return <svg width={size} height={size} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
    <path d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/>
  </svg>
}
function MailIcon({ size = 15 }) {
  return <svg width={size} height={size} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
    <path d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
  </svg>
}
function CalendarIcon({ size = 15 }) {
  return <svg width={size} height={size} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
    <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
    <line x1="16" y1="2" x2="16" y2="6"/>
    <line x1="8" y1="2" x2="8" y2="6"/>
    <line x1="3" y1="10" x2="21" y2="10"/>
  </svg>
}
function NoteIcon({ size = 15 }) {
  return <svg width={size} height={size} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
    <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
  </svg>
}
function CodeIcon({ size = 15 }) {
  return <svg width={size} height={size} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
    <polyline points="16 18 22 12 16 6"/>
    <polyline points="8 6 2 12 8 18"/>
  </svg>
}
