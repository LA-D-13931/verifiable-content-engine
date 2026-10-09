#!/usr/bin/env node
/* 原语层的独立裁决者：用精确有理数（BigInt）复算 det 与 rank。
   ============================================================
   为什么需要它：这是本项目此前最深的那个洞 —— 判题层与原语层的
   「真值」全部来自作者自己的实现。`verify-diagnostics` 里那句「证书数值与
   独立复算一致」，用的其实是**同一个** Mat.det / Mat.rank，只证明
   「证书字段确实装了原语输出」，不独立于原语实现。

   本工具提供一个**算法与外层完全不同的**裁决者：
     · 外层：IEEE 双精度 + 容差（EPS × 尺度^阶数），部分主元高斯消元
     · 这里：BigInt 精确有理数，**零容差**，按定义算行列式与秩

   对内容里的整数矩阵，精确算术是**可以断言的真理**，所以两边必须一致
   （或落在零政策的可解释分支里）。

   与零政策的关系：本工具不否定零政策，而是把它当成**必须被显式解释**的分支——
     若 |det| ≥ 阈值（政策认为非奇异）→ 必须 rank = 精确秩、det = 精确行列式
     若 |det| <  阈值（政策认为奇异）→ 必须 det = 0 且 rank < n
   两种之外的不一致一律报错。

   用法：node tools/audit-matrix-exact.mjs
   ============================================================ */
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const APP = dirname(HERE);
const SITE = dirname(dirname(APP));
const ENGINE = join(SITE, 'engine-core');
const require = createRequire(import.meta.url);
const Mat = require(join(ENGINE, 'mat.js'));

/* ---------------- 精确有理数 ---------------- */
const gcd = (a, b) => { a = a < 0n ? -a : a; b = b < 0n ? -b : b; while (b) { [a, b] = [b, a % b]; } return a; };
function frac(n, d = 1n) {
    if (d === 0n) throw new Error('分母为零');
    if (d < 0n) { n = -n; d = -d; }
    const g = gcd(n, d) || 1n;
    return [n / g, d / g];
}
const fAdd = (a, b) => frac(a[0] * b[1] + b[0] * a[1], a[1] * b[1]);
const fSub = (a, b) => frac(a[0] * b[1] - b[0] * a[1], a[1] * b[1]);
const fMul = (a, b) => frac(a[0] * b[0], a[1] * b[1]);
const fDiv = (a, b) => frac(a[0] * b[1], a[1] * b[0]);
const fIsZero = (a) => a[0] === 0n;
const fToNumber = (a) => Number(a[0]) / Number(a[1]);

/* 精确行列式：分数域上的拉普拉斯展开（n ≤ 4，够用且不易写错） */
function exactDet(M) {
    const n = M.length;
    if (n === 1) return M[0][0];
    if (n === 2) return fSub(fMul(M[0][0], M[1][1]), fMul(M[0][1], M[1][0]));
    let total = frac(0n);
    for (let j = 0; j < n; j++) {
        const minor = M.slice(1).map(row => row.filter((_, c) => c !== j));
        const term = fMul(M[0][j], exactDet(minor));
        total = j % 2 === 0 ? fAdd(total, term) : fSub(total, term);
    }
    return total;
}

/* 精确秩：分数域高斯消元，零容差 */
function exactRank(M) {
    const a = M.map(r => r.slice());
    const rows = a.length, cols = a[0].length;
    let r = 0;
    for (let c = 0; c < cols && r < rows; c++) {
        let p = -1;
        for (let i = r; i < rows; i++) if (!fIsZero(a[i][c])) { p = i; break; }
        if (p < 0) continue;
        [a[r], a[p]] = [a[p], a[r]];
        for (let i = r + 1; i < rows; i++) {
            if (fIsZero(a[i][c])) continue;
            const f = fDiv(a[i][c], a[r][c]);
            for (let j = c; j < cols; j++) a[i][j] = fSub(a[i][j], fMul(f, a[r][j]));
        }
        r++;
    }
    return r;
}

