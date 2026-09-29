/* ============================================================
 * 线代领域判题插件
 *
 * 本文件里的 13 个判题类型是**线性代数专属**的：
 *   det / rank / intercept / null-space / eigen / in-basis-matrix /
 *   on-span / in-basis / vector-angle / cross-mag / cross-dir / solve / collinear
 * 它们的判据里出现了「秩、行列式、特征值、列空间」这类概念，
 * 换到高等数学就不成立，所以留在这里，不进引擎层。
 *
 * ⚠️ 这些 case **是从 assets/js/engine.js 逐字提取的**（用代码切片，不是手抄）。
 *    engine/core 的判题注册表之前出过一次事故：照记忆重写导致五处偏差，
 *    10 个任务在浏览器侧失败。所以本次改为「机器提取 + 回读校验」。
 *
 * 调用方需要提供 ctx（判题上下文），与引擎层注册表共用同一份：
 *   { matrix, matrixSize, vectors, lines, actionLog, choices, Mat, vecEq }
 *
 * 引擎的 checkTask 会先问浏览器层注册表（7 个领域无关类型），
 * 返回 null 时才落到这里。所以本文件不需要处理那 7 个类型。
 * ============================================================ */
(function (root) {
root.LinalgJudge = (function () {
    'use strict';

    function vecEq(a, b, tol) {
            const t = tol == null ? 0.15 : tol;
            return a.length === b.length && a.every((x, i) => Math.abs(x - b[i]) <= t);
        }

    function intersectPair(l1, l2) {
            const d = l1.a * l2.b - l2.a * l1.b;
            if (Math.abs(d) < 1e-9) return null;
            return [(l1.c * l2.b - l2.c * l1.b) / d, (l1.a * l2.c - l2.a * l1.c) / d];
        }

    function intersectLines(lines, n) {
            const use = lines.slice(0, n);
            for (let i = 0; i < use.length; i++) {
                for (let j = i + 1; j < use.length; j++) {
                    const p = intersectPair(use[i], use[j]);
                    if (!p) continue;
                    const onAll = use.every(l => Math.abs(l.a * p[0] + l.b * p[1] - l.c) < 0.05);
                    if (onAll) return p;
                }
            }
            return null;
        }

    function normVec(v) {
            const L = Math.hypot.apply(null, v) || 1;
            return v.map(x => x / L);
        }

    /* 判定入口：返回 true / false；类型不属本领域时返回 null。
       返回 null 而不是 false，是为了让调用方能区分
       「判定为假」与「这不是我的类型」。 */
    function judge(check, ctx) {
        /* 别名：原代码读的是 App.xxx 与全局 Mat，这里改成从 ctx 取。
           领域插件不依赖任何全局，因此可以在 Node 里独立加载与测试。 */
        const App = ctx;
        const Mat = ctx.Mat;
        switch (check.type) {

            case 'det': {
                if (!App.matrix) return false;
                const d = Mat.det(App.matrix);
                if (check.op === 'eq') return Math.abs(d - check.value) <= (check.tol || 0.05);
                if (check.op === 'lt') return d < check.value;
                if (check.op === 'gt') return d > check.value;
                return false;
            }

            case 'rank': {
                if (!App.matrix) return false;
                return Mat.rank(App.matrix) === check.value;
            }

            /* 行图像：拖动 v 去命中若干条直线的交点。
               先把直线两两求交，取那个同时落在所有直线上的点。 */
            case 'intercept': {
                const v = App.vectors.find(x => x.id === (check.target || 'v'));
                if (!v || !App.lines || App.lines.length < 2) return false;
                const p = intersectLines(App.lines, check.maxLines || App.lines.length);
                if (!p) return false;
                return vecEq(v.data, p, check.tol);
            }

            /* v 是否落在零空间里：A·v ≈ 0，且 v 不是零向量 */
            case 'null-space': {
                const v = App.vectors.find(x => x.id === (check.target || 'v'));
                if (!v || !App.matrix) return false;
                if (Math.hypot.apply(null, v.data) < (check.minLen || 0.25)) return false;
                const av = Mat.mulVec(App.matrix, v.data);
                if (Math.hypot.apply(null, av) > (check.tol || 0.08)) return false;
                if (check.dir) {
                    const d = Math.abs(Mat.dot(normVec(v.data), normVec(check.dir)));
                    if (d < (check.minCos || 0.98)) return false;
                }
                return true;
            }

            /* 特征值：v 与 Av 共线，且缩放倍数等于目标 λ。
               λ = (Av·v)/(v·v)，对共线情形（同向或反向）都成立。 */
            case 'eigen': {
                const v = App.vectors.find(x => x.id === (check.target || 'v'));
                if (!v || !App.matrix) return false;
                const vv = Mat.dot(v.data, v.data);
                if (vv < 1e-6) return false;
                const av = Mat.mulVec(App.matrix, v.data);
                const lam = Mat.dot(av, v.data) / vv;
                if (Math.abs(lam - check.value) > (check.tol || 0.12)) return false;
                // 共线包含同向（0°）与反向（180°）两种情况，
                // angleBetweenDeg 对反向给 180，所以要折回锐角再比
                const ang = Mat.angleBetweenDeg(v.data, av);
                return Math.min(ang, 180 - ang) <= (check.tolDeg || 4);
            }

            /* 在新基 P 下看当前变换：要求 P⁻¹AP 等于目标矩阵 */
            case 'in-basis-matrix': {
                if (!App.matrix || !check.basis) return false;
                const Pi = Mat.inv2(check.basis);
                if (!Pi) return false;
                const got = Mat.mul(Mat.mul(Pi, App.matrix), check.basis);
                const tol = check.tol == null ? 0.08 : check.tol;
                return check.matrix.every((row, i) =>
                    row.every((x, j) => Math.abs(got[i][j] - x) <= tol));
            }

            /* v 是否落在矩阵列张成的（低维）子空间里。
               做法：把 v 并成矩阵的最后一列，比较秩有没有变大。
               秩不变 ⇒ v 在列空间里；秩变大 ⇒ v 在列空间外。
               这个判定对 2×2 与 3×3 都成立。 */
            case 'on-span': {
                const v = App.vectors.find(x => x.id === (check.target || 'v'));
                if (!v || !App.matrix) return false;
                const m = App.matrix;
                const aug = m.map((row, i) => row.concat([v.data[i]]));
                const grew = Mat.rank(aug) > Mat.rank(m);
                if (check.op === 'in') return !grew;
                if (check.op === 'out') return grew;
                return false;
            }

            case 'in-basis': {
                // v 在新基（当前矩阵两列）下的坐标 = B⁻¹v
                const v = App.vectors.find(x => x.id === (check.target || 'v'));
                if (!v || !App.matrix || App.matrixSize !== 2) return false;
                const c = Mat.solve2(App.matrix, v.data);
                return !!c && vecEq(c, check.to, check.tol);
            }

            /* 两向量的夹角：可要求等于目标角度（带容差），也可要求两者都是单位向量 */
            case 'vector-angle': {
                const a = App.vectors.find(x => x.id === check.a);
                const b = App.vectors.find(x => x.id === check.b);
                if (!a || !b) return false;
                const la = Math.hypot.apply(null, a.data);
                const lb = Math.hypot.apply(null, b.data);
                if (la < 1e-6 || lb < 1e-6) return false;
                if (check.unit && (Math.abs(la - 1) > (check.unitTol || 0.06)
                                || Math.abs(lb - 1) > (check.unitTol || 0.06))) return false;
                const ang = Mat.angleBetweenDeg(a.data, b.data);
                return Math.abs(ang - check.value) <= (check.tol || 5);
            }

            case 'cross-mag': {
                if (!App.matrix || App.matrixSize !== 3) return false;
                const a = App.matrix.map(r => r[check.colA]);
                const b = App.matrix.map(r => r[check.colB]);
                const mag = Math.hypot.apply(null, Mat.cross(a, b));
                if (check.op === 'eq') return Math.abs(mag - check.value) <= (check.tol || 0.05);
                if (check.op === 'lt') return mag < check.value;
                if (check.op === 'gt') return mag > check.value;
                return false;
            }

            /* a×b 的方向是否与给定方向一致（用归一化后的点积 ≥ minCos 判定） */
            case 'cross-dir': {
                if (!App.matrix || App.matrixSize !== 3) return false;
                const a = App.matrix.map(r => r[check.colA]);
                const b = App.matrix.map(r => r[check.colB]);
                const c = Mat.cross(a, b);
                const L = Math.hypot(c[0], c[1], c[2]);
                if (L < 1e-6) return false;
                const u = [c[0] / L, c[1] / L, c[2] / L];
                const tl = Math.hypot.apply(null, check.dir) || 1;
                const t = check.dir.map(x => x / tl);
                const d = u[0] * t[0] + u[1] * t[1] + u[2] * t[2];
                return d >= (check.minCos == null ? 0.999 : check.minCos);
            }

            case 'solve': {
                const v = App.vectors.find(x => x.id === 'v');
                if (!v || !App.matrix) return false;
                return vecEq(Mat.mulVec(App.matrix, v.data), check.to, check.tol);
            }

            case 'collinear': {
                const v = App.vectors.find(x => x.id === 'v');
                if (!v || !App.matrix) return false;
                const av = Mat.mulVec(App.matrix, v.data);
                if (Math.hypot(v.data[0], v.data[1]) < 0.25) return false;
                if (Math.hypot(av[0], av[1]) < 1e-6) return false;
                const ang = Mat.angleBetweenDeg(v.data, av);
                return Math.min(ang, 180 - ang) <= (check.tolDeg || 4);
            }
            default:
                return null;
        }
    }

    return { judge: judge };
})();
}(typeof globalThis !== 'undefined' ? globalThis : this));
