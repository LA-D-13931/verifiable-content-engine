#!/usr/bin/env node
/* 领域插件与引擎 API 的一致性检查（W2-3）
   ============================================================
   这条任务是「用新引擎 API 回头检查线代插件有没有被污染」。
   靠人工读代码判断不可靠，所以做成检查。

   检查四件事：
     ① 不依赖全局 —— 插件只能从 ctx 取依赖，不得引用 App / document / window
     ② 边界干净 —— 插件不处理引擎层已注册的 7 个类型（应返回 null）
     ③ 返回值规范 —— 每个类型都返回 { pass, reason, certificate } 三元组或 null
     ④ 不越界 —— 插件不得访问 ctx 里没有的字段

   用法：node tools/verify-plugin-api.mjs
   ============================================================ */
import { readFileSync, readdirSync, existsSync } from 'node:fs';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const APP = dirname(HERE);
const REPO = dirname(dirname(APP));
const ENGINE = join(REPO, 'engine-core');

const require = createRequire(import.meta.url);
const Mat = require(join(ENGINE, 'mat.js'));
const Registry = require(join(ENGINE, 'registry.js'));
const domainsDir = join(ENGINE, 'domains');
const plugins = readdirSync(domainsDir).map(d => ({
    d, src: readFileSync(join(domainsDir, d, 'judge.js'), 'utf-8'),
    api: require(join(domainsDir, d, 'judge.js'))
}));

let pass = 0, fail = 0;
const failures = [];
const ok = (c, name, extra) => {
    if (c) { pass++; console.log(`  ✓ ${name}`); }
    else { fail++; failures.push(name); console.log(`  ✗ ${name}${extra ? '  —— ' + extra : ''}`); }
};

/* 引擎层已注册的 7 个类型：领域插件必须对它们返回 null，不能抢着处理 */
const ENGINE_TYPES = Registry.types();

/* 一个「什么都有」的 ctx，用来探测插件是否读了不该读的东西 */
function richCtx() {
    return {
        taskId: 't', matrix: [[1, 1], [1, 1]], matrixSize: 2,
        vectors: [{ id: 'v', data: [1, 1] }, { id: 'u', data: [1, 0] }],
        lines: [{ a: 1, b: 0, c: 1 }, { a: 0, b: 1, c: 2 }],
        actionLog: [], choices: { t: 0 }, param: 0.05,
        Mat, vecEq: (a, b, t) => { const k = t == null ? 0.15 : t;
            return a.length === b.length && a.every((x, i) => Math.abs(x - b[i]) <= k); }
    };
}

console.log('=== 领域插件与引擎 API 一致性 ===');
console.log(`引擎层已注册类型：${ENGINE_TYPES.length} 种`);
console.log(`领域插件：${plugins.map(p => p.d).join('、')}`);
console.log('');

