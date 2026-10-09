/* 全主题对比度校验
   ============================================================
   把 4 套主题 × 亮/暗 逐个套到真实页面上，用**真实像素**算出对比度。

   为什么不读 CSS 值：
     面板底色常写成 background-image 渐变，或 rgba(…,0.94) 半透明，
     逐层合成 CSS 值很容易算错——先前版本就因此产生了大量假警报。
     现在的做法是截图 → 用 canvas 读元素左下内角的实际像素，
     渐变、半透明、阴影、页面自己的 canvas 全部包含在内。

   用法：node tools/verify-themes.mjs [baseUrl]
   ============================================================ */
import puppeteer from 'puppeteer-core';

const EDGE = '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge';
const BASE_PATH = '/apps/linalg-lab';
const PROBE_PATH = '/apps/linalg-lab/index.html';
/* 本地服务由 serve.mjs 保证：它探活、必要时自己从仓库根起一个。
   为什么不再假设「8791 上有个对的服务器」—— 那个假设错过两次，
   失败现象（404）看着像内容坏了，实际跟内容无关。

   本文件是 ESM（.mjs），所以可以顶层 await 与顶层 import。 */
import { ensureServer } from './serve.mjs';
let _srv;
try {
    _srv = await ensureServer({ basePath: BASE_PATH });
} catch (e) {
    console.log('无法准备本地服务：' + e.message);
    process.exit(2);
}
/* BASE 必须是**带路径的完整地址**：
   原来这里是 http://127.0.0.1:8791/apps/linalg-lab/index.html，
   我第一版只取了服务主机（http://127.0.0.1:8791），路径丢了 ——
   于是浏览器去连「根路径」，报 ERR_CONNECTION_REFUSED。
   探针用 PROBE_PATH 是相对仓库根的路径，而浏览器要访问的是带
   apps/linalg-lab 前缀的完整地址。 */
const BASE = process.argv[2] ? _srv.base + (process.argv[2].startsWith('http') ? '' : BASE_PATH)
                             : _srv.base;
const THEMES = ['default', 'eyecare-warm', 'eyecare-cool', 'ink'];
const MODES = ['light', 'dark'];

/* [显示名, 选择器, 最低对比度] —— 正文 4.5（WCAG AA），次要/大字 3.0 */
const CHECKS = [
    ['顶栏品牌标题', '.brand-text h1', 4.5],
    ['顶栏副标题', '.brand-text p', 3.0],
    ['进度文字', '#progress-text', 4.5],
    ['侧栏标题', '.course-nav h2', 3.0],
    ['章节标题', '.chapter-title', 4.5],
    ['章节说明', '.chapter-desc', 3.0],
    ['实验按钮', '#chapter-list .lab-btn', 4.5],
    ['当前实验按钮', '.lab-item.current .lab-btn', 4.5],
    ['任务卡标题', '#level-title', 4.5],
    ['任务说明', '#level-brief', 4.5],
    ['任务文字', '.task-text', 4.5],
    ['选项文字', '.choice-opt', 4.5],
    ['矩阵格数字', '.matrix-cell', 4.5],
    ['诊断数值', '.diag-v', 4.5],
    ['诊断说明', '.diag-h', 3.0],
    ['配套讲义标题', '.crosslink-sec', 4.5],
    ['配套讲义说明', '.crosslink-note', 3.0],
    ['面板提示', '.panel-note', 3.0],
    ['页脚', '.site-footer', 3.0],
    ['画布提示', '.canvas-hint', 3.0],
];

const fail = [];
function ok(cond, msg) {
    console.log(`  ${cond ? '✓' : '✗'} ${msg}`);
    if (!cond) fail.push(msg);
}

