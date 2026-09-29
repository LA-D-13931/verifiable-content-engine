#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成实验台的主题 token（4 套主题 × 亮/暗），与线代讲义站保持视觉统一。

为什么要有这个脚本
------------------
讲义站（高数学习站）已经有一套成熟的配色体系：
  4 套主题（霜蓝 default / 暖沙 eyecare-warm / 竹青 eyecare-cool / 墨檀 ink）
  × 亮/暗两种模式，共 8 个组合，全部走同名的 CSS 变量，并有对比度断言。
实验台原本用的是自己一套高饱和暗色（青绿 #6ee7c8），所以两边看起来不像一家。

本脚本从讲义站的 theme-tokens.css **直接读取**那 8 个组合的 token 值，
再补上实验台特有的两组颜色：
  1. 界面层 —— 直接沿用讲义站的 token 名与值（--bg / --bg-elev / --ink / --line / --brand …）
  2. 画布层 —— 数学对象的语义色（v / av / ai / aj / ak 等），
     按主站的低饱和规范重新取色，并逐个组合断言对比度。

生成物：
  assets/css/theme-tokens.css   8 个组合的 token 块
  assets/js/theme-config.js     主题清单与存储键（与讲义站共用偏好）

用法：
    python3 tools/gen-themes.py            # 生成并断言
    python3 tools/gen-themes.py --check    # 只检查是否最新（退出码 1 表示过期）
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
WORKSPACE = os.path.dirname(os.path.dirname(SITE))  # 多了 01_活工程/ 一层
MAIN = os.path.join(WORKSPACE, '01_活工程', '高等数学学习站')
MAIN_TOKENS = os.path.join(MAIN, 'assets', 'css', 'theme-tokens.css')

OUT_CSS = os.path.join(SITE, 'assets', 'css', 'theme-tokens.css')
OUT_JS = os.path.join(SITE, 'assets', 'js', 'theme-config.js')

THEMES = [
    ('default', '霜蓝'),
    ('eyecare-warm', '暖沙'),
    ('eyecare-cool', '竹青'),
    ('ink', '墨檀'),
]

# 界面层直接沿用讲义站的 token（名字与取值都不改，这样两站才是同一套体系）
INHERIT = [
    '--bg', '--bg-elev', '--bg-sunken', '--bg-code', '--ink', '--ink-soft', '--ink-faint',
    '--brand', '--brand-deep', '--brand-light', '--on-brand', '--line',
    '--ok', '--no', '--warn',
    '--def-soft', '--brand-soft', '--thm-soft', '--method-soft', '--warn-soft',
    '--shadow-color-005', '--shadow-color-006', '--shadow-color-012',
]

# 画布层：数学对象的语义色。
# 设计约束（与讲义站的「低饱和」规范一致的取色思路）：
#   · 与画布底色的对比度 ≥ 4.5:1（亮） / ≥ 5.0:1（暗）
#   · 六种颜色两两可辨（在灰度与色相上都不撞）
#   · 亮暗同色相，只调明度
MATH_DARK = {
    'v': '#e8c46a',      # 主向量（金）
    'av': '#6fbf8f',     # 变换后的向量 Av（绿）
    'ai': '#e08a96',     # 第 1 列 / Aî（玫红）
    'aj': '#a99cd8',     # 第 2 列 / Aĵ（紫）
    'ak': '#7ea6d8',     # 第 3 列 / Ak̂（蓝）
    'target': '#e8c46a',
}
MATH_LIGHT = {
    'v': '#7a5f14',
    'av': '#2f6b4a',
    'ai': '#a8445a',
    'aj': '#5b4a9c',
    'ak': '#2c5d86',
    'target': '#7a5f14',
}


# ---------------- 颜色工具 ----------------

