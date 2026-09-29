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


    /* ---------------- 诊断补齐 ----------------
       下面 13 个 case 是从 engine.js 逐字提取的，内部只 `return true/false`，
       不带原因与证书。这与引擎层（返回 {pass, reason, certificate} 三元组）
       不一致，导致**领域判题拿不到「为什么判不过」的表达能力**——
       而可解释诊断正是本项目的核心主张之一。

       做法：不改那 13 段已验证的代码，而是在这里按类型补一层诊断。
       好处是不碰已验证的逻辑；代价是诊断与判定分处两地，
       所以有一条自动检查（tools/verify-diagnostics.mjs）盯着覆盖率，
       并要求「判不过必须给出原因」。 */

    /* 把数值格式化成短字符串 */
    function n2(v) {
        return (typeof v === 'number' && isFinite(v)) ? (Math.round(v * 1000) / 1000) : String(v);
    }

    const DIAGNOSE = {
        det: function (check, ctx) {
            const d = ctx.Mat.det(ctx.matrix);
            return {
                reason: '当前 det = ' + n2(d) + '，要求 ' + check.op + ' ' + check.value
                        + (check.tol != null ? '（容差 ' + check.tol + '）' : ''),
                certificate: { determinant: d, op: check.op, target: check.value }
            };
        },
        rank: function (check, ctx) {
            const r = ctx.Mat.rank(ctx.matrix);
            return {
                reason: '当前秩 = ' + r + '，要求 ' + (check.op || 'eq') + ' ' + check.value,
                certificate: { rank: r, op: check.op || 'eq', target: check.value }
            };
        },
        solve: function (check, ctx) {
            const v = ctx.vectors.find(x => x.id === 'v');
            const av = (v && ctx.matrix) ? ctx.Mat.mulVec(ctx.matrix, v.data) : null;
            return {
                reason: av ? '当前 Av = ' + JSON.stringify(av.map(n2)) + '，目标是 '
                             + JSON.stringify(check.to) : '缺少向量 v 或矩阵',
                certificate: av ? { av: av, target: check.to } : null
            };
        },
        collinear: function (check, ctx) {
            const v = ctx.vectors.find(x => x.id === 'v');
            const av = (v && ctx.matrix) ? ctx.Mat.mulVec(ctx.matrix, v.data) : null;
            return {
                reason: av ? 'v 与 Av 不共线（要求共线，容差 ' + (check.tolDeg || 4) + '°）'
                           : '缺少向量 v 或矩阵',
                certificate: av ? { v: v.data, av: av } : null
            };
        },
        eigen: function (check, ctx) {
            const v = ctx.vectors.find(x => x.id === (check.target || 'v'));
            if (!v || !ctx.matrix) return { reason: '缺少向量 v 或矩阵', certificate: null };
            const av = ctx.Mat.mulVec(ctx.matrix, v.data);
            const vv = ctx.Mat.dot(v.data, v.data);
            const lam = vv > 1e-12 ? ctx.Mat.dot(av, v.data) / vv : NaN;
            return {
                reason: '当前缩放倍数 λ = ' + n2(lam) + '，目标是 ' + check.value
                        + '（容差 ' + (check.tol || 0.12) + '）',
                certificate: { lambda: lam, target: check.value, av: av }
            };
        },
        'on-span': function (check, ctx) {
            const v = ctx.vectors.find(x => x.id === (check.target || 'v'));
            if (!v || !ctx.matrix) return { reason: '缺少向量 v 或矩阵', certificate: null };
            const m = ctx.matrix;
            const aug = m.map((row, i) => row.concat([v.data[i]]));
            const rA = ctx.Mat.rank(m), rAug = ctx.Mat.rank(aug);
            return {
                reason: 'rank(A) = ' + rA + '，rank([A|v]) = ' + rAug
                        + (rAug > rA ? '（秩升高说明 v 不在列空间内）' : '（秩不变说明 v 在列空间内）'),
                certificate: { rankA: rA, rankAug: rAug }
            };
        },
        'in-basis': function (check, ctx) {
            const v = ctx.vectors.find(x => x.id === (check.target || 'v'));
            if (!v || !ctx.matrix) return { reason: '缺少向量 v 或矩阵', certificate: null };
            const c = ctx.Mat.solve2(ctx.matrix, v.data);
            return {
                reason: c ? '在新基下的坐标是 ' + JSON.stringify(c.map(n2)) + '，目标是 '
                            + JSON.stringify(check.to) : '当前基不可逆，坐标无法定义',
                certificate: c ? { coords: c, target: check.to } : null
            };
        },
        'in-basis-matrix': function (check, ctx) {
            if (!ctx.matrix || !check.basis) return { reason: '缺少矩阵或 basis', certificate: null };
            const Pi = ctx.Mat.inv2(check.basis);
            if (!Pi) return { reason: 'basis 不可逆，P⁻¹ 不存在', certificate: null };
            const got = ctx.Mat.mul(ctx.Mat.mul(Pi, ctx.matrix), check.basis);
            return {
                reason: '当前 P⁻¹AP = ' + JSON.stringify(got.map(r => r.map(n2)))
                        + '，目标是 ' + JSON.stringify(check.matrix),
                certificate: { got: got, target: check.matrix }
            };
        },
        'vector-angle': function (check, ctx) {
            const a = ctx.vectors.find(x => x.id === check.a);
            const b = ctx.vectors.find(x => x.id === check.b);
            if (!a || !b) return { reason: '找不到向量 ' + check.a + ' 或 ' + check.b, certificate: null };
            const ang = ctx.Mat.angleBetweenDeg(a.data, b.data);
            return {
                reason: '当前夹角 ' + n2(ang) + '°，目标是 ' + check.value + '°（容差 '
                        + (check.tol || 5) + '°）',
                certificate: { angle: ang, target: check.value }
            };
        },
        'cross-mag': function (check, ctx) {
            if (!ctx.matrix) return { reason: '缺少矩阵', certificate: null };
            const a = ctx.matrix.map(r => r[check.colA]);
            const b = ctx.matrix.map(r => r[check.colB]);
            const mag = Math.hypot.apply(null, ctx.Mat.cross(a, b));
            return {
                reason: '当前 |a×b| = ' + n2(mag) + '，要求 ' + check.op + ' ' + check.value,
                certificate: { magnitude: mag, op: check.op, target: check.value }
            };
        },
        'cross-dir': function (check, ctx) {
            if (!ctx.matrix) return { reason: '缺少矩阵', certificate: null };
            const a = ctx.matrix.map(r => r[check.colA]);
            const b = ctx.matrix.map(r => r[check.colB]);
            const c = ctx.Mat.cross(a, b);
            const L = Math.hypot(c[0], c[1], c[2]);
            const u = L > 1e-12 ? [c[0] / L, c[1] / L, c[2] / L] : null;
            const tl = Math.hypot.apply(null, check.dir) || 1;
            const t = check.dir.map(x => x / tl);
            const d = u ? (u[0] * t[0] + u[1] * t[1] + u[2] * t[2]) : null;
            return {
                reason: u ? 'a×b 方向与目标方向余弦 ' + n2(d) + '，要求 ≥ '
                            + (check.minCos == null ? 0.999 : check.minCos) : 'a×b 为零向量，方向未定义',
                certificate: u ? { direction: u, target: t, cos: d } : null
            };
        },
        intercept: function (check, ctx) {
            const v = ctx.vectors.find(x => x.id === (check.target || 'v'));
            return {
                reason: '当前 v = ' + (v ? JSON.stringify(v.data.map(n2)) : '(无)')
                        + '，需要落在若干直线的公共交点上',
                certificate: v ? { v: v.data, lineCount: (ctx.lines || []).length } : null
            };
        },
        'null-space': function (check, ctx) {
            const v = ctx.vectors.find(x => x.id === (check.target || 'v'));
            if (!v || !ctx.matrix) return { reason: '缺少向量 v 或矩阵', certificate: null };
            const av = ctx.Mat.mulVec(ctx.matrix, v.data);
            return {
                reason: '当前 |Av| = ' + n2(Math.hypot.apply(null, av))
                        + '，要求接近 0（容差 ' + (check.tol || 0.08) + '）',
                certificate: { av: av, norm: Math.hypot.apply(null, av) }
            };
        }
    };

    /* 判定入口。返回三态：
         · null                                  —— 不是本领域的类型
         · { pass:true,  reason:'', certificate } —— 判过
         · { pass:false, reason:'…', certificate } —— 判不过（带原因）
       下面 13 个 case 从 engine.js 逐字提取，内部仍写 `return true/false`，
       由 judgeRaw 之后统一包装成三元组，避免改动那 13 段已验证的代码。 */
    function judgeRaw(check, ctx) {
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

    /* 包装：把布尔值规范化成 { pass, reason, certificate } 三元组，
       与引擎层注册表的返回结构一致 —— 否则领域判题拿不到
       「为什么判不过」的表达能力，而可解释诊断正是本项目的核心主张之一。

       注：certificate 目前多为 null。逐个 case 补证书是后续工作；
       先保证**结构一致**，再逐步填内容。 */
    function judge(check, ctx) {
        const r = judgeRaw(check, ctx);
        if (r === null) return null;
        const pass = (typeof r === 'boolean') ? r : !!r.pass;
        if (pass) return { pass: true, reason: '', certificate: null };

        /* 判不过：补上原因与证书。诊断与判定分处两地是刻意的取舍
           （不碰那 13 段已验证的代码），覆盖率由 verify-diagnostics.mjs 盯着。 */
        const diag = DIAGNOSE[check.type];
        if (diag && ctx.matrix !== undefined) {
            try {
                const d = diag(check, ctx) || {};
                return { pass: false, reason: d.reason || '', certificate: d.certificate || null };
            } catch (e) {
                return { pass: false, reason: '（诊断生成失败：' + e.message + '）', certificate: null };
            }
        }
        return { pass: false, reason: '', certificate: null };
    }

    const api = { judge: judge, judgeRaw: judgeRaw };
    /* Node 下同时导出，便于离线回归测试直接 require。 */
    if (typeof module === 'object' && module.exports) module.exports = api;
    return api;
})();
}(typeof globalThis !== 'undefined' ? globalThis : this));
