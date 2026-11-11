这个函数有三个问题，最严重的是 SQL 注入：直接用 `%` 把 `name` 拼进 SQL 字符串，只要调用方传入 `' OR '1'='1` 之类的值，就能绕过查询条件，甚至 `'; DROP TABLE users; --` 造成破坏。正确做法是用参数化查询，让驱动负责转义：`conn.execute("SELECT * FROM users WHERE name = ?", (name,))`。

另外两个问题：`cur.fetchone()` 在查不到时返回 `None`，接着 `[0]` 会抛 `TypeError: 'NoneType' object is not subscriptable`，应显式判空；`SELECT *` 后取 `[0]` 依赖列顺序，表结构一变就会静默取到错列，建议写明列名（如 `SELECT id, name FROM users`）并按列名或元组解包取字段。

改完大致是：

```python
def get_user(conn, name):
    cur = conn.execute("SELECT id, name FROM users WHERE name = ?", (name,))
    row = cur.fetchone()
    return row[0] if row else None
```

注意占位符风格随驱动不同：sqlite3/mysql (`mysql-connector`) 用 `?`，`psycopg2`/`MySQLdb` 用 `%s`（但仍然作为第二个参数的元组传入，不是字符串拼接）。
