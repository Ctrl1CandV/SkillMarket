原因：`SELECT ... LIMIT 1` 和 `UPDATE` 是两条语句、两个事务，中间没有任何互斥。两个实例在同一时刻都读到同一行 `queued`，各自执行 `UPDATE`；第二条 `UPDATE` 命中 0 行但并不报错，应用仍把该 id 当成本实例抢到的任务去执行，于是同一任务被执行两次。本质是典型的 “check-then-act” 竞态，不是数据库隔离级别问题——即便用 `REPEATABLE READ`，旧快照仍会让第二个事务读到已过期的 `queued`。

**可改的 SQL 方案（PG 9.5+，单条语句原子化）**

```sql
UPDATE jobs
SET status = 'running',
    started_at = now(),
    owner = $2
WHERE id = (
  SELECT id FROM jobs
  WHERE status = 'queued'
  ORDER BY id
  LIMIT 1
  FOR UPDATE SKIP LOCKED
)
RETURNING id, payload;
```

要点：子查询里的 `FOR UPDATE` 在取行时加行锁，`SKIP LOCKED` 让并发的第二个实例直接跳过被锁住的行，去抢下一行，而不是排队后再失败。`UPDATE` 与外层写在同一事务里，返回 0 行即表示「当前没活可干」，应用必须检查 `RETURNING` 是否为空，不能假设一定能拿到。若还需按优先级/时间调度，把 `ORDER BY id` 换成 `ORDER BY priority DESC, created_at`。批量取用 `LIMIT 1` 改 `LIMIT n`。

若锁超时是关注点，可先粗筛再锁，但一般不必：

```sql
-- 省索引扫描的变体，语义同上
UPDATE jobs SET status='running', started_at=now(), owner=$2
WHERE id = (
  SELECT id FROM jobs
  WHERE status='queued'
  ORDER BY id
  LIMIT 1
  FOR UPDATE SKIP LOCKED
) AND status='queued'
RETURNING id, payload;
```

索引配合：`CREATE INDEX ON jobs (status, id) WHERE status = 'queued';`（部分索引，队列扫描更快）。

**失败重试**：执行体在事务外，失败后不要回滚成 `queued` 让别人立刻抢，而是带租约：

```sql
UPDATE jobs SET status='running', started_at=now(), owner=$2, attempts=attempts+1
WHERE id=$1;
```

- 进程崩溃后由独立的回收作业把租约超时的行放回队列：
  ```sql
  UPDATE jobs SET status='queued', owner=NULL
  WHERE status='running' AND started_at < now() - interval '10 minutes'
    AND attempts < 5;
  ```
- 失败（抛异常）时由执行方显式处理：`attempts >= 5` 置 `status='failed'` 并记录 `last_error`，否则置回 `queued`。因为租约+回收，同一任务在极端情况（超时判定后原执行者又活着完成）下仍可能执行两次，所以任务**必须幂等**——这是设计前提，不做 exactly-once 承诺。

**验证步骤**

1. 造数据：`INSERT INTO jobs(status) SELECT 'queued' FROM generate_series(1,100);`
2. 并发压测：开两个终端各跑同样循环 100 次，脚本逻辑为「执行上面那条 UPDATE，取 `RETURNING id`，非空则 sleep 0.5s 后置为 `done`」。
3. 断言一：`SELECT count(DISTINCT id) FROM jobs WHERE status='done'` 应等于 100，且所有 `done` 行 `owner` 不重复被覆盖——统计「同一 id 被执行次数」可在脚本里写日志后 `sort | uniq -c`，期望全部为 1。
4. 断言二：`SELECT count(*) FROM jobs WHERE status='running'` 在执行结束时应为 0（无悬挂租约）。
5. 回归对照：把原两条语句的版本用同样方法跑，应能看到 `uniq -c` 出现计数 2 的行，确认问题是竞态而非任务本身不幂等。
6. 手工验证锁语义：事务 A 里执行 `SELECT ... FOR UPDATE` 并 `BEGIN;` 不提交，事务 B 执行整条 UPDATE 应立即返回 0 行而非阻塞（`SKIP LOCKED` 生效）。
