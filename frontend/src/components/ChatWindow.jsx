import { useState, useRef, useEffect, forwardRef, useImperativeHandle } from 'react'

const CODE_EXTENSIONS = ['js','jsx','ts','tsx','py','java','cpp','c','cs','go','rb','php','html','css','json','sql','rs','swift','kt','txt','md']

const ChatWindow = forwardRef(function ChatWindow(_, ref) {
  const [messages, setMessages]           = useState([])
  const [input, setInput]                 = useState('')
  const [loading, setLoading]             = useState(false)
  const [selectedImage, setSelectedImage] = useState(null)
  const [imagePreview, setImagePreview]   = useState(null)
  const [selectedCode, setSelectedCode]   = useState(null)
  const [codeFilename, setCodeFilename]   = useState('')
  const bottomRef   = useRef(null)
  const fileRef     = useRef(null)
  const textareaRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useImperativeHandle(ref, () => ({
    sendPrompt(prompt) {
      setInput(prompt)
      setTimeout(() => sendMessage(prompt), 0)
    }
  }))

  function handleFileSelect(e) {
    const file = e.target.files[0]
    if (!file) return
    const ext = file.name.split('.').pop().toLowerCase()
    if (['jpg','jpeg','png','gif','webp'].includes(ext)) {
      setSelectedCode(null); setCodeFilename('')
      setImagePreview(URL.createObjectURL(file))
      const r = new FileReader()
      r.onload = () => setSelectedImage(r.result)
      r.readAsDataURL(file)
    } else if (CODE_EXTENSIONS.includes(ext)) {
      setSelectedImage(null); setImagePreview(null)
      setCodeFilename(file.name)
      const r = new FileReader()
      r.onload = (ev) => setSelectedCode(ev.target.result)
      r.readAsText(file)
    }
    fileRef.current.value = ''
  }

  function removeFile() {
    setSelectedImage(null); setImagePreview(null)
    setSelectedCode(null); setCodeFilename('')
  }

  async function sendMessage(promptOverride) {
    const userMsg = (promptOverride ?? input).trim()
    if ((!userMsg && !selectedImage && !selectedCode) || loading) return
    const img      = selectedImage
    const code     = selectedCode
    const filename = codeFilename

    setInput(''); removeFile(); setLoading(true)
    if (textareaRef.current) textareaRef.current.style.height = 'auto'

    setMessages(prev => [...prev, {
      role: 'user',
      content: userMsg || (img ? 'Analyze this image' : `Analyze ${filename}`),
      image: img, filename
    }])

    try {
      const res  = await fetch('http://localhost:3001/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMsg || (img ? 'Describe this image.' : `Analyze ${filename}`),
          image: img, code, filename
        })
      })
      const data = await res.json()
      setMessages(prev => [...prev, { role: 'assistant', content: data.reply || data.error }])
    } catch {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Something went wrong. Is the backend running?' }])
    }
    setLoading(false)
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage() }
  }

  function handleInput(e) {
    setInput(e.target.value)
    e.target.style.height = 'auto'
    e.target.style.height = Math.min(e.target.scrollHeight, 140) + 'px'
  }

  const hour = new Date().getHours()
  const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening'

  return (
    <div style={{
      flex: 1, display: 'flex', flexDirection: 'column',
      background: '#0d1117', overflow: 'hidden'
    }}>

      {/* Header */}
      <div style={{
        padding: '14px 24px',
        background: '#0d1117',
        borderBottom: '1px solid #21262d',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between'
      }}>
        <div>
          <div style={{ fontSize: '14px', fontWeight: '600', color: '#e6edf3' }}>{greeting}</div>
          <div style={{ fontSize: '12px', color: '#484f58', marginTop: '1px' }}>What can I help you with today?</div>
        </div>
        <div style={{ display: 'flex', gap: '6px' }}>
          {[
            { label: 'Drive',    bg: '#0d2137', color: '#58a6ff' },
            { label: 'Gmail',    bg: '#2d1a1a', color: '#f85149' },
            { label: 'Calendar', bg: '#2d2200', color: '#e6a817' },
            { label: 'Notion',   bg: '#1e1e2e', color: '#a5b4fc' },
          ].map(a => (
            <span key={a.label} style={{
              padding: '3px 10px', borderRadius: '6px',
              fontSize: '11px', fontWeight: '500',
              background: a.bg, color: a.color,
              border: `1px solid ${a.color}30`
            }}>{a.label}</span>
          ))}
        </div>
      </div>

      {/* Messages */}
      <div style={{
        flex: 1, overflowY: 'auto', padding: '24px 0',
        display: 'flex', flexDirection: 'column', gap: '6px'
      }}>
        {messages.length === 0 && <EmptyState onSuggestion={setInput} />}

        {messages.map((msg, i) => (
          <MessageRow key={i} msg={msg} />
        ))}

        {loading && (
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px', padding: '4px 24px' }}>
            <div style={{
              width: '30px', height: '30px', borderRadius: '50%', flexShrink: 0,
              background: 'linear-gradient(135deg, #e6a817, #f5c842)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: '10px', color: '#0d1117', fontWeight: '800'
            }}>OC</div>
            <div style={{
              background: '#161b22', borderRadius: '12px', borderTopLeftRadius: '3px',
              padding: '12px 16px', display: 'flex', gap: '5px', alignItems: 'center',
              border: '1px solid #21262d'
            }}>
              {[0,1,2].map(i => (
                <div key={i} style={{
                  width: '6px', height: '6px', borderRadius: '50%',
                  background: '#e6a817',
                  animation: `pulse 1.2s ease-in-out ${i * 0.2}s infinite`
                }}/>
              ))}
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div style={{ padding: '12px 20px 18px', borderTop: '1px solid #21262d' }}>

        {/* File preview */}
        {(imagePreview || codeFilename) && (
          <div style={{
            display: 'flex', alignItems: 'center', gap: '8px',
            marginBottom: '8px', padding: '8px 12px',
            background: '#161b22', borderRadius: '8px',
            border: '1px solid #21262d'
          }}>
            {imagePreview && (
              <img src={imagePreview} alt="preview" style={{
                height: '38px', borderRadius: '6px', border: '1px solid #21262d'
              }}/>
            )}
            {codeFilename && (
              <div style={{
                background: '#0d1117', color: '#3fb950',
                padding: '4px 10px', borderRadius: '6px',
                fontSize: '12px', fontFamily: 'monospace',
                border: '1px solid #21262d'
              }}>{codeFilename}</div>
            )}
            <button onClick={removeFile} style={{
              marginLeft: 'auto', width: '20px', height: '20px', borderRadius: '4px',
              background: '#f8514920', color: '#f85149', border: '1px solid #f8514940',
              cursor: 'pointer', fontSize: '11px', display: 'flex',
              alignItems: 'center', justifyContent: 'center'
            }}>✕</button>
          </div>
        )}

        <div style={{
          display: 'flex', alignItems: 'flex-end', gap: '10px',
          background: '#161b22', borderRadius: '12px',
          border: '1px solid #30363d',
          padding: '10px 12px',
        }}>
          <input type="file"
            accept="image/*,.js,.jsx,.ts,.tsx,.py,.java,.cpp,.c,.cs,.go,.rb,.php,.html,.css,.json,.sql"
            ref={fileRef} onChange={handleFileSelect}
            style={{ display: 'none' }}
          />
          <button onClick={() => fileRef.current.click()} style={{
            width: '30px', height: '30px', borderRadius: '6px',
            background: '#21262d', border: '1px solid #30363d',
            cursor: 'pointer', color: '#8b949e', fontSize: '16px',
            display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0
          }}>⊕</button>

          <textarea
            ref={textareaRef}
            value={input}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            placeholder={
              selectedCode  ? `Ask about ${codeFilename}...` :
              selectedImage ? 'Ask about the image...' :
              'Ask anything about your workspace...'
            }
            rows={1}
            style={{
              flex: 1, border: 'none', outline: 'none',
              fontSize: '14px', fontFamily: 'inherit',
              resize: 'none', background: 'transparent',
              color: '#e6edf3', lineHeight: '1.6',
              maxHeight: '140px', overflowY: 'auto'
            }}
          />

          <button
            onClick={() => sendMessage()}
            disabled={loading}
            style={{
              width: '32px', height: '32px', borderRadius: '8px',
              background: loading ? '#21262d' : 'linear-gradient(135deg, #e6a817, #f5c842)',
              border: 'none', cursor: loading ? 'not-allowed' : 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              flexShrink: 0, transition: 'opacity 0.15s'
            }}
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
              stroke={loading ? '#484f58' : '#0d1117'} strokeWidth="2.5">
              <line x1="22" y1="2" x2="11" y2="13"/>
              <polygon points="22 2 15 22 11 13 2 9 22 2"/>
            </svg>
          </button>
        </div>
        <div style={{ textAlign: 'center', fontSize: '11px', color: '#30363d', marginTop: '8px' }}>
          Enter to send · Shift+Enter for new line
        </div>
      </div>

      <style>{`
        @keyframes pulse {
          0%,100% { transform: scale(0.8); opacity: 0.3; }
          50% { transform: scale(1.2); opacity: 1; }
        }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #21262d; border-radius: 4px; }
      `}</style>
    </div>
  )
})

