#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 mat 原语的共享测试向量（engine/mat-vectors.json）。

两侧读同一份向量：
    Python：engine/mat.py 的 _selftest()
    JS    ：assets/js/mat.js 的 _selftest()（由 tools/gen-mat-js.py 生成）

这样「Python 与浏览器算的是同一个数学」就不是靠人声称，而是可随时验证的事实。

向量设计原则：**专门覆盖容易出错的地方**，而不是随机撒点。
    · 奇异 / 近奇异矩阵（|det| 在 EPS 附近两侧）
    · 秩亏、重复行、全零行列
    · 反向共线（180°，历史上被判错过）
    · 平行直线（无交点）、三线共点
    · 目标在列空间内 / 外
"""
import hashlib
import json, os, sys, random

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
sys.path.insert(0, SITE)
from engine import mat  # noqa: E402


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


def source_signature():
    """engine/mat.py **数学语义**的指纹（sha256）。

    用 AST 而不是文件字节：注释、docstring、空行都不影响数学，
    不该触发「向量过期」。早先对整文件做哈希的版本，因为加一行注释
    就误报——典型的假警报，而假警报会让检查被忽视。

    include_attributes=False 保证 AST 里不含行号与列偏移。
    """
    import ast, hashlib
    tree = ast.parse(open(os.path.join(SITE, 'engine', 'mat.py'), encoding='utf-8').read())
    tree = _strip_docstrings(tree)
    return 'ast:' + hashlib.sha256(
        ast.dump(tree, include_attributes=False).encode('utf-8')).hexdigest()


random.seed(20260929)          # 固定种子，保证向量可复现

VECTORS = []


def add(fn, args, note):
    """记录一组调用及其期望结果（期望值由本权威实现算出）。"""
    VECTORS.append({
        'fn': fn,
        'args': args,
        'expect': mat._dispatch(fn, args),
        'note': note,
    })


# ---------- 矩阵素材 ----------
M = {
    'identity2': [[1, 0], [0, 1]],
    'identity3': mat.identity(3),
    'singular': [[1, 2], [2, 4]],                 # det = 0
    'near_singular': [[1, 2], [2, 4.0000000001]],  # |det| ≈ 1e-10，卡在 EPS 上
    'tiny_neg': [[1, 2], [2, 3.9999999999]],       # |det| ≈ 1e-10，负侧
    'neg_det': [[0, 1], [1, 0]],                   # det = -1（翻转）
    'shear': [[1, 1], [0, 1]],
    'rotation90': [[0, -1], [1, 0]],               # 无实特征值
    'diag21': [[2, 0], [0, 1]],
    'zero': [[0, 0], [0, 0]],
    'rect23': [[1, 2, 3], [4, 5, 6]],
    'rank1_rect': [[1, 2, 3], [2, 4, 6]],
    'upper3': [[1, 2, 3], [0, 4, 5], [0, 0, 6]],
    'dup_rows': [[1, 1], [1, 1]],
    'zero_row': [[1, 2], [0, 0]],
}

# ---------- det ----------
for k in ['identity2', 'identity3', 'singular', 'near_singular', 'neg_det',
          'shear', 'rotation90', 'diag21', 'zero', 'upper3']:
    add('det', [M[k]], 'det(%s)' % k)

# ---------- rank ----------
for k in ['identity2', 'identity3', 'singular', 'near_singular', 'tiny_neg',
          'zero', 'rect23', 'rank1_rect', 'upper3', 'dup_rows', 'zero_row']:
    add('rank', [M[k]], 'rank(%s)' % k)

# ---------- inv2 / solve2 ----------
for k in ['identity2', 'singular', 'near_singular', 'shear', 'neg_det',
          'diag21', 'zero', 'rotation90']:
    add('inv2', [M[k]], 'inv2(%s)' % k)
for k, b in [('identity2', [3, 4]), ('shear', [1, 1]), ('singular', [1, 1]),
             ('near_singular', [2, 4]), ('diag21', [-5, 7]), ('rotation90', [1, 0])]:
    add('solve2', [M[k], b], 'solve2(%s, %s)' % (k, b))

# ---------- eigen2 ----------
for k in ['identity2', 'diag21', 'singular', 'shear', 'neg_det', 'rotation90', 'zero']:
    add('eigen2', [M[k]], 'eigen2(%s)' % k)

# ---------- 向量运算 ----------
VS = {
    'e1': [1, 0], 'e2': [0, 1],
    'same': [1, 1], 'same2': [2, 2],          # 同向、长度不同
    'anti': [-1, -1],                          # 反向共线（180°）——历史上判错过
    'perp': [-1, 1],
    'zero2': [0, 0],
    'skew': [1, 2],
}
for a, b in [('same', 'same2'), ('same', 'anti'), ('e1', 'e2'),
             ('e1', 'perp'), ('same', 'perp'), ('e1', 'zero2'), ('skew', 'e2')]:
    add('angleBetweenDeg', [VS[a], VS[b]], 'angle(%s, %s)' % (a, b))

for a, b in [('e1', 'e2'), ('same', 'anti'), ('skew', 'e1')]:
    add('dot', [VS[a], VS[b]], 'dot(%s, %s)' % (a, b))

add('cross', [[1, 0, 0], [0, 1, 0]], 'cross(e1, e2) = e3')
add('cross', [[1, 2, 3], [4, 5, 6]], 'cross(任意)')
add('cross', [[1, 0, 0], [2, 0, 0]], 'cross(共线) = 零向量')

# ---------- 矩阵运算 ----------
add('mul', [M['shear'], M['rotation90']], 'shear·rot90')
add('mul', [M['rotation90'], M['shear']], 'rot90·shear（与上一条不可交换）')
add('mul', [M['rect23'], [[1, 0], [0, 1], [1, 1]]], '2×3 · 3×2')
add('mulVec', [M['shear'], [1, 1]], 'shear·(1,1)')
add('mulVec', [M['rotation90'], [1, 0]], 'rot90·e1')
add('identity', [3], 'identity(3)')
add('identity', [1], 'identity(1)')

# ---------- 可达性：onSpan ----------
add('onSpan', [M['singular'], [2, 4]], 'b 在列空间内（与列共线）')
add('onSpan', [M['singular'], [1, 2]], 'b 在列空间内（另一表述）')
add('onSpan', [M['singular'], [2, 2]], 'b 不在列空间内 ← 真实缺陷 7-4 的原型')
add('onSpan', [M['identity2'], [5, -3]], '单位阵：任何 b 都可达')
add('onSpan', [M['zero'], [1, 1]], '零矩阵：非零 b 不可达')
add('onSpan', [M['zero'], [0, 0]], '零矩阵：零 b 可达')
add('onSpan', [M['rect23'], [1, 1]], '2×3 矩阵的列空间')
add('onSpan', [M['rect23'], [0, 0, 1]], '维度不匹配的退化情形')

# ---------- 可达性：intersectLines ----------
L = {
    'x1': {'a': 1, 'b': 0, 'c': 1},              # x = 1
    'y2': {'a': 0, 'b': 1, 'c': 2},              # y = 2
    'y2b': {'a': 0, 'b': 2, 'c': 4},             # y = 2（系数放大）
    'x1b': {'a': 2, 'b': 0, 'c': 2},             # x = 1（系数放大）
    'parallel': {'a': 1, 'b': 0, 'c': 5},        # x = 5，与 x1 平行
    'diag': {'a': 1, 'b': 1, 'c': 3},            # x + y = 3
    'diag2': {'a': 1, 'b': -1, 'c': -1},         # x - y = -1
}
add('intersectLines', [[L['x1'], L['y2']]], '两线交于 (1,2)')
add('intersectLines', [[L['x1'], L['y2'], L['diag']]], '三线共点 (1,2)')
add('intersectLines', [[L['x1'], L['y2'], L['diag2']]], '三线不共点 → None')
add('intersectLines', [[L['x1'], L['parallel']]], '两平行线 → None')
add('intersectLines', [[L['x1b'], L['y2b']]], '系数放大后仍交于 (1,2)')
add('intersectLines', [[L['diag'], L['diag2']]], '斜率相交')
add('intersectLines', [[]], '空列表 → None')


def main():
    out = os.path.join(SITE, 'engine', 'mat-vectors.json')
    payload = {'signature': source_signature(), 'vectors': VECTORS}
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    print('✓ 已生成 %d 组测试向量 → %s' % (len(VECTORS), out))
    print('  签名（engine/mat.py 的 sha256 前 12 位）：%s' % payload['signature'][:12])
    # 立刻自检一遍
    return mat._selftest()


if __name__ == '__main__':
    sys.exit(main())
