# 长期阅读维护

面向单人持续阅读：原始 OCR 保持可追溯，校正有依据，中断可续接，搬家和升级不必重做整套阅读工作。

## 保存与撤销校正

API 返回的是候选转写，只有人工或当前宿主实际核对原图后才能采纳。修订正文放 UTF-8 文件，避免在终端转义 LaTeX：

```text
python "{SKILL_DIR}/scripts/docvision.py" correct add ./out/paper --page 4 --block p4-b5 --text-file ./revision.md --author host --status accepted --reviewer "当前宿主" --evidence "已查看第4页公式原图，核对上下标和编号" --json
python "{SKILL_DIR}/scripts/docvision.py" read ./out/paper --block p4-b5
python "{SKILL_DIR}/scripts/docvision.py" read ./out/paper --block p4-b5 --original
python "{SKILL_DIR}/scripts/docvision.py" correct list ./out/paper --json
python "{SKILL_DIR}/scripts/docvision.py" correct revoke ./out/paper CORRECTION_ID --reviewer "本人" --reason "重新检查后发现依据不足" --json
```

`--author human|host` 记录谁作判断，不能用 API 名冒充复核者。默认 `--status candidate`；`unknown` 可保存无法读清的描述，均不会应用。accepted 要求 `--reviewer` 与至少一项 `--evidence`；不确定部分用可重复的 `--unresolved` 明示。软件记录的是复核者的声明，不声称自动证明看图已发生。

记录包含源 SHA、原页、块或归一化 bbox、原 OCR 及结果指纹、修订、状态与时间，追加存于 `corrections/`；原 `content.json` 和主 Markdown 不改写。整块读取优先展示当前 accepted 修订；按页读取保留原版面并列出限定范围的修订。`--bbox` 只添加区域附注，不猜测要替换哪些字符；页级修订也明确标为附注。源字节、原结果或坐标改变后旧校正不再应用；撤销最新修订不会悄悄复活旧版本。

## 云任务中断后继续

```text
python "{SKILL_DIR}/scripts/docvision.py" jobs list --json
python "{SKILL_DIR}/scripts/docvision.py" jobs resume TASK_ID --allow-remote --json
# 若文件或精读目录已经搬家，显式提供新位置
python "{SKILL_DIR}/scripts/docvision.py" jobs resume TASK_ID --allow-remote --source ./moved/input.png --record ./out/paper/refinements/REQUEST_ID/record.json --json
```

`TASK_ID` 是本机任务号，与服务端 jobId 分别保存。提交前在配置目录旁 `cloud-jobs/` 写入意图，收到 jobId 立即落盘；恢复只 GET 轮询/下载/解析，不 POST。保存选页和源 SHA，恢复时校验同一文件、端点、当前用户远程同意及本次开关；精读恢复也更新原 record，保留论文原页/bbox。

没有 jobId 的 `submission_unknown` 无法判断服务端是否收到了提交，先查服务账号，不能自动重试。明确决定新提交时，convert 可用 `--extra cloud_new_attempt=true`，refine 用 `--force` 新建尝试；可能重复消耗额度。仅移动文件可用 `--source` 提供同 SHA 新路径；URL 来源因无法确认原始字节，不支持可靠恢复，需恢复能力的任务先下载成本地文件。凭据、签名下载链接不写任务回执；`--keep-raw` 保存的原始服务响应仍可能含临时链接，分享时应排除。

## 文献和输出搬家

把整个文档输出目录移动，保留其 assets、refinements、corrections。新精读记录的内部引用相对文档目录保存，CLI 返回当前可用的绝对路径。原文也移动或重命名后执行：

```text
python "{SKILL_DIR}/scripts/docvision.py" relink ./new-location/paper --source ./new-location/original.pdf --dry-run --json
python "{SKILL_DIR}/scripts/docvision.py" relink ./new-location/paper --source ./new-location/original.pdf --json
```

只能重绑 SHA-256 完全一致的源，不扫描磁盘找相似文件，不用改路径绕过源版本验证。成功后保存相对源路径（跨 Windows 卷时保留绝对路径），以后原文与输出一起移动可继续使用。旧绝对精读引用可用不带 `--source` 的 `relink` 规范化；迁移日志保存在 `relinks/`。不要单独搬走某个 asset 或 crop。

## 环境更新与回退

```text
python "{SKILL_DIR}/scripts/docvision.py" setup --profile mineru --sample ./paper.pdf --sample-page 4 --dry-run
python "{SKILL_DIR}/scripts/docvision.py" setup --profile mineru --sample ./paper.pdf --sample-page 4 --yes
python "{SKILL_DIR}/scripts/docvision.py" setup --history --json
python "{SKILL_DIR}/scripts/docvision.py" setup --rollback SNAPSHOT_ID --dry-run
python "{SKILL_DIR}/scripts/docvision.py" setup --rollback SNAPSHOT_ID --yes
```

先保存原配置与已配置环境的版本，再建新环境及模型目录，候选单页通过结构验收后原子切换；失败保留旧默认和诊断记录，不升级原环境。OCR 安装需提供一页实际样本；自动结构通过不能证明识别更准，模型升级后仍应查看样本的关键公式/表格。回退恢复快照的安装字段，保留当前 API 凭据、远程同意与其他设置，不删除环境或模型。快照在配置目录旁保存；旧环境/模型也要保留到确认新版本可用后再自行清理。
