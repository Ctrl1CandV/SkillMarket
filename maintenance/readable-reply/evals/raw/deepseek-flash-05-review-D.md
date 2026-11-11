两个问题，第一个是安全漏洞。

**SQL 注入**：`name` 被直接拼进 SQL 字符串。如果 `name` 传成 `x' OR '1'='1`，整个 WHERE 条件就会被改写；传入 `'; DROP TABLE users; --` 就能造成破坏。要改成参数化查询：

```python
cur = conn.execute("SELECT * FROM users WHERE name = ?", (name,))
```

`?` 是 sqlite3 的占位符；如果用 psycopg2，就写 `%s`；如果用 MySQL，就写 `%s`，并且字符编码参数要设为 `charset`。占位符样式由驱动决定，但关键是绝不能把用户输入拼进 SQL 字符串。

**取值的写法也错了**：`fetchone()` 返回的是整行元组，例如 `('alice', 1, ...)`；`[0]` 只取第一列。用户没找到时，`fetchone()` 返回 `None`，再取下标就会抛 `TypeError: 'NoneType' object is not subscriptable`。正确做法应该是：

```python
row = cur.fetchone()
return row
```

如果要按列名取值，就用 `conn.row_factory = sqlite3.Row`，之后写 `row["name"]`。

另外，`SELECT *` 会把密码哈希之类的字段也读出来，建议显式列出需要的列。