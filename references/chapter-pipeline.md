# 章节流水线

## 写前

运行 `storyctl status` 与 `storyctl preflight`。读取 L0–L3 上下文后，创建章节意图卡：POV、时间地点、章节问题、人物目标与阻力、情绪/爽点、必须推进与禁止改变事项、伏笔、结尾拉力、目标字数。

用 `storyctl stage --chapter N --title 标题` 创建工作区。工作区中应有：

- `draft.md`：正文；
- `summary.md`：100–300 字、只记录正文已发生的事；
- `facts.json`：正文新增或修订的事实；
- `hooks.json`：伏笔状态变动；
- `review.json`：审稿结论。

## 审稿与结算

先做确定性检查，再做独立的判断性审稿。只有 `review.json` 为 `pass`，且事实与伏笔 JSON 合法时，运行 `storyctl commit --chapter N`。任何冲突、需要改总纲的变更、或 `needs_author` 状态均须停下来请作者裁决。

提交后再运行 `storyctl validate`。若派生索引或可视化将来失败，正文和已确认正史仍然有效；报告该派生视图滞后，不要回滚章节。
