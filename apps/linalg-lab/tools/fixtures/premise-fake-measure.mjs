// 夹具（第十五轮批次 A ②(b)）：假量测脚本 —— 只打印 {"skipped": …} 并 exit 0。
//
// 用途：让 apps/linalg-lab/tools/check-skip-exit.py 的 verify_premise() 能**端到端**验证
// 「checks_render.render_measure() 会把 skipped 转成非 pass 态」这条豁免前提。
// 它**入库**（有 revision、可被审），运行时由 verify_premise() 复制到 workspace_root() 认的位置，finally 清理。
// 输出文案里带 "批次 B 假量测输出" —— 那条断言靠它区分"命中的是 skipped 分支"
// 还是"别的早退分支（也是 pass=None）"。
console.log(JSON.stringify({ skipped: '批次 B 假量测输出' }));
