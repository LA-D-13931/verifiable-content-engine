#!/usr/bin/env node
/* 引擎独立运行校验：不打开浏览器，跑完全部关卡任务。
   ============================================================
   这是「引擎成版本」的可验收定义。它证明三件事：

     ① 引擎的判题分派逻辑**不依赖浏览器**——注册表与领域插件都只读显式
        传入的 ctx，因此可以在 Node 里加载并调用。
     ② 全部关卡任务的判题类型都能被某个处理器接住（没有「类型没人管」）。
     ③ 判题不会抛异常，且返回的是布尔值（结构正确）。

   它**不做**的事：不判断「这个任务该不该通过」——那需要构造合法输入，
   由浏览器侧的 verify-actions / smoke 负责。

   用法：node tools/verify-engine.mjs
   ============================================================ */
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const SITE = dirname(HERE);
const require = createRequire(import.meta.url);

const Mat = require(join(SITE, 'assets', 'js', 'mat.js'));
const Registry = require(join(SITE, 'assets', 'js', 'registry.js'));

/* 按科目目录**自动发现**领域插件，而不是写死线代一个。
   这样新增科目时本脚本无需改动 —— 它检验的是「引擎能不能带多个科目」。 */
import { readdirSync, existsSync } from 'node:fs';
const domainsDir = join(SITE, 'domains');
const domains = existsSync(domainsDir)
    ? readdirSync(domainsDir).filter(d => !d.startsWith('.')).sort()
    : [];
const plugins = [];
for (const d of domains) {
    const file = join(domainsDir, d, 'judge.js');
    if (!existsSync(file)) continue;
    const api = require(file);
    const name = d.charAt(0).toUpperCase() + d.slice(1) + 'Judge';
    plugins.push({ domain: d, api: api, global: globalThis[name] });
}

const labs = JSON.parse(readFileSync(join(SITE, 'assets', 'js', 'labs.json'), 'utf-8')).labs;

/* 各科目还可以提供自己的示例关卡（插件里的 sampleLabs），一并纳入统计。
   linalg 的关卡在 labs.json 里；calculus 目前只有 3 个示例关卡。 */
const extraLabs = [];
for (const p of plugins) {
    if (Array.isArray(p.api.sampleLabs)) {
        p.api.sampleLabs.forEach(l => extraLabs.push(Object.assign({ __domain: p.domain }, l)));
    }
}

if (!plugins.length) { console.error('✗ 未发现任何领域插件'); process.exit(2); }

/* 与 engine.js 的 checkTask 同构：先问注册表，再问领域插件。
   刻意在这里复刻而不是加载 engine.js —— engine.js 依赖 DOM，
   而这里要验证的正是「判题分派不依赖 DOM」。 */
function judge(check, taskId, ctxOver) {
    const ctx = Object.assign({
        taskId: taskId,
        matrix: null,
        matrixSize: 2,
        vectors: [],
        lines: [],
        choices: {},
        actionLog: [],
        Mat: Mat,
        vecEq: (a, b, tol) => {
            const t = tol == null ? 0.15 : tol;
            return a.length === b.length && a.every((x, i) => Math.abs(x - b[i]) <= t);
        }
    }, ctxOver || {});

    const r1 = Registry.run(check, ctx);
    if (r1 !== null) return { layer: 'engine', result: r1 };
    for (const p of plugins) {
        const r = p.api.judge(check, ctx);
        if (r !== null) return { layer: 'domain:' + p.domain, result: r };
    }
    return { layer: 'none', result: null };
}

/* 为每个任务构造一份「能触发该判题类型」的最小上下文，
   目的只是让处理器真的执行到判定分支，而不是在参数检查处提前返回。 */
