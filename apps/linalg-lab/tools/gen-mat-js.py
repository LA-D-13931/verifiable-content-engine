#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 engine-core/mat.py 的**等价实现**写成 engine-core/mat.js。

⚠️ 核实记录（2026-10）：本脚本**不解析 mat.py**。整份 JS 是下面 HEADER 里的
一个模板字符串，main() 只是把它写出去。所以：

    「两侧同源」不是由本脚本保证的，而是由 engine-core/mat-vectors.json
    的测试向量在两侧各自自检保证的——向量的期望值来自 mat.py，所以
    只改 mat.py 不改模板（或反之）会被自检抓住。

历史上本脚本的注释写成「从 mat.py 生成」「改数学改 mat.py 然后重跑生成器」，
这是**不成立的**：照那句话做会把浏览器侧悄悄留在旧数学上。真正的纪律是
**两处都改**：engine-core/mat.py 与下面的 HEADER 模板，然后按序重跑
gen-mat-vectors.py（期望值取自 mat.py）与 gen-mat-js.py（写出模板）。

用法：
    python3 tools/gen-mat-js.py            # 生成
    python3 tools/gen-mat-js.py --check    # 只检查是否最新（退出码 1 表示过期）
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# --- 路径解析：统一走 tools/paths.py，不在各工具里数层数 ---
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import APP as SITE, ENGINE, REPO, WORKSPACE as _WS   # noqa: E402

OUT = os.path.join(ENGINE, 'mat.js')

HEADER = '''/* ============================================================
 * 模块 1：矩阵内核（纯函数）
 *
 * ⚠️ 本文件的内容由 tools/gen-mat-js.py 里的模板写出——那个脚本**不解析 mat.py**。
 *    改数学必须两处都改：
 *        engine-core/mat.py                （Python 侧权威实现）
 *        gen-mat-js.py 里的 HEADER 模板     （浏览器侧）
 *    然后按序重跑：
 *        python3 tools/gen-mat-vectors.py   # 期望值由 mat.py 算出
 *        python3 tools/gen-mat-js.py        # 把模板写成本文件
 *    只改一处会被向量自检抓住（期望值来自 mat.py），但不会被生成器抓住。
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

    // 数值零判定阈值 —— 与 engine-core/mat.py 的 EPS 必须相同
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

    /* 矩阵的数值尺度：绝对值最大的元素。全零矩阵取 1（避免零尺度）。
       容差必须随尺度缩放，否则「秩」会随 A→kA 变化，而秩是尺度无关的量
       （实测过：同一个近奇异矩阵乘 1e6，旧实现给出的秩从 1 变成 2）。 */
    function scale(m) {
        let s = 0;
        for (let i = 0; i < m.length; i++) {
            for (let j = 0; j < m[i].length; j++) {
                const v = Math.abs(m[i][j]);
                if (v > s) s = v;
            }
        }
        return s > 0 ? s : 1;
    }

    /* 零政策阈值：EPS × 尺度^order。
       order = 1：消元后的主元（一阶量，A→kA 时按 k 增长）
       order = n：n 阶行列式（按 k^n 增长）
       同一个 EPS 用在不同阶的量上会自相矛盾，见 mat-vectors.json 的 near_singular。 */
    function zeroThreshold(m, order) {
        return EPS * Math.pow(scale(m), order);
    }

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

    function detRaw(m) {
        const n = m.length;
        if (n === 1) return m[0][0];
        if (n === 2) return m[0][0] * m[1][1] - m[0][1] * m[1][0];
        let d = 0;
        for (let j = 0; j < n; j++) {
            const minor = m.slice(1).map(row => row.filter((_, c) => c !== j));
            d += (j % 2 === 0 ? 1 : -1) * m[0][j] * detRaw(minor);
        }
        return d;
    }

    /* 行列式；绝对值低于零政策阈值（EPS × 尺度^n）时返回 0。
       夹取是为了让「奇异」在整个原语层只有一个定义处：否则同一个矩阵上
       会出现「det ≠ 0（可逆）而 rank < n（亏秩）」的自相矛盾判定。 */
    function det(m) {
        const d = detRaw(m);
        return Math.abs(d) < zeroThreshold(m, m.length) ? 0 : d;
    }

    /* 2×2 逆矩阵；按同一零政策判定为奇异时返回 null。
       这里不再单独写阈值：det() 已按零政策夹取，只需判断是否为 0。 */
    function inv2(m) {
        const d = det(m);
        if (d === 0) return null;
        return [
            [m[1][1] / d, -m[0][1] / d],
            [-m[1][0] / d, m[0][0] / d]
        ];
    }

    /* ---------------- 秩 ----------------
       数值秩：带部分主元选取的高斯消元。
       主元是一阶量，故阈值取 EPS × 尺度（zeroThreshold(m, 1)），而不是绝对 EPS——
       绝对 EPS 会让秩随尺度漂移（实测：同一个近奇异矩阵乘 1e6 后秩从 1 变 2）。
       阈值只按原矩阵算一次，消元过程中不变。
       算法步骤与 engine-core/mat.py 的 rank() 逐步对应，两处必须同步改。 */
    function rank(m) {
        const a = clone(m);
        const rows = a.length, cols = a[0].length;
        const thr = zeroThreshold(m, 1);
        let r = 0;
        for (let c = 0; c < cols; c++) {
            if (r >= rows) break;
            let piv = r;
            for (let i = r + 1; i < rows; i++) {
                if (Math.abs(a[i][c]) > Math.abs(a[piv][c])) piv = i;
            }
            if (Math.abs(a[piv][c]) < thr) continue;
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
       读 engine-core/mat-vectors.json，与 Python 侧 engine-core/mat.py 的 _selftest()
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
        identity: identity, clone: clone, scale: scale,
        zeroThreshold: zeroThreshold, mul: mul, mulVec: mulVec,
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
        print('✓ engine-core/mat.js 已是最新')
        return 0
    if check_only:
        print('✗ engine-core/mat.js 已过期 —— 运行 python3 tools/gen-mat-js.py')
        return 1
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'w', encoding='utf-8').write(content)
    print('✓ 已生成 engine-core/mat.js（%d 行）' % content.count('\n'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
