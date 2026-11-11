# 代码问题分析

这个函数有几个问题，按严重程度排列：

## 1. SQL 注入漏洞（严重）

```python
conn.execute("SELECT * FROM users WHERE name = '%s'" % name)
```

这是最严重的问题。直接把 `name` 拼接到 SQL 里，任何外部输入都能篡改查询：

```python
get_user(conn, "x' OR '1'='1")        # 返回所有用户
get_user(conn, "x'; DROP TABLE users; --")  # 删表
```

**修复：** 用参数化查询

```python
cur = conn.execute("SELECT * FROM users WHERE name = ?", (name,))
```

（在 sqlite3 用 `?`，PyMySQL/psycopg2 用 `%s`，一律用占位符而不是字符串格式化）

## 2. `fetchone()[0]` 会崩（运行时错误）

```python
return cur.fetchone()[0]
```

- 如果查不到记录，`fetchone()` 返回 `None`，`None[0]` 抛 `TypeError`
- 如果查到了多条，`fetchone()` 只取一条却 `[0]` 只返回第一列，其他字段丢了

**修复：** 先判空，并明确返回什么

```python
row = cur.fetchone()
return row[0] if row else None   # 或用 row_factory 返回 dict
```

## 3. 索引方式依赖列顺序

`[0]` 假设第一列就是你要的字段（一般是 `id`）。一旦表结构变化（如新增/调整列）就会悄悄返回错误数据。建议按列名取：

```python
conn.row_factory = sqlite3.Row   # sqlite3 下
row = cur.fetchone()
return dict(row) if row else None
```

## 4. 没有关闭游标 / 没有事务边界

虽然是查询，但：

- 游标应当关闭，避免资源泄漏（用 `with conn:` 或 contextlib）
- 没有定义调用方是否提交事务

## 修复后的版本

```python
def get_user(conn, name):
    with conn:  # 自动提交/回滚
        cur = conn.execute("SELECT * FROM users WHERE name = ?", (name,))
        row = cur.fetchone()
    return dict(row) if row else None
```

## 5. runtim 细节

`conn.execute` 返回的游标没有显式 commit——查询还好，但如果以后改成 `INSERT/UPDATE`，忘记提交会静默丢失修改。

---

**小结：`%` 拼接 → 参数化查询；判断 `fetchone()` 是否 `None`；别用位置索引硬取字段。**
