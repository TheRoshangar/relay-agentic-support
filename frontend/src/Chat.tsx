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
}

function Chat({
  selectedOrder,
  selectedConversation,
  messages,
  message,
  chatLoading,
  onMessageChange,
  onSendMessage,
}: ChatProps) {
  return (
    <div>
      <h2>Chat</h2>

      <p>
        Order #{selectedOrder.id} -{' '}
        {selectedOrder.product_name}
      </p>

      {selectedConversation && (
        <p>
          Conversation #{selectedConversation.id}
        </p>
      )}

      <div>
        {messages.length === 0 && (
          <p>No messages yet.</p>
        )}

        {messages.map((msg, index) => (
          <div key={msg.id ?? index}>
            <strong>
              {msg.role === 'user'
                ? 'You'
                : 'Maya'}
              :
            </strong>

            <p>{msg.content}</p>
          </div>
        ))}
      </div>

      <input
        type="text"
        value={message}
        onChange={(event) =>
          onMessageChange(event.target.value)
        }
        placeholder="Type your message..."
        disabled={chatLoading}
      />

      <button
        onClick={onSendMessage}
        disabled={
          chatLoading || !message.trim()
        }
      >
        {chatLoading
          ? 'Sending...'
          : 'Send'}
      </button>
    </div>
  )
}

export default Chat