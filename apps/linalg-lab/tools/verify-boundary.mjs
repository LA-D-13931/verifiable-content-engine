/* 引擎层边界守卫：守住「**新增科目不改引擎层**」这条核心主张。
 *
 * 这条主张是本项目对外的头号论证（线代 → 高数 → …都要靠它成立）。
 * 主张要能被证伪，就必须有一条检查盯着它——否则它只是宣言。
 *
 * 三件事：
 *   ① 引擎层代码里不得出现**学科概念词**（秩 / 行列式 / 特征值 / 列空间 …）。
 *      ⚠️ 判据必须**先剥注释再扫**：registry.js 的头注释里就有这些词，
 *      而那段注释正是**定义分界线**的地方——对着注释扫会稳定误报（假阳性）。
 *      同理，字符串里的类型名（'dot' 等）是引擎层的合法登记，不算违规。
 *   ② 引擎层不得引用具体科目插件（`domains/**`）。
 *   ③ 引擎层注册的类型集合必须**等于**这里声明的 7 类：
 *      多一个少一个都要显式改这份声明——让"往引擎层加学科判据"变成一个**要签字**的动作。
 *
 * 用法：node tools/verify-boundary.mjs [--file <路径>]     # 供反证时指向副本
 * 退出码即结论：0 通过 / 1 失败。
 */
import { readFileSync, existsSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const REPO = resolve(HERE, '..', '..', '..');            // apps/linalg-lab/tools → 仓库根

// 学科概念词：取自引擎层自己的分界线说明 + 两个插件真实注册的类型名。
// 判据是"引擎层不认识这些概念"——所以它们只能出现在**注释**或**插件**里。
const SUBJECT_TERMS = ['秩', '行列式', '特征值', '特征向量', '列空间', '零空间', '线性无关',
                       'det', 'rank', 'eigen', 'null-space', 'on-span', 'in-basis',
                       'cross-dir', 'gradient', 'loss'];

// 引擎层允许注册的类型（领域无关：数值命中 / 位置命中 / 序列匹配 / 选择题）。
const ENGINE_TYPES = ['vector-at', 'av-at', 'matrix-col-at', 'match-matrix', 'dot', 'choice', 'actions'];

const argv = process.argv.slice(2);
const fi = argv.indexOf('--file');
const file = fi >= 0 ? argv[fi + 1] : resolve(REPO, 'engine-core', 'registry.js');
if (!existsSync(file)) { console.log('✗ 找不到引擎层文件：' + file); process.exit(1); }

const raw = readFileSync(file, 'utf8');
// 剥注释（块注释 + 行注释）。注意**保留字符串**：类型名是字符串，属于合法登记。
const code = raw.replace(/\/\*[\s\S]*?\*\//g, ' ').replace(/(^|[^:])\/\/[^\n]*/g, '$1 ');

let bad = 0;
const ok = (name, cond, detail = '') => {
    console.log(`  ${cond ? '✓' : '✗'} ${name}${detail ? '  ' + detail : ''}`);
    if (!cond) bad++;
};

console.log('=== 引擎层边界守卫 ===');
console.log('文件：' + file);

// ① 代码里的学科概念词
const hits = SUBJECT_TERMS.filter((t) => code.includes(t));
ok('代码里没有学科概念词', hits.length === 0,
   hits.length ? '命中了 ' + hits.join('、') + '（若在注释里不算——本判据已剥注释）' : '');

// ② 不得引用具体科目插件
const refs = [...code.matchAll(/(require|import)[^\n]*domains\//g)].map((m) => m[0].slice(0, 60));
ok('不引用具体科目插件', refs.length === 0, refs.join(' ｜ '));

// ③ 注册类型集合必须等于声明的 7 类
const types = [...code.matchAll(/register\('([a-z-]+)'/g)].map((m) => m[1]).sort();
const want = [...ENGINE_TYPES].sort();
const same = types.length === want.length && types.every((t, i) => t === want[i]);
ok('注册类型等于声明的 ' + want.length + ' 类', same,
   same ? '' : `实际 [${types.join(', ')}] ⇄ 声明 [${want.join(', ')}]`
          + (types.length > want.length ? ' ← 引擎层多出了类型（学科判据应下沉到 domains/）' : ''));

console.log(bad === 0 ? '\n引擎层边界完好 ✓' : `\n边界被破坏 ${bad} 处 ✗`);
process.exit(bad === 0 ? 0 : 1);
