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
    <div className="sidebar-section">
      <div className="sidebar-section-heading">
        <h2>Orders</h2>
      </div>

      {orders.length === 0 && (
        <p className="empty-state">No orders yet.</p>
      )}

      <div className="list-stack">
        {orders.map((order) => (
          <button
            key={order.id}
            className="order-card"
            onClick={() => onSelectOrder(order)}
          >
            <div className="order-card-title">
              {order.product_name}
            </div>

            <div className="order-card-meta">
              <span className="order-card-id readout">
                #{order.id} · {order.amount}
              </span>
              <span className="status-pill">{order.status}</span>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}

export default OrderList
