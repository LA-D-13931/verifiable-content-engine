/* ============================================================
 * 模块 9：入口
 * 全部脚本按顺序同步加载（非 ES 模块，双击 index.html 也能跑）。
 * ============================================================ */
(function () {
    'use strict';

    function boot() {
        // 主题要在读取画布配色之前应用，否则首帧会用错颜色
        if (window.Theme) Theme.init();

        const canvas = document.getElementById('stage-canvas');

        Render2D.setHooks({
            handles: () => Interact.handles(),
            hitTest: (x, y) => Interact.hitTest(x, y)
        });
        Render3D.bind(canvas);
        Render2D.init();
        Render3D.setSize(Render2D.width, Render2D.height);
        window.addEventListener('resize', () => Render3D.setSize(Render2D.width, Render2D.height));

        Interact.init(canvas);

        /* 学习路径折叠开关 */
        const body = document.body;
        document.getElementById('nav-toggle').addEventListener('click', () => {
            body.classList.toggle('nav-collapsed');
            setTimeout(() => { Render2D.resize(); Render3D.setSize(Render2D.width, Render2D.height); }, 200);
        });

        /* 缩放按钮 */
        document.getElementById('zoom-in-btn').addEventListener('click', () => {
            Render2D.zoomAt(Render2D.width / 2, Render2D.height / 2, 1.2);
        });
        document.getElementById('zoom-out-btn').addEventListener('click', () => {
            Render2D.zoomAt(Render2D.width / 2, Render2D.height / 2, 1 / 1.2);
        });
        document.getElementById('zoom-level').addEventListener('click', () => {
            Render2D.resetCamera();
            Render2D.fitView();
            UI.updateZoomLabel();
        });
        document.getElementById('fit-btn').addEventListener('click', () => Render2D.fitView());

        document.getElementById('celebrate-dismiss').addEventListener('click', UI.hideCelebrate);
        document.getElementById('next-level-btn').addEventListener('click', () => Engine.goNext());

        /* 键盘：← → 切换实验，R 重置视角 */
        window.addEventListener('keydown', (e) => {
            if (e.target.tagName === 'INPUT') return;
            const idx = LABS.findIndex(l => l.id === App.labId);
            if (e.key === 'ArrowRight' && idx >= 0 && idx + 1 < LABS.length) Engine.goNext();
            if (e.key === 'ArrowLeft' && idx > 0) Engine.loadLab(LABS[idx - 1].id);
            if (e.key === 'r' || e.key === 'R') { Render2D.resetCamera(); Render2D.fitView(); }
        });

        /* 起始实验：地址里的 #编号 优先，其次是上次进度，最后是第 1 个 */
        const lastId = Engine.loadProgress();
        const startId = Engine.labFromHash()
            || ((lastId && Engine.getLab(lastId)) ? lastId : LABS[0].id);
        UI.renderAll();
        Engine.loadLab(startId);
        UI.updateZoomLabel();

        /* 支持浏览器前进 / 后退，以及从别处点进来的 #编号 */
        window.addEventListener('hashchange', () => {
            const id = Engine.labFromHash();
            if (id && id !== App.labId) Engine.loadLab(id);
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', boot);
    } else {
        boot();
    }
})();
