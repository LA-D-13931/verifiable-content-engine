#!/usr/bin/env node
/* 诊断准确性检查：诊断说的失败条件，必须就是真正拦下判定的那一条。
   ============================================================
   为什么需要这一项（不只是「有原因」就够了）：
   有些判题类型的判定分支有 3-4 条失败条件，而诊断只写了其中一条。
   于是会出现「诊断说 |Av| 有问题、实际是不平行」这种**看似有原因、
   实则误导**的情况 —— 这比没有原因更糟，因为作者会照着错的方向去改。

   本项目真实发生过：独立校验页发现 7-5/find 判不过，
   引擎报「当前 |Av| = 0，要求接近 0（容差 0.1）」，
   而真实原因是向量与 dir 不平行（cos = 0.707 < 0.98）。

   做法：对每个多条件类型，构造**只触发其中一条**的输入，
   要求诊断文本指向那一条，且不指向其他条目的特征词。

   用法：node tools/verify-diagnosis-accuracy.mjs
   ============================================================ */
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const APP = dirname(HERE);
const REPO = dirname(dirname(APP));
const require = createRequire(import.meta.url);
const Mat = require(join(REPO, 'engine-core', 'mat.js'));
require(join(REPO, 'engine-core', 'domains', 'linalg', 'judge.js'));

const J = globalThis.LinalgJudge;
let pass = 0, fail = 0;
const failures = [];
function ok(cond, name, extra) {
    if (cond) { pass++; console.log('  ✓ ' + name); }
    else { fail++; failures.push(name); console.log('  ✗ ' + name + (extra ? '  —— ' + extra : '')); }
}
function ctx(o) {
    return Object.assign({
        taskId: 't', matrix: [[1, 1], [1, 1]], matrixSize: 2,
        vectors: [], lines: [], actionLog: [], choices: {}, param: null,
        Mat, vecEq: (a, b, t) => a.length === b.length &&
            a.every((x, i) => Math.abs(x - b[i]) <= (t == null ? 0.15 : t))
    }, o);
}

console.log('=== 诊断准确性：诊断必须指向真正的失败条件 ===');
console.log('');

/* ---------------- null-space：4 条失败条件 ---------------- */
console.log('null-space（4 条失败条件）');
{
    const chk = { type: 'null-space', tol: 0.1, dir: [-1, 1] };

    const short = J.judge(chk, ctx({ vectors: [{ id: 'v', data: [0.1, -0.1] }] }));
    ok(short.pass === false, '① 长度不足 → 判不过');
    ok(/太短|长度/.test(short.reason), '① 诊断说的是「长度」', short.reason);

    const notNull = J.judge(chk, ctx({ vectors: [{ id: 'v', data: [1, 1] }] }));
    ok(notNull.pass === false, '② 不在零空间 → 判不过');
    ok(/\|Av\|/.test(notNull.reason), '② 诊断说的是「|Av|」', notNull.reason);
    ok(!/方向不符/.test(notNull.reason), '② 不误报成「方向不符」');

    /* ③ 方向不符 —— 要真正触发这一条，必须让 ‖Av‖ **通过**而 cos 不通过。
       矩阵 [[1,1],[1,1]] 的零空间沿 [1,-1]，所以要把 dir 选得与它夹角较大：
       dir = [-0.99, 0.14] 与 [1,-1] 的 |cos| ≈ 0.80 < 0.98，方向必然不符。
       v = [-0.75, 0.75] 是与 dir 夹角大的零空间向量，且 ‖Av‖ = 0 通过。
       （写这条用例时先用了 v=[0,1.5]，它的 ‖Av‖=2.121 已超容差，
         判定根本走不到方向检查 —— 是用例错了，不是实现错了。） */
    const chk3 = { type: 'null-space', tol: 0.1, dir: [-0.99, 0.14] };
    const d3 = J.judge(chk3, ctx({ vectors: [{ id: 'v', data: [-0.75, 0.75] }] }));
    ok(d3.pass === false, '③ 方向不符 → 判不过');
    ok(/方向不符/.test(d3.reason), '③ 诊断说的是「方向不符」（旧版会报成 |Av|）', d3.reason);
    ok(/零空间条件/.test(d3.reason), '③ 诊断同时说明「零空间条件已满足」，把范围讲清');

    const good = J.judge(chk, ctx({ vectors: [{ id: 'v', data: [1, -1] }] }));
    ok(good.pass === true, '④ 正确解 [1,-1] → 判过');
}

