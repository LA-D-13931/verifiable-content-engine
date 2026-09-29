/* ============================================================
 * 模块 4：Canvas 2D 渲染器（scene 驱动，无状态）
 * 只读 App 里的场景字段画图；世界坐标 y 向上、屏幕坐标 y 向下。
 * ============================================================ */
window.Render2D = (function () {
    'use strict';

    const canvas = document.getElementById('stage-canvas');
    const ctx = canvas.getContext('2d');
    let W = 0, H = 0;

    /* 外层可注入的钩子（避免模块间循环依赖） */
    let hooks = { handles: () => [], hitTest: () => null };
    function setHooks(h) { hooks = Object.assign(hooks, h); }

    function init() {
        resize();
        window.addEventListener('resize', resize);
    }

    function resize() {
        const wrap = canvas.parentElement;
        const dpr = window.devicePixelRatio || 1;
        W = wrap.clientWidth;
        H = wrap.clientHeight;
        canvas.width = Math.round(W * dpr);
        canvas.height = Math.round(H * dpr);
        canvas.style.width = W + 'px';
        canvas.style.height = H + 'px';
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        render();
    }

    function origin() {
        return { cx: W / 2 + App.cam2d.panX, cy: H / 2 + App.cam2d.panY };
    }

    function w2s(p) {
        const { cx, cy } = origin();
        return { x: cx + p[0] * App.cam2d.scale, y: cy - p[1] * App.cam2d.scale };
    }

    function s2w(sx, sy) {
        const { cx, cy } = origin();
        return [(sx - cx) / App.cam2d.scale, (cy - sy) / App.cam2d.scale];
    }

    function zoomAt(sx, sy, factor) {
        const cam = App.cam2d;
        const next = Math.max(MIN_SCALE, Math.min(MAX_SCALE, cam.scale * factor));
        if (next === cam.scale) return;
        const w = s2w(sx, sy);
        cam.scale = next;
        cam.panX = sx - w[0] * cam.scale - W / 2;
        cam.panY = sy + w[1] * cam.scale - H / 2;
        if (window.UI) UI.updateZoomLabel();
        render();
    }

    function resetCamera() {
        if (App.space === '3d') {
            App.cam3d = { yaw: -0.7, pitch: 0.4, dist: 11 };
        } else {
            App.cam2d = { scale: DEFAULT_SCALE, panX: 0, panY: 0 };
        }
        if (window.UI) UI.updateZoomLabel();
    }

    /* 自动取景：扫所有要画的点，留 90px 边距反推缩放，上限 1.45×默认 */
    function fitView() {
        if (App.space === '3d') { resetCamera(); render(); return; }
        const pts = [[0, 0], [1, 0], [0, 1], [1, 1]];
        App.vectors.forEach(v => {
            pts.push(v.data);
            if (v.showTransform && App.matrix) pts.push(Mat.mulVec(App.matrix, v.data));
        });
        if (App.matrix && App.matrixSize === 2) {
            // 两列的落点
            pts.push(App.matrix.map(r => r[0]));
            pts.push(App.matrix.map(r => r[1]));
        }
        if (App.targetPoint) pts.push(App.targetPoint.point);
        let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
        pts.forEach(([x, y]) => {
            minX = Math.min(minX, x); maxX = Math.max(maxX, x);
            minY = Math.min(minY, y); maxY = Math.max(maxY, y);
        });
        const margin = 90;
        const w = Math.max(maxX - minX, 1), h = Math.max(maxY - minY, 1);
        App.cam2d.scale = Math.max(MIN_SCALE, Math.min(
            Math.min((W - margin * 2) / w, (H - margin * 2) / h),
            DEFAULT_SCALE * 1.45));
        App.cam2d.panX = -((minX + maxX) / 2) * App.cam2d.scale;
        App.cam2d.panY = ((minY + maxY) / 2) * App.cam2d.scale;
        if (window.UI) UI.updateZoomLabel();
        render();
    }

    /* ---------- 绘制原语 ---------- */

    function drawGrid(cx, cy, s) {
        const step = s < 22 ? 2 : 1;
        const x0 = Math.floor(-cx / s) - 1, x1 = Math.ceil((W - cx) / s) + 1;
        const y0 = Math.floor((cy - H) / s) - 1, y1 = Math.ceil(cy / s) + 1;
        ctx.strokeStyle = COLORS.grid;
        ctx.lineWidth = 1;
        ctx.beginPath();
        for (let i = x0; i <= x1; i += step) {
            const x = Math.round(cx + i * s) + 0.5;
            ctx.moveTo(x, 0); ctx.lineTo(x, H);
        }
        for (let j = y0; j <= y1; j += step) {
            const y = Math.round(cy - j * s) + 0.5;
            ctx.moveTo(0, y); ctx.lineTo(W, y);
        }
        ctx.stroke();
    }

    /* 变换后的网格：对每条整数竖线/横线取两个端点做 A 变换后连线 */
    function drawTGrid(m) {
        const span = Math.ceil(Math.max(W, H) / App.cam2d.scale) + 6;
        ctx.strokeStyle = COLORS.tgrid;
        ctx.lineWidth = 1.2;
        ctx.beginPath();
        for (let i = -span; i <= span; i++) {
            let p = w2s(Mat.mulVec(m, [i, -span]));
            let q = w2s(Mat.mulVec(m, [i, span]));
            ctx.moveTo(p.x, p.y); ctx.lineTo(q.x, q.y);
            p = w2s(Mat.mulVec(m, [-span, i]));
            q = w2s(Mat.mulVec(m, [span, i]));
            ctx.moveTo(p.x, p.y); ctx.lineTo(q.x, q.y);
        }
        ctx.stroke();
    }

    function drawAxes(cx, cy) {
        ctx.strokeStyle = COLORS.axis;
        ctx.lineWidth = 1.4;
        ctx.beginPath();
        ctx.moveTo(0, Math.round(cy) + 0.5); ctx.lineTo(W, Math.round(cy) + 0.5);
        ctx.moveTo(Math.round(cx) + 0.5, 0); ctx.lineTo(Math.round(cx) + 0.5, H);
        ctx.stroke();
        ctx.fillStyle = 'rgba(238,246,251,0.45)';
        ctx.font = '12px system-ui,sans-serif';
        ctx.fillText('x', W - 16, cy - 8);
        ctx.fillText('y', cx + 8, 16);
    }

    function drawArrow(x1, y1, x2, y2, color, opt) {
        opt = opt || {};
        const head = opt.head || 9;
        const width = opt.width || 2.4;
        ctx.save();
        ctx.strokeStyle = color;
        ctx.fillStyle = color;
        ctx.lineWidth = width;
        ctx.setLineDash(opt.dash || []);
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();
        ctx.setLineDash([]);
        const ang = Math.atan2(y2 - y1, x2 - x1);
        if (Math.hypot(x2 - x1, y2 - y1) > head * 0.8) {
            ctx.beginPath();
            ctx.moveTo(x2, y2);
            ctx.lineTo(x2 - head * Math.cos(ang - 0.42), y2 - head * Math.sin(ang - 0.42));
            ctx.lineTo(x2 - head * Math.cos(ang + 0.42), y2 - head * Math.sin(ang + 0.42));
            ctx.closePath();
            ctx.fill();
        }
        ctx.restore();
    }

    function label(text, x, y, color, bg) {
        ctx.save();
        ctx.font = '600 13px system-ui,sans-serif';
        const w = ctx.measureText(text).width;
        if (bg !== false) {
            ctx.fillStyle = 'rgba(5,9,14,0.72)';
            ctx.fillRect(x - 3, y - 13, w + 8, 17);
        }
        ctx.fillStyle = color;
        ctx.fillText(text, x, y);
        ctx.restore();
    }

    /* ---------- 场景元素 ---------- */

    /* 基准方块：'square' 是单位正方形；'area' 是半格正方形。
       area 模式让「原方块 + 变换后方块」同时可见——单位正方形会被
       变换后的方块完全盖住，看不出面积对比。 */
    const BASE_SIZE = { square: 1, area: 0.5 };

    function drawBaseShape(size) {
        const o = w2s([0, 0]), a = w2s([size, 0]), b = w2s([size, size]), c = w2s([0, size]);
        ctx.save();
        ctx.fillStyle = 'rgba(142,197,255,0.20)';
        ctx.strokeStyle = 'rgba(142,197,255,0.75)';
        ctx.lineWidth = 1.6;
        ctx.beginPath();
        ctx.moveTo(o.x, o.y); ctx.lineTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.lineTo(c.x, c.y);
        ctx.closePath();
        ctx.fill(); ctx.stroke();
        ctx.restore();
    }

    function drawTransformedShape(m, size) {
        const o = w2s(Mat.mulVec(m, [0, 0]));
        const a = w2s(Mat.mulVec(m, [size, 0]));
        const b = w2s(Mat.mulVec(m, [size, size]));
        const c = w2s(Mat.mulVec(m, [0, size]));
        const d = Mat.det(m);
        const fill = d < 0 ? 'rgba(251,113,133,0.26)' : 'rgba(103,232,165,0.24)';
        const line = d < 0 ? 'rgba(251,113,133,0.9)' : 'rgba(103,232,165,0.85)';
        ctx.save();
        ctx.fillStyle = fill;
        ctx.strokeStyle = line;
        ctx.lineWidth = 1.8;
        ctx.beginPath();
        ctx.moveTo(o.x, o.y); ctx.lineTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.lineTo(c.x, c.y);
        ctx.closePath();
        ctx.fill(); ctx.stroke();
        ctx.restore();
    }

    function drawLine(line) {
        const span = Math.ceil(Math.max(W, H) / App.cam2d.scale) + 6;
        const [a, b, c] = [line.a, line.b, line.c];
        const pts = [];
        if (Math.abs(b) > 1e-9) {
            pts.push([-span, (c - a * -span) / b]);
            pts.push([span, (c - a * span) / b]);
        } else if (Math.abs(a) > 1e-9) {
            const x = c / a;
            pts.push([x, -span], [x, span]);
        }
        if (pts.length < 2) return;
        const p = w2s(pts[0]), q = w2s(pts[1]);
        ctx.save();
        ctx.strokeStyle = line.color || 'rgba(196,181,253,0.75)';
        ctx.lineWidth = 1.6;
        if (line.dash) ctx.setLineDash(line.dash);
        ctx.beginPath();
        ctx.moveTo(p.x, p.y); ctx.lineTo(q.x, q.y);
        ctx.stroke();
        ctx.restore();
    }

    function drawBasis(m) {
        const cols = [0, 1].map(j => m.map(r => r[j]));
        const colors = [COLORS.ai, COLORS.aj];
        const names = ['Aî', 'Aĵ'];
        const o = w2s([0, 0]);
        cols.forEach((col, j) => {
            const p = w2s(col);
            drawArrow(o.x, o.y, p.x, p.y, colors[j], { width: 3, dash: [6, 4] });
            label(names[j], p.x + 7, p.y - 7, colors[j]);
        });
    }

    function drawComboPath() {
        const v = App.vectors.find(x => x.id === 'v');
        if (!v) return;
        const u = App.vectors.find(x => x.id === 'u');
        const w = App.vectors.find(x => x.id === 'w');
        if (!u || !w) return;
        const M = [[u.data[0], w.data[0]], [u.data[1], w.data[1]]];
        const c = Mat.solve2(M, v.data);
        if (!c) return;
        const o = w2s([0, 0]);
        const p1 = w2s([u.data[0] * c[0], u.data[1] * c[0]]);
        const p2 = w2s(v.data);
        ctx.save();
        ctx.setLineDash([5, 4]);
        ctx.lineWidth = 1.4;
        ctx.strokeStyle = 'rgba(251,113,133,0.7)';
        ctx.beginPath(); ctx.moveTo(o.x, o.y); ctx.lineTo(p1.x, p1.y); ctx.stroke();
        ctx.strokeStyle = 'rgba(196,181,253,0.7)';
        ctx.beginPath(); ctx.moveTo(p1.x, p1.y); ctx.lineTo(p2.x, p2.y); ctx.stroke();
        ctx.restore();
        const fx = (n) => (Math.round(n * 100) / 100);
        label(`v = ${fx(c[0])}·u + ${fx(c[1])}·w`, p2.x + 8, p2.y + 18, 'rgba(238,246,251,0.8)');
    }

    function drawTargetPoint() {
        const t = App.targetPoint;
        if (!t) return;
        const p = w2s(t.point);
        ctx.save();
        ctx.strokeStyle = COLORS.target;
        ctx.lineWidth = 2;
        ctx.beginPath(); ctx.arc(p.x, p.y, 7, 0, Math.PI * 2); ctx.stroke();
        ctx.beginPath(); ctx.arc(p.x, p.y, 2.4, 0, Math.PI * 2);
        ctx.fillStyle = COLORS.target; ctx.fill();
        ctx.restore();
        label(t.label || '目标', p.x + 11, p.y - 9, COLORS.target);
    }

    function drawSceneVector(v) {
        const o = w2s([0, 0]);
        const p = w2s(v.data);
        drawArrow(o.x, o.y, p.x, p.y, v.color, { width: 2.8, dash: v.dashed ? [5, 4] : [] });
        if (App.matrix && v.showTransform) {
            const q = w2s(Mat.mulVec(App.matrix, v.data));
            drawArrow(o.x, o.y, q.x, q.y, COLORS.av, { width: 2.4, dash: [7, 4] });
            label(v.transformLabel || 'Av', q.x + 8, q.y + 16, COLORS.av);
        }
        if (v.lineUp) {
            const L = 40;
            const len = Math.hypot(v.data[0], v.data[1]) || 1;
            const u = [v.data[0] / len, v.data[1] / len];
            const a = w2s([u[0] * L, u[1] * L]), b = w2s([-u[0] * L, -u[1] * L]);
            ctx.save();
            ctx.setLineDash([3, 6]);
            ctx.strokeStyle = 'rgba(246,207,114,0.5)';
            ctx.lineWidth = 1.2;
            ctx.beginPath(); ctx.moveTo(b.x, b.y); ctx.lineTo(a.x, a.y); ctx.stroke();
            ctx.restore();
        }
        label(v.label, p.x + 8, p.y + 16, v.color);
    }

    function drawHandles() {
        const hs = hooks.handles();
        hs.forEach(h => {
            const p = w2s(h.p);
            const isHover = App.hover && App.hover.kind === h.kind && App.hover.index === h.index;
            ctx.save();
            ctx.beginPath();
            ctx.arc(p.x, p.y, isHover ? 8 : 6, 0, Math.PI * 2);
            ctx.fillStyle = h.color;
            ctx.globalAlpha = isHover ? 1 : 0.92;
            ctx.fill();
            ctx.lineWidth = 2;
            ctx.strokeStyle = 'rgba(5,9,14,0.85)';
            ctx.stroke();
            ctx.restore();
        });
    }

    function drawEigenHint() {
        if (!App.showEigen || !App.matrix || App.matrixSize !== 2) return;
        const e = Mat.eigen2(App.matrix);
        if (!e) return;
        const L = 30;
        e.vectors.forEach((v, i) => {
            const a = w2s([v[0] * L, v[1] * L]), b = w2s([-v[0] * L, -v[1] * L]);
            ctx.save();
            ctx.setLineDash([2, 7]);
            ctx.strokeStyle = 'rgba(103,232,165,0.55)';
            ctx.lineWidth = 1.3;
            ctx.beginPath(); ctx.moveTo(b.x, b.y); ctx.lineTo(a.x, a.y); ctx.stroke();
            ctx.restore();
            if (i === 0) {
                label(`λ₁ = ${round2(e.values[0])}`, a.x + 8, a.y - 6, 'rgba(103,232,165,0.9)');
            }
        });
    }

    function round2(n) { return Math.round(n * 100) / 100; }

    /* ---------- 列空间（秩的几何） ----------
       rank 2：两列张成整个平面 → 铺一层淡色底
       rank 1：塌缩成过原点的一条直线 → 把那条直线画出来
       rank 0：只剩原点 */
    function drawSpan() {
        if (!App.matrix || App.matrixSize !== 2) return;
        const cols = [0, 1].map(j => App.matrix.map(r => r[j]));
        const L = Math.ceil(Math.max(W, H) / App.cam2d.scale) + 6;
        const rank = Mat.rank(App.matrix);

        if (rank === 2) {
            ctx.save();
            ctx.fillStyle = 'rgba(110,231,200,0.06)';
            ctx.fillRect(0, 0, W, H);
            ctx.restore();
            label('列空间 = 整个平面（秩 2）', 18, 52, 'rgba(110,231,200,0.95)');
            return;
        }

        // 取第一根非零列作为直线的方向
        let dir = cols.find(c => Math.hypot(c[0], c[1]) > 1e-6);
        if (!dir) {
            label('列空间 = 只有原点（秩 0）', 18, 52, 'rgba(251,113,133,0.95)');
            return;
        }
        const len = Math.hypot(dir[0], dir[1]);
        const u = [dir[0] / len, dir[1] / len];
        const p = w2s([u[0] * L, u[1] * L]);
        const q = w2s([-u[0] * L, -u[1] * L]);
        ctx.save();
        ctx.strokeStyle = 'rgba(110,231,200,0.62)';
        ctx.lineWidth = 7;
        ctx.lineCap = 'round';
        ctx.globalAlpha = 0.55;
        ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(q.x, q.y); ctx.stroke();
        ctx.restore();
        label('列空间 = 一条直线（秩 1）：平面被压扁了', 18, 52, 'rgba(110,231,200,0.95)');
    }

    /* ---------- 零空间：被 A 压到原点的那些方向 ----------
       2×2 且秩为 1 时，零空间是一条过原点的直线。
       直线方向 = 与矩阵的行向量都垂直的方向，也就是 A 的零空间。 */
    function drawNullSpace() {
        if (!App.matrix || App.matrixSize !== 2) return;
        if (Mat.rank(App.matrix) !== 1) {
            if (Mat.rank(App.matrix) === 0) {
                // 零矩阵：整个平面都被压到原点
                ctx.save();
                ctx.fillStyle = 'rgba(196,181,253,0.07)';
                ctx.fillRect(0, 0, W, H);
                ctx.restore();
                label('零空间 = 整个平面（A 是零矩阵）', 18, 74, 'rgba(196,181,253,0.95)');
            } else {
                label('零空间只有零向量（A 可逆）', 18, 74, 'rgba(196,181,253,0.95)');
            }
            return;
        }
        // 秩 1：行向量的垂直方向就是零空间方向。
        // 取第一行 (a, b)，则 (-b, a) 与它垂直，且 A·(-b,a) = 0。
        const a = App.matrix[0][0], b = App.matrix[0][1];
        let d = [-b, a];
        if (Math.hypot(d[0], d[1]) < 1e-9) d = [0, 1];
        const L = Math.hypot(d[0], d[1]);
        const u = [d[0] / L, d[1] / L];
        const span = Math.ceil(Math.max(W, H) / App.cam2d.scale) + 6;
        const p = w2s([u[0] * span, u[1] * span]);
        const q = w2s([-u[0] * span, -u[1] * span]);
        ctx.save();
        ctx.strokeStyle = 'rgba(196,181,253,0.85)';
        ctx.lineWidth = 5;
        ctx.lineCap = 'round';
        ctx.globalAlpha = 0.7;
        ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(q.x, q.y); ctx.stroke();
        ctx.restore();
        label('零空间：这条线上的向量都被压到原点', 18, 74, 'rgba(196,181,253,0.95)');
    }

    /* ---------- 基变换：v 在新基（矩阵两列）下的坐标 ---------- */
    function drawBasisCoords() {
        const v = App.vectors.find(x => x.id === 'v');
        if (!v || !App.matrix || App.matrixSize !== 2) return;
        const B = App.matrix;
        const c = Mat.solve2(B, v.data);
        if (!c) {
            label('v 不在新基的张成里，无坐标', 18, 30, 'rgba(251,113,133,0.95)');
            return;
        }
        const b1 = B.map(r => r[0]), b2 = B.map(r => r[1]);
        const o = w2s([0, 0]);
        const p1 = w2s([b1[0] * c[0], b1[1] * c[0]]);
        const pv = w2s(v.data);
        const p2 = w2s([b2[0] * c[1], b2[1] * c[1]]);
        const q2 = w2s(v.data);

        ctx.save();
        ctx.setLineDash([5, 4]);
        ctx.lineWidth = 1.5;
        ctx.strokeStyle = 'rgba(251,113,133,0.75)';
        ctx.beginPath(); ctx.moveTo(o.x, o.y); ctx.lineTo(p1.x, p1.y); ctx.stroke();
        ctx.strokeStyle = 'rgba(196,181,253,0.75)';
        ctx.beginPath(); ctx.moveTo(p1.x, p1.y); ctx.lineTo(pv.x, pv.y); ctx.stroke();
        // 另一条组合路径（先走 b2 再走 b1），构成坐标平行四边形
        ctx.strokeStyle = 'rgba(196,181,253,0.4)';
        ctx.beginPath(); ctx.moveTo(o.x, o.y); ctx.lineTo(p2.x, p2.y); ctx.stroke();
        ctx.strokeStyle = 'rgba(251,113,133,0.4)';
        ctx.beginPath(); ctx.moveTo(p2.x, p2.y); ctx.lineTo(q2.x, q2.y); ctx.stroke();
        ctx.restore();

        label(`新基坐标 (c₁, c₂) = (${round2(c[0])}, ${round2(c[1])})`,
            pv.x + 10, pv.y - 10, 'rgba(238,246,251,0.92)');
    }

    /* ---------- 1D 数轴（点积 / 对偶课） ---------- */
    function drawNumLine() {
        const nl = App.numLine;
        if (!nl) return;
        const y = H - 74;
        const s = App.cam2d.scale;
        const cx = W / 2 + App.cam2d.panX;
        ctx.save();
        ctx.strokeStyle = 'rgba(238,246,251,0.45)';
        ctx.lineWidth = 1.6;
        ctx.beginPath(); ctx.moveTo(40, y); ctx.lineTo(W - 40, y); ctx.stroke();
        ctx.fillStyle = 'rgba(238,246,251,0.45)';
        ctx.font = '11px system-ui,sans-serif';
        const [lo, hi] = nl.range;
        for (let k = lo; k <= hi; k++) {
            const x = cx + k * s;
            if (x < 36 || x > W - 36) continue;
            ctx.beginPath(); ctx.moveTo(x, y - 4); ctx.lineTo(x, y + 4); ctx.stroke();
            ctx.fillText(String(k), x - 3, y + 18);
        }
        ctx.restore();
        label(nl.title || '数轴（1 维）', 44, y - 14, 'rgba(196,181,253,0.9)');
    }

    /* 把一个向量投影到数轴上（取它在 1D 基方向上的分量） */
    function drawOneDim() {
        const od = App.oneDim;
        if (!od) return;
        const basis = od.basis || [1, 0];
        const bn = Math.hypot(basis[0], basis[1]) || 1;
        const u = [basis[0] / bn, basis[1] / bn];
        const y = H - 74;
        const s = App.cam2d.scale;
        const cx = W / 2 + App.cam2d.panX;
        const o = w2s([0, 0]);

        App.vectors.forEach(v => {
            const comp = Mat.dot(v.data, u);
            const onLine = [u[0] * comp, u[1] * comp];
            const p = w2s(onLine);
            // 到数轴的虚线
            ctx.save();
            ctx.setLineDash([4, 4]);
            ctx.strokeStyle = v.color + '99';
            ctx.lineWidth = 1.2;
            ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(p.x, y); ctx.stroke();
            if (od.proj) {
                // 垂线：从 v 端点垂直落到 1D 方向所在直线上
                ctx.strokeStyle = 'rgba(103,232,165,0.55)';
                ctx.beginPath(); ctx.moveTo(o.x, o.y);
                ctx.lineTo(p.x, p.y); ctx.stroke();
            }
            ctx.restore();
            ctx.save();
            ctx.beginPath();
            ctx.arc(p.x, y, 5.5, 0, Math.PI * 2);
            ctx.fillStyle = v.color;
            ctx.fill();
            ctx.lineWidth = 2;
            ctx.strokeStyle = 'rgba(5,9,14,0.85)';
            ctx.stroke();
            ctx.restore();
            label(`${v.label} → ${round2(comp)}`, p.x + 8, y - 10, v.color);
        });
        // 1D 方向本身
        const tip = w2s([u[0] * 1, u[1] * 1]);
        drawArrow(o.x, o.y, tip.x, tip.y, 'rgba(196,181,253,0.8)', { width: 2, dash: [5, 4] });
        void cx; void s;
    }

    /* ---------- 点积：u·v 读数 + v 在 u 上的投影 ---------- */
    function drawDotPair() {
        const dp = App.dotPair;
        if (!dp) return;
        const a = App.vectors.find(x => x.id === dp.a);
        const b = App.vectors.find(x => x.id === dp.b);
        if (!a || !b) return;
        const la = Math.hypot(a.data[0], a.data[1]);
        if (la < 1e-6) return;
        const u = [a.data[0] / la, a.data[1] / la];
        const comp = Mat.dot(b.data, u);
        const foot = [u[0] * comp, u[1] * comp];
        const pb = w2s(b.data);
        const pf = w2s(foot);
        const o = w2s([0, 0]);

        if (dp.proj) {
            ctx.save();
            ctx.setLineDash([4, 4]);
            ctx.strokeStyle = 'rgba(103,232,165,0.7)';
            ctx.lineWidth = 1.4;
            ctx.beginPath(); ctx.moveTo(pb.x, pb.y); ctx.lineTo(pf.x, pf.y); ctx.stroke();
            ctx.restore();
            drawArrow(o.x, o.y, pf.x, pf.y, 'rgba(103,232,165,0.9)', { width: 3 });
            // 直角标记
            const da = [pb.x - pf.x, pb.y - pf.y];
            const dl = Math.hypot(da[0], da[1]);
            if (dl > 12) {
                const d2 = [-u[0], u[1]];
                const px = pf.x + d2[0] * 9, py = pf.y + d2[1] * 9;
                ctx.save();
                ctx.strokeStyle = 'rgba(103,232,165,0.6)';
                ctx.lineWidth = 1.2;
                ctx.beginPath();
                ctx.moveTo(px, py);
                ctx.lineTo(px + da[0] / dl * 9, py + da[1] / dl * 9);
                ctx.stroke();
                ctx.restore();
            }
        }
        const d = Mat.dot(a.data, b.data);
        label(`${a.label}·${b.label} = ${round2(d)}`, 18, 30, 'rgba(103,232,165,0.95)');
        if (dp.showCos) {
            const cos = d / (la * (Math.hypot(b.data[0], b.data[1]) || 1));
            label(`cosθ = ${round2(cos)}`, 18, 50, 'rgba(196,181,253,0.9)');
        }
    }

    /* ---------- 3D 列向量的叉积在 2D 里不画，这里只画 2D 的有向面积 ---------- */
    function drawCrossArea() {
        const cr = App.cross;
        if (!cr || App.space === '3d' || !App.matrix) return;
        const a = App.matrix.map(r => r[cr.colA]);
        const b = App.matrix.map(r => r[cr.colB]);
        const o = w2s([0, 0]), pa = w2s(a), pb = w2s(b), pab = w2s([a[0] + b[0], a[1] + b[1]]);
        ctx.save();
        ctx.fillStyle = 'rgba(142,197,255,0.16)';
        ctx.strokeStyle = 'rgba(142,197,255,0.7)';
        ctx.lineWidth = 1.4;
        ctx.beginPath();
        ctx.moveTo(o.x, o.y); ctx.lineTo(pa.x, pa.y); ctx.lineTo(pab.x, pab.y); ctx.lineTo(pb.x, pb.y);
        ctx.closePath(); ctx.fill(); ctx.stroke();
        ctx.restore();
        const signed = a[0] * b[1] - a[1] * b[0];
        label(`有向面积 a×b = ${round2(signed)}`, 18, 30, 'rgba(142,197,255,0.95)');
    }

    /* ---------- 主渲染 ---------- */
    function render() {
        if (!ctx) return;
        ctx.clearRect(0, 0, W, H);
        if (App.space === '3d') { window.Render3D.render(); return; }

        const { cx, cy } = origin();
        const s = App.cam2d.scale;

        if (App.grid) drawGrid(cx, cy, s);
        if (App.spanView) drawSpan();
        if (App.nullView) drawNullSpace();
        if (App.axes) drawAxes(cx, cy);
        if (App.matrix && App.tgrid) drawTGrid(App.matrix);
        const baseSize = BASE_SIZE[App.shape];
        if (baseSize) {
            drawBaseShape(baseSize);
            if (App.matrix) drawTransformedShape(App.matrix, baseSize);
        }
        if (App.cross) drawCrossArea();
        if (App.comboPath) drawComboPath();
        App.lines.forEach(drawLine);
        if (App.basis && App.matrix && App.matrixSize === 2) drawBasis(App.matrix);
        drawEigenHint();
        App.vectors.forEach(drawSceneVector);
        if (App.basisCoords) drawBasisCoords();
        if (App.dotPair) drawDotPair();
        drawTargetPoint();
        if (App.numLine) { drawNumLine(); drawOneDim(); }
        drawHandles();
    }

    return {
        canvas, ctx, init, resize, render, fitView, resetCamera,
        w2s, s2w, zoomAt, setHooks, label, drawArrow,
        get width() { return W; },
        get height() { return H; }
    };
})();
