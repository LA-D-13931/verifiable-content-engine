/* 逐关截图：便于人工检查每个实验的画布与取景。
   用法：node tools/shots.mjs [baseUrl] */
import puppeteer from 'puppeteer-core';
import fs from 'fs';
const EDGE = '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge';
const BASE_PATH = '/apps/linalg-lab';
const PROBE_PATH = '/apps/linalg-lab';
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

(async () => {
    fs.mkdirSync('shots', { recursive: true });
    const browser = await puppeteer.launch({
        executablePath: EDGE, headless: 'new',
        args: ['--no-sandbox', '--disable-gpu'],
        defaultViewport: { width: 1440, height: 900 }
    });
    const page = await browser.newPage();
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
    await page.goto(BASE + '/index.html', { waitUntil: 'domcontentloaded' });
    await page.evaluate(() => localStorage.clear());
    await page.reload({ waitUntil: 'networkidle0' });

    const withThemes = process.argv.includes('--themes');
    const THEMES = [['default', 'light'], ['default', 'dark'],
                    ['eyecare-warm', 'light'], ['eyecare-warm', 'dark'],
                    ['eyecare-cool', 'light'], ['eyecare-cool', 'dark'],
                    ['ink', 'light'], ['ink', 'dark']];
    if (!withThemes) await page.evaluate(() => Theme.apply('default', 'dark'));

    const ids = await page.evaluate(() => LABS.map(l => l.id));
    for (const id of ids) {
        await page.evaluate((labId) => Engine.loadLab(labId), id);
        await new Promise(r => setTimeout(r, 450));
        await page.screenshot({ path: `shots/lab-${id}.png` });
        if (withThemes) {
            for (const [t, m] of THEMES) {
                await page.evaluate((t, m) => Theme.apply(t, m), t, m);
                await new Promise(r => setTimeout(r, 220));
                await page.screenshot({ path: `shots/theme-${t}-${m}--${id}.png` });
            }
        }
        const info = await page.evaluate(() => ({
            title: document.getElementById('level-title').textContent,
            handles: Interact.handles().length,
            scale: Math.round(App.cam2d.scale),
            space: App.space,
            cells: document.querySelectorAll('.matrix-cell').length
        }));
        console.log(`${id.padEnd(5)} ${info.space}  手柄 ${info.handles}  缩放 ${info.scale}  矩阵格 ${info.cells}  ${info.title}`);
    }
    console.log(errors.length ? `\n控制台错误 ${errors.length}：${errors.join(' | ')}` : '\n无控制台错误 ✓');
    await browser.close();
    process.exit(errors.length ? 1 : 0);
})();

/* 收尾：只停自己起的那个服务（复用别人的不动） */
if (_srv) _srv.stop();
