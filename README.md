# web-story

面向中文网络小说创作的单入口 Agent Skill。

`web-story` 用自然语言协助你从开书、规划、连载、审稿到投稿准备，并把正文、正史、伏笔、章节摘要和审稿结果保存在本地项目中。它的目标不是“一键生成百万字”，而是让短篇、中篇和长篇连载能持续写下去、不轻易写崩。

## 能做什么

```text
/web-story 写一本适合起点的玄幻升级文，预计 150 万字，第一章要有强钩子
/web-story 给我三套都市情感短篇方案，比较开篇卖点
/web-story 继续《夜航者》第 12 章，师父线不能改
/web-story 审第 18 章，找出影响追读的硬伤并修订
/web-story 为《替嫁后我成了侯府掌事人》生成通用投稿包
```

你不必记忆规划、写章、审稿、查询等多个子命令。Skill 根据请求和书籍状态在内部路由工作流。

在 Codex 中可显式使用 `$web-story`；如果当前界面将 `/web-story` 原样传入对话，Skill 同样会将它视为明确入口。

## 核心原则

- **作者拥有正史。** 已接受正文与确认事实是权威；摘要、统计和未来检索索引都可以重建。
- **一章是一笔事务。** 草稿、摘要、事实、伏笔和审稿在工作区中完成，校验通过后才一起提交。
- **长篇按需读上下文。** 默认读取当前目标、硬设定、相邻正文和相关线索，不把整本书塞进上下文。
- **判断与计算分工。** 剧情、人物、节奏由模型和作者判断；字数、schema、状态对账和提交交由脚本完成。
- **投稿准备不等于收益承诺。** Skill 可以整理材料与复核清单，但不能保证过审、签约或收入。

## 安装

将本仓库作为 Skill 文件夹安装或导入到你的 Codex Skill 目录。核心入口为 `SKILL.md`，无第三方 Python 依赖。

如果你仅想在当前项目使用，可以把整个 `web-story/` 目录放入项目的 Skill 目录；如果你使用个人全局 Skill 目录，则将该目录放入对应位置后重新打开或刷新 Codex。

> 本仓库目前不包含平台专用投稿规则。投稿前请自行核对目标平台最新的官方协议与作者规则。

## 快速开始

### 1. 创建书籍项目

在你准备存放小说的空目录中执行：

```bash
python3 /path/to/web-story/scripts/storyctl.py init \
  --project-root ./我的小说 \
  --title "夜航者" \
  --mode serial
```

`--mode` 可选：

- `short`：一次性完成的短篇；
- `medium`：按幕或卷推进的中篇；
- `serial`：按 3–10 章批次推进的长篇连载。

创建后，先使用 `$web-story` 补全创作简报、总纲、人物关系、文风契约和首批章节计划，再开始正文。

### 2. 写并提交第一章

先让 Skill 根据项目状态生成章节意图卡与正文。需要手动检查工作流时，底层命令如下：

```bash
# 查看真实项目状态与写前检查
python3 /path/to/web-story/scripts/storyctl.py status --project-root ./我的小说
python3 /path/to/web-story/scripts/storyctl.py preflight --project-root ./我的小说

# 创建第 1 章工作区
python3 /path/to/web-story/scripts/storyctl.py stage \
  --project-root ./我的小说 \
  --chapter 1 \
  --title "雨夜来信"
```

工作区位于 `.web-story/staging/chapter-0001/`，其中包含：

| 文件 | 用途 |
|---|---|
| `intent-card.md` | 本章目标、冲突、禁止改变事项、伏笔与结尾拉力 |
| `draft.md` | 章节正文 |
| `summary.md` | 只记录正文已经发生的事件 |
| `facts.json` | 本章新增或修订的事实 |
| `hooks.json` | 伏笔状态变动 |
| `review.json` | 审稿结论；只有 `status: "pass"` 才能提交 |

审稿通过后提交并校验：

```bash
python3 /path/to/web-story/scripts/storyctl.py commit \
  --project-root ./我的小说 \
  --chapter 1

python3 /path/to/web-story/scripts/storyctl.py validate --project-root ./我的小说
```

