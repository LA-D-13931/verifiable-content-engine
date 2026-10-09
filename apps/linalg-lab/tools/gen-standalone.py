#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把可视化页打成**单文件自包含**版本（发给谁都能双击打开）。

为什么需要
==========
可视化页用 <script src="../../engine-core/*.js"> 引用引擎。这在原目录里没问题，
但**单独拷出来就废了**——实测：拷到桌面后打开，四个引擎文件全部加载失败，
格子数 0，页面等于空白。

对比赛演示来说这是真风险：自己双击能开，**发给评委就废了**。

做法与取舍
==========
把四个引擎脚本的内容**内联**进 <script> 标签。代价是文件变大（约 +90KB），
收益是零依赖、零服务器、发给任何人双击即用 —— 这正是本项目一贯的取舍
（零构建、双击即运行）。

⚠️ 单文件版是**生成物**，不要手改。要改就改源页面或引擎，再重跑本脚本。
   这是为了不让「同一份逻辑存在两处」。

用法：python3 tools/gen-standalone.py [输出路径]
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(HERE)
REPO = dirname = os.path.dirname(os.path.dirname(APP))
SRC = os.path.join(APP, '引擎可视化.html')
DEFAULT_OUT = os.path.join(APP, '引擎可视化_单文件版.html')

#: 需要内联的引擎脚本（顺序不能换：registry 与领域插件注册到全局）
ENGINE_SCRIPTS = [
    'engine-core/mat.js',
    'engine-core/registry.js',
    'engine-core/domains/linalg/judge.js',
    'engine-core/domains/calculus/judge.js',
]


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUT
    html = open(SRC, encoding='utf-8').read()

    total = 0
    for rel in ENGINE_SCRIPTS:
        full = os.path.join(REPO, rel)
        code = open(full, encoding='utf-8').read()
        # 找到对应的 <script src="..."> 标签并替换为内联内容
        pat = re.compile(r'<script src="[^"]*%s[^"]*"></script>' % re.escape(os.path.basename(rel)))
        m = pat.search(html)
        assert m, '找不到 %s 的 script 标签' % rel
        # 内联时保留一行出处注释，便于别人知道这段来自哪个文件
        inline = ('<script>\n/* ===== 内联自 %s（单文件版；源文件在仓库里，改要改源文件） ===== */\n'
                  % rel) + code + '\n</script>'
        html = html[:m.start()] + inline + html[m.end():]
        total += len(code)
        print('  ✓ 已内联 %-44s %6d 字节' % (rel, len(code)))

    # 自检：不应再残留任何 src 引用
    left = re.findall(r'<script src="[^"]*"></script>', html)
    assert not left, '仍有未内联的脚本引用：%s' % left

    # 在标题下加一行标注，说明这是单文件版
    html = html.replace('<div class="sub">把交互式课件的内容交给引擎',
                        '<div class="sub"><b>单文件版</b>（引擎已内联，双击即用、可单独发送）　｜　'
                        '把交互式课件的内容交给引擎')

    open(out_path, 'w', encoding='utf-8').write(html)
    print()
    print('✓ 已生成 %s' % os.path.basename(out_path))
    print('  内联引擎代码：%d 字节' % total)
    print('  文件体积：%.0f KB' % (os.path.getsize(out_path) / 1024))
    print('  剩余外部依赖：0')


if __name__ == '__main__':
    main()
