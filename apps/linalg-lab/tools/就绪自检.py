#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""就绪自检（交付配套 · 新人第一条命令）。

## 它回答什么 ✓
新人解包后第一句通常问："我这儿能不能跑？缺什么？" ✓ —— 本脚本**逐项体检**并**给出补齐命令** ✓，
**不猜、不假装**：缺什么就报什么 ✓，并明确「**缺它 ⇒ 相关判据只会退 2（没验成），不是绿也不是坏**」✓。

## 三态 ✓
全齐 ⇒ **0** ✓ ｜ 有缺项 ⇒ **2**（**没验成** ✓ —— 与套件的约定一致 ✓）｜ 脚本自身跑不了 ⇒ 非 0 ✓
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))          # …/apps/linalg-lab/tools
LAB = os.path.dirname(HERE)                                 # …/apps/linalg-lab
APPS = os.path.dirname(LAB)                                 # …/apps
REPO = os.path.dirname(APPS)                                # …/线代交互实验台
WORKTAB = os.path.dirname(REPO)                             # …/工作台
WS = os.path.dirname(WORKTAB)                               # 工作区根 ✓
# ⚠️ 第一版我把层级数错了 ✗ ⇒ 把"本机其实有"的 snapshot / 理奥杯 报成缺 ✓
# ⇒ 连带把套件从 0 弄成 2 ✗ ⇒ 现按**实测的真实位置**算 ✓（见每条的注释 ✓）。

项 = []


def add(ok, name, need, fix):
    项.append((bool(ok), name, need, fix))


# ① Python（引擎只依赖标准库 ✓）
py = sys.version_info
add(py >= (3, 9), 'Python ≥ 3.9', '当前 %d.%d.%d' % (py.major, py.minor, py.micro), '装新版 Python 3 即可（引擎本体只用标准库 ✓）')

# ② Node（渲染类探针与两侧矩阵复算用 ✓）
node = shutil.which('node')
add(node, 'Node.js（渲染探针 / 矩阵复算）', node or '未找到 node', '装 Node 18+ 即可（apt/brew/官网安装包）')

# ③ puppeteer-core（浏览器类工具需要 ✓ —— 包内**故意不带 node_modules** ✗）
nm = os.path.join(LAB, 'node_modules', 'puppeteer-core')
# 与 browser.mjs 同口径 ✓：能 require.resolve 到就算在 ✓（装法可能不是本地 node_modules ✓）
resolved = None
try:
    r = subprocess.run(['node', '-e', "try{console.log(require.resolve('puppeteer-core'))}catch(e){process.exit(3)}"],
                       cwd=LAB, capture_output=True, text=True, timeout=30)
    if r.returncode == 0:
        resolved = (r.stdout or '').strip()
except Exception:
    pass
add(resolved or os.path.isdir(nm), 'puppeteer-core（浏览器类工具）',
    resolved or (nm if os.path.isdir(nm) else '未安装'),
    'cd apps/linalg-lab && npm install puppeteer-core（或全局装好后让 node 能解析到 ✓）')

# ④ 浏览器（Edge / Chrome / Chromium 任一 ✓）
cands = ['/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
         '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
         '/Applications/Chromium.app/Contents/MacOS/Chromium',
         shutil.which('google-chrome') or '', shutil.which('chromium') or '']
browser = next((c for c in cands if c and os.path.exists(c)), None)
add(browser, '浏览器（渲染量测：对比度/间距/锚点/高亮/溢出/点击目标）', browser or '未找到 Edge/Chrome/Chromium',
    '装 Edge 或 Chrome；找不到时用 ARCHIFY_CHROME / 环境变量指向可执行文件')

# ⑤ 仓库外目标（高数站快照 ✓ —— **不在包里** ✗，只报告不代造 ✓）
snap = os.path.join(WS, '01_活工程', '线代_两站对照', 'snapshot')       # **实测就是这个位置** ✓
snap2 = os.path.join(REPO, '01_活工程', '线代_两站对照', 'snapshot')     # 备用：包内同层 ✓
found = next((p for p in (snap, snap2) if os.path.isdir(p)), None)
add(found, '仓库外目标：01_活工程/线代_两站对照/snapshot（章节页 12 个）', found or '不在包内、也不在本机该位置',
    '把 snapshot/ 放到工作区下的 01_活工程/线代_两站对照/ —— 它是**被验对象**，不属于引擎 ✗')

# ⑥ 材料线（闸门读 docx ✓ —— 只有做材料交付才需要 ✓）
_gate = os.path.join(WS, '理奥杯', '交付物自检.py')
add(os.path.isfile(_gate),
    '材料线：理奥杯/交付物自检.py（36 项闸门）', _gate if os.path.isfile(_gate) else '同工作区下没有 理奥杯/',
    '把 理奥杯/ 一起放到同一工作区（**只做引擎判据时不需要它** ✓）')

print('=== 就绪自检（新人第一条命令）===')
print('  包：%s' % REPO)
ok_n = sum(1 for o, *_ in 项 if o)
for ok, name, state, fix in 项:
    print('  %s %-52s %s' % ('✓' if ok else '✗', name, state))
    if not ok:
        print('      补齐：%s' % fix)
print()
print('  共 %d 项，齐 %d 项' % (len(项), ok_n))
if ok_n == len(项):
    print('  ✓ 全齐 ⇒ 可以直接跑：cd apps/linalg-lab && python3 tools/verify-all.py --all')
    sys.exit(0)
print('  ⚠️ 有缺项 ⇒ **别把退 2 当绿、也别当坏** ✗：')
print('     · 缺的项只会让**相关判据**报「环境不足 ⇒ 退 2/3 态里的 2（没验成）」✓')
print('     · **静态判据（结构类）不受影响** ✓ ⇒ 仍可先跑：')
print('       cd engine-core/adapters/content-spec && python3 runner.py --discover --scope repo')
sys.exit(2)
