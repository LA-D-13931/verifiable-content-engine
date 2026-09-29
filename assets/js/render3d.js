/* ============================================================
 * 模块 5：Canvas 3D 渲染器
 * 极简自写投影：yaw（绕 y 轴）/ pitch（俯仰）/ dist（距离）。
 * 不引 Three.js——本页只需要线框立方体、三根基向量和几个手柄。
 * ============================================================ */
window.Render3D = (function () {
    'use strict';

    let ctx, W, H;

    function bind(canvas) { ctx = canvas.getContext('2d'); }

    function setSize(w, h) { W = w; H = h; }

    function cam() { return App.cam3d; }

    function project(p) {
        const { yaw, pitch, dist } = cam();
        const cy = Math.cos(yaw), sy = Math.sin(yaw);
        const x1 = p[0] * cy - p[2] * sy;
        const z1 = p[0] * sy + p[2] * cy;
        const cp = Math.cos(pitch), sp = Math.sin(pitch);
        const y2 = p[1] * cp - z1 * sp;
        const z2 = p[1] * sp + z1 * cp;
        const d = dist - z2;
        const f = 520 / Math.max(d, 0.6);
        return { x: W / 2 + x1 * f, y: H / 2 - y2 * f, depth: z2, f };
    }

    /* 屏幕点 → 世界点（在给定的相机空间深度 depth 处反解）。
       project 的逆：先由 d 求相机系坐标，再按 yaw/pitch 旋转回世界系。
       用于拖拽——差值 dx/dy 对外层拖拽逻辑是线性的，够精确。 */
    function unproject(sx, sy, depth) {
        const { yaw, pitch, dist } = cam();
        const d = dist - depth;
        const f = 520 / Math.max(d, 0.6);
        const X = (sx - W / 2) / f;
        const Y = -(sy - H / 2) / f;
        const cp = Math.cos(pitch), sp = Math.sin(pitch);
        const cy = Math.cos(yaw), sy2 = Math.sin(yaw);
        // 相机基向量（世界系）
        const right = [cy, 0, sy2];
        const up = [sp * sy2, cp, -sp * cy];
        const fwd = [cp * sy2, -sp, -cp * cy];
        const px = X * d, py = Y * d;
        return [
            px * right[0] + py * up[0] + d * fwd[0],
            px * right[1] + py * up[1] + d * fwd[1],
            px * right[2] + py * up[2] + d * fwd[2]
        ];
    }

    function seg(p, q, color, width, dash) {
        const a = project(p), b = project(q);
        ctx.save();
        ctx.strokeStyle = color;
        ctx.lineWidth = width || 1.4;
        ctx.setLineDash(dash || []);
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.stroke();
        ctx.restore();
    }

    function arrow(p, q, color, width) {
        const a = project(p), b = project(q);
        const len = Math.hypot(b.x - a.x, b.y - a.y);
        const head = Math.min(10, Math.max(4, len * 0.18));
        ctx.save();
        ctx.strokeStyle = color;
        ctx.lineWidth = width || 2.6;
        ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
        const ang = Math.atan2(b.y - a.y, b.x - a.x);
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.moveTo(b.x, b.y);
        ctx.lineTo(b.x - head * Math.cos(ang - 0.42), b.y - head * Math.sin(ang - 0.42));
        ctx.lineTo(b.x - head * Math.cos(ang + 0.42), b.y - head * Math.sin(ang + 0.42));
        ctx.closePath(); ctx.fill();
        ctx.restore();
    }

    function text(s, p, color) {
        const a = project(p);
        ctx.save();
        ctx.font = '600 13px system-ui,sans-serif';
        const w = ctx.measureText(s).width;
        ctx.fillStyle = 'rgba(5,9,14,0.72)';
        ctx.fillRect(a.x + 5, a.y - 19, w + 8, 17);
        ctx.fillStyle = color;
        ctx.fillText(s, a.x + 9, a.y - 6);
        ctx.restore();
    }

    /* 三维网格：xz 与 xy 两个平面的整数网格线（范围 -N..N） */
    function drawFloor() {
        const N = 4;
        for (let i = -N; i <= N; i++) {
            seg([i, 0, -N], [i, 0, N], 'rgba(142,197,255,0.11)', 1);
            seg([-N, 0, i], [N, 0, i], 'rgba(142,197,255,0.11)', 1);
            seg([i, -N, 0], [i, N, 0], 'rgba(142,197,255,0.06)', 1);
            seg([-N, i, 0], [N, i, 0], 'rgba(142,197,255,0.06)', 1);
        }
    }

    function axes() {
        const L = 5;
        seg([-L, 0, 0], [L, 0, 0], 'rgba(238,246,251,0.28)', 1.3);
        seg([0, -L, 0], [0, L, 0], 'rgba(238,246,251,0.28)', 1.3);
        seg([0, 0, -L], [0, 0, L], 'rgba(238,246,251,0.28)', 1.3);
    }

    const CUBE = [
        [0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0],
        [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]
    ];
    const EDGES = [
        [0, 1], [1, 2], [2, 3], [3, 0],
        [4, 5], [5, 6], [6, 7], [7, 4],
        [0, 4], [1, 5], [2, 6], [3, 7]
    ];

    function drawCube(m, color) {
        if (!m) return;
        const p = CUBE.map(v => Mat.mulVec(m, v));
        EDGES.forEach(([i, j]) => seg(p[i], p[j], color, 1.5));
    }

    function drawSolid(m, fillColor) {
        if (!m) return;
        const p = CUBE.map(v => Mat.mulVec(m, v)).map(project);
        // 画三个可见面（按深度排序取前 4 个面，简单起见全画并半透明叠加）
        const FACES = [
            [0, 1, 2, 3], [4, 5, 6, 7], [0, 1, 5, 4],
            [3, 2, 6, 7], [1, 2, 6, 5], [0, 3, 7, 4]
        ];
        ctx.save();
        ctx.fillStyle = fillColor;
        FACES.forEach(f => {
            ctx.beginPath();
            f.forEach((idx, k) => {
                const q = p[idx];
                if (k === 0) ctx.moveTo(q.x, q.y); else ctx.lineTo(q.x, q.y);
            });
            ctx.closePath();
            ctx.fill();
        });
        ctx.restore();
    }

    function drawBasisArrows(m) {
        const o = [0, 0, 0];
        const colors = [COLORS.ai, COLORS.aj, COLORS.ak];
        const names = ['Aî', 'Aĵ', 'Ak̂'];
        const oS = project(o);
        const placed = [];
        for (let j = 0; j < 3; j++) {
            const col = m.map(r => r[j]);
            arrow(o, col, colors[j], 2.8);
            const p = project(col);
            const far = Math.hypot(p.x - oS.x, p.y - oS.y) > 34;
            // 两个列的视线方向接近时投影会重叠，只标第一个，避免文字互相压住
            const clash = placed.some(q => Math.hypot(q.x - p.x, q.y - p.y) < 52);
            if (far && !clash) {
                text(names[j], col, colors[j]);
                placed.push(p);
            }
        }
    }

    function drawHandles3d() {
        if (!App.matrix) return;
        for (let j = 0; j < 3; j++) {
            const col = App.matrix.map(r => r[j]);
            if (!col.every(Number.isFinite)) continue;
            const p = project(col);
            const hovered = App.hover && App.hover.kind === 'col' && App.hover.index === j;
            ctx.save();
            ctx.beginPath();
            ctx.arc(p.x, p.y, hovered ? 9 : 7, 0, Math.PI * 2);
            ctx.fillStyle = [COLORS.ai, COLORS.aj, COLORS.ak][j];
            ctx.fill();
            ctx.lineWidth = 2;
            ctx.strokeStyle = 'rgba(5,9,14,0.85)';
            ctx.stroke();
            ctx.restore();
        }
    }

    function drawVectors3d() {
        App.vectors.forEach(v => {
            if (v.data.length < 3) return;
            arrow([0, 0, 0], v.data, v.color, 2.8);
            text(v.label, v.data, v.color);
            if (App.matrix && v.showTransform) {
                const q = Mat.mulVec(App.matrix, v.data);
                arrow([0, 0, 0], q, COLORS.av, 2.4);
                text(v.transformLabel || 'Av', q, COLORS.av);
            }
        });
    }

    function round2(n) { return Math.round(n * 100) / 100; }

    /* 叉积：a×b 是一根同时垂直于 a、b 的向量，长度 = 平行四边形面积 */
    function drawCross3d() {
        const cr = App.cross;
        if (!cr || !App.matrix) return;
        const a = App.matrix.map(r => r[cr.colA]);
        const b = App.matrix.map(r => r[cr.colB]);
        const c = Mat.cross(a, b);
        const mag = Math.hypot(c[0], c[1], c[2]);

        // 平行四边形（a、b 张成）
        const quad = [[0, 0, 0], a, [a[0] + b[0], a[1] + b[1], a[2] + b[2]], b].map(project);
        ctx.save();
        ctx.fillStyle = 'rgba(142,197,255,0.16)';
        ctx.strokeStyle = 'rgba(142,197,255,0.7)';
        ctx.lineWidth = 1.4;
        ctx.beginPath();
        quad.forEach((pt, k) => { if (k === 0) ctx.moveTo(pt.x, pt.y); else ctx.lineTo(pt.x, pt.y); });
        ctx.closePath(); ctx.fill(); ctx.stroke();
        ctx.restore();

        if (mag < 1e-6) {
            text('a×b = 0（a 与 b 共线，面积为 0）', [1.4, 1.8, 0], 'rgba(251,113,133,0.95)');
            return;
        }
        arrow([0, 0, 0], c, 'rgba(103,232,165,0.95)', 3);
        text(`${cr.label || 'a×b'}  |a×b| = ${round2(mag)}`, c, 'rgba(103,232,165,0.95)');
    }

    function render() {
        if (!ctx) return;
        ctx.clearRect(0, 0, W, H);
        drawFloor();
        axes();
        if (App.matrix) {
            drawSolid(App.matrix, 'rgba(103,232,165,0.13)');
            drawCube(App.matrix, 'rgba(103,232,165,0.85)');
        }
        drawCube(Mat.identity(3), 'rgba(142,197,255,0.7)');
        drawBasisArrows(App.matrix || Mat.identity(3));
        drawCross3d();
        drawVectors3d();
        drawHandles3d();
    }

    return { bind, setSize, project, unproject, render };
})();
