# 夹具：真实坏例（只读副本）

这里的产物**不是手造的**，是从 `人智与图识学习工作区` **逐字复制**过来的，作为"检查器能抓"的反证材料。
复制时间：2026-10-10 ｜ 来源根：`/Users/a18760/Desktop/人智与图识学习工作区`

**为什么是 8 对**：同一个脚本 `scripts/build-lab-fragments.py` 写出两条渲染路径——
`:755-759` 写片段（原样塞 `q.text`，无 `md()`），`:765-772` 写独立页（`:767` 把 `FRAGMENT_CSS` 只注入这一条）。
所以 8 个课时**全部**都坏，而不是偶发。一条检查能在这 16 个真实产物上全部判对，才算它在辨别。

| 文件 | sha256 | 角色 |
|---|---|---|
| `foundation-index.json` | `8ff1fdb8d4ca12a5` | 数据源（教材关卡唯一来源） |
| `frag-L00-S1.html` | `9e474bf8392d9f0e` | **坏例**（片段：0 个 `<style>`、无 md()） |
| `frag-L00-S2.html` | `6251c296b810d16e` | **坏例**（片段：0 个 `<style>`、无 md()） |
| `frag-L00-S3.html` | `ee59297a8888d460` | **坏例**（片段：0 个 `<style>`、无 md()） |
| `frag-L00-S4.html` | `e57e4c9f3a85d986` | **坏例**（片段：0 个 `<style>`、无 md()） |
| `frag-L00-S5.html` | `33ece0b168f34e68` | **坏例**（片段：0 个 `<style>`、无 md()） |
| `frag-L00-S6.html` | `0d30c4836c129be5` | **坏例**（片段：0 个 `<style>`、无 md()） |
| `frag-L00-S7.html` | `a2ee11feeb5b788d` | **坏例**（片段：0 个 `<style>`、无 md()） |
| `frag-L00-S8.html` | `7ae3f62989a490ee` | **坏例**（片段：0 个 `<style>`、无 md()） |
| `lab-L00-S1.html` | `fef990da9e307e44` | **好例**（独立页：2 个 `<style>`、有 md()） |
| `lab-L00-S2.html` | `34d574a4f8e108f9` | **好例**（独立页：2 个 `<style>`、有 md()） |
| `lab-L00-S3.html` | `0c6088502c6bf378` | **好例**（独立页：2 个 `<style>`、有 md()） |
| `lab-L00-S4.html` | `ae7be0bfb72f8236` | **好例**（独立页：2 个 `<style>`、有 md()） |
| `lab-L00-S5.html` | `577d8389f24318b2` | **好例**（独立页：2 个 `<style>`、有 md()） |
| `lab-L00-S6.html` | `611906ea8f84a252` | **好例**（独立页：2 个 `<style>`、有 md()） |
| `lab-L00-S7.html` | `203d5cb128305a71` | **好例**（独立页：2 个 `<style>`、有 md()） |
| `lab-L00-S8.html` | `98305a52fcf2578a` | **好例**（独立页：2 个 `<style>`、有 md()） |

## 修好之后怎么办

坏例**不要删**。修复走"补丁"而不是直接改这个副本：

1. 检查器先红（证明它抓得到）；
2. 修复补丁应用到**源项目**（由那边的人或 agent 应用——本仓库不改别人的项目）；
3. 源项目产物更新后，重跑反证：那时 `frag-*` 的 `expect` 才会从 `fail` 改成 `pass`。

反过来：如果哪天某个 `frag-*` 被判成 `pass` 而它并没有被修，说明**检查器坏了**——
这正是 `runner.py --selftest` 会拦住的情况。

## 刷新夹具

```bash
SRC=/Users/a18760/Desktop/人智与图识学习工作区
for i in 1 2 3 4 5 6 7 8; do
  cp "$SRC/book/_static/labs/frag-L00-S$i.html" .
  cp "$SRC/book/_static/labs/lab-L00-S$i.html"  .
done
cp "$SRC/content/tasks/foundation-index.json" .
shasum -a 256 *.html *.json   # 更新上表
```
