/* 渲染量测：把页面放进真实浏览器，量三个"静态看不出来"的东西。
 *
 * 为什么在消费者侧（apps/linalg-lab/tools/）：本项目早先定的分工——
 * **规则层放 content-spec，量测层放消费者侧**（那边装着 puppeteer-core 与浏览器自检）。
 * content-spec 的检查通过声明的路径调用本脚本，解析它的 JSON 结论。
 *
 * 量什么（都来自用户 UI 规范「改完必做的自检」）：
 *   ① 横向溢出 px —— 规范第 1 条"无异常横向滚动条"；
 *   ② 过小的点击目标 —— 可达性/触屏可用性（<24px 见方）；
 *   ③ 页面脚本报错 —— 交互组件坏了往往先在这里露头。
 *
 * 用法：node render-measure.mjs <file|url> [--width 1440]
 * 输出：一行 JSON（stdout）。找不到浏览器时输出 {"skipped": "..."} 并以 0 退出——
 *       「环境不足」是独立状态，由调用方决定怎么记，脚本本身不假装成功。
 */
import { readFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';
import { resolveBrowser } from './browser.mjs';   // D-4a：四级回退，共用一份

const EDGE = resolveBrowser();   // D-4a：显式 → 环境变量 → 探测 → exit 2

const argv = process.argv.slice(2);
const target = argv[0];
const wi = argv.indexOf('--width');
const WIDTH = wi >= 0 ? parseInt(argv[wi + 1], 10) || 1440 : 1440;
// 20px 是「明显过小」的保守下限：约 24px 的设计取舍不该被这条判红——
// 那是站主的标准，不是我们的判据（阈值必须能被声明和复核）。
const ti = argv.indexOf('--min-tap');
const MIN_TAP = ti >= 0 ? (parseFloat(argv[ti + 1]) || 20) : 20;
if (!target) { console.log(JSON.stringify({ error: '用法：node render-measure.mjs <file|url>' })); process.exit(2); }

const exe = resolveBrowser();   // D-4a
if (!exe) { console.log(JSON.stringify({ skipped: '找不到 Edge 或 Chrome（环境不足，不是通过）' })); process.exit(0); }

let puppeteer;
try { puppeteer = (await import('puppeteer-core')).default; }
catch (e) { console.log(JSON.stringify({ skipped: 'puppeteer-core 不可用：' + e.message })); process.exit(0); }

const url = /^https?:/.test(target) ? target : pathToFileURL(target).href;
const br = await puppeteer.launch({ executablePath: exe, headless: 'new',
  args: ['--no-sandbox', '--disable-gpu', `--window-size=${WIDTH},900`] });
let browserTag = 'unknown';
try { const v = await br.version(); browserTag = v; } catch (e) { /* 量不到就写 unknown，不写死 */ }
const out = { browser: browserTag, url, width: WIDTH, pageErrors: [], consoleErrors: [] };
try {
  const page = await br.newPage();
  await page.setViewport({ width: WIDTH, height: 900 });
  page.on('pageerror', (e) => out.pageErrors.push(String(e).slice(0, 200)));
  page.on('console', (m) => { if (m.type() === 'error') out.consoleErrors.push(m.text().slice(0, 200)); });
  await page.goto(url, { waitUntil: 'load', timeout: 40000 });
  await new Promise((r) => setTimeout(r, 600));      // 让运行时渲染（内联脚本）落定
  const m = await page.evaluate((MIN_TAP) => {
    const de = document.documentElement;
    const sel = 'button, a, input, select, summary, [role="button"], [onclick]';
    const small = [];
    for (const el of document.querySelectorAll(sel)) {
      // 有效点击区域 = 元素与它最近的 <label>（radio/checkbox 本体默认很小，
      // 但真实可点区域是包裹它的 label）。不做这一步会稳定误报一整类假阳性。
      // 有效点击区域 = 元素与它的 label：
      //   ① 包裹式 <label><input></label> → closest('label')
      //   ② **label[for=id] 式**（第二十三轮补上：此前只覆盖 ①，导致一整类假阳性）
      //      —— 真实可点区域是那个 label，而不是 input 本体（浏览器默认 28.2×19.8）
      const _lab = el.closest('label')
        || (el.id ? document.querySelector('label[for="' + CSS.escape(el.id) + '"]') : null);
      const box = (_lab || el);
      // 排除**正文内联链接**：段落里的 <a> 高度就是行高（约 19px），把它算成
      // "点击目标过小"是经典假阳性——导航/页脚/按钮里的链接仍然照测。
      if (el.tagName === 'A' && el.closest('p')) continue;
      const r = box.getBoundingClientRect();
      if (r.width === 0 && r.height === 0) continue;   // 隐藏元素不算
      if (r.width < MIN_TAP || r.height < MIN_TAP) {
        // 报**精确值**：判定用的是未取整的数，报告若四舍五入会出现"报 24 却被判小"的对不上。
        small.push({ tag: el.tagName.toLowerCase(),
                     w: Math.round(r.width * 10) / 10, h: Math.round(r.height * 10) / 10,
                     text: (el.textContent || '').trim().slice(0, 24) });
      }
    }
    return { scrollWidth: de.scrollWidth, clientWidth: de.clientWidth, scrollHeight: de.scrollHeight,
             smallTaps: small.slice(0, 20), smallTapCount: small.length, nodes: document.querySelectorAll('*').length };
  }, MIN_TAP);   // ← 必须传参：page.evaluate 的函数跑在浏览器里，看不到 Node 侧常量
  out.overflowX = Math.max(0, m.scrollWidth - m.clientWidth);
  out.scrollHeight = m.scrollHeight; out.nodes = m.nodes;
  out.smallTapCount = m.smallTapCount; out.smallTaps = m.smallTaps;
  out.ok = true;
} catch (e) {
  out.error = String(e).slice(0, 300);
} finally { await br.close(); }
console.log(JSON.stringify(out));
