/* ============================================================
 * 模块 8：界面装配
 * 学习路径 / 任务卡 / 矩阵面板 / 工具栏 / 庆祝层 / 提示
 * ============================================================ */
window.UI = (function () {
    'use strict';

    const el = id => document.getElementById(id);
    let toastTimer = null;

    /* ---------- 小工具 ---------- */
    function toast(text) {
        const t = el('toast');
        t.textContent = text;
        t.classList.add('show');
        clearTimeout(toastTimer);
        toastTimer = setTimeout(() => t.classList.remove('show'), 2400);
    }

    function round2(n) { return Math.round(n * 100) / 100; }
    function fx(n) { return Math.abs(n) < 1e-9 ? '0' : String(round2(n)); }

    /* 首次通关的短音效（WebAudio 合成，无外部资源） */
    let audioCtx = null;
    function playChime() {
        try {
            audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
            const notes = [523.25, 659.25, 783.99];
            notes.forEach((f, i) => {
                const osc = audioCtx.createOscillator();
                const gain = audioCtx.createGain();
                osc.type = 'sine';
                osc.frequency.value = f;
                const t0 = audioCtx.currentTime + i * 0.11;
                gain.gain.setValueAtTime(0.0001, t0);
                gain.gain.exponentialRampToValueAtTime(0.16, t0 + 0.02);
                gain.gain.exponentialRampToValueAtTime(0.0001, t0 + 0.28);
                osc.connect(gain).connect(audioCtx.destination);
                osc.start(t0);
                osc.stop(t0 + 0.3);
            });
        } catch (err) { /* 音频不可用时忽略 */ }
    }

    /* ---------- 学习路径 ---------- */
    function renderNav() {
        const box = el('chapter-list');
        box.innerHTML = '';
        CHAPTERS.forEach(ch => {
            const labs = LABS.filter(l => l.chapter === ch.id);
            if (!labs.length) return;
            const done = labs.filter(l => App.completed.includes(l.id)).length;
            const sec = document.createElement('section');
            sec.className = 'chapter';
            sec.innerHTML =
                `<div class="chapter-head">
                    <span class="chapter-no">第 ${ch.id} 章</span>
                    <span class="chapter-count">${done}/${labs.length}</span>
                 </div>
                 <h3 class="chapter-title">${ch.title}</h3>
                 <p class="chapter-desc">${ch.desc}</p>`;
            const ul = document.createElement('ul');
            ul.className = 'lab-list';
            labs.forEach(lab => {
                const idx = LABS.indexOf(lab);
                const isDone = App.completed.includes(lab.id);
                const isCur = App.labId === lab.id;
                const li = document.createElement('li');
                li.className = 'lab-item' + (isCur ? ' current' : '') + (isDone ? ' done' : '');
                li.innerHTML =
                    `<button class="lab-btn" title="第 ${idx + 1} / ${LABS.length} 个实验 · ${lab.tasks.length} 个任务">
                        <span class="lab-dot">${isDone ? '✓' : ''}</span>
                        <span class="lab-id">${lab.id}</span>
                        <span class="lab-title">${lab.title}</span>
                    </button>`;
                // 全部实验都可以自由点开：这是学习工具，不该用「完成上一关」锁住后面的内容
                li.querySelector('button').addEventListener('click', () => Engine.loadLab(lab.id));
                ul.appendChild(li);
            });
            sec.appendChild(ul);
            box.appendChild(sec);
        });
    }

    function renderProgress() {
        const n = App.completed.length;
        el('progress-text').textContent = `实验进度 ${n}/${LABS.length}`;
        const dots = el('progress-dots');
        dots.innerHTML = '';
        LABS.forEach(lab => {
            const d = document.createElement('i');
            d.className = 'pdot' + (App.completed.includes(lab.id) ? ' on' : '');
            dots.appendChild(d);
        });
    }

    /* ---------- 任务卡 ---------- */
    function renderTaskCard() {
        const lab = Engine.getLab(App.labId);
        if (!lab) return;
        const idx = LABS.indexOf(lab);
        el('level-kicker').textContent = `第 ${lab.chapter} 章 · 第 ${idx + 1} 个实验`;
        el('level-title').textContent = lab.title;
        el('level-brief').innerHTML = lab.brief;

        const ul = el('task-list');
        ul.innerHTML = '';
        if (!lab.tasks.length) {
            const li = document.createElement('li');
            li.className = 'task free';
            li.innerHTML = '<span class="task-mark">∞</span><span>自由探索：没有任务，随便拖</span>';
            ul.appendChild(li);
        }
        lab.tasks.forEach(t => {
            const done = !!App.taskStatus[t.id];
            const li = document.createElement('li');
            li.className = 'task' + (done ? ' done' : '');
            li.innerHTML =
                `<span class="task-mark">${done ? '✓' : '○'}</span>
                 <span class="task-text">${t.text}</span>`;
            ul.appendChild(li);
            if (t.options) ul.appendChild(renderChoice(t));
        });

        renderCrossLink(lab);

        const hintBody = el('hint-body');
        hintBody.innerHTML = (lab.hints || []).map(h => `<p>${h}</p>`).join('') || '<p>本实验没有额外提示。</p>';
        el('hint-box').open = false;

        const actions = el('task-actions');
        actions.innerHTML = '';
        if (Engine.allTasksDone(lab)) {
            const b = document.createElement('button');
            b.className = 'btn primary';
            b.textContent = LABS.indexOf(lab) === LABS.length - 1 ? '去沙盒 →' : '下一个实验 →';
            b.addEventListener('click', () => Engine.goNext());
            actions.appendChild(b);
        }
    }

    /* ---------- 配套讲义链接 ----------
       数据来自 assets/js/crosslinks.js（由 线代_两站对照/tools/桥接.py 生成），
       路径前缀在 links-config.js 里，装到别处时只改那一行。
       找不到配置或映射时静默不显示，不影响实验台单独运行。 */
    function mainSiteBase() {
        const cfg = window.LINKS_CONFIG || {};
        let base = cfg.mainSite;
        if (!base) return null;
        return base.replace(/\/+$/, '') + '/';
    }

    function renderCrossLink(lab) {
        const box = el('crosslink');
        if (!box) return;
        const map = window.CROSSLINKS || {};
        const item = map[lab.id];
        if (!item) { box.style.display = 'none'; box.innerHTML = ''; return; }
        const base = mainSiteBase();
        if (!base) { box.style.display = 'none'; box.innerHTML = ''; return; }

        box.style.display = '';
        box.innerHTML = '';
        const title = document.createElement('div');
        title.className = 'crosslink-title';
        title.textContent = '配套讲义';
        box.appendChild(title);

        const a = document.createElement('a');
        a.className = 'crosslink-a';
        a.href = base + item.href;
        a.target = '_blank';
        a.rel = 'noopener';
        a.innerHTML = '<span class="crosslink-sec">' + item.title + '</span>'
                    + '<span class="crosslink-note">' + (item.note || '') + '</span>';
        box.appendChild(a);

        const tip = document.createElement('p');
        tip.className = 'crosslink-tip';
        tip.textContent = '在讲义里把这个概念算一遍，再回来拖一拖。';
        box.appendChild(tip);
    }

    /* ---------- 辨析题 ----------
       三条规矩：
         1) 只评判用户点的那一项，不把正确项标出来（否则等于公布答案）
         2) 答错只给「你选的这条为什么不对」的解释，并允许重试
         3) 答对之后才把正确项标记为确定，同时不再允许改答案
    */
    function renderChoice(task) {
        const wrap = document.createElement('li');
        wrap.className = 'choice-wrap';
        const box = document.createElement('div');
        box.className = 'choice-box';
        // 每道题各存各的选择
        const picked = Object.prototype.hasOwnProperty.call(App.choices, task.id)
            ? App.choices[task.id] : null;
        const answered = picked != null;
        const isRight = answered && picked === task.check.correct;
        const locked = isRight;          // 答对才锁死

        const btns = [];
        task.options.forEach((opt, i) => {
            const b = document.createElement('button');
            b.className = 'choice-opt';
            b.textContent = opt;

            if (answered && i === picked) {
                b.classList.add(isRight ? 'right' : 'wrong');
                b.classList.add('picked');
            }
            // 答错时其余选项保持原样，不暴露哪个才是对的
            b.disabled = locked;

            if (!locked) {
                b.addEventListener('click', () => {
                    if (i === picked) return;      // 已经选过这条，不动
                    App.choices[task.id] = i;
                    if (i !== task.check.correct) toast('这条不对，再想想');
                    renderTaskCard();
                    Engine.evaluateTasks();
                });
            }
            btns.push(b);
            box.appendChild(b);
        });

        // 解释与重试都放在**全部选项之后**。
        // 之前把它们插在选项中间，会把三个选项劈成两半，看起来像两组题。
        if (answered && task.explains) {
            const p = document.createElement('p');
            p.className = 'choice-explain' + (isRight ? ' right' : ' wrong');
            p.textContent = task.explains[picked];
            box.appendChild(p);
        }
        if (answered && !isRight) {
            const retry = document.createElement('button');
            retry.className = 'choice-retry';
            retry.textContent = '再试一次';
            retry.addEventListener('click', () => {
                delete App.choices[task.id];
                renderTaskCard();
            });
            box.appendChild(retry);
        }

        wrap.appendChild(box);
        return wrap;
    }

    function renderToolbar() {
        const bar = el('scene-toolbar');
        bar.innerHTML = '';

        // 上一关 / 下一关：让用户不必回左侧栏就能连续走
        const idx = LABS.findIndex(l => l.id === App.labId);
        const prev = document.createElement('button');
        prev.className = 'btn tool ghost';
        prev.textContent = '← 上一个';
        prev.disabled = idx <= 0;
        prev.addEventListener('click', () => { if (idx > 0) Engine.loadLab(LABS[idx - 1].id); });
        bar.appendChild(prev);

        const pos = document.createElement('span');
        pos.className = 'toolbar-pos';
        pos.textContent = `第 ${idx + 1} / ${LABS.length} 个`;
        bar.appendChild(pos);

        const next = document.createElement('button');
        next.className = 'btn tool';
        next.textContent = '下一个 →';
        next.disabled = idx < 0 || idx >= LABS.length - 1;
        next.addEventListener('click', () => {
            if (idx >= 0 && idx < LABS.length - 1) Engine.loadLab(LABS[idx + 1].id);
        });
        bar.appendChild(next);

        const sep = document.createElement('span');
        sep.className = 'toolbar-sep';
        bar.appendChild(sep);

        (App.toolbar || []).forEach(tool => {
            const b = document.createElement('button');
            b.className = 'btn tool' + (tool.action === 'play-transform' || tool.action === 'play-inverse' ? ' gold' : '');
            b.textContent = tool.label;
            b.addEventListener('click', () => Engine.runAction(tool));
            bar.appendChild(b);
        });
    }

    /* ---------- 矩阵 / 指标面板 ---------- */
    function updatePanels() {
        const grid = el('matrix-grid');
        const legendBox = el('matrix-legend');
        const title = el('matrix-panel-title');
        const diag = el('diag-list');
        const note = el('matrix-note');

        if (!App.matrix) {
            title.textContent = '实验状态';
            grid.style.gridTemplateColumns = '1fr';
            grid.innerHTML = '<div class="matrix-empty">本实验没有矩阵<br><span>直接拖动向量即可</span></div>';
            legendBox.innerHTML = '';
            diag.innerHTML = '';
            const v = App.vectors.find(x => x.draggable);
            note.textContent = v ? `v = (${fx(v.data[0])}, ${fx(v.data[1])})` : '';
            return;
        }

        const n = App.matrix.length;          // 行数 = 向量维度
        const cols = App.matrix[0].length;    // 列数（可以多于行数，如 2×3）
        const isSquare = n === cols;
        title.textContent = `当前矩阵 A（${n}×${cols}）`;
        grid.style.gridTemplateColumns = `repeat(${cols}, 1fr)`;
        grid.innerHTML = '';
        const colColors = [COLORS.ai, COLORS.aj, COLORS.ak];
        for (let i = 0; i < n; i++) {
            for (let j = 0; j < cols; j++) {
                const cell = document.createElement('div');
                cell.className = 'matrix-cell';
                cell.style.color = colColors[j] || COLORS.v;
                cell.style.borderColor = (colColors[j] || COLORS.v) + '55';
                cell.textContent = fx(App.matrix[i][j]);
                grid.appendChild(cell);
            }
        }
        const baseNames = ['î', 'ĵ', 'k̂'];
        legendBox.innerHTML = Array.from({ length: cols }, (_, j) =>
            `<span style="color:${colColors[j] || COLORS.v}">第 ${j + 1} 列${j < n ? ' = A' + baseNames[j] + ' 的落点' : '（多出来的列）'}</span>`).join('');

        const rank = Mat.rank(App.matrix);
        const rows = [];
        if (isSquare) {
            const d = Mat.det(App.matrix);
            rows.push(['det(A)', fx(d),
                Math.abs(d) < 1e-9 ? '空间被压扁' : (d < 0 ? '空间被翻转' : '面积/体积放大 ' + fx(d) + ' 倍')]);
        }
        rows.push(['rank(A)', String(rank),
            rank === cols ? '列张成整个空间' : '列线性相关，张成维度比列数少']);
        if (n === 2 && isSquare) {
            const e = Mat.eigen2(App.matrix);
            if (e) {
                rows.push(['特征值 λ', `${fx(e.values[0])}, ${fx(e.values[1])}`,
                    `方向 (${fx(e.vectors[0][0])}, ${fx(e.vectors[0][1])}) 与 (${fx(e.vectors[1][0])}, ${fx(e.vectors[1][1])})`]);
            } else {
                rows.push(['特征值 λ', '无实特征值', '这是旋转型矩阵，没有不被转向的方向']);
            }
        }
        diag.innerHTML = rows.map(([k, v, hint]) =>
            `<div class="diag-row"><span class="diag-k">${k}</span><span class="diag-v">${v}</span><span class="diag-h">${hint}</span></div>`
        ).join('');

        note.textContent = App.vectors.find(v => v.draggable)
            ? '拖动手柄操作 · 拖拽空白平移 · 滚轮缩放'
            : '拖拽两列端点 · 拖拽空白平移 · 滚轮缩放';
    }

    /* ---------- 庆祝层 ---------- */
    function showCelebrate(lab) {
        const idx = LABS.indexOf(lab);
        const isLast = idx === LABS.length - 1;
        el('celebrate-text').textContent = isLast
            ? '全部实验完成！去沙盒模式随便玩吧。'
            : `「${lab.title}」已完成，下一个实验已解锁。`;
        const next = el('next-level-btn');
        next.textContent = isLast ? '去沙盒 →' : '下一个实验 →';
        next.onclick = () => Engine.goNext();
        el('celebrate').classList.add('show');
    }

    function hideCelebrate() {
        el('celebrate').classList.remove('show');
        Engine.clearCelebrate();
    }

    function updateZoomLabel() {
        const l = el('zoom-level');
        if (!l) return;
        l.textContent = App.space === '3d' ? '3D' : Math.round(App.cam2d.scale / DEFAULT_SCALE * 100) + '%';
        const hint = el('canvas-hint');
        if (hint) {
            hint.textContent = App.space === '3d'
                ? '拖动小球改列 · 拖拽空白旋转视角 · 滚轮缩放'
                : (App.interact.dragColumns ? '拖动列向量端点 · 拖拽空白平移 · 滚轮缩放'
                    : '拖动箭头端点 · 拖拽空白平移 · 滚轮缩放');
        }
    }

    function renderAll() {
        renderNav();
        renderProgress();
        renderTaskCard();
        renderToolbar();
        updatePanels();
        updateZoomLabel();
    }

    return {
        toast, renderNav, renderProgress, renderTaskCard, renderToolbar,
        updatePanels, updateZoomLabel, renderAll, showCelebrate, hideCelebrate, renderCrossLink,
        playChime, el
    };
})();
