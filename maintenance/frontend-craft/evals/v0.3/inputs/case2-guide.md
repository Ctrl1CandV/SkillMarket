# ReAct 导读：让语言模型边想边做

论文：ReAct: Synergizing Reasoning and Acting in Language Models
作者：Shunyu Yao, Jeffrey Zhao, Dian Yu, Nan Du, Izhak Shafran, Karthik Narasimhan, Yuan Cao
发表：ICLR 2023（arXiv 2210.03629）
导读适合：读过 Chain-of-Thought、想了解 Agent 基本工作方式的同学，预计阅读 15 分钟。

在 ReAct 之前，大语言模型的两种能力基本是分开研究的：一边是推理，比如 Chain-of-Thought（CoT）让模型先写出中间步骤再给答案；另一边是行动，比如让模型生成动作计划、在环境里一步步操作。ReAct 的想法很直接：让模型交替写“想法”和“动作”，想法帮助它制定、跟踪和修改计划，动作让它从外部取得新信息。这篇导读按“问题—方法—实验—局限”的顺序梳理全文，重点放在方法和实验设计上。

## 一、这篇论文想解决什么

只做推理的模型有一个老问题：它所有的判断都来自自己的参数，遇到需要事实的问题时，推理链看起来通顺，却可能建立在一个记错的事实上，而且错误会沿着链条一路传下去。论文把这类问题称为幻觉（hallucination）和错误传播（error propagation）。

只做行动的模型则相反。它能调用搜索、能在环境里操作，但没有显式的推理过程，很难把大目标拆成小目标，也很难在某一步失败后意识到需要换一种做法。

作者的判断是：人在完成任务时本来就是边想边做的，想的内容决定下一步做什么，做的结果又反过来修正想法。如果让模型也按这种方式工作，两种能力应该可以互相补足。

## 二、ReAct 怎么做

ReAct 不训练新模型，核心是一种提示方式。提示里放一两个人工写好的解题轨迹，模型照着格式往下生成。每条轨迹由三种内容交替组成：

- **Thought（想法）**：用自然语言写下当前的判断，比如“我需要先查出这个人出生在哪一年”。想法不改变外部环境。
- **Action（动作）**：调用一个外部接口。在问答任务里，作者只给了三个动作：`search[实体]` 搜索维基百科页面，`lookup[字符串]` 在当前页面里找关键词，`finish[答案]` 给出最终答案。
- **Observation（观察）**：外部接口返回的结果，由环境填入，不由模型生成。

这样，模型每一步都能看到真实返回的信息，再决定下一步。对知识类任务，想法和动作通常一一交替；对需要很多步操作的决策类任务，想法只在需要的时候出现，比如拆分目标或者发现计划走不通的时候。

> 图 1（原文 Figure 1）：同一道 HotpotQA 问题在 Standard、CoT、Act-only、ReAct 四种提示方式下的解题轨迹，以及 ALFWorld 中 Act-only 与 ReAct 的对比。导读没有复制原图，建议对照原文阅读。

下表概括了这四种方式的区别：

| 方式 | 显式推理 | 调用外部信息 | 主要风险 |
| --- | --- | --- | --- |
| Standard | 无 | 无 | 直接给答案，无法检查过程 |
| CoT | 有 | 无 | 推理通顺但事实可能是编的 |
| Act-only | 无 | 有 | 能查资料，但不会拆解目标和纠错 |
| ReAct | 有 | 有 | 轨迹更长，搜索结果不好时可能原地打转 |

## 三、实验看什么

论文在两类任务上测试 ReAct。第一类是知识密集型推理：多跳问答 HotpotQA 和事实核查 FEVER，模型只能通过上面三个动作访问维基百科。第二类是交互式决策：ALFWorld 是文字版的家务环境，WebShop 是模拟的网上购物。

读实验部分时，建议关注三个结果。

第一，在 HotpotQA 和 FEVER 上，ReAct 通过查维基百科，明显减少了 CoT 中常见的幻觉和错误传播，生成的轨迹也更容易被人读懂和检查。但只用 ReAct 并不总是最好的，论文把 ReAct 和 CoT 结合起来，按条件在两者之间切换，效果更好。这说明内部知识和外部检索各有长处。

第二，在 ALFWorld 和 WebShop 上，ReAct 只用一到两个示例，成功率就比模仿学习和强化学习方法分别高出 34 和 10 个百分点（绝对值）。这是论文里最醒目的数字，注意它比较的是提示方法和需要大量训练数据的方法。

第三，论文做了错误分析。ReAct 的失败有不少来自搜索没有返回有用信息，以及模型反复生成相同的想法和动作、陷入循环。读这部分可以帮助理解后来的工作为什么要加入反思或记忆。

## 四、局限与延伸阅读

ReAct 依赖人工写的示例，示例的质量和风格会影响结果；轨迹较长，复杂任务容易超出上下文长度；动作空间也是人为设计的，换一个任务就要重新定义。作者还尝试用 ReAct 轨迹微调较小的模型，这部分可以作为选读。

读完 ReAct，可以接着读两篇工作：Reflexion 让模型在失败后写下反思、存进记忆再重试，直接回应了上面提到的“原地打转”问题；Toolformer 则让模型自己学会在什么时候调用什么工具，而不是靠提示示例。

## 自测

1. Thought、Action、Observation 三者中，哪一个不是模型生成的？为什么这一点重要？
2. 为什么在 HotpotQA 上单独使用 ReAct 不一定比 CoT 好？
3. 34 和 10 个百分点是和哪类方法比较得出的？

## 参考来源

1. Yao et al. ReAct: Synergizing Reasoning and Acting in Language Models. https://arxiv.org/abs/2210.03629
2. ReAct 项目主页与代码：https://react-lm.github.io
3. Wei et al. Chain-of-Thought Prompting Elicits Reasoning in Large Language Models. https://arxiv.org/abs/2201.11903
4. Shinn et al. Reflexion: Language Agents with Verbal Reinforcement Learning. https://arxiv.org/abs/2303.11366
5. Schick et al. Toolformer: Language Models Can Teach Themselves to Use Tools. https://arxiv.org/abs/2302.04761
