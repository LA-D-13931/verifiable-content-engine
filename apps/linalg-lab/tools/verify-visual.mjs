#!/usr/bin/env node
/* 可视化页自检：样例必须各自触发预期缺陷，真实内容必须全绿。
   ============================================================
   为什么需要它：本页的样例是「故意做坏的」，做坏得不彻底就会**显示通过**，
   演示时反而砸招牌。这个坑真实踩过两次：
     · 第一版用 actions 类型演示「恒假任务」→ 动作日志被填满，显示通过
     · 第二版忘了写 faithful 标记 → 三个样例跑在了错误的模式上

   做法：用真实浏览器加载页面，逐个跑样例并核对「该报问题的必须报、
   对照组必须全绿」；再跑一遍真实 58 关内容，必须 0 问题。

   用法：node tools/verify-visual.mjs
   ============================================================ */
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const APP = dirname(HERE);
const REPO = dirname(dirname(APP));
const PAGE = join(APP, '引擎可视化.html');
//: 单文件版（引擎已内联）—— 也要检查，否则它会悄悄坏掉。
//: 它存在的理由：源页面用相对路径引用 engine-core，**单独拷出来就打不开**
//: （实测：拷到桌面后四个引擎文件全加载失败、格子数 0）。比赛演示要发给评委，
//: 所以必须有能单独发送的版本。
const STANDALONE = join(APP, '引擎可视化_单文件版.html');

const require = createRequire(import.meta.url);
let puppeteer;
try { puppeteer = require('puppeteer-core'); }
catch (e) {
    console.log('跳过：未安装 puppeteer-core（浏览器类工具需要它）');
    process.exit(0);
}
const EDGE = '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge';
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';

let pass = 0, fail = 0;
const failures = [];
function ok(cond, name, extra) {
    if (cond) { pass++; console.log('  ✓ ' + name); }
    else { fail++; failures.push(name); console.log('  ✗ ' + name + (extra ? '  —— ' + extra : '')); }
}

const exe = (() => { for (const p of [EDGE, CHROME]) { try { readFileSync(p); return p; } catch {} } return null; })();
if (!exe) { console.log('跳过：找不到 Edge 或 Chrome'); process.exit(0); }

const br = await puppeteer.launch({ executablePath: exe, headless: 'new',
    args: ['--no-sandbox', '--disable-gpu'] });
const p = await br.newPage();
const errs = [];
p.on('pageerror', e => errs.push(e.message));
await p.goto(pathToFileURL(PAGE).href, { waitUntil: 'load' });
await new Promise(r => setTimeout(r, 300));

console.log('=== 可视化页自检 ===');
ok(errs.length === 0, '页面无脚本异常', errs.slice(0, 2).join(' | '));
ok(await p.evaluate(() => typeof window.EngineVisual === 'object'), '对外接口 EngineVisual 可用');

const n = await p.evaluate(() => window.EngineVisual.samples.length);
ok(n >= 4, `内置样例 ${n} 个（含对照组）`);

// 逐个样例：前 n-1 个必须报问题，最后一个必须全绿
for (let i = 0; i < n; i++) {
    const r = await p.evaluate(k => {
        const s = window.EngineVisual.samples[k];
        const res = window.EngineVisual.analyze(s[2], s[2].faithful ? { useScene: true } : {});
        const bad = res.rows.filter(x => !x.pass);
        return { name: s[0], total: res.total, bad: bad.length,
                 reasons: bad.map(x => x.kind) };
    }, i);
    const isControl = (i === n - 1);
    if (isControl) {
        ok(r.bad === 0, `对照组全绿（${r.total} 个任务）`, `有问题 ${r.bad}`);
    } else {
        ok(r.bad > 0, `样例「${r.name}」触发缺陷`,
           `任务 ${r.total} 个但 0 问题 —— 样例做得不够“坏”`);
    }
}

// 真实内容必须全绿（打开即正印象）
try {
    const labs = readFileSync(join(APP, 'assets/js/labs.json'), 'utf-8');
    const real = await p.evaluate(t => {
        const r = window.EngineVisual.analyze(JSON.parse(t));
        return { total: r.total, bad: r.rows.filter(x => !x.pass).length };
    }, labs);
    ok(real.bad === 0, `真实内容全绿（${real.total} 个任务）`, `有问题 ${real.bad}`);
} catch (e) {
    ok(false, '真实内容可加载', e.message);
}

/* ---- 单文件版：必须在**没有任何外部文件**的情况下可用 ---- */
console.log('');
console.log('单文件版（引擎内联，应零外部依赖）');
{
    const html = readFileSync(STANDALONE, 'utf-8');
    const left = html.match(/<script src="[^"]*"><\/script>/g) || [];
    ok(left.length === 0, '页面里没有残留的外部脚本引用', left.join(' '));
    for (const f of ['mat.js', 'registry.js', 'judge.js']) {
        ok(html.includes(f), `已内联 ${f} 的内容`);
    }
    const p2 = await br.newPage();
    const e2 = [];
    const failed = [];
    p2.on('pageerror', e => e2.push(e.message));
    p2.on('requestfailed', r => failed.push(r.url()));
    await p2.goto(pathToFileURL(STANDALONE).href, { waitUntil: 'load' });
    await new Promise(r => setTimeout(r, 400));
    const st = await p2.evaluate(() => ({
        mat: typeof window.Mat, ev: typeof window.EngineVisual,
        n: window.EngineVisual ? window.EngineVisual.samples.length : 0
    }));
    ok(st.mat === 'object' && st.ev === 'object', '隔离打开后引擎与接口都可用',
       `Mat=${st.mat} EngineVisual=${st.ev}`);
    ok(st.n >= 4, `单文件版内置样例 ${st.n} 个`);
    ok(failed.length === 0, '没有任何外部请求（零依赖）', failed.slice(0, 2).join(' '));
    ok(e2.length === 0, '单文件版无脚本异常', e2.slice(0, 2).join(' | '));
    await p2.close();
}

await br.close();
console.log('');
console.log(`通过 ${pass} / ${pass + fail}`);
if (fail) { console.log(`失败 ${fail} 项 ✗`); failures.forEach(f => console.log('   - ' + f)); process.exit(1); }
console.log('全部通过 ✓ 可视化页的样例与真实内容都符合预期');
