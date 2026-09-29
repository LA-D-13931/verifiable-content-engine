# 引擎 API：如何新增一个科目

> 本文是引擎可扩展性的说明，也是它的验收标准——
> **如果照本文加不出一个新科目，说明引擎的接口设计有问题。**
>
> 本文档写于 2026-09-29，描述的是当时的接口。接口变了要同步改这里。

---

## 一、引擎的两层结构

```
            ┌─────────────────────────────────────────┐
判题分派 →  │ ① 引擎层  assets/js/registry.js          │  7 个领域无关类型
            │           （数值命中 / 矩阵相等 / 点积 /  │
            │            选择题 / 动作序列）            │
            └─────────────────────────────────────────┘
                              ↓ 未命中
            ┌─────────────────────────────────────────┐
            │ ② 领域插件  domains/<科目>/judge.js       │  学科专属判据
            └─────────────────────────────────────────┘
```

**判断一个判题类型该放哪一层**：

| 判据里出现…… | 放哪层 |
|---|---|
| 「秩、行列式、特征值、列空间」等**学科概念** | 领域插件 |
| 只是「数值相等 / 位置命中 / 序列匹配」 | 引擎层 |

---

## 二、领域插件需要实现什么

**一个文件，一个函数。** 插件导出：

```js
{ judge: function (check, ctx) { ... } }
```

- 参数 `check` —— 关卡数据里那条任务的 `check` 对象（JSON）
- 参数 `ctx` —— 判题上下文（见下）
- 返回 `true` 或 `false` —— 判定结果
- 返回 `null` —— **表示「这不是我的类型」**，交由调用方处理

**返回 `null` 而不是 `false` 很关键**：调用方要能区分「判定为假」与「不是我的类型」。

### ctx 里有什么

| 字段 | 含义 |
|---|---|
| `matrix` / `matrixSize` | 当前矩阵与其阶数 |
| `vectors` | 可拖动向量数组，每项 `{id, data}` |
| `lines` | 行图像的直线，每项 `{a, b, c}` 表示 `a·x + b·y = c` |
| `actionLog` | 已发生的动作名**数组**（顺序有意义） |
| `choices` | 选择题作答，`{taskId: 选项下标}` |
| `taskId` | 当前任务 id（区分同一关里的多道选择题） |
| `Mat` | 矩阵原语（见 `engine/mat.py`，与浏览器侧同源） |
| `vecEq(a, b, tol)` | 向量近似相等 |

**插件不得依赖任何全局**——所有依赖从 `ctx` 取。这样它能在 Node 里独立加载与测试。

---

## 三、加一个科目：完整步骤

以「高等数学」为例，三步。

### 步骤 1 · 建目录与插件骨架

```
domains/calculus/
└─ judge.js
```

```js
(function (root) {
root.CalculusJudge = (function () {
    'use strict';

    function judge(check, ctx) {
        const Mat = ctx.Mat;                 // 依赖一律从 ctx 取
        switch (check.type) {
            case 'limit-at':
                /* 判据写在这里 */
                return true;
            default:
                return null;                 // 不是我的类型
        }
    }

    const api = { judge: judge };
    if (typeof module === 'object' && module.exports) module.exports = api;
    return api;
})();
}(typeof globalThis !== 'undefined' ? globalThis : this));
```

### 步骤 2 · 在 index.html 里加载（放在 engine.js 之前）

```html
<script src="domains/calculus/judge.js"></script>
<script src="assets/js/engine.js?v=xxxxxxxx"></script>
```

然后跑 `python3 tools/加缓存版本.py` 更新资源指纹。
（指纹工具会**从 index.html 自动发现资源**，新目录无需改工具。）

### 步骤 3 · 在 engine.js 的分派链里接上

`checkTask` 目前是：

```js
if (window.CheckRegistry) { ... }        // ① 引擎层
if (window.LinalgJudge)   { ... }        // ② 线代
return false;
```

在 ② 之后、`return false` 之前插入：

```js
if (window.CalculusJudge) {
    const r = window.CalculusJudge.judge(check, ctx);
    if (r !== null) return !!r;
}
```

**就这些。** 引擎层、矩阵原语、判题上下文、证书规范都不需要改。

---

## 四、写完必须做的三件事

### 1. 离线回归测试

新建 `tools/verify-calculus.mjs`，照 `tools/verify-registry.mjs` 的结构写：
每个判题类型至少覆盖「通过与不通过」，并对**历史上出错的地方**写回归用例。

### 2. 引擎独立运行校验

`tools/verify-engine.mjs` 里加上新插件的加载，然后跑一遍——
**必须做到「无人接管 0 个、抛异常 0 个」**。

### 3. 逐步自检

把新测试加进 `tools/build-log.py` 的 `CHECKS` 列表，跑：

```bash
python3 tools/build-log.py check --label "新增高数科目"
```

任一项不过就**不许提交**。

---

## 五、这套接口的设计取舍（已知的不足）

| 取舍 | 说明 |
|---|---|
| **判题只返回布尔值** | 引擎层的处理器返回 `{pass, reason, certificate}` 三元组，领域插件目前只返回布尔值。**这是不一致的地方**，下一步应把证书机制也推给领域插件 |
| **插件是全局单例** | 一个科目一个全局名（`LinalgJudge` / `CalculusJudge`）。科目多了会拥挤，但好处是简单、无需注册调用 |
| **ctx 字段是固定的** | 新科目若需要新的场景数据（如函数表达式），要同时扩 `ctx` 与关卡数据 schema |
| **分派是硬编码的顺序** | 插件多了要改成注册表式（插件自报能处理的类型），目前 2 个科目还用不上 |

**上面第 1 条是最该先修的**：领域判题拿不到「为什么判不过」的表达能力，
而可解释诊断恰恰是本项目的核心主张之一。

---

## 六、这份说明的验收标准

> **照本文加一个新科目，只需动三处：新建插件文件、在 index.html 加一行、在 checkTask 加四行。**
>
> 如果需要改动引擎层、矩阵原语或判题上下文的结构，说明接口设计有问题，应先修接口。

高等数学科目将按本文实现，作为对这套接口的第一次真实检验。
