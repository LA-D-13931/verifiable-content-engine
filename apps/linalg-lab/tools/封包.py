#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""引擎封包（用户要求 · 第八十一轮确认后）。

## 封什么 ✓
**引擎本体 + 跑它所需的一切** ✓：`engine-core/**`（含 `fixtures/` —— C2 契约要 fail 夹具 ✓，不能省 ✗）、
`apps/linalg-lab/tools/**`（验证入口 ✓）、`README.md` / `能力清单.md` / `未做与计划.md` / `AGENTS.md` ✓。
**不封** ✗：`.git` / `node_modules` / `dist` / `__pycache__` / `.certificates` / 任何缓存 ✓。

## 产物 ✓
`dist/引擎-<版本>.tar.gz` ✓，内含 `VERSION.md`（版本 + 事实源四数 + **怎么验** ✓）与 `MANIFEST.sha256` ✓。

## 自证（关键 ✓ —— 不是"打完了"，是"**解包后还能跑**"✓）
解包到一个临时目录 ⇒ 从**解出来的那份**跑 `runner.py --selftest --scope repo|env` ✓ 与 `verify-all.py --all` ✓
⇒ **退出码即结论** ✓（0 = 通过 ✓；非 0 = 封包不合格 ✗，不许只报"已打包" ✗）。
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
WS = os.path.dirname(os.path.dirname(os.path.dirname(REPO)))
DIST = os.path.join(REPO, 'dist')
SKIP_DIRS = {'.git', 'node_modules', 'dist', '__pycache__', '.certificates', '.pytest_cache', '.DS_Store'}
# ⚠️ 第一版**漏了站点资源** ✗ ⇒ 解包里 `check-lab.py` 读不到 `assets/js/lab-data.js` ⇒ **崩**（exit 3 ✗）
# ⇒ 现在把工具真正**读到的输入**也封进来 ✓（`assets/` 与 `index.html` ✓；仍排除 node_modules ✓）。
INCLUDE = ['engine-core', 'apps/linalg-lab/tools', 'apps/linalg-lab/assets', 'apps/linalg-lab/index.html',
           'README.md', '能力清单.md', '未做与计划.md', '交付说明.md', 'AGENTS.md', '.githooks']


def walk_files():
    out = []
    for rel in INCLUDE:
        p = os.path.join(REPO, rel)
        if os.path.isfile(p):
            out.append((rel, p))
        elif os.path.isdir(p):
            for root, dirs, files in os.walk(p):
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
                for f in files:
                    if f in SKIP_DIRS or f.endswith('.pyc'):
                        continue
                    fp = os.path.join(root, f)
                    out.append((os.path.relpath(fp, REPO), fp))
    return sorted(out)


