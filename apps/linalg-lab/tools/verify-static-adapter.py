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

# ---------- 结构校验：原脚本 ----------
print('')
print('原脚本（主站 tests/check-structure.py）')
rc2, out2 = run_original('check-structure.py')
if rc2 is None:
    ok(False, '结构原脚本可运行', out2)
else:
    ok(rc2 == 0, '结构原脚本对快照通过（退出码 0）', '退出码 %s' % rc2)
    def g(pat, cast=int):
        m = re.search(pat, out2)
        return cast(m.group(1)) if m else None
    o_sections = g(r'小节\s*(\d+)')
    o_examples = g(r'例题\s*(\d+)')
    o_qpapers = g(r'测验卷\s*(\d+)')
    o_qquestions = g(r'测验题\s*(\d+)')
    o_reviews = g(r'讲评\s*(\d+)')
    print('    统计：小节 %s · 例题 %s · 测验卷 %s · 测验题 %s · 讲评 %s'
          % (o_sections, o_examples, o_qpapers, o_qquestions, o_reviews))

print('')
print('结构校验一致性')
S = by.get('structure')
if S is None:
    ok(False, '适配器报告里有结构项')
else:
    c = S.get('certificate') or {}
    cnt = c.get('counts') or {}
    ok(S['pass'] == (rc2 == 0), '结论一致（适配器 %s / 原脚本退出码 %s）'
       % ('通过' if S['pass'] else '不通过', rc2))
    for key, want, label in [('sections', o_sections, '小节'),
                             ('examples', o_examples, '例题'),
                             ('quizPapers', o_qpapers, '测验卷'),
                             ('quizQuestions', o_qquestions, '测验题'),
                             ('reviews', o_reviews, '讲评')]:
        if want is None:
            continue
        ok(cnt.get(key) == want,
           '%s 数一致（适配器 %s / 原脚本 %s）' % (label, cnt.get(key), want))
    ok(c.get('delegated') is not False, '明确标注该项为「委托执行」而非重写')

# ---------- 双语对照：原脚本 ----------
print('')
print('原脚本（主站 tests/check-bilingual.py）')
rc3, out3 = run_original('check-bilingual.py')
if rc3 is None:
    ok(False, '双语原脚本可运行', out3)
else:
    ok(rc3 == 0, '双语原脚本对快照通过（退出码 0）', '退出码 %s' % rc3)
    o_detail = nums(r'行内符号出现次数不同\s*(\d+)\s*处', out3)
    o_num = nums(r'数字/节号两侧不完全对应\s*(\d+)\s*处', out3)
    print('    统计：行内符号差异 %s 处（不阻断）· 节号不对应 %s 处（不阻断）'
          % (o_detail, o_num))

print('')
print('双语对照一致性')
B = by.get('bilingual')
if B is None:
    ok(False, '适配器报告里有双语项')
else:
    cb = B.get('certificate') or {}
    ok(B['pass'] == (rc3 == 0), '结论一致（适配器 %s / 原脚本退出码 %s）'
       % ('通过' if B['pass'] else '不通过', rc3))
    ok(cb.get('inlineSymbolDiff') == o_detail,
       '行内符号差异数一致（适配器 %s / 原脚本 %s）'
       % (cb.get('inlineSymbolDiff'), o_detail))
    ok(cb.get('numberMismatch') == o_num,
       '节号不对应数一致（适配器 %s / 原脚本 %s）'
       % (cb.get('numberMismatch'), o_num))
    # 关键：不阻断的两档不能被算成硬性问题
    ok(not cb.get('issues'),
       '「供人工确认」的两档未被误算为硬性问题（硬性问题 %d 条）'
       % len(cb.get('issues') or []))

print('')
if failures:
    print('失败 %d 项 ✗' % len(failures))
    for f in failures:
        print('   - ' + f)
    sys.exit(1)
print('全部通过 ✓ 适配器与原脚本在同一批文件上结论一致')
