#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 assets/js/labs.json 生成 assets/js/lab-data.js。

方向说明（重要）
================
    labs.json  ──[本脚本]──▶  lab-data.js
    唯一编辑面                  生成物（请勿手改）

为什么不反过来：纯 JSON 才能被语言模型可靠地书写、被校验器直接 json.load、
被任意语言的工具读取。lab-data.js 保留下来只是为了**浏览器能以普通
<script> 同步加载**（本项目的硬约束：零构建、双击 index.html 即可运行，
不能用 fetch 读 JSON——file:// 下会被 CORS 拦住）。

因此两者不是「两份实现」，而是「一份数据 + 一个装数据的壳」。
一致性由 tools/verify-labs.mjs 逐字段比对来保证。

用法：
    python3 tools/gen-labs-js.py            # 生成
    python3 tools/gen-labs-js.py --check    # 只检查是否最新
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
SRC = os.path.join(SITE, 'assets', 'js', 'labs.json')
OUT = os.path.join(SITE, 'assets', 'js', 'lab-data.js')

HEADER = '''/* ============================================================
 * 关卡内容（生成物）
 *
 * ⚠️ 本文件由 tools/gen-labs-js.py 从 assets/js/labs.json 生成，请勿手改。
 *    要改关卡内容，改 labs.json，然后重跑：
 *        python3 tools/gen-labs-js.py
 *
 * 为什么保留这个文件：浏览器要用普通 <script> **同步**加载关卡数据，
 * 这样双击 index.html 就能运行（file:// 下 fetch 读 JSON 会被 CORS 拦住）。
 * 数据本身以 labs.json 为准，本文件只是它的加载壳。
 * ============================================================ */
'''


def render(obj, indent=0):
    """把数据渲染成 JS 字面量（JSON 本身就是合法 JS，直接用 json.dumps）。"""
    return json.dumps(obj, ensure_ascii=False, indent=2)


def main():
    check_only = '--check' in sys.argv
    if not os.path.exists(SRC):
        print('✗ 找不到 %s —— 先运行 node tools/gen-labs-json.mjs' % SRC)
        return 2
    with open(SRC, encoding='utf-8') as f:
        data = json.load(f)

    chapters = data['chapters']
    labs = data['labs']

    # 缩进内部再缩一层，让整体看起来像手写的常量
    def block(name, arr):
        body = render(arr)
        body = '\n'.join(('    ' + ln) if ln.strip() else ln for ln in body.split('\n'))
        return 'window.%s = %s;\n' % (name, body)

    content = HEADER + '\n' + block('CHAPTERS', chapters) + '\n' + block('LABS', labs)

    old = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
    if old == content:
        print('✓ assets/js/lab-data.js 已是最新（%d 实验 / %d 章节）'
              % (len(labs), len(chapters)))
        return 0
    if check_only:
        print('✗ assets/js/lab-data.js 已过期 —— 运行 python3 tools/gen-labs-js.py')
        return 1
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write(content)
    n_tasks = sum(len(l['tasks']) for l in labs)
    print('✓ 已生成 assets/js/lab-data.js')
    print('  %d 实验 / %d 章节 / %d 任务，%d KB'
          % (len(labs), len(chapters), n_tasks, len(content.encode()) // 1024))
    return 0


if __name__ == '__main__':
    sys.exit(main())
