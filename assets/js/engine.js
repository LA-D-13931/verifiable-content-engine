/* ============================================================
 * 模块 7：实验引擎
 * 载入实验 / 判题 / 进度存档 / 工具栏动作分发 / 变换动画
 * ============================================================ */
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
    }

    /* ---------- 判题 ---------- */
    function vecEq(a, b, tol) {
        const t = tol == null ? 0.15 : tol;
        return a.length === b.length && a.every((x, i) => Math.abs(x - b[i]) <= t);
    }

    /* 两条直线 ax+by=c 的交点；平行（行列式为 0）时返回 null */
    function intersectPair(l1, l2) {
        const d = l1.a * l2.b - l2.a * l1.b;
        if (Math.abs(d) < 1e-9) return null;
        return [(l1.c * l2.b - l2.c * l1.b) / d, (l1.a * l2.c - l2.a * l1.c) / d];
    }

    /* 取同时落在前 n 条直线上的那个交点（容差 0.05） */
    function intersectLines(lines, n) {
        const use = lines.slice(0, n);
        for (let i = 0; i < use.length; i++) {
            for (let j = i + 1; j < use.length; j++) {
                const p = intersectPair(use[i], use[j]);
                if (!p) continue;
                const onAll = use.every(l => Math.abs(l.a * p[0] + l.b * p[1] - l.c) < 0.05);
                if (onAll) return p;
            }
        }
        return null;
    }

    function normVec(v) {
        const L = Math.hypot.apply(null, v) || 1;
        return v.map(x => x / L);
    }

    function currentMatrix() { return App.matrix; }

    /* 判题上下文：交给注册表的处理器使用。
       刻意做成「显式传入」而不是让处理器直接读 App —— 这样注册表里的
       判定逻辑不依赖全局状态，可以在没有页面的环境（Node 测试）里单独跑。 */
    function judgeContext(taskId) {
        return {
            taskId: taskId,
            matrix: App.matrix,
            vectors: App.vectors || [],
            lines: App.lines || [],
            choices: App.choices || {},
            actionLog: App.actionLog || [],   // 原实现用数组，不是对象
            Mat: Mat,
            vecEq: vecEq
        };
    }

    function checkTask(check, taskId) {
        /* 先问注册表：领域无关的判题类型（数值命中 / 矩阵相等 / 点积 /
           选择题 / 动作序列）由 assets/js/registry.js 处理。
           返回 null 表示该类型未注册，落到下面的领域专属分支。 */
        if (window.CheckRegistry) {
            const r = window.CheckRegistry.run(check, judgeContext(taskId));
            if (r !== null) return !!r.pass;
        }
        switch (check.type) {
            case 'vector-at': {
                const v = App.vectors.find(x => x.id === check.target);
                return !!v && vecEq(v.data, check.to, check.tol);
            }
            case 'av-at': {
                const v = App.vectors.find(x => x.id === 'v');
                if (!v || !App.matrix) return false;
                return vecEq(Mat.mulVec(App.matrix, v.data), check.to, check.tol);
            }
            case 'matrix-col-at': {
                if (!App.matrix) return false;
                return vecEq(App.matrix.map(r => r[check.col]), check.to, check.tol);
            }
            case 'match-matrix': {
                if (!App.matrix) return false;
                const tol = check.tol == null ? 0.05 : check.tol;
                return check.matrix.every((row, i) =>
                    row.every((x, j) => Math.abs(App.matrix[i][j] - x) <= tol));
            }
            case 'det': {
                if (!App.matrix) return false;
                const d = Mat.det(App.matrix);
                if (check.op === 'eq') return Math.abs(d - check.value) <= (check.tol || 0.05);
                if (check.op === 'lt') return d < check.value;
                if (check.op === 'gt') return d > check.value;
                return false;
            }
            case 'rank': {
                if (!App.matrix) return false;
                return Mat.rank(App.matrix) === check.value;
            }
            /* 行图像：拖动 v 去命中若干条直线的交点。
               先把直线两两求交，取那个同时落在所有直线上的点。 */
            case 'intercept': {
                const v = App.vectors.find(x => x.id === (check.target || 'v'));
                if (!v || !App.lines || App.lines.length < 2) return false;
                const p = intersectLines(App.lines, check.maxLines || App.lines.length);
                if (!p) return false;
                return vecEq(v.data, p, check.tol);
            }
            /* v 是否落在零空间里：A·v ≈ 0，且 v 不是零向量 */
            case 'null-space': {
                const v = App.vectors.find(x => x.id === (check.target || 'v'));
                if (!v || !App.matrix) return false;
                if (Math.hypot.apply(null, v.data) < (check.minLen || 0.25)) return false;
                const av = Mat.mulVec(App.matrix, v.data);
                if (Math.hypot.apply(null, av) > (check.tol || 0.08)) return false;
                if (check.dir) {
                    const d = Math.abs(Mat.dot(normVec(v.data), normVec(check.dir)));
                    if (d < (check.minCos || 0.98)) return false;
                }
                return true;
            }
            /* 特征值：v 与 Av 共线，且缩放倍数等于目标 λ。
               λ = (Av·v)/(v·v)，对共线情形（同向或反向）都成立。 */
            case 'eigen': {
                const v = App.vectors.find(x => x.id === (check.target || 'v'));
                if (!v || !App.matrix) return false;
                const vv = Mat.dot(v.data, v.data);
                if (vv < 1e-6) return false;
                const av = Mat.mulVec(App.matrix, v.data);
                const lam = Mat.dot(av, v.data) / vv;
                if (Math.abs(lam - check.value) > (check.tol || 0.12)) return false;
                // 共线包含同向（0°）与反向（180°）两种情况，
                // angleBetweenDeg 对反向给 180，所以要折回锐角再比
                const ang = Mat.angleBetweenDeg(v.data, av);
                return Math.min(ang, 180 - ang) <= (check.tolDeg || 4);
            }
            /* 在新基 P 下看当前变换：要求 P⁻¹AP 等于目标矩阵 */
            case 'in-basis-matrix': {
                if (!App.matrix || !check.basis) return false;
                const Pi = Mat.inv2(check.basis);
                if (!Pi) return false;
                const got = Mat.mul(Mat.mul(Pi, App.matrix), check.basis);
                const tol = check.tol == null ? 0.08 : check.tol;
                return check.matrix.every((row, i) =>
                    row.every((x, j) => Math.abs(got[i][j] - x) <= tol));
            }
            /* v 是否落在矩阵列张成的（低维）子空间里。
               做法：把 v 并成矩阵的最后一列，比较秩有没有变大。
               秩不变 ⇒ v 在列空间里；秩变大 ⇒ v 在列空间外。
               这个判定对 2×2 与 3×3 都成立。 */
            case 'on-span': {
                const v = App.vectors.find(x => x.id === (check.target || 'v'));
                if (!v || !App.matrix) return false;
                const m = App.matrix;
                const aug = m.map((row, i) => row.concat([v.data[i]]));
                const grew = Mat.rank(aug) > Mat.rank(m);
                if (check.op === 'in') return !grew;
                if (check.op === 'out') return grew;
                return false;
            }
            case 'in-basis': {
                // v 在新基（当前矩阵两列）下的坐标 = B⁻¹v
                const v = App.vectors.find(x => x.id === (check.target || 'v'));
                if (!v || !App.matrix || App.matrixSize !== 2) return false;
                const c = Mat.solve2(App.matrix, v.data);
                return !!c && vecEq(c, check.to, check.tol);
            }
            /* 两向量的夹角：可要求等于目标角度（带容差），也可要求两者都是单位向量 */
            case 'vector-angle': {
                const a = App.vectors.find(x => x.id === check.a);
                const b = App.vectors.find(x => x.id === check.b);
                if (!a || !b) return false;
                const la = Math.hypot.apply(null, a.data);
                const lb = Math.hypot.apply(null, b.data);
                if (la < 1e-6 || lb < 1e-6) return false;
                if (check.unit && (Math.abs(la - 1) > (check.unitTol || 0.06)
                                || Math.abs(lb - 1) > (check.unitTol || 0.06))) return false;
                const ang = Mat.angleBetweenDeg(a.data, b.data);
                return Math.abs(ang - check.value) <= (check.tol || 5);
            }
            case 'dot': {
                const a = App.vectors.find(x => x.id === check.a);
                const b = App.vectors.find(x => x.id === check.b);
                if (!a || !b) return false;
                const d = Mat.dot(a.data, b.data);
                if (check.op === 'eq') return Math.abs(d - check.value) <= (check.tol || 0.05);
                if (check.op === 'lt') return d < check.value;
                if (check.op === 'gt') return d > check.value;
                return false;
            }
            case 'cross-mag': {
                if (!App.matrix || App.matrixSize !== 3) return false;
                const a = App.matrix.map(r => r[check.colA]);
                const b = App.matrix.map(r => r[check.colB]);
                const mag = Math.hypot.apply(null, Mat.cross(a, b));
                if (check.op === 'eq') return Math.abs(mag - check.value) <= (check.tol || 0.05);
                if (check.op === 'lt') return mag < check.value;
                if (check.op === 'gt') return mag > check.value;
                return false;
            }
            /* a×b 的方向是否与给定方向一致（用归一化后的点积 ≥ minCos 判定） */
            case 'cross-dir': {
                if (!App.matrix || App.matrixSize !== 3) return false;
                const a = App.matrix.map(r => r[check.colA]);
                const b = App.matrix.map(r => r[check.colB]);
                const c = Mat.cross(a, b);
                const L = Math.hypot(c[0], c[1], c[2]);
                if (L < 1e-6) return false;
                const u = [c[0] / L, c[1] / L, c[2] / L];
                const tl = Math.hypot.apply(null, check.dir) || 1;
                const t = check.dir.map(x => x / tl);
                const d = u[0] * t[0] + u[1] * t[1] + u[2] * t[2];
                return d >= (check.minCos == null ? 0.999 : check.minCos);
            }
            case 'solve': {
                const v = App.vectors.find(x => x.id === 'v');
                if (!v || !App.matrix) return false;
                return vecEq(Mat.mulVec(App.matrix, v.data), check.to, check.tol);
            }
            case 'collinear': {
                const v = App.vectors.find(x => x.id === 'v');
                if (!v || !App.matrix) return false;
                const av = Mat.mulVec(App.matrix, v.data);
                if (Math.hypot(v.data[0], v.data[1]) < 0.25) return false;
                if (Math.hypot(av[0], av[1]) < 1e-6) return false;
                const ang = Mat.angleBetweenDeg(v.data, av);
                return Math.min(ang, 180 - ang) <= (check.tolDeg || 4);
            }
            /* 辨析题：只有当这一次的选择确实属于这道题时才算数。
               同一关里可能有两道辨析题，必须用 taskId 区分，否则会互相干扰。 */
            case 'choice':
                return taskId != null && App.choices[taskId] === check.correct;
            case 'actions': {
                if (check.ordered) {
                    let pos = 0;
                    for (const a of App.actionLog) {
                        if (a === check.all[pos]) pos++;
                        if (pos >= check.all.length) return true;
                    }
                    return false;
                }
                return check.all.every(a => App.actionLog.includes(a));
            }
            default:
                return false;
        }
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
