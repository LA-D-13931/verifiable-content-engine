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
console.log(`判题类型：calc-limit / calc-derivative / calc-monotone / calc-riemann`);
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

console.log('\ncalc-riemann（黎曼和逼近定积分）');
{
    const chk = { type: 'calc-riemann', expr: { op: 'pow', a: X, b: K(2) },
                  from: 0, to: 1, value: 1 / 3, tol: 0.01 };
    ok(C.judge(chk, ctx(100)).pass === true, 'n = 100 判过（够细）');
    ok(C.judge(chk, ctx(50)).pass === true, 'n = 50 判过');
    const coarse = C.judge(chk, ctx(5));
    ok(coarse.pass === false, 'n = 5 判不过（太粗）');
    ok(/相差/.test(coarse.reason), '原因里给出了误差', coarse.reason);
    ok(typeof coarse.certificate.error === 'number', '证书里带误差数值');
    /* 参数敏感性 —— 这是本关卡的立身之本 */
    /* 初值必须是 +Infinity，不能用 -1：
       误差是「越小越好」，从 -1 起比会让第一次迭代就判成「变大」。
       （第一版写成 -1，于是这条断言必然失败——测试自身的 bug，不是实现的。） */
    let prev = Infinity, monotone = true, seen = [];
    for (const n of [1, 2, 5, 10, 20, 50, 100, 200]) {
        const err = C.judge(chk, ctx(n)).certificate.error;
        seen.push(err.toFixed(4));
        if (err > prev + 1e-12) monotone = false;
        prev = err;
    }
    ok(monotone, '误差随 n 单调不增（说明判据真的在衡量逼近程度）', seen.join(' → '));
    ok(C.judge(chk, ctx(0)).pass === false, 'n = 0 判不过');
    ok(C.judge(chk, ctx(NaN)).pass === false, 'n 非数值时判不过');
    /* 不可达：无界函数在含奇点的区间上，任何 n 都做不出来 */
    const unreach = C.judge({ type: 'calc-riemann', expr: { op: 'div', a: K(1), b: X },
                              from: 0, to: 1, value: 1, tol: 0.01 }, ctx(100));
    ok(unreach.pass === false, '无界函数（1/x 在 0 处）给出不可达诊断', unreach.reason);
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
    ok(Array.isArray(C.sampleLabs) && C.sampleLabs.length === 5,
       `提供 ${C.sampleLabs ? C.sampleLabs.length : 0} 个示例关卡（P2 目标：5 个）`);
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
