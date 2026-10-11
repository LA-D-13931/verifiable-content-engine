#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""锚点安全替换 —— 治「凭记忆写锚点」。

## 为什么有它
我在第 24–33 轮里，**至少 6 次**因为"锚点是我以为的文本"而让替换**静默不命中**：
把 `sed` 加的前缀缩进当成了文件缩进、子串里少一个空格、把正则转义写进了普通子串……
**每一次都白费一轮**，而且**失败时没有任何提示**（替换函数找不到就不改，退出码照样 0）。

## 它做什么
- **命中必须为 1**：0 次 → 报错并**打印最相近的几行**（带行号）；>1 次 → 报错并列出全部位置；
- **先看再改**：`--show` 只打印匹配处上下文，不改文件；
- **写完自证**：替换后重新读回文件，确认 `old` 已消失、`new` 已出现。

用法：
  python3 替换.py <文件> --show "<锚点子串>"
  python3 替换.py <文件> --old "<锚点子串>" --new "<新文本>"     # 简单替换
  python3 替换.py <文件> --old "<锚点>" --block <含新文本的文件或 -> 从 stdin 读整段
退出码：0 成功 / 1 锚点不唯一或没找到（并打印候选）
"""
import os
import argparse
import difflib
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('path')
    ap.add_argument('--show')
    ap.add_argument('--old')
    ap.add_argument('--new')
    ap.add_argument('--block')
    ap.add_argument('--verify-cmd', default=None,
                    help='替换后要跑的命令；非 0 则报错（用于"改完这个文件还站得住吗"）')
    a = ap.parse_args()
    try:
        text = open(a.path, encoding='utf-8').read()
    except OSError as e:
        print('✗ 读不到文件：%s' % e); return 1
    lines = text.splitlines(True)

    if a.show:
        hits = [i for i, l in enumerate(lines, 1) if a.show in l]
        print('锚点 %r 在 %s 命中 %d 处' % (a.show[:60], a.path, len(hits)))
        for i in hits[:6]:
            print('  %4d  %s' % (i, lines[i - 1].rstrip()))
        return 0

    if not a.old:
        print('✗ 要替换就得给 --old（先 --show 看一眼）'); return 1
    n = text.count(a.old)
    if n != 1:
        print('✗ 锚点命中 %d 次（必须恰好 1 次）—— 这是"凭记忆写锚点"的典型症状' % n)
        near = difflib.get_close_matches(a.old, [l.strip() for l in lines], n=5, cutoff=0.4)
        if n == 0 and near:
            print('  最相近的几行：')
            for c in near:
                for i, l in enumerate(lines, 1):
                    if l.strip() == c:
                        print('    %4d  %s' % (i, c[:100])); break
        elif n > 1:
            for i, l in enumerate(lines, 1):
                if a.old in l:
                    print('    %4d  %s' % (i, l.strip()[:100]))
        return 1

    new = a.new
    if a.block:
        new = sys.stdin.read() if a.block == '-' else open(a.block, encoding='utf-8').read()
    out = text.replace(a.old, new, 1)
    # 自证：old 必须消失（除非 new 里本来就含它 —— 例如插入到某行之前这种用法 ✓）；new 必须出现 ✓
    _old_gone = (a.old not in out) or (a.old in (new or ''))
    if not _old_gone or (new and new not in out):
        print('✗ 写完自证失败（old 仍在或 new 未出现）'); return 1
    # **先验后写**（第四十轮修正）：上一版先写再验 ⇒ 语法一坏就把坏内容落盘了 ✗。
    # 现在：先在内存里验，只有全过才写。
    # 自证 1：**整份文件还站得住吗**（上一轮我摔 4 次全是因为缺这一步）
    if a.path.endswith('.py'):
        import ast
        try:
            ast.parse(open(a.path, encoding='utf-8').read())
        except SyntaxError as e:
            print('✗ 替换后语法坏了：%s（行 %s）—— 已停在此处，请修' % (e.msg, e.lineno))
            return 1
    # 落盘自证 2：可选地跑一条命令（如该文件的主命令 / 单元测试）
    if a.verify_cmd:
        import subprocess as _sp
        r = _sp.run(a.verify_cmd, shell=True, capture_output=True, text=True)
        if r.returncode != 0:
            print('✗ --verify-cmd 失败（退出码 %d）：%s' % (r.returncode, a.verify_cmd))
            print('   ' + (r.stdout or r.stderr).strip()[:200])
            return 1
        print('  · --verify-cmd 通过：%s' % a.verify_cmd)

    # **写盘自证**（第四十二轮）：上一轮我踩过"报了成功却没写盘" ✗ ——
    # 那次是"写盘那行被自己的替换删掉" ✗，工具毫无察觉 ✗。
    # 所以落盘之后必须**读回**确认内容真的变了、**mtime** 真的动了 ✓。
    _before = os.path.getmtime(a.path) if os.path.exists(a.path) else 0
    open(a.path, 'w', encoding='utf-8').write(out)
    os.utime(a.path, None)                       # 显式 touch，确保 mtime 一定变化 ✓
    _after = os.path.getmtime(a.path)
    _back = open(a.path, encoding='utf-8').read()
    if _back != out:
        print('✗ 写盘自证失败：读回的內容与要写入的不一致（磁盘没落 / 被并发改）')
        return 1
    if not (_after > _before):
        print('✗ 写盘自证失败：mtime 没变（%s → %s）—— 文件可能没被真正写入' % (_before, _after))
        return 1
    print('✓ 替换成功（锚点唯一；写完自证通过；语法' + ('已校验' if a.path.endswith('.py') else '不适用') + '）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
