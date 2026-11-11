# 原因

这正是经典的 **“先查后改”（read-modify-write）竞态**。两条语句各自处于独立事务中，彼此之间没有任何锁或约束：

```
时刻  实例 A                   实例 B                    jobs.id=42 status=queued
 t1    SELECT ... LIMIT 1  → 42
 t2                             SELECT ... LIMIT 1  → 42   （A 尚未 UPDATE，42 仍为 queued）
 t3    UPDATE 42 → running
 t4                             UPDATE 42 → running       （WHERE id=42 无条件，照样命中）
 t5    执行 42                  执行 42                   ← 同一任务跑两次
```

关键点：

1. **SELECT 不加锁**：`SELECT` 在默认隔离级别（Read Committed，或 MySQL 的 REPEATABLE READ）下，读取的是事务快照，不会阻塞其他实例的读；两条 `SELECT` 完全可能读到同一行。
2. **UPDATE 没有谓词保护**：`WHERE id=$1` 只校验主键，不校验“该行当前是否仍为 queued”，所以 B 的 UPDATE 是合法的，返回 `rowCount = 1`，B 认为自己抢到任务，实际是覆盖了 A 的赋值。
3. **自动提交**：每条语句独立提交，`SELECT` 与 `UPDATE` 之间没有事务边界，因此窗口无法被缩小到 0，只是碰运气。
4. `LIMIT 1` 只能限制“单次取几行”，**不提供互斥**。

# SQL 方案：用 `UPDATE ... WHERE 原状态` 的返回行数做“抢占”

把“判断 + 占用”合并成**一条原子的 UPDATE**，由数据库保证行级锁和条件校验。中标者一定是 `rowCount = 1` 的那个实例；落败者得到 `rowCount = 0`，直接换下一个任务。

## 方案 A（PostgreSQL，推荐 `FOR UPDATE SKIP LOCKED` + `RETURNING`）

```sql
-- 抢占一条任务；返回 0 行表示此刻没有可抢的任务
UPDATE jobs
SET    status     = 'running',
       started_at = now(),
       worker     = $1            -- 实例标识，便于排查/回收
WHERE  id = (
         SELECT id
         FROM   jobs
         WHERE  status = 'queued'
         ORDER  BY id          -- 固定顺序，避免活锁/饥饿
         LIMIT  1
         FOR UPDATE SKIP LOCKED   -- 跳过其他事务已锁定的行，不排队等待
       )
  AND  status = 'queued'          -- 双保险：子查询求值后状态若已变，也不误抢
RETURNING id, payload;
```

外层 `AND status = 'queued'` 不是冗余：在 PostgreSQL 中，`UPDATE` 遇到并发更新的行会重新求值谓词（EvalPlanQual），这一句保证即使在极端时序下也不会把 `running` 改回 `running` 而误判自己中标。若用 `READ COMMITTED`（默认），并发写同一行会对 UPDATE 造成阻塞或重新检查，此时 `rowCount` 才是可信的抢占信号。

## 方案 B（MySQL 8 / 通用，不依赖 SKIP LOCKED）

```sql
UPDATE jobs
SET    status     = 'running',
       started_at = NOW(),
       worker     = ?
WHERE  status = 'queued'
ORDER  BY id
LIMIT  1;
-- 然后：SELECT ... WHERE worker = ? AND status = 'running' ORDER BY started_at DESC LIMIT 1;
-- 或直接用 session 变量/单独的 claim 表记录刚抢到的 id
```

MySQL 无法在 `UPDATE` 里 `RETURNING`，因此需要在**同一个事务**内用 `SELECT ... FOR UPDATE` 补齐 id，或者改用 `worker` 加一个 `claim_token`（UUID）来定位刚抢到的行：

