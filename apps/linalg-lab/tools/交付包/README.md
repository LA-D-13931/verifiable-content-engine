# 可验证的交互式教学内容引擎

**在内容发布之前，自动判定学习任务是否做得出来、判题规则是否判得对。**

零第三方依赖 · 零构建 · 双击即可运行。

---

## 一、这个引擎解决什么问题

交互式教学课件有一类缺陷，**危险性恰在于「看起来一切正常」**：

> 页面的显示、操作反馈、提示文本全部正常，但其中某个学习任务
> **在任何操作下都不可能完成**。

作者（无论是人还是语言模型）通常发现不了它，因为确认这类缺陷需要遍历
「用户能到达的全部状态」——而用户可以把对象拖到平面上的**任意实数位置**，
状态是连续且无穷的。

引擎把这件不可能人工完成的事情，变成一条命令：

```bash
node apps/linalg-lab/tools/verify-engine.mjs
# 全部通过 ✓ 引擎可在无浏览器环境下加载并跑完全部任务
```

---

## 二、30 秒上手

### 2.1 浏览器里用（推荐）

```html
<!-- 引擎必须在调用方之前加载，顺序不能换 -->
<script src="engine-core/mat.js"></script>
<script src="engine-core/registry.js"></script>
<script src="engine-core/domains/linalg/judge.js"></script>

<script>
  // 判题上下文：引擎从这里读取全部状态
  const ctx = {
    taskId: 'demo',
    matrix: [[1, 1], [1, 1]],      // 场景里的矩阵
    matrixSize: 2,
    vectors: [{ id: 'v', data: [1, 0] }],
    lines: [],
    actionLog: [],                  // 用户做过的动作
    choices: {},                    // 选择题的作答
    param: null,                    // 滑杆/拖拽的连续参数
    Mat: window.Mat,                // 矩阵原语
    vecEq: (a, b) => a.every((x, i) => Math.abs(x - b[i]) <= 0.15)
  };

  // 作者声明的判题条件
  const check = { type: 'rank', op: 'eq', value: 2 };

  // 先问引擎层，未命中再问领域插件
  let r = window.CheckRegistry.run(check, ctx);
  if (r === null) r = window.LinalgJudge.judge(check, ctx);

  console.log(r);
  // {
  //   pass: false,
  //   reason: '当前秩 = 1，要求 eq 2',
  //   certificate: { rank: 1, op: 'eq', target: 2 }
  // }
</script>
```

### 2.2 Node 里用

```js
const Mat      = require('./engine-core/mat.js');
const Registry = require('./engine-core/registry.js');
const Linalg   = require('./engine-core/domains/linalg/judge.js');

const ctx = { taskId: 'demo', matrix: [[1,1],[1,1]], matrixSize: 2,
              vectors: [], lines: [], actionLog: [], choices: {}, param: null,
              Mat, vecEq: () => true };

console.log(Linalg.judge({ type: 'rank', op: 'eq', value: 2 }, ctx));
```

**引擎不依赖浏览器**——`window` / `document` 全部置空后依然可用，
所以它能在 Node 里独立跑完整个内容库（这正是自动化校验的前提）。

---

## 三、核心约定：每个判题返回三元组

| 字段 | 含义 |
|---|---|
| `pass` | 是否通过 |
| `reason` | 不通过时的一句话原因（**给人看**，不是给机器看） |
| `certificate` | 判定依据（见证或反证），**可被自动复核** |

**为什么必须有 `certificate`**：只给一个布尔值，作者拿到也没法修。
证书让「诊断质量」变成可核对的东西——例如判定为「可达」时给出见证参数，
把参数代回去必须真的能通过。

实测输出示例：

```
det      → 当前 det = 4，要求 eq 0（容差 0.08）        { determinant: 4, … }
rank     → 当前秩 = 1，要求 eq 2                       { rank: 1, … }
eigen    → 当前缩放倍数 λ = 1，目标是 5（容差 0.12）     { lambda: 1, av: [1,1] }
null-space → 方向不符：v 与目标方向的 |cos| = 0.707，
             要求 ≥ 0.98（零空间条件 |Av| = 0 已满足，
             所以问题确实出在方向上）
```

**注意最后一条**：这个类型有 4 条失败条件，诊断会逐条对应、并**镜像判定的
条件顺序**。否则会出现「诊断说方向不对、实际判定卡在 |Av|」——
看似有原因、实则误导，比没有原因更糟。

---

## 四、两级分派：一条可检验的分界线

```
          判题条件 check
                │
    ┌───────────▼────────────┐
    │ engine-core/registry.js │  7 个领域无关类型
    │ 数值命中/矩阵相等/点积/  │  169 行
    │ 选择题/动作序列         │
    └───────────┬────────────┘
                │ 未命中
    ┌───────────▼────────────────────┐
    │ engine-core/domains/<科目>/     │  学科专属判据
    │ linalg 13 类 · calculus 4 类    │  642 行
    └────────────────────────────────┘
```

**分界线**：

| 判据里出现…… | 放在哪一层 |
|---|---|
| 「秩、行列式、特征值、列空间」等**学科概念** | `domains/<科目>/` |
| 只是「数值相等 / 位置命中 / 序列匹配」 | `registry.js` |

**这条界线是可检验的**：新增一个科目，`registry.js` 与 `mat.js`
**不需要改一个字符**。高等数学科目就是这样接入的——只动了三处
（新建插件文件、`index.html` 加一行、调用方分派链加四行）。
详见 `engine-core/API_如何新增科目.md`。

