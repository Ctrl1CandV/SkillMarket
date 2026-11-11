## 原因

`SELECT ... LIMIT 1` 和 `UPDATE ... WHERE id=$1` 是两次独立的自动提交事务。从 SELECT 到 UPDATE 之间存在竞态窗口：

1. 实例 A 先 SELECT 到任务 42；此时还没有加锁，实例 B 看到同一个任务仍是 `queued`，于是也 SELECT 到 42。
2. 两个实例各自执行 UPDATE，结果都变成 `running`，并且因此都认为自己抢到了。
3. 这两条 UPDATE 都返回 1 行，第二个 UPDATE 覆盖第一个，没有任何语句报错或冲突。

关键点在于：`UPDATE ... WHERE id=$1` 这个条件本身不检查 status，所以它不会阻止重复认领。读取和写入之间没有任何东西保证“同一个任务只会被认领一次”，除非把判断合并进写语句，或者使用行锁。

## 改法：把“判断 + 认领”合成一条 UPDATE

使用 `RETURNING` 拿到被认领的任务，不再单独 SELECT，也不要先查后改：

```sql
UPDATE jobs
   SET status = 'running',
       started_at = now(),
       attempts = attempts + 1
 WHERE id = (
         SELECT id
           FROM jobs
          WHERE status = 'queued'
          ORDER BY created_at, id
          FOR UPDATE SKIP LOCKED
          LIMIT 1
       )
   AND status = 'queued'
RETURNING id, payload, attempts;
```

要点：

- `FOR UPDATE SKIP LOCKED`：A 锁住候选行时，B 直接跳过它去锁下一行，不等待、不重复，两台机器并行也不会拿到同一行。
- 外层 `AND status='queued'`：这是一道后备保护，防止子查询选出行之后、外层更新之前 status 已被改成其他值（例如被人工取消）。
- 返回 0 行就表示“当前没有可认领的任务”，稍后再来，不要当作错误。
- `attempts + 1` 让重试次数有据可查，用于后续退避和死信判断。
- `ORDER BY created_at, id` 保证扫描顺序稳定，避免乱序和跳任务。

如果你们用的是 MySQL，或者需要给任务加归属和租约（用于崩溃恢复），可以改成租约模型：

```sql
UPDATE jobs
   SET status = 'running',
       locked_by = :worker_id,
       lease_until = now() + interval '5 minutes',
       attempts = attempts + 1
 WHERE status = 'queued'
    OR (status = 'running' AND lease_until < now())
 ORDER BY created_at
 LIMIT 1
 RETURNING id, payload, attempts;
```

注意：PostgreSQL 没有 `UPDATE ... ORDER BY ... LIMIT`，必须用上面那种子查询写法；MySQL 8 可以直接用这条。另外还要有一步定期把 `lease_until` 过期、`status='running'` 的任务重新置回 `queued`（即崩溃恢复），否则任务会卡在 `running` 状态。

## 验证步骤

1. **单实例串行测试**：依次调用两次认领语句，第一次返回 1 行 `attempts=1`，第二次返回 0 行。先确认基本逻辑正确。
2. **双并发压测**：两个客户端在同一个事务里执行 `BEGIN;` 加上面的 UPDATE 语句，手工在结尾加 `pg_sleep(2)`，先不提交，然后让两者互相交错：
   - 旧写法：两边的 `UPDATE` 都得到 `rowcount=1`，也就是复现你观察到的 bug。
   - 新写法：后到的那次会阻塞（`FOR UPDATE` 没有 SKIP LOCKED 时）或直接跳过（有 SKIP LOCKED 时），只可能有一方拿到这一行。
3. **在测试库里造出 1000 条 `queued` 任务，启动 4 个 worker 实例并发消费**，跑完之后检查：
   ```sql
   SELECT id, count(*) FROM job_runs GROUP BY id HAVING count(*) > 1;
   ```
   或者在每次真正执行任务前打日志，并给每次执行生成一个唯一的 run id（执行记录表里 `UNIQUE (job_id, attempt)`），然后检查有没有重复的 `job_id` 出现两次执行记录。发生重复执行时必须出现零结果，这是“同一任务不会被两个 worker 同时执行”的口径。
4. **崩溃场景**：认领后让 worker 进程 `kill -9`，验证租约版能过一段时间把任务重新放回可认领状态，且 `attempts` 递增，达到上限的任务会进入 `dead`，而不是无限重试。

## 关于 exactly-once

上面只能保证**同一时刻只有一个 worker 持有该任务**，不能保证**只执行一次**。至少这三处仍会导致重复执行：worker 认领后、任务执行中或提交结果前崩溃，租约过期后任务会被别人重做；网络超时导致 worker 以为失败并重试，实际上第一次已经生效。因此：

- 把任务执行做成**幂等**：给任务带一个稳定的业务键，在写入侧使用 `INSERT ... ON CONFLICT DO NOTHING` 或唯一约束去重；或让下游操作接受重复送达。
- 用 `attempts`、`request_id`、执行记录表做审计，把“重复执行”当成必然发生的事件来探测和核对，而不是当成 bug 去消灭。
- 明确语义是 **at-least-once**，需要精确次数的业务单独设计（例如结果表加唯一键，配合补偿校验）。