第一句结论：SELECT 之后、UPDATE 之前，两个实例都可能读到同一个 id；因为两条语句各自自动提交，UPDATE 也没有加状态条件，所以两个实例都成功把这些行改成了 running。这是典型的“先检查后执行”（check-then-act）竞态，不是数据库 bug。

要修的问题有两层。一是取任务和占用任务必须由同一条语句完成，用 `UPDATE ... WHERE status='queued'` 的原子更新来抢；二是最好只让一个实例看到候选行。下面给出的事务外执行、可重试方案，不承诺 exactly-once。

**SQL 方案**

单条“抢占并返回”的语句（PostgreSQL）：

```sql
WITH candidate AS (
  SELECT id FROM jobs
  WHERE status = 'queued'
  ORDER BY id
  FOR UPDATE SKIP LOCKED
  LIMIT 1
)
UPDATE jobs j
SET status = 'running',
    started_at = now(),
    attempt = attempt + 1
FROM candidate c
WHERE j.id = c.id
  AND j.status = 'queued'
RETURNING j.id;
```

返回 0 行表示当前没有可抢的任务，回去轮询或退出即可；返回 1 行说明这个实例获得了该任务。要点：

- `FOR UPDATE SKIP LOCKED` 让并发实例跳过已被锁定的行，而不是排队等待。
- 外层 `AND j.status='queued'` 是第二道保险：就算候选行在锁释放后被别人改过，更新也不会生效。
- `attempt` 自增方便实现重试上限。

如果用的是 MySQL 8，`SKIP LOCKED` 也支持，写法为 `SELECT id ... FOR UPDATE SKIP LOCKED LIMIT 1` 再 `UPDATE ... WHERE id=? AND status='queued'`。这两步放在一个显式事务里，并检查受影响行数是否为 1。MySQL 不能在 UPDATE 中再用子查询引用同一张表，也不能用 `RETURNING`，所以这条 UPDATE 必须在事务内完成。

**执行与重试**

任务在事务外跑，意味着“抢占”和“执行”不是原子的：

- 抢占成功并提交后实例崩溃，任务会卡在 running。加一个回收策略：`UPDATE jobs SET status='queued' WHERE status='running' AND started_at < now() - interval '10 minutes'`，用一个定期巡检跑。
- 执行失败时：`UPDATE jobs SET status = CASE WHEN attempt >= 3 THEN 'failed' ELSE 'queued' END, last_error = $2 WHERE id = $1`。重试就是重新变成可抢的 queued，所以**同一个任务仍可能被执行两次**：第一次跑完提交前崩溃，回收后被重新抢占。下游操作要幂等（按 job id 去重），不要假设只跑一次。

**验证步骤**

1. 造数据：`INSERT INTO jobs(status) SELECT 'queued' FROM generate_series(1, 100)`。
2. 并发压测：起 8 个客户端，每个循环执行上面的抢占 SQL 直到返回 0 行，把返回的 id 汇总。
3. 断言：`COUNT(*)` 等于 `COUNT(DISTINCT id)`，且总数 = 100。旧代码在同样压测下几乎必然重复。
4. 并发冲突用例：两个会话手工执行 `SELECT ... FOR UPDATE` 抢同一行，验证第二个会话被 SKIP LOCKED 跳过。
5. 崩溃场景：抢占后直接 kill 进程，等回收窗口过去，确认任务回到 queued 并被重跑，同时下游幂等逻辑挡住了重复副作用。

`status` 上的索引（`WHERE status='queued'` 的部分索引或普通索引）会让步骤 2 的吞吐稳定，压测前先建好。