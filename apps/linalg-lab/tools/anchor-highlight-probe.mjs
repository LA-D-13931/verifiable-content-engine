#!/usr/bin/env node
// 锚点 + 高亮探针（第六十七轮 P5 第五、六维）—— **真实布局与真实计算样式** ✓
// 环境自检：任何"跑不了"的原因都走 exit 2（由 Python 侧转成 pass=None ✓），不许变成红 ✗。
const [url, ...rest] = process.argv.slice(2);
const die = (m) => { console.error('ENV: ' + m); process.exit(2); };
let puppeteer, resolveBrowser, exec;
try { puppeteer = (await import('puppeteer-core')).default; ({ resolveBrowser } = await import('./browser.mjs')); }
catch (e) { die('依赖不可用：' + e.message); }
try { exec = resolveBrowser(); } catch (e) { die('浏览器解析失败：' + e.message); }
if (!exec) die('没有可用浏览器');
let browser;
try { browser = await puppeteer.launch({ executablePath: exec, args: ['--no-sandbox'] }); }
catch (e) { die('浏览器起不来：' + e.message); }
const page = await browser.newPage();
await page.setViewport({ width: 1440, height: 900 });
try { await page.goto(url, { waitUntil: 'load' }); } catch (e) { await browser.close(); die('页面打不开：' + e.message); }

const data = await page.evaluate(() => {
  const parse = (c) => { const m = String(c).match(/rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?\)/);
    return m ? [+m[1], +m[2], +m[3], m[4] === undefined ? 1 : +m[4]] : null; };
  const over = (f, b) => { const a = f[3] + b[3] * (1 - f[3]); return a === 0 ? [255,255,255,1]
    : [(f[0]*f[3]+b[0]*b[3]*(1-f[3]))/a, (f[1]*f[3]+b[1]*b[3]*(1-f[3]))/a, (f[2]*f[3]+b[2]*b[3]*(1-f[3]))/a, a]; };
  const effBG = (el) => { const ch = []; let n = el;
    while (n) { const c = parse(getComputedStyle(n).backgroundColor); if (c) ch.push(c); n = n.parentElement; }
    let acc = [255,255,255,1]; for (let i = ch.length-1; i >= 0; i--) acc = over(ch[i], acc);
    return 'rgb(' + acc.slice(0,3).map(Math.round).join(', ') + ')'; };
  // ① 页内锚点
  const anchors = [];
  for (const a of document.querySelectorAll('a[href^="#"]')) {
    const href = a.getAttribute('href') || '';
    const id = href.slice(1);
    const t = id ? document.getElementById(id) : null;
    let obscuredBy = null;
    if (t) {
      const r = t.getBoundingClientRect();
      for (const n of document.querySelectorAll('header, nav, .sticky, [style*="position: fixed"], [style*="position:fixed"]')) {
        const cs = getComputedStyle(n);
        if (cs.position !== 'fixed' && cs.position !== 'sticky') continue;
        const nr = n.getBoundingClientRect();
        if (nr.height > 0 && r.top < nr.bottom && r.bottom > nr.top && nr.top < 120) { obscuredBy = (n.tagName + '.' + (n.className || '')).slice(0, 40); break; }
      }
    }
    anchors.push({ href, id, exists: !!t, obscuredBy, text: (a.textContent || '').trim().slice(0, 30) });
  }
  // ② 高亮：被显式标记的高亮元素，其背景必须与其"有效父背景"区别得开
  const marks = [];
  const sel = 'mark, .highlight, [data-highlight], [class*="highlight" i], [class*="hl-"]';
  for (const el of document.querySelectorAll(sel)) {
    const cs = getComputedStyle(el);
    const own = parse(cs.backgroundColor);
    if (!own || own[3] === 0) { marks.push({ tag: el.tagName, cls: (el.className||'').slice(0,30), bg: null, parentBG: effBG(el.parentElement || el), note: '自身背景透明' }); continue; }
    const composed = (() => { let ch = [], n = el; while (n) { const c = parse(getComputedStyle(n).backgroundColor); if (c) ch.push(c); n = n.parentElement; }
      let acc = [255,255,255,1]; for (let i = ch.length-1; i >= 0; i--) acc = over(ch[i], acc); return 'rgb(' + acc.slice(0,3).map(Math.round).join(', ') + ')'; })();
    marks.push({ tag: el.tagName, cls: (el.className||'').slice(0,30), bg: composed,
                 parentBG: effBG(el.parentElement || el), text: (el.textContent||'').trim().slice(0,30) });
  }
  return { anchors, marks };
});
await browser.close();
console.log(JSON.stringify({ url, ...data }));
