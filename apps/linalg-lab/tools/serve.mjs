/* 浏览器类工具共用的「页面地址解析器」。
   ============================================================
   结论先行：这些工具**不需要 HTTP 服务**。
   它们加载的是普通 <script src>（不是 ES module），file:// 下完全可用。
   历史：这里原本是个「本地服务管家」，会探活、找空闲端口、自己起 python http.server。
   它错了很多次（旧服务根目录不对、端口被占、子进程起不来），
   而每次的失败现象（404 / 连接被拒）都像是**被测内容坏了** —— 这是最糟的误导。
   改用 file:// 后这一类问题整体消失，也不需要任何人记得先起服务。

   仍然保留这个模块，但职责缩小为一件事：把「仓库内的相对路径」变成绝对地址。
   ============================================================
   为什么需要它（这不是洁癖，是踩过两次的坑）：

     浏览器类工具（verify-themes / verify-actions / smoke / verify-visual）
     假设 8791 端口上有一个**从仓库根启动**的静态服务。但那个服务是谁起的、
     根目录对不对，工具完全不知道。于是出现：

       · 旧服务从 apps/linalg-lab 起 → 请求 /apps/linalg-lab/index.html 得 404
       · 检查报「失败」，而失败原因跟被检查的东西毫无关系
       · 同一类问题**重复出现了两次**

     更糟的是这类失败容易被误读成「内容坏了」。所以把它做成代码：
     工具不再假设服务存在，而是**要一个可用的服务**，拿不到就明确报错。

   做法：
     1. 探活：请求 `<root>/<probe>`，若 200 说明现有服务可用，直接复用
     2. 探到 404/其它端口有杂服务 → 不抢端口，换一个空闲端口自己起
     3. 自己起的一定从仓库根起，起完再探活一次，确认能用
     4. 返回 { base, stop() }，调用方用完调 stop()

   用法：
     import { ensureServer } from './serve.mjs';
     const srv = await ensureServer({ probe: 'apps/linalg-lab/index.html' });
     console.log(srv.base);        // http://127.0.0.1:8791
     ...用完
     srv.stop();
   ============================================================ */
import { fileURLToPath, pathToFileURL } from 'node:url';
import { dirname, join, resolve } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const APP = dirname(HERE);
export const REPO = dirname(dirname(APP));      // 仓库根 —— 服务必须从这里起

/**
 * 返回可直接交给 puppeteer 的基址（file:// 协议）。
 * @param {{basePath?:string}} opts basePath：相对仓库根的路径，
 *        例如 '/apps/linalg-lab' 或 '/apps/linalg-lab/index.html'
 */
export function ensureServer(opts = {}) {
    const basePath = opts.basePath || '/apps/linalg-lab/index.html';
    return {
        base: pathToFileURL(join(REPO, basePath.replace(/^\//, ''))).href,
        port: null,
        reused: true,
        stop() {}
    };
}

/* 兼容旧调用名（这些工具原先用它来「要一个服务」） */
export const pageUrl = ensureServer;

/* 作为脚本直接跑：相当于「起一个可用的服务并保持」 */
if (process.argv[1] === fileURLToPath(import.meta.url)) {
    const srv = await ensureServer();
    console.log('页面地址：' + srv.base);
    console.log('（不需要起服务：这些工具走 file:// 即可）');
}
