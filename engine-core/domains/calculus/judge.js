/* ============================================================
 * 高等数学领域判题插件
 *
 * 这是**第二个科目**，用于检验引擎接口的可复用性
 * （见 engine/API_如何新增科目.md）。
 *
 * 三个判题类型，都围绕「连续参数空间」这一本项目关注的形态：
 *
 *   calc-limit       ε-δ 极限：用户拖动 δ，要求对邻域内所有 x 都有 |f(x)−L| < ε
 *   calc-derivative  数值导数 = 目标值（用户拖动 h，要求割线斜率趋近目标）
 *   calc-monotone    单调区间：给定区间内导数恒正（或恒负）
 *
 * 为什么这三个能体现「连续参数可达性」：
 *   · calc-limit 若对给定 ε 找不到任何 δ 成立，则该教学任务**根本不可达**
 *     —— 这正是引擎要判定的退化情形（解集为空）
 *   · calc-derivative 的目标值若超出函数在该点的可导范围，同样不可达
 *   · calc-monotone 若区间内存在驻点，则「恒正」不可达
 *
 * 表达式表示法：只支持程序构造的结构化形式，不支持解析字符串——
 * 这样既能被 JS 求值，也能被 Python 侧以同样语义求值，两侧可互相校验。
 *   {op:'var'}                          → x
 *   {op:'const', v:2}                   → 2
 *   {op:'add'|'sub'|'mul'|'div'|'pow', a, b}
 *   {op:'sin'|'cos'|'exp'|'log'|'sqrt', a}
 * ============================================================ */
