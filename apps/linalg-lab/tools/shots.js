/* 逐关截图：便于人工检查每个实验的画布与取景。
   用法：node tools/shots.js [baseUrl] */
const puppeteer = require('puppeteer-core');
const fs = require('fs');
const EDGE = '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge';
const BASE = process.argv[2] || 'http://127.0.0.1:8791/apps/linalg-lab';

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
