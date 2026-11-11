# 原因

这是典型的 **check-then-act 竞态**，而且两边的保护都不可靠：

1. `SELECT ... LIMIT 1` 是普通快照读，**不加锁**。A、B 两个实例可以同时在各自事务里读到同一行 `id=42`。
2. 两条语句各自自动提交，所以不存在"持有锁直到 UPDATE 完成"的时间窗口。
3. `UPDATE ... WHERE id=$1` 的谓词只有主键，**不校验 `status` 仍然是 `queued`**。等 B 执行 UPDATE 时，A 早已把状态改成 `running`，但 B 的 UPDATE 依然命中该行、依然成功。即使加了 `WHERE status='queued'`，如果不用**行锁**配合，普通 UPDATE 也会等锁然后重新求值——这里的问题恰是谓词里没有 status，所以无从"重新求值失败"。
4. 没有任何"领取者/租约"标记，因此即使想检测重复也无法检测。

在 READ COMMITTED 下，正确做法是让 **选取和抢占在同一条语句（或同一组持锁语句）里完成**，并让 UPDATE 的 WHERE 承担"抢占"判定。

# SQL 方案

### 方案 A：单语句原子领取（Postgres，推荐）

用 `UPDATE ... FROM (SELECT ... FOR UPDATE SKIP LOCKED)` 一条语句完成选取 + 抢占：

```sql
UPDATE jobs
SET status         = 'running',
    locked_by      = $worker_id,
    lease_until    = now() + interval '5 minutes',
    attempts       = attempts + 1,
    started_at     = now()
WHERE id = (
    SELECT id
    FROM jobs
    WHERE status = 'queued'
    ORDER BY id            -- 或 created_at
    LIMIT 1
    FOR UPDATE SKIP LOCKED -- 关键：跳过已被别人锁住的行
)
RETURNING id;
```

返回 0 行 = 没活干；返回 1 行 = 你确实独占了这个任务。两个实例会各自拿到不同的行（或一个拿到、一个空等），绝不会拿到同一行。

### 方案 B：若坚持两步，UPDATE 必须带状态谓词

```sql
-- step 1
SELECT id FROM jobs
WHERE status = 'queued'
ORDER BY id
LIMIT 1
FOR UPDATE SKIP LOCKED;   -- 锁住，事务内使用

-- step 2（同一事务）
UPDATE jobs
SET status = 'running', locked_by = $worker_id,
    lease_until = now() + interval '5 minutes'
WHERE id = $1 AND status = 'queued'
RETURNING id;
```

`WHERE status='queued'` 让后到者在拿到行锁后重新求值，发现状态已变，更新 0 行。**必须检查受影响行数**，0 行就回滚重选。缺点：需要事务包裹，且 `FOR UPDATE` 无 `SKIP LOCKED` 时会排队而非跳过。

> 注意：如果不用 `FOR UPDATE SKIP LOCKED` 而只是把 `SELECT` 和带 `AND status='queued'` 的 `UPDATE` 分在两个自动提交事务里，**仍可能**因为查询之后、更新之前的时间差而更新 0 行——这不会导致重复执行，但会产生空转；且在 REPEATABLE READ 下会报序列化失败。所以方案 A 最稳。

# 验证步骤

1. **准备数据**：插入 200 条 `status='queued'` 的 jobs，`attempts` 默认 0。
2. **并发压测**：启动 2 个（或 N 个）worker，各自循环执行方案 A 的 UPDATE 直到返回 0 行。
   - 可用 `pgbench`、两个 `psql` 会话循环、或简单脚本并发调用。
3. **核对不重复**：压测结束后查
   ```sql
   SELECT count(*) AS total, count(DISTINCT id) AS distinct_ids,
          count(*) FILTER (WHERE status='running') AS running
   FROM jobs;
   ```
   `attempts` 之和应等于被领取的行数；不应有同一 id 被两个不同 `locked_by` 领取两次（`locked_by` 或审计表可记录）。
4. **对照复现旧逻辑**：把方案 A 换回你原来的两条语句，同样压测，应能观测到同一 id 被执行两次（可在执行体里对 `id` 做幂等计数或日志比对）。
5. **失败重试路径**：simulate 一个 worker 领取后不提交 / 崩溃，验证 `lease_until` 过期后任务可被重新领取：
   ```sql
   UPDATE jobs SET status='queued', locked_by=NULL
   WHERE status='running' AND lease_until < now();
   ```
   跑一个定时回收任务，确认重试能发生。

# 关于 exactly-once

**不要承诺 exactly-once**。上面的方案只保证"同一时刻只有一个 worker 领取同一任务"（at-most-once 抢占），任务本体在事务外执行，可能：

- 执行成功但提交状态前崩溃 → 到期后被重试 → **至少一次（at-least-once）**；
- 执行中途失败 → 重试。

所以任务执行体必须**幂等**（例如以 `job_id` 为业务键做 upsert、或带幂等令牌），并对 `attempts` 设上限、退避。正确语义是 **at-least-once + 幂等执行**，而不是 exactly-once。
