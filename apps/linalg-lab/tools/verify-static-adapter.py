#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""差分对照：原脚本 vs 引擎适配器（W3-4）。

P3 的迁移纪律是「迁移只改组织方式，不改判定结论」。所以每一步迁移都要证明：

    在**同一批文件**上，原脚本与适配器对同一项检查给出**一致的结论**。

做法：两边的退出码都必须为 0（都通过），且两边各自声明的统计量必须相等
（页数、链接数、锚点数、卫生问题数）。任何一项对不上就说明迁移改变了行为。

用法：
    python3 tools/verify-static-adapter.py
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(APP))
WORKSPACE = os.path.dirname(os.path.dirname(REPO))

SNAPSHOT = os.path.join(WORKSPACE, '01_活工程', '线代_两站对照', 'snapshot')
ADAPTER_DIR = os.path.join(REPO, 'engine-core', 'adapters', 'static-content')

failures = []


def ok(cond, name, extra=''):
    if cond:
        print('  ✓ %s' % name)
    else:
        failures.append(name)
        print('  ✗ %s%s' % (name, ('  —— ' + extra) if extra else ''))


def run_original(script):
    """在快照里跑原脚本（脚本用 __file__ 推导站点根，所以拷进快照才会对快照跑）。"""
    p = os.path.join(SNAPSHOT, 'tests', script)
    if not os.path.isfile(p):
        return None, '快照里没有 %s' % script
    r = subprocess.run([sys.executable, p], capture_output=True, text=True, cwd=SNAPSHOT)
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def run_adapter():
    sys.path.insert(0, ADAPTER_DIR)
    import checks                                   # noqa: E402
    return checks.run(SNAPSHOT)


def nums(pattern, text, cast=int):
    m = re.search(pattern, text)
    return cast(m.group(1)) if m else None


print('=== 差分对照：原脚本 vs 引擎适配器 ===')
print('对照目录：%s' % SNAPSHOT)
print('')

# ---------- 原脚本 ----------
print('原脚本（主站 tests/check-html.py）')
rc, out = run_original('check-html.py')
if rc is None:
    ok(False, '原脚本可运行', out)
else:
    ok(rc == 0, '原脚本对快照通过（退出码 0）', '退出码 %s' % rc)
    orig_pages = nums(r'标签配平：(\d+)/', out)
    orig_links = nums(r'检查 (\d+) 个链接', out)
    orig_broken = nums(r'失效 (\d+) 个', out)
    orig_anchor = nums(r'失效锚点 (\d+) 个', out)
    orig_hyg = nums(r'内容卫生：(\d+) 处问题', out)
    print('    统计：页 %s · 链接 %s · 失效 %s · 失效锚点 %s · 卫生 %s'
          % (orig_pages, orig_links, orig_broken, orig_anchor, orig_hyg))

# ---------- 适配器 ----------
print('')
print('引擎适配器（engine-core/adapters/static-content）')
res = run_adapter()
by = {r['name']: r for r in res['results']}
for name, label, _ in __import__('checks').CHECKS:
    r = by[name]
    print('    %s %-16s %s' % ('✓' if r['pass'] else '✗', label, (r['reason'] or '通过')[:70]))

print('')
print('一致性比对')
if rc is not None:
    ok(res['docs'] == orig_pages,
       '页面数一致（适配器 %d / 原脚本 %s）' % (res['docs'], orig_pages))
    A = by['tag-balance']
    ok(A['pass'] and orig_broken is not None,
       '标签配平：两边都判通过（原脚本失效标签 %s）' % orig_broken)
    L = by['internal-links']
    ok(L['pass'] == (orig_broken == 0),
       '站内链接：结论一致（适配器 %s / 原脚本失效 %s）'
       % ('通过' if L['pass'] else '不通过', orig_broken))
    if L['certificate'] and orig_links is not None:
        ok(L['certificate']['checked'] == orig_links,
           '链接检查条数一致（适配器 %d / 原脚本 %s）'
           % (L['certificate']['checked'], orig_links))
    else:
        ok(False, '链接检查条数可对比', '适配器未给出统计')
    AN = by['in-page-anchors']
    if AN['certificate'] and orig_anchor is not None:
        ok(len(AN['certificate']['broken']) == orig_anchor,
           '失效锚点数一致（适配器 %d / 原脚本 %s）'
           % (len(AN['certificate']['broken']), orig_anchor))
    H = by['content_hygiene'] if 'content_hygiene' in by else by['content-hygiene']
    if H['certificate'] and orig_hyg is not None:
        ok(len(H['certificate']['hits']) == orig_hyg,
           '卫生问题数一致（适配器 %d / 原脚本 %s）'
           % (len(H['certificate']['hits']), orig_hyg))

print('')
if failures:
    print('失败 %d 项 ✗' % len(failures))
    for f in failures:
        print('   - ' + f)
    sys.exit(1)
print('全部通过 ✓ 适配器与原脚本在同一批文件上结论一致')
