/* ============================================================
 * 显示偏好：配色主题 / 亮暗模式
 * ------------------------------------------------------------
 * 与线代讲义站**完全共用**同一套偏好：
 *   · 存储键相同（advmath.theme.v1 / advmath.mode.v1）
 *   · 属性写法相同（data-theme / data-mode）
 *   · auto 时移除 data-mode，交给 prefers-color-scheme
 * 所以在讲义站里选的主题，打开实验台就是同一个；反过来也一样。
 *
 * 色板在 assets/css/theme-tokens.css（由 tools/gen-themes.py 生成）。
 * ============================================================ */
window.Theme = (function () {
    'use strict';

    const cfg = window.THEME_CONFIG || {};
    const THEME_KEY = cfg.themeKey || 'advmath.theme.v1';
    const MODE_KEY = cfg.modeKey || 'advmath.mode.v1';
    const THEMES = cfg.themes || [{ id: 'default', name: '霜蓝' }];
    const DEFAULT_THEME = cfg.defaultTheme || 'default';
    const DEFAULT_MODE = cfg.defaultMode || 'auto';

    function read(key, fallback) {
        try { return localStorage.getItem(key) || fallback; } catch (err) { return fallback; }
    }
    function write(key, val) {
        try { localStorage.setItem(key, val); } catch (err) { /* 降级 */ }
    }

    function currentTheme() {
        const t = read(THEME_KEY, DEFAULT_THEME);
        return THEMES.some(x => x.id === t) ? t : DEFAULT_THEME;
    }
    function currentMode() {
        const m = read(MODE_KEY, DEFAULT_MODE);
        return ['light', 'dark', 'auto'].includes(m) ? m : DEFAULT_MODE;
    }

    /* 把偏好写到 <html> 上；auto 时移除 data-mode 以跟随系统 */
    function apply(theme, mode) {
        const el = document.documentElement;
        el.setAttribute('data-theme', theme);
        if (mode === 'auto') el.removeAttribute('data-mode');
        else el.setAttribute('data-mode', mode);
        // 画布与面板的配色都从 token 读；refreshColors 内部会重绘受影响的部分
        if (typeof window.refreshColors === 'function') window.refreshColors();
    }

    function setTheme(id) {
        write(THEME_KEY, id);
        apply(id, currentMode());
        paint();
    }
    function setMode(m) {
        write(MODE_KEY, m);
        apply(currentTheme(), m);
        paint();
    }
    function cycleMode() {
        const order = ['auto', 'light', 'dark'];
        setMode(order[(order.indexOf(currentMode()) + 1) % order.length]);
    }

    const MODE_LABEL = { auto: '跟随系统', light: '亮色', dark: '暗色' };

    /* 顶栏控件：主题下拉 + 亮暗切换按钮 */
    function build() {
        const box = document.getElementById('theme-controls');
        if (!box) return;

        const sel = document.createElement('select');
        sel.className = 'theme-select';
        sel.setAttribute('aria-label', '切换配色主题');
        THEMES.forEach(t => {
            const o = document.createElement('option');
            o.value = t.id;
            o.textContent = t.name;
            sel.appendChild(o);
        });
        sel.value = currentTheme();
        sel.addEventListener('change', () => setTheme(sel.value));
        box.appendChild(sel);

        const btn = document.createElement('button');
        btn.className = 'theme-mode-btn';
        btn.type = 'button';
        btn.title = '在「跟随系统 / 亮色 / 暗色」之间切换';
        box.appendChild(btn);

        box._sel = sel;
        box._btn = btn;
        paint();
    }

    function paint() {
        const box = document.getElementById('theme-controls');
        if (!box || !box._sel) return;
        box._sel.value = currentTheme();
        const m = currentMode();
        box._btn.textContent = (m === 'dark' ? '🌙 ' : m === 'light' ? '☀️ ' : '🖥 ') + MODE_LABEL[m];
        box._btn.setAttribute('aria-label', '当前亮暗模式：' + MODE_LABEL[m] + '，点击切换');
    }

    /* 跟随系统时，系统切换要重绘画布 */
    if (window.matchMedia) {
        try {
            window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
                if (currentMode() === 'auto') apply(currentTheme(), 'auto');
            });
        } catch (err) { /* 老浏览器忽略 */ }
    }

    function init() {
        apply(currentTheme(), currentMode());
        build();
    }

    return { init, apply, setTheme, setMode, cycleMode, currentTheme, currentMode, THEMES };
})();
