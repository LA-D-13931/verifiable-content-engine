/**
 * D-4a：浏览器路径的**四级回退**（6 个脚本共用这一份，不许各写一份）。
 *
 *   ① 显式声明        —— 调用方传入（resolveBrowser({ explicit })，如 manifest 声明）或 LIN_ENGINE_BROWSER
 *   ② 环境变量        —— PUPPETEER_EXECUTABLE_PATH
 *                        （`puppeteer-core` 是 core 版、**不带浏览器、也不会自动读它** → 必须自己读）
 *   ③ 跨平台探测      —— macOS / Windows / Linux 的常见安装位置 + PATH 上的可执行名
 *   ④ 全部失败        —— **exit 2**（环境不足），并打印四级各试过什么
 *
 * ## 一条刻意的设计：① 与 ② **优先且权威**
 * 只要它们被设置，就必须可用；**不可用就直接 exit 2，不许静默回退到探测**。
 * 理由：声明了的东西不能悄悄被忽略 —— 那正是 `RX-01` 要治的病
 * （"没按我声明的方式跑"与"通过了"在退出码上必须可区分）。
 * 反例（审计方第九轮定的验收）：`PUPPETEER_EXECUTABLE_PATH=/nonexistent` → **必须 exit 2**。
 */
import { readFileSync, existsSync } from 'node:fs';
import { delimiter, join } from 'node:path';

const MAC = [
  '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/Applications/Chromium.app/Contents/MacOS/Chromium',
  '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser',
];
const WIN = [
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
  'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
];
const LINUX = [
  '/usr/bin/microsoft-edge', '/usr/bin/microsoft-edge-stable',
  '/usr/bin/google-chrome', '/usr/bin/google-chrome-stable',
  '/usr/bin/chromium', '/usr/bin/chromium-browser', '/snap/bin/chromium',
];
const NAMES = ['msedge', 'microsoft-edge', 'google-chrome', 'google-chrome-stable',
               'chromium', 'chromium-browser', 'chrome'];

function usable(p) {
  try { return Boolean(p) && existsSync(p) && readFileSync(p).length > 0; } catch { return false; }
}
function onPath(name) {
  for (const dir of (process.env.PATH || '').split(delimiter)) {
    if (!dir) continue;
    const p = join(dir, name);
    if (usable(p)) return p;
  }
  return null;
}

export function resolveBrowser(opts = {}) {
  const tried = [];
  const declared = [['① 显式声明（调用方）', opts.explicit],
                    ['① 显式声明（LIN_ENGINE_BROWSER）', process.env.LIN_ENGINE_BROWSER],
                    ['② PUPPETEER_EXECUTABLE_PATH', process.env.PUPPETEER_EXECUTABLE_PATH]];
  for (const [how, p] of declared) {
    if (!p) continue;
    tried.push([how, p, usable(p)]);
    // 声明了就必须可用：不可用 → 立刻 exit 2（不许静默回退）
    if (!usable(p)) fail(tried, `按你声明的方式找不到可用的浏览器：${how} = ${p}`);
  }
  for (const [how, p] of declared) if (p) return p;

  const cands = process.platform === 'darwin' ? MAC : process.platform === 'win32' ? WIN : LINUX;
  for (const p of cands) {
    tried.push(['③ 平台探测', p, usable(p)]);
    if (usable(p)) return p;
  }
  for (const n of NAMES) {
    const p = onPath(n);
    tried.push(['③ PATH 查找', n, Boolean(p)]);
    if (p) return p;
  }
  fail(tried, '四级都试过，找不到可用的浏览器');
}

function fail(tried, why) {
  console.error('环境不足（exit 2）：' + why);
  console.error('  已尝试：');
  for (const [how, p, ok] of tried) console.error(`    ${ok ? '✓' : '✗'} ${how}  ${p}`);
  console.error('  可用声明方式：LIN_ENGINE_BROWSER=<路径> 或 PUPPETEER_EXECUTABLE_PATH=<路径>');
  process.exit(2);
}