```sql
-- 1) 生成 token 并抢占（单条语句，原子）
UPDATE jobs
SET    status = 'running', claim_token = ?, started_at = NOW(), worker = ?
WHERE  status = 'queued'
ORDER  BY id
LIMIT  1;

-- 2) 同一事务内取回
SELECT id, payload FROM jobs WHERE claim_token = ? FOR UPDATE;
```

## 配套的“可重试”设计（不承诺 exactly-once）

既然任务在事务外执行、失败要重试，抢占必须可回收：

```sql
-- 心跳：长任务定期续约，证明自己还活着
UPDATE jobs
SET    heartbeat_at = now()
WHERE  id = $1 AND claim_token = $2 AND status = 'running';

-- 回收：worker 崩溃 / 超时未续约的任务重新入队
UPDATE jobs
SET    status = 'queued', worker = NULL, claim_token = NULL, attempts = attempts + 1
WHERE  status = 'running'
  AND  heartbeat_at < now() - interval '5 minutes';
```

要点：

- 每次执行都携带 `claim_token`，所有后续状态写回（`succeeded`/`failed`）都带 `AND claim_token = $2`，避免旧 worker 的延迟写入污染新一次的抢占。
- `attempts` 做上限，进 `dead` 队列，避免毒丸无限重试。
- 加 `CHECK`/枚举约束限制状态取值，并考虑 `(status, id)` 复合索引支撑抢占子查询。
- **明确放弃 exactly-once**：抢占保证的是“同一时刻最多一个 worker 在执行”（mutual exclusion），但外部副作用（发邮件、扣款、调第三方）在“执行成功但状态写回前崩溃”时必然可能重复。重试语义应为 **at-least-once + 幂等**：给下游传 `idempotency_key = job.id + '/' + attempts`，或让下游按业务键去重。

# 验证步骤

1. **静态确认**：检查代码里所有抢占语句，`UPDATE ... WHERE` 必须包含 `status = 'queued'`，且用 `rowCount/returning` 判定是否中标；绝不接受“SELECT 结果直接当抢到”。

2. **造数据**：插入 1 条 `queued` 任务，启动 2 个（或多）实例，让执行逻辑对同一 id 写一行审计日志（`job_id, worker, claim_token, started_at`）。

3. **并发压测复现旧行为**：在旧代码上让 `SELECT` 与 `UPDATE` 之间人为 `sleep 200ms`，并发实例数 ≥ 2，跑 100 轮。预期：审计表出现同一 `job_id` 的多条 `started` 记录（即 bug 复现）。这是验证“测试确实能抓到问题”的关键一步。

4. **换新 SQL 后重跑**：同样的压测，预期
   - 每条任务在审计表中**恰好一条**成功抢占记录（`claim_token` 唯一）；
   - 抢不到的实例 `rowCount = 0` 并继续轮询，不报错；
   - `SELECT job_id, COUNT(*) FROM audit WHERE event='started' GROUP BY job_id HAVING COUNT(*) > 1` 返回空集。

5. **锁等待/吞吐检查**：压测期间观察 `pg_stat_activity`（或 MySQL `performance_schema.data_locks`），确认“空闲排队”没有异常增长；若无 `SKIP LOCKED`，高并发下会看到大量实例阻塞在同一行上，属于性能问题而非正确性问题。

6. **崩溃回收测试**：抢占后 `kill -9` worker，确认超过心跳阈值后任务被 `queued` 回收且 `attempts` 递增；重复到超过上限后进入 `dead`，不再被抢占。

7. **幂等与重复副作用**：注入“执行成功、写回状态前崩溃”的故障，确认重试时下游按 `idempotency_key` 去重；在监控里统计“同一 job 的 attempts > 1”的比例，作为可接受的重复率指标，而不是当作 bug 清零。

如果第 4 步仍偶发两条抢占记录，最可能的原因是 `UPDATE` 的 `WHERE` 缺了 `status = 'queued'` 谓词，或所用隔离级别/驱动把语句又拆成了两条独立事务——优先检查这两点。