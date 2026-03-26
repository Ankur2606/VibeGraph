import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

const INITIAL_MESSAGES = [
  {
    id: 1,
    role: 'bot',
    text: "Hi! I'm the **Graph Agent** for your O2C data. Ask me anything about sales orders, deliveries, billing documents, payments, or customers.",
    time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    code: null,
  },
]

function MessageBubble({ msg }) {
  const isBot = msg.role === 'bot'

  return (
    <div className={`message ${isBot ? 'bot' : 'user'}`}>
      <div className="message-bubble">
        <ReactMarkdown 
          remarkPlugins={[remarkGfm]}
          components={{
            table: ({node, ...props}) => (
              <div className="result-table-container">
                <table className="result-table" {...props} />
              </div>
            ),
            p: ({node, ...props}) => <p style={{ margin: '0 0 0.5rem 0' }} {...props} />,
            hr: ({node, ...props}) => <hr style={{ border: 0, borderBottom: '1px solid rgba(255,255,255,0.1)', margin: '1rem 0' }} {...props} />,
            a: ({node, ...props}) => <a style={{ color: 'var(--accent-blue)', textDecoration: 'none' }} {...props} />,
            ul: ({node, ...props}) => <ul style={{ paddingLeft: '1.5rem', margin: '0.5rem 0' }} {...props} />,
            ol: ({node, ...props}) => <ol style={{ paddingLeft: '1.5rem', margin: '0.5rem 0' }} {...props} />,
            li: ({node, ...props}) => <li style={{ marginBottom: '0.25rem' }} {...props} />
          }}
        >
          {msg.text}
        </ReactMarkdown>
      </div>
      {msg.code && (
        <div className="message-code" style={{ maxWidth: 300, marginTop: 6 }}>
          {msg.code}
        </div>
      )}
      <div className="message-time">{msg.time}</div>
    </div>
  )
}

export default function ChatSidebar() {
  const [messages, setMessages] = useState(INITIAL_MESSAGES)
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const sendMessage = async () => {
    const text = input.trim()
    if (!text || loading) return

    const userMsg = {
      id: Date.now(),
      role: 'user',
      text,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      code: null,
    }
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const API_BASE = import.meta.env.VITE_API_BASE_URL || ''
      const resp = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      })

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: 'Unknown error' }))
        throw new Error(err.detail || `HTTP ${resp.status}`)
      }

      const data = await resp.json()
      const botMsg = {
        id: Date.now() + 1,
        role: 'bot',
        text: data.answer || 'No response received.',
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        code: data.code_type !== 'none' ? data.code : null,
      }
      setMessages((prev) => [...prev, botMsg])
    } catch (e) {
      const errMsg = {
        id: Date.now() + 1,
        role: 'bot',
        text: `❌ Error: ${e.message}`,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        code: null,
      }
      setMessages((prev) => [...prev, errMsg])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="chat-sidebar">
      {/* Header */}
      <div className="chat-header">
        <div className="chat-title">Chat with Graph</div>
        <div className="chat-subtitle">Order to Cash</div>
        <div className="chat-agent-row">
          <div className="agent-avatar">D</div>
          <div className="agent-info">
            <div className="agent-name">Graph Agent</div>
            <div className="agent-status">
              <div className="status-dot" />
              {loading ? 'thinking…' : 'awaiting instructions'}
            </div>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="messages-container">
        {messages.map((msg) => (
          <MessageBubble key={msg.id} msg={msg} />
        ))}

        {loading && (
          <div className="message bot">
            <div className="typing-indicator">
              <div className="typing-dot" />
              <div className="typing-dot" />
              <div className="typing-dot" />
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="chat-input-area">
        <textarea
          ref={inputRef}
          className="chat-input"
          placeholder="Ask about orders, deliveries, payments…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={1}
          disabled={loading}
        />
        <button
          className="send-btn"
          onClick={sendMessage}
          disabled={loading || !input.trim()}
          title="Send (Enter)"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="22" y1="2" x2="11" y2="13" />
            <polygon points="22 2 15 22 11 13 2 9 22 2" />
          </svg>
        </button>
      </div>
    </div>
  )
}