export default ChatWindow

function MessageRow({ msg }) {
  const isUser = msg.role === 'user'
  return (
    <div style={{
      display: 'flex', gap: '12px', padding: '4px 24px',
      flexDirection: isUser ? 'row-reverse' : 'row',
      alignItems: 'flex-start'
    }}>
      <div style={{
        width: '30px', height: '30px', borderRadius: '50%', flexShrink: 0,
        background: isUser
          ? '#21262d'
          : 'linear-gradient(135deg, #e6a817, #f5c842)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: '10px', fontWeight: '800',
        color: isUser ? '#8b949e' : '#0d1117',
        marginTop: '2px', border: isUser ? '1px solid #30363d' : 'none'
      }}>
        {isUser ? 'G' : 'OC'}
      </div>

      <div style={{
        maxWidth: '68%', display: 'flex', flexDirection: 'column',
        gap: '4px', alignItems: isUser ? 'flex-end' : 'flex-start'
      }}>
        <span style={{ fontSize: '11px', color: '#484f58', fontWeight: '500' }}>
          {isUser ? 'You' : 'Omni Copilot'}
        </span>
        {msg.image && (
          <img src={msg.image} alt="upload" style={{
            maxWidth: '100%', maxHeight: '200px', borderRadius: '10px',
            border: '1px solid #21262d', objectFit: 'cover'
          }}/>
        )}
        {msg.filename && (
          <div style={{
            background: '#0d1117', color: '#3fb950',
            padding: '4px 10px', borderRadius: '6px',
            fontSize: '12px', fontFamily: 'monospace',
            border: '1px solid #21262d'
          }}>{msg.filename}</div>
        )}
        <div style={{
          padding: '10px 16px',
          borderRadius: isUser ? '12px 12px 3px 12px' : '12px 12px 12px 3px',
          fontSize: '14px', lineHeight: '1.65', whiteSpace: 'pre-wrap',
          background: isUser ? '#1c2128' : '#161b22',
          color: isUser ? '#e6edf3' : '#c9d1d9',
          border: isUser ? '1px solid #e6a81730' : '1px solid #21262d',
          boxShadow: isUser ? '0 0 0 1px #e6a81715' : 'none'
        }}>
          {msg.content}
        </div>
      </div>
    </div>
  )
}

