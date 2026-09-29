/* ============================================================
 * 判题注册表（引擎层）
 *
 * 定位：这里只放**与学科无关**的判题类型——数值命中、矩阵相等、
 * 点积、选择题、动作序列。它们不需要知道「什么是行列式」。
 *
 * 学科专属的判题类型（det / rank / eigen / on-span / cross-dir …）
 * 留在 engine.js 里，将来迁到 domains/<科目>/。分界线是：
 *
 *     判据里出现「秩、行列式、特征值、列空间」等概念 → 领域专属
 *     判据只是「数值相等 / 位置命中 / 序列匹配」      → 引擎层
 *
 * ⚠️ 本文件必须与 engine.js 里对应的 case **逐字对齐**。
 *    第一版是「照着记忆重写」的，结果五处偏差：
 *      · actions 用了 App.log（对象），原实现是 App.actionLog（数组）
 *      · actions 漏掉 check.ordered 的顺序匹配逻辑
 *      · dot 写成 check.target / check.with，原实现是 check.a / check.b
 *      · dot 漏掉 op 的 lt / gt 两种比较
 *      · choice 漏掉 taskId != null 的判断
 *    教训：**平移代码必须照源码逐行译，不能凭印象重写。**
 *    平移是否忠实，由 tools/verify-registry.mjs 的离线用例与浏览器侧的
 *    verify-actions / smoke 共同把关。
 *
 * 每个处理器返回 { pass, reason, certificate }：
 *   · pass        —— 是否通过
 *   · reason      —— 不通过时的一句话原因（给人看）
 *   · certificate —— 判定依据（见证或反证），把诊断质量变成可核对的东西
 *
 * 加载顺序：必须在 engine.js 之前（engine.js 读 window.CheckRegistry）。
 * ============================================================ */
