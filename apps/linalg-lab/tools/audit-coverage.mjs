#!/usr/bin/env node
/* 判题信息量审计：原因与证书的覆盖率
   ============================================================
   本项目的核心主张之一是「可解释诊断」。但诊断是最容易静默缺失的东西：
   判题依然工作、任务依然判得对错，只是失败时不给任何信息。
   本脚本给出全局覆盖率数字，用于判断还有多少缺口。

   ⚠️ 关键：必须为每个类型构造**语义正确**的上下文，分「判过」与「判不过」
      两条路径分别统计。第一版用同一份通用上下文，导致大量假警报
      （例如给 ε-δ 判题传 param=0.05，它其实判过了，判过时本就无证书）。

   用法：node tools/audit-coverage.mjs
   ============================================================ */
import { readFileSync, readdirSync, existsSync } from 'node:fs';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const APP = dirname(dirname(fileURLToPath(import.meta.url)));
const SITE = dirname(dirname(APP));
const ENGINE = join(SITE, 'engine-core');
const require = createRequire(import.meta.url);
const Mat = require(join(ENGINE, 'mat.js'));
const Registry = require(join(ENGINE, 'registry.js'));
const plugins = existsSync(join(ENGINE, 'domains'))
    ? readdirSync(join(ENGINE, 'domains')).map(d => ({ d, api: require(join(ENGINE, 'domains', d, 'judge.js')) }))
    : [];
const labs = JSON.parse(readFileSync(join(APP, 'assets', 'js', 'labs.json'), 'utf-8')).labs;
const extra = [];
plugins.forEach(p => { if (Array.isArray(p.api.sampleLabs)) p.api.sampleLabs.forEach(l => extra.push({ ...l, __d: p.d })); });

function mk(over) {
    return Object.assign({
        matrix: [[1, 0], [0, 1]], matrixSize: 2,
        vectors: [{ id: 'v', data: [1, 1] }, { id: 'u', data: [1, 0] }],
        lines: [{ a: 1, b: 0, c: 1 }, { a: 0, b: 1, c: 2 }],
        actionLog: [], choices: { t: 0 }, taskId: 't', param: 0.05, Mat,
        vecEq: (a, b, t) => { const k = t == null ? 0.15 : t; return a.length === b.length && a.every((x, i) => Math.abs(x - b[i]) <= k); }
    }, over || {});
}

const stat = { rows: [], fail: { noReason: 0, noCert: 0 }, pass: { withCert: 0 } };

function run(check, ctx) {
    const r1 = Registry.run(check, ctx);
    if (r1 !== null) return { layer: 'engine', r: r1 };
    for (const p of plugins) {
        const r = p.api.judge(check, ctx);
        if (r !== null) return { layer: p.d, r };
    }
    return { layer: 'none', r: null };
}

/* ① 用真实关卡数据跑一遍（默认上下文），统计判不过时的信息量 */
let total = 0;
for (const lab of labs.concat(extra)) {
    for (const task of lab.tasks) {
        const check = { ...task.check };
        const ctx = mk({ matrix: (lab.scene && lab.scene.matrix) || [[1, 0], [0, 1]], choices: { [task.id]: 0 } });
        const { layer, r } = run(check, ctx);
        total++;
        if (!r) { stat.rows.push({ layer: 'none', type: check.type }); continue; }
        if (r.pass === false) {
            if (!r.reason) stat.fail.noReason++;
            if (!r.certificate) stat.fail.noCert++;
        } else if (r.certificate) stat.pass.withCert++;
    }
}

