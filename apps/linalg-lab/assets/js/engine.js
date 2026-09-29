/* ============================================================
 * 模块 7：实验引擎
 * 载入实验 / 判题 / 进度存档 / 工具栏动作分发 / 变换动画
 * ============================================================ */
/* 注意：本文件属于**应用层**，不是引擎。
   判题逻辑分两层，都在 engine-core/ 下：
     ① engine-core/registry.js        7 个领域无关类型
     ② engine-core/domains/<科目>/judge.js  学科专属判据
   本文件只保留 15 行的判题分派，其余是加载实验、进度存档、动画与工具栏编排，
   因此它引用了大量 App.* 字段——这些不属于可复用的引擎。 */
window.Engine = (function () {
    'use strict';

    const STORE_KEY = 'linalg-labs-progress-v1';

    function getLab(id) { return LABS.find(l => l.id === id); }

    function allTasksDone(lab) {
        return lab.tasks.length > 0 && lab.tasks.every(t => App.taskStatus[t.id]);
    }

    /* ---------- 进度 ---------- */
    function loadProgress() {
        try {
            const raw = localStorage.getItem(STORE_KEY);
            if (raw) {
                const d = JSON.parse(raw);
                App.completed = d.completed || [];
                return d.last || null;
            }
        } catch (err) { /* localStorage 不可用时静默降级 */ }
        return null;
    }

    function saveProgress() {
        try {
            localStorage.setItem(STORE_KEY, JSON.stringify({ v: 1, completed: App.completed, last: App.labId }));
        } catch (err) { /* 忽略 */ }
    }

    /* 注意：顺序解锁已经取消（学习工具不该锁住后面的内容），
       这个函数只为向后兼容保留，界面与 goNext 都不再调用它。 */
    function isUnlocked(index) {
        if (index === 0) return true;
        return App.completed.includes(LABS[index - 1].id);
    }

    /* ---------- 载入实验 ---------- */
    function loadLab(id) {
        const lab = getLab(id);
        if (!lab) return;
        App.labId = id;
        App.taskStatus = {};
        App.actionLog = [];
        App.choices = {};
        App.hover = null;
        App.showEigen = false;
        stopAnimation();

        const s = lab.scene;
        App.space = s.space || '2d';
        App.matrix = s.matrix ? Mat.clone(s.matrix) : null;
        App.matrixSize = s.matrixSize || (s.matrix ? s.matrix.length : 2);
        App.vectors = (s.vectors || []).map(v => Object.assign({}, v, { data: v.data.slice() }));
        App.shape = s.shape || null;
        App.lines = (s.lines || []).slice();
        App.targetPoint = s.targetPoint || null;
        App.grid = true;
        App.axes = true;
        App.tgrid = s.tgrid !== false;
        App.basis = !!s.basis;
        App.comboPath = !!s.comboPath;
        App.spanView = !!s.spanView;
        App.nullView = !!s.nullView;
        App.basisCoords = !!s.basisCoords;
        App.numLine = s.numLine || null;
        App.oneDim = s.oneDim || null;
        App.dotPair = s.dotPair || null;
        App.cross = s.cross || null;
        App.metric = s.metric || null;
        App.toolbar = s.toolbar || [];
        App.interact = Object.assign(
            { clickPlace: false, dragVectors: true, dragColumns: false, orbit: false },
            s.interact || {});
        App.cam2d = { scale: DEFAULT_SCALE, panX: 0, panY: 0 };
        App.cam3d = { yaw: -0.7, pitch: 0.4, dist: 11 };

        UI.renderAll();
        if (App.space === '2d') Render2D.fitView(); else Render2D.render();
        saveProgress();
        syncHash(id);
    }

    /* ---------- hash 路由 ----------
       让 `index.html#6-2` 这样的地址能直接打开指定实验，
       这样「配套讲义」链接才能从主站跳进具体某一关，而不是只到首页。 */
    function syncHash(id) {
        const want = '#' + id;
        if (window.location.hash !== want) {
            // replaceState 不产生历史记录，避免每换一关都往后退栈里塞一条
            try {
                history.replaceState(null, '', want);
            } catch (err) {
                window.location.hash = id;      // file:// 下可能受限，降级处理
            }
        }
    }

    /* 从当前地址读实验 id；没有或无效就返回 null */
    function labFromHash() {
        const raw = (window.location.hash || '').replace(/^#/, '').trim();
        if (!raw) return null;
        return getLab(raw) ? raw : null;
    }

    function goNext() {
        const idx = LABS.findIndex(l => l.id === App.labId);
        if (idx >= 0 && idx + 1 < LABS.length) {
            // 不设顺序锁：任何一个实验都可以自由进入
            UI.hideCelebrate();
            loadLab(LABS[idx + 1].id);
        } else {
            UI.hideCelebrate();
            UI.toast('已经是最后一个实验了，去沙盒模式玩吧');
        }
    }    function currentMatrix() { return App.matrix; }

    /* 向量近似相等。判题与外部都用到（Engine.vecEq 是公开接口），
       所以引擎层保留一份；domains/linalg/judge.js 里另有一份供领域判题使用。
       这两份是**刻意的小重复**：领域插件要能独立加载，不依赖引擎内部函数。
       代价是同一个函数两处维护，收益是模块边界干净。 */
    function vecEq(a, b, tol) {
        const t = tol == null ? 0.15 : tol;
        return a.length === b.length && a.every((x, i) => Math.abs(x - b[i]) <= t);
    }

    /* 判题上下文：交给注册表的处理器使用。
       刻意做成「显式传入」而不是让处理器直接读 App —— 这样注册表里的
       判定逻辑不依赖全局状态，可以在没有页面的环境（Node 测试）里单独跑。 */
    function judgeContext(taskId) {
        return {
            taskId: taskId,
            matrix: App.matrix,
            matrixSize: App.matrixSize,        // 领域判题要用（2×2 与 3×3 分支）
            vectors: App.vectors || [],
            lines: App.lines || [],
            choices: App.choices || {},
            actionLog: App.actionLog || [],   // 原实现用数组，不是对象
            param: App.param,                 // 可拖动标量参数（高数用：δ / h / 系数）
            Mat: Mat,
            vecEq: vecEq
        };
    }

    /* 判题总入口。
       分派顺序很重要：
         ① 引擎层注册表（assets/js/registry.js）—— 7 个领域无关的类型
         ② 领域插件（domains/<科目>/judge.js）—— 学科专属的判据
       两者都用同一份判题上下文 judgeContext()，都返回「结果对象」或 null。
       返回 null 表示「这不是我的类型」，由下一层接手。 */
    function checkTask(check, taskId) {
        const ctx = judgeContext(taskId);
        if (window.CheckRegistry) {
            const r = window.CheckRegistry.run(check, ctx);
            if (r !== null) return !!r.pass;
        }
        if (window.LinalgJudge) {
            const r = window.LinalgJudge.judge(check, ctx);
            if (r !== null) return !!r.pass;      // 两层返回结构一致（三元组）
        }
        if (window.CalculusJudge) {               // 高等数学（第二个科目）
            const r = window.CalculusJudge.judge(check, ctx);
            if (r !== null) return !!r.pass;
        }
        return false;
    }

    function logAction(name) {
        App.actionLog.push(name);
        evaluateTasks();
    }

    let celebrateShown = false;

    function evaluateTasks() {
        if (App.mode !== 'lab' || !App.labId) return;
        const lab = getLab(App.labId);
        if (!lab) return;
        let changed = false;
        lab.tasks.forEach(t => {
            if (!App.taskStatus[t.id] && checkTask(t.check, t.id)) {
                App.taskStatus[t.id] = true;
                changed = true;
            }
        });
        if (changed) UI.renderTaskCard();
        if (lab.tasks.length && allTasksDone(lab)) completeLab(lab);
    }

    function completeLab(lab) {
        const first = !App.completed.includes(lab.id);
        if (first) {
            App.completed.push(lab.id);
            saveProgress();
            UI.playChime();
        }
        UI.renderNav();
        UI.renderProgress();
        if (!celebrateShown) {
            celebrateShown = true;
            UI.showCelebrate(lab);
        }
    }

    function clearCelebrate() { celebrateShown = false; }

    /* ---------- 状态变化后的统一收口 ---------- */
    function afterChange() {
        Render2D.render();
        UI.updatePanels();
        evaluateTasks();
    }

    /* ---------- 工具栏动作 ---------- */
    function runAction(tool) {
        // 每个工具栏动作都记一条日志到 App.actionLog：
        // 日志名优先用 tool.log，其次用 tool.action（actions 型任务的判定依据）
        const logName = tool.log || tool.action;
        switch (tool.action) {
            case 'play-transform':
                playAnimation(App.matrix, null);
                logAction(logName);
                break;
            case 'play-inverse': {
                const inv = Mat.inv2(App.matrix);
                if (!inv) { UI.toast('det = 0，这个矩阵没有逆矩阵'); logAction(logName); break; }
                playAnimation(App.matrix, inv);
                logAction(logName);
                break;
            }
            case 'identity':
                App.matrix = Mat.identity(App.matrixSize);
                afterChange();
                logAction(logName);
                break;
            case 'preset':
                App.matrix = Mat.clone(tool.matrix);
                App.matrixSize = tool.matrix.length;
                afterChange();
                logAction(logName);
                break;
            case 'mul-left':
                App.matrix = Mat.mul(tool.matrix, App.matrix);
                afterChange();
                logAction(logName);
                break;
            /* 左乘给定矩阵三次：演示「特征方向上反复作用 = λ 连乘」 */
            case 'mul-left-3':
                App.matrix = Mat.mul(Mat.mul(tool.matrix, tool.matrix), Mat.mul(tool.matrix, App.matrix));
                afterChange();
                logAction(logName);
                break;
            /* 左乘一个给定矩阵的逆：用来演示「撤销上一步变换」。
               与 mul-left 的顺序一致，都是 M ← X·M 的写法。 */
            case 'mul-left-inv': {
                const inv = Mat.inv2(tool.matrix);
                if (!inv) { UI.toast('这个变换不可逆，撤不回来'); logAction(logName); break; }
                App.matrix = Mat.mul(inv, App.matrix);
                afterChange();
                logAction(logName);
                break;
            }
            case 'try-inverse': {
                const inv = Mat.inv2(App.matrix);
                if (!inv) {
                    UI.toast('det = 0，不可逆：空间已被压扁，无法还原');
                    logAction(logName);          // 算不出来也算「试过了」，必须记日志
                    break;
                }
                App.matrix = inv;
                afterChange();
                UI.toast('已应用 A⁻¹');
                logAction(logName);
                break;
            }
            case 'reveal-eigen': {
                App.showEigen = true;
                const e = App.matrix && App.matrixSize === 2 ? Mat.eigen2(App.matrix) : null;
                if (!e) UI.toast('这个矩阵没有实特征方向（旋转型矩阵）');
                else UI.toast(`λ₁ = ${round2(e.values[0])}，λ₂ = ${round2(e.values[1])}`);
                Render2D.render();
                break;
            }
            case 'toggle-space': {
                if (App.space === '2d') {
                    App.space = '3d';
                    App.matrix = [[App.matrix[0][0], App.matrix[0][1], 0],
                                  [App.matrix[1][0], App.matrix[1][1], 0],
                                  [0, 0, 1]];
                    App.matrixSize = 3;
                    App.shape = 'cube';
                } else {
                    App.space = '2d';
                    App.matrix = [[App.matrix[0][0], App.matrix[0][1]],
                                  [App.matrix[1][0], App.matrix[1][1]]];
                    App.matrixSize = 2;
                    App.shape = 'square';
                }
                UI.renderAll();
                Render2D.render();
                break;
            }
            default:
                break;
        }
    }

    /* ---------- 变换动画：从 from 插值到 to（线性插值） ---------- */
    let animRaf = null;

    function stopAnimation() {
        if (animRaf) cancelAnimationFrame(animRaf);
        animRaf = null;
        App.anim = null;
    }

    function playAnimation(from, to) {
        stopAnimation();
        const target = to || Mat.identity(from.length);
        const start = performance.now();
        const dur = 900;
        const origin = Mat.clone(from);
        App.anim = { from: origin, to: target, t: 0 };
        const tick = (now) => {
            const k = Math.min(1, (now - start) / dur);
            const e = k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2; // ease-in-out
            App.matrix = origin.map((row, i) => row.map((x, j) => x + (target[i][j] - x) * e));
            UI.updatePanels();
            Render2D.render();
            if (k < 1) {
                animRaf = requestAnimationFrame(tick);
            } else {
                App.matrix = Mat.clone(target);
                animRaf = null;
                App.anim = null;
                afterChange();
            }
        };
        animRaf = requestAnimationFrame(tick);
    }

    function round2(n) { return Math.round(n * 100) / 100; }

    return {
        getLab, loadLab, goNext, isUnlocked, loadProgress, saveProgress,
        labFromHash, syncHash,
        checkTask, evaluateTasks, afterChange, logAction, runAction,
        playAnimation, stopAnimation, clearCelebrate, allTasksDone, vecEq
    };
})();
