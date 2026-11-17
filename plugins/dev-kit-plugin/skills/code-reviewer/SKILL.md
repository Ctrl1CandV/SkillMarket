---
name: code-reviewer
description: 审查一段代码改动的正确性、安全、兼容性和可维护性，只报有触发条件和后果的实际问题。用于审 PR 或 diff、提交前做代码质量检查；dev-acceptance 的审查者看代码时也用它。项目写明的编码规范优先，一组常见坏味道作兜底。
license: MIT
metadata:
  version: "0.2.0"
  upstream: "alirezarezvani/claude-skills@7b1abd5 engineering-team/skills/code-reviewer（rules、languages）"
---

# 代码审查

## 1. 定范围

审的是一段确定的改动，即用户给的提交、分支或 PR。用户没给起点，就问。

用 `git diff <起点>...HEAD` 和 `git log <起点>..HEAD --oneline` 把范围固定下来，并先确认起点存在、改动不为空。

然后读改动涉及的调用方和测试。项目里有开工确认单（`docs/briefs/`）的，也一起读，用来判断改动有没有超出范围。

## 2. 找项目自己的规范

在项目里找写明代码怎么写的文件：CONTRIBUTING.md、CODING_STANDARDS.md、AGENTS.md、CLAUDE.md，以及 lint 和格式化配置。

项目写明的规范优先。项目明确认可的写法，即使第 3 步的坏味道会标出来，也不报。工具已经自动检查的规则，不再重复报。

## 3. 按影响从大到小找问题

**先看会出事的地方**：正确性、安全、数据丢失、资源释放、并发、接口兼容，以及该有却没有的回归测试。

**再看会拖累以后修改的地方**。下面这组坏味道在项目没写规范时也适用。每一条都只是判断，报的时候写成“可能是……”：

- 名字说不清用途：改名。想不出贴切的名字，往往说明设计本身不清楚。
- 同样的逻辑出现在几处：提取出来共用。
- 函数总在用别的模块的数据：把它挪到那份数据旁边。
- 几个字段或参数总是一起出现：合成一个类型。
- 用字符串或基本类型代替本该独立的概念：给这个概念一个小类型。
- 同一组 `switch` 或 `if` 分支在几处重复：改成一张共用的映射，或者用多态。
- 一个改动要动很多文件：把一起变化的东西收进一个模块。
- 一个模块因为几种不相干的原因被反复修改：拆开，让每个模块只为一种原因修改。
- 为需求里没有的情况加的抽象、参数或钩子：删掉，等真有需要时再加。
- 调用方要顺着 `a.b().c().d()` 一路往下取：把这段查找藏到第一个对象的一个方法里。
- 只是转手调用的中间层：删掉，直接调用真正干活的对象。
- 子类或实现忽略、改写了大部分继承来的东西：去掉继承，改用组合。

需要按语言细看时，读下表里对应的语言指南；跨语言的通用规则在 `rules/universal.md`。用到哪节读哪节。

| 文件类型 | 语言指南 |
|---|---|
| Python | `languages/python.md` |
| TypeScript / JavaScript | `languages/typescript.md` |
| Go | `languages/go.md` |
| Swift | `languages/swift.md` |
| Kotlin | `languages/kotlin.md` |
| C# / .NET | `languages/csharp.md` |
| Java | `languages/java.md` |
| C / C++ | `languages/c.md`、`languages/cpp.md` |
| Rust | `languages/rust.md` |
| Ruby | `languages/ruby.md` |
| PHP | `languages/php.md` |
| Dart / Flutter | `languages/dart.md` |

每个问题都写清四件事：位置、触发条件、后果、可行的改法。分清“已确认的缺陷”和“要复现才能确认的风险”。风格偏好不算缺陷，也不为凑数找问题。

## 4. 能跑就跑

权限允许时，跑项目已有的检查，比如测试、类型检查、lint。不能跑的，说明原因，并请派你来的一方去跑指定的检查。没跑过的检查，不说跑过。

## 报告

1. 先按影响分组列出问题。
2. 再写跑过的检查及结果。
3. 最后写没能确认的地方。

没有问题时，写“没有需要处理的问题”，但这不等于证明没有缺陷。合不合并由用户或项目流程决定，不看分数。

规则和语言指南来自 alirezarezvani/claude-skills（MIT 许可），说明正文为本仓库重写，坏味道清单参考 mattpocock/skills 的 code-review（MIT 许可）。
