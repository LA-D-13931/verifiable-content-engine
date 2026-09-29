#!/usr/bin/env node
/* 判题注册表的离线回归测试
   ============================================================
   这个套件**不需要浏览器、不需要线代数据**——判题逻辑只依赖传入的 ctx，
   所以在 Node 里就能跑。这正是「引擎可独立测试」的证明（W1-5）。

   用例分两类：
     · 常规用例   —— 覆盖每个判题类型的通过与不通过
     · 回归用例   —— 复现本项目真实发生过的缺陷，防止再次发生

   运行：node tools/verify-registry.mjs
   ============================================================ */
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const APP = dirname(HERE);                        // apps/linalg-lab
const SITE = dirname(dirname(APP));               // 仓库根
const ENGINE = join(SITE, 'engine-core');
const require = createRequire(import.meta.url);

const R = require(join(ENGINE, 'registry.js'));
const Mat = require(join(ENGINE, 'mat.js'));
/* 领域插件也加载进来：回归用例要同时覆盖引擎层与领域层。 */
let Linalg = null;
try { Linalg = require(join(ENGINE, 'domains', 'linalg', 'judge.js')); } catch (e) { /* 无 */ }

let pass = 0, fail = 0;
const failures = [];

function ctx(over) {
    return Object.assign({
        taskId: 't1',
        matrix: null,
        vectors: [],
        lines: [],
        choices: {},
        actionLog: [],          // 原实现用数组，不是对象
        Mat: Mat,
        vecEq: (a, b, tol) => {
            const t = tol == null ? 0.15 : tol;
            return a.length === b.length && a.every((x, i) => Math.abs(x - b[i]) <= t);
        }
    }, over || {});
}

/* 断言：判定通过/不通过，并可核对原因与证书 */
function t(name, check, context, expect) {
    const r = R.run(check, context);
    if (r === null) {
        fail++; failures.push(`${name}：类型 ${check.type} 未注册`);
        console.log(`  ✗ ${name} —— 类型未注册`);
        return;
    }
    const problems = [];
    if (r.pass !== expect.pass) problems.push(`期望 pass=${expect.pass} 实得 ${r.pass}`);
    if (expect.reasonIncludes && !String(r.reason).includes(expect.reasonIncludes)) {
        problems.push(`原因里应包含「${expect.reasonIncludes}」，实为「${r.reason}」`);
    }
    if (expect.certificate && !r.certificate) problems.push('应带证书但没有');
    if (problems.length) {
        fail++; failures.push(`${name}：${problems.join('；')}`);
        console.log(`  ✗ ${name}`);
        problems.forEach(p => console.log(`      ${p}`));
    } else {
        pass++;
        console.log(`  ✓ ${name}`);
    }
}

console.log('=== 判题注册表：离线回归测试 ===');
console.log(`已注册类型：${R.types().join(', ')}`);
console.log('');

/* ---------------- vector-at ---------------- */
console.log('vector-at（向量是否停在目标位置）');
t('命中目标', { type: 'vector-at', target: 'v', to: [2, 1] },
  ctx({ vectors: [{ id: 'v', data: [2, 1] }] }), { pass: true, certificate: true });
t('差一点点但在容差内', { type: 'vector-at', target: 'v', to: [2, 1], tol: 0.2 },
  ctx({ vectors: [{ id: 'v', data: [2.1, 1.05] }] }), { pass: true });
t('超出容差', { type: 'vector-at', target: 'v', to: [2, 1] },
  ctx({ vectors: [{ id: 'v', data: [2.5, 1] }] }),
  { pass: false, reasonIncludes: '目标', certificate: true });
t('向量不存在', { type: 'vector-at', target: 'nope', to: [1, 1] },
  ctx({ vectors: [] }), { pass: false, reasonIncludes: '找不到' });

/* ---------------- av-at ---------------- */
console.log('\nav-at（变换后的向量是否命中目标）');
t('Av 命中', { type: 'av-at', to: [2, 2] },
  ctx({ matrix: [[1, 0], [0, 1]], vectors: [{ id: 'v', data: [2, 2] }] }),
  { pass: true, certificate: true });
t('Av 未命中', { type: 'av-at', to: [9, 9] },
  ctx({ matrix: [[1, 0], [0, 1]], vectors: [{ id: 'v', data: [2, 2] }] }),
  { pass: false, reasonIncludes: 'Av', certificate: true });
t('没有矩阵', { type: 'av-at', to: [1, 1] },
  ctx({ matrix: null, vectors: [{ id: 'v', data: [1, 1] }] }),
  { pass: false, reasonIncludes: '缺少' });

/* ---------------- matrix-col-at ---------------- */
console.log('\nmatrix-col-at（矩阵某一列是否等于目标）');
t('第 1 列命中', { type: 'matrix-col-at', col: 0, to: [1, 2] },
  ctx({ matrix: [[1, 3], [2, 4]] }), { pass: true, certificate: true });
t('第 2 列命中', { type: 'matrix-col-at', col: 1, to: [3, 4] },
  ctx({ matrix: [[1, 3], [2, 4]] }), { pass: true });
