/* ============================================================
 * 模块 1：矩阵内核（纯函数）
 * 自研实现。约定：矩阵是行数组的数组（[[a,b],[c,d]] 即
 *   ┌ a b ┐
 *   └ c d ┘
 * 矩阵第 j 列 = 该列对应的基向量落点。
 * ============================================================ */
window.Mat = (function () {
    'use strict';

    const EPS = 1e-10;

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

    function inv2(m) {
        const d = det(m);
        if (Math.abs(d) < EPS) return null;
        return [
            [m[1][1] / d, -m[0][1] / d],
            [-m[1][0] / d, m[0][0] / d]
        ];
    }

    function rank(m) {
        const a = m.map(row => row.slice());
        const rows = a.length, cols = a[0].length;
        let r = 0;
        for (let c = 0; c < cols && r < rows; c++) {
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

    /* 2×2 实特征值与特征方向；无实特征值时返回 null。
       返回 { values:[λ1,λ2], vectors:[v1,v2] }，方向已归一化。 */
    function eigen2(m) {
        const tr = m[0][0] + m[1][1];
        const d = det(m);
        const disc = tr * tr - 4 * d;
        if (disc < 0) return null;
        const sq = Math.sqrt(disc);
        const l1 = (tr + sq) / 2, l2 = (tr - sq) / 2;
        const raw = (l) => {
            const a = m[0][0] - l, b = m[0][1], c = m[1][0], e = m[1][1] - l;
            if (Math.abs(b) > EPS) return [b, -a];
            if (Math.abs(c) > EPS) return [-e, c];
            if (Math.abs(a) < EPS) return [1, 0];
            return [0, 1];
        };
        const norm = (v) => {
            const L = Math.hypot(v[0], v[1]);
            return L < EPS ? [0, 0] : [v[0] / L, v[1] / L];
        };
        return { values: [l1, l2], vectors: [norm(raw(l1)), norm(raw(l2))] };
    }

    function solve2(A, b) {
        const inv = inv2(A);
        return inv ? mulVec(inv, b) : null;
    }

    /* v 与 Av 的夹角（度），用于特征向量判定 */
    function angleBetweenDeg(u, v) {
        const lu = Math.hypot(u[0], u[1]), lv = Math.hypot(v[0], v[1]);
        if (lu < EPS || lv < EPS) return 180;
        let cos = dot(u, v) / (lu * lv);
        cos = Math.max(-1, Math.min(1, cos));
        return Math.acos(cos) * 180 / Math.PI;
    }

    return {
        EPS, identity, clone, mul, mulVec, dot, cross,
        det, inv2, rank, eigen2, solve2, angleBetweenDeg
    };
})();
