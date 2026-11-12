封面已经做好了：`/home/claude-dev/.local/share/skillmarket-tools/runs/imagecraft/2026-11-12/a2/task/cover.png`（1200×630，PNG）。

**先说最重要的一句：这张图是用代码画的，并非由 AI 生成。**
我按顺序检查了两条生图通道：
- 本机：`discover` 报告 GPU `present_but_inaccessible`（WSL 里 NVML 被系统挡住），也没找到 ComfyUI，更没有 FLUX 权重；
- 云端：没装 `codex` CLI，也没有 ChatGPT 订阅登录，无法上传生成。

所以我按「原生绘制」处理，用 Pillow 从零绘制了一张扁平编辑插画风格的封面，这样也能做到文字逐字可控、以后改起来方便。

**画的是什么**
- 暖象牙纸底和青灰釉陶杯：杯壁略不均、把手略歪，杯口保留一圈不上釉的素胎；这些细节正是文中那只每天用的杯子。
- 文案（逐字核对过）：
  - 眉标：陶艺课笔记
  - 主标题：第一次自己做陶杯
  - 副标题：三个周末，四只杯子，一只留下
  - 页脚：揉泥 · 拉坯 · 修坯 · 上釉
- 配色：象牙底 #F4EEE4，青灰釉 #7F928D，陶土 #D6BFA2，炭黑字，陶红点缀。

**想换成真正的生图**
显卡可用，或能装上 ComfyUI 并放好权重（约 12.5 GB，需 25 GB 空间）后，我可以按同一份 brief 出一批 FLUX 或 Z-Image 的版本再挑；或者你装好 `codex` CLI 并登录后走云端（需你明确同意上传提示词）。brief 已经存在 `.imagecraft/briefs/cover-brief.md`。

**要改字或改配色**：直接改 `.imagecraft/scratch/make_cover.py` 重跑即可，精确不会跑偏；`.imagecraft/` 是临时工作区，交付确认后可整个删掉。