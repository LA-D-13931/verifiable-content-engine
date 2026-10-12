#!/usr/bin/env node
// P12 目录↔正文探针（第七十八轮）—— **真实 DOM** ✓（照 anchor-highlight-probe.mjs 的做法 ✓）
// 环境自检：任何"跑不了"的原因都走 exit 2（由 Python 侧转成 pass=None ✓），不许变成红 ✗。
const [url, ...rest] = process.argv.slice(2);
const arg = (n, d) => { const i = rest.indexOf(n); return i >= 0 ? rest[i + 1] : d; };
const tocSel = arg('--toc', 'nav.toc, aside.toc, .table-of-contents, [data-toc]');
const linkSel = arg('--link', 'a[href^="#"]');
const headSel = arg('--heading', 'h2, h3, h4');
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
const data = await page.evaluate((tocSel, linkSel, headSel) => {
  const tocs = [...document.querySelectorAll(tocSel)];
  const entries = [];
  for (const t of tocs) {
    for (const a of t.querySelectorAll(linkSel)) {
      const href = a.getAttribute('href') || '';
      const id = href.startsWith('#') ? href.slice(1) : '';
      const target = id ? document.getElementById(id) : null;
      const r = a.getBoundingClientRect();
      entries.push({ text: (a.textContent || '').trim().slice(0, 60), href, id,
                     exists: !!target, targetLevel: target ? Number(target.tagName.slice(1)) : null,
                     line: null, rect: { top: Math.round(r.top) } });
    }
  }
  const headings = [];
  for (const h of document.querySelectorAll(headSel)) {
    const r = h.getBoundingClientRect();
    headings.push({ id: h.id || '', level: Number(h.tagName.slice(1)),
                    text: (h.textContent || '').trim().slice(0, 60), top: Math.round(r.top) });
  }
  return { hasToc: tocs.length > 0, tocCount: tocs.length, entries, headings };
}, tocSel, linkSel, headSel);
await browser.close();
console.log(JSON.stringify({ url, ...data }));
