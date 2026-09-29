#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""路径解析（所有工具共用）。

为什么单独一个文件：本仓库现在分成两块 —— `engine-core/`（引擎库）与
`apps/linalg-lab/`（参考实现）。工具散落在应用侧，却要读写引擎侧的文件，
于是「引擎在哪」这个事实**必须只有一个出处**，否则跟着目录调整到处改。

本文件的做法是：从自身位置向上找，认目录名而不是数层数。
这样将来再挪目录，只要相对关系不变，这个文件不用改。

用法（工具里）：
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from paths import APP, ENGINE, WORKSPACE, REPO
"""
import os

#: 本文件位于 <repo>/apps/linalg-lab/tools/paths.py
TOOLS = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(TOOLS)                    # apps/linalg-lab
APPS = os.path.dirname(APP)                     # apps
REPO = os.path.dirname(APPS)                    # 仓库根
ENGINE = os.path.join(REPO, 'engine-core')      # 引擎库
WORKSPACE = os.path.dirname(os.path.dirname(REPO))   # 工作区根


def check():
    """自检：两个目录都存在且关键文件齐全。工具启动时可用它早失败。"""
    problems = []
    for label, path in (('应用目录', APP), ('引擎目录', ENGINE)):
        if not os.path.isdir(path):
            problems.append('%s不存在：%s' % (label, path))
    for f in ('registry.js', 'mat.js', 'mat.py', 'mat-vectors.json'):
        if not os.path.isfile(os.path.join(ENGINE, f)):
            problems.append('引擎缺少 %s' % f)
    for f in ('index.html',):
        if not os.path.isfile(os.path.join(APP, f)):
            problems.append('应用缺少 %s' % f)
    return problems


if __name__ == '__main__':
    print('仓库根　：%s' % REPO)
    print('引擎目录：%s' % ENGINE)
    print('应用目录：%s' % APP)
    print('工作区　：%s' % WORKSPACE)
    p = check()
    print('自检：%s' % ('通过 ✓' if not p else '失败 ✗'))
    for x in p:
        print('  ✗ %s' % x)
