# 夹具：真实坏例（只读副本）

这里的 HTML/JSON **不是手造的**，是从另一个真实项目**逐字复制**过来的，作为"检查器能抓"的反证材料。

| 文件 | 来源（绝对路径） | sha256（前 16 位） | 角色 |
|---|---|---|---|
| `renzhi/frag-L00-S1.html` | `/Users/a18760/Desktop/人智与图识学习工作区/book/_static/labs/frag-L00-S1.html` | `9e474bf8392d9f0e` | **坏例**（注入正文的片段：无 md()、`<style>` 块 0 个） |
| `renzhi/lab-L00-S1.html` | `/Users/a18760/Desktop/人智与图识学习工作区/book/_static/labs/lab-L00-S1.html` | `fef990da9e307e44` | **好例**（同数据的独立小页：有 md() 与 2 个 `<style>` 块） |
| `renzhi/foundation-index.json` | `/Users/a18760/Desktop/人智与图识学习工作区/content/tasks/foundation-index.json` | `8ff1fdb8d4ca12a5` | 数据源（"教材关卡的唯一来源"） |

复制时间：2026-10-10。

## 为什么用真实坏例而不是手造

本项目自己的台账写得很清楚：手造的坏例只覆盖想象得到的形状。这一对产物的价值在于
**同一份数据、两条渲染路径**——好例证明"这个能力是可实现的"，坏例证明"缺了会怎样"。
一条检查能同时通过这两项，才算它真的在辨别，而不是在空转。

## 修好之后怎么办

坏例**不要删**。修复走"补丁"而不是直接改这个副本：

1. 检查器先红（证明它抓得到）；
2. 修复补丁应用到**源项目**（由那边的人或 agent 应用，本仓库不改别人的项目）；
3. 源项目产物更新后，用同一份夹具流程重跑 —— 那时 `frag` 的 `expect` 才会从 `fail` 改成 `pass`。

反过来：如果哪天 `frag` 被判成 `pass` 而它并没有被修，说明**检查器坏了**——这正是
`runner.py --selftest` 会拦住的情况。

## 刷新夹具

源项目内容变化后，重新复制并更新上表的 sha256：

```bash
SRC=/Users/a18760/Desktop/人智与图识学习工作区
cp "$SRC/book/_static/labs/frag-L00-S1.html" renzhi/
cp "$SRC/book/_static/labs/lab-L00-S1.html"  renzhi/
cp "$SRC/content/tasks/foundation-index.json" renzhi/
shasum -a 256 renzhi/*
```
