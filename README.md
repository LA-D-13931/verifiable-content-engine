# 线代交互实验台 · 可复核判据引擎

> 本文件**只做导航与入口** ✓（细节都在它指向的文件里 ✓）。

## 唯一入口（两条命令）

```bash
# 1) 套件自检：29 项，绿/红/没验成三态（退出码 0 / 1 / 2 / 3）
cd apps/linalg-lab && python3 tools/verify-all.py --all

# 2) 判据引擎（内容规范域）：列出 产物 × 检查 的判定
cd engine-core/adapters/content-spec && python3 runner.py --discover --scope repo   # 结构类
cd engine-core/adapters/content-spec && python3 runner.py --discover --scope env    # 渲染类
```

## 它是什么

纯逻辑、零 DOM、零第三方依赖的**判据引擎**：每条检查输出 `{pass, reason, certificate}` 三元组，
退出码分**三态**（`0` 通过 / `1` 失败 / `2` 没验成 / `3` 检查器崩溃 ✓）。

## 往哪看

| 想知道 | 看 |
|---|---|
| 引擎核心与适配层（检查清单、契约 C1/C2） | [`engine-core/README.md`](engine-core/README.md) |
| 29 项自检各自在验什么 | [`能力清单.md`](能力清单.md) |
| 还没做的、以及为什么不做 | [`未做与计划.md`](未做与计划.md) |
| 已知失败模式台账（P 项 / M 项） | [`engine-core/adapters/content-spec/失败模式台账.md`](engine-core/adapters/content-spec/失败模式台账.md) |
| 覆盖了哪些痛点、漏检率是多少 | [`../理奥杯/漏检率.py`](../理奥杯/漏检率.py) |