t('列不匹配', { type: 'matrix-col-at', col: 0, to: [9, 9] },
  ctx({ matrix: [[1, 3], [2, 4]] }),
  { pass: false, reasonIncludes: '第 1 列', certificate: true });

/* ---------------- match-matrix ---------------- */
console.log('\nmatch-matrix（整个矩阵是否等于目标）');
t('完全相等', { type: 'match-matrix', matrix: [[2, 0], [0, 2]] },
  ctx({ matrix: [[2, 0], [0, 2]] }), { pass: true, certificate: true });
t('在容差内', { type: 'match-matrix', matrix: [[2, 0], [0, 2]], tol: 0.1 },
  ctx({ matrix: [[2.05, 0], [0, 1.97]] }), { pass: true });
t('超出容差并指出位置', { type: 'match-matrix', matrix: [[2, 0], [0, 2]], tol: 0.05 },
  ctx({ matrix: [[2, 0], [0, 9]] }),
  { pass: false, reasonIncludes: '第 2 行第 2 列', certificate: true });

/* ---------------- dot ---------------- */
console.log('\ndot（点积是否等于目标值）');
t('点积 eq 命中', { type: 'dot', a: 'u', b: 'v', op: 'eq', value: 4 },
  ctx({ vectors: [{ id: 'u', data: [2, 0] }, { id: 'v', data: [2, 1] }] }),
  { pass: true, certificate: true });
t('点积 eq 不命中', { type: 'dot', a: 'u', b: 'v', op: 'eq', value: 4 },
  ctx({ vectors: [{ id: 'u', data: [2, 0] }, { id: 'v', data: [1, -2] }] }),
  { pass: false, reasonIncludes: '点积', certificate: true });
t('点积 lt 通过', { type: 'dot', a: 'u', b: 'v', op: 'lt', value: 5 },
  ctx({ vectors: [{ id: 'u', data: [2, 0] }, { id: 'v', data: [1, -2] }] }),
  { pass: true });
t('点积 gt 通过', { type: 'dot', a: 'u', b: 'v', op: 'gt', value: 3 },
  ctx({ vectors: [{ id: 'u', data: [2, 0] }, { id: 'v', data: [2, 1] }] }),
  { pass: true });
t('点积 op 非法时判不过', { type: 'dot', a: 'u', b: 'v', op: 'ne', value: 4 },
  ctx({ vectors: [{ id: 'u', data: [2, 0] }, { id: 'v', data: [2, 1] }] }),
  { pass: false });

/* ---------------- choice ---------------- */
console.log('\nchoice（辨析题：只判定用户实际选中那一项）');
t('选对了', { type: 'choice', correct: 1 },
  ctx({ choices: { t1: 1 } }), { pass: true, certificate: true });
t('选错了', { type: 'choice', correct: 1 },
  ctx({ choices: { t1: 0 } }),
  { pass: false, reasonIncludes: '第 1 项', certificate: true });
t('还没选', { type: 'choice', correct: 1 },
  ctx({ choices: {} }), { pass: false, reasonIncludes: '还没有选择' });
t('缺少 taskId 时判不过', { type: 'choice', correct: 1 },
  ctx({ taskId: null, choices: { t1: 1 } }),
  { pass: false, reasonIncludes: '任务标识' });

/* ---------------- actions ---------------- */
console.log('\nactions（声明的动作是否都产生过可观测事件）');
t('动作都发生过', { type: 'actions', all: ['try-inverse'] },
  ctx({ actionLog: ['try-inverse'] }), { pass: true, certificate: true });
t('动作没发生过', { type: 'actions', all: ['try-inverse'] },
  ctx({ actionLog: [] }),
  { pass: false, reasonIncludes: 'try-inverse', certificate: true });
/* ordered：要求按序出现。中间允许夹别的动作（子序列匹配）。 */
t('有序动作按序完成', { type: 'actions', all: ['a', 'b'], ordered: true },
  ctx({ actionLog: ['a', 'x', 'b'] }), { pass: true, certificate: true });
t('有序动作顺序颠倒', { type: 'actions', all: ['a', 'b'], ordered: true },
  ctx({ actionLog: ['b', 'a'] }),
  { pass: false, reasonIncludes: '顺序', certificate: true });
t('有序动作只完成一半', { type: 'actions', all: ['a', 'b'], ordered: true },
  ctx({ actionLog: ['a'] }),
  { pass: false, reasonIncludes: '1 / 2', certificate: true });

/* ============================================================
   回归用例：复现本项目真实发生过的缺陷
   ============================================================ */
console.log('\n=== 回归用例（复现真实缺陷）===');

/* 缺陷 6-2：按钮「试着求 A⁻¹」的实现遗漏了写日志，
   于是依赖它的动作型任务**在任何输入下都不可能为真**。
   本用例锁定：注册表必须能识别出「缺少动作」并给出可读原因。 */
