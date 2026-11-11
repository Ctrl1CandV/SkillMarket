# 原因

两条语句各自自动提交，所以“查”和“改”之间存在窗口：

```
实例 A: SELECT → 拿到 id=42
实例 B: SELECT → 也拿到 id=42（A 还没 UPDATE）
实例 A: UPDATE 42 → 成功，status='running'
实例 B: UPDATE 42 → 也“成功”（WHERE 只有 id，没有 status 条件），把 42 又写了一遍
两个实例都以为自己领到了 42 → 各执行一次
```

关键点：`UPDATE ... WHERE id=$1` 没有“仍然是我看到的状态”这个条件，所以第二次 UPDATE 不会挡住任何人。这不是隔离级别能救的问题（READ COMMITTED 下就足以复现），因为两条语句之间根本没有事务边界。

# 方案：把“认定”变成一条原子的条件 UPDATE

不要在应用里做 SELECT 再 UPDATE，让数据库用一条语句完成“选一个并标记”。

```sql
-- 领取任务：一条语句完成 选 + 认领
UPDATE jobs AS j
SET status = 'running',
    started_at = now(),
    locked_by = $1          -- 实例标识，便于排查/回收
WHERE j.id = (
    SELECT id FROM jobs
    WHERE status = 'queued'
    ORDER BY id
    LIMIT 1
    FOR UPDATE SKIP LOCKED   -- 跳过被别人锁住的行，避免排队
)
  AND j.status = 'queued'    -- 双保险：只有仍未被认领的行生效
RETURNING j.id, j.payload;
```

要点：

1. **一条语句**：子查询和 UPDATE 在同一语句、同一隐式事务里，`FOR UPDATE SKIP LOCKED` 保证两个实例不会选中同一行。
2. **`AND j.status='queued'`**：即使有人绕过或锁行为不理想，第二次 UPDATE 会命中 0 行，`RETURNING` 返回空 → 实例知道“没领到”，不会再执行。
3. **返回空就继续下一轮**（见下方循环），不要报错。
4. 也可以给 `status='queued'` 加部分索引：`CREATE INDEX ON jobs (id) WHERE status='queued';`

如果是 PostgreSQL 以外的库（MySQL 8+ 也支持 `FOR UPDATE SKIP LOCKED`；旧版本至少保留 `AND status='queued'` + 检查 affected rows）。若某库没有 `SKIP LOCKED`，`AND j.status='queued'` + 单语句已经足以保证“只执行一次认领”，只是并发实例可能互相空转重试，可接受。

如果你想更简单，甚至可以去掉子查询，用应用侧的乐观并发：

```sql
UPDATE jobs SET status='running', started_at=now(), locked_by=$1
WHERE id=$2 AND status='queued';
-- affected rows = 1 才算领到；= 0 则被别人抢了，回去重查
```

但这仍是“SELECT 候选 + 单条条件 UPDATE”，比原方案安全（不会重复执行业务），只是可能多几次空转。

# 验证步骤

1. **检查返回行数才执行**：代码里必须判断 `RETURNING` 是否为空 / affected rows 是否为 0。这是正确性的最后一道闸门。
2. **并发压测**：插入 100 条 `status='queued'`，启动 N 个实例循环领取，直到返回空。统计每个 `id` 的认领次数：**每个 id 恰好被认领一次，总认领数 = 100**。
   ```sql
   -- 执行完后核对：不应有 running 之外被重复处理痕迹
   SELECT COUNT(*) FILTER (WHERE status='running') FROM jobs;  -- 应等于已领数
   ```
   可用 pgbench、或简单脚本 `for i in 1..N; do psql -c "$SQL"; done &` 并发跑。
3. **故意制造重叠**：把两个实例的领取代码同时停在 UPDATE 前（加 sleep），确认只有一个返回行、另一个返回空。
4. **注入失败重试**：让任务执行抛错，确认回收逻辑把 `status` 改回 `'queued'`（或置 `'failed'` 后由重试调度处理），且重试的是同一条、没有并发重复执行：
   ```sql
   UPDATE jobs SET status='queued', locked_by=NULL
   WHERE id=$1 AND status='running' AND locked_by=$2;  -- 带归还者条件
   ```
   如果担心实例崩溃留下永久 `running`，加租约：`WHERE status='running' AND started_at < now() - interval '10 min'` 回收。
5. **复查日志**：`locked_by` 能直接看出同一 id 是否被两个实例写。压测中若出现同一 id 两个不同 `locked_by` 即为失败。

# 不要承诺 exactly-once

数据库只能保证**任务被认领（claim）一次**。任务在事务外执行，以下情况必然导致“至少一次”：

- 认领成功、任务执行到一半实例崩溃 → 任务状态是 `running`，需要租约回收 + 重新执行；
- 执行成功但“把状态改回 done”之前崩溃 → 会重试；
- 网络分区、进程被 kill、写入成功未返回。

因此设计上要：

- 明确 **at-least-once** 语义；
- 让任务执行**幂等**（业务侧重放安全，例如带唯一键的写入、去重表、条件更新）；
- 重试策略用退避 + 最大次数，失败进入 `failed`/死信；
- 用 `locked_by` + 租约时间做崩溃回收。

一句话：SQL 方案解决的是“不会有两个实例同时认领同一行”，而“执行恰好一次”在事务外不可保证，必须靠幂等兜底。
