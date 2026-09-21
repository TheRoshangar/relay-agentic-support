import { useEffect, useRef, useState } from 'react'
import OrderList from "./OrderList"
import Chat from "./Chat"
import ConversationList from "./ConversationList"


type Order = {
  id: number
  product_name: string
  amount: string
  status: string
  carrier: string
  tracking_number: string
  delivery: string
  created_at: string
  updated_at: string
}


type Message = {
  id?: number
  role: 'user' | 'model'
  content: string
  created_at?: string
}


type ConversationType = {
  id: number
  user_id: number
  order_id: number
  created_at: string
}


type ConversationDetail = {
  conversation: ConversationType
  messages: Message[]
}


function Conversation() {

  const [orders , setOrders] = useState<Order[]>([])
  const [conversations, setConversations] = useState<ConversationType[]>([])
  const [error, setError] = useState('')

  const [selectedOrder, setSelectedOrder] =
    useState<Order | null>(null)

  const [selectedConversation, setSelectedConversation] =
    useState<ConversationType | null>(null)

  const [message, setMessage] = useState('')
  const [messages, setMessages] = useState<Message[]>([])

  const [chatLoading, setChatLoading] = useState(false)
  const [conversationLoading, setConversationLoading] = useState(false)

 

  type ConnectionStatus = 'connecting' | 'connected' | 'reconnecting' | 'failed'

  const [connectionStatus, setConnectionStatus] =
  useState<ConnectionStatus>('connecting')

  const wasConnectedRef = useRef(false)
  const failedAttemptsRef = useRef(0) 

  const selectedConversationRef = useRef<ConversationType | null>(null)

  useEffect(() => {
    selectedConversationRef.current = selectedConversation
  }, [selectedConversation])

  const [csrfToken, setCsrfToken] = useState('')

  const chatRef = useRef<HTMLDivElement | null>(null)
  const [feedbackGiven, setFeedbackGiven] = useState<Record<number, 1 | -1>>({})




  useEffect(() => {

    fetch('http://localhost:8000/api/csrf/', {
      credentials: 'include',
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error('Failed to get CSRF token')
        }

        return response.json()
      })
      .then((data) => {
        setCsrfToken(data.csrfToken)
      })
      .catch((error) => {
        setError(error.message)
      })


    fetch('http://localhost:8000/orders/api/', {
      credentials: 'include',
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error('Failed to fetch orders')
        }

        return response.json()
      })
      .then((data) => {
        setOrders(data)
      })
      .catch((error) => {
        setError(error.message)
      })


    fetch('http://localhost:8000/support/dashboard/', {
      credentials: 'include',
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error('Failed to fetch conversations')
        }

        return response.json()
      })
      .then((data) => {
        setConversations(data)
      })
      .catch((error) => {
        setError(error.message)
      })


    // SSE connection
    const eventSource = new EventSource(
      'http://localhost:8000/support/events/',
      { withCredentials: true }
    )

    eventSource.onopen = () => {
      failedAttemptsRef.current = 0
      setConnectionStatus('connected')

      if (wasConnectedRef.current === true) {
        resyncCurrentConversation()
      }

      wasConnectedRef.current = true
    }

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.type === 'support_response') {
        setMessages((previous) => [
          ...previous,
        { id: data.reply_message_id,role: 'model', content: data.reply },
        ])
        setChatLoading(false)
      }
    }

    eventSource.onerror = () => {
      failedAttemptsRef.current += 1

      if (eventSource.readyState === EventSource.CLOSED) {
        setConnectionStatus('failed')
      } 
      else if (failedAttemptsRef.current >= 5) {
        eventSource.close()
        setConnectionStatus('failed')
      } 
      else {
        setConnectionStatus('reconnecting')
      }

      console.log('SSE connection error')
    }


    return () => {
      eventSource.close()
    }


  }, [])



  const loadConversation = async (
    conversation: ConversationType
  ) => {

    setConversationLoading(true)
    setError('')


    try {

      const response = await fetch(
        `http://localhost:8000/support/dashboard/${conversation.id}/`,
        {
          credentials: 'include',
        }
      )


      if (!response.ok) {
        throw new Error('Failed to fetch conversation')
      }


      const data: ConversationDetail =
        await response.json()



      const order = orders.find(
        (order) => order.id === conversation.order_id
      )


      if (!order) {
        throw new Error(
          'Order for this conversation was not found'
        )
      }


      setSelectedConversation(conversation)
      setSelectedOrder(order)
      setMessages(data.messages)


      setTimeout(() => {

        chatRef.current?.scrollIntoView({
          behavior: 'smooth',
        })

      }, 100)


      setMessage('')


    } catch (error) {

      setError(
        error instanceof Error
          ? error.message
          : 'Something went wrong'
      )

    } finally {

      setConversationLoading(false)

    }

  }



  const startNewChat = (order: Order) => {

    setSelectedOrder(order)
    setSelectedConversation(null)
    setMessages([])
    setMessage('')
    setError('')

  }

  const resyncCurrentConversation = async () => {
    const conv = selectedConversationRef.current
    if (!conv) return

    try {
      const response = await fetch(
        `http://localhost:8000/support/dashboard/${conv.id}/`,
        { credentials: 'include' }
      )

      if (!response.ok) return

      const data: ConversationDetail = await response.json()
      setMessages(data.messages)
      setChatLoading(false)
    } catch {
    // مشکلی نیست، دفعه‌ی بعد که وصل بشه دوباره امتحان می‌کنیم
    }
  }
  
  const sendFeedback = async (messageId: number, score: 1 | -1) => {
    if (!csrfToken) return

    try {
      const response = await fetch('http://localhost:8000/support/feedback/', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify({
          message_id: messageId,
          score,
        }),
     })

    if (response.ok) {
      setFeedbackGiven((previous) => ({
        ...previous,
        [messageId]: score,
      }))
    }
  } catch {
    // بازخورد یه ویژگی جانبیه، شکستش نباید تجربه‌ی چت رو خراب کنه
  }
}



  const sendMessage = async () => {

    if (
      !message.trim() ||
      !selectedOrder ||
      !csrfToken
    ) {
      return
    }


    const userMessage = message



    setMessages((previous) => [
      ...previous,
      {
        role: 'user',
        content: userMessage,
      },
    ])



    setMessage('')
    setChatLoading(true)
    setError('')



    try {

      const response = await fetch(
        `http://localhost:8000/support/chat/${selectedOrder.id}/`,
        {
          method: 'POST',

          credentials: 'include',

          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
          },

          body: JSON.stringify({
            message: userMessage,
          }),

        }
      )



      if (!response.ok) {
        throw new Error('Failed to send message')
      }

    } catch (error) {

      setError(
        error instanceof Error
          ? error.message
          : 'Something went wrong'
      )

      setChatLoading(false)

    }

  }



  const statusLabel =
    connectionStatus === 'connected' ? 'Connected' :
    connectionStatus === 'connecting' ? 'Connecting…' :
    connectionStatus === 'reconnecting' ? 'Reconnecting…' :
    'Connection lost — refresh the page'

  return (

    <div className="page-conversation">

      <aside className="sidebar">

        <div className="status-row">
          <span className={`status-dot status-dot--${connectionStatus}`} />
          {statusLabel}
        </div>

        {error && <div className="error-banner">{error}</div>}

        <ConversationList
          conversations={conversations}
          loading={conversationLoading}
          onSelectConversation={loadConversation}
        />

        <OrderList
          orders={orders}
          onSelectOrder={startNewChat}
        />

      </aside>

      {selectedOrder ? (

        <div
          ref={chatRef}
          style={{ display: 'flex', flexDirection: 'column', minHeight: 0, height: '100%' }}
        >

          <Chat

            selectedOrder={selectedOrder}

            selectedConversation={selectedConversation}

            messages={messages}

            message={message}

            chatLoading={chatLoading}

            onMessageChange={setMessage}

            onSendMessage={sendMessage}
            onFeedback={sendFeedback}
            feedbackGiven={feedbackGiven}
          />

        </div>

      ) : (

        <div className="chat-empty">
          Pick an order on the left to start a new chat, or open a
          previous conversation.
        </div>

      )}

    </div>

  )

}


export default Conversation
