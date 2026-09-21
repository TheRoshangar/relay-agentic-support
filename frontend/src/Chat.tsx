import { useEffect, useRef } from 'react'

type Message = {
  id?: number
  role: 'user' | 'model'
  content: string
  created_at?: string
}

type Order = {
  id: number
  product_name: string
}

type ConversationType = {
  id: number
  user_id: number
  order_id: number
  created_at: string
}

type ChatProps = {
  selectedOrder: Order
  selectedConversation: ConversationType | null
  messages: Message[]
  message: string
  chatLoading: boolean
  onMessageChange: (value: string) => void
  onSendMessage: () => void
  onFeedback: (messageId: number, score: 1 | -1) => void
  feedbackGiven: Record<number, 1 | -1>
}

function Chat({
  selectedOrder,
  selectedConversation,
  messages,
  message,
  chatLoading,
  onMessageChange,
  onSendMessage,
  onFeedback,
  feedbackGiven,
}: ChatProps) {
  const messageListRef = useRef<HTMLDivElement | null>(null)

  // Always keep the view pinned to the latest message: on first render,
  // whenever a new message is added, and whenever the selected
  // conversation changes.
  useEffect(() => {
    const el = messageListRef.current
    if (!el) return
    el.scrollTop = el.scrollHeight
  }, [messages, selectedConversation])

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <div>
          <div className="chat-header-title">
            {selectedOrder.product_name}
          </div>
          <div className="chat-header-meta readout">
            Order #{selectedOrder.id}
            {selectedConversation && ` · Conversation #${selectedConversation.id}`}
          </div>
        </div>
      </div>

      <div className="message-list" ref={messageListRef}>
        {messages.length === 0 && (
          <p className="empty-state">
            No messages yet. Say hello to Maya below.
          </p>
        )}

        {messages.map((msg, index) => (
          <div
            key={msg.id ?? index}
            className={
              "message-row " +
              (msg.role === "user" ? "message-row--user" : "message-row--model")
            }
          >
            <div className="message-label">
              {msg.role === "user" ? "You" : "Maya"}
            </div>

            <div className="message-bubble">{msg.content}</div>

            {msg.role === "model" && msg.id && (
              <div className="message-feedback">
                <button
                  className={
                    "feedback-btn" +
                    (feedbackGiven[msg.id] === 1 ? " is-picked" : "") +
                    (feedbackGiven[msg.id] !== undefined && feedbackGiven[msg.id] !== 1
                      ? " is-dimmed"
                      : "")
                  }
                  onClick={() => onFeedback(msg.id!, 1)}
                  disabled={feedbackGiven[msg.id] !== undefined}
                  aria-label="Helpful reply"
                >
                  👍
                </button>
                <button
                  className={
                    "feedback-btn" +
                    (feedbackGiven[msg.id] === -1 ? " is-picked" : "") +
                    (feedbackGiven[msg.id] !== undefined && feedbackGiven[msg.id] !== -1
                      ? " is-dimmed"
                      : "")
                  }
                  onClick={() => onFeedback(msg.id!, -1)}
                  disabled={feedbackGiven[msg.id] !== undefined}
                  aria-label="Unhelpful reply"
                >
                  👎
                </button>
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="chat-composer">
        <input
          className="chat-input"
          type="text"
          value={message}
          onChange={(event) => onMessageChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !chatLoading && message.trim()) {
              onSendMessage()
            }
          }}
          placeholder="Type your message..."
          disabled={chatLoading}
        />

        <button
          className="primary-button send-button"
          onClick={onSendMessage}
          disabled={chatLoading || !message.trim()}
        >
          {chatLoading ? "Sending..." : "Send"}
        </button>
      </div>
    </div>
  )
}

export default Chat
