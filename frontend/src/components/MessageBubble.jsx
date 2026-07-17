export default function MessageBubble({ message }) {
  const { role, text } = message
  return <div className={`bubble ${role === 'user' ? 'user' : 'bot'}`}>{text}</div>
}
