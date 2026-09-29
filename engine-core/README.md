# engine-core · 可验证的交互式教学内容引擎

**这一层不认识「行列式」「极限」这类学科概念。** 它只做一件事：
把作者声明的判题条件，与用户实际可达的状态空间求交，判定任务是否可达、判题规则是否健全，
并在退化时给出**可解释诊断**。

```
判题上下文 ctx  ──▶  ① registry.js           7 个领域无关类型
                      （数值命中 / 矩阵相等 / 点积 / 选择题 / 动作序列）
                              ↓ 未命中
                     ② domains/<科目>/judge.js  学科专属判据
                              ↓
                     返回 { pass, reason, certificate }
```

---

## 一、目录内容

| 文件 | 行数 | 作用 |
|---|---|---|
| `registry.js` | 169 | 引擎层判题注册表（7 个领域无关类型） |
| `mat.js` | 256 | 矩阵原语（**生成物**，由 `mat.py` 生成） |
| `mat.py` | 304 | 矩阵原语**权威实现**（Python 侧，两侧共用同一套定义） |
| `mat-vectors.json` | 1664 | 77 组共享测试向量，两侧各自自检 |
| `domains/linalg/judge.js` | 409 | 线代领域插件（13 个类型） |
| `domains/calculus/judge.js` | 233 | 高数领域插件（3 个类型） |
| `API_如何新增科目.md` | 176 | **加一个新科目的完整步骤** |

**引擎本体合计 1367 行。全部是纯逻辑**：不碰 DOM、不读全局变量，
所有依赖从传入的 `ctx` 取——因此可以在 Node 里独立加载与测试。

---

## 二、怎么用（两种方式）

### 方式 1 · 浏览器（零构建，推荐）

```html
<!-- 引擎必须在调用方之前加载 -->
<script src="engine-core/mat.js"></script>
<script src="engine-core/registry.js"></script>
<script src="engine-core/domains/linalg/judge.js"></script>

<script>
  // 判题上下文：引擎只读这里面的字段
  const ctx = {
    matrix: [[1, 1], [1, 1]], matrixSize: 2,
    vectors: [{ id: 'v', data: [2, 2] }],
    lines: [], actionLog: [], choices: {}, taskId: 't1', param: null,
    Mat: window.Mat
  };

  // ① 先问引擎层
  let r = window.CheckRegistry.run(
      { type: 'rank', op: 'eq', value: 2 }, ctx);
  // ② 未命中再问领域插件
  if (r === null) r = window.LinalgJudge.judge(
      { type: 'rank', op: 'eq', value: 2 }, ctx);

  console.log(r);
  // { pass: false,
  //   reason: '当前秩 = 1，要求 eq 2',
  //   certificate: { rank: 1, op: 'eq', target: 2 } }
</script>
```

**为什么坚持普通 `<script>` 而不是 ES module**：这样 `file://` 下双击就能跑，
不需要起服务器。改成 `import/export` 会被 CORS 拦下，等于丢掉这个优点。

### 方式 2 · Node（用于自动化校验）

```js
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);

const Mat = require('./engine-core/mat.js');
const Registry = require('./engine-core/registry.js');
require('./engine-core/domains/linalg/judge.js');   // 挂到 globalThis
const Linalg = globalThis.LinalgJudge;

const ctx = { matrix: [[1,1],[1,1]], vectors: [], actionLog: [], choices: {},
              taskId: 't', Mat, vecEq: (a,b,t) => true };
console.log(Linalg.judge({ type: 'rank', op: 'eq', value: 2 }, ctx));
```

---

## 三、判题结果的三元组

每个处理器**必须**返回：

| 字段 | 含义 |
|---|---|
| `pass` | 是否通过 |
| `reason` | 不通过时的一句话原因（**给人看**，不是给机器看） |
| `certificate` | 判定依据（见证或反证），**可被自动复核** |

**为什么要有 `certificate`**：只给一个布尔值，作者拿到也没法修。
证书让「诊断质量」变成可核对的东西——例如「可达」时给出见证参数，
把参数代回去必须真的能通过。

实测输出示例：

```
det      → 当前 det = 4，要求 eq 0（容差 0.08）      { determinant: 4, … }
rank     → 当前秩 = 1，要求 eq 2                     { rank: 1, … }
eigen    → 当前缩放倍数 λ = 1，目标是 5（容差 0.12）   { lambda: 1, av: [1,1] }
on-span  → rank(A) = 1，rank([A|v]) = 2（秩升高说明 v 不在列空间内）
actions  → 还缺少这些动作：try-inverse               { missing: ['try-inverse'] }
```

---

## 四、两级分派的分界线

| 判据里出现…… | 放哪层 |
|---|---|
| 「秩、行列式、特征值、列空间」等**学科概念** | `domains/<科目>/` |
| 只是「数值相等 / 位置命中 / 序列匹配」 | `registry.js` |

**这条界线是可检验的**：新增一个科目，`registry.js` 与 `mat.js` **不需要改一个字符**。
高等数学科目就是这么接入的——只动了三处（新建插件文件、`index.html` 加一行、
调用方分派链加四行）。详见 `API_如何新增科目.md`。

---

## 五、改这个目录时的纪律

| 规则 | 原因 |
|---|---|
| **不要手改 `mat.js`** | 它由 `mat.py` 生成。改数学要改 `mat.py`，然后重跑生成器 |
| **改完 `mat.py` 必须重跑 `gen-mat-vectors.py`** | 测试向量带 AST 指纹；改了数学不重跑会被检查拦下 |
| **新增判题类型必须给出 `reason`** | 有专门的覆盖率检查盯着这件事 |
| **不要引 `App.*` 或任何全局** | 引擎要能在 Node 里独立加载（这是它可测的前提） |

对应的校验命令在参考实现那边（`apps/linalg-lab/tools/`）：
`verify-engine.mjs`（引擎独立运行）、`verify-diagnostics.mjs`（诊断覆盖率）、
`audit-coverage.mjs`（逐类型信息量审计）、`verify-registry.mjs`、`verify-calculus.mjs`。

---

## 六、已知边界（不含什么）

| 不含 | 原因 |
|---|---|
| 具体的课程内容 | 那是使用者的内容，不是引擎能力 |
| **渲染层** | 这一版引擎**只判题，不画图**。使用者要自己实现界面 |
| 任何服务端组件 | 引擎是纯前端、纯离线的，不上传任何数据 |
| 依赖与构建配置 | 零依赖是刻意的设计，不是省事 |

**最重要的一条**：这一版**不含渲染层**。`apps/linalg-lab/` 里的 `render2d.js`
（650 行）等文件属于参考实现，**不在引擎交付范围内**。
若将来要做，应把渲染抽象成可插拔的「场景适配器」。