function EmptyState({ onSuggestion }) {
  const suggestions = [
    { text: 'Find my resume in Drive',        icon: '📁' },
    { text: 'Show unread emails',             icon: '📧' },
    { text: 'What meetings do I have today?', icon: '📅' },
    { text: 'Search my Notion notes',         icon: '📝' },
  ]
  return (
    <div style={{
      margin: 'auto', textAlign: 'center',
      padding: '40px 24px', maxWidth: '460px',
      width: '100%', alignSelf: 'center'
    }}>
      <div style={{
        width: '52px', height: '52px',
        background: 'linear-gradient(135deg, #e6a817, #f5c842)',
        borderRadius: '14px', margin: '0 auto 18px',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: '24px', color: '#0d1117', fontWeight: '900',
        boxShadow: '0 8px 24px rgba(230,168,23,0.25)'
      }}>O</div>
      <div style={{ fontSize: '18px', fontWeight: '700', color: '#e6edf3', marginBottom: '6px' }}>
        Omni Copilot
      </div>
      <div style={{ fontSize: '13px', color: '#484f58', marginBottom: '28px' }}>
        Your entire workspace, one conversation
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
        {suggestions.map(s => (
          <button key={s.text}
            onClick={() => onSuggestion(s.text)}
            style={{
              padding: '12px 14px', borderRadius: '10px', fontSize: '12px',
              border: '1px solid #21262d', background: '#161b22',
              color: '#8b949e', cursor: 'pointer', textAlign: 'left',
              display: 'flex', alignItems: 'center', gap: '8px',
              transition: 'all 0.15s'
            }}
            onMouseEnter={e => {
              e.currentTarget.style.borderColor = '#e6a81760'
              e.currentTarget.style.color = '#e6edf3'
              e.currentTarget.style.background = '#1c2128'
            }}
            onMouseLeave={e => {
              e.currentTarget.style.borderColor = '#21262d'
              e.currentTarget.style.color = '#8b949e'
              e.currentTarget.style.background = '#161b22'
            }}
          >
            <span style={{ fontSize: '15px' }}>{s.icon}</span>
            {s.text}
          </button>
        ))}
      </div>
    </div>
  )
}
