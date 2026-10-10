#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""锚点引用检查（第七轮 §3.4）：**材料之间禁止用行号互引**。

为什么：行号是**位置**不是**标识**——文件头插入一行，全文件的引用静默失效。
本轮实证：台账头部插入 17 行后，复审方指令里的 `:25`/`:83` 指向了别的内容。
这与「数字要附取数命令」同族：**会漂的硬编码**。

**范围**：只扫"材料文件 → 材料文件"的引用（`.md:123`、`.md:12-34`）。
对**代码的取证引用**（如 `checks_data.py:61-62`）是合法的**时点证据**，不在此列——
把它一并禁掉会逼着人写模糊的引用，反而降低可核查性。

用法：python3 apps/linalg-lab/tools/check-anchor-refs.py
退出码：0 = 没有材料互引行号；1 = 有（列出并建议改成锚点）
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
PAT = re.compile(r'[`"\s（(]([A-Za-z0-9_\u4e00-\u9fff\-]+\.md):(\d+(?:-\d+)?)')
SKIP_DIRS = {'node_modules', '.git', 'fixtures', '.archify', '审查包'}


def main():
    hits = []
    for root, dirs, files in os.walk(REPO):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if not f.endswith('.md'):
                continue
            path = os.path.join(root, f)
            rel = os.path.relpath(path, REPO)
            if rel.startswith('fixtures'):
                continue
            for i, line in enumerate(open(path, encoding='utf-8', errors='replace'), 1):
                for m in PAT.finditer(line):
                    if m.group(1) == f:      # 同文件内自引不算互引
                        continue
                    hits.append((rel, i, m.group(0).strip('`"（( '), line.strip()[:80]))
    print('=== 锚点引用检查（材料互引禁用行号）===')
    print('仓库：%s' % REPO)
    if not hits:
        print('  ✓ 没有发现"材料 → 材料"的行号互引')
        return 0
    print('  发现 %d 处材料互引行号（建议改成锚点：表头名 / 节标题 / 稳定 ID）：' % len(hits))
    for rel, i, ref, snippet in hits[:20]:
        print('    %s:%d → %s' % (rel, i, ref))
        print('        %s' % snippet)
    return 1


if __name__ == '__main__':
    sys.exit(main())
