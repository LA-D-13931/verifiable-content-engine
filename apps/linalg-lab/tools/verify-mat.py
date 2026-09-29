#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""矩阵原语层的完整校验：生成物是否最新 + 两侧是否算同一个数学。

为什么单独一个脚本：check-lab.py 是纯内容的只读校验，不应依赖 Node。
矩阵层的一致性需要同时跑 Python 与 JS，故独立出来。

检查项：
  1. engine-core/mat.js 是否与 tools/gen-mat-js.py 的模板一致（--check）
  2. mat.py / gen-mat-js.py 是否比生成物更新（改了源头忘了重新生成的兜底）
  3. 两侧各自跑 77 组测试向量

用法：python3 tools/verify-mat.py
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# --- 路径解析：统一走 tools/paths.py，不在各工具里数层数 ---
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import APP as SITE, ENGINE, REPO, WORKSPACE as _WS   # noqa: E402

GEN_JS = os.path.join(HERE, 'gen-mat-js.py')
MAT_PY = os.path.join(ENGINE, 'mat.py')
MAT_JS = os.path.join(ENGINE, 'mat.js')
VEC = os.path.join(ENGINE, 'mat-vectors.json')

problems = []


def check_generated():
    r = subprocess.run([sys.executable, GEN_JS, '--check'],
                       capture_output=True, text=True)
    if r.returncode != 0:
        problems.append('engine-core/mat.js 已过期 —— 运行 python3 tools/gen-mat-js.py')


def _strip_docstrings(tree):
    """从 AST 里剥掉模块/函数/类的文档字符串。

    docstring 是常量字符串，会被 ast.dump 收进去，导致「只改文档」
    也被判为数学变更。我们关心的是可执行语义，所以剥掉它们。
    """
    import ast
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.FunctionDef,
                                 ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        body = node.body
        if (body and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)):
            node.body = body[1:] or [ast.Pass()]
    return tree


def mat_py_signature():
    """engine-core/mat.py 数学语义的指纹，与 gen-mat-vectors.py 用同一算法（AST）。"""
    import ast, hashlib
    tree = ast.parse(open(MAT_PY, encoding='utf-8').read())
    tree = _strip_docstrings(tree)
    return 'ast:' + hashlib.sha256(
        ast.dump(tree, include_attributes=False).encode('utf-8')).hexdigest()


def check_vectors_signature():
    """向量文件里记着生成它的 mat.py 签名；对不上说明改了数学但没重新生成。

    比时间戳可靠得多：改注释、删别名都不会误报，改了数学一定报。
    （早先用时间戳的版本就因为删了一个别名而误报，属于典型的假警报。）
    """
    import json
    if not os.path.exists(VEC):
        problems.append('缺少 engine-core/mat-vectors.json —— 运行 python3 tools/gen-mat-vectors.py')
        return
    with open(VEC, encoding='utf-8') as f:
        payload = json.load(f)
    recorded = payload.get('signature') if isinstance(payload, dict) else None
    if not recorded:
        problems.append('engine-core/mat-vectors.json 里没有签名 —— 运行 python3 tools/gen-mat-vectors.py')
        return
    if recorded != mat_py_signature():
        problems.append('engine-core/mat.py 的数学已变更，但测试向量未重新生成 —— '
                        '运行 python3 tools/gen-mat-vectors.py')
    # mat.js 的新鲜度由 gen-mat-js.py --check 逐字节比对，不必再看时间戳


def check_vectors():
    """两侧各自跑测试向量。"""
    r = subprocess.run([sys.executable, MAT_PY], capture_output=True, text=True)
    print('  [Python] ' + (r.stdout or r.stderr).strip().split('\n')[-1])
    if r.returncode != 0:
        problems.append('engine-core/mat.py 的测试向量自检未通过')
    r2 = subprocess.run(['node', os.path.join(HERE, 'verify-mat.mjs')],
                        capture_output=True, text=True, cwd=SITE)
    last = [l for l in (r2.stdout or '').strip().split('\n') if l.strip()]
    print('  [JS]     ' + (last[-1] if last else '(无输出)'))
    if r2.returncode != 0:
        problems.append('engine-core/mat.js 的测试向量自检未通过')


if __name__ == '__main__':
    print('=== 矩阵原语层校验 ===')
    check_generated()
    check_vectors_signature()
    check_vectors()
    print()
    if problems:
        print('发现 %d 个问题：' % len(problems))
        for p in problems:
            print('  ✗ %s' % p)
        sys.exit(1)
    print('全部通过 ✓ 生成物最新，且两侧算的是同一个数学')
