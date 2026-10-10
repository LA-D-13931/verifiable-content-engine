# 夹具：真实坏例 + 突变体（只读副本）

| 文件 | sha256 | 角色 |
|---|---|---|
| `build-lab-fragments.py` | `f36fdcfbafdf9969` | **渲染器源码**（缺陷源头：两条渲染路径、样式与枚举的声明处） |
| `foundation-index.json` | `8ff1fdb8d4ca12a5` | 数据源（教材关卡唯一来源，24 题） |
| `foundation-index.mutant.json` | `d452b386b0ac7ea2` | **突变体**（把一道题的 correct 位移一位——声明式构造，用来反证答案键检查） |
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

**为什么是 8 对**：同一个脚本 `build-lab-fragments.py` 写出两条渲染路径——
`:755-759` 写片段（原样塞 `q.text`，无 `md()`），`:765-772` 写独立页（`:767` 把 `FRAGMENT_CSS` 只注入这一条）。
所以 8 个课时**全部**都坏，而不是偶发。

**突变体**是这类"现状全好"的检查唯一能自证的方式：真实数据 24 题答案键全一致，
不构造一个错例，就无法证明这条检查真的在看。突变由脚本按声明式规则生成（位移一位），
**不是**手改出来的——所以它可以被重新生成、也可以被复查。

## 刷新夹具

```bash
SRC=/Users/a18760/Desktop/人智与图识学习工作区
for i in 1 2 3 4 5 6 7 8; do
  cp "$SRC/book/_static/labs/frag-L00-S$i.html" .
  cp "$SRC/book/_static/labs/lab-L00-S$i.html"  .
done
cp "$SRC/content/tasks/foundation-index.json" .
cp "$SRC/scripts/build-lab-fragments.py" .
shasum -a 256 * 2>/dev/null   # 更新上表
```
