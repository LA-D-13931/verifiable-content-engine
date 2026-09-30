# apps/linalg-lab · 参考实现

**这不是引擎。** 这是引擎的一个**消费者**——用来说明「引擎接上一个真实内容库之后长什么样」。

引擎本体在 [`engine-core/`](../../engine-core/)，它不碰 DOM、不读全局，可以被单独拿走。
本目录里的画布、交互、界面与存档**都不属于引擎**。

---

## 一、这里有什么

| 部分 | 规模 | 说明 |
|---|---|---|
| 内容 `assets/js/labs.json` | 6135 行 | **纯 JSON，不含可执行代码**——这是内容的唯一编辑面 |
| 应用层 `assets/js/*.js` | 约 2200 行 | 画布渲染（2D/3D）、鼠标交互、界面、进度存档 |
| 关卡 | 12 章 / 58 个实验 / 168 个学习任务 | |
| 工具 `tools/` | — | 校验与生成工具，见下 |

**内容与代码是分开的**：`labs.json` 用声明式格式描述每一关，由
`assets/js/lab-data.js`（生成物）加载，引擎只读 JSON，**不解析 JS 源码**。

---

## 二、跑起来

```bash
# 方式 1：双击 index.html
#   file:// 下也能跑，因为脚本是同步 <script> 而非 ES 模块

# 方式 2：本地服务（推荐，行为与托管一致）
cd <仓库根>
python3 -m http.server 8791 --bind 127.0.0.1
# 打开 http://127.0.0.1:8791/apps/linalg-lab/index.html
```

**注意路径**：`index.html` 用 `../../engine-core/*.js` 引用引擎，
所以它必须待在仓库的这个位置，**不能单独拷出来**。

---

## 三、校验工具

全部**零第三方依赖**、纯离线（浏览器类三项除外，见下）：

```bash
node tools/verify-engine.mjs               # 引擎能否跑完全部任务
node tools/verify-registry.mjs             # 判题注册表离线回归
node tools/verify-calculus.mjs             # 第二个科目复用同一套接口
node tools/verify-diagnostics.mjs          # 判不过必须给原因与证书
node tools/verify-diagnosis-accuracy.mjs   # 诊断说的失败条件必须是对的
node tools/verify-plugin-api.mjs           # 插件与引擎 API 的一致性
node tools/audit-coverage.mjs              # 判题信息量审计
node tools/verify-labs.mjs                 # lab-data.js 可由 labs.json 无损重建
python3 tools/check-lab.py                 # 内容规范、缓存指纹
```

**内容改动后的标准动作**：

```bash
python3 tools/gen-labs-js.py      # labs.json → lab-data.js
python3 tools/加缓存版本.py         # 刷新 ?v= 指纹
python3 tools/check-lab.py        # 确认通过
```

**浏览器类工具**（需要 `node_modules`，即 puppeteer）：

```bash
node tools/verify-actions.js      # 真实鼠标拖动与判题抽查
node tools/smoke.js               # 冒烟：控制台无错误
node tools/verify-themes.js       # 8 组主题对比度
```

---

## 四、不要做的事

| 别做 | 原因 |
|---|---|
| 手改 `assets/js/lab-data.js` | 它是 `labs.json` 的生成物；改内容请改 `labs.json` |
| 手改 `engine-core/mat.js` | 它由 `engine-core/mat.py` 生成 |
| 把 `index.html` 单独拷出去 | 它依赖 `../../engine-core/` |
| 把这个目录当成引擎 | 引擎是 `engine-core/`，本目录只是它的一个使用者 |

---

## 五、历史

早期原型（11 个实验 / 8 章）的文档保留在
[`旧版README_原型v0.1.md`](旧版README_原型v0.1.md)，
其中的规模描述与目录结构**均已过期**，仅作历史记录。
