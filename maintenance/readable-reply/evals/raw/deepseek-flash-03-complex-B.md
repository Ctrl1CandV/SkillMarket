原因：两次 SELECT 和它们各自的 UPDATE 之间没有锁，两个实例都能读到同一行 queued（处于可串行化以上隔离级别也不会自动阻止这种“读后写”，因为在 read committed 下 SELECT 不加锁、不加快照约束；UPDATE 本身是原子的，但它只是在第二个实例已经“以为自己抢到了”之后才排他），于是两边的 `UPDATE ... WHERE id=$1` 都成功——第二个只是把 running 覆盖成 running。真正的互斥必须落在“选定即占用”的同一条语句里。

**可改的 SQL 方案：单语句原子领取，用 `FOR UPDATE SKIP LOCKED` 或带条件的 UPDATE 返回。**

推荐写法（PG 9.5+），在一个短事务里用 CTE 完成选中+更新，锁和状态变更在同一处产生：

```sql
WITH picked AS (
  SELECT id FROM jobs
  WHERE status = 'queued'
  ORDER BY id            -- 或 created_at，保证公平且避免随机
  LIMIT 1
  FOR UPDATE SKIP LOCKED -- 已被别的实例锁住的列直接跳过
)
UPDATE jobs j SET status = 'running',
                  started_at = now(),
                  locked_by = $worker_id,
                  attempts = attempts + 1
FROM picked
WHERE j.id = picked.id
RETURNING j.id;
```

返回 0 行 = 没抢到，本轮退出；返回 1 行 = 你独占该任务，提交这个事务后再去事务外执行。`SKIP LOCKED` 让并发实例不去排队等同一行，而是各取不同行，吞吐也更好。

如果数据库不支持 `SKIP LOCKED`（MySQL 8.0 之前、SQL Server 的某些写法），用条件 UPDATE + 影响行数判断，仍是单语句，但两端读取之间靠 UPDATE 的行锁和条件重检来保证只有一个成功：

```sql
UPDATE jobs SET status='running', locked_by=$1, started_at=now(), attempts=attempts+1
WHERE id = (SELECT id FROM jobs WHERE status='queued' ORDER BY id LIMIT 1)
  AND status='queued'
RETURNING id;
```

注意 MySQL 里子查询不能在 UPDATE 同表时直接引用，需改成 `UPDATE jobs SET ... WHERE status='queued' ORDER BY id LIMIT 1` 并用 affected_rows 判定；affected_rows=1 才算领到。

失败重试：不要回滚成 `queued` 后立刻重抢（会忙等），用 `status='failed'` 或 `status='queued', run_at = now() + backoff`，并加 `attempts < max_attempts` 条件；领取查询里加上 `AND (status='queued') AND (run_at IS NULL OR run_at <= now())`。超时任务的恢复用另一个检查语句把 `status='running' AND started_at < now() - interval 'X'` 重置为 queued，`locked_by` 用于识别陈旧锁。这里只能做到 at-least-once：任务可能执行两次（进程在执行中被杀、租约过期后被重抢），所以任务本身必须幂等（按 job id 做幂等键、写入做 upsert 或先查后写带唯一约束）。

**验证步骤：** 起两个以上实例，把领取函数压成只跑领取，然后在压测里统计：断言每个 id 的 `attempts` 只在被领取时 +1，且所有实例返回的 id 集合无交集；先插 1000 条 queued，跑 N 个并发 worker 直到队列空，检查 `SELECT count(*) FROM jobs WHERE status='running' > 1 group by id` 应为 0 行，以及总成功领取次数 ≤ 1000 而不是大于 1000。再用 `pg_sleep` 或人为 kill 模拟执行中崩溃，验证超时恢复语句不会抢走仍持有有效锁的行，并且重跑后因为幂等键不产生重复副作用。