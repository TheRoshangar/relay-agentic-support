import psycopg
from psycopg.rows import dict_row

import config


def _connect():
    return psycopg.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        dbname=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        row_factory=dict_row,
    )


def _fetch_one(sql, params=None):
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchone()
    finally:
        conn.close()


def _fetch_all(sql, params=None):
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()
    finally:
        conn.close()


def _execute(sql, params=None):
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
        conn.commit()
    finally:
        conn.close()


def _execute_returning(sql, params=None):
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            row = cur.fetchone()
        conn.commit()
        return row
    finally:
        conn.close()


# ---- Conversation ----

def get_conversation(conversation_id):
    row = _fetch_one(
        "SELECT id, user_id, order_id, total_input_tokens, total_output_tokens, tavily_calls "
        "FROM support_conversation WHERE id = %s",
        (conversation_id,),
    )
    if row is None:
        raise ValueError(f"Conversation {conversation_id} not found")
    return row


def get_conversation_messages(conversation_id):
    return _fetch_all(
        "SELECT role, content FROM support_message "
        "WHERE conversation_id = %s ORDER BY created_at ASC",
        (conversation_id,),
    )


def insert_message(conversation_id, role, content, correlation_id):
    row = _execute_returning(
        "INSERT INTO support_message (conversation_id, role, content, correlation_id, created_at) "
        "VALUES (%s, %s, %s, %s, now()) RETURNING id",
        (conversation_id, role, content, correlation_id),
    )
    return row["id"]


def increment_conversation_tokens(conversation_id, input_tokens, output_tokens):
    _execute(
        "UPDATE support_conversation "
        "SET total_input_tokens = total_input_tokens + %s, "
        "    total_output_tokens = total_output_tokens + %s "
        "WHERE id = %s",
        (input_tokens, output_tokens, conversation_id),
    )


def increment_tavily_calls(conversation_id):
    _execute(
        "UPDATE support_conversation SET tavily_calls = tavily_calls + 1 WHERE id = %s",
        (conversation_id,),
    )


# ---- AgentLog ----

def insert_agent_log(conversation_id, event_type, message):
    _execute(
        "INSERT INTO support_agentlog (conversation_id, event_type, message, created_at) "
        "VALUES (%s, %s, %s, now())",
        (conversation_id, event_type, message),
    )


# ---- Order / RefundRequest ----

def get_order(order_id):
    return _fetch_one(
        "SELECT id, product_name, amount, status, carrier, tracking_number, "
        "delivery, created_at FROM orders_order WHERE id = %s",
        (order_id,),
    )


def get_refund_history(user_id):
    return _fetch_all(
        "SELECT r.order_id, o.product_name, r.reason, r.status, r.created_at "
        "FROM orders_refundrequest r "
        "JOIN orders_order o ON o.id = r.order_id "
        "WHERE r.user_id = %s "
        "ORDER BY r.created_at DESC",
        (user_id,),
    )


def get_customer_risk_counts(user_id):
    return _fetch_one(
        """
        SELECT
            (SELECT COUNT(*) FROM orders_order WHERE user_id = %(uid)s) AS total_orders,
            (SELECT COUNT(*) FROM orders_refundrequest WHERE user_id = %(uid)s) AS total_refunds,
            (SELECT COUNT(*) FROM orders_refundrequest
                WHERE user_id = %(uid)s AND created_at >= now() - interval '90 days') AS refunds_last_90_days,
            (SELECT COUNT(*) FROM orders_refundrequest WHERE user_id = %(uid)s AND status = 'denied') AS denied_refunds,
            (SELECT COUNT(*) FROM orders_refundrequest WHERE user_id = %(uid)s AND status = 'approved') AS approved_refunds,
            (SELECT COUNT(*) FROM orders_refundrequest WHERE user_id = %(uid)s AND status = 'pending') AS pending_refunds
        """,
        {"uid": user_id},
    )


# ---- DocumentChunk / RAG ----

def upsert_document_chunk(document, chunk_index, content):
    _execute(
        "INSERT INTO support_documentchunk (document, chunk_index, content) "
        "VALUES (%s, %s, %s) "
        "ON CONFLICT (document, chunk_index) DO UPDATE SET content = EXCLUDED.content",
        (document, chunk_index, content),
    )


def full_text_search_document_chunks(query, limit=3):
    return _fetch_all(
        "SELECT document, content, "
        "ts_rank(to_tsvector('english', content), plainto_tsquery('english', %(q)s)) AS rank "
        "FROM support_documentchunk "
        "WHERE to_tsvector('english', content) @@ plainto_tsquery('english', %(q)s) "
        "ORDER BY rank DESC "
        "LIMIT %(limit)s",
        {"q": query, "limit": limit},
    )

def is_duplicate_event(event_id):
    row = _fetch_one(
        """
        SELECT id 
        FROM support_processedevent
        WHERE event_id = %s
        """,
        (event_id,),
    )
    return row is not None


def mark_event_processed(event_id, event_type):
    _execute(
        """
        INSERT INTO support_processedevent
        (event_id, event_type, processed_at)
        VALUES (%s, %s, now())
        ON CONFLICT (event_id) DO NOTHING
        """,
        (event_id, event_type),
    )