(function (root) {
root.CalculusJudge = (function () {
    'use strict';

    const EPS = 1e-12;

    /* 求值：把结构化表达式在 x 处求值 */
    function evalF(expr, x) {
        if (expr == null) return NaN;
        switch (expr.op) {
            case 'var':   return x;
            case 'const': return expr.v;
            case 'add':   return evalF(expr.a, x) + evalF(expr.b, x);
            case 'sub':   return evalF(expr.a, x) - evalF(expr.b, x);
            case 'mul':   return evalF(expr.a, x) * evalF(expr.b, x);
            case 'div':   return evalF(expr.a, x) / evalF(expr.b, x);
            case 'pow':   return Math.pow(evalF(expr.a, x), evalF(expr.b, x));
            case 'sin':   return Math.sin(evalF(expr.a, x));
            case 'cos':   return Math.cos(evalF(expr.a, x));
            case 'exp':   return Math.exp(evalF(expr.a, x));
            case 'log':   return Math.log(evalF(expr.a, x));
            case 'sqrt':  return Math.sqrt(evalF(expr.a, x));
            default:      return NaN;
        }
    }

    const ok  = (cert)         => ({ pass: true,  reason: '', certificate: cert });
    const bad = (reason, cert) => ({ pass: false, reason: reason, certificate: cert });

    const num = (v) => Math.round(v * 1e6) / 1e6;

    /* ---------------- ε-δ 极限 ----------------
       用户拖动 δ。判定：对采样邻域内所有 x，|f(x) − L| < ε。
       若对任何 δ 都无法成立，该任务不可达 —— 引擎报「解集为空」。 */
    function checkLimit(check, ctx) {
        const delta = ctx.param;
        if (typeof delta !== 'number' || !isFinite(delta)) {
            return bad('参数 δ 还不是一个有效数值', { delta: delta });
        }
        if (delta <= 0) return bad('δ 必须为正数', { delta: delta });

        const { expr, at: x0, value: L, epsilon, tol } = check;
        const t = tol == null ? epsilon : tol;
        const N = check.samples || 400;
        let worst = 0, worstX = null;
        for (let i = 0; i <= N; i++) {
            const x = x0 - delta + (2 * delta * i) / N;
            if (Math.abs(x - x0) < EPS) continue;      // 跳过 x0 本身（可能无定义）
            const fx = evalF(expr, x);
            if (!isFinite(fx)) return bad('函数在 x = ' + num(x) + ' 处无定义', { x: x });
            const dev = Math.abs(fx - L);
            if (dev > worst) { worst = dev; worstX = x; }
        }
        return worst < t
            ? ok({ delta: delta, worstDeviation: worst })
            : bad('δ = ' + num(delta) + ' 时最坏偏差 ' + num(worst) +
                  '，未小于 ε = ' + epsilon,
                  { delta: delta, worstDeviation: worst, worstX: worstX });
    }

    /* ---------------- 数值导数 ----------------
       用户拖动 h。判定：中心差商与目标导数值之差在容差内。 */
    function checkDerivative(check, ctx) {
        const h = ctx.param;
        if (typeof h !== 'number' || !isFinite(h)) {
            return bad('参数 h 还不是一个有效数值', { h: h });
        }
        if (h <= 0) return bad('步长 h 必须为正数', { h: h });

        const { expr, at: x0, value: target, tol } = check;
        const t = tol == null ? 0.05 : tol;
        const f1 = evalF(expr, x0 + h), f0 = evalF(expr, x0 - h);
        if (!isFinite(f1) || !isFinite(f0)) {
            return bad('函数在 x = ' + num(x0) + ' ± ' + num(h) + ' 处无定义', { h: h });
        }
        const slope = (f1 - f0) / (2 * h);
        return Math.abs(slope - target) <= t
            ? ok({ h: h, slope: slope })
            : bad('h = ' + num(h) + ' 时割线斜率 ' + num(slope) +
                  '，目标 ' + target + '（容差 ' + t + '）',
                  { h: h, slope: slope, target: target });
    }

    /* ---------------- 单调区间 ----------------
       判定 [from, to] 上函数是否**非减**（sign = 1）或**非增**（sign = -1）。

       为什么直接比较函数值，而不是检查「导数点点恒号」：
       后者在驻点处会误判 —— 例如 x² 在 [-1, 0] 上确实单调递减，
       但端点 x = 0 处导数为 0，逐点判据会把它判成「不满足恒负」。
       直接比较相邻采样点的函数值没有这个问题，且更贴近「单调」的定义。

       另加两条更严的检查（可选，由 strict 控制，默认开启）：
         · 端点不能取等（否则是常函数区间，不是严格单调）
         · 至少存在一段严格变化（排除「几乎处处相等」的退化情形）
       ============================================================ */
    function checkMonotone(check, ctx) {
        const { expr, from, to, sign } = check;
        if (!(from < to)) return bad('区间不合法：from 应小于 to', { from: from, to: to });
        const want = sign == null ? 1 : sign;      // 1 非减，-1 非增
        const N = check.samples || 200;
        const t = check.tol == null ? 1e-9 : check.tol;
        const strict = check.strict !== false;

        let prev = evalF(expr, from);
        if (!isFinite(prev)) return bad('x = ' + num(from) + ' 处函数无定义', { x: from });
        let changed = 0;
        let violatedAt = null;

        for (let i = 1; i <= N; i++) {
            const x = from + ((to - from) * i) / N;
            const cur = evalF(expr, x);
            if (!isFinite(cur)) return bad('x = ' + num(x) + ' 处函数无定义', { x: x });
            const d = cur - prev;
            if (want > 0 ? d < -t : d > t) { violatedAt = x; break; }
            if (Math.abs(d) > t) changed += Math.abs(d);
            prev = cur;
        }

        if (violatedAt !== null) {
            return bad('x = ' + num(violatedAt) + ' 处打破了' +
                       (want > 0 ? '非减' : '非增') + '（函数值反向变化了）',
                       { at: violatedAt, sign: want });
        }
        if (strict && changed < t) {
            return bad('该区间上函数值几乎没有变化，不是严格单调',
                       { changed: changed, sign: want });
        }
        return ok({ from: from, to: to, sign: want, totalChange: changed });
    }

    /* 判定入口。返回三态：
         null                                  —— 不是本领域的类型
         { pass:true,  reason:'', certificate } —— 判过
         { pass:false, reason:'…', certificate } —— 判不过
       与引擎层注册表、线代插件的返回结构一致。 */
    /* 规范化 ctx：缺失字段给安全默认值。与 linalg 插件保持一致的行为——
       插件作为公共接口被调用时，不该要求调用者填全所有字段。 */
    function normalizeCtx(ctx) {
        const c = ctx || {};
        return {
            taskId: c.taskId == null ? null : c.taskId,
            matrix: c.matrix === undefined ? null : c.matrix,
            matrixSize: c.matrixSize == null ? 2 : c.matrixSize,
            vectors: c.vectors || [],
            lines: c.lines || [],
            actionLog: c.actionLog || [],
            choices: c.choices || {},
            param: c.param === undefined ? null : c.param,
            Mat: c.Mat,
            vecEq: c.vecEq
        };
    }

    function judge(check, ctx) {
        ctx = normalizeCtx(ctx);
        switch (check.type) {
            case 'calc-limit':      return checkLimit(check, ctx);
            case 'calc-derivative': return checkDerivative(check, ctx);
            case 'calc-monotone':   return checkMonotone(check, ctx);
            default:                return null;   // 不是高数的类型
        }
    }

    /* 导出表达式求值器，便于测试与将来的 Python 侧对照 */
    const api = { judge: judge, evalF: evalF };

    /* 供浏览器界面使用的示例关卡数据（也是离线测试的输入） */
    api.sampleLabs = [
        {
            id: 'cal-1',
            title: 'ε-δ：找到够小的 δ',
            param: { name: 'delta', from: 0.01, to: 2, step: 0.01, init: 1 },
            tasks: [
                {
                    id: 'make-small',
                    text: '把 δ 调小，使邻域内所有 x 都满足 |f(x) − L| < ε',
                    check: {
                        type: 'calc-limit',
                        expr: { op: 'var' },                 // f(x) = x
                        at: 1, value: 1, epsilon: 0.1,
                        samples: 400
                    }
                }
            ]
        },
        {
            id: 'cal-2',
            title: '导数：割线斜率的极限',
            param: { name: 'h', from: 0.001, to: 1, step: 0.001, init: 0.5 },
            tasks: [
                {
                    id: 'slope',
                    text: '把 h 调小，让割线斜率趋近 f′(x₀)',
                    check: {
                        type: 'calc-derivative',
                        /* 用 sin 而不是 x²：中心差商对二次函数**任何 h 都精确**
                           等于导数，那样这个关卡判不出 h 的大小，作为教学任务
                           是坏的（判据对参数不敏感）。sin(h)/h 会随 h 变化。 */
                        expr: { op: 'sin', a: { op: 'var' } },
                        at: 0, value: 1, tol: 0.02       // f(x)=sin x, f′(0)=1
                    }
                }
            ]
        },
        {
            id: 'cal-3',
            title: '单调区间：导数不变号',
            param: { name: 'a', from: -2, to: 2, step: 0.1, init: 0 },
            tasks: [
                {
                    id: 'increasing',
                    text: '让函数在 [0, 1] 上单调递增',
                    check: {
                        type: 'calc-monotone',
                        expr: { op: 'add', a: { op: 'pow', a: { op: 'var' }, b: { op: 'const', v: 2 } },
                                b: { op: 'const', v: 0 } },
                        from: 0, to: 1, sign: 1
                    }
                }
            ]
        }
    ];

    if (typeof module === 'object' && module.exports) module.exports = api;
    return api;
})();
}(typeof globalThis !== 'undefined' ? globalThis : this));
