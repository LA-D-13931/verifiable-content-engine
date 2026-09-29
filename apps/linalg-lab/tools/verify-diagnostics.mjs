#!/usr/bin/env node
/* 诊断覆盖率检查
   ============================================================
   本项目的核心主张之一是「可解释诊断」：判不过时必须告诉作者为什么。
   但诊断是**最容易静默缺失**的东西——判题依然工作、任务依然判得对错，
   只是失败时不给任何信息。所以需要一条自动检查盯着它。

   检查三件事：
     ① 覆盖率 —— 每个判题类型在"判不过"时都必须给出原因
     ② 诊断有信息量 —— 原因不能是空串或占位符
     ③ 证书可用 —— 证书里的数值必须与独立复算一致（不是随便填的）

   用法：node tools/verify-diagnostics.mjs
   ============================================================ */
import { readFileSync, readdirSync, existsSync } from 'node:fs';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const APP = dirname(HERE);                        // apps/linalg-lab
const SITE = dirname(dirname(APP));               // 仓库根
const ENGINE = join(SITE, 'engine-core');
const require = createRequire(import.meta.url);
const Mat = require(join(ENGINE, 'mat.js'));
const Registry = require(join(ENGINE, 'registry.js'));

const plugins = existsSync(join(ENGINE, 'domains'))
    ? readdirSync(join(ENGINE, 'domains')).map(d => ({ d, api: require(join(ENGINE, 'domains', d, 'judge.js')) }))
    : [];

let pass = 0, fail = 0;
const failures = [];
const ok = (c, name, extra) => {
    if (c) { pass++; console.log(`  ✓ ${name}`); }
    else { fail++; failures.push(name); console.log(`  ✗ ${name}${extra ? '  —— ' + extra : ''}`); }
};

function mk(over) {
    return Object.assign({
        matrix: [[1, 0], [0, 1]], matrixSize: 2,
        vectors: [{ id: 'v', data: [1, 1] }, { id: 'u', data: [1, 0] }],
        lines: [{ a: 1, b: 0, c: 1 }, { a: 0, b: 1, c: 2 }],
        actionLog: [], choices: {}, taskId: 't', param: 0.05, Mat,
        vecEq: (a, b, t) => { const k = t == null ? 0.15 : t; return a.length === b.length && a.every((x, i) => Math.abs(x - b[i]) <= k); }
    }, over || {});
}

console.log('=== 诊断覆盖率检查 ===');
console.log('');

/* ---------------- ① 引擎层 ---------------- */
console.log('引擎层（registry.js）');
{
    const failing = [
        ['vector-at', { type: 'vector-at', target: 'v', to: [9, 9] }],
        ['av-at', { type: 'av-at', to: [9, 9] }],
        ['matrix-col-at', { type: 'matrix-col-at', col: 0, to: [9, 9] }],
        ['match-matrix', { type: 'match-matrix', matrix: [[9, 9], [9, 9]] }],
        ['dot', { type: 'dot', a: 'u', b: 'v', op: 'eq', value: 999 }],
        ['choice', { type: 'choice', correct: 1 }],
        ['actions', { type: 'actions', all: ['不存在的动作'] }]
    ];
    for (const [name, check] of failing) {
        const r = Registry.run(check, mk({ choices: { t: 0 } }));
        ok(r && r.pass === false, `${name}：判不过`, JSON.stringify(r));
        ok(r && typeof r.reason === 'string' && r.reason.length > 0,
           `${name}：给出了原因`, r ? JSON.stringify(r.reason) : '');
    }
}

