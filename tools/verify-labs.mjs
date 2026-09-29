#!/usr/bin/env node
/* 校验「labs.json → lab-data.js」这条生成链是否无损。
   ============================================================
   比对三次：
     ① labs.json 与 lab-data.js 的数据是否等价（逐字段，忽略键序）
     ② 生成链是否最新（gen-labs-json --check、gen-labs-js --check）
     ③ 统计口径（实验数 / 章节数 / 任务数）是否与预期一致

   ⚠️ 比较必须**忽略对象的键顺序**：JSON.stringify 对键序敏感，
   而 JS 对象的键序不影响任何行为。早先用 stringify 直接比对，
   因为「comboPath 的位置不同」报了一次假差异，白查了半天。

   用法：node tools/verify-labs.mjs [期望实验数] [期望任务数]
   ============================================================ */
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { execFileSync } from 'node:child_process';

const HERE = dirname(fileURLToPath(import.meta.url));
const SITE = dirname(HERE);
const require = createRequire(import.meta.url);

const EXP_LABS = Number(process.argv[2] || 58);
const EXP_TASKS = Number(process.argv[3] || 168);

const fail = [];
const ok = (c, m) => { console.log(`  ${c ? '✓' : '✗'} ${m}`); if (!c) fail.push(m); };

/* 递归规范化：对象按键名排序，数组保持顺序，数字保留原值 */
function canon(v) {
    if (Array.isArray(v)) return v.map(canon);
    if (v && typeof v === 'object') {
        const o = {};
        Object.keys(v).sort().forEach(k => { o[k] = canon(v[k]); });
        return o;
    }
    return v;
}

/* 在受控全局里求值 lab-data.js */
function loadLabDataJs(path) {
    const g = globalThis;
    g.window = g;
    g.Mat = require(join(SITE, 'assets', 'js', 'mat.js'));
    g.COLORS = new Proxy({}, { get: () => '#000000' });
    delete g.CHAPTERS; delete g.LABS;
    const code = readFileSync(path, 'utf-8');
    new Function('window', 'Mat', 'COLORS', code)(g, g.Mat, g.COLORS);
    return { chapters: JSON.parse(JSON.stringify(g.CHAPTERS)),
             labs: JSON.parse(JSON.stringify(g.LABS)) };
}

console.log('=== 关卡数据生成链校验 ===');

// ---- ① json 与 js 的数据是否等价 ----
const json = JSON.parse(readFileSync(join(SITE, 'assets', 'js', 'labs.json'), 'utf-8'));
const js = loadLabDataJs(join(SITE, 'assets', 'js', 'lab-data.js'));

const jsonPayload = { chapters: json.chapters, labs: json.labs };
const jsPayload = { chapters: js.chapters, labs: js.labs };
const same = JSON.stringify(canon(jsonPayload)) === JSON.stringify(canon(jsPayload));
ok(same, 'labs.json 与 lab-data.js 的数据完全等价（忽略键序）');
if (!same) {
    // 定位第一处差异
    const a = JSON.stringify(canon(jsonPayload)), b = JSON.stringify(canon(jsPayload));
    let i = 0;
    while (i < a.length && i < b.length && a[i] === b[i]) i++;
    console.log('     首个差异位置 %d', i);
    console.log('     labs.json    …%s', a.slice(Math.max(0, i - 70), i + 70));
    console.log('     lab-data.js  …%s', b.slice(Math.max(0, i - 70), i + 70));
}

// ---- ② 生成链是否最新 ----
// 只校验「labs.json → lab-data.js」这一个方向。
// 反方向（gen-labs-json.mjs）是一次性迁移工具，迁移完成后会主动拒绝运行，
// 不该出现在常规校验里——否则等于鼓励「从生成物反推源头」。
let pyOk = true;
try {
    execFileSync('python3', [join(HERE, 'gen-labs-js.py'), '--check'], { cwd: SITE, stdio: 'pipe' });
} catch (e) { pyOk = false; }
ok(pyOk, 'lab-data.js 与 labs.json 同步（生成物最新）');

// ---- ③ 统计口径 ----
const nLabs = js.labs.length, nCh = js.chapters.length;
const nTasks = js.labs.reduce((s, l) => s + l.tasks.length, 0);
ok(nLabs === EXP_LABS, `实验数 ${nLabs}（预期 ${EXP_LABS}）`);
ok(nTasks === EXP_TASKS, `任务数 ${nTasks}（预期 ${EXP_TASKS}）`);
console.log(`  · 章节数 ${nCh}，labs.json 体积 ${(readFileSync(join(SITE, 'assets', 'js', 'labs.json')).length / 1024).toFixed(0)} KB`);

// ---- ④ 纯 JSON 约束：不得含可执行痕迹 ----
const raw = readFileSync(join(SITE, 'assets', 'js', 'labs.json'), 'utf-8');
ok(!/Mat\.|COLORS\.|=>|\bfunction\b/.test(raw), 'labs.json 是纯数据（无 Mat./COLORS./函数）');

console.log('');
if (fail.length) {
    console.log(`失败 ${fail.length} 项 ✗`);
    process.exit(1);
}
console.log('全部通过 ✓ lab-data.js 可由 labs.json 无损重建');