提交会把正文写入 `正文/`，并同步接受摘要、事实、伏笔、审稿报告和可恢复运行记录。脚本拒绝跳章、重复提交、空草稿、未审稿或格式不合法的工作区。

## 项目结构

```text
我的小说/
├── 正文/                         # 已接受章节
├── 大纲/                         # 创作简报、总纲、卷纲、章节意图
├── 设定集/                       # 人物、世界观、文风契约
├── 素材/                         # 作者拥有或获授权的参考资料
├── 投稿包/                       # 导出的全稿与投稿准备材料
└── .web-story/
    ├── manifest.json             # 书籍身份、模式、真实进度
    ├── canon.json                # 人物、事件、关系等结构化正史
    ├── timeline.json             # 时间线
    ├── hooks.json                # 伏笔与读者承诺账本
    ├── current-focus.md          # 未来 1–3 章的作者方向
    ├── summaries/                # 章节和分卷摘要
    ├── reviews/                  # 审稿结论
    ├── runs/                     # 提交快照和已归档工作区
    └── staging/                  # 未提交章节工作区
```

`.web-story/` 是每部书的运行状态，不是 Skill 源码的一部分；仓库的 `.gitignore` 已忽略这类生成项目文件。

## `storyctl` 命令

| 命令 | 作用 |
|---|---|
| `init` | 创建空书籍项目与状态文件 |
| `status` | 根据磁盘文件计算项目状态 |
| `preflight` | 写前检查目录、状态和未结算工作区 |
| `stage` | 创建可恢复的章节工作区 |
| `validate` | 校验 schema、正文、摘要与提交清单 |
| `reconcile` | 对账正文、摘要、正史和运行状态，不静默修复 |
| `commit` | 将已通过审稿的工作区原子化地接受为下一章 |
| `build` | 生成全稿和通用投稿前人工复核清单 |

所有命令输出 JSON；因此 Skill 可以根据真实结果报告进度，而不是仅凭模型的文字判断“已经完成”。

## 审稿与修订

审稿分为两部分：

1. 脚本检查：文件结构、顺序、字数、状态、摘要与正史的基本一致性；
2. 叙事审稿：因果、人物动机、知识边界、节奏、对白、章节承诺、钩子和文风。

中高严重度问题必须给出位置、证据、读者影响和可执行的修改建议。若改动会影响已接受章节、核心动机、结局或世界规则，Skill 会先列出影响范围并等待作者确认。

## 投稿准备

使用下面的命令可生成通用投稿准备文件：

```bash
python3 /path/to/web-story/scripts/storyctl.py build \
  --project-root ./我的小说 \
  --platform "通用中文商业网文"
```

输出位于 `投稿包/`，包含合并全稿、投稿包清单和人工复核清单。后续版本会在作者明确选择某个平台并核对其当期官方规则后，再提供平台专用 profile。

`web-story` 不提供规避 AI 检测、伪造人工创作或模仿在世作者独特文风的功能。它帮助作者做原创、可审阅的协作创作，并保留关键修改与决策的本地记录。

## 开发与测试

仅依赖 Python 标准库。运行测试：

```bash
python3 -m unittest discover -s tests -v
```

当前测试覆盖：

- 新建书籍 → 暂存章节 → 审稿通过 → 提交 → 校验 → 投稿包导出；
- 未通过审稿时禁止提交；
- 摘要丢失时 `reconcile` 能报告状态差异。

## 当前范围与路线图

当前版本是可靠的最小闭环：短篇/中篇脚手架、章节工作区、正史/伏笔状态、基础对账和通用投稿准备。

后续计划包括长篇批次管理、分卷摘要、导入已有正文、可重建本地检索、结构化修订影响分析与经过明确授权的平台 profile。

## 参考与许可证

本项目从零实现，并参考了公开项目的架构思路：`webnovel-writer` 的事实提交链、InkOS 的自然语言入口与章节工作区、`chinese-novelist-skill` 的递进式开书、Storywright 的 story bible、Longform 的活文档，以及 Novel Ralph 的确定性工具边界。

请勿直接复制受 GPL/AGPL 保护项目的代码、提示词或模板；本仓库尚未声明开源许可证，在对外分发前应先确定许可证。
