import { useState, useRef, useEffect, forwardRef, useImperativeHandle } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

const CODE_EXTENSIONS = ['js','jsx','ts','tsx','py','java','cpp','c','cs','go','rb','php','html','css','json','sql','rs','swift','kt','txt','md']

const THEME = {
  bg:          '#0a0a0f',
  surface:     '#13131a',
  surfaceHigh: '#1c1c27',
  border:      '#2a2a3d',
  borderHigh:  '#3d3d5c',
  accent:      '#f43f7a',
  accentSoft:  '#f43f7a18',
  accentGlow:  '#f43f7a30',
  accentDim:   '#f43f7a60',
  text:        '#f0eeff',
  textMid:     '#a09ab8',
  textDim:     '#4a4466',
  green:       '#34d399',
  greenBg:     '#0d2e22',
  red:         '#f87171',
}

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:3001'

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
      image: img, filename,
      time: new Date()
    }])

    try {
      const res  = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMsg || (img ? 'Describe this image.' : `Analyze ${filename}`),
          image: img, code, filename
        })
      })
      const data = await res.json()
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.reply || data.error,
        time: new Date()
      }])
    } catch {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Something went wrong. Is the backend running?',
        time: new Date()
      }])
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
      background: THEME.bg, overflow: 'hidden'
    }}>

      {/* Header */}
      <div style={{
        padding: '14px 24px',
        background: THEME.bg,
        borderBottom: `1px solid ${THEME.border}`,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between'
      }}>
        <div>
          <div style={{ fontSize: '14px', fontWeight: '600', color: THEME.text }}>{greeting}</div>
          <div style={{ fontSize: '12px', color: THEME.textDim, marginTop: '1px' }}>What can I help you with today?</div>
        </div>
        <div style={{ display: 'flex', gap: '6px' }}>
          {[
            { label: 'Drive',    bg: '#0d1a2e', color: '#60a5fa' },
            { label: 'Gmail',    bg: '#2d1a1a', color: '#f87171' },
            { label: 'Calendar', bg: '#2a1a2e', color: '#c084fc' },
            { label: 'Notion',   bg: '#1a1a2e', color: '#818cf8' },
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
            <SparkleAvatar size={30} />
            <div style={{
              background: THEME.surface, borderRadius: '12px', borderTopLeftRadius: '3px',
              padding: '12px 16px', display: 'flex', gap: '5px', alignItems: 'center',
              border: `1px solid ${THEME.border}`
            }}>
              {[0,1,2].map(i => (
                <div key={i} style={{
                  width: '6px', height: '6px', borderRadius: '50%',
                  background: THEME.accent,
                  animation: `pulse 1.2s ease-in-out ${i * 0.2}s infinite`
                }}/>
              ))}
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div style={{ padding: '12px 20px 18px', borderTop: `1px solid ${THEME.border}` }}>

        {/* File preview */}
        {(imagePreview || codeFilename) && (
          <div style={{
            display: 'flex', alignItems: 'center', gap: '8px',
            marginBottom: '8px', padding: '8px 12px',
            background: THEME.surface, borderRadius: '8px',
            border: `1px solid ${THEME.border}`
          }}>
            {imagePreview && (
              <img src={imagePreview} alt="preview" style={{
                height: '38px', borderRadius: '6px', border: `1px solid ${THEME.border}`
              }}/>
            )}
            {codeFilename && (
              <div style={{
                background: THEME.bg, color: THEME.green,
                padding: '4px 10px', borderRadius: '6px',
                fontSize: '12px', fontFamily: 'monospace',
                border: `1px solid ${THEME.border}`
              }}>{codeFilename}</div>
            )}
            <button onClick={removeFile} style={{
              marginLeft: 'auto', width: '20px', height: '20px', borderRadius: '4px',
              background: '#f8714920', color: THEME.red, border: '1px solid #f8714940',
              cursor: 'pointer', fontSize: '11px', display: 'flex',
              alignItems: 'center', justifyContent: 'center'
            }}>✕</button>
          </div>
        )}

        <div style={{
          display: 'flex', alignItems: 'flex-end', gap: '10px',
          background: THEME.surface, borderRadius: '14px',
          border: `1px solid ${THEME.borderHigh}`,
          padding: '10px 12px',
          boxShadow: `0 0 0 1px ${THEME.accentGlow}`,
        }}>
          <input type="file"
            accept="image/*,.js,.jsx,.ts,.tsx,.py,.java,.cpp,.c,.cs,.go,.rb,.php,.html,.css,.json,.sql"
            ref={fileRef} onChange={handleFileSelect}
            style={{ display: 'none' }}
          />
          <button onClick={() => fileRef.current.click()} style={{
            width: '30px', height: '30px', borderRadius: '6px',
            background: THEME.surfaceHigh, border: `1px solid ${THEME.border}`,
            cursor: 'pointer', color: THEME.textMid, fontSize: '16px',
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
              color: THEME.text, lineHeight: '1.6',
              maxHeight: '140px', overflowY: 'auto'
            }}
          />

          <button
            onClick={() => sendMessage()}
            disabled={loading}
            style={{
              width: '32px', height: '32px', borderRadius: '8px',
              background: loading ? THEME.surfaceHigh : `linear-gradient(135deg, ${THEME.accent}, #ff6b9d)`,
              border: 'none', cursor: loading ? 'not-allowed' : 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              flexShrink: 0, transition: 'opacity 0.15s',
              boxShadow: loading ? 'none' : `0 2px 12px ${THEME.accentGlow}`
            }}
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
              stroke={loading ? THEME.textDim : '#fff'} strokeWidth="2.5">
              <line x1="22" y1="2" x2="11" y2="13"/>
              <polygon points="22 2 15 22 11 13 2 9 22 2"/>
            </svg>
          </button>
        </div>
        <div style={{ textAlign: 'center', fontSize: '11px', color: THEME.textDim, marginTop: '8px' }}>
          Enter to send · Shift+Enter for new line
        </div>
      </div>

      <style>{`
        @keyframes pulse {
          0%,100% { transform: scale(0.8); opacity: 0.3; }
          50% { transform: scale(1.2); opacity: 1; }
        }
        @keyframes sparkle-spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: ${THEME.border}; border-radius: 4px; }
        .copy-btn { opacity: 0; transition: opacity 0.15s; }
        .msg-row:hover .copy-btn { opacity: 1; }

        /* Markdown styles */
        .md-body { color: ${THEME.textMid}; font-size: 14px; line-height: 1.7; }
        .md-body p { margin: 0 0 8px; }
        .md-body p:last-child { margin-bottom: 0; }
        .md-body strong { color: ${THEME.text}; font-weight: 600; }
        .md-body em { color: ${THEME.textMid}; font-style: italic; }
        .md-body h1,.md-body h2,.md-body h3 {
          color: ${THEME.text}; font-weight: 700; margin: 12px 0 6px;
        }
        .md-body h1 { font-size: 16px; }
        .md-body h2 { font-size: 15px; }
        .md-body h3 { font-size: 14px; }
        .md-body ul, .md-body ol {
          margin: 6px 0; padding-left: 20px;
        }
        .md-body li { margin: 3px 0; }
        .md-body a { color: ${THEME.accent}; text-decoration: none; }
        .md-body a:hover { text-decoration: underline; }
        .md-body blockquote {
          border-left: 3px solid ${THEME.accent};
          margin: 8px 0; padding: 4px 12px;
          color: ${THEME.textMid}; background: ${THEME.surfaceHigh};
          border-radius: 0 6px 6px 0;
        }
        .md-body hr { border: none; border-top: 1px solid ${THEME.border}; margin: 12px 0; }
        .md-body table { border-collapse: collapse; width: 100%; margin: 8px 0; font-size: 13px; }
        .md-body th {
          background: ${THEME.surfaceHigh}; color: ${THEME.text};
          padding: 6px 10px; border: 1px solid ${THEME.border}; text-align: left;
        }
        .md-body td { padding: 5px 10px; border: 1px solid ${THEME.border}; }
        .md-body code {
          background: ${THEME.surfaceHigh}; color: #f9a8d4;
          padding: 1px 6px; border-radius: 4px;
          font-family: 'Fira Code', 'Cascadia Code', monospace; font-size: 13px;
          border: 1px solid ${THEME.border};
        }
        .md-body pre {
          background: #0d0d14; border: 1px solid ${THEME.border};
          border-radius: 8px; padding: 14px 16px; overflow-x: auto;
          margin: 10px 0; position: relative;
        }
        .md-body pre code {
          background: none; border: none; padding: 0;
          color: #e2d9f3; font-size: 13px; line-height: 1.6;
        }
      `}</style>
    </div>
  )
})