/* ---------------- ② 领域层 ---------------- */
for (const p of plugins) {
    console.log('');
    console.log(`领域层（domains/${p.d}）`);
    const types = p.d === 'linalg'
        ? ['det', 'rank', 'solve', 'collinear', 'eigen', 'on-span', 'in-basis',
           'in-basis-matrix', 'vector-angle', 'cross-mag', 'cross-dir', 'intercept', 'null-space']
        : ['calc-limit', 'calc-derivative', 'calc-monotone'];

    /* 为每个类型构造一个「必然判不过」的上下文 */
    const failCtx = {
        det: { matrix: [[1, 1], [1, 1]] },          // det = 0
        rank: { matrix: [[1, 1], [1, 1]] },         // rank = 1
        solve: { matrix: [[1, 0], [0, 1]] },
        /* 共线判定用的是 v=(1,1) 与 Av；单位阵下二者恒等（夹角 0°），
           任何容差都会判过，构造不出「判不过」。改用把 Av 转 90° 的矩阵。 */
        collinear: { matrix: [[0, -1], [1, 0]] },
        eigen: { matrix: [[0, 1], [1, 0]] },
        'on-span': { matrix: [[1, 1], [1, 1]], vectors: [{ id: 'v', data: [1, 0] }] },
        'in-basis': { matrix: [[1, 0], [0, 1]], vectors: [{ id: 'v', data: [3, 4] }] },
        'in-basis-matrix': { matrix: [[1, 0], [0, 1]] },   // 目标 [[9,9],[9,9]] 必然不符
        'vector-angle': { vectors: [{ id: 'u', data: [1, 0] }, { id: 'v', data: [0, 1] }] },
        'cross-mag': { matrix: [[1, 0, 0], [0, 1, 0], [0, 0, 1]], matrixSize: 3 },
        'cross-dir': { matrix: [[1, 0, 0], [0, 1, 0], [0, 0, 1]], matrixSize: 3 },
        intercept: { lines: [{ a: 1, b: 0, c: 1 }, { a: 1, b: 0, c: 5 }], vectors: [{ id: 'v', data: [0, 0] }] },
        /* 零空间判定要求 |Av| ≈ 0；单位阵下 |Av| = |v| ≠ 0，
           但 v=(1,1)、|Av|=√2 > 容差，确实判不过 —— 保留 */
        'null-space': { matrix: [[1, 0], [0, 1]] },
        'calc-limit': { param: 99 },
        'calc-derivative': { param: 99 },
        'calc-monotone': {}
    };
    const failCheck = {
        det: { type: 'det', op: 'eq', value: 999, tol: 0.1 },
        rank: { type: 'rank', op: 'eq', value: 99 },
        solve: { type: 'solve', to: [99, 99] },
        collinear: { type: 'collinear', tolDeg: 0.0001 },
        eigen: { type: 'eigen', value: 99, tol: 0.01, tolDeg: 0.01 },
        'on-span': { type: 'on-span', op: 'in', target: 'v' },
        'in-basis': { type: 'in-basis', target: 'v', to: [99, 99] },
        'in-basis-matrix': { type: 'in-basis-matrix', basis: [[1, 0], [0, 1]], matrix: [[9, 9], [9, 9]] },
        'vector-angle': { type: 'vector-angle', a: 'u', b: 'v', value: 10, tol: 1 },
        'cross-mag': { type: 'cross-mag', colA: 0, colB: 1, op: 'eq', value: 99 },
        'cross-dir': { type: 'cross-dir', colA: 0, colB: 1, dir: [0, 0, -1] },
        intercept: { type: 'intercept', target: 'v' },
        'null-space': { type: 'null-space', target: 'v' },
        'calc-limit': { type: 'calc-limit', expr: { op: 'var' }, at: 1, value: 1, epsilon: 0.0001 },
        'calc-derivative': { type: 'calc-derivative', expr: { op: 'sin', a: { op: 'var' } }, at: 0, value: 1, tol: 0.0001 },
        'calc-monotone': { type: 'calc-monotone', expr: { op: 'pow', a: { op: 'var' }, b: { op: 'const', v: 2 } }, from: -1, to: 1, sign: 1 }
    };

    let covered = 0;
    for (const t of types) {
        const r = p.api.judge(failCheck[t], mk(failCtx[t]));
        /* ⚠️ 先自校验「测试上下文本身」：如果它其实判过了，后面的
           「有没有原因」就失去意义 —— 这是本脚本第一版挂 17 项的原因
           （我把上下文构造错了，却以为是代码有 bug）。 */
        if (!r || r.pass !== false) {
            ok(false, `${t}：测试上下文必须构造出「判不过」的情形`,
               'r = ' + JSON.stringify(r) + '（若为 pass:true，说明这个用例本身就无效）');
            continue;
        }
        const hasReason = r && typeof r.reason === 'string' && r.reason.length > 0;
        if (hasReason) covered++;
        ok(r !== null && r.pass === false, `${t}：构造出判不过的情形`);
        ok(hasReason, `${t}：给出了原因`, r ? JSON.stringify(r.reason) : 'null');
        ok(r && r.certificate, `${t}：给出了证书`, r ? JSON.stringify(r.certificate) : '');
    }
    console.log(`    覆盖率：${covered} / ${types.length}`);
}

/* ---------------- ③ 证书必须与独立复算一致 ---------------- */
console.log('');
console.log('证书数值与独立复算是否一致');
{
    const target = [[7, 7], [7, 7]], current = [[1, 0], [0, 1]];
    const r = Registry.run({ type: 'match-matrix', matrix: target, tol: 0.01 },
                           mk({ matrix: current }));
    // 独立复算最大偏差：|1-7|=6、|0-7|=7 → 应为 7（我第一版写成 6，是期望值算错了）
    let expect = 0;
    target.forEach((row, i) => row.forEach((x, j) => {
        expect = Math.max(expect, Math.abs(current[i][j] - x));
    }));
    ok(r && r.certificate && Math.abs(r.certificate.maxDeviation - expect) < 1e-9,
       `match-matrix 的证书偏差 = ${expect}（与独立复算一致）`,
       r && r.certificate ? String(r.certificate.maxDeviation) : '');
}
{
    const Linalg = plugins.find(p => p.d === 'linalg');
    /* 注意检查值要与实际 det 不同，否则会判过、没有证书 */
    const M = [[1, 2], [2, 4]];
    const r = Linalg.api.judge({ type: 'det', op: 'eq', value: 999, tol: 0.01 },
                               mk({ matrix: M }));
    const truth = Mat.det(M);        // = 0
    ok(r && r.certificate && Math.abs(r.certificate.determinant - truth) < 1e-9,
       'det 的证书行列式与 Mat.det 一致', r && r.certificate ? String(r.certificate.determinant) : '');
}
{
    const Linalg = plugins.find(p => p.d === 'linalg');
    const m = [[1, 1], [2, 2]];      // rank = 1
    const r = Linalg.api.judge({ type: 'rank', op: 'eq', value: 2 }, mk({ matrix: m }));
    ok(r && r.certificate && r.certificate.rank === Mat.rank(m),
       'rank 的证书秩与 Mat.rank 一致', r && r.certificate ? String(r.certificate.rank) : '');
}

console.log('');
console.log(`通过 ${pass} / ${pass + fail}`);
if (fail) {
    console.log(`失败 ${fail} 项 ✗`);
    failures.slice(0, 16).forEach(f => console.log('   - ' + f));
    process.exit(1);
}
console.log('全部通过 ✓ 每个判题类型在判不过时都给出原因与证书');
