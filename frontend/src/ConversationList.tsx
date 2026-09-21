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
    <div className="sidebar-section">
      <div className="sidebar-section-heading">
        <h2>Previous conversations</h2>
      </div>

      {conversations.length === 0 && (
        <p className="empty-state">No previous conversations.</p>
      )}

      <div className="list-stack">
        {conversations.map((conversation) => (
          <button
            key={conversation.id}
            className="conversation-card"
            onClick={() => onSelectConversation(conversation)}
            disabled={loading}
          >
            <div className="conversation-card-title">
              Conversation #{conversation.id}
              <span className="readout"> · Order #{conversation.order_id}</span>
            </div>

            <div className="conversation-card-meta">
              {loading ? "Loading..." : conversation.created_at}
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}

export default ConversationList
