#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""给 index.html 的资源引用加上内容指纹（缓存击穿）。

为什么需要它
------------
本页用 9 个普通 <script src="..."> 同步加载，URL 永远不变。
浏览器（尤其用 file:// 或本地静态服务时）不会主动重新下载没变过的 URL，
于是**我改了 JS，你刷新后跑的还是旧代码**——
6-2 那条「点击试着求 A⁻¹」的任务就是这么反复「修不好」的：
代码在磁盘上是对的，浏览器跑的是缓存里的旧版。

做法
----
把所有本地 js/css 的内容算一个总指纹，写进 URL 的查询串：

    <script src="assets/js/engine.js?v=ab12cd34"></script>

内容一变指纹就变，URL 就变，浏览器必然重新下载；内容没变则指纹不变，
URL 不变，仍然走缓存。**不需要构建工具，也不需要手动改版本号。**

用法
----
    python3 tools/加缓存版本.py          # 写入指纹
    python3 tools/加缓存版本.py --check  # 只检查，不写入（退出码 1 表示过期）
"""
import hashlib
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
INDEX = os.path.join(SITE, 'index.html')


def asset_files():
    files = []
    for sub in ('assets/js', 'assets/css'):
        d = os.path.join(SITE, sub)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if fn.endswith(('.js', '.css')):
                files.append(os.path.join(d, fn))
    return files


def fingerprint():
    h = hashlib.sha256()
    for p in asset_files():
        h.update(os.path.relpath(p, SITE).encode('utf-8'))
        with open(p, 'rb') as f:
            h.update(f.read())
    return h.hexdigest()[:8]


def read_index():
    return open(INDEX, encoding='utf-8').read()


def current_versions(src):
    return set(re.findall(r'(?:src|href)="(assets/[^"]+?)\?v=([0-9a-f]+)"', src))


def main():
    check_only = '--check' in sys.argv
    fp = fingerprint()
    src = read_index()

    # 已有的 ?v=... 先统一替换成新指纹，再补上还没加过的
    new = re.sub(r'((?:src|href)="assets/[^"]+?)\?v=[0-9a-f]+"', r'\1?v=%s"' % fp, src)
    new = re.sub(r'((?:src|href)="assets/[^"]+?\.(?:js|css))"', r'\1?v=%s"' % fp, new)

    if check_only:
        stale = sorted({v for _, v in current_versions(src)} - {fp})
        if stale or not current_versions(src):
            print('✗ index.html 的资源指纹已过期（当前 %s，应为 %s）'
                  % (', '.join(stale) or '无', fp))
            print('  修复：python3 tools/加缓存版本.py')
            return 1
        print('✓ 资源指纹是最新的：%s' % fp)
        return 0

    if new == src:
        print('✓ 指纹已是最新（%s），无需改动' % fp)
        return 0
    open(INDEX, 'w', encoding='utf-8').write(new)
    n = len(re.findall(r'\?v=%s' % fp, new))
    print('✓ 已把 %d 处资源引用更新为指纹 %s' % (n, fp))
    return 0


if __name__ == '__main__':
    sys.exit(main())
