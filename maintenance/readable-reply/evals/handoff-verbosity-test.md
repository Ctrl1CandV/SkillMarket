# readable-reply 2.0.0 简洁度对照试跑：交接说明

给执行者（GPT、DeepSeek 或其他 Agent）的自包含说明。不需要读这个仓库的其他内容。

## 目的

检查 readable-reply 2.0.0 的规则（或它的全局指令短版）是否真的让回复更短、更直接，同时没有把必要内容删掉。只记录事实，不下结论，不修改任何技能文件。

## 如果用 pi 跑

不必手工操作：题目已存成 `prompts/*.txt`，`run_pi.sh` 会用 pi 的 JSON 模式把 6 题 × 4 组（A 无指令、B 全局短版、C 提供技能由模型自行加载、D 强制加载技能）跑完，最终回复写入 `raw/*.md`，工具调用写入 `raw/*.tools.txt`；所有组只开放 `read` 工具，因为 pi 的技能须由模型用 read 读取才算加载。`measure.py` 再统计字数、标题、加粗、列表项等客观指标。关键点命中与“第一句是否直接回答”仍须人工读原文判断。

```sh
pi --list-models deepseek          # 先确认模型名称
bash run_pi.sh deepseek            # 在本目录运行；gpt 同理
python3 -I measure.py raw
```

下面是不用脚本时的手工做法与题目说明。

## 要用到的文件

- 全局指令短版：`readable-reply/references/global-instruction.md` 里的代码块文字。
- 完整技能：`readable-reply/SKILL.md`（仅当宿主能加载技能时用）。

## 做法

对下面 6 个题，各跑三组，每组都在**全新会话**里，只发这一条用户消息：

- **A 组**：不加任何指令。
- **B 组**：在会话最前面放入全局指令短版的那段文字，再发题目。
- **C 组**（宿主能加载技能时才做）：加载 readable-reply 技能，再发题目。

每个回复的**原文**存成文件：`maintenance/readable-reply/evals/raw/<题号>-<组>.md`。不要改写、不要删减。

## 6 个题与关键点

关键点是回复里必须有的信息，用来判断有没有“删过头”。

1. **事实题**：`Python 里 list 和 tuple 有什么区别？`
   关键点：①list 可变、tuple 不可变；②tuple 可哈希，可以做 dict 的键（或集合元素）。
2. **操作题**：`我的 git push 被拒绝了，提示 non-fast-forward，怎么办？`
   关键点：①原因是远端有本地没有的提交；②先 fetch 并查看差异；③合并或 rebase 后再 push；④不要直接 force push。
3. **复杂技术题**（需要保留 SQL 和步骤，检查不会压过头）：
   `两个应用实例各自先 SELECT id FROM jobs WHERE status='queued' LIMIT 1，再 UPDATE jobs SET status='running' WHERE id=$1，两条语句各自自动提交。偶尔同一个任务执行两次。请解释原因，给一个可以改的 SQL 方案和验证步骤。任务在数据库事务之外执行，失败后需要重试，不要承诺 exactly-once。`
   关键点：①查找和认领不是一个原子操作；②用 FOR UPDATE SKIP LOCKED 或带条件的 UPDATE … RETURNING；③有 SQL 代码；④有并发验证步骤；⑤没有承诺 exactly-once。
4. **建议题**：`我们团队 10 个人，要给一个内部小工具选数据库，SQLite 和 PostgreSQL 选哪个？`
   关键点：①给出明确倾向；②说明在什么条件下换另一个（并发写入、多机或网络访问、运维能力）。
5. **评审题**：
   ```python
   def get_user(conn, name):
       cur = conn.execute("SELECT * FROM users WHERE name = '%s'" % name)
       return cur.fetchone()[0]
   ```
   题目：`帮我看看这个函数有什么问题。`
   关键点：①SQL 注入，应参数化；②fetchone() 可能返回 None，导致 TypeError；③SELECT * 后取 [0] 含义不明（可选）。
6. **信息不足的排障题**：`网站今天突然很慢，帮我排查。`
   关键点：①不假装已知原因；②给出最少的判别步骤或先问最关键的信息，而不是几十条清单。

## 每个回复要记录的指标

| 指标 | 怎么记 |
|---|---|
| 字数 | 去掉代码块后的汉字与英文单词总数 |
| 第一句是否直接回答 | 是 / 否（客套、复述题目算否） |
| 标题数 / 加粗处数 / 列表项数 | 数一下 |
| 结尾是否有总结或客套 | 是 / 否（如“综上”“希望对你有帮助”） |
| 关键点命中 | 命中数 / 总数，逐条标出缺哪条 |

## 结果怎么交

写成 `maintenance/readable-reply/evals/results-<日期>.md`：每题一张表，行是 A / B / C 组，列是上面的指标，表后各写一两句事实描述（例如“B 组比 A 组少了结尾总结，缺关键点 ④”）。

不要写“效果好”“有效”这类结论，不要建议修改技能，不要修改 raw 以外的任何已有文件。盲评偏好（哪个更好读）由用户自己做，不由执行者判断。

## 注意

- 每组每题只跑一次；如果跑了多次，全部保留，不挑选。
- 题目里的代码和数据不要改。
- 记录所用的模型名称与版本、日期，写在结果文件开头。
