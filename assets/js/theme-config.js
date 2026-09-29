/* 主题清单与存储键 —— 由 tools/gen-themes.py 生成，请勿手改。
   存储键与线代讲义站完全一致（advmath.theme.v1 / advmath.mode.v1），
   所以在讲义站里选的主题会直接带到实验台，反之亦然。 */
window.THEME_CONFIG = {
    themes: [
        { id: 'default',       name: '霜蓝' },
        { id: 'eyecare-warm',  name: '暖沙' },
        { id: 'eyecare-cool',  name: '竹青' },
        { id: 'ink',           name: '墨檀' }
    ],
    themeKey: 'advmath.theme.v1',
    modeKey: 'advmath.mode.v1',
    defaultTheme: 'default',
    defaultMode: 'auto'        // 'light' | 'dark' | 'auto'（auto 时跟随系统）
};
