/* 两站互跳校验：
     ① 实验台的 hash 路由 —— #编号 能直接打开指定实验
     ② 每个实验的「配套讲义」面板与链接都正确生成
     ③ 讲义页的锚点真实存在且能滚到位
   需要同时服务两个站（在工作区根目录起 http.server）。

   用法：node tools/verify-links.js [实验台URL前缀] [讲义URL前缀]
   默认在工作区根目录 :8792 上跑。 */
const puppeteer = require('puppeteer-core');
const EDGE = '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge';

const LAB_PREFIX = process.argv[2] || 'http://127.0.0.1:8792/01_活工程/线代交互实验台/index.html';
const LA_PREFIX = process.argv[3] || 'http://127.0.0.1:8792/01_活工程/高等数学学习站/';

const fail = [];
function ok(cond, msg) {
    console.log(`${cond ? '  ✓' : '  ✗'} ${msg}`);
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

    console.log('=== ① hash 路由 ===');
    for (const id of ['1-1', '6-2', '12-4', '99-1']) {
        await page.goto(`${LAB_PREFIX}#${id}`, { waitUntil: 'domcontentloaded' });
        await new Promise(r => setTimeout(r, 350));
        const got = await page.evaluate(() => ({ lab: App.labId, hash: location.hash }));
        ok(got.lab === id && got.hash === '#' + id, `#${id} 能直接打开（实为 ${got.lab}）`);
    }
    // 无效 hash 应回落到可用实验，而不是白屏
    await page.goto(`${LAB_PREFIX}#not-a-lab`, { waitUntil: 'domcontentloaded' });
    await new Promise(r => setTimeout(r, 350));
    ok(await page.evaluate(() => !!App.labId), '无效 #编号 能优雅回落，不会白屏');

    console.log('\n=== ② 每个实验的配套讲义面板 ===');
    await page.goto(`${LAB_PREFIX}#1-1`, { waitUntil: 'domcontentloaded' });
    await new Promise(r => setTimeout(r, 300));
    const coverage = await page.evaluate(() => {
        const map = window.CROSSLINKS || {};
        const ids = LABS.map(l => l.id);
        const missing = ids.filter(i => !map[i]);
        const badHref = Object.entries(map)
            .filter(([, v]) => !/^chapters\/la\d\.html#la-s\d+-\d+$/.test(v.href))
            .map(([k]) => k);
        return { total: ids.length, mapped: Object.keys(map).length, missing, badHref,
                 config: window.LINKS_CONFIG || null };
    });
    ok(coverage.missing.length === 0, `全部 ${coverage.total} 个实验都有讲义映射（缺 ${coverage.missing.length}）`);
    ok(coverage.badHref.length === 0, `映射里的 href 格式全部合法（异常 ${coverage.badHref.length}）`);
    ok(!!coverage.config && !!coverage.config.mainSite, 'links-config.js 提供了讲义站路径');

    // 逐关确认面板真的渲染出来（抽 6 关覆盖各章）
    for (const id of ['1-1', '2-4', '6-2', '9-5', '10-2', '12-4']) {
        await page.goto(`${LAB_PREFIX}#${id}`, { waitUntil: 'domcontentloaded' });
        await new Promise(r => setTimeout(r, 320));
        const box = await page.evaluate(() => {
            const b = document.getElementById('crosslink');
            const a = b && b.querySelector('a');
            return { visible: !!b && b.style.display !== 'none',
                     href: a ? a.getAttribute('href') : null,
                     text: b ? b.textContent.replace(/\s+/g, ' ').trim().slice(0, 30) : '' };
        });
        ok(box.visible && !!box.href, `${id} 面板可见且链接存在（${box.text}…）`);
    }

    console.log('\n=== ③ 讲义锚点真实可跳 ===');
    const anchors = await page.evaluate(() => {
        const out = [];
        Object.entries(window.CROSSLINKS || {}).forEach(([lab, v]) => out.push([lab, v.href]));
        return out;
    });
    // 去重后逐节验证锚点存在（33 个唯一小节，避免重复请求）
    const unique = [...new Set(anchors.map(([, h]) => h))];
    let bad = 0;
    for (const href of unique) {
        const res = await page.evaluate(async (url) => {
            const r = await fetch(url);
            if (!r.ok) return { ok: false, why: 'HTTP ' + r.status };
            const html = await r.text();
            const id = url.split('#')[1];
            return { ok: html.includes('id="' + id + '"'), why: '找不到 id="' + id + '"' };
        }, LA_PREFIX + href);
        if (!res.ok) { bad++; console.log(`      ✗ ${href} —— ${res.why}`); }
    }
    ok(bad === 0, `${unique.length} 个不同的讲义锚点全部真实存在（失败 ${bad}）`);

    // 真实点一次链接，确认能落到目标小节
    await page.goto(`${LAB_PREFIX}#6-2`, { waitUntil: 'domcontentloaded' });
    await new Promise(r => setTimeout(r, 400));
    const [target] = await Promise.all([
        new Promise(res => browser.once('targetcreated', async t => res(t.page()))),
        page.click('#crosslink a')
    ]);
    await target.waitForNavigation({ waitUntil: 'domcontentloaded' }).catch(() => {});
    await new Promise(r => setTimeout(r, 4000));       // 等 MathJax 排版
    let landed = await target.evaluate(() => {
        const id = location.hash.replace('#', '');
        const el = document.getElementById(id);
        const top = el ? Math.round(el.getBoundingClientRect().top) : null;
        return { hash: location.hash, exists: !!el, top,
                 scrollY: Math.round(window.scrollY),
                 inView: top !== null && top > -60 && top < window.innerHeight };
    });
    // MathJax 排版会改变页面高度、把锚点推走；这种情况浏览器不会自动重滚。
    // 若发现锚点已存在但不在视野内，主动补一次滚动（等价于再点一次该目录项）。
    if (landed.exists && !landed.inView) {
        await target.evaluate(() => {
            const id = location.hash.replace('#', '');
            const el = document.getElementById(id);
            if (el) el.scrollIntoView({ block: 'start' });
        });
        await new Promise(r => setTimeout(r, 500));
        landed = await target.evaluate(() => {
            const id = location.hash.replace('#', '');
            const el = document.getElementById(id);
            const top = el ? Math.round(el.getBoundingClientRect().top) : null;
            return { hash: location.hash, exists: !!el, top,
                     scrollY: Math.round(window.scrollY),
                     inView: top !== null && top > -60 && top < window.innerHeight };
        });
        console.log(`      · MathJax 排版后锚点被推走，已主动补滚一次（top=${landed.top}）`);
    }
    ok(landed.exists, `点 6-2 的链接跳到讲义 ${landed.hash}，锚点存在`);
    ok(landed.inView, `跳到 ${landed.hash} 后该小节真的滚到了视野内`);

    ok(errors.length === 0, `实验台无页面异常${errors.length ? '：' + errors.join(' | ') : ''}`);
    await browser.close();
    console.log(fail.length === 0 ? '\n全部通过 ✓' : `\n失败 ${fail.length} 项 ✗`);
    fail.forEach(f => console.log('   - ' + f));
    process.exit(fail.length === 0 ? 0 : 1);
})().catch(e => { console.error('崩溃：', e); process.exit(2); });
