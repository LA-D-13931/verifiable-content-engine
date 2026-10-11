#!/usr/bin/env node
// 对比度探针（第六十三轮 P5 第一段）—— **真实计算样式取色** ✓（与 verify-themes.mjs 同一套做法 ✓）
// **环境自检（本文件的头等事 ✓）**：任何"跑不了"的原因都必须走 **退出码 2**（环境不足 ✓），
// 由 checks_contrast.py 转成 pass=None ✓ —— **不许变成"检查器故障"或红** ✗。
const [url, ...rest] = process.argv.slice(2);
const arg = (n, d) => { const i = rest.indexOf(n); return i >= 0 ? rest[i + 1] : d; };
const width = Number(arg('--width', '1440'));
const minRatio = Number(arg('--min-ratio', '4.5'));
const die = (msg) => { console.error('ENV: ' + msg); process.exit(2); };

let puppeteer, resolveBrowser;
try {
  puppeteer = (await import('puppeteer-core')).default;
  ({ resolveBrowser } = await import('./browser.mjs'));
} catch (e) { die('依赖不可用：' + e.message); }
let exec = null;
try { exec = resolveBrowser(); } catch (e) { die('浏览器解析失败：' + e.message); }
if (!exec) die('没有可用浏览器');
if (!url) die('缺 URL');

let browser;
try {
  browser = await puppeteer.launch({ executablePath: exec, args: ['--no-sandbox'] });
} catch (e) { die('浏览器起不来：' + e.message); }
const page = await browser.newPage();
await page.setViewport({ width, height: 900 });
try { await page.goto(url, { waitUntil: 'load' }); } catch (e) { await browser.close(); die('页面打不开：' + e.message); }
const items = await page.evaluate(() => {
  const out = [];
  for (const el of document.querySelectorAll('p, li, td, h1, h2, h3, h4, span, strong, em, a')) {
    const t = (el.textContent || '').trim(); if (!t) continue;
    const s = getComputedStyle(el);
    let bg = s.backgroundColor, node = el;
    while (node && (bg === 'rgba(0, 0, 0, 0)' || bg === 'transparent')) { node = node.parentElement; if (!node) break; bg = getComputedStyle(node).backgroundColor; }
    out.push({ text: t.slice(0, 40), fg: s.color, bg: bg || 'rgb(255,255,255)', size: parseFloat(s.fontSize), weight: s.fontWeight });
  }
  return out;
});
await browser.close();
console.log(JSON.stringify({ url, width, minRatio, items }));