/* ---------------- 挖出内容里的方阵 ---------------- */
const labs = JSON.parse(readFileSync(join(APP, 'assets', 'js', 'labs.json'), 'utf-8')).labs;
const found = [];
(function walk(o, path) {
    if (Array.isArray(o)) {
        const square = o.length >= 2 && o.length <= 3 && o.every(r =>
            Array.isArray(r) && r.length === o.length &&
            r.every(x => typeof x === 'number' && isFinite(x)));
        if (square) { found.push({ path, m: o }); return; }
        o.forEach((x, i) => walk(x, `${path}[${i}]`));
    } else if (o && typeof o === 'object') {
        for (const k of Object.keys(o)) walk(o[k], `${path}.${k}`);
    }
})(labs, 'labs');

/* ---------------- 逐个对照 ---------------- */
const policyThreshold = (M, order) => {
    let s = 0;
    for (const row of M) for (const x of row) s = Math.max(s, Math.abs(x));
    if (!(s > 0)) s = 1;
    return Mat.EPS * Math.pow(s, order);
};

let bad = 0, checked = 0, policyZero = 0;
const problems = [];
for (const { path, m } of found) {
    const n = m.length;
    const E = m.map(row => row.map(x => frac(BigInt(Math.round(x * 1e9)), 1000000000n)));
    const det = exactDet(E), rank = exactRank(E);
    const detNum = fToNumber(det);
    const thr = policyThreshold(m, n);
    const matDet = Mat.det(m), matRank = Mat.rank(m);
    checked++;

    if (Math.abs(detNum) >= thr) {
        // 政策认为非奇异：必须与精确值一致
        const detOk = Math.abs(matDet - detNum) <= Math.max(1e-9, Math.abs(detNum) * 1e-9);
        const rankOk = matRank === rank;
        if (!detOk || !rankOk) {
            bad++;
            problems.push(`${path}  ${JSON.stringify(m)}\n      精确: det=${detNum}  rank=${rank}｜引擎: det=${matDet}  rank=${matRank}`);
        }
    } else {
        // 政策认为奇异：必须 det=0 且 rank<n —— 这是**可解释**的分支，不算错
        policyZero++;
        if (!(matDet === 0 && matRank < n)) {
            bad++;
            problems.push(`${path}  ${JSON.stringify(m)}\n      政策奇异分支未遵守：引擎 det=${matDet}（应 0） rank=${matRank}（应 <${n}）`);
        }
    }
}

console.log('=== 原语层独立裁决（BigInt 精确有理数 vs 双精度+容差）===');
console.log(`内容里的方阵：${checked} 个（2×2 / 3×3）`);
console.log(`其中落在零政策「奇异」分支：${policyZero} 个（这些按政策应报 det=0、rank<n）`);
console.log('');
if (bad) {
    console.log(`不一致 ${bad} 处 ✗`);
    problems.slice(0, 12).forEach(p => console.log('   - ' + p));
    process.exit(1);
}
console.log('全部一致 ✓ 每个方阵要么与精确算术完全吻合，要么落在可解释的零政策分支里');

/* 顺带用精确算术验一遍共享向量里那些整数矩阵的证书数值 */
const vec = JSON.parse(readFileSync(join(ENGINE, 'mat-vectors.json'), 'utf-8')).vectors;
let vChecked = 0, vBad = 0;
for (const v of vec) {
    if (v.fn !== 'det' && v.fn !== 'rank') continue;
    const M = v.args && v.args[0];
    if (!Array.isArray(M) || !Array.isArray(M[0])) continue;
    if (!M.every(r => r.every(x => typeof x === 'number' && Number.isInteger(x)))) continue;
    const E = M.map(r => r.map(x => frac(BigInt(x))));
    const d = fToNumber(exactDet(E)), r = exactRank(E);
    vChecked++;
    const ok = (v.fn === 'det')
        ? (Math.abs(d) < policyThreshold(M, M.length) ? v.expect === 0 : Math.abs(v.expect - d) < 1e-9)
        : (v.expect === r);
    if (!ok) { vBad++; console.log(`   ✗ 向量 ${v.note}: 精确 ${v.fn}=${v.fn === 'det' ? d : r}，记录 ${v.expect}`); }
}
console.log(`整数矩阵向量：${vChecked} 条，与精确算术不一致 ${vBad} 条${vBad ? ' ✗' : ' ✓'}`);
process.exit(vBad ? 1 : 0);