/* ---- ① 不依赖全局 ---- */
console.log('① 不依赖全局（插件只能从 ctx 取依赖）');
for (const p of plugins) {
    /* window / document / App 这些一旦出现，插件就不能在 Node 里独立加载。
       注释里提到不算违规，所以先剥掉注释再查。 */
    const code = p.src
        .replace(/\/\*[\s\S]*?\*\//g, '')      // 块注释
        .replace(/^\s*\/\/.*$/gm, '');          // 行注释
    const bad = [];
    if (/\bwindow\./.test(code)) bad.push('window.');
    if (/\bdocument\./.test(code)) bad.push('document.');
    if (/\blocalStorage\b/.test(code)) bad.push('localStorage');
    /* `App.` 要看它是不是本地别名：插件里写 `const App = ctx;` 是有意的做法
       （13 个 case 从 engine.js 逐字提取，原名就是 App.*），此时 App 指的是 ctx，
       不是全局——不能当违规。只有在没有这行别名却使用 App. 时才是真依赖全局。
       （第一版检查没区分这两种情况，误报了一次。） */
    const hasAlias = /const\s+App\s*=\s*ctx\s*;/.test(code);
    if (!hasAlias && /\bApp\./.test(code)) bad.push('App.（且无 const App = ctx 别名）');
    ok(bad.length === 0, `${p.d}：代码里不引用全局`, bad.join('、'));
}

/* ---- ② 边界干净：不处理引擎层的类型 ---- */
console.log('');
console.log('② 边界干净（引擎层的类型必须返回 null）');
for (const p of plugins) {
    const stolen = [];
    for (const t of ENGINE_TYPES) {
        // 造一个最小 check，只要类型名对得上，插件就该返回 null
        const r = p.api.judge({ type: t }, richCtx());
        if (r !== null) stolen.push(t);
    }
    ok(stolen.length === 0, `${p.d}：不接管引擎层的 ${ENGINE_TYPES.length} 个类型`,
       '抢了：' + stolen.join('、'));
}

/* ---- ③ 返回值规范 ---- */
console.log('');
console.log('③ 返回值规范（三元组或 null）');
const PROBE = {
    linalg: [
        { type: 'det', op: 'eq', value: 999, tol: 0.1 },
        { type: 'rank', op: 'eq', value: 99 },
        { type: 'eigen', value: 99, tol: 0.01, tolDeg: 0.01 },
        { type: 'on-span', op: 'in', target: 'v' },
        { type: 'in-basis', target: 'v', to: [99, 99] },
        { type: 'in-basis-matrix', basis: [[1, 0], [0, 1]], matrix: [[9, 9], [9, 9]] },
        { type: 'vector-angle', a: 'u', b: 'v', value: 10, tol: 1 },
        { type: 'cross-mag', colA: 0, colB: 1, op: 'eq', value: 99 },
        { type: 'cross-dir', colA: 0, colB: 1, dir: [0, 0, -1] },
        { type: 'solve', to: [99, 99] },
        { type: 'collinear', tolDeg: 0.0001 },
        { type: 'intercept', target: 'v' },
        { type: 'null-space', target: 'v' }
    ],
    calculus: [
        { type: 'calc-limit', expr: { op: 'var' }, at: 1, value: 1, epsilon: 0.0001 },
        { type: 'calc-derivative', expr: { op: 'sin', a: { op: 'var' } }, at: 0, value: 1, tol: 0.0001 },
        { type: 'calc-monotone', expr: { op: 'pow', a: { op: 'var' }, b: { op: 'const', v: 2 } }, from: -1, to: 1, sign: 1 }
    ]
};
for (const p of plugins) {
    const probes = PROBE[p.d] || [];
    const bad = [];
    for (const chk of probes) {
        for (const [label, c] of [['判不过', richCtx()],
                                  ['判过', Object.assign(richCtx(), {
                                      matrix: [[1, 0], [0, 1]], matrixSize: 3,
                                      param: 0.05 })],
                                  ['缺字段', { taskId: 't' }]]) {
            let r;
            try { r = p.api.judge(chk, c); }
            catch (e) { bad.push(`${chk.type}(${label}) 抛异常 ${e.message}`); continue; }
            if (r === null) continue;
            if (typeof r !== 'object' || typeof r.pass !== 'boolean') {
                bad.push(`${chk.type}(${label}) 返回非三元组：${JSON.stringify(r)}`);
            } else if (r.pass === false && typeof r.reason !== 'string') {
                bad.push(`${chk.type}(${label}) reason 不是字符串`);
            }
        }
    }
    ok(bad.length === 0, `${p.d}：${probes.length} 个类型 × 3 种 ctx 都返回规范值`,
       bad.slice(0, 3).join('；'));
}

/* ---- ④ 不越界：插件不得访问 ctx 里没有的字段 ---- */
console.log('');
console.log('④ 不越界（用最小 ctx 探测，不得因缺字段而抛异常）');
for (const p of plugins) {
    const probes = PROBE[p.d] || [];
    const bad = [];
    for (const chk of probes) {
        try {
            p.api.judge(chk, { taskId: 't', Mat });
        } catch (e) {
            bad.push(`${chk.type}: ${e.message}`);
        }
    }
    ok(bad.length === 0, `${p.d}：ctx 只有 taskId 与 Mat 时也不抛异常`, bad.slice(0, 2).join('；'));
}

console.log('');
console.log(`通过 ${pass} / ${pass + fail}`);
if (fail) {
    console.log(`失败 ${fail} 项 ✗`);
    failures.forEach(f => console.log('   - ' + f));
    process.exit(1);
}
console.log('全部通过 ✓ 领域插件与引擎 API 一致，无全局依赖、无越界、边界干净');
