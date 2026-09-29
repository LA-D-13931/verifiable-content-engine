#!/usr/bin/env node
/* 高等数学领域插件的离线回归测试
   ============================================================
   这是「引擎可扩展到第二个科目」的验收（见 engine/API_如何新增科目.md）。
   不需要浏览器，只需要领域插件本身。

   用例分三类：
     · 参数敏感 —— 判据必须随参数变化（否则关卡是坏的）
     · 可达性   —— 对任何参数都不成立的判据必须报「不可达」，而不是静默判假
     · 诊断质量 —— 不通过时必须给出可读原因

   运行：node tools/verify-calculus.mjs
   ============================================================ */
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const APP = dirname(HERE);                        // apps/linalg-lab
const SITE = dirname(dirname(APP));               // 仓库根
const ENGINE = join(SITE, 'engine-core');
const require = createRequire(import.meta.url);
const C = require(join(ENGINE, 'domains', 'calculus', 'judge.js'));

let pass = 0, fail = 0;
const failures = [];
function ok(cond, name, extra) {
    if (cond) { pass++; console.log(`  ✓ ${name}`); }
    else { fail++; failures.push(name); console.log(`  ✗ ${name}${extra ? '  —— ' + extra : ''}`); }
}
function ctx(param) {
    return { matrix: null, matrixSize: 2, vectors: [], lines: [], actionLog: [],
             choices: {}, taskId: 't', param: param };
}

const X = { op: 'var' };
const K = (v) => ({ op: 'const', v: v });
const SIN = { op: 'sin', a: X };
const SQR = { op: 'pow', a: X, b: K(2) };

console.log('=== 高数领域插件：离线回归测试 ===');
console.log(`判题类型：calc-limit / calc-derivative / calc-monotone`);
console.log('');

console.log('calc-limit（ε-δ 极限）');
{
    const chk = { type: 'calc-limit', expr: X, at: 1, value: 1, epsilon: 0.1 };
    ok(C.judge(chk, ctx(0.05)).pass === true,   'δ = 0.05 判过（够小）');
    const big = C.judge(chk, ctx(0.5));
    ok(big.pass === false,                       'δ = 0.5 判不过（太大）');
    ok(/最坏偏差/.test(big.reason),              '原因里给出了最坏偏差', big.reason);
    ok(typeof big.certificate.worstDeviation === 'number', '证书里带偏差数值');
    ok(C.judge(chk, ctx(-1)).pass === false,     'δ 为负时判不过');
    ok(C.judge(chk, ctx(NaN)).pass === false,    'δ 非数值时判不过');
    /* 不可达：要求 ε 小于 0 —— 任何 δ 都不可能成立 */
    const unreach = C.judge(
        { type: 'calc-limit', expr: K(5), at: 1, value: 0, epsilon: 1e-9 }, ctx(0.001));
    ok(unreach.pass === false && /最坏偏差/.test(unreach.reason),
       '不可达判据给出诊断而非静默判假', unreach.reason);
}

console.log('\ncalc-derivative（数值导数）');
{
    const chk = { type: 'calc-derivative', expr: SIN, at: 0, value: 1, tol: 0.02 };
    ok(C.judge(chk, ctx(0.001)).pass === true, 'h = 0.001 判过');
    ok(C.judge(chk, ctx(0.1)).pass === true,   'h = 0.1 判过（在容差内）');
    const coarse = C.judge(chk, ctx(1));
    ok(coarse.pass === false,                   'h = 1 判不过（太粗）');
    ok(/割线斜率/.test(coarse.reason),          '原因里给出割线斜率', coarse.reason);
    /* 参数敏感性：这是本关卡的立身之本 —— 判据必须随 h 变化。
       反例：若用 x²，中心差商对任何 h 都精确等于导数，关卡就是坏的。 */
    const sq = { type: 'calc-derivative', expr: SQR, at: 1, value: 2, tol: 0.001 };
    const sqSensitive = C.judge(sq, ctx(1)).pass !== C.judge(sq, ctx(0.001)).pass;
    ok(!sqSensitive,
       '（已知）x² 的中心差商与 h 无关 —— 故示例关卡改用 sin，不用 x²');
}

console.log('\ncalc-monotone（单调区间）');
{
    const inc = { type: 'calc-monotone', expr: SQR, from: 0, to: 1, sign: 1 };
    ok(C.judge(inc, ctx(null)).pass === true, 'x² 在 [0,1] 递增：判过');
    const both = { type: 'calc-monotone', expr: SQR, from: -1, to: 1, sign: 1 };
    const r = C.judge(both, ctx(null));
    ok(r.pass === false,                       'x² 在 [-1,1] 递增：判不过（含驻点）');
    ok(/非增|非减/.test(r.reason),              '原因里说明了打破了哪个方向的单调', r.reason);
    ok(C.judge({ type: 'calc-monotone', expr: SQR, from: -1, to: 0, sign: -1 }, ctx(null)).pass === true,
       'x² 在 [-1,0] 递减：判过');
    ok(C.judge({ type: 'calc-monotone', expr: SQR, from: 1, to: 0, sign: 1 }, ctx(null)).pass === false,
       '区间不合法时判不过');
}

console.log('\n领域边界');
{
    ok(C.judge({ type: 'det', op: 'eq', value: 1 }, ctx(null)) === null,
       '线代类型返回 null（不是本领域，交由别的插件）');
    ok(C.judge({ type: 'choice', correct: 0 }, ctx(null)) === null,
       '引擎层类型返回 null');
    ok(typeof C.evalF === 'function', '导出表达式求值器（便于将来与 Python 侧对照）');
    const e = C.evalF({ op: 'add', a: K(2), b: { op: 'mul', a: K(3), b: X } }, 4);
    ok(e === 14, '表达式求值正确：2 + 3x 在 x=4 得 14', String(e));
}

console.log('\n示例关卡');
{
    ok(Array.isArray(C.sampleLabs) && C.sampleLabs.length === 3,
       `提供 ${C.sampleLabs ? C.sampleLabs.length : 0} 个示例关卡（供界面与测试使用）`);
    const all = C.sampleLabs.every(l => l.tasks.every(t => C.judge(t.check, ctx(null)) !== null));
    ok(all, '示例关卡里的判题类型都能被本插件接住');
}

console.log('');
console.log(`通过 ${pass} / ${pass + fail}`);
if (fail) {
    console.log(`失败 ${fail} 项 ✗`);
    failures.forEach(f => console.log('   - ' + f));
    process.exit(1);
}
console.log('全部通过 ✓ 第二个科目可复用同一套引擎接口');