(function (root) {
root.CheckRegistry = (function () {
    'use strict';

    const handlers = Object.create(null);

    function register(type, fn) { handlers[type] = fn; }
    function get(type) { return handlers[type] || null; }
    function types() { return Object.keys(handlers); }

    const ok = (cert)         => ({ pass: true,  reason: '', certificate: cert });
    const bad = (reason, cert) => ({ pass: false, reason: reason, certificate: cert });

    /* 把向量格式化成 (1, 2) 这样的短字符串，用于诊断信息 */
    function fmt(v) {
        return '(' + v.map(x => (Math.round(x * 100) / 100)).join(', ') + ')';
    }

    /* 数值比较：与原实现一致；op 不是 eq/lt/gt 时返回 false */
    function cmp(got, op, value, tol) {
        const t = tol == null ? 0.05 : tol;
        if (op === 'eq') return Math.abs(got - value) <= t;
        if (op === 'lt') return got < value;
        if (op === 'gt') return got > value;
        return false;
    }

    /* ---------------- 领域无关的判题类型 ---------------- */

    /* 指定 id 的向量是否停在目标位置 */
    register('vector-at', function (check, ctx) {
        const v = ctx.vectors.find(x => x.id === check.target);
        if (!v) return bad('找不到向量 ' + check.target);
        const hit = ctx.vecEq(v.data, check.to, check.tol);
        return hit ? ok({ witness: v.data })
                   : bad('向量 ' + check.target + ' 在 ' + fmt(v.data) +
                         '，目标是 ' + fmt(check.to),
                         { current: v.data, target: check.to });
    });

    /* 变换后的向量 Av 是否命中目标 */
    register('av-at', function (check, ctx) {
        const v = ctx.vectors.find(x => x.id === 'v');
        if (!v || !ctx.matrix) return bad('缺少向量 v 或矩阵');
        const av = ctx.Mat.mulVec(ctx.matrix, v.data);
        const hit = ctx.vecEq(av, check.to, check.tol);
        return hit ? ok({ witness: v.data, image: av })
                   : bad('Av = ' + fmt(av) + '，目标是 ' + fmt(check.to),
                         { current: av, target: check.to });
    });

    /* 矩阵的第 col 列是否等于目标向量 */
    register('matrix-col-at', function (check, ctx) {
        if (!ctx.matrix) return bad('当前没有矩阵');
        const col = ctx.matrix.map(r => r[check.col]);
        const hit = ctx.vecEq(col, check.to, check.tol);
        return hit ? ok({ col: check.col })
                   : bad('第 ' + (check.col + 1) + ' 列是 ' + fmt(col) +
                         '，目标是 ' + fmt(check.to),
                         { current: col, target: check.to });
    });

    /* 整个矩阵是否等于目标矩阵（逐元素，容差默认 0.05） */
    register('match-matrix', function (check, ctx) {
        if (!ctx.matrix) return bad('当前没有矩阵');
        const tol = check.tol == null ? 0.05 : check.tol;
        let worst = 0, at = null;
        check.matrix.forEach((row, i) => row.forEach((x, j) => {
            const d = Math.abs(ctx.matrix[i][j] - x);
            if (d > worst) { worst = d; at = [i, j]; }
        }));
        return worst <= tol
            ? ok({ maxDeviation: worst })
            : bad('第 ' + (at[0] + 1) + ' 行第 ' + (at[1] + 1) + ' 列差 ' +
                  (Math.round(worst * 100) / 100) + '，超出容差 ' + tol,
                  { maxDeviation: worst, at: at });
    });

    /* 两指定向量 id 的点积；op 支持 eq / lt / gt（与原实现一致） */
    register('dot', function (check, ctx) {
        const a = ctx.vectors.find(x => x.id === check.a);
        const b = ctx.vectors.find(x => x.id === check.b);
        if (!a || !b) return bad('找不到向量 ' + (check.a || '?') + ' 或 ' + (check.b || '?'));
        const d = ctx.Mat.dot(a.data, b.data);
        return cmp(d, check.op, check.value, check.tol)
            ? ok({ value: d })
            : bad('点积是 ' + (Math.round(d * 100) / 100) +
                  '，条件是 ' + (check.op || 'eq') + ' ' + check.value,
                  { current: d, target: check.value, op: check.op });
    });

    /* 辨析题：只有当这一次的选择确实属于这道题时才算数。
       同一关可能有两道辨析题，必须用 taskId 区分，否则互相干扰。 */
    register('choice', function (check, ctx) {
        if (ctx.taskId == null) return bad('缺少任务标识，无法判断这是哪一道题');
        const picked = ctx.choices[ctx.taskId];
        if (picked == null) return bad('还没有选择');
        return picked === check.correct
            ? ok({ picked: picked })
            : bad('选了第 ' + (picked + 1) + ' 项，不是正确答案',
                  { picked: picked, correct: check.correct });
    });

    /* 过程型任务：声明的动作必须都产生过可观测事件。
       ordered 为真时要求按序出现（子序列匹配，允许中间夹别的动作）。
       这一类专门捕捉「按钮点了但没写日志」导致的恒假任务。 */
    register('actions', function (check, ctx) {
        const all = check.all || [];
        const log = ctx.actionLog || [];
        if (check.ordered) {
            let pos = 0;
            for (const a of log) {
                if (a === all[pos]) pos++;
                if (pos >= all.length) return ok({ order: all });
            }
            return bad('顺序还没走完，已完成 ' + pos + ' / ' + all.length + ' 步',
                       { matched: pos, need: all.length });
        }
        const missing = all.filter(n => !log.includes(n));
        return missing.length === 0
            ? ok({ done: all })
            : bad('还缺少这些动作：' + missing.join('、'), { missing: missing });
    });

    const api = {
        register: register,
        get: get,
        types: types,
        /* 供测试直接调用：不依赖 App，只依赖传入的 ctx */
        run: function (check, ctx) {
            const fn = get(check.type);
            if (!fn) return null;      // 未注册 → 由调用方决定怎么处理
            return fn(check, ctx);
        }
    };
    if (typeof module === 'object' && module.exports) module.exports = api;
    return api;
})();
}(typeof globalThis !== 'undefined' ? globalThis : this));