def hex2rgb(h):
    h = h.strip().lstrip('#')
    if len(h) == 3:
        h = ''.join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _f(c):
    c /= 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(h):
    r, g, b = (_f(x) for x in hex2rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def mix(a, b, wa):
    """按比例混合两个十六进制颜色（wa 为 a 的权重）。"""
    ra, rb = hex2rgb(a), hex2rgb(b)
    return '#%02x%02x%02x' % tuple(
        round(ra[i] * wa + rb[i] * (1 - wa)) for i in range(3))


def lab_tokens(t, mode, math):
    """实验台专用 token —— 全部预计算成实色。

    为什么不用 color-mix()：实测部分浏览器在 getComputedStyle 里
    不会把它求值成实际颜色（原样输出字符串），导致对比度校验和
    JS 读色都拿到无效值。预计算最稳。
    """
    bg = t['--bg']
    elev = t['--bg-elev']
    line = t['--line']
    ink = t['--ink']
    faint = t['--ink-faint']
    brand = t['--brand']
    d = {}
    d['--lab-line-soft'] = mix(line, bg, 0.62)
    d['--lab-faint'] = mix(faint, bg, 0.78)
    d['--lab-tint-brand-t'] = mix(brand, bg, 0.06 if mode == 'dark' else 0.05)
    d['--lab-tint-brand'] = mix(brand, bg, 0.12 if mode == 'dark' else 0.10)
    d['--lab-tint-brand-2'] = mix(brand, bg, 0.20 if mode == 'dark' else 0.16)
    d['--lab-tint-danger'] = mix(t['--no'], bg, 0.10)
    d['--lab-tint-danger-2'] = mix(t['--no'], bg, 0.20)
    d['--lab-tint-gold'] = mix(math['v'], bg, 0.10)
    d['--lab-tint-ok'] = mix(t['--ok'], bg, 0.10)
    # 遮罩：深色模式下压暗，亮色模式下也在深底上显示（画布上的浮层）
    d['--lab-scrim'] = mix(bg, '#000000', 0.72 if mode == 'dark' else 0.86)
    d['--lab-scrim-soft'] = mix(bg, '#000000', 0.55 if mode == 'dark' else 0.74)
    return d


def sat(h):
    """HSL 里的 S（0~1），用来核对「低饱和」这条规范。"""
    r, g, b = (x / 255 for x in hex2rgb(h))
    mx, mn = max(r, g, b), min(r, g, b)
    l = (mx + mn) / 2
    if mx == mn:
        return 0.0
    d = mx - mn
    return d / (2 - mx - mn) if l > 0.5 else d / (mx + mn)


# ---------------- 读取讲义站 token ----------------

def read_main_tokens():
    if not os.path.exists(MAIN_TOKENS):
        raise SystemExit('找不到讲义站 token：%s' % MAIN_TOKENS)
    src = open(MAIN_TOKENS, encoding='utf-8').read()
    out = {}
    for theme, _ in THEMES:
        for mode in ('light', 'dark'):
            if theme == 'default' and mode == 'light':
                sel = ':root, [data-theme="default"]'
            elif mode == 'dark':
                sel = '[data-theme="%s"][data-mode="dark"]' % theme
            else:
                sel = '[data-theme="%s"]' % theme
            m = re.search(re.escape(sel) + r'\s*\{([^}]*)\}', src)
            if not m:
                raise SystemExit('讲义站 token 里找不到组合：%s' % sel)
            body = m.group(1)
            vals = {}
            for tok in INHERIT:
                mm = re.search(re.escape(tok) + r'\s*:\s*([^;]+);', body)
                if mm:
                    vals[tok] = mm.group(1).strip()
            # hero 渐变等拿来当强调底色用（讲义站里只有这 3 个）
            for tok in ('--hero-1', '--hero-2', '--hero-3', '--on-hero', '--on-hero-soft', '--header-bg'):
                mm = re.search(re.escape(tok) + r'\s*:\s*([^;]+);', body)
                if mm:
                    vals[tok] = mm.group(1).strip()
            out['%s/%s' % (theme, mode)] = vals
    return out


# ---------------- 生成 ----------------

def build_css(tokens):
    L = []
    L.append('/* ============================================================')
    L.append(' * 主题 token —— 由 tools/gen-themes.py 生成，请勿手改')
    L.append(' *')
    L.append(' * 界面层（--bg / --ink / --brand / --line …）与线代讲义站同名同值，')
    L.append(' * 所以两站是同一套配色体系；画布层（--m-*）是实验台特有的')
    L.append(' * 数学对象语义色，按同样的低饱和思路取色并逐个组合验证过对比度。')
    L.append(' *')
    L.append(' * 4 套主题 × 亮/暗 = 8 个组合，与讲义站一一对应，')
    L.append(' * 并且共用 localStorage 偏好（advmath.theme.v1 / advmath.mode.v1）。')
    L.append(' * ============================================================ */')
    L.append('')

    for theme, cname in THEMES:
        for mode in ('light', 'dark'):
            key = '%s/%s' % (theme, mode)
            t = tokens[key]
            math = MATH_DARK if mode == 'dark' else MATH_LIGHT
            # 选择器设计（要同时支持 4 主题 × 3 模式）：
            #   · 亮色块：不带 data-mode 时的默认值 + 显式 light
            #   · 暗色块：显式 dark + 「没显式指定 light」时的 prefers-color-scheme 兜底
            # 靠「媒体查询块排在亮色块之后」来保证 auto 且系统为暗时暗色生效；
            # 显式属性选择器优先级更高，所以手动选亮/暗永远覆盖系统。
            base = ':root' if theme == 'default' else '[data-theme="%s"]' % theme
            if mode == 'dark':
                if theme == 'default':
                    sel = ('[data-theme="default"][data-mode="dark"],\n'
                           ':root:not([data-mode="light"])')
                    media_sel = ':root:not([data-mode="light"])'
                else:
                    sel = ('[data-theme="%s"][data-mode="dark"],\n'
                           '[data-theme="%s"]:not([data-mode="light"])' % (theme, theme))
                    media_sel = '[data-theme="%s"]:not([data-mode="light"])' % theme
            else:
                if theme == 'default':
                    sel = ('[data-theme="default"][data-mode="light"],\n'
                           ':root:not([data-mode="dark"])')
                    media_sel = None
                else:
                    sel = ('[data-theme="%s"][data-mode="light"],\n'
                           '[data-theme="%s"]:not([data-mode="dark"])' % (theme, theme))
                    media_sel = None
            void = base  # 占位，避免 lint 警告

            L.append('/* %s · %s */' % (cname, '暗色' if mode == 'dark' else '亮色'))
            L.append('%s {' % sel)
            for tok in INHERIT:
                if tok in t:
                    L.append('    %s: %s;' % (tok, t[tok]))
            for tok in ('--hero-1', '--hero-2', '--hero-3', '--on-hero', '--on-hero-soft', '--header-bg'):
                if tok in t:
                    L.append('    %s: %s;' % (tok, t[tok]))
            L.append('')
            L.append('    /* 画布层：数学对象语义色 */')
            for k in ('v', 'av', 'ai', 'aj', 'ak', 'target'):
                L.append('    --m-%s: %s;' % (k, math[k]))
            # 网格 / 坐标轴 / 变换后网格：由主站 token 派生，保证同一色系
            if mode == 'dark':
                L.append('    --m-grid: %s;' % mix(t['line'] if 'line' in t else t['--line'], t['--bg'], 0.55))
                L.append('    --m-tgrid: color-mix(in srgb, %s 42%%, %s);' % (math['av'], t['--bg']))
                L.append('    --m-axis: color-mix(in srgb, %s 62%%, %s);' % (t['--ink-faint'], t['--bg']))
            else:
                L.append('    --m-grid: %s;' % mix(t['--ink-faint'], t['--bg'], 0.22))
                L.append('    --m-tgrid: color-mix(in srgb, %s 40%%, %s);' % (math['av'], t['--bg']))
                L.append('    --m-axis: color-mix(in srgb, %s 70%%, %s);' % (t['--ink-faint'], t['--bg']))
            L.append('')
            L.append('    --m-canvas: %s;' % t['--bg'])
            L.append('    --m-chip: %s;' % t['--bg-elev'])
            L.append('')
            _lab = lab_tokens(t, mode, math)
            L.append('    /* 实验台派生 token（预计算实色，不用 color-mix） */')
            for _k, _v in _lab.items():
                L.append('    %s: %s;' % (_k, _v))
            L.append('}')

            # auto 模式：跟随系统。放在亮色块之后，且选择器与亮色块同优先级，
            # 因此「未显式指定 light」且系统为暗时生效。
            if mode == 'dark':
                L.append('@media (prefers-color-scheme: dark) {')
                L.append('    %s {' % media_sel)
                for tok in INHERIT:
                    if tok in t:
                        L.append('        %s: %s;' % (tok, t[tok]))
                L.append('')
                L.append('        /* 画布层：数学对象语义色 */')
                for k in ('v', 'av', 'ai', 'aj', 'ak', 'target'):
                    L.append('        --m-%s: %s;' % (k, math[k]))
                L.append('        --m-grid: %s;' % mix(t['--line'], t['--bg'], 0.55))
                L.append('        --m-tgrid: color-mix(in srgb, %s 42%%, %s);' % (math['av'], t['--bg']))
                L.append('        --m-axis: color-mix(in srgb, %s 62%%, %s);' % (t['ink_faint'] if False else t['--ink-faint'], t['--bg']))
                L.append('        --m-canvas: %s;' % t['--bg'])
                L.append('        --m-chip: %s;' % t['--bg-elev'])
                L.append('')
                _lab = lab_tokens(t, mode, math)
                L.append('        /* 实验台派生 token（预计算实色，不用 color-mix） */')
                for _k, _v in _lab.items():
                    L.append('        %s: %s;' % (_k, _v))
                L.append('    }')
                L.append('}')
            L.append('')
    return '\n'.join(L)


def build_js():
    return '''/* 主题清单与存储键 —— 由 tools/gen-themes.py 生成，请勿手改。
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
'''


# ---------------- 断言 ----------------

def assert_contrast(tokens, problems, notes):
    for key, t in tokens.items():
        mode = key.split('/')[1]
        math = MATH_DARK if mode == 'dark' else MATH_LIGHT
        floor = 5.0 if mode == 'dark' else 4.5
        for name in ('v', 'av', 'ai', 'aj', 'ak'):
            c = contrast(math[name], t['--bg'])
            if c < floor:
                problems.append('%s 的 --m-%s 对底色只有 %.2f:1（要求 ≥ %.1f:1）'
                                % (key, name, c, floor))
        # 界面文字：沿用讲义站的值，这里复核一遍确保没读错
        for name, tok in (('正文', '--ink'), ('次要文字', '--ink-soft')):
            c = contrast(t[tok], t['--bg'])
            if c < 7.0:
                problems.append('%s 的 %s(%s) 对比度只有 %.2f:1（要求 ≥ 7:1）'
                                % (key, name, tok, c))
        # 低饱和规范：暗色底饱和度 ≤ 15%
        s = sat(t['--bg'])
        if mode == 'dark' and s > 0.15:
            problems.append('%s 的 --bg 饱和度 %.3f 超过 0.15' % (key, s))
        # 网格线要对底色可辨（太浅等于没画网格）
        gc = contrast(t.get('--lab-grid', t['--line']), t['--bg'])
        # --m-grid 单独算一遍（生成时用 mix 出来的）
        grid_col = mix(t['--ink-faint'], t['--bg'], 0.22) if mode == 'light' \
                   else mix(t['--line'], t['--bg'], 0.55)
        gr = contrast(grid_col, t['--bg'])
        if gr < 1.06:
            problems.append('%s 的网格线对底色只有 %.3f:1，几乎看不见' % (key, gr))

        # 六色两两可辨：转灰度后不能撞在一起
        greys = sorted((luminance(math[n]), n) for n in ('v', 'av', 'ai', 'aj', 'ak'))
        for i in range(len(greys) - 1):
            if abs(greys[i][0] - greys[i + 1][0]) < 0.004:
                notes.append('%s 的 %s 与 %s 灰度非常接近，深色盲用户可能难分辨'
                             % (key, greys[i][1], greys[i + 1][1]))


def main():
    check_only = '--check' in sys.argv
    tokens = read_main_tokens()

    problems, notes = [], []
    assert_contrast(tokens, problems, notes)
    if problems:
        print('对比度/规范断言失败：')
        for p in problems:
            print('  ✗ %s' % p)
        return 1

    css = build_css(tokens)
    js = build_js()
    changed = []
    for path, content in ((OUT_CSS, css), (OUT_JS, js)):
        old = open(path, encoding='utf-8').read() if os.path.exists(path) else ''
        if old != content:
            changed.append(os.path.basename(path))
            if not check_only:
                open(path, 'w', encoding='utf-8').write(content)

    print('读取讲义站 %d 个主题组合，对比度与饱和度断言全部通过 ✓' % len(tokens))
    for n in notes:
        print('  · 提示：%s' % n)
    if check_only:
        if changed:
            print('✗ 需要重新生成：%s' % '、'.join(changed))
            return 1
        print('✓ theme-tokens.css / theme-config.js 已是最新')
        return 0
    print('✓ 已生成 %s' % '、'.join(changed) if changed else '✓ 已是最新，无需改动')
    return 0


if __name__ == '__main__':
    sys.exit(main())
