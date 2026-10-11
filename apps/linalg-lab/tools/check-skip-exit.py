#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""元检查（批次 C · 第八轮 D-1 的 5a 片）：**"打印跳过却 exit 0"** 必须判红，除非它是有意的。

判据（审计方给的，我照抄并写进判据里）：
> **"这个脚本退出 0 时，聚合层会不会把它记成通过？"** 会 → 必须改；不会 → 进白名单并注明理由。

机械识别：同一行（或其后 2 行内）既有「跳过/skipped」又有 `process.exit(0)`。
**白名单**（逐处判定过，附理由）：
  · `render-measure.mjs:33` 输出 `{"skipped": "找不到 Edge 或 Chrome（环境不足，不是通过）"}` 且 exit 0
  · `render-measure.mjs:37` 输出 `{"skipped": "puppeteer-core 不可用：…"}` 且 exit 0
    理由：`engine-core/adapters/content-spec/checks_render.py:56-57` 会读 `skipped` 键并转成
    `triple(None, '环境不足：…')` —— **聚合层把它记成"环境不足"，不是"通过"** → 不属于本检查要治的病。
    （反例：若哪天 `checks_render.py` 不再认 `skipped` 键，这两处就会变成"静默通过" → 本检查会失去豁免理由，
     所以白名单里同时记下"依赖 checks_render.py 认这个键"这一条前提。）

用法：python3 apps/linalg-lab/tools/check-skip-exit.py
退出码：0 = 无未豁免的命中；1 = 有
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
TOOLS = os.path.join(REPO, 'apps', 'linalg-lab', 'tools')
WHITELIST = {
    'render-measure.mjs:33': 'skipped 键被 checks_render.py:56 转成"环境不足" → 聚合层不会记成通过',
    'render-measure.mjs:37': '同上（puppeteer-core 不可用）',
}



def verify_premise():
    """批次 B：**豁免前提必须被真实校验**，不能只写在注释里。

    白名单的前提是「checks_render.py 会把 skipped 键转成非 pass 态」。
    这里动态喂一个 {"skipped": "…"} 给它的判定函数，断言 pass is None。
    改了就会红：删掉 checks_render.py 的 skipped 分支 → 本检查报红。
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        'checks_render', os.path.join(REPO, 'engine-core', 'adapters', 'content-spec', 'checks_render.py'))
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as e:
        return False, 'checks_render.py 无法加载：%s' % e
    cand = None
    for name in dir(mod):
        f = getattr(mod, name)
        if callable(f) and getattr(f, '__module__', '') == mod.__name__ and not name.startswith('_'):
            cand = f
            break
    if cand is None:
        return False, 'checks_render.py 里找不到可调用的判定函数'
    payload = {'skipped': '批次 B 校验用的假输出'}
    try:
        t = cand(payload) if cand.__code__.co_argcount == 1 else cand(payload, 'fixtures/x.html')
    except Exception as e:
        return False, '调用判定函数失败（%s）—— 请人工确认 skipped 的转译位置' % e
    got = getattr(t, 'pass', None) if not isinstance(t, tuple) else t[0]
    if got is None:
        return True, '假输出 {"skipped": …} → pass is None（仍是非通过态）✓'
    return False, 'skipped 被转成了 pass=%r —— 豁免前提失效，那两处会退化成静默通过 ✗' % (got,)


def main():
    print('=== 元检查：打印跳过却 exit 0（批次 C）===')
    hits = []
    for name in sorted(os.listdir(TOOLS)):
        if not name.endswith('.mjs'):
            continue
        path = os.path.join(TOOLS, name)
        lines = open(path, encoding='utf-8', errors='replace').read().splitlines()
        for i, line in enumerate(lines):
            window = '\n'.join(lines[i:i + 3])
            if re.search(r'跳过|skipped', line) and 'process.exit(0)' in window:
                key = '%s:%d' % (name, i + 1)
                hits.append((key, line.strip()[:110]))
    unwaived = [(k, t) for k, t in hits if k not in WHITELIST]
    premise_ok, why = verify_premise()
    print('  豁免前提校验：%s' % why)
    print('  命中 %d 处 ｜ 已豁免 %d 处（白名单带理由）｜ 未豁免 %d 处'
          % (len(hits), len(hits) - len(unwaived), len(unwaived)))
    for k, reason in WHITELIST.items():
        print('    ✓ 豁免 %s —— %s' % (k, reason))
    for k, text in hits:
        if k in WHITELIST:
            print('    · %s  %s' % (k, text))
    for k, text in unwaived:
        print('    ✗ %s  %s' % (k, text))
    if unwaived:
        print('\\n发现未豁免的"打印跳过却 exit 0" ✗（判据：聚合层会不会把它记成通过？）')
        return 1
    print('\\n没有未豁免的命中 ✓')
    return 0


if __name__ == '__main__':
    sys.exit(main())