---

## 五、目录结构

```
engine-core/                      引擎库（可被单独拿走的那一层）
├─ README.md                      引擎自身的说明（API 与已知边界）
├─ registry.js                    引擎层判题注册表
├─ mat.js / mat.py                矩阵原语（JS 版由 Python 版生成，两侧同源）
├─ mat-vectors.json               77 组共享测试向量，两侧各自自检
├─ API_如何新增科目.md              加一个新科目的完整步骤
├─ domains/linalg/judge.js        线性代数领域插件（13 个判题类型）
├─ domains/calculus/judge.js      高等数学领域插件（4 个判题类型）
└─ adapters/static-content/       第二个领域：静态内容一致性校验

apps/linalg-lab/                  参考实现（引擎的一个消费者，不是引擎）
├─ index.html                     58 个交互实验 / 168 个学习任务
├─ assets/js/                     应用层：画布、交互、界面、存档（约 2200 行）
├─ assets/js/labs.json            关卡内容（纯 JSON，唯一编辑面）
└─ tools/                         校验与构建工具
```

**「引擎」与「参考实现」必须分得清**：`engine-core/` 是纯逻辑
（不碰 DOM、不读全局），可被别人直接拿走；`apps/` 里的界面与渲染**不属于引擎**。

---

## 六、自己跑一遍校验

```bash
# 引擎能跑完全部任务吗（不需要浏览器）
node apps/linalg-lab/tools/verify-engine.mjs

# 判题注册表的离线回归（含真实缺陷回归用例）
node apps/linalg-lab/tools/verify-registry.mjs

# 第二个科目复用同一套接口
node apps/linalg-lab/tools/verify-calculus.mjs

# 每个类型判不过时都必须给出原因与证书
node apps/linalg-lab/tools/verify-diagnostics.mjs

# 诊断准确性：诊断说的失败条件必须就是真正拦截判定的那一条
node apps/linalg-lab/tools/verify-diagnosis-accuracy.mjs

# 领域插件与引擎 API 的一致性（不依赖全局、边界干净、缺字段不崩）
node apps/linalg-lab/tools/verify-plugin-api.mjs

# 判题信息量审计（逐类型两条路径）
node apps/linalg-lab/tools/audit-coverage.mjs
```

以上**全部不需要第三方依赖**（纯离线）。

### 静态内容校验（第二个领域）

```bash
# 对一个站点目录跑内容一致性校验
python3 engine-core/adapters/static-content/verify.py <站点目录>

# 若页面会引用本站目录之外的文件（引擎仓库的参考实现就是这样）
python3 engine-core/adapters/static-content/verify.py apps/linalg-lab --allow-outside

# 机器可读
python3 engine-core/adapters/static-content/verify.py <站点目录> --json
```

输出形如：

```
✓ 标签配平            （25 页，标签全部配平）
✓ 站内链接可达          （719 条站内链接全部可达）
✓ 页内锚点存在          （4 条页内锚点全部存在）
✓ 内容卫生            （0 页无 Markdown 星号、无 SVG 内数学）
– 结构 / 例题 / 双语统计  宿主站点未提供 tests/check-structure.py，本项跳过
```

`–` 表示**跳过**（宿主站点没提供那项检查所需的脚本），**不算失败**。

---

## 七、加一个新的科目

完整步骤见 `engine-core/API_如何新增科目.md`，摘要：

1. 新建 `engine-core/domains/<科目>/judge.js`，导出一个 `judge(check, ctx)`
2. 在 `index.html` 里加一行 `<script>`
3. 在调用方的分派链里加四行

**`registry.js` 与 `mat.js` 不需要改动**——这是分界线的可检验后果。

---

## 八、已知边界（请先读这一节）

| 不含 / 不做 | 说明 |
|---|---|
| **渲染层** | 这一版引擎**只判题、不画图**。界面需要你自己实现。 |
| 具体课程内容 | `apps/linalg-lab` 里的 58 个实验只是示例内容。 |
| 服务端组件 | 引擎是纯前端、纯离线的，不上传任何数据。 |
| 依赖与构建 | 零依赖是**刻意的设计**，不是省事。 |
| 教学有效性判定 | 保证「任务可完成、判题自洽」，**不保证**「教学有效」。 |
| 形式化证明 | 这是工程判定策略，不提供定理级证明。 |

**两条特别注意**：

1. **不要手改 `engine-core/mat.js`**——它由 `mat.py` 生成。
   要改数学就改 `mat.py`，再跑 `apps/linalg-lab/tools/gen-mat-js.py`。
2. **不要改成 ES module**。现在用普通 `<script>` 同步加载，`file://` 下
   双击就能跑；改成 `import`/`export` 会被浏览器的 CORS 拦住，
   使用者就必须起一个服务器——那会丢掉这个包最实在的优点。

---

## 九、把它接进自己的项目

最小接入清单：

```
你需要的：engine-core/          （整个目录）
你需要写的：
  · 内容 JSON（参考 apps/linalg-lab/assets/js/labs.json 的格式）
  · 一个渲染与交互层（引擎不管这个）
  · 若内容库有新的判题类型，写一个 domains/<科目>/judge.js
```

`apps/linalg-lab/` 整个目录可以当作**参考实现**阅读，
但它不是引擎的一部分，可以直接删掉。