def main():
    stamp = time.strftime('%Y%m%d')
    try:
        rev = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], cwd=REPO, capture_output=True, text=True).stdout.strip() or 'nogit'
    except Exception:
        rev = 'nogit'
    ver = 'v0.81.%s+%s' % (stamp, rev)
    files = walk_files()
    if not files:
        print('✗ 一个文件都没选到 ⇒ **没验成** ✓'); return 2
    os.makedirs(DIST, exist_ok=True)
    stage = tempfile.mkdtemp(prefix='引擎封包-')
    root = os.path.join(stage, '引擎-%s' % ver)
    for rel, src in files:
        dst = os.path.join(root, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
    stats = subprocess.run([sys.executable, os.path.join(HERE, 'verify-all.py'), '--stats'],
                           cwd=HERE, capture_output=True, text=True)
    nums = (stats.stdout or '').strip().splitlines()[-1] if stats.returncode == 0 else '{}'
    open(os.path.join(root, 'VERSION.md'), 'w', encoding='utf-8').write(
        '# 引擎封包 %s\n\n'
        '- 引擎 revision：`%s`\n- 打包时间：%s\n- 事实源四数：`%s`\n\n'
        '## 第 0 步：先跑就绪自检（**缺什么、补哪里**，一条命令说清 ✓）\n\n'
        '```bash\ncd apps/linalg-lab && python3 tools/就绪自检.py\n```\n\n'
        '依赖说明（包里**故意不带** node_modules ✗）：\n'
        '- Python ≥ 3.9（引擎本体**只用标准库** ✓）\n'
        '- Node 18+ 与 `npm install puppeteer-core`（仅**浏览器类工具**需要 ✓）\n'
        '- 浏览器 Edge / Chrome / Chromium 任一（渲染量测需要 ✓）\n'
        '- `01_活工程/线代_两站对照/snapshot/`：**被验对象**，不在包里 ✗，要一起带 ✓\n\n'
        '## 解包后怎么验（**两条命令，退出码即结论** ✓）\n\n'
        '```bash\ncd apps/linalg-lab && python3 tools/verify-all.py --all\n'
        'cd engine-core/adapters/content-spec && python3 runner.py --selftest --scope repo\n'
        'cd engine-core/adapters/content-spec && python3 runner.py --selftest --scope env\n```\n\n'
        '退出码 ✓：`0` 通过 ｜ `1` 失败 ｜ `2` **没验成**（环境不足，不是通过 ✗）｜ `3` 检查器崩溃 ✓\n'
        % (ver, rev, time.strftime('%Y-%m-%d %H:%M:%S'), nums))
    man = []
    for rel, _ in files:
        fp = os.path.join(root, rel)
        man.append('%s  %s' % (hashlib.sha256(open(fp, 'rb').read()).hexdigest(), rel))
    open(os.path.join(root, 'MANIFEST.sha256'), 'w', encoding='utf-8').write('\n'.join(man) + '\n')
    tarball = os.path.join(DIST, '引擎-%s.tar.gz' % ver)
    with tarfile.open(tarball, 'w:gz') as tf:
        tf.add(root, arcname='引擎-%s' % ver)
    print('  已打包：%s（%d 个文件 ✓）' % (os.path.relpath(tarball, WS), len(files) + 2))

    # ── 自证：**从解出来的那份**跑 ✓ ──
    print('  ── 自证（解包后跑 ✓，退出码即结论）──')
    ex = tempfile.mkdtemp(prefix='引擎解包-')
    with tarfile.open(tarball) as tf:
        tf.extractall(ex)
    top = os.path.join(ex, '引擎-%s' % ver)
    rcs = {}
    r = subprocess.run([sys.executable, 'tools/verify-all.py', '--all'],
                       cwd=os.path.join(top, 'apps', 'linalg-lab'), capture_output=True, text=True)
    rcs['verify-all --all'] = r.returncode
    print('    verify-all --all ⇒ %d' % r.returncode)
    for sc in ('repo', 'env'):
        r = subprocess.run([sys.executable, 'runner.py', '--selftest', '--scope', sc],
                           cwd=os.path.join(top, 'engine-core', 'adapters', 'content-spec'),
                           capture_output=True, text=True)
        rcs['selftest %s' % sc] = r.returncode
        print('    selftest --scope %s ⇒ %d' % (sc, r.returncode))
    # **自证判据（第一版判错了 ✗，据实测改正 ✓）**：
    # 解包后的目标机**没有** `node_modules`（puppeteer-core ✓ 装不进包 ✗）、也没有仓库外的渲染目标 ✓
    # ⇒ 渲染类会**正当地**报 `2`（环境不足 ✓，三态里"没验成" ✓ —— **不是失败** ✗）。
    # 所以判据是：**`repo` 档必须 0** ✓；其余**只许 0 或 2** ✓（出现 **1（失败）或 3（检查器崩溃）⇒ 封包不合格** ✗）。
    # ⚠️ 并且**逐条印出**每条是什么码 ✓ —— 不许把"2"混进"通过"里 ✗。
    ok = True
    for k, v in rcs.items():
        if k == 'selftest repo' and v != 0:
            ok = False
        elif v not in (0, 2):
            ok = False
    if not ok:
        print('  ✗ **封包不合格**（%s）—— `repo` 档须 0；其余只许 0 或 2；**1/3 一律不合格** ✗' % rcs)
        return 1
    print('  ✓ 封包自证通过：repo 档 0 ✓；其余 %s 全在 {0,2} 内 ✓（2 = 目标机缺 node_modules/仓库外渲染目标 ⇒ **没验成** ✓ 不是通过 ✗）'
          % {k: v for k, v in rcs.items() if v == 2})
    return 0


if __name__ == '__main__':
    sys.exit(main())
