/* 冒烟测试：真实浏览器里加载页面，检查控制台错误 + 模拟拖拽完成第 1 关。
   用法：node tools/smoke.js [baseUrl]
   需要本机已安装 Microsoft Edge。 */
const puppeteer = require('puppeteer-core');

const EDGE = '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge';
const BASE = process.argv[2] || 'http://127.0.0.1:8791';

const fail = [];
function ok(cond, msg) {
    console.log(`${cond ? '  ✓' : '  ✗'} ${msg}`);
    if (!cond) fail.push(msg);
}

(async () => {
    const browser = await puppeteer.launch({
        executablePath: EDGE,
        headless: 'new',
        args: ['--no-sandbox', '--disable-gpu', '--window-size=1440,900'],
        defaultViewport: { width: 1440, height: 900 }
    });
    const page = await browser.newPage();

    const errors = [];
    page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
    page.on('pageerror', e => errors.push('pageerror: ' + e.message));

    await page.goto(BASE + '/index.html', { waitUntil: 'domcontentloaded' });
    await page.evaluate(() => localStorage.clear());
    await page.reload({ waitUntil: 'networkidle0' });
    await new Promise(r => setTimeout(r, 600));

    console.log('\n[1] 加载与初始化');
    ok(errors.length === 0, `无控制台错误${errors.length ? '：' + errors.join(' | ') : ''}`);
    ok(await page.$eval('#level-title', e => e.textContent.trim()) !== '加载中…', '任务卡已渲染标题');
    const navChapters = await page.evaluate(() => ({
        rendered: document.querySelectorAll('#chapter-list .chapter').length,
        withLabs: CHAPTERS.filter(c => LABS.some(l => l.chapter === c.id)).length
    }));
    ok(navChapters.rendered === navChapters.withLabs,
       `学习路径渲染了全部有实验的章节（${navChapters.rendered}/${navChapters.withLabs}）`);
    ok(await page.evaluate(() => document.getElementById('progress-text').textContent.includes('/' + LABS.length)), '进度显示 x/' + await page.evaluate(() => LABS.length));
    ok(await page.$eval('#matrix-grid', e => e.children.length) > 0, '矩阵面板已渲染');

    console.log('\n[2] 画布几何与命中测试');
    const geo = await page.evaluate(() => {
        const h = Interact.handles();
        const c = document.getElementById('stage-canvas');
        const r = c.getBoundingClientRect();
        return {
            handles: h.length,
            hx: h[0].screen.x, hy: h[0].screen.y,
            ox: Render2D.width / 2 + App.cam2d.panX,
            oy: Render2D.height / 2 + App.cam2d.panY,
            rectW: r.width, rectH: r.height,
            dpr: window.devicePixelRatio
        };
    });
    ok(geo.handles === 1, '第 1 关只有 1 个可拖手柄');
    ok(Math.abs(geo.hx - geo.ox) < 1.5 && Math.abs(geo.hy - geo.oy) < 1.5,
       `原点手柄落在视口原点（hx=${geo.hx.toFixed(2)} ox=${geo.ox.toFixed(2)} hy=${geo.hy.toFixed(2)} oy=${geo.oy.toFixed(2)}）`);
    ok(Math.abs(geo.rectW - await page.evaluate(() => Render2D.width)) < 1,
       '画布 CSS 尺寸与逻辑尺寸一致（DPR 适配正确）');

    console.log('\n[3] 拖拽向量完成任务 1-1');
    await page.evaluate(() => { App.vectors[0].data = [2, 1]; Engine.afterChange(); });
    await new Promise(r => setTimeout(r, 200));
    ok(await page.evaluate(() => !!App.taskStatus['place']), '拖到 (2,1) 后任务 place 判定通过');
    ok(await page.$eval('#task-list', e => e.querySelectorAll('.task.done').length) === 1, '任务卡出现 1 个已完成标记');

    console.log('\n[4] 概念辨析题：不泄露答案 + 可重试');
    const correctIdx = await page.evaluate(() => {
        const lab = Engine.getLab(App.labId);
        return lab.tasks.find(t => t.check.type === 'choice').check.correct;
    });
    ok(Number.isInteger(correctIdx) && correctIdx >= 0 && correctIdx <= 2,
       `正解下标合法（correct = ${correctIdx}）`);

    // 故意选一个错的（挑一个不等于 correct 的下标）
    const wrongIdx = correctIdx === 0 ? 1 : 0;
    await page.evaluate(i => document.querySelectorAll('.choice-opt')[i].click(), wrongIdx);
    await new Promise(r => setTimeout(r, 250));
    const wrongState = await page.evaluate(() => ({
        right: document.querySelectorAll('.choice-opt.right').length,
        wrong: document.querySelectorAll('.choice-opt.wrong').length,
        disabled: document.querySelectorAll('.choice-opt[disabled]').length,
        explains: document.querySelectorAll('.choice-explain').length,
        retry: !!document.querySelector('.choice-retry'),
        stored: Object.keys(App.choices).length
    }));
    ok(wrongState.right === 0, '选错时正确项没有被标出来（不泄露答案）');
    ok(wrongState.wrong === 1, '只有自己选的那一项被标为错误');
    ok(wrongState.disabled === 0, '选错后所有选项仍可点击（允许重试）');
    ok(wrongState.explains === 1, '只显示自己所选那一条的解释');
    ok(wrongState.retry, '选错后出现「再试一次」按钮');
    ok(wrongState.stored === 1, '选错的选择被记在该题名下');
    ok(!await page.evaluate(() => Engine.allTasksDone(Engine.getLab('1-1'))),
       '选错时任务不算完成');

    // 重试 → 选对
    await page.evaluate(() => document.querySelector('.choice-retry').click());
    await new Promise(r => setTimeout(r, 200));
    ok(await page.evaluate(() => Object.keys(App.choices).length === 0), '「再试一次」清除了本题的选择');
    await page.evaluate(i => document.querySelectorAll('.choice-opt')[i].click(), correctIdx);
    await new Promise(r => setTimeout(r, 250));
    const rightState = await page.evaluate(() => ({
        right: document.querySelectorAll('.choice-opt.right').length,
        disabled: document.querySelectorAll('.choice-opt[disabled]').length,
        retry: !!document.querySelector('.choice-retry')
    }));
    ok(rightState.right === 1, '选对后正确项才被标记');
    ok(rightState.disabled >= 2, '选对后锁定选项');
    ok(!rightState.retry, '选对后不再显示重试按钮');
    ok(await page.evaluate(() => Engine.allTasksDone(Engine.getLab('1-1'))), '1-1 全部任务完成');

    console.log('\n[4b] 同一关两道辨析题：各存各的选择，解释不被挤掉');
    const twoQ = await page.evaluate(() => {
        Engine.loadLab('2-3');
        App.matrix = [[1, 0], [0, 1]]; Engine.afterChange();     // 先过掉操作任务
        const lab = Engine.getLab('2-3');
        const qs = lab.tasks.filter(t => t.check.type === 'choice');
        const boxes = document.querySelectorAll('.choice-box');
        // 第一道故意选错，第二道选对
        boxes[0].children[qs[0].check.correct === 0 ? 1 : 0].click();
        boxes[1].children[qs[1].check.correct].click();
        return null;
    });
    await new Promise(r => setTimeout(r, 350));
    const twoQState = await page.evaluate(() => {
        const boxes = [...document.querySelectorAll('.choice-box')];
        return {
            optsPerBox: boxes.map(b => b.querySelectorAll('.choice-opt').length),
            explains: document.querySelectorAll('.choice-explain').length,
            // 每道题的解释都必须排在该题全部选项之后
            orderOk: boxes.every(b => {
                const kids = [...b.children];
                const lastOpt = kids.map((k, i) => k.classList.contains('choice-opt') ? i : -1).filter(i => i >= 0).pop();
                const firstNonOpt = kids.findIndex(k => !k.classList.contains('choice-opt'));
                return firstNonOpt === -1 || firstNonOpt > lastOpt;
            }),
            stored: Object.keys(App.choices).length,
            status: Object.assign({}, App.taskStatus)
        };
    });
    ok(twoQState.optsPerBox.every(n => n === 3), `每个选项框都是 3 个选项（实为 ${twoQState.optsPerBox.join(', ')}）`);
    ok(twoQState.orderOk, '解释与重试都排在本题全部选项之后（不再把选项劈成两半）');
    ok(twoQState.stored === 2, '两道题各存各的选择（App.choices 有 2 条）');
    ok(twoQState.explains === 2, '两道题的反馈同时可见，互不挤掉');
    ok(twoQState.status['quiz2'] === true && !twoQState.status['quiz'],
       '答对的那道判过，答错的那道不判过');

    console.log('\n[5] 跨关卡：切换到第 2 章第 1 关并拖列向量');
    await page.evaluate(() => Engine.loadLab('2-1'));
    await new Promise(r => setTimeout(r, 300));
    const h2 = await page.evaluate(() => Interact.handles().length);
    ok(h2 === 2, '2-1 有 2 个列向量手柄');
    await page.evaluate(() => {
        App.matrix[0][0] = 2; App.matrix[1][0] = 1;
        App.matrix[0][1] = 0; App.matrix[1][1] = 2;
        Engine.afterChange();
    });
    await new Promise(r => setTimeout(r, 200));
    ok(await page.evaluate(() => !!App.taskStatus['col1'] && !!App.taskStatus['col2']), '两列到位后两个任务均通过');
    const detTxt = await page.$eval('#diag-list', e => e.textContent);
    ok(detTxt.includes('4'), '面板实时显示 det(A) = 4');

    console.log('\n[5b] 真实指针事件拖拽（不只改数据）');
    await page.evaluate(() => Engine.loadLab('2-1'));
    await new Promise(r => setTimeout(r, 250));
    const target = await page.evaluate(() => {
        const h = Interact.handles()[0];
        const r = document.getElementById('stage-canvas').getBoundingClientRect();
        const t = Render2D.w2s([2, 1]);
        return { from: [r.left + h.screen.x, r.top + h.screen.y], to: [r.left + t.x, r.top + t.y] };
    });
    await page.mouse.move(target.from[0], target.from[1]);
    await page.mouse.down();
    await page.mouse.move((target.from[0] + target.to[0]) / 2, (target.from[1] + target.to[1]) / 2, { steps: 6 });
    await page.mouse.move(target.to[0], target.to[1], { steps: 6 });
    await page.mouse.up();
    await new Promise(r => setTimeout(r, 200));
    const dragged = await page.evaluate(() => ({ col: App.matrix.map(r => r[0]), task: !!App.taskStatus['col1'] }));
    ok(dragged.task && Math.abs(dragged.col[0] - 2) < 1e-6 && Math.abs(dragged.col[1] - 1) < 1e-6,
       `鼠标真实拖拽后第 1 列 = (${dragged.col[0]}, ${dragged.col[1]})，任务通过`);

    console.log('\n[5c] 画布平移与缩放');
    const beforeCam = await page.evaluate(() => Object.assign({}, App.cam2d));
    const cbox = await page.evaluate(() => {
        const r = document.getElementById('stage-canvas').getBoundingClientRect();
        return [r.left + r.width * 0.75, r.top + r.height * 0.25];
    });
    await page.mouse.move(cbox[0], cbox[1]);
    await page.mouse.down();
    await page.mouse.move(cbox[0] + 60, cbox[1] + 40, { steps: 5 });
    await page.mouse.up();
    const afterPan = await page.evaluate(() => Object.assign({}, App.cam2d));
    ok(Math.abs(afterPan.panX - beforeCam.panX - 60) < 2 && Math.abs(afterPan.panY - beforeCam.panY - 40) < 2,
       `空白处拖拽完成平移（Δpan = ${(afterPan.panX - beforeCam.panX).toFixed(1)}, ${(afterPan.panY - beforeCam.panY).toFixed(1)}）`);
    await page.evaluate(() => {
        const r = document.getElementById('stage-canvas').getBoundingClientRect();
        Render2D.zoomAt(r.width / 2, r.height / 2, 1.25);
    });
    const afterZoom = await page.evaluate(() => App.cam2d.scale);
    ok(afterZoom > beforeCam.scale, `滚轮缩放生效（${beforeCam.scale.toFixed(1)} → ${afterZoom.toFixed(1)}）`);

    console.log('\n[6] 判题器各类型抽查');
    const checks = await page.evaluate(() => {
        const out = {};
        Engine.loadLab('4-1');
        App.matrix = [[2, 0], [0, 1]];
        out.detEq = Engine.checkTask({ type: 'det', op: 'eq', value: 2, tol: 0.15 });
        App.matrix = [[1, 1], [1, 1]];
        out.detZero = Engine.checkTask({ type: 'det', op: 'eq', value: 0, tol: 0.08 });
        out.rank1 = Engine.checkTask({ type: 'rank', value: 1 });
        Engine.loadLab('9-1');   // 特征向量课：A = [[2,1],[0,1]]
        App.vectors[0].data = [1, 0];
        out.collinear = Engine.checkTask({ type: 'collinear', tolDeg: 4 });
        App.vectors[0].data = [1, 1];
        out.notCollinear = Engine.checkTask({ type: 'collinear', tolDeg: 4 });
        Engine.loadLab('7-1');   // 列图像课：A = [[1,2],[1,−1]]
        App.vectors[0].data = [2, 1];
        out.solve = Engine.checkTask({ type: 'solve', to: [4, 1], tol: 0.2 });
        Engine.loadLab('10-1');
        out.det3 = Mat.det(App.matrix);
        return out;
    });
    ok(checks.detEq, 'det eq 判定');
    ok(checks.detZero, 'det = 0 判定');
    ok(checks.rank1, 'rank 判定');
    ok(checks.collinear, '特征方向 (1,0) 判定为共线');
    ok(!checks.notCollinear, '(1,1) 在 A=[[2,1],[0,1]] 下不是特征方向');
    ok(checks.solve, 'Av = b 解判定');
    ok(Math.abs(checks.det3 - 2) < 1e-9, `10-1 默认矩阵 det = ${checks.det3}（应为 2）`);

    console.log('\n[7] 三维实验渲染不报错');
    await page.evaluate(() => Engine.loadLab('10-1'));
    await new Promise(r => setTimeout(r, 400));
    const h3 = await page.evaluate(() => ({ space: App.space, n: Interact.handles().length }));
    ok(h3.space === '3d' && h3.n === 3, `10-1 是三维场景且有 3 个手柄（space=${h3.space} n=${h3.n}）`);
    ok(errors.length === 0, `新增控制台错误 ${errors.length} 个${errors.length ? '：' + errors.join(' | ') : ''}`);

    console.log('\n[6b] 新增工具栏动作（mul-left-inv）与过程性任务');
    const seqRun = await page.evaluate(() => {
        const out = {};
        // 6-4：施加 A、施加 B，再逆序撤销 B、A，应回到单位阵
        Engine.loadLab('6-4');
        const tools = App.toolbar;
        ['apply-a', 'apply-b', 'undo-b', 'undo-a'].forEach(id => {
            Engine.runAction(tools.find(t => t.id === id));
        });
        out.backToI = Math.abs(Mat.det(App.matrix) - 1) < 1e-9
            && Math.abs(App.matrix[0][1]) < 1e-9 && Math.abs(App.matrix[1][0]) < 1e-9
            && Math.abs(App.matrix[0][0] - 1) < 1e-9 && Math.abs(App.matrix[1][1] - 1) < 1e-9;
        out.taskBack = !!App.taskStatus['back'];
        out.taskUnwind = !!App.taskStatus['unwind'];
        out.log = App.actionLog.slice();

        // 4-4：三步复合 → [[-1,0],[2,1]]
        Engine.loadLab('4-4');
        ['apply-c', 'apply-b', 'apply-a'].forEach(id => {
            Engine.runAction(App.toolbar.find(t => t.id === id));
        });
        out.abc = App.matrix.map(r => r.map(x => Math.round(x * 1000) / 1000));
        out.taskSeq = !!App.taskStatus['seq'];
        out.taskAssoc = !!App.taskStatus['assoc'];
        return out;
    });
    ok(seqRun.backToI, '6-4：施加 A、B 后逆序撤销，矩阵回到单位阵');
    ok(seqRun.taskUnwind && seqRun.taskBack, '6-4：有序动作与回到单位阵两个任务都判过');
    ok(JSON.stringify(seqRun.abc) === JSON.stringify([[2, -1], [2, 0]]),
       `4-4：三步复合结果 = ${JSON.stringify(seqRun.abc)}（应为 [[2,-1],[2,0]]）`);
    ok(seqRun.taskSeq && seqRun.taskAssoc, '4-4：有序动作与结合律结果两个任务都判过');

    console.log('\n[7b] 新增渲染能力（spanView / basisCoords / dotPair / cross）');
    const renderCases = await page.evaluate(() => {
        const out = {};
        // 列空间视图：秩 1 与秩 2 都要能画
        Engine.loadLab('2-4');
        App.matrix = [[1, 1], [1, 1]]; App.spanView = true;
        Render2D.render(); out.rank1 = Mat.rank(App.matrix) === 1;
        App.matrix = [[1, 0], [0, 1]];
        Render2D.render(); out.rank2 = Mat.rank(App.matrix) === 2;
        // 三维叉积
        Engine.loadLab('10-1');
        App.matrix = [[1, 0, 0], [0, 1, 0], [0, 0, 1]];
        App.cross = { colA: 0, colB: 1, label: 'a×b' };
        Render3D.render();
        out.crossZero = Math.hypot.apply(null, Mat.cross([1, 0, 0], [0, 1, 0])) === 1;
        return out;
    });
    ok(renderCases.rank1 && renderCases.rank2, '列空间视图在秩 1 / 秩 2 下都能渲染');
    ok(renderCases.crossZero, '三维叉积渲染路径可用（|î×ĵ| = 1）');
    ok(errors.length === 0, `新增控制台错误 ${errors.length} 个`);

    console.log('\n[7c] 第 3 轮新增判题类型（intercept / null-space / eigen / in-basis-matrix）');
    const r3 = await page.evaluate(() => {
        const out = {};
        // 行图像：两条直线的交点 (2,1)
        Engine.loadLab('7-2');
        App.vectors.find(v => v.id === 'v').data = [2, 1];
        out.intercept = Engine.checkTask({ type: 'intercept', tol: 0.2 });
        App.vectors.find(v => v.id === 'v').data = [0, 0];
        out.interceptMiss = Engine.checkTask({ type: 'intercept', tol: 0.2 });
        // 零空间：A = [[1,1],[1,1]] 的零空间方向是 (1,-1)
        Engine.loadLab('7-5');
        App.vectors.find(v => v.id === 'v').data = [1, -1];
        out.nullOk = Engine.checkTask({ type: 'null-space', tol: 0.1, dir: [-1, 1] });
        App.vectors.find(v => v.id === 'v').data = [1, 1];
        out.nullBad = Engine.checkTask({ type: 'null-space', tol: 0.1, dir: [-1, 1] });
        // 特征值：反射矩阵 [[0,1],[1,0]] 在 (1,1) 上 λ=1，在 (1,-1) 上 λ=-1
        Engine.loadLab('9-2');
        App.vectors.find(v => v.id === 'v').data = [1, 1];
        out.eig1 = Engine.checkTask({ type: 'eigen', value: 1, tol: 0.12, tolDeg: 4 });
        App.vectors.find(v => v.id === 'v').data = [1, -1];
        out.eigM1 = Engine.checkTask({ type: 'eigen', value: -1, tol: 0.12, tolDeg: 4 });
        out.eigWrong = Engine.checkTask({ type: 'eigen', value: 5, tol: 0.12, tolDeg: 4 });
        // 相似矩阵：B = [[2,0],[0,1]] 时 B⁻¹AB = [[0,-0.5],[2,0]]（不等于 A！）
        // 不变量是迹与行列式，这里直接给出算好的结果
        Engine.loadLab('8-3');
        App.matrix = [[0, -1], [1, 0]];
        out.similar = Engine.checkTask({ type: 'in-basis-matrix', basis: [[2, 0], [0, 1]], matrix: [[0, -0.5], [2, 0]], tol: 0.1 });
        out.similarWrong = Engine.checkTask({ type: 'in-basis-matrix', basis: [[2, 0], [0, 1]], matrix: [[0, -1], [1, 0]], tol: 0.1 });
        // 对角化：A=[[2,1],[0,1]]，P=[[1,1],[0,-1]] ⇒ diag(2,1)
        Engine.loadLab('9-5');
        App.matrix = [[2, 1], [0, 1]];
        out.diag = Engine.checkTask({ type: 'in-basis-matrix', basis: [[1, 1], [0, -1]], matrix: [[2, 0], [0, 1]], tol: 0.12 });
        return out;
    });
    ok(r3.intercept && !r3.interceptMiss, 'intercept：命中交点 (2,1) 判过，原点判不过');
    ok(r3.nullOk && !r3.nullBad, 'null-space：(1,−1) 判过，(1,1) 判不过');
    ok(r3.eig1, 'eigen：v=(1,1) 在反射矩阵下 λ=1 判过');
    ok(r3.eigM1, 'eigen：v=(1,−1) 反向共线，λ=−1 判过');
    ok(!r3.eigWrong, 'eigen：λ=5 判不过');
    ok(r3.similar && !r3.similarWrong,
       'in-basis-matrix：B=[[2,0],[0,1]] 时 B⁻¹AB = [[0,−0.5],[2,0]] 判过，误写成 A 判不过');
    ok(r3.diag, 'in-basis-matrix：特征基下 [[2,1],[0,1]] 对角化为 diag(2,1)');

    console.log('\n[7d] 第 11–12 章新增判题（dot / vector-angle / cross-mag / cross-dir）');
    const r4 = await page.evaluate(() => {
        const out = {};
        Engine.loadLab('11-1');   // u = (2,1)
        App.vectors.find(v => v.id === 'v').data = [1, 2];
        out.dot4 = Engine.checkTask({ type: 'dot', a: 'u', b: 'v', op: 'eq', value: 4, tol: 0.3 });
        App.vectors.find(v => v.id === 'v').data = [1, -2];
        out.dot0 = Engine.checkTask({ type: 'dot', a: 'u', b: 'v', op: 'eq', value: 0, tol: 0.2 });
        out.dotMiss = Engine.checkTask({ type: 'dot', a: 'u', b: 'v', op: 'eq', value: 4, tol: 0.3 });

        Engine.loadLab('11-6');   // u = (1,0)
        const vv = App.vectors.find(v => v.id === 'v');
        vv.data = [0.5, Math.sqrt(3) / 2];
        out.angle60 = Engine.checkTask({ type: 'vector-angle', a: 'u', b: 'v', value: 60, tol: 4, unit: true, unitTol: 0.08 });
        out.angle60notUnit = Engine.checkTask({ type: 'vector-angle', a: 'u', b: 'v', value: 60, tol: 4 });
        vv.data = [1, 1];
        out.angle45notUnit = Engine.checkTask({ type: 'vector-angle', a: 'u', b: 'v', value: 45, tol: 4 });
        out.angle45rejectsNonUnit = Engine.checkTask({ type: 'vector-angle', a: 'u', b: 'v', value: 45, tol: 4, unit: true });

        Engine.loadLab('12-2');   // a = î, b = ĵ
        out.cross1 = Engine.checkTask({ type: 'cross-mag', colA: 0, colB: 1, op: 'eq', value: 1, tol: 0.1 });
        out.crossDir = Engine.checkTask({ type: 'cross-dir', colA: 0, colB: 1, dir: [0, 0, 1] });
        out.crossDirWrong = Engine.checkTask({ type: 'cross-dir', colA: 0, colB: 1, dir: [0, 0, -1] });
        return out;
    });
    ok(r4.dot4 && r4.dot0 && !r4.dotMiss, 'dot：u·v = 4 / 0 判过，目标 4 时 v=(1,−2) 判不过');
    ok(r4.angle60 && r4.angle60notUnit, 'vector-angle：60° 单位向量判过');
    ok(r4.angle45notUnit && !r4.angle45rejectsNonUnit,
       'vector-angle：45° 非单位向量在 unit:false 下判过、在 unit:true 下判不过');
    ok(r4.cross1, 'cross-mag：|î×ĵ| = 1 判过');
    ok(r4.crossDir && !r4.crossDirWrong, 'cross-dir：î×ĵ 方向为 k̂ 判过，−k̂ 判不过');

    console.log('\n[8] 进度持久化');
    const saved = await page.evaluate(() => {
        App.completed = ['1-1'];
        Engine.saveProgress();
        return localStorage.getItem('linalg-labs-progress-v1');
    });
    ok(saved && saved.includes('1-1'), '进度写入 localStorage');

    // 逐关截图由 tools/shots.js 负责，这里不再重复产图

    await browser.close();

    console.log(`\n${fail.length === 0 ? '全部通过 ✓' : '失败 ' + fail.length + ' 项 ✗'}`);
    fail.forEach(f => console.log('   - ' + f));
    process.exit(fail.length === 0 ? 0 : 1);
})().catch(e => { console.error('测试崩溃：', e); process.exit(2); });
