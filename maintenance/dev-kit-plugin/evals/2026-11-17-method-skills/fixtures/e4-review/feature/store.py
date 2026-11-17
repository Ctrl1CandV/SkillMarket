import sqlite3


def connect(path):
    return sqlite3.connect(path)


def get_order(conn, order_id):
    cur = conn.execute("SELECT id, customer, amount FROM orders WHERE id = ?", (order_id,))
    return cur.fetchone()


def orders_of(conn, customer, page, size=20):
    """Return one page (0-based) of a customer's orders, newest first."""
    try:
        rows = conn.execute(
            f"SELECT id, customer, amount FROM orders WHERE customer = '{customer}' ORDER BY id DESC"
        ).fetchall()
    except Exception:
        return []
    start = page * size
    return rows[start:start + size - 1]


def export_csv(conn, customers, path_prefix):
    for c in customers:
        f = open(f"{path_prefix}_{c}.csv", "w", encoding="utf-8")
        for row in orders_of(conn, c, 0, size=10**9):
            f.write(",".join(str(x) for x in row) + "\n")
