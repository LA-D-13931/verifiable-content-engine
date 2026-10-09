/* 判题调用与上下文构造（**唯一实现**，供 verify-engine 与 audit-tautology 共用）。
   ============================================================
   为什么抽出来：这段逻辑原本只写在 verify-engine.mjs 里。新的
   区分力审计（audit-tautology.mjs）也必须用**同一套**上下文构造，
   否则两个工具报的数字不可比 —— 而"同一段逻辑两份实现迟早分叉"
   正是本项目吃过亏的地方（矩阵原语那一层就是这样）。

   用法：
       import { makeJudge, ctxFor } from './judge-ctx.mjs';
       const judge = makeJudge(Registry, plugins, Mat);
   ============================================================ */

/* 调用判题分派：先问引擎层注册表，未命中再逐个领域插件。
   刻意在这里复刻而不是加载 engine.js —— engine.js 依赖 DOM，
   而这套工具要验证的正是「判题分派不依赖 DOM」。 */
export function makeJudge(Registry, plugins, Mat) {
    return function judge(check, taskId, ctxOver) {
        const ctx = Object.assign({
            taskId: taskId,
            matrix: null,
            matrixSize: 2,
            vectors: [],
            lines: [],
            choices: {},
            actionLog: [],
            Mat: Mat,
            vecEq: (a, b, tol) => {
                const t = tol == null ? 0.15 : tol;
                return a.length === b.length && a.every((x, i) => Math.abs(x - b[i]) <= t);
            }
        }, ctxOver || {});

        const r1 = Registry.run(check, ctx);
        if (r1 !== null) return { layer: 'engine', result: r1 };
        for (const p of plugins) {
            const r = p.api.judge(check, ctx);
            if (r !== null) return { layer: 'domain:' + p.domain, result: r };
        }
        return { layer: 'none', result: null };
    };
}

/* 为每个任务构造一份「能触发该判题类型」的最小上下文，
   目的只是让处理器真的执行到判定分支，而不是在参数检查处提前返回。 */
export function ctxFor(check, lab) {
    const scene = lab.scene || {};
    const base = {
        matrix: scene.matrix || [[1, 0], [0, 1]],
        matrixSize: (scene.matrix || [[1, 0], [0, 1]]).length,
        vectors: [{ id: 'v', data: [1, 1] }, { id: 'u', data: [1, 0] }],
        lines: [{ a: 1, b: 0, c: 1 }, { a: 0, b: 1, c: 2 }],
        choices: { [check.__taskId]: 0 },
        actionLog: ['apply-a', 'apply-b', 'apply-c', 'undo-a', 'undo-b',
                    'try-inverse', 'view-ab', 'view-ba', 'play-transform']
    };
    if (check.type === 'dot') {
        base.vectors = [{ id: check.a || 'u', data: [1, 0] },
                        { id: check.b || 'v', data: [2, 1] }];
    }
    if (check.type === 'vector-at' || check.type === 'matrix-col-at') {
        base.vectors = [{ id: check.target || 'v', data: check.to || [0, 0] }];
    }
    return base;
}
