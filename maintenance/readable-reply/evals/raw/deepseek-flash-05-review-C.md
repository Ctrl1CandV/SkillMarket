这个函数有 4 个问题，按严重程度排列：

**1. SQL 注入（严重）**
`"SELECT * FROM users WHERE name = '%s'" % name` 是直接用字符串拼接 SQL。只要传入 `name = "' OR '1'='1"` 就能绕过查询条件，传入 `"'; DROP TABLE users; --"` 就能删表。这个问题必须修复。

**2. 应该改用参数化查询**
```python
cur = conn.execute("SELECT * FROM users WHERE name = ?", (name,))
```
参数由数据库驱动负责转义和绑定，因此天然能防止注入。（PostgreSQL 使用 `%s` 占位符，SQLite/MySQL 使用 `?`，具体取决于你用的驱动。）

**3. `fetchone()[0]` 可能直接崩溃**
如果查不到用户，`fetchone()` 会返回 `None`，再对 `None` 取 `[0]` 就会抛出 `TypeError`。因此要么显式判空，要么改用默认返回值：
```python
row = cur.fetchone()
return row[0] if row else None
```

**4. `SELECT *` 的 `[0]` 依赖列顺序**
`fetchone()[0]` 固定取第一列，一旦表结构或列顺序变化（比如以后加了 id 前缀），返回值就会悄悄变成错误的值。应当显式指定列：
```python
cur = conn.execute("SELECT name FROM users WHERE name = ?", (name,))
```

合并后的写法：

```python
def get_user(conn, name):
    cur = conn.execute("SELECT name FROM users WHERE name = ?", (name,))
    row = cur.fetchone()
    return row[0] if row else None
```

另外，如果 `name` 上有唯一约束，这里用 `fetchone` 没问题；否则同一重名会有多行，需要确认调用方期望的行为。