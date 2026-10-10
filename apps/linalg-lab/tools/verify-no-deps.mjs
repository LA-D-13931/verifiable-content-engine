/* 依赖边界守卫：**引擎本体零第三方依赖**——把用户的要求变成自动检查。
 *
 * 这条要求原先只是文字（AGENTS.md 写"零第三方依赖"），没有任何东西守着它。
 * 而它一旦被破坏，是**静默**的：某天有人 import 一个包，本地装了就跑得通，
 * 全新克隆/CI 上才炸——正好是最难查的那种。
 *
 * 判据（机械可判）：
 *   · 引擎本体（engine-core/，不含 fixtures/）的每一处导入，必须是
 *     ① Python 标准库、② Node 内置（node: 前缀或声明列表）、或 ③ 同仓库里的相对/同名本地模块；
 *   · 出现任何其它名字 → 判红，并指出**文件与行号**。
 *
 * 用法：
 *   node tools/verify-no-deps.mjs                 # 扫整个引擎本体
 *   node tools/verify-no-deps.mjs --file <路径>   # 只扫一个文件（反证用）
 * 退出码即结论：0 通过 / 1 失败。
 */
import { readFileSync, readdirSync, existsSync, statSync } from 'node:fs';
import { resolve, dirname, join, basename } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const REPO = resolve(HERE, '..', '..', '..');
const ENGINE = join(REPO, 'engine-core');

//: Python 标准库白名单（只列引擎本体实际可能用到的；新增要**显式加**，这就是护栏的意义）
const PY_STDLIB = new Set(['os', 're', 'sys', 'json', 'subprocess', 'collections', 'time', 'hashlib',
    'glob', 'inspect', 'shutil', 'math', 'itertools', 'functools', 'pathlib', 'argparse', 'ast',
    'tempfile', 'difflib', 'runpy', 'unicodedata', 'html', 'urllib', 'typing', 'io', 'string',
    '__future__', 'datetime', 'random', 'csv', 'xml']);
//: Node 内置
const JS_BUILTIN = new Set(['fs', 'path', 'url', 'util', 'crypto', 'events', 'stream', 'os', 'child_process']);

function walk(dir, out = []) {
    for (const name of readdirSync(dir)) {
        if (name === 'fixtures' || name === 'node_modules' || name === '__pycache__') continue;
        const p = join(dir, name);
        const st = statSync(p);
        if (st.isDirectory()) walk(p, out);
        else if (/\.(py|js|mjs)$/.test(name)) out.push(p);
    }
    return out;
}

/** 引擎本体里出现的所有"本地模块名"（同目录同名文件） */
function localNames(dir) {
    const s = new Set();
    for (const n of readdirSync(dir)) s.add(basename(n).replace(/\.(py|js|mjs)$/, ''));
    return s;
}

function checkFile(file) {
    const src = readFileSync(file, 'utf8');
    const dir = dirname(file);
    const local = localNames(dir);
    const problems = [];
    const lines = src.split('\n');
    const isPy = file.endsWith('.py');

    lines.forEach((line, i) => {
        let mods = [];
        if (isPy) {
            const m = line.match(/^\s*(?:import|from)\s+([A-Za-z_][\w.]*)/);
            if (m) mods = [m[1].split('.')[0]];
        } else {
            for (const m of line.matchAll(/(?:^|\s)(?:import|export)[^\n]*?from\s+['"]([^'"]+)['"]/g)) mods.push(m[1]);
            for (const m of line.matchAll(/require\(\s*['"]([^'"]+)['"]\s*\)/g)) mods.push(m[1]);
        }
        for (const mod of mods) {
            const relative = mod.startsWith('.') || mod.startsWith('/');
            const nodeBuiltin = mod.startsWith('node:');
            const allowed = isPy
                ? (PY_STDLIB.has(mod) || local.has(mod))
                : (relative || nodeBuiltin || JS_BUILTIN.has(mod.replace(/^node:/, '')) || local.has(mod));
            if (!allowed) problems.push(`${file.replace(REPO + '/', '')}:${i + 1} → ${mod}`);
        }
    });
    return problems;
}

const argv = process.argv.slice(2);
const fi = argv.indexOf('--file');
let cwd = process.cwd();
const files = fi >= 0 ? [resolve(argv[fi + 1])] : walk(ENGINE);

console.log('=== 依赖边界守卫（引擎本体零第三方依赖）===');
console.log('扫描：' + (fi >= 0 ? files[0] : ENGINE.replace(REPO + '/', '') + '/ （不含 fixtures/）'));
const all = [];
for (const f of files) all.push(...checkFile(f));
if (all.length === 0) {
    console.log(`  ✓ ${files.length} 个文件：导入全部是标准库 / 内置 / 本地模块`);
    console.log('\n零第三方依赖成立 ✓');
    process.exit(0);
}
for (const p of all.slice(0, 20)) console.log('  ✗ ' + p);
console.log(`\n发现 ${all.length} 处非标准库导入 ✗（引擎本体必须零第三方依赖）`);
process.exit(1);