/* ---------------- eigen：4 条失败条件 ---------------- */
console.log('');
console.log('eigen（4 条失败条件）');
{
    const o = { vectors: [{ id: 'v', data: [1, 0] }] };

    const noV = J.judge({ type: 'eigen', value: 2, tol: 0.1, tolDeg: 4 }, ctx({ matrix: [[2, 0], [0, 1]] }));
    ok(noV.pass === false && noV.reason.length > 0, '缺向量 → 有诊断', noV.reason);

    const zero = J.judge({ type: 'eigen', value: 2, tol: 0.1, tolDeg: 4 },
                         ctx(Object.assign({}, o, { vectors: [{ id: 'v', data: [0, 0] }] })));
    ok(/零向量/.test(zero.reason), '零向量 → 诊断说「零向量」', zero.reason);

    const lamBad = J.judge({ type: 'eigen', value: 5, tol: 0.05, tolDeg: 4 },
                           ctx(Object.assign({}, o, { matrix: [[2, 0], [0, 2]] })));
    ok(/缩放倍数|λ/.test(lamBad.reason), 'λ 不符 → 诊断说「缩放倍数」', lamBad.reason);

    /* ④ 不共线 —— 必须让 λ **通过**而角度不通过。
       A=[[1,1],[0,1]]、v=[1,1]：Av=[2,1]，λ=(Av·v)/(v·v)=3/2=1.5。
       所以目标 λ 要写 1.5（而不是 2）：写 2 会先在 λ 处返回 false，
       走不到共线检查 —— 又是用例写错，不是实现错。
       v 与 Av 夹角：cos=(2+1)/(√2·√5)≈0.949 → 偏离 18.4° > 4°。 */
    const angBad = J.judge({ type: 'eigen', value: 1.5, tol: 0.05, tolDeg: 4 },
                           ctx({ matrix: [[1, 1], [0, 1]], vectors: [{ id: 'v', data: [1, 1] }] }));
    ok(!angBad.pass, '不共线 → 判不过', 'pass=' + angBad.pass);
    ok(/不共线/.test(angBad.reason), '不共线 → 诊断说「不共线」', angBad.reason);
    ok(/λ/.test(angBad.reason), '诊断同时说明 λ 已符合，把范围讲清');
}

/* ---------------- collinear：3 条失败条件 ---------------- */
console.log('');
console.log('collinear（3 条失败条件）');
{
    const short = J.judge({ type: 'collinear', tolDeg: 4 },
                          ctx({ vectors: [{ id: 'v', data: [0.1, 0] }] }));
    ok(/太短/.test(short.reason), 'v 太短 → 诊断说「太短」', short.reason);

    const squashed = J.judge({ type: 'collinear', tolDeg: 4 },
                             ctx({ matrix: [[0, 0], [0, 0]], vectors: [{ id: 'v', data: [1, 1] }] }));
    ok(/零向量/.test(squashed.reason), 'Av 是零向量 → 诊断说明「压扁」', squashed.reason);

    const notCol = J.judge({ type: 'collinear', tolDeg: 4 },
                           ctx({ matrix: [[0, -1], [1, 0]], vectors: [{ id: 'v', data: [1, 0] }] }));
    ok(/不共线/.test(notCol.reason), '不共线 → 诊断说「不共线」', notCol.reason);

    /* 反向共线（180°）必须判过 —— 这是真实缺陷 ④ 的回归 */
    const opposite = J.judge({ type: 'collinear', tolDeg: 4 },
                             ctx({ matrix: [[-1, 0], [0, -1]], vectors: [{ id: 'v', data: [1, 0] }] }));
    ok(opposite.pass === true, '反向共线（180°）→ 判过（真实缺陷回归）');
}

/* ---------------- vector-angle：4 条失败条件 ---------------- */
console.log('');
console.log('vector-angle（4 条失败条件）');
{
    const mk = (a, b, extra) => ctx(Object.assign({
        vectors: [{ id: 'u', data: a }, { id: 'v', data: b }]
    }, extra || {}));

    const zero = J.judge({ type: 'vector-angle', a: 'u', b: 'v', value: 90, tol: 5 },
                         mk([0, 0], [1, 0]));
    ok(/长度为零/.test(zero.reason), '零向量 → 诊断说「长度为零」', zero.reason);

    const notUnit = J.judge({ type: 'vector-angle', a: 'u', b: 'v', value: 90, tol: 5, unit: true },
                            mk([3, 0], [0, 1]));
    ok(/单位向量/.test(notUnit.reason), '非单位向量 → 诊断说「单位向量」', notUnit.reason);

    const angBad = J.judge({ type: 'vector-angle', a: 'u', b: 'v', value: 90, tol: 5 },
                           mk([1, 0], [1, 0]));
    ok(/夹角/.test(angBad.reason), '夹角不符 → 诊断说「夹角」', angBad.reason);
}

console.log('');
console.log(`通过 ${pass} / ${pass + fail}`);
if (fail) {
    console.log(`失败 ${fail} 项 ✗`);
    failures.forEach(f => console.log('   - ' + f));
    process.exit(1);
}
console.log('全部通过 ✓ 多条件类型在每条失败路径上都给出了对的诊断');