(async () => {
    const browser = await puppeteer.launch({
        executablePath: EDGE, headless: 'new',
        args: ['--no-sandbox', '--disable-gpu'],
        defaultViewport: { width: 1440, height: 900 }
    });
    const page = await browser.newPage();
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    await page.goto(BASE + '/index.html#5-1', { waitUntil: 'domcontentloaded' });
    await new Promise(r => setTimeout(r, 600));
    await page.evaluate(() => { const h = document.getElementById('hint-box'); if (h) h.open = true; });

    for (const theme of THEMES) {
        for (const mode of MODES) {
            await page.evaluate((t, m) => Theme.apply(t, m), theme, mode);
            await new Promise(r => setTimeout(r, 280));

            // 1) 量出每个检查点的取样坐标与文字色
            const spots = await page.evaluate((checks) => checks.map(([name, sel, need]) => {
                const el = document.querySelector(sel);
                if (!el) return { name, sel, need, missing: true };
                const r = el.getBoundingClientRect();
                if (r.width < 2 || r.height < 2) return { name, sel, need, missing: true };
                return {
                    name, sel, need,
                    x: Math.round(r.left + 4),
                    y: Math.round(r.bottom - 3)      // 左下内角：避开文字与装饰
                };
            }), CHECKS);

            // 2) 截图，用 canvas 取真实像素
            const shot = await page.screenshot({ encoding: 'base64' });
            const rows = await page.evaluate(async (spots, shot, checks) => {
                function parseColor(c) {
                    let m = c && c.match(/color\(srgb\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)/);
                    if (m) return [+m[1] * 255, +m[2] * 255, +m[3] * 255];
                    m = c && c.match(/rgba?\(([^)]+)\)/);
                    if (!m) return null;
                    const p = m[1].split(/[,\s/]+/).filter(Boolean).map(Number);
                    return p.length >= 3 ? p.slice(0, 3) : null;
                }
                function lum(rgb) {
                    const [r, g, b] = rgb.map(v => {
                        v /= 255;
                        return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
                    });
                    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
                }
                function ratio(a, b) {
                    const la = lum(a), lb = lum(b);
                    return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05);
                }

                const img = new Image();
                await new Promise((res, rej) => {
                    img.onload = res; img.onerror = rej;
                    img.src = 'data:image/png;base64,' + shot;
                });
                const cv = document.createElement('canvas');
                cv.width = img.width; cv.height = img.height;
                const cx = cv.getContext('2d');
                cx.drawImage(img, 0, 0);
                const dpr = img.width / window.innerWidth;

                return spots.map((s, i) => {
                    if (s.missing) return s;
                    // 文字色要从（重新取的）元素上读，保证与当前主题一致
                    const el = document.querySelector(checks[i][1]);
                    const fg = el ? parseColor(getComputedStyle(el).color) : null;
                    if (!fg) return { name: s.name, missing: true };
                    let bg = [255, 255, 255];
                    try {
                        const x = Math.min(img.width - 1, Math.max(0, Math.round(s.x * dpr)));
                        const y = Math.min(img.height - 1, Math.max(0, Math.round(s.y * dpr)));
                        const d = cx.getImageData(x, y, 1, 1).data;
                        bg = [d[0], d[1], d[2]];
                    } catch (e) { /* 取不到就按白底算 */ }
                    return { name: s.name, need: s.need, fg, bg,
                             ratio: Math.round(ratio(fg, bg) * 100) / 100 };
                });
            }, spots, shot, CHECKS);

            console.log(`\n【${theme} / ${mode}】`);
            rows.forEach(r => {
                if (r.missing) { console.log(`  · ${r.name}（元素不存在，跳过）`); return; }
                ok(r.ratio >= r.need,
                   `${r.name} ${r.ratio}:1（要求 ≥ ${r.need}）  rgb(${r.fg.map(Math.round)}) 对 rgb(${r.bg})`);
            });
        }
    }

    ok(errors.length === 0, `无页面异常${errors.length ? '：' + errors.join(' | ') : ''}`);
    await browser.close();
    console.log(fail.length === 0 ? '\n全部通过 ✓' : `\n失败 ${fail.length} 项 ✗`);
    fail.slice(0, 24).forEach(f => console.log('   - ' + f));
    process.exit(fail.length === 0 ? 0 : 1);
})().catch(e => { console.error('崩溃：', e); process.exit(2); });

/* 收尾：只停自己起的那个服务（复用别人的不动） */
if (_srv) _srv.stop();
