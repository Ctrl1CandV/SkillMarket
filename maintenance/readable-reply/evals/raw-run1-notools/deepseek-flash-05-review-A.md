# 这个函数的问题

```python
def get_user(conn, name):
    cur = conn.execute("SELECT * FROM users WHERE name = '%s'" % name)
    return cur.fetchone()[0]
```

## 1. SQL 注入（最严重）

字符串拼接直接引入注入漏洞。例如 `name = "' OR '1'='1"` 会返回任意用户；`name = "'; DROP TABLE users; --"` 可能直接删表。

## 2. `fetchone()` 可能返回 `None`

用户不存在时 `cur.fetchone()[0]` 抛 `TypeError: 'NoneType' object is not subscriptable`，调用方无法区分"没找到"和"程序错误"。

## 3. `[0]` 只取第一列

`SELECT *` 的列顺序依赖表结构，`[0]` 大概率是 `id` 而不是用户数据，且表加列/改列顺序就会静默出错。

## 4. 返回结构不明确

返回一个裸值，调用方不知道拿到的是什么。建议显式过滤字段。

## 修复建议

```python
def get_user(conn, name):
    cur = conn.execute(
        "SELECT id, name, email FROM users WHERE name = ?",
        (name,),
    )
    row = cur.fetchone()
    if row is None:
        return None          # 或 raise UserNotFound
    return {"id": row[0], "name": row[1], "email": row[2]}
```

要点：
- 用参数化查询（`?` 占位符，sqlite3 风格；psycopg 用 `%s`，但值要走参数元组，不是格式化）。
- 检查 `fetchone()` 是否为 `None`。
- 明确列出字段，别用 `SELECT *`。

> 补充：`name` 若有唯一索引，语义才清晰；否则同名用户会随机返回一条，考虑改为按 `id` 查询或加 `LIMIT 1`。
