#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全貌图单一来源检查（第八轮 §3）：`.archify/` 的源图与仓库内副本**必须同内容**。

为什么要有这条：图在仓库外 → 改动没有 revision、审计方无法逐行核；
复制进仓库后，**两边就会开始漂** —— 而"同一份东西被写在两处"正是 `single-source` 在治的病。
**图自己先犯一次，就不体面了。**

范围：只比 `.archify/architecture-engine-audit-flow-*/review-2/engine-audit-flow.html`
（取**最新**的那个目录）与 `docs/全貌图/engine-audit-flow.html` 的**字节内容**。
源图不存在（如全新克隆、或 archify 未跑）→ 报「不适用」（不算通过、也不算失败）。

用法：python3 apps/linalg-lab/tools/check-figure-sync.py
退出码：0 = 一致（或源图不在位）；1 = 不一致（会打印两边的 sha256 与字节数）
"""
import glob
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
WS = os.path.dirname(os.path.dirname(REPO))          # 工作区根（.archify 在它下面）
IN_REPO = os.path.join(REPO, 'docs', '全貌图', 'engine-audit-flow.html')


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    print('=== 全貌图单一来源检查 ===')
    srcs = sorted(glob.glob(os.path.join(WS, '.archify', 'architecture-engine-audit-flow-*',
                                         'review-2', 'engine-audit-flow.html')))
    if not srcs:
        print('  – 不适用：.archify 下的源图不在位（全新克隆或 archify 未跑）→ 不算通过，也不算失败')
        return 0
    src = srcs[-1]
    if not os.path.isfile(IN_REPO):
        print('  ✗ 仓库内副本缺失：%s' % os.path.relpath(IN_REPO, REPO))
        return 1
    a, b = sha(src), sha(IN_REPO)
    print('  源图（.archify，取最新）：%s' % os.path.relpath(src, WS))
    print('      sha256 %s ｜ %d 字节' % (a[:16], os.path.getsize(src)))
    print('  仓库副本（docs/全貌图）：sha256 %s ｜ %d 字节' % (b[:16], os.path.getsize(IN_REPO)))
    if a != b:
        print('  ✗ 两边内容不一致 —— 图已经漂了（这正是 single-source 要治的病）')
        print('     修法：把源图重新复制进仓库（cp "<源图>" docs/全貌图/engine-audit-flow.html）')
        return 1
    print('  ✓ 一致（同一份内容，两个位置）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
