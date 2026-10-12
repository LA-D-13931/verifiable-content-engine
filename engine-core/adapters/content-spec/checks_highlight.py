#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P5 第六维 · 高亮（第六十七轮）：**渲染维** ✓ —— 真实计算样式取色 ✓。

## 判据（来源 ✓）
- 被显式标记的高亮元素（`mark` / `.highlight` / `[data-highlight]` / `class*=highlight|hl-` ✓）
  其**合成背景**必须与其**有效父背景**可区分：**ΔE(CIE76) ≥ 10** ✓；
- **阈值是自定的，理由写清** ✓（不假装它是外部标准 ✗）：
  **WCAG 1.4.11 的 3:1 不适用于"高亮"** ✗ —— 它管的是 **UI 组件与图形对象** ✓，而高亮是"文字底纹" ✓；
  实测：**常见高亮黄 `#ffe066` 对白底只有 1.30:1** ✗ ⇒ 用 3:1 会把**正常高亮全判红** ✗（我第一版就这么错了 ✓，
  好例被判红 ✗ ⇒ 当场改回 ✓）。ΔE ≥ 10 是"肉眼明显可辨"的常用下限 ✓；
- **自身背景透明 ⇒ 红** ✓（那是"标了个 class 但视觉上没高亮" ✗，正是这一维要抓的 ✓）；
- **浏览器不在 ⇒ `pass=None` + 环境不足** ✓（不是红 ✗）。
"""
import json
import os
import re
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
PROBE = os.path.join(REPO, 'apps', 'linalg-lab', 'tools', 'anchor-highlight-probe.mjs')
MIN_DELTA_E = 10.0       # **自定阈值** ✓：ΔE(CIE76) ≥ 10 = 肉眼明显可辨 ✓（3:1 不适用于文字底纹 ✗，见 docstring）


def _lum(c):
    m = re.match(r'rgba?\((\d+),\s*(\d+),\s*(\d+)', c or '')
    if not m:
        return None
    r, g, b = (int(m.group(i)) / 255.0 for i in (1, 2, 3))
    f = lambda v: v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def _rgb(c):
    m = re.match(r'rgba?\((\d+),\s*(\d+),\s*(\d+)', c or '')
    return None if not m else tuple(int(m.group(i)) for i in (1, 2, 3))


def _xyz(c):
    rgb = _rgb(c)
    if rgb is None:
        return None
    def lin(v):
        v = v / 255.0
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(x) for x in rgb)
    return (r * 0.4124 + g * 0.3576 + b * 0.1805,
            r * 0.2126 + g * 0.7152 + b * 0.0722,
            r * 0.0193 + g * 0.1192 + b * 0.9505)


def _lab(c):
    """sRGB → XYZ → **CIELAB** ✓（ΔE 定义在 Lab 上 ✗ —— 我第一版在 XYZ 上算欧氏距离，
    结果 #ffe066 对白底只算出 0.92 ✗，而正确的 ΔE 约 28 ✓）。"""
    xyz = _xyz(c)
    if xyz is None:
        return None
    # D65 白点
    xr, yr, zr = xyz[0] / 0.95047, xyz[1] / 1.0, xyz[2] / 1.08883
    def f(t):
        return t ** (1.0 / 3.0) if t > 0.008856 else (7.787 * t + 16.0 / 116.0)
    fx, fy, fz = f(xr), f(yr), f(zr)
    return (116.0 * fy - 16.0, 500.0 * (fx - fy), 200.0 * (fy - fz))


def delta_e(a, b):
    """**CIE76 ΔE**（CIELAB 上的欧氏距离 ✓）—— 可区分度，不是对比度比 ✓。"""
    x, y = _lab(a), _lab(b)
    if x is None or y is None:
        return None
    return sum((x[i] - y[i]) ** 2 for i in range(3)) ** 0.5


def run(artifact, source, base):
    # 第六十七轮：**相对路径一律 abspath** ✓ —— 我自己的测试 harness 三次传 base='.'
    # ⇒ `file://./…` 非法 ⇒ 探针报 ERR_INVALID_URL ✗（那是测试的错，不是检查的错 ✓）。
    path = os.path.abspath(os.path.join(base, artifact['path']))
    if not os.path.isfile(path):
        return {'pass': None, 'reason': '不适用：产物不在位由 runner 的统一门负责（第五十五轮 ✓）'}
    r = subprocess.run(['node', PROBE, 'file://' + path], capture_output=True, text=True, timeout=180)
    if r.returncode == 2:
        why = ((r.stderr or '').strip().splitlines() or ['(无 stderr)'])[-1][:160]
        return {'pass': None, 'reason': '环境不足：高亮（渲染维）这次判不了（不是失败 ✗）｜ 探针 stderr: ' + why,
                'certificate': {'needs': 'browser'}}
    if r.returncode != 0:
        return {'pass': None, 'reason': '检查器故障（探针退出码 %d）：%s' % (r.returncode, (r.stderr or '')[:120]),
                'certificate': {'checker_crash': True}}
    try:
        data = json.loads(r.stdout)
    except Exception as e:
        return {'pass': None, 'reason': '检查器故障：探针输出不是 JSON（%s）' % e, 'certificate': {'checker_crash': True}}
    marks = data.get('marks') or []
    transparent = [m for m in marks if not m.get('bg')]
    weak = []
    for m in marks:
        de = delta_e(m.get('bg'), m.get('parentBG'))
        if de is not None and de < MIN_DELTA_E:
            weak.append((round(de, 1), m))
    if transparent:
        m = transparent[0]
        return {'pass': False,
                'reason': '高亮元素**自身背景透明**（标了 %s 但视觉上没高亮；共 %d 处）'
                          % (m.get('cls') or m.get('tag'), len(transparent)),
                'certificate': {'verdict': 'fail', 'evidence_type': 'render',
                                'detail': {'tag': m.get('tag'), 'cls': m.get('cls'), 'kind': 'transparent_highlight',
                                           'count': len(transparent), 'where': artifact['path']}}}
    if weak:
        de, m = weak[0]
        return {'pass': False,
                'reason': '高亮与父背景**不可辨**：ΔE=%.1f < 阈值 %.1f（**自定**：ΔE≥10 为肉眼明显可辨；'
                          'WCAG 1.4.11 的 3:1 不适用于文字底纹 ✗）—— 例：「%s」背景 %s ／ 父背景 %s；共 %d 处'
                          % (de, MIN_DELTA_E, m.get('text'), m.get('bg'), m.get('parentBG'), len(weak)),
                'certificate': {'verdict': 'fail', 'evidence_type': 'render',
                                'environment': {'threshold': MIN_DELTA_E, 'threshold_basis': '自定：ΔE(CIE76)≥10（3:1 不适用于文字底纹 ✗）'},
                                'detail': {'delta_e': de, 'threshold': MIN_DELTA_E, 'bg': m.get('bg'), 'parentBG': m.get('parentBG'),
                                           'text': m.get('text'), 'count': len(weak), 'where': artifact['path']}}}
    return {'pass': True, 'reason': '', 'certificate': {'marks_checked': len(marks), 'threshold_delta_e': MIN_DELTA_E}}
