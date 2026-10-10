# 站点级检查的夹具：一页真实页面 + 两个声明式突变体

| 文件 | sha256 | 角色 | 大小 |
|---|---|---|---|
| `ch1.html` | `2c6e829bfd67aa34` | **真实页面**（高数站 ch1，逐字复制；作为突变体的对照） | 599 KB |
| `ch1.lang-mutant.html` | `8017f1e38c36911d` | **突变体 A**：从一个 `.bi` 容器里删掉最后一个英文段 → 中英段数不再相等 | 598 KB |
| `ch1.nav-mutant.html` | `9238a1bc630a429f` | **突变体 B**：在 `header-nav` 上插入一个属性 → 模拟"这页导航被单独改过" | 599 KB |

## 为什么要突变体

站点级检查（`lang-policy` / `single-source`）的输入是**一组页面**。真实站点当前状态基本是好的，
所以"检查能不能抓"必须靠**声明式突变**来反证——突变由脚本按规则生成（删一个英文段 / 改一处导航），
可重新生成、可复查，**不是**手改出来的。

两个突变体各只破坏**一条**不变量，因此还有一个作用：证明两条检查**互不串味**——
语言突变体的 `single-source` 仍然是 pass，导航突变体的 `lang-policy` 仍然是 pass。

## 同一个快照里有两个站（踩过的坑）

`01_活工程/线代_两站对照/snapshot/chapters/` 里其实混着：

- `ch*.html` **12 个——高数站**（`header-nav` 指向 `../index.html`）
- `la*.html` **6 个——线代站**（`header-nav` 指向 `../linear-algebra.html`）
- `supp1.html` 1 个补充页

所以页面集必须写成 `chapters/ch[0-9]*.html`；写成 `chapters/*.html` 会把两个站混在一起，
**"逐字节一致"这条判据会永久假红**（两个站的导航 href 本来就不同）。

## 首跑抓到的真实缺陷

`snapshot · single-source = fail`：高数站 12 页的 `site-footer` 有 **2 个版本**——
`ch1.html` 写「中英**对照**」，其余 11 页写「中英**逐行对照**」。这是真实缺陷（已登记进
`manifest.discovered_defects` 的 `footer-wording-drift`），不是突变体造出来的。
