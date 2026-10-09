#!/usr/bin/env node
/* 判据区分力审计：抓「恒真判据」——这正是本项目此前主动承认的盲点。
   ============================================================
   盲点是什么：校验页用的是「最有利上下文」——动作日志填满、选择题选正确项、
   矩阵按判据反推。在这个构造下，**任何状态都通过的判据**（恒真）看起来一切正常。
   送审说明第七节第 7 条就是这条：「如果作者把判据写成恒真，这个模式查不出来」。

   本工具的做法：对每个任务，构造两组「本该判不过」的输入，看判据是否照样通过。

     A 上下文扰动 —— 把状态改成明显错的（矩阵置零、向量挪远、动作日志清空…）
     B 判据扰动   —— 把判据自己的目标值改成荒谬值（value 改 1e9、to 改 [1e9,…]…）

   判定：
     · 只要**任一组**探针让判据返回 pass:false → 这条判据有区分力
     · **所有**探针都 pass:true → 说明它区分不了对错，报为「疑似无区分力」
     · 探针抛异常 → 单独报（在错误输入上也应当给出判不过，而不是崩）

   为什两组都要：有些判题的判据完全来自 check 本身（例如高数的极限/导数），
   上下文扰动对它毫无影响；只有扰动判据本身才能证伪它。

   用法：node tools/audit-tautology.mjs
   ============================================================ */
import { readFileSync, readdirSync, existsSync } from 'node:fs';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { makeJudge, ctxFor } from './judge-ctx.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const APP = dirname(HERE);
const SITE = dirname(dirname(APP));
const ENGINE = join(SITE, 'engine-core');
const require = createRequire(import.meta.url);

const Mat = require(join(ENGINE, 'mat.js'));
const Registry = require(join(ENGINE, 'registry.js'));

const domainsDir = join(ENGINE, 'domains');
const domains = existsSync(domainsDir)
    ? readdirSync(domainsDir).filter(d => !d.startsWith('.')).sort() : [];
const plugins = [];
for (const d of domains) {
    const file = join(domainsDir, d, 'judge.js');
    if (!existsSync(file)) continue;
    plugins.push({ domain: d, api: require(file) });
}
const judge = makeJudge(Registry, plugins, Mat);

const labs = JSON.parse(readFileSync(join(APP, 'assets', 'js', 'labs.json'), 'utf-8')).labs;
const extraLabs = [];
for (const p of plugins) {
    if (Array.isArray(p.api.sampleLabs)) {
        p.api.sampleLabs.forEach(l => extraLabs.push(Object.assign({ __domain: p.domain }, l)));
    }
}

/* ---------------- A 上下文扰动 ---------------- */
const CTX_PROBES = [
    ['矩阵置零', b => ({ ...b, matrix: [[0, 0], [0, 0]] })],
    ['矩阵置空', b => ({ ...b, matrix: null })],
    ['矩阵换成 2I', b => ({ ...b, matrix: [[2, 0], [0, 2]] })],
    ['向量挪到远处', b => ({ ...b, vectors: (b.vectors || []).map(v => ({ ...v, data: [7.5, -3.25] })) })],
    ['向量全置零', b => ({ ...b, vectors: (b.vectors || []).map(v => ({ ...v, data: [0, 0] })) })],
    ['动作日志清空', b => ({ ...b, actionLog: [] })],
    ['选项改为越界', b => ({ ...b, choices: Object.fromEntries(Object.keys(b.choices || {}).map(k => [k, 99])) })],
    ['直线清空', b => ({ ...b, lines: [] })],
];

/* ---------------- B 判据扰动 ---------------- */
const CHECK_PROBES = [
    ['value 改 1e9', c => ('value' in c ? { ...c, value: 1e9 } : null)],
    ['to 改远处', c => (Array.isArray(c.to) ? { ...c, to: c.to.map((_, i) => (i % 2 ? -1e9 : 1e9)) } : null)],
    ['node 改远处', c => (Array.isArray(c.node) ? { ...c, node: c.node.map(() => 1e9) } : null)],
    ['minCos 改 1', c => ('minCos' in c ? { ...c, minCos: 1 } : null)],
    ['sign 取反', c => ('sign' in c ? { ...c, sign: -c.sign } : null)],
];