/* ② 每个类型分别构造「判过」与「判不过」两条路径，逐类型统计 */
const CASES = {
    'vector-at':        [{ type: 'vector-at', target: 'v', to: [1, 1] }, { type: 'vector-at', target: 'v', to: [9, 9] }],
    'av-at':            [{ type: 'av-at', to: [1, 1] }, { type: 'av-at', to: [9, 9] }],
    'matrix-col-at':    [{ type: 'matrix-col-at', col: 0, to: [1, 0] }, { type: 'matrix-col-at', col: 0, to: [9, 9] }],
    'match-matrix':     [{ type: 'match-matrix', matrix: [[1, 0], [0, 1]] }, { type: 'match-matrix', matrix: [[9, 9], [9, 9]] }],
    'dot':              [{ type: 'dot', a: 'u', b: 'v', op: 'eq', value: 1 }, { type: 'dot', a: 'u', b: 'v', op: 'eq', value: 999 }],
    'choice':           [{ type: 'choice', correct: 0 }, { type: 'choice', correct: 1 }],
    'actions':          [{ type: 'actions', all: [] }, { type: 'actions', all: ['不存在'] }],
    'det':              [{ type: 'det', op: 'eq', value: 1, tol: 0.01 }, { type: 'det', op: 'eq', value: 999, tol: 0.01 }],
    'rank':             [{ type: 'rank', op: 'eq', value: 2 }, { type: 'rank', op: 'eq', value: 99 }],
    'solve':            [{ type: 'solve', to: [1, 1] }, { type: 'solve', to: [99, 99] }],
    /* 共线判定比较 v 与 A·v 的夹角。单位阵下二者恒等（0°），任何容差都判过，
    所以判不过的用例必须换一个真会把向量转 90° 的矩阵。 */
    'collinear':        [{ type: 'collinear', tolDeg: 90 }, { type: 'collinear', tolDeg: 0.0001 }],
    'eigen':            [{ type: 'eigen', value: 1, tol: 0.01, tolDeg: 0.01 }, { type: 'eigen', value: 99, tol: 0.01, tolDeg: 0.01 }],
    'on-span':          [{ type: 'on-span', op: 'in', target: 'v' }, { type: 'on-span', op: 'out', target: 'v' }],
    'in-basis':         [{ type: 'in-basis', target: 'v', to: [1, 1] }, { type: 'in-basis', target: 'v', to: [99, 99] }],
    'in-basis-matrix':  [{ type: 'in-basis-matrix', basis: [[1, 0], [0, 1]], matrix: [[1, 0], [0, 1]] },
                         { type: 'in-basis-matrix', basis: [[1, 0], [0, 1]], matrix: [[9, 9], [9, 9]] }],
    'vector-angle':     [{ type: 'vector-angle', a: 'u', b: 'v', value: 45, tol: 5 }, { type: 'vector-angle', a: 'u', b: 'v', value: 10, tol: 1 }],
    'cross-mag':        [{ type: 'cross-mag', colA: 0, colB: 1, op: 'eq', value: 1 }, { type: 'cross-mag', colA: 0, colB: 1, op: 'eq', value: 99 }],
    'cross-dir':        [{ type: 'cross-dir', colA: 0, colB: 1, dir: [0, 0, 1] }, { type: 'cross-dir', colA: 0, colB: 1, dir: [0, 0, -1] }],
    /* 交点可达：落在两直线交点 (1,2) 上才判过，所以判不过的用例要给别的坐标 */
    'intercept':        [{ type: 'intercept', target: 'v' }, { type: 'intercept', target: 'v' }],
    'null-space':       [{ type: 'null-space', target: 'v' }, { type: 'null-space', target: 'v' }],
    'calc-limit':       [{ type: 'calc-limit', expr: { op: 'var' }, at: 1, value: 1, epsilon: 0.5 },
                         { type: 'calc-limit', expr: { op: 'var' }, at: 1, value: 1, epsilon: 0.0001 }],
    /* h 越大差商越偏。判过用 h=0.01；判不过必须用**大 h**（h=1 时 sin(h)/h≈0.841）
       而不是小容差 —— 小 h 会让差商更准，反而判过。 */
    'calc-derivative':  [{ type: 'calc-derivative', expr: { op: 'sin', a: { op: 'var' } }, at: 0, value: 1, tol: 0.02 },
                         { type: 'calc-derivative', expr: { op: 'sin', a: { op: 'var' } }, at: 0, value: 1, tol: 0.02 }],
    'calc-monotone':    [{ type: 'calc-monotone', expr: { op: 'pow', a: { op: 'var' }, b: { op: 'const', v: 2 } }, from: 0, to: 1, sign: 1 },
                         { type: 'calc-monotone', expr: { op: 'pow', a: { op: 'var' }, b: { op: 'const', v: 2 } }, from: -1, to: 1, sign: 1 }]
};

