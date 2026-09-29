/* ============================================================
 * 模块 6：指针交互
 * 命中测试 → 拖拽（带吸附）/ 平移 / 缩放 / 3D 轨道
 * ============================================================ */
window.Interact = (function () {
    'use strict';

    let canvas = null;
    let dragging = null;   // {kind:'vec'|'col', index, depth?}
    let panning = null;    // {sx, sy, panX, panY}
    let orbiting = null;   // {sx, sy, yaw, pitch}
    let last = { x: 0, y: 0 };

    const HIT_R = 18;      // 命中半径（像素）

    function init(cv) {
        canvas = cv;
        canvas.addEventListener('pointerdown', onDown);
        canvas.addEventListener('pointermove', onMove);
        canvas.addEventListener('pointerup', endDrag);
        canvas.addEventListener('pointercancel', endDrag);
        canvas.addEventListener('pointerleave', () => { App.hover = null; requestRender(); });
        canvas.addEventListener('wheel', onWheel, { passive: false });
        canvas.addEventListener('dblclick', () => { Render2D.resetCamera(); Render2D.fitView(); });
        canvas.addEventListener('contextmenu', e => e.preventDefault());
    }

    function pointOf(e) {
        const r = canvas.getBoundingClientRect();
        return { x: e.clientX - r.left, y: e.clientY - r.top };
    }

    function requestRender() {
        if (window.Render2D) Render2D.render();
    }

    /* ---------- 手柄位置：渲染器与命中测试共用同一份真值 ---------- */
    function handles() {
        const out = [];
        if (App.space === '3d') {
            if (App.matrix && (App.interact.dragColumns || true)) {
                for (let j = 0; j < App.matrixSize; j++) {
                    const col = App.matrix.map(r => r[j]);
                    if (!col.every(Number.isFinite)) continue;
                    out.push({ kind: 'col', index: j, p: col, screen: Render3D.project(col), color: [COLORS.ai, COLORS.aj, COLORS.ak][j] });
                }
            }
            return out;
        }
        if (App.matrix && App.interact.dragColumns) {
            for (let j = 0; j < App.matrixSize; j++) {
                const col = App.matrix.map(r => r[j]);
                out.push({
                    kind: 'col', index: j, p: col,
                    screen: Render2D.w2s(col),
                    color: j === 0 ? COLORS.ai : (j === 1 ? COLORS.aj : COLORS.ak)
                });
            }
        }
        if (App.interact.dragVectors) {
            App.vectors.forEach((v, i) => {
                if (!v.draggable) return;
                out.push({ kind: 'vec', index: i, p: v.data, screen: Render2D.w2s(v.data), color: v.color });
            });
        }
        return out;
    }

    function hitTest(sx, sy) {
        const hs = handles();
        let best = null, bestD = HIT_R;
        hs.forEach(h => {
            const d = Math.hypot(h.screen.x - sx, h.screen.y - sy);
            if (d <= bestD) { bestD = d; best = h; }
        });
        return best;
    }

    /* 吸附：屏幕距离小于 12px 时吸到最近的 0.5，避免拖不准 */
    function snap(p) {
        const s = App.cam2d.scale;
        const tol = 12 / s;
        const out = p.map(x => {
            const n = Math.round(x * 2) / 2;
            return Math.abs(x - n) <= tol ? n : Math.round(x * 100) / 100;
        });
        return out;
    }

    /* ---------- 事件 ---------- */
    function onDown(e) {
        canvas.focus();
        const p = pointOf(e);
        last = p;
        const hit = hitTest(p.x, p.y);

        if (hit) {
            dragging = { kind: hit.kind, index: hit.index };
            if (App.space === '3d') dragging.depth = hit.screen.depth;
            canvas.setPointerCapture(e.pointerId);
            return;
        }

        if (App.space === '3d' && App.interact.orbit) {
            orbiting = { sx: p.x, sy: p.y, yaw: App.cam3d.yaw, pitch: App.cam3d.pitch };
            canvas.setPointerCapture(e.pointerId);
            return;
        }

        if (App.interact.clickPlace && App.vectors.some(v => v.draggable)) {
            const w = Render2D.s2w(p.x, p.y);
            const v = App.vectors.find(x => x.draggable);
            v.data = snap([w[0], w[1]]);
            dragging = { kind: 'vec', index: App.vectors.indexOf(v) };
            Engine.afterChange();
            canvas.setPointerCapture(e.pointerId);
            return;
        }

        panning = { sx: p.x, sy: p.y, panX: App.cam2d.panX, panY: App.cam2d.panY };
        canvas.setPointerCapture(e.pointerId);
    }

    function onMove(e) {
        const p = pointOf(e);

        if (dragging) {
            if (dragging.kind === 'col') {
                if (App.space === '3d') {
                    const prev = Render3D.unproject(last.x, last.y, dragging.depth);
                    const now = Render3D.unproject(p.x, p.y, dragging.depth);
                    const j = dragging.index;
                    const col = App.matrix.map(r => r[j]);
                    const next = col.map((x, i) => x + (now[i] - prev[i]));
                    setColumn(j, next.map(n => Math.round(n * 100) / 100));
                } else {
                    const w = Render2D.s2w(p.x, p.y);
                    setColumn(dragging.index, snap([w[0], w[1]]));
                }
            } else if (dragging.kind === 'vec') {
                const v = App.vectors[dragging.index];
                if (App.space === '3d') {
                    const prev = Render3D.unproject(last.x, last.y, 0);
                    const now = Render3D.unproject(p.x, p.y, 0);
                    v.data = v.data.map((x, i) => Math.round((x + (now[i] - prev[i])) * 100) / 100);
                } else {
                    const w = Render2D.s2w(p.x, p.y);
                    v.data = snap([w[0], w[1]]);
                }
            }
            Engine.afterChange();
        } else if (panning) {
            App.cam2d.panX = panning.panX + (p.x - panning.sx);
            App.cam2d.panY = panning.panY + (p.y - panning.sy);
            requestRender();
        } else if (orbiting) {
            App.cam3d.yaw = orbiting.yaw + (p.x - orbiting.sx) * 0.008;
            App.cam3d.pitch = Math.max(-1.35, Math.min(1.35, orbiting.pitch + (p.y - orbiting.sy) * 0.006));
            requestRender();
        } else {
            const hit = hitTest(p.x, p.y);
            const nextHover = hit ? { kind: hit.kind, index: hit.index } : null;
            const changed = JSON.stringify(nextHover) !== JSON.stringify(App.hover);
            App.hover = nextHover;
            canvas.style.cursor = hit ? 'grab' : (App.interact.orbit && App.space === '3d' ? 'move' : 'default');
            if (changed) requestRender();
        }
        last = p;
    }

    function setColumn(j, col) {
        App.matrix.forEach((row, i) => { row[j] = col[i]; });
    }

    function endDrag(e) {
        if (dragging || panning || orbiting) {
            Engine.afterChange();
        }
        dragging = null;
        panning = null;
        orbiting = null;
        if (e && e.pointerId != null && canvas.hasPointerCapture && canvas.hasPointerCapture(e.pointerId)) {
            canvas.releasePointerCapture(e.pointerId);
        }
    }

    function onWheel(e) {
        e.preventDefault();
        const p = pointOf(e);
        if (App.space === '3d') {
            App.cam3d.dist = Math.max(3.2, Math.min(30, App.cam3d.dist + (e.deltaY > 0 ? 0.7 : -0.7)));
            requestRender();
            return;
        }
        Render2D.zoomAt(p.x, p.y, e.deltaY > 0 ? 0.9 : 1.1);
    }

    function isDragging() { return !!dragging; }

    return { init, handles, hitTest, isDragging, setColumn };
})();
