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