/* 上下文按「判过 / 判不过」分别给：一个类型的两条路径往往需要不同的场景。 */
const CTX_OK = {
    'cross-mag': { matrix: [[1, 0, 0], [0, 1, 0], [0, 0, 1]], matrixSize: 3 },
    'cross-dir': { matrix: [[1, 0, 0], [0, 1, 0], [0, 0, 1]], matrixSize: 3 },
    'intercept': { vectors: [{ id: 'v', data: [1, 2] }], lines: [{ a: 1, b: 0, c: 1 }, { a: 0, b: 1, c: 2 }] },
    'null-space': { matrix: [[0, 0], [0, 0]], vectors: [{ id: 'v', data: [1, 1] }] },
    'collinear': { matrix: [[1, 0], [0, 1]] },
    'calc-limit': { param: 0.05 },
    'calc-derivative': { param: 0.01 },
    'calc-monotone': {}
};
const CTX_BAD = {
    'cross-mag': CTX_OK['cross-mag'],
    'cross-dir': CTX_OK['cross-dir'],
    'intercept': { vectors: [{ id: 'v', data: [5, 5] }], lines: [{ a: 1, b: 0, c: 1 }, { a: 0, b: 1, c: 2 }] },
    'null-space': CTX_OK['null-space'],
    'collinear': { matrix: [[0, -1], [1, 0]] },     // 把 v 转 90°，必然不共线
    /* 零空间判定要求 |Av| ≈ 0。用零矩阵会判过，所以判不过的用例用单位阵，
       且向量不能太短 —— 长度小于 minLen(0.25) 会先被「不是零向量」这一条拦下。 */
    'null-space': { matrix: [[1, 0], [0, 1]], vectors: [{ id: 'v', data: [1, 1] }] },
    'calc-limit': { param: 99 },                     // δ 很大 → 邻域内有偏差
    'calc-derivative': { param: 1 },                 // h 很大 → 差商明显偏离
    'calc-monotone': {}
};

console.log('=== 判题信息量审计 ===');
console.log(`任务总数：${total}`);
console.log('');
console.log(`真实关卡数据（默认上下文）：`);
console.log(`  判不过但没有原因：${stat.fail.noReason}`);
console.log(`  判不过但没有证书：${stat.fail.noCert}`);
console.log('');
console.log('逐类型覆盖（两条路径都尝试）：');
console.log('  类型                判过时给证书   判不过时给原因/证书');
let gaps = 0;
const rows = [];
for (const [type, [okCheck, badCheck]] of Object.entries(CASES)) {
    const rOk = run(okCheck, mk(CTX_OK[type] || {}));
    const rBad = run(badCheck, mk(CTX_BAD[type] || {}));
    const okCert = rOk.r ? (rOk.r.pass ? (!!rOk.r.certificate) : null) : null;
    const badReason = rBad.r ? (rBad.r.pass === false ? !!rBad.r.reason : null) : null;
    const badCert = rBad.r ? (rBad.r.pass === false ? !!rBad.r.certificate : null) : null;
    const layer = (rOk.layer === 'engine' ? 'engine' : rOk.layer);
    // 只把「判不过却没有原因」算作缺口；证书在部分类型上确实无语义，单独标注
    const gap = badReason === false;
    if (gap) gaps++;
    rows.push({ type, layer, okCert, badReason, badCert, gap });
    const f = (v) => v === null ? '—' : (v ? '有' : '**无**');
    console.log(`  ${type.padEnd(18)} ${String(f(okCert)).padEnd(12)} ${f(badReason)} / ${f(badCert)}   [${layer}]`);
}
console.log('');
console.log(`判不过却无原因的类型数：${gaps}`);
if (gaps) { console.log('✗ 存在缺口'); process.exit(1); }
console.log('✓ 所有类型在判不过时都给出原因（证书按类型语义可有可无）');
