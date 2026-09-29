/* 浏览器内的工具栏动作校验：
   把每个实验的工具栏动作在真实页面上跑一遍，检查两件事：
     1) preset / mul-left 的 matrix 与 match-matrix 任务的目标是否一致
     2) mul-left 序列跑完后，det 是否等于 det 任务要求的目标
   这能在浏览器里用真正的 Mat 实现验证矩阵运算，避免手算出错。
   用法：node tools/verify-actions.js [baseUrl]   （需要先起静态服务） */
const puppeteer = require('puppeteer-core');
const EDGE = '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge';
const BASE = process.argv[2] || 'http://127.0.0.1:8791/apps/linalg-lab';

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
    await page.goto(BASE + '/index.html', { waitUntil: 'domcontentloaded' });
    await page.evaluate(() => localStorage.clear());
    await page.reload({ waitUntil: 'networkidle0' });

    console.log('=== 第一部分：每个工具栏按钮点一遍，检查日志是否真的增长 ===');
    const logReport = await page.evaluate(() => {
        const out = [];
        LABS.forEach(lab => {
            const tools = (lab.scene.toolbar || []);
            tools.forEach((tool, k) => {
                Engine.loadLab(lab.id);
                const before = App.actionLog.length;
                Engine.runAction(App.toolbar[k]);
                const grew = App.actionLog.length > before;
                // 该按钮的日志名是否被某个 actions 任务依赖
                const name = tool.log || tool.action;
                const needed = LABS.some(l => l.tasks.some(t =>
                    t.check.type === 'actions' && (t.check.all || []).includes(name)));
                out.push({ lab: lab.id, tool: tool.id, action: tool.action,
                           log: name, grew, needed });
            });
        });
        return out;
    });
    // 只有「被 actions 任务依赖」的按钮才必须写日志；
    // 纯演示按钮（如 reveal-eigen / toggle-space）不写日志不算问题
    let bad = 0;
    logReport.forEach(r => {
        if (r.needed && !r.grew) {
            bad++;
            console.log(`  ✗ ${r.lab} 的按钮「${r.tool}」(${r.action}) 被任务依赖，但点了不写日志`);
        }
    });
    const neededCount = logReport.filter(r => r.needed).length;
    const idleNoLog = logReport.filter(r => !r.needed && !r.grew).map(r => r.action);
    ok(bad === 0,
       `${neededCount} 个被任务依赖的按钮全都写了动作日志（漏写 ${bad} 个）`
       + (idleNoLog.length ? `；另有 ${idleNoLog.length} 个纯演示按钮不写日志（无害）` : ''));

    // 逐关：该关所有 actions 型任务是否都能通过「把按钮都点一遍」完成
    const seqReport = await page.evaluate(() => {
        const out = [];
        LABS.forEach(lab => {
            const actTasks = lab.tasks.filter(t => t.check.type === 'actions');
            if (!actTasks.length) return;
            Engine.loadLab(lab.id);
            (App.toolbar || []).forEach(t => Engine.runAction(t));
            actTasks.forEach(t => out.push({ lab: lab.id, task: t.id,
                                             pass: !!App.taskStatus[t.id], need: t.check.all }));
        });
        return out;
    });
    const failed = seqReport.filter(r => !r.pass);
    failed.forEach(r => console.log(`  ✗ ${r.lab} 任务 ${r.task} 需要 ${JSON.stringify(r.need)}，点完所有按钮仍未通过`));
    ok(failed.length === 0, `${seqReport.length} 个 actions 型任务在「点完该关所有按钮」后全部通过`);

    console.log('\n=== 第二部分：preset 与序列的矩阵复算 ===');
    // 收集所有带工具栏的实验
    const labs = await page.evaluate(() => LABS
        .filter(l => (l.scene.toolbar || []).length)
        .map(l => ({ id: l.id, title: l.title })));
    console.log(`带工具栏的实验：${labs.length} 个\n`);

    for (const lab of labs) {
        const r = await page.evaluate((labId) => {
            const out = { checks: [], notes: [] };
            Engine.loadLab(labId);
            const tools = App.toolbar;

            // 1) preset 动作：跑一遍，看是否与某个 match-matrix 任务一致
            for (const tool of tools) {
                if (tool.action !== 'preset' || !tool.matrix) continue;
                Engine.loadLab(labId);
                Engine.runAction(tool);
                const m = App.matrix;
                const lab0 = Engine.getLab(labId);
                const mmTask = lab0.tasks.find(t => t.check.type === 'match-matrix');
                if (!mmTask) continue;
                const target = mmTask.check.matrix;
                const tol = mmTask.check.tol == null ? 0.05 : mmTask.check.tol;
                const same = m.length === target.length && m.every((row, i) =>
                    row.every((x, j) => Math.abs(x - target[i][j]) <= tol));
                out.checks.push({ kind: 'preset', tool: tool.id, same, got: m, want: target });
            }

            // 2) mul-left / mul-left-inv 序列：按顺序全部跑一遍，比较 det 目标
            const seq = tools.filter(t => ['mul-left', 'mul-left-inv', 'mul-left-3'].includes(t.action));
            const pureForward = seq.length > 0 && seq.every(t => t.action === 'mul-left');
            if (seq.length) {
                Engine.loadLab(labId);
                const log = [];
                for (const tool of seq) { Engine.runAction(tool); log.push(tool.id); }
                const m = App.matrix;
                const det = Mat.det(m);
                const lab0 = Engine.getLab(labId);
                const detTask = lab0.tasks.find(t => t.check.type === 'det' && t.check.op === 'eq');
                out.notes.push({ kind: 'seq', order: log, matrix: m, det: Math.round(det * 1e6) / 1e6,
                                 detTask: detTask ? detTask.check.value : null, pureForward });
                // 有 match-matrix 任务时也一并比对
                const mmTask = lab0.tasks.find(t => t.check.type === 'match-matrix');
                if (mmTask) {
                    const target = mmTask.check.matrix;
                    const tol = mmTask.check.tol == null ? 0.05 : mmTask.check.tol;
                    const same = m.length === target.length && m.every((row, i) =>
                        row.every((x, j) => Math.abs(x - target[i][j]) <= tol));
                    out.notes.push({ kind: 'seq-vs-match-matrix', same, got: m, want: target });
                }
            }
            return out;
        }, lab.id);

        console.log(`【${lab.id}】${lab.title}`);
        if (r.checks.length) {
            const hit = r.checks.filter(c => c.same);
            ok(hit.length >= 1,
               `至少有一个 preset 命中 match-matrix 目标 ${JSON.stringify(r.checks[0].want)}`
               + `（共 ${r.checks.length} 个 preset，命中 ${hit.length} 个）`);
            if (hit.length === 0) {
                r.checks.forEach(c => console.log(
                    `      · preset「${c.tool}」得到 ${JSON.stringify(c.got)}`));
            } else {
                console.log(`      · 命中：${hit.map(c => c.tool).join('、')}`);
            }
        }
        for (const n of r.notes) {
            if (n.kind === 'seq') {
                console.log(`  · 依次执行 ${n.order.join(' → ')} ⇒ ${JSON.stringify(n.matrix)}，det = ${n.det}`
                    + (n.detTask != null && n.pureForward ? `（det 任务目标 ${n.detTask}）`
                       : (n.pureForward ? '' : '（含撤销动作，不作 det 比对）')));
                if (n.detTask != null && n.pureForward) {
                    ok(Math.abs(n.det - n.detTask) < 0.11,
                       `序列 det ${n.det} 与任务目标 ${n.detTask} 相符`);
                }
            } else if (n.kind === 'seq-vs-match-matrix') {
                ok(n.same, `序列结果 ${JSON.stringify(n.got)} 与 match-matrix 目标 ${JSON.stringify(n.want)} 一致`);
            }
        }
        console.log('');
    }

    ok(errors.length === 0, `无页面异常${errors.length ? '：' + errors.join(' | ') : ''}`);
    await browser.close();
    console.log(fail.length === 0 ? '全部通过 ✓' : `失败 ${fail.length} 项 ✗`);
    fail.forEach(f => console.log('   - ' + f));
    process.exit(fail.length === 0 ? 0 : 1);
})().catch(e => { console.error('崩溃：', e); process.exit(2); });
