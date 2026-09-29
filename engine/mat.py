#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""矩阵与向量原语 —— 本项目的唯一权威实现（Python 侧）。

为什么要单独一个文件
====================
在此之前，「同一个数学」有**两套各自独立**的实现：

  · `assets/js/mat.js`     浏览器判题用（高斯消元法求秩，主元用最大值）
  · `tools/check-lab.py`   内容校验用（det2 / rank_of，主元同样用最大值）

两套实现的容差还不一样（JS 用 1e-10、Python 用 1e-9），秩的算法细节也有差异。
**同一个数学有两套实现，迟早会分叉**——而校验器的全部价值就在于「它和被校验的
对象算的是同一个数学」。所以这里收敛为一份权威实现：

  · Python 侧读本文件
  · 浏览器侧读 `assets/js/mat.js`，而后者**由 tools/gen-mat-js.py 从本文件生成**

生成保证了「改一处、两边同步」，而不是靠人记得。

约定
====
矩阵是行数组的数组：`[[a, b], [c, d]]` 表示
    ┌ a  b ┐
    └ c  d ┘
矩阵第 j 列 = 该列对应的基向量落点。
"""

import math

#: 数值零的判定阈值。
#: 取 1e-10：既小于常见输入的最小有效位（0.5 步长的拖动），
#: 又大于 2×2 行列式在双精度下的典型舍入误差。
EPS = 1e-10

#: 直线求交时的零判定阈值。比 EPS 宽，因为直线的 a/b/c 是由点算出来的，
#: 累积误差比原始矩阵元素大。
LINE_EPS = 1e-9

#: 判断交点是否真的落在所有直线上时允许的偏差。
#: 不能用 1e-9——拖动是 0.5 步长、直线参数来自浮点运算，实测量级在 1e-2 左右。
INTERSECT_TOL = 0.05


# ---------------- 基础 ----------------

def identity(n):
    """n×n 单位阵。"""
    return [[1 if i == j else 0 for j in range(n)] for i in range(n)]


def clone(m):
    """深拷贝一个矩阵（逐行复制，避免共享行引用）。"""
    return [row[:] for row in m]


def mul(a, b):
    """矩阵相乘 a·b。"""
    n, k, m = len(a), len(b), len(b[0])
    return [[sum(a[i][t] * b[t][j] for t in range(k)) for j in range(m)]
            for i in range(n)]


def mul_vec(m, v):
    """矩阵乘向量 m·v。"""
    return [sum(x * v[j] for j, x in enumerate(row)) for row in m]


def dot(a, b):
    """向量点积。"""
    return sum(x * b[i] for i, x in enumerate(a))


def cross(a, b):
    """三维向量叉积。"""
    return [a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0]]


# ---------------- 行列式与逆 ----------------

def det(m):
    """行列式（拉普拉斯展开，1/2/3 阶有直通路径）。"""
    n = len(m)
    if n == 1:
        return m[0][0]
    if n == 2:
        return m[0][0] * m[1][1] - m[0][1] * m[1][0]
    total = 0
    for j in range(n):
        minor = [[x for c, x in enumerate(row) if c != j] for row in m[1:]]
        total += (1 if j % 2 == 0 else -1) * m[0][j] * det(minor)
    return total


def inv2(m):
    """2×2 逆矩阵；奇异（|det| < EPS）时返回 None。

    注意：这里用 < EPS 而不是 == 0，因为拖动产生的浮点误差会让
    本该为 0 的行列式变成 1e-17 之类的值。
    """
    d = det(m)
    if abs(d) < EPS:
        return None
    return [[m[1][1] / d, -m[0][1] / d],
            [-m[1][0] / d, m[0][0] / d]]


# ---------------- 秩 ----------------

def rank(m):
    """数值秩：带部分主元选取的高斯消元。

    全程用同一个 EPS 判定主元是否为零，因此「秩」这个判定是稳定的：
    对同一个输入，Python 侧与浏览器侧必须给出相同结果（由 gen-mat-js.py
    从本文件生成 JS 来保证）。
    """
    a = clone(m)
    rows, cols = len(a), len(a[0])
    r = 0
    for c in range(cols):
        if r >= rows:
            break
        piv = max(range(r, rows), key=lambda i: abs(a[i][c]))
        if abs(a[piv][c]) < EPS:
            continue
        a[r], a[piv] = a[piv], a[r]
        for i in range(r + 1, rows):
            f = a[i][c] / a[r][c]
            for j in range(c, cols):
                a[i][j] -= f * a[r][j]
        r += 1
    return r



# ---------------- 2×2 特征 ----------------

def eigen2(m):
    """2×2 实特征值与特征方向；无实特征值时返回 None。

    返回 {"values": [λ1, λ2], "vectors": [v1, v2]}，方向已归一化。
    """
    tr = m[0][0] + m[1][1]
    d = det(m)
    disc = tr * tr - 4 * d
    if disc < 0:
        return None
    sq = math.sqrt(disc)
    l1, l2 = (tr + sq) / 2, (tr - sq) / 2

    def raw(lam):
        a = m[0][0] - lam
        b = m[0][1]
        c = m[1][0]
        e = m[1][1] - lam
        if abs(b) > EPS:
            return [b, -a]
        if abs(c) > EPS:
            return [-e, c]
        if abs(a) < EPS:
            return [1, 0]
        return [0, 1]

    def norm(v):
        length = math.hypot(v[0], v[1])
        return [0, 0] if length < EPS else [v[0] / length, v[1] / length]

    return {"values": [l1, l2], "vectors": [norm(raw(l1)), norm(raw(l2))]}


def solve2(A, b):
    """解 2×2 线性方程组 Ax = b；A 奇异时返回 None。"""
    inv = inv2(A)
    return None if inv is None else mul_vec(inv, b)


def angle_between_deg(u, v):
    """两向量夹角（度）。任一个接近零向量时返回 180。

    注意调用方的用法：共线判定必须用 min(ang, 180 - ang)，
    否则反向共线（180°）会被误判为不共线。这个坑真实发生过。
    """
    lu, lv = math.hypot(u[0], u[1]), math.hypot(v[0], v[1])
    if lu < EPS or lv < EPS:
        return 180.0
    cos = dot(u, v) / (lu * lv)
    cos = max(-1.0, min(1.0, cos))
    return math.degrees(math.acos(cos))


# ---------------- 可达性辅助 ----------------

def augment(A, b):
    """把向量 b 作为新的一列接到矩阵 A 右边，用于秩比较判可达。"""
    return [list(row) + [b[i]] for i, row in enumerate(A)]


def on_span(A, target, tol=INTERSECT_TOL):
    """target 是否落在 A 的列空间内。

    这是最核心的一条可达性判据：
        b 可达  <=>  rank([A | b]) == rank(A)
    加一列不会降秩；只要秩升高，就说明 b 带来了 A 无法生成的方向。
    """
    return rank(augment(A, target)) == rank(A)


def intersect_lines(lines):
    """求同时落在所有直线上的交点；不存在则返回 None。

    lines 的每一项形如 {"a":…, "b":…, "c":…}，表示直线 a·x + b·y = c。
    做法是两两求交，再回代检查是否落在每一条直线上。
    """
    for i in range(len(lines)):
        for j in range(i + 1, len(lines)):
            l1, l2 = lines[i], lines[j]
            d = l1["a"] * l2["b"] - l2["a"] * l1["b"]
            if abs(d) < LINE_EPS:
                continue          # 两直线平行（或重合），换一对
            p = ((l1["c"] * l2["b"] - l2["c"] * l1["b"]) / d,
                 (l1["a"] * l2["c"] - l2["a"] * l1["c"]) / d)
            if all(abs(l["a"] * p[0] + l["b"] * p[1] - l["c"]) < INTERSECT_TOL
                   for l in lines):
                return p
    return None


# ---------------- 自检 ----------------

def _selftest():
    """读本文件末尾的测试向量并与本地算法对照。

    这个自检是给 Python 和 JS 两侧做「同一数学」的证据用的：
    JS 侧的 _selftest() 读同一段向量，两边结果必须一致。
    """
    import json
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, 'mat-vectors.json')
    if not os.path.exists(path):
        print('找不到测试向量：%s' % path)
        return 1
    with open(path, encoding='utf-8') as f:
        payload = json.load(f)
    # 兼容两种结构：{signature, vectors} 或裸数组
    vectors = payload['vectors'] if isinstance(payload, dict) else payload

    bad = []
    for v in vectors:
        kind, args = v['fn'], v['args']
        got = _dispatch(kind, args)
        exp = v['expect']
        if not _same(got, exp):
            bad.append((kind, args, exp, got))
    if bad:
        print('自检失败 %d 项：' % len(bad))
        for kind, args, exp, got in bad[:8]:
            print('  %s(%s) 期望 %s 实得 %s' % (kind, args, exp, got))
        return 1
    print('mat.py 自检通过：%d 组测试向量全部一致' % len(vectors))
    return 0


def _dispatch(kind, args):
    table = {
        'det': lambda a: det(a[0]),
        'rank': lambda a: rank(a[0]),
        'inv2': lambda a: inv2(a[0]),
        'solve2': lambda a: solve2(a[0], a[1]),
        'eigen2': lambda a: eigen2(a[0]),
        'angleBetweenDeg': lambda a: angle_between_deg(a[0], a[1]),
        'onSpan': lambda a: on_span(a[0], a[1]),
        'intersectLines': lambda a: intersect_lines(a[0]),
        'cross': lambda a: cross(a[0], a[1]),
        'mul': lambda a: mul(a[0], a[1]),
        'dot': lambda a: dot(a[0], a[1]),
        'identity': lambda a: identity(a[0]),
        'mulVec': lambda a: mul_vec(a[0], a[1]),
    }
    return table[kind](args)


def _same(a, b):
    """比较结果，浮点按 1e-9 容差，结构必须一致。"""
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        if len(a) != len(b):
            return False
        return all(_same(x, y) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a) != set(b):
            return False
        return all(_same(a[k], b[k]) for k in a)
    if a is None or b is None:
        return a is b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) < 1e-9
    return a == b


if __name__ == '__main__':
    import sys
    sys.exit(_selftest())