export default ChatWindow

// ── Sparkle logo avatar ──────────────────────────────────────────────────────
function SparkleAvatar({ size = 30 }) {
  return (
    <div style={{
      width: size, height: size, borderRadius: '50%', flexShrink: 0,
      background: `linear-gradient(135deg, #f43f7a, #ff6b9d)`,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      boxShadow: '0 2px 10px #f43f7a40'
    }}>
      <svg width={size * 0.55} height={size * 0.55} viewBox="0 0 24 24" fill="white">
        <path d="M12 2 L13.5 9 L20 12 L13.5 15 L12 22 L10.5 15 L4 12 L10.5 9 Z"/>
      </svg>
    </div>
  )
}

// ── Message row ──────────────────────────────────────────────────────────────
function MessageRow({ msg }) {
  const isUser = msg.role === 'user'
  const [copied, setCopied] = useState(false)

  function copyToClipboard() {
    navigator.clipboard.writeText(msg.content).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  const timeStr = msg.time
    ? msg.time.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
    : ''

  return (
    <div className="msg-row" style={{
      display: 'flex', gap: '12px', padding: '4px 24px',
      flexDirection: isUser ? 'row-reverse' : 'row',
      alignItems: 'flex-start'
    }}>
      {/* Avatar */}
      {isUser ? (
        <div style={{
          width: '30px', height: '30px', borderRadius: '50%', flexShrink: 0,
          background: THEME.surfaceHigh,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '10px', fontWeight: '800', color: THEME.textMid,
          marginTop: '2px', border: `1px solid ${THEME.border}`
        }}>G</div>
      ) : (
        <div style={{ marginTop: '2px', flexShrink: 0 }}>
          <SparkleAvatar size={30} />
        </div>
      )}

      <div style={{
        maxWidth: '68%', display: 'flex', flexDirection: 'column',
        gap: '4px', alignItems: isUser ? 'flex-end' : 'flex-start'
      }}>
        {/* Name + time */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ fontSize: '11px', color: THEME.textDim, fontWeight: '500' }}>
            {isUser ? 'You' : 'Omni Copilot'}
          </span>
          {timeStr && (
            <span style={{ fontSize: '10px', color: THEME.textDim }}>{timeStr}</span>
          )}
        </div>

        {/* Image attachment */}
        {msg.image && (
          <img src={msg.image} alt="upload" style={{
            maxWidth: '100%', maxHeight: '200px', borderRadius: '10px',
            border: `1px solid ${THEME.border}`, objectFit: 'cover'
          }}/>
        )}

        {/* Code filename badge */}
        {msg.filename && (
          <div style={{
            background: THEME.bg, color: THEME.green,
            padding: '4px 10px', borderRadius: '6px',
            fontSize: '12px', fontFamily: 'monospace',
            border: `1px solid ${THEME.border}`
          }}>{msg.filename}</div>
        )}

        {/* Message bubble */}
        <div style={{ position: 'relative', width: '100%' }}>
          <div style={{
            padding: '10px 16px',
            borderRadius: isUser ? '12px 12px 3px 12px' : '12px 12px 12px 3px',
            background: isUser ? THEME.surfaceHigh : THEME.surface,
            border: isUser ? `1px solid ${THEME.accentGlow}` : `1px solid ${THEME.border}`,
            boxShadow: isUser ? `0 0 0 1px ${THEME.accentSoft}` : 'none'
          }}>
            {isUser ? (
              <div style={{
                fontSize: '14px', lineHeight: '1.65', whiteSpace: 'pre-wrap',
                color: THEME.text
              }}>
                {msg.content}
              </div>
            ) : (
              <div className="md-body">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {msg.content}
                </ReactMarkdown>
              </div>
            )}
          </div>

          {/* Copy button — only on assistant messages */}
          {!isUser && (
            <button
              className="copy-btn"
              onClick={copyToClipboard}
              title="Copy response"
              style={{
                position: 'absolute', top: '8px', right: '8px',
                width: '26px', height: '26px', borderRadius: '6px',
                background: THEME.surfaceHigh, border: `1px solid ${THEME.border}`,
                cursor: 'pointer', display: 'flex', alignItems: 'center',
                justifyContent: 'center', color: copied ? THEME.green : THEME.textMid,
                transition: 'all 0.15s'
              }}
            >
              {copied ? (
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <polyline points="20 6 9 17 4 12"/>
                </svg>
              ) : (
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                  <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/>
                </svg>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

// ── Empty state ──────────────────────────────────────────────────────────────
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
      {/* Animated logo */}
      <div style={{
        width: '60px', height: '60px',
        background: `linear-gradient(135deg, #f43f7a, #ff6b9d)`,
        borderRadius: '18px', margin: '0 auto 20px',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        boxShadow: '0 8px 32px #f43f7a35',
        animation: 'logo-glow 3s ease-in-out infinite'
      }}>
        <svg width="28" height="28" viewBox="0 0 24 24" fill="white">
          <path d="M12 2 L13.5 9 L20 12 L13.5 15 L12 22 L10.5 15 L4 12 L10.5 9 Z"/>
        </svg>
      </div>
      <div style={{ fontSize: '20px', fontWeight: '700', color: THEME.text, marginBottom: '6px' }}>
        Omni Copilot
      </div>
      <div style={{ fontSize: '13px', color: THEME.textDim, marginBottom: '28px' }}>
        Your entire workspace, one conversation
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
        {suggestions.map(s => (
          <button key={s.text}
            onClick={() => onSuggestion(s.text)}
            style={{
              padding: '12px 14px', borderRadius: '10px', fontSize: '12px',
              border: `1px solid ${THEME.border}`, background: THEME.surface,
              color: THEME.textMid, cursor: 'pointer', textAlign: 'left',
              display: 'flex', alignItems: 'center', gap: '8px',
              transition: 'all 0.15s'
            }}
            onMouseEnter={e => {
              e.currentTarget.style.borderColor = THEME.accentDim
              e.currentTarget.style.color = THEME.text
              e.currentTarget.style.background = THEME.surfaceHigh
            }}
            onMouseLeave={e => {
              e.currentTarget.style.borderColor = THEME.border
              e.currentTarget.style.color = THEME.textMid
              e.currentTarget.style.background = THEME.surface
            }}
          >
            <span style={{ fontSize: '15px' }}>{s.icon}</span>
            {s.text}
          </button>
        ))}
      </div>
      <style>{`
        @keyframes logo-glow {
          0%, 100% { box-shadow: 0 8px 32px #f43f7a35; }
          50% { box-shadow: 0 8px 40px #f43f7a60; }
        }
      `}</style>
    </div>
  )
}