console.log('回归 · 实验 6-2：按钮不写日志导致任务永远无法完成');
{
    const check = { type: 'actions', all: ['try-inverse'] };
    // 用户点了 100 次，但日志始终为空（复现当时的实现）
    const context = ctx({ actionLog: [] });
    const r = R.run(check, context);
    if (r.pass === false && /try-inverse/.test(r.reason)) {
        pass++; console.log('  ✓ 判定为不通过，且明确指出缺少哪个动作');
    } else {
        fail++; failures.push('6-2 回归：未能识别缺失动作');
        console.log('  ✗ 未识别出缺失动作');
    }
    // 补上日志后必须立即通过 —— 证明判定本身是活的，不是恒假
    const r2 = R.run(check, ctx({ actionLog: ['try-inverse'] }));
    if (r2.pass === true) {
        pass++; console.log('  ✓ 补上日志后立即通过（判定不是恒假）');
    } else {
        fail++; failures.push('6-2 回归：补上日志后仍不通过');
        console.log('  ✗ 补上日志后仍不通过');
    }
}

/* 缺陷：辨析题曾把「所有选项」都判为正确。
   本用例锁定：choice 只能接受 check.correct 指定的那一项。 */
console.log('回归 · 辨析题：不能把多个选项都判为对');
{
    const check = { type: 'choice', correct: 2 };
    const wrongPicks = [0, 1, 3];
    const bad = wrongPicks.filter(i => R.run(check, ctx({ choices: { t1: i } })).pass);
    if (bad.length === 0) {
        pass++; console.log('  ✓ 错误选项全部判为不通过（0/1/3 无一漏过）');
    } else {
        fail++; failures.push(`辨析题回归：第 ${bad.join('、')} 项被误判为正确`);
        console.log(`  ✗ 第 ${bad.join('、')} 项被误判为正确`);
    }
}

/* 缺陷 4-4：矩阵 A·B·C 手算错误（写成了 [[-1,0],[2,1]]，正确是 [[2,-1],[2,0]]）。
   界面上矩阵显示正常、网格变形正常，任务却永远判不过。
   本用例锁定：match-matrix 必须能分辨出这两个矩阵，不能因为容差过宽而放行。 */
console.log('回归 · 实验 4-4：手算矩阵数值错误必须被判据分辨出来');
{
    const wrong = [[-1, 0], [2, 1]];      // 当时写错的值
    const right = [[2, -1], [2, 0]];      // 正确值
    const check = { type: 'match-matrix', matrix: right, tol: 0.05 };
    const rWrong = R.run(check, ctx({ matrix: wrong }));
    const rRight = R.run(check, ctx({ matrix: right }));
    if (rWrong.pass === false && rRight.pass === true) {
        pass++; console.log('  ✓ 错误矩阵判不过、正确矩阵判过（判据能分辨）');
        console.log('      诊断：' + rWrong.reason);
    } else {
        fail++; failures.push('4-4 回归：match-matrix 无法分辨错误矩阵');
        console.log(`  ✗ 错误矩阵 pass=${rWrong.pass}，正确矩阵 pass=${rRight.pass}`);
    }
}

/* 缺陷：collinear / eigen 曾把「反向共线」当成不共线。
   原因是直接用 angleBetweenDeg 与角度阈值比较，而反向共线给的是 180°。
   修法是折回锐角：min(ang, 180 - ang)。
   本用例锁定：eigen 在反向共线（λ = −1）时必须判过。 */
console.log('回归 · 反向共线（180°）不能被误判为不共线');
if (!Linalg) {
    console.log('  · 领域插件未加载，跳过');
} else {
    const check = { type: 'eigen', value: -1, tol: 0.12, tolDeg: 4 };
    // 反射矩阵 [[0,1],[1,0]]：v=(1,−1) 是特征向量，特征值 −1（反向）
    const context = ctx({
        matrix: [[0, 1], [1, 0]],
        vectors: [{ id: 'v', data: [1, -1] }]
    });
    const r = Linalg.judge(check, context);
    if (r && r.pass === true) {
        pass++; console.log('  ✓ 反向共线（λ = −1）判过');
    } else {
        fail++; failures.push('反向共线回归：eigen 判不过');
        console.log(`  ✗ 反向共线判为 ${JSON.stringify(r)}`);
    }
    // 反例：同向共线但 λ 不对，必须判不过 —— 证明判定不是恒真
    const r2 = Linalg.judge({ type: 'eigen', value: 5, tol: 0.12, tolDeg: 4 }, context);
    if (r2 && r2.pass === false) {
        pass++; console.log('  ✓ λ 不符时判不过（判定不是恒真）');
    } else {
        fail++; failures.push('反向共线回归：λ 不符却判过');
        console.log('  ✗ λ 不符却判过');
    }
}

console.log('');
console.log(`通过 ${pass} / ${pass + fail}`);
if (fail) {
    console.log(`失败 ${fail} 项 ✗`);
    failures.forEach(f => console.log('   - ' + f));
    process.exit(1);
}
console.log('全部通过 ✓ 判题注册表可离线独立测试，无需浏览器与科目数据');