const run = (check, taskId, ctx) => {
    try {
        const out = judge(check, taskId, ctx);
        return out.result ? { pass: out.result.pass === true } : { none: true };
    } catch (e) {
        return { threw: String(e && e.message || e) };
    }
};

const rows = [];
for (const lab of labs.concat(extraLabs)) {
    for (const task of lab.tasks) {
        const check = Object.assign({ __taskId: task.id }, task.check);
        const base = ctxFor(check, lab);
        const probes = [];

        for (const [name, f] of CTX_PROBES) {
            probes.push([name, run(check, task.id, f(base))]);
        }
        for (const [name, f] of CHECK_PROBES) {
            const c2 = f(check);
            if (c2) probes.push([name, run(c2, task.id, base)]);
        }

        const fails = probes.filter(([, r]) => r.pass === false).length;
        const throws = probes.filter(([, r]) => r.threw);
        rows.push({
            lab: lab.id, task: task.id, type: check.type,
            nProbes: probes.length, fails, throws,
            alwaysPass: probes.length > 0 && fails === 0 && throws.length === 0,
            base: run(check, task.id, base),
        });
    }
}

/* ---------------- 报告 ---------------- */
console.log('=== 判据区分力审计（抓恒真判据）===');
console.log(`任务总数：${rows.length}    每个任务最多 ${CTX_PROBES.length + CHECK_PROBES.length} 组探针`);
console.log('');

const byType = {};
for (const r of rows) {
    const t = byType[r.type] = byType[r.type] || { n: 0, minFails: Infinity, maxFails: 0, always: [] };
    t.n++;
    t.minFails = Math.min(t.minFails, r.fails);
    t.maxFails = Math.max(t.maxFails, r.fails);
    if (r.alwaysPass) t.always.push(`${r.lab}/${r.task}`);
}
console.log('逐类型（探针让判据判不过的最少/最多次数）');
for (const [t, s] of Object.entries(byType).sort()) {
    const flag = s.minFails === 0 ? '  ← 有任务对全部探针都判通过' : '';
    console.log(`  ${t.padEnd(18)} ${String(s.n).padStart(3)} 个   ${String(s.minFails).padStart(2)}–${String(s.maxFails).padStart(2)}${flag}`);
}

const always = rows.filter(r => r.alwaysPass);
const threw = rows.filter(r => r.throws.length);
console.log('');
console.log(`① 疑似无区分力（所有探针都判通过）：${always.length} 个`);
for (const r of always.slice(0, 20)) {
    console.log(`   - ${r.lab}/${r.task}  [${r.type}]  探针 ${r.nProbes} 组全部通过`);
}
if (always.length > 20) console.log(`   … 另有 ${always.length - 20} 个`);
console.log('');
console.log(`② 探针上抛异常：${threw.length} 个`);
for (const r of threw.slice(0, 10)) {
    console.log(`   - ${r.lab}/${r.task}  [${r.type}]  ${r.throws[0][0]}：${r.throws[0][1].threw}`);
}
if (threw.length > 10) console.log(`   … 另有 ${threw.length - 10} 个`);
console.log('');
const noneRow = rows.filter(r => r.base && r.base.none);
console.log(`③ 最有利上下文下无人接管：${noneRow.length} 个`);

console.log('');
if (always.length || threw.length || noneRow.length) {
    console.log(`发现 ${always.length + threw.length + noneRow.length} 个待查项 ✗`);
    process.exit(1);
}
console.log('全部通过 ✓ 每个任务的判据至少能被一组「本该判不过」的输入证伪 —— 没有恒真判据');
