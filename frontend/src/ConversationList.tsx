type ConversationType = {
  id: number
  user_id: number
  order_id: number
  created_at: string
}

type ConversationListProps = {
  conversations: ConversationType[]
  loading: boolean
  onSelectConversation: (
    conversation: ConversationType
  ) => void
}

function ConversationList({
  conversations,
  loading,
  onSelectConversation,
}: ConversationListProps) {
  return (
    <div>
      <h2>Previous Conversations</h2>

      {conversations.length === 0 && (
        <p>No previous conversations.</p>
      )}

      {conversations.map((conversation) => (
        <div key={conversation.id}>
          <p>
            <strong>
              Conversation #{conversation.id}
            </strong>
          </p>

          <p>Order #{conversation.order_id}</p>

          <p>
            Created: {conversation.created_at}
          </p>

          <button
            onClick={() =>
              onSelectConversation(conversation)
            }
            disabled={loading}
          >
            {loading
              ? 'Loading...'
              : 'Open conversation'}
          </button>

          <hr />
        </div>
      ))}
    </div>
  )
}

export default ConversationList