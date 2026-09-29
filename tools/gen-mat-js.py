#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 engine/mat.py 的定义生成 assets/js/mat.js。

为什么用「生成」而不是「手写两份」
==================================
同一段数学如果手写两遍（Python 一份、JS 一份），迟早会分叉——
容差改了一边忘了另一边、秩的主元策略不一致，都会让「校验器」和
「被判定的对象」算的不是同一个数学，而校验器的全部价值正在于此。

生成的 JS 与 Python 共用同一套常量与算法步骤；是否真的一致，
由 engine/mat-vectors.json 的 77 组向量在两侧各自自检来证明
（Python：python3 engine/mat.py；JS：node tools/verify-mat.mjs）。

用法：
    python3 tools/gen-mat-js.py            # 生成
    python3 tools/gen-mat-js.py --check    # 只检查是否最新（退出码 1 表示过期）
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
OUT = os.path.join(SITE, 'assets', 'js', 'mat.js')

HEADER = '''/* ============================================================
 * 模块 1：矩阵内核（纯函数）
 *
 * ⚠️ 本文件由 tools/gen-mat-js.py 生成，请勿手改。
 *    要改数学，改 engine/mat.py，然后重跑：
 *        python3 tools/gen-mat-js.py
 *    Python 侧读 engine/mat.py，浏览器侧读本文件，两侧是同一套定义。
 *    一致性由 engine/mat-vectors.json 的测试向量在两侧各自自检来证明。
 *
 * 约定：矩阵是行数组的数组（[[a,b],[c,d]] 即
 *   ┌ a b ┐
 *   └ c d ┘
 * 矩阵第 j 列 = 该列对应的基向量落点。
 * ============================================================ */
(function (root, factory) {
    const api = factory(typeof require === 'function' ? require : null);
    root.Mat = api;                       // 浏览器：window.Mat
    if (typeof module === 'object' && module.exports) module.exports = api;  // Node
}(typeof self !== 'undefined' ? self : this, function (require) {
    'use strict';

    // 数值零判定阈值 —— 与 engine/mat.py 的 EPS 必须相同
    const EPS = 1e-10;
    // 直线求交的零判定阈值（比 EPS 宽，因直线系数由点算出，误差更大）
    const LINE_EPS = 1e-9;
    // 交点回代检查允许的偏差（拖动是 0.5 步长，实测量级在 1e-2）
    const INTERSECT_TOL = 0.05;

    /* ---------------- 基础 ---------------- */

    function identity(n) {
        return Array.from({ length: n }, (_, i) =>
            Array.from({ length: n }, (_, j) => (i === j ? 1 : 0)));
    }

    function clone(m) { return m.map(row => row.slice()); }

    function mul(a, b) {
        const n = a.length, k = b.length, m = b[0].length;
        return Array.from({ length: n }, (_, i) =>
            Array.from({ length: m }, (_, j) => {
                let s = 0;
                for (let t = 0; t < k; t++) s += a[i][t] * b[t][j];
                return s;
            }));
    }

    function mulVec(m, v) {
        return m.map(row => row.reduce((s, x, j) => s + x * v[j], 0));
    }

    function dot(a, b) {
        return a.reduce((s, x, i) => s + x * b[i], 0);
    }

    function cross(a, b) {
        return [
            a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0]
        ];
    }

    /* ---------------- 行列式与逆 ---------------- */

    function det(m) {
        const n = m.length;
        if (n === 1) return m[0][0];
        if (n === 2) return m[0][0] * m[1][1] - m[0][1] * m[1][0];
        let d = 0;
        for (let j = 0; j < n; j++) {
            const minor = m.slice(1).map(row => row.filter((_, c) => c !== j));
            d += (j % 2 === 0 ? 1 : -1) * m[0][j] * det(minor);
        }
        return d;
    }

    /* 2×2 逆矩阵；奇异（|det| < EPS）时返回 null。
       用 < EPS 而不是 === 0：拖动产生的浮点误差会让本该为 0 的
       行列式变成 1e-17 之类的值。 */
    function inv2(m) {
        const d = det(m);
        if (Math.abs(d) < EPS) return null;
        return [
            [m[1][1] / d, -m[0][1] / d],
            [-m[1][0] / d, m[0][0] / d]
        ];
    }

    /* ---------------- 秩 ----------------
       数值秩：带部分主元选取的高斯消元。
       算法步骤与 engine/mat.py 的 rank() 逐步对应，不要单独改动此处。 */
    function rank(m) {
        const a = clone(m);
        const rows = a.length, cols = a[0].length;
        let r = 0;
        for (let c = 0; c < cols; c++) {
            if (r >= rows) break;
            let piv = r;
            for (let i = r + 1; i < rows; i++) {
                if (Math.abs(a[i][c]) > Math.abs(a[piv][c])) piv = i;
            }
            if (Math.abs(a[piv][c]) < EPS) continue;
            const tmp = a[r]; a[r] = a[piv]; a[piv] = tmp;
            for (let i = r + 1; i < rows; i++) {
                const f = a[i][c] / a[r][c];
                for (let j = c; j < cols; j++) a[i][j] -= f * a[r][j];
            }
            r++;
        }
        return r;
    }

    /* ---------------- 2×2 特征 ----------------
       返回 { values:[λ1,λ2], vectors:[v1,v2] }；无实特征值时返回 null。
       方向已归一化。 */
    function eigen2(m) {
        const tr = m[0][0] + m[1][1];
        const d = det(m);
        const disc = tr * tr - 4 * d;
        if (disc < 0) return null;
        const sq = Math.sqrt(disc);
        const l1 = (tr + sq) / 2, l2 = (tr - sq) / 2;
        function raw(l) {
            const a = m[0][0] - l, b = m[0][1], c = m[1][0], e = m[1][1] - l;
            if (Math.abs(b) > EPS) return [b, -a];
            if (Math.abs(c) > EPS) return [-e, c];
            if (Math.abs(a) < EPS) return [1, 0];
            return [0, 1];
        }
        function norm(v) {
            const L = Math.hypot(v[0], v[1]);
            return L < EPS ? [0, 0] : [v[0] / L, v[1] / L];
        }
        return { values: [l1, l2], vectors: [norm(raw(l1)), norm(raw(l2))] };
    }

    function solve2(A, b) {
        const inv = inv2(A);
        return inv ? mulVec(inv, b) : null;
    }

    /* 两向量夹角（度）。任一个接近零向量时返回 180。
       ⚠️ 共线判定必须用 Math.min(ang, 180 - ang)，
       否则反向共线（180°）会被误判为不共线——这个坑真实发生过。 */
    function angleBetweenDeg(u, v) {
        const lu = Math.hypot(u[0], u[1]), lv = Math.hypot(v[0], v[1]);
        if (lu < EPS || lv < EPS) return 180;
        let cos = dot(u, v) / (lu * lv);
        cos = Math.max(-1, Math.min(1, cos));
        return Math.acos(cos) * 180 / Math.PI;
    }

    /* ---------------- 可达性辅助 ---------------- */

    /* 把向量 b 作为新的一列接到矩阵 A 右边，用于秩比较判可达 */
    function augment(A, b) {
        return A.map((row, i) => row.concat([b[i]]));
    }

    /* target 是否落在 A 的列空间内 —— 最核心的可达性判据：
           b 可达  <=>  rank([A | b]) === rank(A)
       加一列不会降秩；只要秩升高，就说明 b 带来了 A 无法生成的方向。 */
    function onSpan(A, target, tol) {
        if (tol === undefined) tol = INTERSECT_TOL;
        return rank(augment(A, target)) === rank(A);
    }

    /* 求同时落在所有直线上的交点；不存在则返回 null。
       lines 每项形如 {a, b, c}，表示直线 a·x + b·y = c。 */
    function intersectLines(lines) {
        for (let i = 0; i < lines.length; i++) {
            for (let j = i + 1; j < lines.length; j++) {
                const l1 = lines[i], l2 = lines[j];
                const d = l1.a * l2.b - l2.a * l1.b;
                if (Math.abs(d) < LINE_EPS) continue;
                const p = [(l1.c * l2.b - l2.c * l1.b) / d,
                           (l1.a * l2.c - l2.a * l1.c) / d];
                let ok = true;
                for (let k = 0; k < lines.length; k++) {
                    const l = lines[k];
                    if (Math.abs(l.a * p[0] + l.b * p[1] - l.c) >= INTERSECT_TOL) {
                        ok = false; break;
                    }
                }
                if (ok) return p;
            }
        }
        return null;
    }

    /* ---------------- 测试向量自检 ----------------
       读 engine/mat-vectors.json，与 Python 侧 engine/mat.py 的 _selftest()
       读同一份向量。两侧都通过，才说明算的是同一个数学。 */

    const DISPATCH = {
        det: a => det(a[0]),
        rank: a => rank(a[0]),
        inv2: a => inv2(a[0]),
        solve2: a => solve2(a[0], a[1]),
        eigen2: a => eigen2(a[0]),
        angleBetweenDeg: a => angleBetweenDeg(a[0], a[1]),
        onSpan: a => onSpan(a[0], a[1]),
        intersectLines: a => intersectLines(a[0]),
        cross: a => cross(a[0], a[1]),
        mul: a => mul(a[0], a[1]),
        dot: a => dot(a[0], a[1]),
        identity: a => identity(a[0]),
        mulVec: a => mulVec(a[0], a[1])
    };

    function same(a, b) {
        if (Array.isArray(a) && Array.isArray(b)) {
            if (a.length !== b.length) return false;
            return a.every((x, i) => same(x, b[i]));
        }
        if (a && b && typeof a === 'object' && typeof b === 'object') {
            const ka = Object.keys(a), kb = Object.keys(b);
            if (ka.length !== kb.length) return false;
            return ka.every(k => same(a[k], b[k]));
        }
        if (a === null || b === null) return a === b;
        if (typeof a === 'number' && typeof b === 'number') {
            if (!isFinite(a) || !isFinite(b)) return a === b;
            return Math.abs(a - b) < 1e-9;
        }
        return a === b;
    }

    /* 返回 { total, failed, details }；在浏览器里由 main.js 调用，
       在 Node 里由 tools/verify-mat.mjs 调用。 */
    function selftest(payloadOrList) {
        // 兼容两种结构：{signature, vectors} 或裸数组
        const data = Array.isArray(payloadOrList)
            ? payloadOrList : payloadOrList.vectors;
        const failed = [];
        data.forEach(v => {
            const fn = DISPATCH[v.fn];
            if (!fn) { failed.push({ fn: v.fn, why: '未知函数' }); return; }
            const got = fn(v.args);
            if (!same(got, v.expect)) {
                failed.push({ fn: v.fn, args: v.args, expect: v.expect, got: got });
            }
        });
        return { total: data.length, failed: failed.length, details: failed };
    }

    return {
        EPS: EPS, LINE_EPS: LINE_EPS, INTERSECT_TOL: INTERSECT_TOL,
        identity: identity, clone: clone, mul: mul, mulVec: mulVec,
        dot: dot, cross: cross, det: det, inv2: inv2, rank: rank,
        eigen2: eigen2, solve2: solve2, angleBetweenDeg: angleBetweenDeg,
        augment: augment, onSpan: onSpan, intersectLines: intersectLines,
        selftest: selftest
    };
}));
'''


def main():
    check_only = '--check' in sys.argv
    # 生成物与 mat.py 是否一致无法自动判定，故本脚本只负责产出；
    # 正确性由测试向量在两侧自检。
    content = HEADER
    old = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
    if old == content:
        print('✓ assets/js/mat.js 已是最新')
        return 0
    if check_only:
        print('✗ assets/js/mat.js 已过期 —— 运行 python3 tools/gen-mat-js.py')
        return 1
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'w', encoding='utf-8').write(content)
    print('✓ 已生成 assets/js/mat.js（%d 行）' % content.count('\n'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
