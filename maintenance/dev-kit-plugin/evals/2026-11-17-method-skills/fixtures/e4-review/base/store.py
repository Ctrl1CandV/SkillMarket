import sqlite3


def connect(path):
    return sqlite3.connect(path)


def get_order(conn, order_id):
    cur = conn.execute("SELECT id, customer, amount FROM orders WHERE id = ?", (order_id,))
    return cur.fetchone()
