#!/usr/bin/env node
/* 验证 assets/js/mat.js 与 engine/mat.py 算的是同一个数学。
   ============================================================
   做法：读 engine/mat-vectors.json（77 组测试向量，由 Python 侧生成），
   在 JS 侧逐条重算并比对。Python 侧的自检由 `python3 engine/mat.py` 负责。

   两侧都通过，才说明「浏览器判题」与「Python 内容校验」用的是同一套数学——
   这是校验器可信的前提。

   用法：node tools/verify-mat.mjs
   ============================================================ */
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const SITE = dirname(HERE);
const require = createRequire(import.meta.url);

const Mat = require(join(SITE, 'assets', 'js', 'mat.js'));
const vectors = JSON.parse(
    readFileSync(join(SITE, 'engine', 'mat-vectors.json'), 'utf-8'));

console.log('=== mat 原语：JS 与 Python 一致性校验 ===');
console.log(`测试向量：${vectors.length} 组`);
console.log('');

const fail = [];
let checked = 0;

for (const v of vectors) {
    const fn = Mat[v.fn];
    if (typeof fn !== 'function') {
        fail.push(`${v.fn}: JS 侧没有这个函数`);
        continue;
    }
    // 逐个调用（不借助 Mat.selftest，以便独立于被测实现自身的比较逻辑）
    let got;
    try {
        got = fn(...v.args);
    } catch (err) {
        fail.push(`${v.fn}(${JSON.stringify(v.args)}) 抛异常：${err.message}`);
        continue;
    }
    checked++;
    if (!deepEqual(got, v.expect)) {
        fail.push(`${v.fn}(${JSON.stringify(v.args)})\n      期望 ${JSON.stringify(v.expect)}\n      实得 ${JSON.stringify(got)}`);
    }
}

function deepEqual(a, b) {
    if (Array.isArray(a) && Array.isArray(b)) {
        return a.length === b.length && a.every((x, i) => deepEqual(x, b[i]));
    }
    if (a && b && typeof a === 'object' && typeof b === 'object') {
        const ka = Object.keys(a), kb = Object.keys(b);
        if (ka.length !== kb.length) return false;
        return ka.every(k => deepEqual(a[k], b[k]));
    }
    if (a === null || b === null) return a === b;
    if (typeof a === 'number' && typeof b === 'number') {
        if (!Number.isFinite(a) || !Number.isFinite(b)) return a === b;
        return Math.abs(a - b) < 1e-9;
    }
    return a === b;
}

// 顺带跑一遍 mat.js 自带的自检（它用 Mat.selftest），确保那个入口也能用
const st = Mat.selftest(vectors);

console.log(`  已重算：${checked} / ${vectors.length} 组`);
console.log(`  Mat.selftest()：通过 ${st.total - st.failed} / ${st.total}`);
console.log('');

if (fail.length || st.failed) {
    if (fail.length) {
        console.log(`✗ 不一致 ${fail.length} 组：`);
        fail.slice(0, 12).forEach(f => console.log('   - ' + f));
    }
    if (st.failed) {
        console.log(`✗ Mat.selftest 报 ${st.failed} 组失败：`);
        st.details.slice(0, 12).forEach(d => console.log('   - ' + JSON.stringify(d)));
    }
    process.exit(1);
}

// 再报告一下关键边界用例的实际取值，便于人工确认语义正确
console.log('关键边界用例的实际结果：');
const show = (fn, ...args) => {
    const r = Mat[fn](...args);
    console.log(`  ${fn}(${JSON.stringify(args)}) = ${JSON.stringify(r)}`);
};
show('det', [[1, 2], [2, 4.0000000001]]);
show('rank', [[1, 2], [2, 4.0000000001]]);
show('inv2', [[1, 2], [2, 4]]);
show('onSpan', [[1, 2], [2, 4]], [2, 2]);
show('angleBetweenDeg', [1, 1], [-1, -1]);
show('intersectLines', [{ a: 1, b: 0, c: 1 }, { a: 0, b: 1, c: 2 }]);

// ---------- 顺带跑 Python 侧自检 ----------
// 这样一条命令就能证明两侧一致，不需要人工分两步跑。
console.log('');
console.log('=== 调用 Python 侧自检 engine/mat.py ===');
const { spawnSync } = await import('node:child_process');
const py = spawnSync('python3', [join(SITE, 'engine', 'mat.py')],
                     { encoding: 'utf-8', cwd: SITE });
process.stdout.write(py.stdout || '');
if (py.stderr) process.stderr.write(py.stderr);
if (py.status !== 0) {
    console.log('✗ Python 侧自检失败');
    process.exit(1);
}

console.log('');
console.log('全部通过 ✓  JS 与 Python 算的是同一个数学（两侧各 77 组向量）');
