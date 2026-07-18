import { useEffect, useRef } from 'react'
import MessageBubble from './MessageBubble.jsx'

export default function ChatWindow({ messages, onOption, pending = false, children }) {
  const endRef = useRef(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, pending])

  return (
    <main className="chat" aria-live="polite">
      {messages.map((m, i) => (
        <MessageBubble
          key={m.id}
          message={m}
          isLast={i === messages.length - 1}
          onOption={pending ? undefined : onOption}
        />
      ))}
      {children}
      <div ref={endRef} />
    </main>
  )
}
