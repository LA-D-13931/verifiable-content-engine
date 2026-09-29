#!/usr/bin/env node
/* 从 assets/js/lab-data.js 提取出纯 JSON：assets/js/labs.json
   ============================================================
   为什么要提取
   ------------
   原先关卡内容硬编码在 lab-data.js 里（1926 行 JavaScript 字面量），带来两个问题：

     ① 语言模型无从产出一份「可被独立校验的输入」——它没法可靠地生成 JS 字面量，
        也就拍不出演示录像里「模型写关卡 → 引擎拦下」那一段。
     ② 校验工具只能**解析 JS 源码**（check-lab.py 里有个手写的逐字符扫描器），
        校验器因此依赖于内容的表示形式，而不是内容本身。

   提取成纯 JSON 后：
     · labs.json 是**唯一编辑面**（人与模型都只写它）
     · lab-data.js 改为由 tools/gen-labs-js.py 从 labs.json **生成**
     · 校验器可以直接 json.load，不再需要扫描器

   注意：提取必须用「求值后序列化」，不能靠正则改写源码——
   文件里有 `Mat.identity(2)` 这类需要展开的表达式，以及用 `+` 拼接的长字符串。

   用法：
     node tools/gen-labs-json.mjs            # 提取并写入 labs.json
     node tools/gen-labs-json.mjs --check    # 只比对，不写入（退出码 1 表示不一致）
   ============================================================ */
import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const SITE = dirname(HERE);
const OUT = join(SITE, 'assets', 'js', 'labs.json');
const SRC = join(SITE, 'assets', 'js', 'lab-data.js');
const checkOnly = process.argv.includes('--check');

/* 在一个受控的全局环境里求值 lab-data.js。
   lab-data.js 需要 Mat（展开 Mat.identity）与 COLORS，二者都给最小替身。 */
const require = createRequire(import.meta.url);
globalThis.window = globalThis;
globalThis.Mat = require(join(SITE, 'assets', 'js', 'mat.js'));
globalThis.COLORS = new Proxy({}, { get: () => '#000000' });
require(SRC);

/* ⚠️ 关键护栏：本脚本是**一次性迁移工具**。
   它从 lab-data.js 提取出 labs.json。但迁移完成后 lab-data.js 本身
   就是由 labs.json 生成的，此时再跑本脚本会「从生成物反推源头」——
   一旦提取有损，就会把源头改坏，而且产物看起来完全正常。
   （这个坑真实踩过：提取时丢掉字段，labs.json 被写坏。）

   所以：如果检测到 lab-data.js 已带生成物标记，就直接拒绝运行。 */
if (/本文件由 tools\/gen-labs-js\.py 从 assets\/js\/labs\.json 生成/.test(
        readFileSync(SRC, 'utf-8'))) {
    console.error('✗ 拒绝运行：assets/js/lab-data.js 已是生成物。');
    console.error('  本脚本只用于「把手写的 lab-data.js 迁移成 labs.json」这一次。');
    console.error('  迁移后，编辑面是 labs.json，反向生成请用：');
    console.error('      python3 tools/gen-labs-js.py');
    console.error('  想校验两者是否一致，用：');
    console.error('      node tools/verify-labs.mjs');
    process.exit(3);
}

const chapters = globalThis.CHAPTERS;
const labs = globalThis.LABS;

if (!Array.isArray(chapters) || !Array.isArray(labs)) {
    console.error('✗ 未能从 lab-data.js 取到 CHAPTERS / LABS');
    process.exit(2);
}

/* 序列化。
   ⚠️ 这里**原样复制所有键**，不用白名单。
   第一版用了 whitelist，结果漏掉 scene.comboPath 等字段——
   「提取时静默丢字段」比报错危险得多，因为产物看起来完全正常。
   键的顺序按实际观察到的顺序写死，保证生成的 JSON 逐字节稳定。 */
function pick(src, order) {
    const o = {};
    for (const k of order) if (src[k] !== undefined) o[k] = src[k];
    // 兜底：order 里没列出、但数据里实际存在的键也要带上
    for (const k of Object.keys(src)) if (!(k in o)) o[k] = src[k];
    return o;
}

function chapterOut(c) {
    return pick(c, ['id', 'title', 'desc']);
}

function sceneOut(s) {
    return pick(s, ['space', 'matrix', 'matrixSize', 'basis', 'basisCoords', 'tgrid',
                    'spanView', 'nullView', 'shape', 'metric', 'vectors', 'lines',
                    'oneDim', 'numLine', 'dotPair', 'cross', 'targetPoint',
                    'comboPath', 'interact', 'toolbar']);
}

function taskOut(t) {
    return pick(t, ['id', 'text', 'options', 'explains', 'check']);
}

function labOut(l) {
    return pick(l, ['id', 'chapter', 'title', 'brief', 'scene', 'tasks', 'hints']);
}

/* scene 与 tasks 需要递归套用上面的函数 */
function labDeep(l) {
    const o = labOut(l);
    o.scene = sceneOut(l.scene);
    o.tasks = l.tasks.map(taskOut);
    return o;
}

const payload = {
    $comment: '本文件是关卡内容的唯一编辑面。assets/js/lab-data.js 由 tools/gen-labs-js.py 从本文件生成，请勿手改。',
    version: 2,
    chapters: chapters.map(chapterOut),
    labs: labs.map(labDeep)
};

const text = JSON.stringify(payload, null, 2) + '\n';

/* 自检：解析回来必须与「按同样规则序列化源数据」的结果一致。
   这能挡住「pick 漏字段」这类静默丢数据的问题——产物看起来完全正常，
   但字段已经没了。 */
const expect = JSON.stringify({
    $comment: payload.$comment,
    version: payload.version,
    chapters: chapters.map(chapterOut),
    labs: labs.map(labDeep)
});
const got = JSON.stringify(JSON.parse(text));
if (expect !== got) {
    console.error('✗ 自检失败：序列化结果与源数据不一致（可能有字段没被带上）');
    let i = 0;
    while (i < expect.length && i < got.length && expect[i] === got[i]) i++;
    console.error('   首个差异位置 %d', i);
    console.error('   期望 …%s', expect.slice(Math.max(0, i - 60), i + 60));
    console.error('   实得 …%s', got.slice(Math.max(0, i - 60), i + 60));
    process.exit(2);
}

const nTasks = labs.reduce((s, l) => s + l.tasks.length, 0);
const kb = (text.length / 1024).toFixed(0);

if (checkOnly) {
    const old = existsSync(OUT) ? readFileSync(OUT, 'utf-8') : '';
    if (old !== text) {
        console.error('✗ labs.json 与 lab-data.js 不一致 —— 运行 node tools/gen-labs-json.mjs');
        process.exit(1);
    }
    console.log(`✓ labs.json 与 lab-data.js 一致（${labs.length} 实验 / ${nTasks} 任务 / ${kb} KB）`);
    process.exit(0);
}

writeFileSync(OUT, text, 'utf-8');
console.log(`✓ 已提取 ${labs.length} 个实验 / ${chapters.length} 个章节 / ${nTasks} 个任务`);
console.log(`  → assets/js/labs.json（${kb} KB，纯 JSON，无函数与 undefined）`);
console.log('  自检通过：序列化结果与源数据完全一致');
