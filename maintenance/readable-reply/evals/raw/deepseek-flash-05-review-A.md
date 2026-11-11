这个函数有三个问题，其中第一个是严重的安全漏洞。

## 1. SQL 注入（严重）

```python
conn.execute("SELECT * FROM users WHERE name = '%s'" % name)
```

`name` 被直接拼进 SQL。只要传入 `"' OR '1'='1"`，就绕过条件查到所有人的第一条记录；更糟的是 `"x'; DROP TABLE users; --"` 可以直接删表。

**修复**：用参数化查询，让驱动做转义和绑定：

```python
cur = conn.execute("SELECT * FROM users WHERE name = ?", (name,))
```

占位符写法要看驱动：sqlite3 用 `?`，psycopg/psycopg2 用 `%s`（注意：是占位符，不是字符串拼接），MySQL 驱动常用 `%s`。别混用。

## 2. 查询无结果时会崩

`fetchone()` 查不到时返回 `None`，`None[0]` 直接 `TypeError`。要显式处理：

```python
row = cur.fetchone()
if row is None:
    return None  # 或抛自定义异常 / 返回 404
```

## 3. 用下标取列，依赖列顺序

`[0]` 取的是 `SELECT *` 的第一列，表结构一变（加列、调顺序）就悄悄取错数据。建议显式列出字段并用名字取值：

```python
cur = conn.execute("SELECT id, name, email FROM users WHERE name = ?", (name,))
```

如果行对象支持映射访问（sqlite3 的 `Row`、psycopg 的 `dict_row`），可以用 `row["id"]`。

## 修完的版本

```python
def get_user(conn, name):
    cur = conn.execute(
        "SELECT id, name, email FROM users WHERE name = ?",
        (name,),
    )
    row = cur.fetchone()
    if row is None:
        return None
    return {"id": row[0], "name": row[1], "email": row[2]}
```

## 顺带两点

- **`name` 未必唯一**：如果 `users.name` 没有唯一约束，`fetchone()` 只返回任意一条。查询应该用 `id` 这类唯一键，或者明确 `LIMIT 1` 并说明语义。
- **连接/游标管理**：函数只管查，不负责关闭是合理的，但要注意调用方是否复用了同一个连接、异常路径下是否回滚。如果这是 Web 请求处理，建议每次请求独立连接或用连接池。

另外，如果 `conn` 来自用户可控的输入（比如把连接串当参数传进来），那属于另一层问题，不在这里讨论范围内。