function ctxFor(check, lab) {
    const scene = lab.scene || {};
    const base = {
        matrix: scene.matrix || [[1, 0], [0, 1]],
        matrixSize: (scene.matrix || [[1, 0], [0, 1]]).length,
        vectors: [{ id: 'v', data: [1, 1] }, { id: 'u', data: [1, 0] }],
        lines: [{ a: 1, b: 0, c: 1 }, { a: 0, b: 1, c: 2 }],
        choices: { [check.__taskId]: 0 },
        actionLog: ['apply-a', 'apply-b', 'apply-c', 'undo-a', 'undo-b',
                    'try-inverse', 'view-ab', 'view-ba', 'play-transform']
    };
    if (check.type === 'dot') {
        base.vectors = [{ id: check.a || 'u', data: [1, 0] },
                        { id: check.b || 'v', data: [2, 1] }];
    }
    if (check.type === 'vector-at' || check.type === 'matrix-col-at') {
        base.vectors = [{ id: check.target || 'v', data: check.to || [0, 0] }];
    }
    return base;
}

console.log('=== 引擎独立运行校验（无浏览器）===');
console.log(`引擎层已注册类型：${Registry.types().length} 种`);
console.log(`领域插件（自动发现）：${plugins.map(p => p.domain).join('、')}`);
console.log(`关卡数据：${labs.length} 个实验（另有各科目示例关卡 ${extraLabs.length} 个）`);
console.log('');

const stats = { total: 0, engineLayer: 0, domainLayer: 0, none: [], threw: [], badType: [] };
const byDomain = {};
const byType = {};

const allLabs = labs.concat(extraLabs);
console.log('');
for (const lab of allLabs) {
    for (const task of lab.tasks) {
        const check = Object.assign({ __taskId: task.id }, task.check);
        stats.total++;
        const key = check.type;
        byType[key] = byType[key] || { n: 0, layer: null };
        byType[key].n++;
        byType[key].domain = lab.__domain || 'linalg';
        try {
            const out = judge(check, task.id, ctxFor(check, lab));
            if (out.layer === 'none') {
                stats.none.push(`${lab.id}/${task.id} → ${check.type}`);
            } else {
                if (out.layer === 'engine') stats.engineLayer++;
                else { stats.domainLayer++; byDomain[out.layer.slice(7)] = (byDomain[out.layer.slice(7)] || 0) + 1; }
                byType[key].layer = out.layer;
                const pass = out.result.pass;      // 两层现在都是 { pass, … }
                if (typeof pass !== 'boolean') {
                    stats.badType.push(`${lab.id}/${task.id} → ${check.type} 返回 ${typeof pass}`);
                }
            }
        } catch (e) {
            stats.threw.push(`${lab.id}/${task.id} → ${check.type}: ${e.message}`);
        }
    }
}

console.log('判题类型分布：');
Object.keys(byType).sort().forEach(t => {
    const where = byType[t].layer === 'engine' ? '引擎层'
                : byType[t].layer ? '领域插件·' + (byType[t].domain || '') : '**无人接管**';
    console.log(`  ${t.padEnd(18)} ${String(byType[t].n).padStart(3)} 个   ${where}`);
});

console.log('');
console.log(`任务总数：${stats.total}`);
console.log(`  引擎层处理：${stats.engineLayer}`);
console.log(`  领域插件处理：${stats.domainLayer}` + (Object.keys(byDomain).length ? '（' + Object.entries(byDomain).map(([k,v])=>k+' '+v).join('、') + '）' : ''));
console.log(`  无人接管：${stats.none.length}`);
console.log(`  抛异常：${stats.threw.length}`);
console.log(`  返回非布尔：${stats.badType.length}`);

let bad = 0;
if (stats.none.length) { bad++; console.log('\n✗ 有判题类型无人接管：'); stats.none.slice(0, 10).forEach(x => console.log('   - ' + x)); }
if (stats.threw.length) { bad++; console.log('\n✗ 有判题抛异常：'); stats.threw.slice(0, 10).forEach(x => console.log('   - ' + x)); }
if (stats.badType.length) { bad++; console.log('\n✗ 有判题返回非布尔值：'); stats.badType.slice(0, 10).forEach(x => console.log('   - ' + x)); }

if (bad) { console.log('\n失败 ✗'); process.exit(1); }
console.log('\n全部通过 ✓ 引擎可在无浏览器环境下加载并跑完全部任务');
