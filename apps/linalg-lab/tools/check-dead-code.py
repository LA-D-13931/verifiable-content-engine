#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""死代码静态判据（第六十四轮 §负一）：**`return` 之后不许出现可执行语句** ✓。

为什么：`runner.py` 里曾有两行 `print('失败…')` / `return 1` 排在 `return 0` **之后** ✗ ——
它们**永远不会执行** ✓，而"看不出来"正是它危险的地方（收尾行从不打印「失败 N 项」✗ 就是这么来的 ✓）。
⇒ 把"看不出"变成**机器判据** ✓（AST 层面，与 `替换.py` 的写前 ast 校验同一套思路 ✓）。

判据：同一 block 里，`Return` 之后若还有**可执行语句** ⇒ 报出（`ast.Return`/`ast.Raise`/`ast.Continue`/`ast.Break` 都算终结 ✓）。
**不报**的情形：`pass`、字符串表达式（docstring ✓）、`# 注释`（不是语句 ✓）。
"""
import ast
import os
import sys


def dead_after_terminator(tree):
    out = []
    for node in ast.walk(tree):
        body = getattr(node, 'body', None)
        if not isinstance(body, list):
            continue
        for i, st in enumerate(body[:-1]):
            if isinstance(st, (ast.Return, ast.Raise, ast.Continue, ast.Break)):
                nxt = body[i + 1]
                if isinstance(nxt, ast.Pass):
                    continue
                if isinstance(nxt, ast.Expr) and isinstance(nxt.value, ast.Constant) and isinstance(nxt.value.value, str):
                    continue          # docstring ✓
                out.append((getattr(nxt, 'lineno', 0), type(st).__name__, type(nxt).__name__))
    return out


def main():
    targets = sys.argv[1:]
    if not targets:
        CS = os.path.dirname(os.path.abspath(__file__))
        targets = [os.path.join(CS, 'runner.py'), os.path.join(CS, 'common.py')]
    bad = 0
    for f in targets:
        if not os.path.isfile(f):
            continue
        try:
            tree = ast.parse(open(f, encoding='utf-8').read())
        except SyntaxError as e:
            print('✗ %s 语法就坏了：%s' % (os.path.basename(f), e)); bad += 1; continue
        probs = dead_after_terminator(tree)
        if probs:
            bad += len(probs)
            print('✗ %s：%d 处**死代码**（终结语句之后还有可执行语句 ✗）' % (os.path.basename(f), len(probs)))
            for ln, a, b in probs[:8]:
                print('    第 %d 行：%s 之后是 %s' % (ln, a, b))
        else:
            print('✓ %s 无死代码' % os.path.basename(f))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
