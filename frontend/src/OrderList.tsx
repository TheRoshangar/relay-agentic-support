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

type OrderListProps = {
  orders: Order[]
  onSelectOrder: (order: Order) => void
}

function OrderList({
  orders,
  onSelectOrder,
}: OrderListProps) {
  return (
    <div>
      <h2>Orders</h2>

      {orders.map((order) => (
        <div key={order.id}>
          <h3>{order.product_name}</h3>

          <p>Order ID: {order.id}</p>
          <p>Status: {order.status}</p>
          <p>Amount: {order.amount}</p>

          <button
            onClick={() => onSelectOrder(order)}
          >
            Start new chat
          </button>

          <hr />
        </div>
      ))}
    </div>
  )
}

export default OrderList